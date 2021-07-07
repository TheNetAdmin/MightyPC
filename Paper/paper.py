import contextlib
import json
import logging
import os
import re
from collections import Counter
from pathlib import Path

import click
import pdftotext
from refextract import extract_references_from_file

log_format = logging.Formatter(
    "[%(asctime)s][%(filename)s:%(lineno)4s - %(funcName)10s()] %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
handler = logging.FileHandler("paper.log")
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)


@click.group()
def paper():
    pass


@paper.command()
@click.argument("paper_path")
@click.argument("paper_data")
def parse_hotcrp_info(paper_path, paper_data):
    logger = logging.getLogger()
    with open(paper_data, "r") as f:
        data_origin = json.load(f)
        data = dict()
        for d in data_origin:
            data[d["pid"]] = d
    with chdir(paper_path):
        for file in Path(".").iterdir():
            if ".pdf" not in file.name:
                continue
            logger.info(f"Parsing {file.name}")
            pid = re.findall(r"(?:paper)(\d+)(?:\.pdf)", file.name)[0]
            pdata = data[int(pid)]
            file = file.resolve()
            with chmkdir(pid):
                with open(f"paper{pid}.json", "w") as f:
                    json.dump(pdata, f, ensure_ascii=False, indent=4)
                file.rename(file.name)


def _extract_single(curr_paper_path, force=False):
    logger = logging.getLogger()
    file = Path(curr_paper_path)
    with chdir(file.resolve()):
        pdata = prefs = ptext = None
        data_file = pdf_file = None
        for curr_file in Path(".").iterdir():
            if ".json" in curr_file.name and not pdata:
                data_file = curr_file
                with open(curr_file, "r") as f:
                    pdata = json.load(f)
            elif ".pdf" in curr_file.name and not prefs:
                pdf_file = curr_file.name
                with open(curr_file, "rb") as f:
                    ptext = pdftotext.PDF(f)
        if not force and "reference" in pdata:
            logger.info("    Already parsed, skip")
            return
        else:
            logger.info(f"Parsing [{file.name:>4}]")
        # Parse reference counts
        cite = []
        for ppage in ptext:
            cpage = re.sub(r"\s+", " ", ppage)
            cite += re.findall(r"\[[\d\,\-\s]+\]", cpage)
        ref_count = Counter()
        for c in cite:
            cc = c
            cc = cc.replace("[", "")
            cc = cc.replace("]", "")
            cc = re.sub(r"[\,\s]+", " ", cc)
            for single_cite in cc.split(" "):
                if single_cite == "":
                    continue
                try:
                    if "-" in single_cite:
                        # NOTE: this brings some false positive, for e.g.
                        #       consider a range represented in submission text [1, 15]
                        #       this is parsed as citation, but it should be a range
                        cite_group = single_cite.split("-")
                        if len(cite_group) != 2:
                            logger.warning(f"Skipping non-citation entry: [{c}]")
                            continue
                        start, end = cite_group
                        if start == "" or end == "" or int(start) < 0 or int(end) < 0:
                            logger.warning(f"Skipping non-citation entry: [{c}]")
                            continue
                        for i in range(int(start), int(end) + 1):
                            ref_count[int(i)] += 1
                    else:
                        if int(single_cite) < 0:
                            logger.warning(f"Skipping non-citation entry: [{c}]")
                            continue
                        ref_count[int(single_cite)] += 1
                except Exception as e:
                    logger.error(f"Cannot convert to int: [{single_cite}] [{c}]")
                    raise e
        # Parse reference list
        ref_count = dict(ref_count)
        prefs = extract_references_from_file(pdf_file)
        for ref in prefs:
            ref_id = ref["linemarker"][0]
            try:
                ref["count"] = ref_count[int(ref_id)]
            except KeyError as e:
                logger.error(f"Error parsing paper {file.name}")
                logger.error(f"Dangling citation id {ref_id}")
                logger.error(f"Original citations {cite}")
                raise e
            # Fix reference title if not parsed
            if "title" not in ref:
                title = ""

                def parse_title(s):
                    s = re.sub(r"\s[a-zA-Z]\.\s", " ", s)
                    s = re.sub(r"\[\d+\]", "", s)
                    candidate = s.split(".")
                    res = ""
                    if len(candidate) > 2:
                        if "and " in candidate[0]:
                            res = candidate[1]
                        elif "[" in candidate[0] or "]" in candidate[0]:
                            res = candidate[1]
                        else:
                            res = ""
                    else:
                        res = candidate[0]
                    if len(res) > 15:
                        return res
                    else:
                        return ""

                if "raw_ref" in ref:
                    rr = ref["raw_ref"][0]
                    if "author" in ref:
                        for a in ref["author"]:
                            rr = rr.replace(a, "")
                    title = parse_title(rr)
                if len(title) == 0 and "misc" in ref:
                    if "." in ref["misc"][-1]:
                        title = parse_title(ref["misc"][-1])
                    else:
                        title = parse_title(ref["misc"][0])
                    if "page" in title and len(ref["misc"]) > 1:
                        candidate = ref["misc"][0].split(".")
                        title = None
                        if len(candidate) > 2 and "and " in candidate[0]:
                            title = candidate[1]
                        else:
                            title = candidate[0]

                ref["title"] = [title]
        # Update result
        pdata["reference"] = prefs
        with open(data_file, "w") as f:
            json.dump(pdata, f, ensure_ascii=False, indent=4)


@paper.command()
@click.argument("curr_paper_path")
@click.option("-f", "--force", is_flag=True)
def extract_single(curr_paper_path, force):
    _extract_single(curr_paper_path, force)


@paper.command()
@click.argument("curr_paper_path")
def clear_single(curr_paper_path):
    logger = logging.getLogger()
    file = Path(curr_paper_path)
    with chdir(file.resolve()):
        for curr_file in Path(".").iterdir():
            if ".json" in curr_file.name:
                with open(curr_file, "r") as f:
                    pdata = json.load(f)
                if "reference" in pdata:
                    pdata.pop("reference")
                    logger.info(
                        f'Clear "reference" field in data file {curr_file.name}'
                    )
                    with open(curr_file, "w") as f:
                        json.dump(pdata, f, ensure_ascii=False, indent=4)


@paper.command()
@click.argument("paper_path")
def extract_reference(paper_path):
    with chdir(paper_path):
        for file in Path(".").iterdir():
            if not file.is_dir():
                continue
            _extract_single(file)


@paper.command()
@click.argument("paper_path")
@click.option("-s", "--skip", multiple=True)
def gen_makefile(paper_path, skip):
    with chdir(paper_path):
        paths = []
        for file in Path(".").iterdir():
            if file.is_dir():
                if file.name in skip:
                    continue
                paths.append(file.name)
        paths.sort()
        with open("Makefile", "w") as f:
            f.write(f".DEFAULT_GOAL=all\n")
            f.write(f"\n")
            f.write(f"%/parse:\n")
            f.write(f"\tpython3 ../paper.py extract-single $*\n")
            f.write(f"\n")
            f.write(f"%/clean:\n")
            f.write(f"\tpython3 ../paper.py clear-single $*\n")
            f.write(f"\n")
            f.write(f".PHONY: all\n")
            f.write(f"all: \\\n\t" + "\\\n\t".join([f"{p}/parse" for p in paths]))
            f.write(f"\n")
            f.write(f".PHONY: clean\n")
            f.write(f"clean: \\\n\t" + "\\\n\t".join([f"{p}/clean" for p in paths]))


@contextlib.contextmanager
def chdir(path):
    """Go to working directory and return to previous on exit."""
    prev_cwd = Path.cwd()
    os.chdir(Path(path))
    try:
        yield
    finally:
        os.chdir(prev_cwd)


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
    paper()
