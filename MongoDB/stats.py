import contextlib
import csv
import json
import logging
import os
import re
from pathlib import Path
from collections import Counter

import click

from utils import make_mongodb

log_format = logging.Formatter(
    "[%(asctime)s][%(filename)s:%(lineno)4s - %(funcName)10s()][%(levelname)s] %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
handler = logging.FileHandler("stats.log")
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.DEBUG)


@click.group()
def stats():
    pass


def review_email_mapping(review_email) -> str:
    mapping = {
        "pcmember_new_email@example.com": "pcmember_previous_email@example.com"
    }
    if review_email in mapping:
        return mapping[review_email]
    else:
        return review_email


@stats.command()
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
@click.option("-p", "--pcmember_dbcol_name", required=True, default="hotcrp:pc")
def reviews_per_pc(submission_dbcol_name, pcmember_dbcol_name):
    logger = logging.getLogger()
    sdb = make_mongodb(submission_dbcol_name)
    pdb = make_mongodb(pcmember_dbcol_name)

    logger.info("Getting all pc member info")
    pcs = dict()
    all_pc = pdb.client.find()
    for pc in all_pc:
        pid = pc["email"]
        pcs[pid] = {"tags": pc["tags"], "total_reviews": 0}
    logger.info(f"[{len(pcs)}] total pc members found")

    logger.info("Getting all submissions")
    all_sub = sdb.client.find()
    for sub in all_sub:
        logger.info(f"  [{sub['_id']:>4}]")
        if "review_assignment" in sub:
            for review in sub["review_assignment"]:
                pcs[review_email_mapping(review)]["total_reviews"] += 1
        else:
            logger.warning(f"[{sub['_id']:>4}] does not have reviewers assigned")

    logger.info("Review per PC member")
    tpc = {"count": 0, "reviews": 0}
    erc = {"count": 0, "reviews": 0}
    logger.debug(f'{pcs["xiaowei@ece.ubc.ca"]}')
    for email, pc in pcs.items():
        if "tpc" in pc["tags"]:
            tpc["count"] += 1
            tpc["reviews"] += pc["total_reviews"]
        elif "erc" in pc["tags"]:
            erc["count"] += 1
            erc["reviews"] += pc["total_reviews"]
        else:
            logger.warning(f"PC member is neither TPC nor ERC: [{email:>20}]")
    logger.info(f"TPC:")
    logger.info(f"    - Count:       {tpc['count']}")
    logger.info(f"    - Reviews:     {tpc['reviews']}")
    logger.info(f"    - Avg Reviews: {tpc['reviews'] / tpc['count']}")
    logger.info(f"ERC:")
    logger.info(f"    - Count:       {erc['count']}")
    logger.info(f"    - Reviews:     {erc['reviews']}")
    logger.info(f"    - Avg Reviews: {erc['reviews'] / erc['count']}")


@stats.command()
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
def topics(submission_dbcol_name):
    logger = logging.getLogger()
    sdb = make_mongodb(submission_dbcol_name)
    topics = dict()
    logger.info("Getting all topics")
    for sub in sdb.client.find():
        if "decision" not in sub:
            logger.warning(f"Submission [{sub['_id']:>4}] has no decision, skipping")
            continue
        if "topics" in sub:
            for t in sub["topics"]:
                if t not in topics:
                    topics[t] = {"Accepted": 0, "Rejected": 0}
                topics[t][sub["decision"]] += 1
    logger.info(f"Summary:")
    logger.info(f"    Total topics: {len(topics)}")
    logger.info(f"topic,accepted,rejected")
    all_topics = [(n, t) for n, t in topics.items()]
    all_topics.sort()
    for n, t in all_topics:
        n = n.replace(",", "")
        print(f"{n}\t{t['Accepted']}\t{t['Rejected']}")


@stats.command()
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
def authors_per_paper(submission_dbcol_name):
    logger = logging.getLogger()
    sdb = make_mongodb(submission_dbcol_name)

    total_paper = 0
    total_author = 0
    authors = dict()
    logger.info("Getting authors for each paper")
    for sub in sdb.client.find():
        if "decision" not in sub:
            logger.warning(f"Submission [{sub['_id']:>4}] has no decision, skipping")
            continue
        pid = sub["_id"]
        author = len(sub["authors"])
        print(f"{pid}, {author}")
        total_paper += 1
        total_author += author
        if author not in authors:
            authors[author] = {"Accepted": 0, "Rejected": 0}
        authors[author][sub["decision"]] += 1
    logger.info(
        f"Avg authors per paper: {total_author} / {total_paper} = {total_author / total_paper}"
    )
    logger.info(f"#Authors per Paper, Accepted, Rejected")
    for n, a in authors.items():
        print(f'{n}\t{a["Accepted"]}\t{a["Rejected"]}')


@stats.command()
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
def papers_per_author(submission_dbcol_name):
    logger = logging.getLogger()
    sdb = make_mongodb(submission_dbcol_name)

    papers = dict()
    logger.info("Parsing all papers")
    for sub in sdb.client.find():
        logger.info(f"Parsing [{sub['_id']:>4}]")
        if "decision" not in sub:
            logger.warning(f"Submission [{sub['_id']:>4}] has no decision, skipping")
            continue
        for author in sub["authors"]:
            if "first" not in author:
                logger.warning(f"Author does not have name: {author}, skipping")
                continue
            aname = author["first"] + " " + author["last"]
            if aname not in papers:
                papers[aname] = {"Accepted": 0, "Rejected": 0}
            papers[aname][sub["decision"]] += 1

    summary = dict()
    for aname, paper in papers.items():
        total = paper["Accepted"] + paper["Rejected"]
        if total not in summary:
            summary[total] = {"Accepted": 0, "Rejected": 0, "Occurance": 0}
        summary[total]["Occurance"] += 1
        for decision in ["Accepted", "Rejected"]:
            summary[total][decision] += paper[decision]
    logger.info("Summary: #papers per author,#Accepted,#Rejected,Occurance")
    for n, s in summary.items():
        print(f'{n}\t{s["Accepted"]}\t{s["Rejected"]}\t{s["Occurance"]}')
    logger.info(f"Total distince authors: {len(papers)}")


@stats.command()
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
def submission_type(submission_dbcol_name):
    logger = logging.getLogger()
    sdb = make_mongodb(submission_dbcol_name)

    total = {"First submission": 0, "Resubmission": 0}
    accepted = {"First submission": 0, "Resubmission": 0}

    for sub in sdb.client.find():
        if "decision" not in sub:
            continue
        if "revisionlettersharingoptions" in sub:
            if sub["revisionlettersharingoptions"] == "First submission":
                isResubmission = False
            else:
                isResubmission = True
                if "resubmission" not in sub:
                    logger.warning(
                        f"Guessing paper [{sub['_id']:>4}] is a resubmission"
                    )
        else:
            if "resubmission" in sub:
                isResubmission = True
            else:
                isResubmission = False

        if isResubmission:
            total["Resubmission"] += 1
            if sub["decision"] == "Accepted":
                accepted["Resubmission"] += 1
        else:
            total["First submission"] += 1
            if sub["decision"] == "Accepted":
                accepted["First submission"] += 1

    logger.info(f"Total: {total}")
    logger.info(f"Accepted: {accepted}")


@stats.command()
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
@click.option("-p", "--pcmember_dbcol_name", required=True, default="hotcrp:pc")
def pc_type_per_paper(submission_dbcol_name, pcmember_dbcol_name):
    logger = logging.getLogger()
    sdb = make_mongodb(submission_dbcol_name)
    pdb = make_mongodb(pcmember_dbcol_name)

    paper_tpc = Counter()
    paper_erc = Counter()

    all_pcs_raw = pdb.client.find()
    all_pcs = dict()
    for pc in all_pcs_raw:
        all_pcs[pc["_id"]] = pc

    for sub in sdb.client.find():
        logger.info(f"Parsing [{sub['_id']:>4}]")
        if "decision" not in sub:
            logger.warning(f"Submission [{sub['_id']:>4}] has no decision, skipping")
            continue
        curr_tpc = 0
        curr_erc = 0
        for reviewer in sub["review_assignment"]:
            remail = review_email_mapping(reviewer)
            if "tpc" in all_pcs[remail]["tags"]:
                curr_tpc += 1
            elif "erc" in all_pcs[remail]["tags"]:
                curr_erc += 1
            else:
                raise Exception(f"Reviewer [{remail}] is neigher TPC nor ERC")
        paper_tpc[curr_tpc] += 1
        paper_erc[curr_erc] += 1

    logger.info("TPC summary:")
    print(paper_tpc)
    logger.info("ERC summary")
    print(paper_erc)

if __name__ == "__main__":
    stats()
