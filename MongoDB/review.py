import contextlib
import csv
import json
import logging
import os
import re
from pathlib import Path

import click

from utils import make_mongodb

log_format = logging.Formatter(
    "[%(asctime)s][%(filename)s:%(lineno)4s - %(funcName)10s()] %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
handler = logging.FileHandler("submission.log")
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)


@click.group()
def review():
    pass


@review.command()
@click.option("-i", "--submission_id", type=int)
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
@click.option(
    "-r",
    "--submission_review_pref_dbcol_name",
    required=True,
    default="hotcrp:review_preference",
)
@click.option("-p", "--pcmember_dbcol_name", required=True, default="hotcrp:pc")
@click.option("-f", "--force", is_flag=True)
def gen_review_preference(
    submission_id,
    submission_dbcol_name,
    submission_review_pref_dbcol_name,
    pcmember_dbcol_name,
    force,
):
    sdb = make_mongodb(submission_dbcol_name)
    rdb = make_mongodb(submission_review_pref_dbcol_name)
    pdb = make_mongodb(pcmember_dbcol_name)

    if submission_id:
        gen_review_preference_single(submission_id, sdb, rdb, pdb, force)
    else:
        ids = sdb.client.find().distinct("_id")
        for sid in ids:
            gen_review_preference_single(sid, sdb, rdb, pdb, force)


def gen_review_preference_single(sid, sdb, rdb, pdb, force=False):
    logger = logging.getLogger()
    logger.info(f"Generating review preference for paper [{sid:>4}]")

    # Get all pc info
    pc_records = pdb.client.find(projection={"name": True, "email": True, "tags": True})
    all_pc = dict()
    for r in pc_records:
        r["tags"] = set(r["tags"])
        all_pc[r["email"]] = r

    # Get submission info
    submission = sdb.client.find_one({"_id": sid})
    submission["tags"] = set(submission["tags"])

    # Get preference list of current paper
    prefs = rdb.client.find({"paper": str(sid)})
    for pref in prefs:
        reviewer = all_pc[pref["email"]]
        score = 0
        for st in submission["tags"]:
            if st in reviewer["tags"]:
                score += 1
        if pref["conflict"] != "":
            score = 0
        preference = "1" if score > 0 else ""
        rdb.client.update_one(
            {"_id": pref["_id"]},
            {"$set": {"preference": preference, "preference_score": score}},
            upsert=True,
        )


if __name__ == "__main__":
    review()
