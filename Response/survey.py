import click
import csv
import json
import logging
from fuzzywuzzy import fuzz
from collections import defaultdict
from prettytable import PrettyTable
from dateutil.parser import parse as parse_time

log_format = logging.Formatter(
    "[%(asctime)s][%(filename)s:%(lineno)4s - %(funcName)10s()] %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
handler = logging.FileHandler("survey.log")
handler.setFormatter(log_format)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.DEBUG)


def get_timezones():
    # https://stackoverflow.com/a/4766400
    tz_str = """-12 Y
    -11 X NUT SST
    -10 W CKT HAST HST TAHT TKT
    -9 V AKST GAMT GIT HADT HNY
    -8 U AKDT CIST HAY HNP PST PT
    -7 T HAP HNR MST PDT
    -6 S CST EAST GALT HAR HNC MDT
    -5 R CDT COT EASST ECT EST ET HAC HNE PET
    -4 Q AST BOT CLT COST EDT FKT GYT HAE HNA PYT
    -3 P ADT ART BRT CLST FKST GFT HAA PMST PYST SRT UYT WGT
    -2 O BRST FNT PMDT UYST WGST
    -1 N AZOT CVT EGT
    0 Z EGST GMT UTC WET WT
    1 A CET DFT WAT WEDT WEST
    2 B CAT CEDT CEST EET SAST WAST
    3 C EAT EEDT EEST IDT MSK
    4 D AMT AZT GET GST KUYT MSD MUT RET SAMT SCT
    5 E AMST AQTT AZST HMT MAWT MVT PKT TFT TJT TMT UZT YEKT
    6 F ALMT BIOT BTT IOT KGT NOVT OMST YEKST
    7 G CXT DAVT HOVT ICT KRAT NOVST OMSST THA WIB
    8 H ACT AWST BDT BNT CAST HKT IRKT KRAST MYT PHT SGT ULAT WITA WST
    9 I AWDT IRKST JST KST PWT TLT WDT WIT YAKT
    10 K AEST ChST PGT VLAT YAKST YAPT
    11 L AEDT LHDT MAGT NCT PONT SBT VLAST VUT
    12 M ANAST ANAT FJT GILT MAGST MHT NZST PETST PETT TVT WFT
    13 FJST NZDT
    11.5 NFT
    10.5 ACDT LHST
    9.5 ACST
    6.5 CCT MMT
    5.75 NPT
    5.5 SLT
    4.5 AFT IRDT
    3.5 IRST
    -2.5 HAT NDT
    -3.5 HNT NST NT
    -4.5 HLV VET
    -9.5 MART MIT"""

    tzd = {}
    for tz_descr in map(str.split, tz_str.split("\n")):
        tz_offset = int(float(tz_descr[0]) * 3600)
        for tz_code in tz_descr[1:]:
            tzd[tz_code] = tz_offset
    return tzd


@click.group()
def survey():
    pass


@survey.command()
@click.argument("in_file")
@click.argument("out_file")
def parse(in_file, out_file):
    logger = logging.getLogger()
    logger.info(f"Read {in_file}")
    data = []
    with open(in_file, "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            data.append(row)

    logger.info(f"Transform to json type")
    res = []
    topics = set()

    last_delimiter_used = ""
    for d in data:
        r = {}
        r["timestamp"] = d["Timestamp"]
        r["name"] = d["Name (First Last)"].strip()
        r["dblp"] = d["Your DBLP URL"]
        r["google_scholar"] = d["Your Google Scholar URL"]
        country_field = "From which country are you likely attending the Virtual PC meeting (July 8~9)? (We will use this information to predict your time zone during the PC meeting for planning purposes.)"
        if country_field in d.keys():
            r["meeting_country"] = d[country_field]
        r["comments"] = d["Comments"]

        comma_delim_fields = {
            "FPGA, CGRA, Reconfigurable Systems": "FPGA/CGRA/Reconfigurable Systems"
        }
        for k in [
            "Topics",
            "Application Domains",
            "Memory/Storage",
            "Compilers/Programming Languages",
            "Measurement, Modeling, Simulation",
            "Operating Systems",
            "Microarchitecture",
        ]:
            delimiter = ";"
            curr_topics = d[k]
            if len(curr_topics) > 0 and ";" not in curr_topics:
                delimiter = ","
                if len(last_delimiter_used) > 0 and last_delimiter_used != delimiter:
                    raise Exception(
                        f'Delimiter discrepancy, last time used "{last_delimiter_used}", but this time "{delimiter}"'
                    )
                else:
                    last_delimiter_used = delimiter
            if len(curr_topics) > 0:
                for src, tgt in comma_delim_fields.items():
                    if src in curr_topics:
                        logger.debug(f"Before applying comma fixing {curr_topics}")
                        curr_topics = curr_topics.replace(src, tgt)
                        logger.debug(f"After applying comma fixing {curr_topics}")
            curr_topics = [t.strip() for t in curr_topics.split(delimiter)]
            r[k] = curr_topics
            for f in curr_topics:
                topics.add(f)
        res.append(r)

    logger.info(f"Save to {out_file}")
    with open(out_file, "w") as f:
        json.dump(res, f, indent=4, ensure_ascii=False)

    logger.info(f"All topic fields:")
    for i, t in enumerate(topics):
        logger.info(f"  {i:02}: {t}")


def dedup_response(resps, strategy, fields=[]) -> dict:
    logger = logging.getLogger()
    tzd = get_timezones()
    resps.sort(key=lambda r: parse_time(r["timestamp"], tzinfos=tzd))
    if strategy == "latest":
        return resps[-1]
    elif strategy == "earliest":
        return resps[0]
    elif strategy == "union":
        res = {}
        for k in resps[0].keys():
            if k in fields:
                u = set()
                for r in resps:
                    for v in r[k]:
                        u.add(v)
                res[k] = list(u)
            else:
                res[k] = resps[-1][k]
        return res


@survey.command()
@click.argument("survey_file")
@click.option("-u", "--union_response", multiple=True)
@click.option("-l", "--latest_response", multiple=True)
@click.option("-e", "--earliest_response", multiple=True)
@click.option("-o", "--dedup_file")
def check_duplicate(
    survey_file, union_response, latest_response, earliest_response, dedup_file
):
    logger = logging.getLogger()

    # Read json file
    with open(survey_file, "r") as f:
        data = json.load(f)

    # Check duplicated response

    logger.info(f"Checking duplicate responses")
    response_count = defaultdict(int)
    for d in data:
        response_count[d["name"]] += 1
    dedup_data = {}
    for name, cnt in response_count.items():
        if cnt > 1:
            logger.warning(f"Got [{cnt:02}] duplicate responses from [{name:20}]")
            resp = [d for d in data if d["name"] == name]
            inconsistent_fields = set()
            for field in resp[0].keys():
                if field == "timestamp":
                    continue
                value = resp[0][field]
                for n, r in enumerate(resp[1:]):
                    if r[field] != value:
                        inconsistent_fields.add(field)
            inconsistent_fields = list(inconsistent_fields)
            inconsistent_fields.sort()
            if len(inconsistent_fields) > 0:
                report = PrettyTable()
                logger.debug(f"[{name}] inconsistent_fields: {inconsistent_fields}")
                report.field_names = ["Type", "Response Time."] + inconsistent_fields
                for n, r in enumerate(resp):
                    rep = ["Original Response", r["timestamp"]]
                    for field in inconsistent_fields:
                        rep.append(r[field])
                    report.add_row(rep)
                logger.warning(f"    Inconsistent response:")
                if name in latest_response:
                    dedup = dedup_response(resp, "latest")
                    dedup_report = ["Dedup (Latest)", dedup["timestamp"]]
                    for field in inconsistent_fields:
                        dedup_report.append(dedup[field])
                    report.add_row(dedup_report)
                elif name in union_response:
                    dedup = dedup_response(
                        resp,
                        "union",
                        fields=[
                            f for f in inconsistent_fields if f != "meeting_country"
                        ],
                    )
                    dedup_report = ["Dedup (Union)", dedup["timestamp"]]
                    for field in inconsistent_fields:
                        dedup_report.append(dedup[field])
                    report.add_row(dedup_report)
                elif name in earliest_response:
                    dedup = dedup_response(resp, "earliest")
                    dedup_report = ["Dedup (Earliest)", dedup["timestamp"]]
                    for field in inconsistent_fields:
                        dedup_report.append(dedup[field])
                    report.add_row(dedup_report)
                else:
                    dedup = dedup_response(resp, "latest")
                    dedup_report = ["Dedup (Latest)", dedup["timestamp"]]
                    for field in inconsistent_fields:
                        dedup_report.append(dedup[field])
                    report.add_row(dedup_report)
                    logger.warning(f'Applying default "latest" strategy')

                logger.info("\n" + report.get_string(title=name))
            else:
                logger.info(
                    f"    No inconsistent responses found, apply latest strategy to remove duplicate responses"
                )
                dedup = dedup_response(resp, "latest")
                logger.info(f"    {dedup}")
            dedup_data[name] = dedup

    if dedup_file:
        logger.info(f"Output dedup results to {dedup_file}")
        dedup_output = []
        for name, cnt in response_count.items():
            if cnt == 0:
                raise Exception(
                    "This member has 0 response, something is wrong with this script"
                )
            elif cnt == 1:
                for d in data:
                    if name == d["name"]:
                        dedup_output.append(d)
                        break
            else:
                d = dedup_data[name]
                logger.info(f"Create dedup record for [{name:20}]: {d}")
                dedup_output.append(d)
        if len(dedup_output) != len(response_count):
            raise Exception(
                f"Dedup failed, number of records not matching: {len(dedup_output)} != {len(response_count)}"
            )
        with open(dedup_file, "w") as f:
            json.dump(dedup_output, f, indent=4, ensure_ascii=False)


@survey.command()
@click.argument("survey_file")
@click.argument("member_file")
@click.option("-c", "--cnt_fuzzy_results", default=3, type=int)
@click.option("-r", "--fuzzy_ratio", default=0, type=int)
def check_no_response(survey_file, member_file, cnt_fuzzy_results, fuzzy_ratio):
    logger = logging.getLogger()

    logger.info(f"Read survey file: {survey_file}")
    with open(survey_file, "r") as f:
        survey = json.load(f)

    logger.info(f"Read member file: {member_file}")
    with open(member_file, "r") as f:
        reader = csv.DictReader(f)
        member = []
        for row in reader:
            member.append(row)

    logger.info(f"Check members not responded yet")
    all_response = set([r["name"] for r in survey])
    all_member_names = [r["first"] + " " + r["last"] for r in member]
    no_response_members = []
    for m in all_member_names:
        if m not in all_response:
            no_response_members.append(m)
    report = PrettyTable()
    if "email" in member[0].keys():
        report.field_names = ["name", "email"]
        for m in no_response_members:
            email = ""
            for origin_member in member:
                if m == origin_member["first"] + " " + origin_member["last"]:
                    email = origin_member["email"]
            report.add_row([m, email])
    else:
        report.field_names = ["name"]
        for m in no_response_members:
            report.add_row([m])
    report.align = "l"
    logger.info("\n" + report.get_string(title="Members not responded yet"))

    if len(all_response) + len(no_response_members) != len(all_member_names):
        logger.critical(
            f"Number of records mismatched, maybe someone misspell his/her name and this script does not detect it:"
        )
        logger.critical(f"    All Responses: {len(all_response)}")
        logger.critical(f"    All Members  : {len(all_member_names)}")
        logger.critical(f"    No Response  : {len(no_response_members)}")
        logger.critical(
            f"    Error        : {len(all_response) + len(no_response_members) - len(all_member_names)}"
        )
        logger.info(f"Try to fuzzy match the names")
        report = PrettyTable()

        if "email" in member[0].keys():
            report.field_names = ["Member Name", "Email"] + [
                f"Resp candidate {i}" for i in range(cnt_fuzzy_results)
            ]
        else:
            report.field_names = ["Member Name"] + [
                f"Resp candidate {i}" for i in range(cnt_fuzzy_results)
            ]
        for m in no_response_members:
            candidates = []
            for c in all_response:
                r = fuzz.ratio(m.lower(), c.lower())
                if r > fuzzy_ratio:
                    candidates.append({"name": c, "ratio": r})
            candidates.sort(key=lambda x: x["ratio"], reverse=True)
            if "email" in member[0].keys():
                email = ""
                for origin_member in member:
                    if m == origin_member["first"] + " " + origin_member["last"]:
                        email = origin_member["email"]
                report.add_row(
                    [m, email]
                    + [
                        f'{c["name"]}({c["ratio"]})'
                        for c in candidates[:cnt_fuzzy_results]
                    ]
                )
            else:
                report.add_row(
                    [m]
                    + [
                        f'{c["name"]}({c["ratio"]})'
                        for c in candidates[:cnt_fuzzy_results]
                    ]
                )
        report.align = "l"
        logger.info("\n" + report.get_string(title="Members not responded yet"))

        logger.info(f"Reverse fuzzy matching")
        report = PrettyTable()
        report.field_names = ["Responded Member Name"] + [
            f"Member candidate {i}" for i in range(cnt_fuzzy_results)
        ]
        name_to_remove = []
        for name in all_response:
            if name not in all_member_names:
                candidates = []
                for c in all_member_names:
                    r = fuzz.ratio(name.lower(), c.lower())
                    if r > fuzzy_ratio:
                        candidates.append({"name": c, "ratio": r})
                candidates.sort(key=lambda x: x["ratio"], reverse=True)
                report.add_row(
                    [name]
                    + [
                        f'{c["name"]}({c["ratio"]})'
                        for c in candidates[:cnt_fuzzy_results]
                    ]
                )
                name_to_remove.append(name)
        report.align = "l"
        logger.info(
            "\n" + report.get_string(title="Members responded but name not found")
        )


@survey.command()
@click.argument("filename")
@click.option("-o", "--out_filename")
@click.option("-n", "--name", multiple=True, type=(str, str))
def fix_name(filename, out_filename, name):
    logger = logging.getLogger()
    logger.info(f"Fix names")
    table = PrettyTable()
    table.field_names = ["origin", "fixed"]
    table.add_rows(name)
    logger.info("\n" + table.get_string(title="Name Fixes"))

    with open(filename, "r") as f:
        data = json.load(f)

    need_fix = dict()
    for src, tgt in name:
        need_fix[src] = tgt

    for d in data:
        if d["name"] in need_fix.keys():
            logger.info(f'Rename {d["name"]} --> {need_fix[d["name"]]}')
            d["name"] = need_fix[d["name"]]

    if out_filename:
        with open(out_filename, "w") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


@survey.command()
@click.argument("survey_file")
@click.argument("member_file")
@click.option("-o", "--out_file")
def add_email(survey_file, member_file, out_file):
    with open(survey_file, "r") as f:
        survey = json.load(f)
    with open(member_file, "r") as f:
        reader = csv.DictReader(f)
        emails = dict()
        for m in reader:
            emails[f'{m["first"]} {m["last"]}'] = m["email"]

    res = []
    for s in survey:
        s["email"] = emails[s["name"]]
        res.append(s)

    if out_file:
        with open(out_file, "w") as f:
            json.dump(res, f, indent=4, ensure_ascii=False)


def check_and_add_fields(hotcrp, responses, new_fields):
    category_map = {
        "ApplicationDomains": "Application Domains",
        "Measurement,Modeling,Simulation": "Measurement, Modeling, Simulation",
        "Architecture Support for OS": "Operating Systems",
    }
    subtopic_map = {
        "FPGA, CGRA, Reconfigurable Systems": "FPGA/CGRA/Reconfigurable Systems",
        "Parallelism(Memory Consistency/Coherence)": "Parallelism (Memory Consistency/Coherence)",
    }

    logger = logging.getLogger()
    topics = [f for f in hotcrp.keys() if f.startswith("topic: ")]
    survey = None
    name = hotcrp["first"] + " " + hotcrp["last"]

    logger.info(f"Checking [{name:20}]")
    for resp in responses:
        if resp["name"] == name:
            survey = resp
            break
    if not survey:
        logger.warning(f"Survey response not found for [{name:20}]")
        for nf in new_fields:
            hotcrp[nf] = "Not responded"
        # Do not hard check topics as it may be set by member,
        #   but not responded through survey
        for t in topics:
            if hotcrp[t] is not None and hotcrp[t] != "" and int(hotcrp[t]) != 0:
                logger.warning(
                    f"    Topic set on HotCRP not from Google Forms: [{t:40}] value [{hotcrp[t]:3}]"
                )
            if hotcrp[t] is None or hotcrp[t] == "":
                hotcrp[t] = 0
            else:
                if int(hotcrp[t]) <= 0:
                    hotcrp[t] = 0
                else:
                    hotcrp[t] = 1
    else:
        for nf in new_fields:
            if nf not in survey.keys():
                if nf == "meeting_country":
                    hotcrp[nf] = ""
                    continue
                else:
                    raise Exception(f"Field [{nf}] missing in record {survey}")
            hotcrp[nf] = survey[nf]
        # Hard check topics from HotCRP to make sure the updates are as expected
        for t in topics:
            rt = t
            rt = ": ".join(rt.split(": ")[1:])
            rt = ". ".join(rt.split(". ")[1:])
            category = rt.split(":")[0].strip()
            if category in category_map:
                category = category_map[category]
            subtopic = rt.split(":")[1].strip()
            if subtopic in subtopic_map:
                subtopic = subtopic_map[subtopic]
            if int(hotcrp[t]) <= 0:
                if subtopic in survey[category]:
                    raise Exception(
                        f"Inconsistent record for [{name:20}]"
                        + f" hotcrp topic [{t}] is {hotcrp[t]}"
                        + f" but survey response of [{category}] has [{subtopic}]"
                    )
                hotcrp[t] = 0
            if int(hotcrp[t]) > 0:
                if subtopic not in survey[category]:
                    raise Exception(
                        f"Inconsistent record for [{name:20}]"
                        + f" hotcrp topic [{t}] is {hotcrp[t]}"
                        + f" but survey response of [{category}] has no [{subtopic}]"
                    )
                hotcrp[t] = 1
    return hotcrp


@survey.command()
@click.argument("hotcrp_file")
@click.argument("out_file")
@click.option("-e", "--erc_response")
@click.option("-t", "--tpc_response")
def gen_csv(hotcrp_file, out_file, erc_response, tpc_response):
    resp = []
    with open(erc_response, "r") as f:
        resp += json.load(f)
    with open(tpc_response, "r") as f:
        resp += json.load(f)
    hotcrp = []
    with open(hotcrp_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            hotcrp.append(row)
    out = []
    new_fields = ["timestamp", "dblp", "google_scholar", "meeting_country", "comments"]
    for h in hotcrp:
        res = check_and_add_fields(h, resp, new_fields)
        out.append(res)
    with open(out_file, "w") as f:
        writer = csv.DictWriter(f, fieldnames=out[0].keys())
        writer.writeheader()
        writer.writerows(out)


if __name__ == "__main__":
    survey()
