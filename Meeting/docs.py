import copy
import csv
import re
import inspect
import logging
import os
import sys
from pathlib import Path
import shutil

import click
import pandas as pd

# To import a module from parent dir
# https://stackoverflow.com/questions/714063/importing-modules-from-parent-folder
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from MongoDB.utils import make_mongodb
from Utils.logger import setup_logger
from Utils.utils import chmkdir, chdir


@click.group()
def docs():
    pass


@docs.command()
@click.option("-i", "--submission_id", type=int)
@click.option(
    "-m",
    "--submission_id_file",
    type=click.Path(exists=True),
    help="TSV file specifying all papers to be generated, "
    "in the same format as required by "
    "'MongoDB/import.py:tpc_meeting_discussion_schedule()'",
)
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
@click.option("-p", "--pcmember_dbcol_name", required=True, default="hotcrp:pc")
@click.option("-o", "--output_path", required=True, default="member_check")
def gen_member_check_docs(
    submission_id,
    submission_id_file,
    submission_dbcol_name,
    pcmember_dbcol_name,
    output_path,
):
    """
    Generate member (all pc, including tpc and erc and chair) check .csv file
    for each paper to be discussed. This .csv contains three columns:
    1. name:  pc member full name;
    2. email: pc member hotcrp email;
    3. role:  'conflict' or 'review_tpc' or 'reviewer_erc' or 'other'.
    """
    sdb = make_mongodb(submission_dbcol_name)
    pdb = make_mongodb(pcmember_dbcol_name)
    all_pc = pdb.client.find(
        {"roles": {"$regex": r".*pc.*"}}, {"name": 1, "email": 1, "tags": 1}
    )

    if submission_id:
        gen_member_check_docs_single(submission_id, sdb, pdb, all_pc, output_path)
    else:
        assert submission_id_file
        all_sid = []
        ds = pd.read_csv(submission_id_file, sep="\t", keep_default_na=False)
        for _, d in ds.iterrows():
            papers = d["Paper IDs"]
            all_sid += re.split(r"\s*,\s*", papers)
        all_sid = [int(i) for i in all_sid]

        for sid in all_sid:
            gen_member_check_docs_single(
                sid, sdb, pdb, copy.deepcopy(all_pc), output_path
            )


def gen_member_check_docs_single(sid, sdb, pdb, all_pc, output_path):
    logger = logging.getLogger()

    logger.info(f"Generating member checking docs for submission [{sid:>4}]")
    sub = sdb.client.find_one({"_id": sid})

    member_check = []
    for pc in all_pc:
        if pc["email"] in sub["pc_conflicts"]:
            role = "conflict"
        elif pc["email"] in sub["review_assignment"]:
            if "tpc" in pc["tags"]:
                role = "reviewer_tpc"
            elif "erc" in pc["tags"]:
                role = "reviewer_erc"
            else:
                raise Exception(
                    f"Reviewer [{pc['name']}] for paper [{sid:>4}] is neither tpc nor erc (i.e. no 'tpc' or 'erc' tag)"
                )
        else:
            role = "other"
        member_check.append({"role": role, "name": pc["name"]})
    member_check.sort(key=lambda x: x["name"])
    member_check.sort(
        key=lambda x: ["conflict", "reviewer_tpc", "reviewer_erc", "other"].index(
            x["role"]
        )
    )

    with chmkdir(output_path):
        with open(f"{sid}.csv", "w") as f:
            writer = csv.DictWriter(f, fieldnames=member_check[0].keys())
            writer.writeheader()
            writer.writerows(member_check)


if __name__ == "__main__":
    setup_logger("docs")
    docs()
