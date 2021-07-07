import copy
import csv
import inspect
import logging
import os
import sys
from pathlib import Path

import click
import pandas as pd

# To import a module from parent dir
# https://stackoverflow.com/questions/714063/importing-modules-from-parent-folder
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from MongoDB.utils import make_mongodb
from Utils.logger import setup_logger


@click.group()
def zoom():
    pass


@zoom.command()
@click.option("-i", "--submission_id", type=int)
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
@click.option("-p", "--pcmember_dbcol_name", required=True, default="hotcrp:pc")
@click.option("-o", "--output_path", required=True, default="zoom")
@click.option(
    "-a",
    "--preset_accounts_file",
    type=click.Path(exists=True),
    help="A csv file with two column 'email' and 'preset_room'."
    "It preset one email to be always in a room. "
    "Available rooms are [discussion|conflict]",
)
@click.option("-f", "--force", is_flag=True)
def gen_room(
    submission_id,
    submission_dbcol_name,
    pcmember_dbcol_name,
    output_path,
    preset_accounts_file,
    force,
):
    sdb = make_mongodb(submission_dbcol_name)
    pdb = make_mongodb(pcmember_dbcol_name)
    all_tpc = find_all_tpc(pdb)
    preset = read_preset_accounts(preset_accounts_file)

    if submission_id:
        gen_room_single(submission_id, sdb, all_tpc, pdb, output_path, preset, force)
    else:
        ids = sdb.client.find({"haspdf": True}).distinct("_id")
        for sid in ids:
            gen_room_single(
                sid, sdb, copy.deepcopy(all_tpc), pdb, output_path, preset, force
            )


def read_preset_accounts(preset_accounts_file):
    preset = {"discussion": [], "conflict": []}
    if preset_accounts_file:
        with open(preset_accounts_file, "r") as f:
            reader = csv.DictReader(f)
            for r in reader:
                # Check if one account is already set
                if (
                    r["email"] in preset["discussion"]
                    or r["email"] in preset["conflict"]
                ):
                    raise Exception(
                        f"This email is set multiple times, cannot "
                        f"preset one email to multiple rooms: {r['email']}"
                    )
                preset[r["preset_room"]].append(r["email"])
    return preset


@zoom.command()
@click.option("-e", "--pc_member_email")
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
@click.option("-m", "--mag_dbcol_name", required=True, default="mag:paper")
@click.option("-p", "--pcmember_dbcol_name", required=True, default="hotcrp:pc")
@click.option("-z", "--zoom_email_survey", required=True, type=click.Path(exists=True))
@click.option("-i", "--ignore_member_email", multiple=True)
def import_zoom_email(
    pc_member_email,
    submission_dbcol_name,
    mag_dbcol_name,
    pcmember_dbcol_name,
    zoom_email_survey,
    ignore_member_email,
):
    sdb = make_mongodb(submission_dbcol_name)
    pdb = make_mongodb(pcmember_dbcol_name)
    all_tpc = find_all_tpc(pdb)
    zoom_emails = read_zoom_email(zoom_email_survey, ignore_member_email)

    if pc_member_email:
        import_zoom_email_single(pc_member_email, sdb, all_tpc, pdb, zoom_emails)
    else:
        for p in all_tpc:
            if p["email"] in ignore_member_email:
                continue
            import_zoom_email_single(p["email"], sdb, all_tpc, pdb, zoom_emails)


def read_zoom_email(zoom_email_survey_file, ignore_member_email) -> dict:
    """Read zoom email survey as tab-separated tsv file,
    return a dict mapts hotcrp email to corresponding zoom email"""

    logger = logging.getLogger()
    zoom_emails_origin = pd.read_csv(
        zoom_email_survey_file, sep="\t", keep_default_na=False
    )
    zoom_emails = dict()

    # Column names
    zoom_col = "Zoom email (if different from HotCRP account)"
    hotcrp_col = "HotCRP email"
    zoom_same_col = "Same email for Zoom (Y/N)?"

    member_no_response = []
    for _, ze in zoom_emails_origin.iterrows():
        # Check response values
        hemail = ze[hotcrp_col].strip()
        zemail = ze[zoom_col].strip()
        hzsame = ze[zoom_same_col].strip()

        if hemail in ignore_member_email:
            logger.warning(
                f"Ignorring member {hemail} as specified through cli argument"
            )
            continue

        if hzsame in ["N", "n"]:
            if zemail == "":
                raise Exception(
                    f"This member declared zoom email different from hotcrp email, "
                    f"but does not provide a zoom email: {hemail}"
                )
        elif hzsame in ["Y", "y"]:
            if zemail != "" and zemail != hemail:
                raise Exception(
                    f"This member declared zoom email same as hotcrp email, "
                    f"but provides a different zoom email: {hemail} - {zemail}"
                )
            zemail = hemail  # Set zoom email the same as hotcrp email
        elif hzsame == "":
            member_no_response.append(ze)
        else:
            raise Exception(f"This member respond with unknown option: {hzsame}")
        # Check finished, add to return data
        zoom_emails[hemail] = zemail

    # Print non-responded members
    logger.warning(
        f"The following {len(member_no_response)} members has not responded yet:"
    )
    for m in member_no_response:
        logger.warning(f"  {m[hotcrp_col]}")

    return zoom_emails


def find_all_tpc(pdb):
    tpc = []
    # Find all pc member with 'tpc' tag
    tpc += pdb.client.find({"tags": "tpc"}, {"name": 1, "email": 1, "zoom_email": 1})
    # Chair may not have 'tpc' tag, search instead for 'chair' role
    tpc += pdb.client.find(
        {"roles": {"$regex": r".*chair.*"}}, {"name": 1, "email": 1, "zoom_email": 1}
    )
    # Remove redundent results, e.g. Chair has 'tpc' tag and 'chair' role
    tpc_unique = []
    tpc_emails = set()
    for t in tpc:
        if t["email"] not in tpc_emails:
            tpc_emails.add(t["email"])
            tpc_unique.append(t)

    return tpc_unique


def import_zoom_email_single(pemail, sdb, all_tpc, pdb, zoom_emails):
    logger = logging.getLogger()
    no_record = []
    if pemail in zoom_emails:
        zemail = zoom_emails[pemail]
        logger.info(f"Import zoom email for pc member: {pemail} -> {zemail}")
        pdb.client.update_one({"_id": pemail}, {"$set": {"zoom_email": zemail}})
    else:
        no_record.append(pemail)

    for nr in no_record:
        logger.error(f"This member does not have zoom email specified: {nr}")


def gen_room_single(sid, sdb, all_tpc, pdb, output_path, preset_rooms, force=False):
    logger = logging.getLogger()
    logger.info(f"Generating zoom room config for paper [{sid:>4}]")
    output_file = Path(output_path) / f"{sid}.csv"
    if output_file.exists():
        if not force:
            logger.info(f"    Already generated, skipping")

    sub = sdb.client.find_one({"_id": sid})
    assert sub is not None
    sub_conflict = sub["pc_conflicts"]

    room = []
    room_names = {"conflict": "Conflict Room", "discussion": f"Discussion Room {sid}"}
    for tpc in all_tpc:
        if tpc["email"] in sub_conflict:
            name = room_names["conflict"]
        else:
            name = room_names["discussion"]
        # Get zoom email
        if "zoom_email" in tpc and tpc["zoom_email"].strip() != "":
            zemail = tpc["zoom_email"]
        else:
            zemail = tpc["email"]
            logger.warning(f"This member does not declare a Zoom email: {tpc['email']}")
        room.append({"Pre-assign Room Name": name, "Email Address": zemail})
    room.sort(key=lambda x: x["Email Address"])
    room.sort(key=lambda x: x["Pre-assign Room Name"])
    # Add preset accounts
    for room_type in ["discussion", "conflict"]:
        for pemail in preset_rooms[room_type]:
            room.insert(
                0,
                {
                    "Pre-assign Room Name": room_names[room_type],
                    "Email Address": pemail,
                },
            )

    with open(output_file, "w") as f:
        writer = csv.DictWriter(f, fieldnames=room[0].keys())
        writer.writeheader()
        writer.writerows(room)


if __name__ == "__main__":
    setup_logger("zoom")
    zoom()
