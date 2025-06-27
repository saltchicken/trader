
import os
from sec_edgar_downloader import Downloader
from bs4 import BeautifulSoup
from lxml import etree
import re

# Create downloader with identifying info
dl = Downloader("John Eicher", "john.eicher89@gmail.com")

# Download 3 recent 10-Q and 10-K filings for Apple
dl.get("10-Q", "AAPL", limit=30)
dl.get("10-K", "AAPL", limit=30)

# Folder where filings are stored
# base_path = dl.get_filings_folder()
base_path = 'sec-edgar-filings'

# Concepts we want to extract
TARGET_CONCEPTS = {
    "NetIncomeLoss": "Earnings",
    "CommonStockSharesOutstanding": "Shares Outstanding"
}

# def extract_facts(file_path):
#     with open(file_path, "r", encoding="utf-8") as f:
#         raw = f.read()
#
#     header_match = re.search(r"<SEC-HEADER>(.*?)</SEC-HEADER>", raw, re.DOTALL)
#     header = header_match.group(1) if header_match else None
#
#     # print(header)
#     xbrl_match = re.search(r"<XBRL>(.*?)</XBRL>", raw, re.DOTALL)
#     xbrl = xbrl_match.group(1) if xbrl_match else None
#     # print(xbrl)
#     if xbrl:
#         xbrl = xbrl.strip()
#         # Ensure it starts with an XML tag
#         if not xbrl.startswith("<?xml"):
#             xbrl = "<?xml version='1.0'?>" + xbrl
#
#         tree = etree.fromstring(xbrl.encode("utf-8"))
#         print(tree)
#
#         # Extract revenue or other XBRL tags
#         revenue_tags = tree.xpath("//*[contains(name(), 'Revenue') and contains(text(), 'USD')]")
#         for tag in revenue_tags:
#             print(tag.tag, tag.text)

def extract_facts(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read()

    # Extract XBRL section
    xbrl_match = re.search(r"<XBRL>(.*?)</XBRL>", raw, re.DOTALL)
    if not xbrl_match:
        print("XBRL section not found")
        return

    xbrl = xbrl_match.group(1).strip()
    if not xbrl.startswith("<?xml"):
        xbrl = "<?xml version='1.0'?>" + xbrl

    try:
        tree = etree.fromstring(xbrl.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        print("XML parse error:", e)
        return

    ns = {
        "ix": "http://www.xbrl.org/2013/inlineXBRL",
        "us-gaap": "http://fasb.org/us-gaap/2024",
        "dei": "http://xbrl.sec.gov/dei/2024"
    }

    # Find all ix:nonFraction (which hold numeric facts)
    facts = tree.xpath("//ix:nonFraction", namespaces=ns)

    for fact in facts:
        name = fact.attrib.get("name", "")
        context = fact.attrib.get("contextRef", "")
        value = fact.text
        if "Revenue" in name or "EarningsPerShare" in name or "SharesOutstanding" in name:
            print(f"{name} ({context}): {value}")

def extract_revenue_with_dates(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read()

    # Extract the <XBRL> section
    xbrl_match = re.search(r"<XBRL>(.*?)</XBRL>", raw, re.DOTALL)
    if not xbrl_match:
        raise ValueError("XBRL section not found")
    xbrl = xbrl_match.group(1).strip()
    if not xbrl.startswith("<?xml"):
        xbrl = "<?xml version='1.0'?>" + xbrl

    tree = etree.fromstring(xbrl.encode("utf-8"))

    ns = {
        "ix": "http://www.xbrl.org/2013/inlineXBRL",
        "xbrli": "http://www.xbrl.org/2003/instance",
        "xbrldi": "http://xbrl.org/2006/xbrldi",
    }

    # Build a map of context ID -> date range + segment label
    context_data = {}
    for ctx in tree.xpath("//xbrli:context", namespaces=ns):
        ctx_id = ctx.attrib["id"]

        # Try to get start/end dates (duration) or instant (point-in-time)
        start = ctx.find("xbrli:period/xbrli:startDate", namespaces=ns)
        end = ctx.find("xbrli:period/xbrli:endDate", namespaces=ns)
        instant = ctx.find("xbrli:period/xbrli:instant", namespaces=ns)

        if start is not None and end is not None:
            date_range = (start.text, end.text)
        elif instant is not None:
            date_range = (instant.text, instant.text)
        else:
            date_range = (None, None)

        # Try to get a label (e.g., Product, Service)
        segment = ctx.find(".//xbrldi:explicitMember", namespaces=ns)
        if segment is not None:
            segment_name = segment.text.split(":")[-1]
        else:
            segment_name = "Total"

        context_data[ctx_id] = {
            "start_date": date_range[0],
            "end_date": date_range[1],
            "segment": segment_name
        }

    # Extract facts and link to context
    facts = tree.xpath("//ix:nonFraction", namespaces=ns)

    data = []
    for fact in facts:
        name = fact.attrib.get("name", "")
        if "RevenueFromContractWithCustomerExcludingAssessedTax" in name:
            ctx_id = fact.attrib.get("contextRef")
            value = fact.text.replace(",", "") if fact.text else None

            if ctx_id in context_data and value:
                row = {
                    "value": float(value),
                    "start_date": context_data[ctx_id]["start_date"],
                    "end_date": context_data[ctx_id]["end_date"],
                    "segment": context_data[ctx_id]["segment"]
                }
                data.append(row)

    return data


def extract_total_revenue(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read()

    xbrl_match = re.search(r"<XBRL>(.*?)</XBRL>", raw, re.DOTALL)
    if not xbrl_match:
        raise ValueError("XBRL section not found")

    xbrl = xbrl_match.group(1).strip()
    if not xbrl.startswith("<?xml"):
        xbrl = "<?xml version='1.0'?>" + xbrl

    tree = etree.fromstring(xbrl.encode("utf-8"))

    ns = {
        "ix": "http://www.xbrl.org/2013/inlineXBRL",
        "xbrli": "http://www.xbrl.org/2003/instance",
        "xbrldi": "http://xbrl.org/2006/xbrldi",
    }

    # Step 1: Map contextRef → date range, and check if it's "Total" (no segment)
    context_data = {}
    for ctx in tree.xpath("//xbrli:context", namespaces=ns):
        ctx_id = ctx.attrib["id"]

        # Dates
        start = ctx.find("xbrli:period/xbrli:startDate", namespaces=ns)
        end = ctx.find("xbrli:period/xbrli:endDate", namespaces=ns)
        instant = ctx.find("xbrli:period/xbrli:instant", namespaces=ns)

        if start is not None and end is not None:
            date_range = (start.text, end.text)
        elif instant is not None:
            date_range = (instant.text, instant.text)
        else:
            continue

        # Skip if there's a <xbrldi:explicitMember> segment — not "Total"
        if ctx.find(".//xbrldi:explicitMember", namespaces=ns) is not None:
            continue

        # Save only contexts for total (no explicit member)
        context_data[ctx_id] = {
            "start_date": date_range[0],
            "end_date": date_range[1]
        }

    # Step 2: Pull only revenue facts linked to these "total" contextRefs
    results = []
    for fact in tree.xpath("//ix:nonFraction", namespaces=ns):
        name = fact.attrib.get("name", "")
        context_ref = fact.attrib.get("contextRef", "")
        if (
            "RevenueFromContractWithCustomerExcludingAssessedTax" in name
            and context_ref in context_data
        ):
            value = fact.text.replace(",", "") if fact.text else None
            if value:
                results.append({
                    "value": float(value),
                    "start_date": context_data[context_ref]["start_date"],
                    "end_date": context_data[context_ref]["end_date"]
                })

    return results

path = os.path.join(base_path, "AAPL", "10-Q")
if not os.path.exists(path):
    print("Not there dawg")
    exit()

for filing_dir in os.listdir(path):
    filing_path = os.path.join(path, filing_dir)
    txt_files = [f for f in os.listdir(filing_path) if f.endswith(".txt")]
    other_files = [f for f in os.listdir(filing_path) if not f.endswith(".txt")]
    if len(txt_files) == 0:
        print("no txt files")
        continue
    if len(txt_files) > 1:
        print("too many txt files")
        continue
    if len(other_files) > 0:
        print("other files")
        continue

    file_path = os.path.join(filing_path, txt_files[0])
    print(file_path)

    # facts = extract_facts(file_path)
    # facts = extract_revenue_with_dates(file_path)
    facts = extract_total_revenue(file_path)
    print(facts)


    # if facts:
    #     print(f"\n=== 10-Q Filing: {filing_dir} ===")
    #     for concept, context, value in facts:
    #         print(f"{TARGET_CONCEPTS[concept]} ({context}): {value}")
