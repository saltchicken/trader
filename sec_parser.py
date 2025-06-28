import os
from sec_edgar_downloader import Downloader
import re

# dl.get("10-K", "AAPL", limit=1)


class SECParser:
    def __init__(self, base_path):
        self.base_path = base_path

    def get_docs(self, symbol, doc_type, limit=1):
        dl = Downloader("John Eicher", "john.eicher89@gmail.com", self.base_path)
        dl.get(doc_type, symbol, limit=limit)


if __name__ == "__main__":
    base_path = "sec-edgar-filings"
    parser = SECParser(base_path)

    symbol = "AAPL"
    # doc_type = "10-K"
    doc_type = "SC 13G"

    parser.get_docs(symbol, doc_type, limit=1)
    path = os.path.join(base_path, "sec-edgar-filings", symbol, doc_type)

    if not os.path.exists(path):
        print("Something went wrong")
        exit()

    filing_dirs = [
        filing
        for filing in os.listdir(path)
        if os.path.isdir(os.path.join(path, filing))
    ]

    filing_path = os.path.join(path, filing_dirs[0])
    txt_files = [f for f in os.listdir(filing_path) if f.endswith(".txt")]
    other_files = [f for f in os.listdir(filing_path) if not f.endswith(".txt")]
    if len(txt_files) == 0:
        print("no txt files")
        exit()
    if len(txt_files) > 1:
        print("too many txt files")
        exit()
    if len(other_files) > 0:
        print("other files")
        exit()

    file_path = os.path.join(filing_path, txt_files[0])

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    documents = re.findall(r"<DOCUMENT>(.*?)</DOCUMENT>", content, re.DOTALL)
    print(f"Found {len(documents)} documents")

    # Make a folder inside base_path called documents
    documents_path = os.path.join(base_path, "documents")
    if not os.path.exists(documents_path):
        os.makedirs(documents_path)

    for i, doc in enumerate(documents):
        with open(
            f"{documents_path}/document_{i + 1}.html", "w", encoding="utf-8"
        ) as out_file:
            out_file.write(doc)
