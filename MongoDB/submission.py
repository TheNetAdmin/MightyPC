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
def submission():
    pass


@submission.command()
@click.option("-i", "--submission_id", type=int)
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
@click.option("-m", "--mag_dbcol_name", required=True, default="mag:paper")
@click.option("-p", "--pcmember_dbcol_name", required=True, default="hotcrp:pc")
@click.option("-f", "--force", is_flag=True)
def check_pc_reference(
    submission_id, submission_dbcol_name, mag_dbcol_name, pcmember_dbcol_name, force
):
    sdb = make_mongodb(submission_dbcol_name)
    mdb = make_mongodb(mag_dbcol_name)
    pdb = make_mongodb(pcmember_dbcol_name)

    if submission_id:
        check_pc_reference_single(submission_id, sdb, mdb, pdb, force)
    else:
        ids = sdb.client.find().distinct("_id")
        for sid in ids:
            check_pc_reference_single(sid, sdb, mdb, pdb, force)


@submission.command()
@click.option("-i", "--submission_id", type=int)
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
@click.option("-m", "--mag_dbcol_name", required=True, default="mag:paper")
@click.option("-p", "--pcmember_dbcol_name", required=True, default="hotcrp:pc")
@click.option("-f", "--force", is_flag=True)
def aggregate_tags(
    submission_id, submission_dbcol_name, mag_dbcol_name, pcmember_dbcol_name, force
):
    sdb = make_mongodb(submission_dbcol_name)
    mdb = make_mongodb(mag_dbcol_name)
    pdb = make_mongodb(pcmember_dbcol_name)

    if submission_id:
        aggregate_tags_single(submission_id, sdb, mdb, pdb, force)
    else:
        ids = sdb.client.find().distinct("_id")
        for sid in ids:
            aggregate_tags_single(sid, sdb, mdb, pdb, force)


@submission.command()
@click.option("-i", "--submission_id", type=int)
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
@click.option("-m", "--mag_dbcol_name", required=True, default="mag:paper")
@click.option("-p", "--pcmember_dbcol_name", required=True, default="hotcrp:pc")
@click.option("-f", "--force", is_flag=True)
def suggest_reviewers(
    submission_id, submission_dbcol_name, mag_dbcol_name, pcmember_dbcol_name, force
):
    sdb = make_mongodb(submission_dbcol_name)
    mdb = make_mongodb(mag_dbcol_name)
    pdb = make_mongodb(pcmember_dbcol_name)

    if submission_id:
        suggest_reviewers_single(submission_id, sdb, mdb, pdb, force)
    else:
        ids = sdb.client.find().distinct("_id")
        for sid in ids:
            suggest_reviewers_single(sid, sdb, mdb, pdb, force)


def suggest_reviewers_single(sid, sdb, mdb, pdb, force=False):
    logger = logging.getLogger()
    logger.info(f"Suggesting reviewers for paper [{sid:>4}]")
    sub = sdb.client.find_one({"_id": sid})
    assert sub is not None
    if "reference" not in sub:
        logger.warning(
            f"Paper [{sid:>4}] does not have reference extraced from pdf: {sub.keys()}"
        )
        return

    sub_conflict = sub["pc_conflicts"]
    pc_no_conflict = dict()

    def get_pc(pemail):
        if pemail not in pc_no_conflict:
            precord = pdb.client.find_one({"_id": pemail})
            if "tpc" in precord["tags"]:
                precord["pc_type"] = "tpc"
            elif "erc" in precord["tags"]:
                precord["pc_type"] = "erc"
            else:
                logger.warning(
                    f'Skip this pc member who is neither tpc nor erc, based on the tags field: {precord["first"]} {precord["last"]}'
                )
                precord["pc_type"] = None
            precord["count_paper"] = 0
            precord["count_cited"] = 0
            pc_no_conflict[pemail] = precord
        return pc_no_conflict[pemail]

    for ref in sub["reference"]:
        ref["pc_paper_no_conflict"] = False
        if ref["pc_paper"]:
            ref["tpc_no_conflict"] = []
            ref["erc_no_conflict"] = []
            for p in ref["mag_record"]["PCAuthor"]:
                if p["email"] not in sub_conflict:
                    ref["pc_paper_no_conflict"] = True
                    pc = get_pc(p["email"])
                    pc["count_paper"] += 1
                    pc["count_cited"] += ref["count"]
                    if pc["pc_type"] == "tpc":
                        ref["tpc_no_conflict"].append(p)
                    elif pc["pc_type"] == "erc":
                        ref["erc_no_conflict"].append(p)

    suggested_reviewers = [p for _, p in pc_no_conflict.items()]
    suggested_reviewers.sort(key=lambda x: x["first"])

    sdb.client.update_one(
        {"_id": sid},
        {
            "$set": {
                "reference": sub["reference"],
                "potential_reviewers": suggested_reviewers,
            }
        },
        upsert=True,
    )


def aggregate_tags_single(sid, sdb, mdb, pdb, force=False):
    logger = logging.getLogger()
    logger.info(f"Aggregating tags for paper [{sid:>4}]")
    sub = sdb.client.find_one({"_id": sid})
    assert sub is not None
    if "reference" not in sub:
        logger.warning(
            f"Paper [{sid:>4}] does not have reference extraced from pdf: {sub.keys()}"
        )
        return

    tag_check = dict()
    for t in tag_fields:
        tag_check[t] = dict()
        if t in sub["tags"]:
            tag_check[t]["declared_by_author"] = True
        else:
            tag_check[t]["declared_by_author"] = False
        tag_check[t]["declared_by_pc_member"] = False
        tag_check[t]["pc_member"] = set()

    all_pc_email_cited = set()
    all_pc_author = set()
    for ref in sub["reference"]:
        if ref["pc_paper"]:
            for p in ref["mag_record"]["PCAuthor"]:
                all_pc_email_cited.add(p["email"])
                all_pc_author.add(p["first"])
                all_pc_author.add(p["last"])

    for pe in all_pc_email_cited:
        precord = pdb.client.find_one({"_id": pe})
        for pt in precord["tags"]:
            if pt in tag_check:
                tag_check[pt]["declared_by_pc_member"] = True
                tag_check[pt]["pc_member"].add(precord["first"])
                tag_check[pt]["pc_member"].add(precord["last"])

    for _, v in tag_check.items():
        v["pc_member"] = list(v["pc_member"])
        v["pc_member"].sort()

    tag_upload = []
    for k, v in tag_check.items():
        v["tag_name"] = k
        tag_upload.append(v)

    logger.info("Upload tags info")
    sdb.client.update_one({"_id": sid}, {"$set": {"tag_check": tag_upload}},upsert=True)


def check_pc_reference_single(sid, sdb, mdb, pdb, force=False):
    logger = logging.getLogger()
    logger.info(f"Checking paper [{sid:>4}]")
    sub = sdb.client.find_one({"_id": sid})
    assert sub is not None
    if "reference" not in sub:
        logger.warning(
            f"Paper [{sid:>4}] does not have reference extraced from pdf: {sub.keys()}"
        )
        return

    total_pc_ref = 0
    for ref in sub["reference"]:
        if "title" not in ref:
            ref["pc_paper"] = False
            continue
        if not force and "pc_paper" in ref:
            logger.info(f"Paper [{sid:>4}] already parsed, skip")
            return
        ref["pc_paper"] = False
        title = norm_title(ref["title"][0])
        match = mdb.client.find_one({"title": title})
        if match:
            ref["pc_paper"] = True
            ref["mag_record"] = match
            total_pc_ref += 1

    logger.info(f"Paper [{sid:>4}] has cited [{total_pc_ref:>3}] PC papers")
    logger.debug(f"PC paper references:")
    for ref in sub["reference"]:
        if "mag_record" in ref:
            logger.debug(f'  - Title : {ref["title"][0]}')
            logger.debug(f'    MAG ID: {ref["mag_record"]["_id"]}')
            logger.debug(f'    MAG Ti: {ref["mag_record"]["title"]}')
            logger.debug(f"    PC    :")
            for pc in ref["mag_record"]["PCAuthor"]:
                logger.debug(f'    - {pc["first"]} {pc["last"]}')
    logger.info("Upload pc paper info")
    sdb.client.update_one({"_id": sid}, {"$set": {"reference": sub["reference"]}},upsert=True)


tag_fields = [
    "Accel-Cloud",
    "Accel-DB_TP",
    "Accel-Graph",
    "Accel-Health",
    "Accel-ML",
    "Accel-Sci",
    "AprxCmp",
    "Embed",
    "FPGA",
    "GPGPU",
    "Integration",
    "InMemCmp",
    "Network",
    "Neuro",
    "Quantum",
    "Reliability",
    "Security",
    "Traditional",
    "VLSI",
    "CacheTLB",
    "DRAM",
    "Disk",
    "NVM",
    "ArchPL",
    "CGO",
    "PLuArch",
    "RealSys",
    "PerfModel",
    "WorkCharac",
    "VM",
    "Virt",
    "ILP",
    "LowPower",
    "Parallelism",
    "CacheSec",
    "MemSec",
]


def norm_title(title):
    t = title
    t = t.lower()
    t = re.sub(r"\W", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


if __name__ == "__main__":
    submission()
