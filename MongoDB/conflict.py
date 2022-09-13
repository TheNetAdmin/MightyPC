import contextlib
import copy
import csv
import json
import logging
import os
import re
from pathlib import Path

import click
from fuzzywuzzy import process

from utils import make_mongodb

log_format = logging.Formatter(
    "[%(asctime)s][%(filename)s:%(lineno)4s - %(funcName)10s()] %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
handler = logging.FileHandler("conflict.log")
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)


@click.group()
def conflict():
    pass


@conflict.command()
@click.option("-i", "--submission_id", type=int)
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
@click.option("-m", "--mag_dbcol_name", required=True, default="mag:paper")
@click.option("-p", "--pcmember_dbcol_name", required=True, default="hotcrp:pc")
@click.option("-f", "--force", is_flag=True)
def check_author_in_conflict(
    submission_id, submission_dbcol_name, mag_dbcol_name, pcmember_dbcol_name, force
):
    """Check if a submission's author is specified as a conflict"""
    sdb = make_mongodb(submission_dbcol_name)
    mdb = make_mongodb(mag_dbcol_name)
    pdb = make_mongodb(pcmember_dbcol_name)

    all_pc = pdb.client.find()

    if submission_id:
        check_author_in_conflict_single(submission_id, sdb, mdb, pdb, all_pc, force)
    else:
        ids = sdb.client.find().distinct("_id")
        for sid in ids:
            check_author_in_conflict_single(
                sid, sdb, mdb, pdb, copy.deepcopy(all_pc), force
            )


@conflict.command()
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
@click.option("-p", "--pcmember_dbcol_name", required=True, default="hotcrp:pc")
def find_chair_conflict_papers(submission_dbcol_name, pcmember_dbcol_name):
    """Find papers that specify all chairs as conflicts"""
    sdb = make_mongodb(submission_dbcol_name)
    pdb = make_mongodb(pcmember_dbcol_name)

    logger = logging.getLogger()

    all_chairs = list(
        pdb.client.find({"roles": {"$regex": r".*chair.*"}}, {"name": 1, "email": 1})
    )

    all_papers = list(sdb.client.find())
    for p in all_papers:
        all_conflict = True
        for c in all_chairs:
            if c["email"] not in p["pc_conflicts"]:
                all_conflict = False
                break
        if all_conflict:
            logger.info(f"Paper [{p['_id']:>4}] is conflict with all chairs")


def check_author_in_conflict_single(sid, sdb, mdb, pdb, all_pc, force=False):
    logger = logging.getLogger()
    logger.info(f"Checking paper [{sid:>4}]")
    sub = sdb.client.find_one({"_id": sid})
    assert sub is not None

    # 1. Check by email
    all_pc_email = set([p["email"] for p in copy.deepcopy(all_pc)])
    for author in sub["authors"]:
        if "email" not in author:
            logger.error(f"    Author does not have email field: {author}")
            continue
        email = author["email"]
        if email in all_pc_email:
            if email not in sub["pc_conflicts"]:
                logger.error(
                    f"    [ERROR][Detected by email] Author is PC but not declared as conflict: {author}"
                )
    # 2. Check by name
    all_pc_name = [(p["first"] + " " + p["last"]) for p in copy.deepcopy(all_pc)]
    for author in sub["authors"]:
        if "first" not in author or "last" not in author:
            logger.error(f"    Author does not have first/last name field: {author}")
            continue
        name = f"{author['first']} {author['last']}"
        name_best_match = process.extractOne(name, all_pc_name, score_cutoff=90)
        logger.debug(f"    Best name match: {name} == {name_best_match}")
        if name_best_match:
            for p in copy.deepcopy(all_pc):
                if (p["first"] + " " + p["last"]) == name_best_match[0]:
                    pc_email = p["email"]
            if pc_email not in sub["pc_conflicts"]:
                logger.error(
                    f"    [ERROR][Detected by name ] Author is PC but not declared as conflict: \n\tPC Member: {name_best_match}\n\tAuthor: {author}"
                )
            if "email" in author:
                if author["email"] not in sub["pc_conflicts"]:
                    logger.info(
                        f"    [INFO ][Detected by name ] Author is PC but using different email from PC profile: {author}"
                    )


if __name__ == "__main__":
    conflict()
