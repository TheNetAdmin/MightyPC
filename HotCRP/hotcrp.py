import click
import csv
import json
import re
import pprint
from fuzzywuzzy import fuzz
import requests
import click
import logging
import contextlib
from pathlib import Path
import os

log_format = logging.Formatter(
    "[%(asctime)s][%(filename)s:%(lineno)4s - %(funcName)10s()] %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
handler = logging.FileHandler("hotcrp.log")
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.DEBUG)


@click.group()
def hotcrp():
    pass


tag_fields = [
    "Academia",
    "Industry",
    "Seniority",
    "Gender",
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


def dict_read_csv(filename, delimiter=","):
    data = []
    with open(filename, "r", encoding="utf-8", newline="\n") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            data.append(row)
    return data


def dict_read_tsv(filename):
    return dict_read_csv(filename, delimiter="\t")


def dict_write_csv(filename, data):
    with open(filename, "w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)


def get_pc_type(hotcrp, email):
    for h in hotcrp:
        if h["email"] == email:
            if "tpc" in h["tags"]:
                return "tpc"
            elif "erc" in h["tags"]:
                return "erc"
            else:
                raise Exception(
                    f'This member is neither a tpc nor an erc: {h["first"]} {h["last"]} <{h["email"]}>'
                )
    raise Exception(f"Member not found from HotCRP with email: {email}")


@hotcrp.command()
@click.argument("tag_file")
@click.argument("hotcrp_file")
@click.option("-o", "--out_file")
@click.option("-t", "--tpc", is_flag=True)
@click.option("-e", "--erc", is_flag=True)
@click.option("-a", "--add", "operation", flag_value="add", default=True)
@click.option("-r", "--remove", "operation", flag_value="remove")
@click.option("-s", "--suffix")
def gen_pc_tags(tag_file, hotcrp_file, out_file, tpc, erc, operation, suffix):
    logger = logging.getLogger()

    logger.info(f"Open tag file {tag_file}")
    data = dict_read_tsv(tag_file)

    logger.info(f"Open hotcrp file {hotcrp_file}")
    hotcrp = dict_read_csv(hotcrp_file)

    choose_pc_type = []
    choose_pc_type += ["tpc"] if tpc else []
    choose_pc_type += ["erc"] if erc else []
    if len(choose_pc_type) == 0:
        raise Exception(
            f"Please choose tpc or erc, or both tpc and erc, not none of them"
        )

    res = []
    tags = set()
    for d in data:
        if d["first"] == d["last"] == d["email"] == "":
            logger.info(f"Skipping empty entry {d}")
            continue

        pc_type = get_pc_type(hotcrp, d["email"])
        if pc_type not in choose_pc_type:
            continue

        r = {"first": d["first"], "last": d["last"], "email": d["email"]}

        if operation == "add":
            r["add_tags"] = " ".join(
                [d[f] + suffix for f in tag_fields if f in d.keys() and d[f]]
            )
        elif operation == "remove":
            r["remove_tags"] = " ".join(
                [d[f] + suffix for f in tag_fields if f in d.keys() and d[f]]
            )
        else:
            raise Exception(f"Wrong operation {operation}")

        for f in tag_fields:
            if f in d.keys():
                tags.add(d[f])
        res.append(r)

    tags = list(tags)
    tags.sort()
    logger.info(f"All tags:")
    logger.info(" ".join(tags))
    for i, t in enumerate(tags):
        logger.info(f"  {i:02}: {t}")

    logger.info(f"Checking missing tag fields")
    for f in tag_fields:
        if f not in tags:
            logger.info(f"- {f}")

    logger.info(f"Operation stats:")
    logger.info(f"  Total records:  {len(res)}")
    logger.info(f"  PC member type: {choose_pc_type}")
    logger.info(f"  Operation:      {operation}")
    logger.info(f"  Output file:    {out_file}")

    if out_file:
        with open(out_file, "w", encoding="utf-8", newline="\n") as f:
            writer = csv.DictWriter(f, fieldnames=res[0].keys())
            writer.writeheader()
            writer.writerows(res)


@hotcrp.command()
@click.argument("tag_file")
@click.option("-o", "--out_file")
def gen_paper_tags(tag_file, out_file):
    data = dict_read_csv(tag_file)
    res = []
    for d in data:
        res.append(
            {"action": "tag", "paper": d["Paper"], "tag": f'#haspdf {d["Tags"]}'}
        )
    if out_file:
        dict_write_csv(out_file, res)


if __name__ == "__main__":
    hotcrp()
