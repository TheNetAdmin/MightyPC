import contextlib
import csv
import json
import logging
import os
import re
from pathlib import Path
from xmlrpc.client import Boolean, boolean

import click
import pandas as pd
from utils import make_mongodb, mongodb

def norm_title(title):
    t = title
    t = t.lower()
    t = re.sub(r"\W", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t

log_format = logging.Formatter(
    "[%(asctime)s][%(filename)s:%(lineno)4s - %(funcName)10s()] %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
handler = logging.FileHandler("import.log")
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.DEBUG)


@click.group()
def dbimport():
    pass


@dbimport.command()
@click.option("-f", "--dblp_file", required=True)
@click.option("-a", "--author_dbcol_name", default="hotcrp:pc")
@click.option("-p", "--paper_dbcol_name", default="dblp:paper")
@click.option("-n", "--number_of_authors", type=int, default=1)
@click.option("--all_members", is_flag=True)
def dblp(
    dblp_file, author_dbcol_name, paper_dbcol_name, number_of_authors, all_members
):
    logger = logging.getLogger()
    with open(dblp_file, "r") as f:
        data = json.load(f)
        if not all_members:
            data = data[:number_of_authors]

    db, col = author_dbcol_name.split(":")
    adb = mongodb(db, col)
    db, col = paper_dbcol_name.split(":")
    pdb = mongodb(db, col)

    for d in data:
        logger.info(f'Importing author [{d["name"]:30}]')
        # Update author
        author = {
            "_id": d["email"],
            "name": d["name"],
            "email": d["email"],
            "dblp": d["dblp"],
            "google_scholar": d["google_scholar"],
        }
        adb.client.update_one(
            {"_id": author["_id"]},
            {
                "$setOnInsert": author,
                "$set": {
                    "dblp_publication": [p["ID"] for p in d["publication"] if "ID" in p]
                },
            },
            upsert=True,
        )
        # Update publications
        pubs = [p for p in d["publication"] if "ID" in p]
        for p in pubs:
            p["_id"] = p.pop("ID")
            if "editor" in p and "author" not in p:
                p["author"] = p["editor"]
            author_list = p["author"].split("\n")
            p["author"] = []
            for a in author_list:
                a = re.sub(r"\s*and\s*", "", a)
                a = re.sub(r"\s+", " ", a)
                p["author"].append(a)
            p["title"] = norm_title(p.pop("title"))
            pa = {"name": author["name"], "email": author["email"]}
            pdb.client.update_one(
                {"_id": p["_id"]},
                {"$set": p, "$addToSet": {"PCAuthor": pa}},
                upsert=True,
            )


@dbimport.command()
@click.option("-m", "--mag_author_file", required=True)
@click.option("-d", "--mag_paper_dir", required=True)
@click.option("-a", "--author_dbcol_name", default="hotcrp:pc")
@click.option("-p", "--paper_dbcol_name", default="mag:paper")
@click.option("-n", "--number_of_authors", type=int, default=1)
@click.option("--all_members", is_flag=True)
def mag(
    mag_author_file,
    mag_paper_dir,
    author_dbcol_name,
    paper_dbcol_name,
    number_of_authors,
    all_members,
):
    logger = logging.getLogger()
    with open(mag_author_file, "r") as f:
        mag_author = json.load(f)
        mag_author = [v for _, v in mag_author.items()]
        if not all_members:
            mag_author = mag_author[:number_of_authors]

    db, col = author_dbcol_name.split(":")
    adb = mongodb(db, col)
    db, col = paper_dbcol_name.split(":")
    pdb = mongodb(db, col)

    for ma in mag_author:
        logger.info(f'Importing author [{ma["name"]:30}]')
        # Open publication record file
        with open(Path(mag_paper_dir) / f'{ma["name"]}.json', "r") as f:
            mp = json.load(f)
        # Update author
        author = {
            "_id": ma["email"],
            "name": ma["name"],
            "email": ma["email"],
            "dblp": ma["dblp"],
            "google_scholar": ma["google_scholar"],
        }
        adb.client.update_one(
            {"_id": author["_id"]},
            {
                "$setOnInsert": author,
                "$set": {
                    "mag_publication": [p["Id"] for p in mp],
                    "mag_auid": ma["mag_id"],
                },
            },
            upsert=True,
        )
        # Update paper
        for pub in mp:
            pub["_id"] = pub.pop("Id")
            pcauthor = {"name": ma["name"], "email": ma["email"]}
            pdb.client.update_one(
                {"_id": pub["_id"]},
                {"$setOnInsert": pub, "$addToSet": {"PCAuthor": pcauthor}},
                upsert=True,
            )


@dbimport.command()
@click.option(
    "-d",
    "--submission_path",
    required=True,
    help="Path to all papers and infos, generated by script 'Paper/paper.py'",
)
@click.option("-s", "--submission_dbcol_name", default="hotcrp:submission")
@click.option("-f", "--field_to_update")
def submission(submission_path, submission_dbcol_name, field_to_update):
    logger = logging.getLogger()
    db, col = submission_dbcol_name.split(":")
    sdb = mongodb(db, col)

    with chdir(submission_path):
        for file in Path(".").iterdir():
            if not file.is_dir():
                continue
            logger.info(f"Importing paper [{file.name:>4}]")
            with open(file / f"paper{file.name}.json", "r") as f:
                pdata = json.load(f)
            pdata["_id"] = pdata.pop("pid")
            sdb.client.update_one(
                {"_id": pdata["_id"]}, {"$setOnInsert": pdata}, upsert=True
            )
            if field_to_update:
                sdb.client.update_one(
                    {"_id": pdata["_id"]},
                    {"$set": {field_to_update: pdata[field_to_update]}},
                )


@dbimport.command()
@click.option(
    "-i",
    "--submission_info_file",
    required=True,
    help="JSON file of submission info, downloaded from HotCRP.",
)
@click.option("-s", "--submission_dbcol_name", default="hotcrp:submission")
@click.option("-f", "--field_to_update", required=True)
def submission_info(submission_info_file, submission_dbcol_name, field_to_update):
    logger = logging.getLogger()
    sdb = make_mongodb(submission_dbcol_name)

    with open(submission_info_file, "r") as f:
        sub_info = json.load(f)

    for sub in sub_info:
        if field_to_update not in sub:
            raise Exception(f"Field {field_to_update} not found in record {sub}")
        logger.info(f'Updating paper [{sub["pid"]:>4}], field {field_to_update}')
        sdb.client.update_one(
            {"_id": int(sub["pid"])}, {"$set": {field_to_update: sub[field_to_update]}}, upsert=True 
        )


@dbimport.command()
@click.option("-t", "--submission_tag_file", required=True)
@click.option("-s", "--submission_dbcol_name", default="hotcrp:submission")
def submission_tag(submission_tag_file, submission_dbcol_name):
    logger = logging.getLogger()
    db, col = submission_dbcol_name.split(":")
    sdb = mongodb(db, col)

    with open(submission_tag_file, "r") as f:
        reader = csv.DictReader(f)
        tags = []
        for r in reader:
            tags.append(r)
    for t in tags:
        pid = t["paper"]
        ptags = t["topic"]
        ptags = ptags.replace("#", " ")
        ptags = re.sub(r"\s+", " ", ptags)
        ptags = ptags.split(" ")
        ptags = [t for t in ptags if t != ""]
        logger.info(f"Updating tags for paper [{pid:>4}]: {ptags}")
        sdb.client.update_one({"_id": int(pid)}, {"$set": {"tags": ptags}})


@dbimport.command()
@click.option("-t", "--submission_file", required=True)
@click.option("-s", "--submission_dbcol_name", default="hotcrp:submission")
def submission_mark_haspdf(submission_file, submission_dbcol_name):
    logger = logging.getLogger()
    db, col = submission_dbcol_name.split(":")
    sdb = mongodb(db, col)

    with open(submission_file, "r", encoding="utf-8") as f:
        subs = json.load(f)
    total = 0
    for s in subs:
        pid = s["pid"]
        logger.info(f"Updating paper [{pid:>4}]")
        sdb.client.update_one({"_id": int(pid)}, {"$set": {"haspdf": True}})
        total += 1
    logger.info(f"Total updated: {total}")


@dbimport.command()
@click.option("-f", "--pcmember_file", required=True)
@click.option("-p", "--pcmember_dbcol_name", default="hotcrp:pc")
def pc_member(pcmember_file, pcmember_dbcol_name):
    logger = logging.getLogger()
    db, col = pcmember_dbcol_name.split(":")
    sdb = mongodb(db, col)

    with open(pcmember_file, "r") as f:
        reader = csv.DictReader(f)
        members = []
        for r in reader:
            members.append(r)

    for member in members:
        name = f'{member["first"]} {member["last"]}'
        logger.info(f"Updating member [{name:30}]")
        tags = member.pop("tags")
        tags = re.sub(r"\s+", " ", tags)
        member["tags"] = tags.split(" ")
        sdb.client.update_one({"_id": member["email"]}, {"$set": member}, upsert=True)


@dbimport.command()
@click.option("-f", "--review_preference_file", required=True)
@click.option(
    "-p", "--review_preference_dbcol_name", default="hotcrp:review_preference"
)
def review_preference(review_preference_file, review_preference_dbcol_name):
    logger = logging.getLogger()
    db, col = review_preference_dbcol_name.split(":")
    sdb = mongodb(db, col)

    with open(review_preference_file, "r") as f:
        reader = csv.DictReader(f)
        prefs = []
        for r in reader:
            prefs.append(r)

    logger.info("Import all review prefrence records")
    sdb.client.insert_many(prefs)
    logger.info("Done importing all review prefrence records")


@dbimport.command()
@click.option(
    "-f",
    "--review_assignment_file",
    required=True,
    help="CSV file of review assignment, downloaded from HotCRP.",
)
@click.option("-s", "--submission_dbcol_name", default="hotcrp:submission")
def review_assignment(review_assignment_file, submission_dbcol_name):
    logger = logging.getLogger()
    sdb = make_mongodb(submission_dbcol_name)

    with open(review_assignment_file, "r") as f:
        assignment = dict()
        reader = csv.DictReader(f)
        for r in reader:
            if r["action"] != "clearreview":
                pid = r["paper"]
                if pid not in assignment:
                    assignment[pid] = []
                assignment[pid].append(r["email"])

    for pid, asm in assignment.items():
        pid = int(pid)
        logger.info(f"Updating paper review assignment for paper [{pid:>4}]")
        sdb.client.update_one({"_id": int(pid)}, {"$set": {"review_assignment": asm}})


@dbimport.command()
@click.option("-f", "--submission_assignment", required=True)
@click.option("-s", "--submission_dbcol_name", default="hotcrp:submission")
def ms_suggested_assignment(submission_assignment, submission_dbcol_name):
    """
    To import the ML suggested assignment, provided by UIUC's ML-based
    review assignment tools.
    """
    logger = logging.getLogger()
    db, col = submission_dbcol_name.split(":")
    sdb = mongodb(db, col)

    assignment = dict()
    with open(submission_assignment, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            submission_id = r["sid"]
            if submission_id not in assignment:
                assignment[submission_id] = list()
            assignment[submission_id].append(r["name"])

    for sid, review_list in assignment.items():
        logger.info(f"Importing review assignment list for [{sid:>4}]")
        sdb.client.update_one(
            {"_id": int(sid)},
            {"$set": {"ml_suggested_reviewers": review_list}},
            upsert=True,
        )


@dbimport.command()
@click.option(
    "-f",
    "--discussion_schedule_file",
    required=True,
    help="TSV with two columns: Session and Paper IDs. Paper IDs is ids separated by comma.",
)
@click.option("-s", "--submission_dbcol_name", default="hotcrp:submission")
def tpc_meeting_discussion_schedule(discussion_schedule_file, submission_dbcol_name):
    logger = logging.getLogger()
    sdb = make_mongodb(submission_dbcol_name)

    ds = pd.read_csv(discussion_schedule_file, sep="\t", keep_default_na=False)

    for _, d in ds.iterrows():
        session = int(d["Session"])
        papers = d["Paper IDs"]
        papers = re.split(r"\s*,\s*", papers)
        for i in range(len(papers)):
            paper = int(papers[i])
            index = i + 1
            logger.info(f"Updating paper discussion schedule for paper [{paper:>4}]")
            sdb.client.update_one(
                {"_id": paper},
                {"$set": {"tpc_discussion": {"session": session, "index": index}}},
            )


@contextlib.contextmanager
def chdir(path):
    """Go to working directory and return to previous on exit."""
    prev_cwd = Path.cwd()
    os.chdir(Path(path))
    try:
        yield
    finally:
        os.chdir(prev_cwd)


@dbimport.command()
def test():
    mongo = mongodb("test", "data")


if __name__ == "__main__":
    dbimport()
