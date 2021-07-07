import json
import logging
import re
import time

import bibtexparser
import click
import requests
from prettytable import PrettyTable

log_format = logging.Formatter(
    "[%(asctime)s][%(filename)s:%(lineno)4s - %(funcName)10s()] %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
handler = logging.FileHandler("dblp.log")
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)


@click.group()
def dblp():
    pass


@dblp.command()
@click.option("-t", "--tpc_file", required=True)
@click.option("-e", "--erc_file", required=True)
@click.option("-o", "--out_file")
def parse_and_check(tpc_file, erc_file, out_file):
    logger = logging.getLogger()
    pc = []
    logger.info(f"Reading erc file {erc_file}")
    with open(erc_file, "r") as f:
        pc += json.load(f)
    logger.info(f"Reading tpc file {tpc_file}")
    with open(tpc_file, "r") as f:
        pc += json.load(f)

    table = PrettyTable()
    table.field_names = ["Name", "DBLP Link"]
    table.align = "l"
    for p in pc:
        dblp_url = parse_dblp_url(p["dblp"])
        p["dblp_origin"] = p["dblp"]
        p["dblp"] = dblp_url
        table.add_row([p["name"], parse_dblp_url(p["dblp"])])
    logger.info("\n" + table.get_string(title="All PC Members"))

    if out_file:
        logger.info(f"Output to {out_file}")
        with open(out_file, "w") as f:
            json.dump(pc, f, ensure_ascii=False, indent=4)


def download_single_pc_publication(pc_record):
    url = f'{pc_record["dblp"]}.bib'
    responses = requests.get(url)
    bib = bibtexparser.loads(responses.content)
    return bib.entries


def summarize_pc_member(members):
    table = PrettyTable()
    table.field_names = ["name", "google scholar"]
    table.align = "l"
    for m in members:
        table.add_row([m["name"], m["google_scholar"]])
    return table


@dblp.command()
@click.option("-p", "--pc_file", required=True)
@click.option("-n", "--pc_name")
@click.option("-o", "--out_file", required=True)
@click.option("-n", "--need_fix_file", default="pc_need_publication.json")
@click.option("-m", "--manual_fix_file")
def download_publication(pc_file, pc_name, out_file, need_fix_file, manual_fix_file):
    logger = logging.getLogger()
    with open(pc_file, "r") as f:
        pc = json.load(f)

    pc_fixed = None
    if manual_fix_file:
        with open(manual_fix_file, "r") as f:
            pc_fixed = json.load(f)

    modified = False
    pc_no_dblp = []
    pc_empty_publication = []
    try:
        for i, p in enumerate(pc):
            if pc_name and p["name"] != pc_name:
                continue
            logger.info(f'Parsing publication for PC [{i:>3}]: [{p["name"]:30}]')
            if "publication" not in p.keys() and pc_fixed:
                for pf in pc_fixed:
                    if pf["name"] == p["name"]:
                        p["publication"] = pf["publication"]
                        logger.info(
                            f'    Got [{len(p["publication"]):>3}] publications from manual fixed file'
                        )
                        modified = True

            if "publication" in p.keys():
                logger.info(
                    f'    Already have [{len(p["publication"]):>3}] publications, skip'
                )
                continue

            if "pid" not in p["dblp"]:
                logger.info(f"    Does not have dblp link, skip")
                pc_no_dblp.append(p)
                continue

            p["publication"] = download_single_pc_publication(p)
            if "publication" not in p.keys() or len(p["publication"]) == 0:
                pc_empty_publication.append(p)
            logger.info(f'    Got [{len(p["publication"]):>3}] publications')
            modified = True
            time.sleep(1)

        if len(pc_no_dblp) > 0:
            logger.info(
                f"The following pc members do not have dblp links, "
                f"please manually fill at least one publication record for each of them:\n"
                + summarize_pc_member(pc_no_dblp).get_string()
            )
            with open(need_fix_file, "w") as f:
                json.dump(pc_no_dblp, f, ensure_ascii=False, indent=4)
        if len(pc_empty_publication) > 0:
            logger.info(
                f"The following pc members do not have publications, "
                f"please manually fill at least one publication record for each of them:\n"
                + summarize_pc_member(pc_empty_publication).get_string()
            )
    finally:
        if out_file and modified:
            with open(out_file, "w") as f:
                json.dump(pc, f, ensure_ascii=False, indent=4)


def parse_dblp_url(origin_url):
    res_url = ""
    if "dblp" not in origin_url:
        return res_url
    if "pid" not in origin_url:
        return res_url
    res_url = origin_url
    res_url = re.sub(r"\.html.*", "", res_url)
    return res_url


if __name__ == "__main__":
    dblp()
