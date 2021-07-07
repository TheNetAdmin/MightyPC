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

from Meeting.zoom import find_all_tpc
from MongoDB.utils import make_mongodb
from Utils.logger import setup_logger
from Utils.utils import chmkdir, chdir


@click.group()
def slides():
    pass


@slides.command()
@click.option("-i", "--submission_id", type=int)
@click.option(
    "-m",
    "--submission_id_file",
    type=click.Path(exists=True),
    help="TSV file specifying all papers to be generated, "
    "in the same format as required by 'MongoDB/import.py:tpc_meeting_discussion_schedule'",
)
@click.option(
    "-s", "--submission_dbcol_name", required=True, default="hotcrp:submission"
)
@click.option("-p", "--pcmember_dbcol_name", required=True, default="hotcrp:pc")
@click.option("-o", "--output_path", required=True, default="slides/output")
@click.option("-t", "--template_path", required=True, default="slides/template")
def gen_beamer_slides(
    submission_id,
    submission_id_file,
    submission_dbcol_name,
    pcmember_dbcol_name,
    output_path,
    template_path,
):
    """
    Generate beamer pdf slides to display conflicts for the current discussion.
    You should run MongoDB/import.py:tpc_meeting_discussion_schedule to import
    discussion schedule before generating slides.
    """
    sdb = make_mongodb(submission_dbcol_name)
    pdb = make_mongodb(pcmember_dbcol_name)
    _all_tpc = find_all_tpc(pdb)
    all_tpc = dict()
    for tpc in _all_tpc:
        all_tpc[tpc["email"]] = tpc

    gen_beamer_template(template_path, output_path)

    if submission_id:
        gen_beamer_slides_single(submission_id, sdb, pdb, all_tpc, output_path)
    else:
        assert submission_id_file
        all_sid = []
        ds = pd.read_csv(submission_id_file, sep="\t", keep_default_na=False)
        for _, d in ds.iterrows():
            papers = d["Paper IDs"]
            all_sid += re.split(r"\s*,\s*", papers)
        all_sid = [int(i) for i in all_sid]
        all_discussion = []

        for sid in all_sid:
            discussion = gen_beamer_slides_single(sid, sdb, pdb, all_tpc, output_path)
            all_discussion.append(discussion)
        # Generate 'content.tex'
        all_discussion.sort(key=lambda x: x["index"])
        all_discussion.sort(key=lambda x: x["session"])
        curr_session = -1
        with open(Path(output_path) / "content.tex", "w") as f:
            for discussion in all_discussion:
                if curr_session != discussion["session"]:
                    curr_session = discussion["session"]
                    f.write("\\section{SESSION " + str(curr_session) + "}\n")
                f.write("\\input{frames/" + str(discussion["sid"]) + ".tex}\n")


def gen_beamer_slides_single(sid, sdb, pdb, all_tpc, output_path):
    logger = logging.getLogger()

    logger.info(f"Generating beamer frame for submission [{sid:>4}]")
    sub = sdb.client.find_one({"_id": sid})

    # Find all tpc conflicts, generate a list of names
    tpc_conflicts = []
    for email, reason in sub["pc_conflicts"].items():
        if email in all_tpc:
            # pc = pdb.client.find_one({"_id": email}, {"name": 1})
            tpc_conflicts.append(all_tpc[email]["name"])
    tpc_conflicts.sort()

    num_tpc_per_line = 3
    padding_size = num_tpc_per_line - (len(tpc_conflicts) % num_tpc_per_line)
    if padding_size != num_tpc_per_line:
        for i in range(padding_size):
            tpc_conflicts.append("")

    session = sub["tpc_discussion"]["session"]
    index = sub["tpc_discussion"]["index"]
    frame_title = f"Session {session}"
    frame_title += f" No. {index}"

    with chdir(output_path):
        with chmkdir("frames"):
            with open(f"{sid}.tex", "w") as f:
                f.write("\\begin{frame}{" + frame_title + "}\n")
                f.write("  \\begin{center}\n")
                f.write("    {\\LARGE\\bfseries Paper \\#" + str(sid) + "}\n")
                f.write("    \n")
                f.write("    \\bigskip\n")
                f.write("    \n")
                if len(tpc_conflicts) == 0:
                    f.write("    No tpc member is in conflict")
                else:
                    f.write(
                        "    The following tpc members are in conflict (sorted by first name)\n"
                    )
                    f.write("    \n")
                    f.write("    \\bigskip\n")
                    f.write("    \n")
                    f.write("    \\begin{footnotesize}\n")
                    f.write(
                        "      \\begin{tabularx}{\\linewidth}{|"
                        + num_tpc_per_line * ("X|")
                        + "} \\hline \n"
                    )
                    for i in range(len(tpc_conflicts)):
                        if i % num_tpc_per_line == 0:
                            f.write("        ")
                        f.write(tpc_conflicts[i])
                        if i % num_tpc_per_line == num_tpc_per_line - 1:
                            f.write(" \\\\ \\hline \n")
                        else:
                            f.write(" & ")
                    f.write("      \\end{tabularx}\n")
                    f.write("    \\end{footnotesize}\n")
                f.write("  \\end{center}\n")
                f.write("\\end{frame}\n")
        with open("content.tex", "w") as f:
            f.write("\\input{frames/" + str(sid) + ".tex}\n")

    return {"sid": sid, "session": session, "index": index}


def gen_beamer_template(template_path, output_path):
    logger = logging.getLogger()

    tp = Path(template_path).resolve()
    op = Path(output_path).resolve()

    logger.info(f"Generating top TeX file in {op}")
    with chmkdir(op):
        with open("slides.tex", "w") as f:
            f.write("\\documentclass{beamer}\n")
            f.write("\\usepackage{tabularx}\n")
            f.write("\\usetheme{focus}\n")
            f.write("\\title{MICRO 2021}\n")
            f.write("\\subtitle{TPC Meeting}\n")
            f.write("\\date{8-9 July 2021}\n")
            f.write("\\begin{document}\n")
            f.write("  \\begin{frame}\n")
            f.write("    \maketitle\n")
            f.write("  \\end{frame}\n")
            f.write("\\input{content.tex}\n")
            f.write("\\end{document}\n")

        with open("content.tex", "w") as f:
            f.write("\n")

    logger.info(f"Copying template .sty files to {op}")
    for f in tp.iterdir():
        if f.suffix == ".sty":
            src_file = f.resolve()
            dst_file = op / f.name
            shutil.copy(src_file, dst_file)


if __name__ == "__main__":
    setup_logger("slides")
    slides()
