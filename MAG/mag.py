import contextlib
import csv
import json
import logging
import os
import pprint
import re
import time
from pathlib import Path

import click
import requests
from fuzzywuzzy import fuzz

log_format = logging.Formatter(
    "[%(asctime)s][%(filename)s:%(lineno)4s - %(funcName)10s()] %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
handler = logging.FileHandler("mag.log")
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.DEBUG)


class mag_client:
    def __init__(self):
        # Replace with your own Microsoft Academic Graph API subscription key
        self.sub_key = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
        self.paper_attrs = [
            "Ti",
            "Y",
            "D",
            "DN",
            "F.FN",
            "F.DFN",
            "F.FId",
            "CC",
            "AA.AuN",
            "AA.DAuN",
            "AA.AuId",
            "Id",
            "AA.AfId",
            "AA.AfN",
            "AA.DAfN",
        ]
        self.logger = logging.getLogger("mag_client")
        pass

    def evaluate(self, args):
        url = f"https://api.labs.cognitive.microsoft.com/academic/v1.0/evaluate?subscription-key={self.sub_key}&{args}"
        response = requests.get(url=url).json()
        time.sleep(1)
        return response

    def get_author_id(self, author_name, pub_title):
        # Normalize title
        pub_title = pub_title.lower()
        pub_title = re.sub(r"\W", " ", pub_title)
        pub_title = re.sub(r" +", " ", pub_title)
        # Get record
        record = self.evaluate(
            f"expr=Ti='{pub_title}'&complete=1&count=10&attributes={','.join(self.paper_attrs)}"
        )
        if len(record["entities"]) == 0:
            self.logger.debug(f"Got empty pub info for {pub_title}:\n{record}")
            return False, None, None
        # Get author id
        auid = None
        daun = None
        ratio = -float("inf")
        for author in record["entities"][0]["AA"]:
            curr_ratio = fuzz.ratio(author_name.lower(), author["DAuN"].lower())
            if curr_ratio > ratio:
                ratio = curr_ratio
                auid = author["AuId"]
                daun = author["DAuN"]
        return True, auid, daun

    def get_author_pubs(self, author_id, count=10):
        pubs = self.evaluate(
            f"expr=Composite(AA.AuId={author_id})&complete=1&count={count}&attributes={','.join(self.paper_attrs)}"
        )
        return pubs


@click.group()
def mag():
    pass


@mag.command()
@click.argument("in_file")
@click.argument("out_file")
@click.option("-n", "--number_of_authors", type=int, default=1)
@click.option("-a", "--all_authors", is_flag=True, help="Set this flag to get all authors' info, or use '-n' to specify how many authors to crawl and parse")
@click.option("-m", "--max_try", type=int, default=3)
def parse_author(in_file, out_file, number_of_authors, all_authors, max_try):
    logger = logging.getLogger()
    client = mag_client()
    with open(in_file, "r") as f:
        authors = json.load(f)
        if not all_authors:
            authors = authors[:number_of_authors]
    if Path(out_file).exists():
        with open(out_file, "r") as f:
            res = json.load(f)
    else:
        res = {}
    try:
        for author in authors:
            author_name = author["name"]
            if author_name in res and "mag_id" in res[author_name]:
                logger.info(f"Member [{author_name:30}] already has MAG info, skip")
                continue

            auid = daun = None
            for i, pub in enumerate(reversed(author["publication"])):
                pub_title = pub["title"]
                succ, auid, daun = client.get_author_id(author_name, pub_title)
                if succ:
                    break
                else:
                    if i >= max_try:
                        err_msg = f"Failed to detect MAG info for member [{author_name:30}] after [{i:3}] tries"
                        logger.error(err_msg)
                        raise Exception(err_msg)

            res_author = {
                "mag_id": auid,
                "mag_name": daun,
                "name": author["name"],
                "email": author["email"],
                "dblp": author["dblp"],
                "dblp_origin": author["dblp_origin"],
                "google_scholar": author["google_scholar"],
            }

            res[author_name] = res_author
            logger.info(
                f"Author [{author_name:30}] | MAG Id [{auid:10}] | MAG Name [{daun:30}]"
            )
    finally:
        with open(out_file, "w") as f:
            json.dump(res, f, ensure_ascii=False, indent=4)


@mag.command()
@click.argument("mag_file")
@click.argument("pc_file")
def check_missing_member(mag_file, pc_file):
    logger = logging.getLogger()
    with open(mag_file, "r") as f:
        mag_members = json.load(f)
    with open(pc_file, "r") as f:
        pc_members = []
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            pc_members.append(r)

    logger.info(f"Total MAG records: {len(mag_members)}")
    logger.info(f"Total PC members:  {len(pc_members)}")
    for p in pc_members:
        name = f'{p["first"]} {p["last"]}'
        if name not in mag_members:
            logger.warning(f"PC member [{name:30}] does not have a MAG record")


@mag.command()
@click.argument("author_json_file")
@click.argument("output_dir")
@click.option("-f", "--force", is_flag=True)
@click.option("-p", "--number_of_papers", type=int, default=10, help='How many papers to download, set to a small number for debugging, and a large number (e.g. 1000) to get all publications for each member.')
@click.option("-n", "--number_of_authors", type=int, default=1)
@click.option("-a", "--all_authors", is_flag=True)
def download_papers(
    author_json_file, output_dir, force, number_of_papers, number_of_authors, all_authors
):
    logger = logging.getLogger()
    client = mag_client()
    with open(author_json_file, "r") as f:
        authors = json.load(f)
        authors = [a for _, a in authors.items()]
        if not all_authors:
            authors = authors[:number_of_authors]
    for author in authors:
        out_file = Path(output_dir) / f'{author["name"]}.json'
        if out_file.exists() and not force:
            logger.info(
                f'Found publication records for author [{author["name"]:30}], skipping'
            )
            continue

        auid = author["mag_id"]
        pubs = client.get_author_pubs(auid, count=number_of_papers)
        len_pubs = len(pubs["entities"])
        logger.info(f'Got [{len_pubs:4}] publications for [{author["name"]:30}]')
        if len_pubs == 0:
            raise Exception(
                f"Found no publication for author {author}, MAG response {pubs}"
            )
        if len_pubs == number_of_papers:
            logger.warning(
                f"    Required [{number_of_papers:4}] publications, "
                f"got [{len_pubs:4}], "
                f"potentially more publications to get"
            )

        with chmkdir(output_dir):
            with open(f'{author["name"]}.json', "w") as f:
                json.dump(pubs["entities"], f, ensure_ascii=False, indent=4)


@contextlib.contextmanager
def chmkdir(path):
    """Go to working directory and return to previous on exit."""
    prev_cwd = Path.cwd()
    Path(path).mkdir(parents=True, exist_ok=True)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


if __name__ == "__main__":
    mag()
