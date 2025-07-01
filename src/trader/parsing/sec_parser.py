import os
from sec_edgar_downloader import Downloader
from arelle import Cntlr
from arelle.ModelManager import ModelManager
from arelle import FileSource

import re
from typing import Dict, List, Optional

# Create controller
ctrl = Cntlr.Cntlr()
modelManager = ModelManager(ctrl)

# import re

# import trafilatura

# dl.get("10-K", "AAPL", limit=1)


class SECParser:
    def __init__(self, base_path):
        self.base_path = base_path

    def get_docs(self, symbol, doc_type, limit=1):
        dl = Downloader("John Eicher", "john.eicher89@gmail.com", self.base_path)
        dl.get(doc_type, symbol, limit=limit)


class SECSubmissionParser:
    """Parser for SEC full-submission.txt files"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.content = self._read_file()
        self.documents = self._parse_documents()
        self.header_info = self._parse_header()

    def _read_file(self) -> str:
        """Read the submission file"""
        try:
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(self.file_path, "r", encoding="latin1") as f:
                return f.read()

    def _parse_header(self) -> Dict[str, str]:
        """Parse the SEC header information"""
        header_pattern = r"<SEC-HEADER>(.*?)</SEC-HEADER>"
        header_match = re.search(header_pattern, self.content, re.DOTALL)

        header_info = {}
        if header_match:
            header_content = header_match.group(1)

            # Parse key-value pairs from header
            patterns = {
                "accession_number": r"ACCESSION NUMBER:\s*(\S+)",
                "company_name": r"COMPANY CONFORMED NAME:\s*(.+)",
                "cik": r"CENTRAL INDEX KEY:\s*(\d+)",
                "filing_date": r"FILED AS OF DATE:\s*(\d+)",
                "form_type": r"CONFORMED SUBMISSION TYPE:\s*(\S+)",
                "public_document_count": r"PUBLIC DOCUMENT COUNT:\s*(\d+)",
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, header_content)
                if match:
                    header_info[key] = match.group(1).strip()

        return header_info

    def _parse_documents(self) -> List[Dict[str, str]]:
        """Parse individual documents within the submission"""
        documents = []

        # Split by document boundaries
        doc_pattern = r"<DOCUMENT>\s*<TYPE>([^<]+)<SEQUENCE>([^<]+)<FILENAME>([^<]+)<DESCRIPTION>([^<]*)<TEXT>\s*(.*?)\s*</TEXT>\s*</DOCUMENT>"

        for match in re.finditer(doc_pattern, self.content, re.DOTALL):
            doc_type = match.group(1).strip()
            sequence = match.group(2).strip()
            filename = match.group(3).strip()
            description = match.group(4).strip()
            text_content = match.group(5).strip()

            documents.append(
                {
                    "type": doc_type,
                    "sequence": sequence,
                    "filename": filename,
                    "description": description,
                    "content": text_content,
                    "content_length": len(text_content),
                }
            )

        return documents

    def get_filing_info(self) -> Dict:
        """Get basic filing information"""
        return {
            "header": self.header_info,
            "document_count": len(self.documents),
            "documents": [
                {
                    "type": doc["type"],
                    "filename": doc["filename"],
                    "description": doc["description"],
                    "content_length": doc["content_length"],
                }
                for doc in self.documents
            ],
        }

    def get_document_by_type(self, doc_type: str) -> Optional[Dict]:
        """Get a specific document by type (e.g., 'SC 13G', 'EX-99.1')"""
        for doc in self.documents:
            if doc["type"].upper() == doc_type.upper():
                return doc
        return None

    def get_main_document(self) -> Optional[Dict]:
        """Get the main filing document (usually sequence 1)"""
        for doc in self.documents:
            if doc["sequence"] == "1":
                return doc
        return self.documents[0] if self.documents else None

    def extract_xbrl_documents(self) -> List[Dict]:
        """Find any XBRL documents in the submission"""
        xbrl_docs = []
        for doc in self.documents:
            filename = doc["filename"].lower()
            content = doc["content"].lower()

            # Check if this might be an XBRL document
            if (
                filename.endswith(".xml")
                or filename.endswith(".htm")
                or "xbrl" in filename
                or "xbrl" in content[:1000]
            ):
                xbrl_docs.append(doc)

        return xbrl_docs

    def save_document(self, doc_type: str, output_path: str) -> bool:
        """Save a specific document to a file"""
        doc = self.get_document_by_type(doc_type)
        if doc:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(doc["content"])
            return True
        return False

    def print_summary(self):
        """Print a summary of the filing"""
        print("=== SEC FILING SUMMARY ===")
        print(f"Company: {self.header_info.get('company_name', 'Unknown')}")
        print(f"CIK: {self.header_info.get('cik', 'Unknown')}")
        print(f"Form Type: {self.header_info.get('form_type', 'Unknown')}")
        print(f"Filing Date: {self.header_info.get('filing_date', 'Unknown')}")
        print(
            f"Accession Number: {self.header_info.get('accession_number', 'Unknown')}"
        )
        print(f"Number of Documents: {len(self.documents)}")

        print("\n=== DOCUMENTS IN FILING ===")
        for i, doc in enumerate(self.documents, 1):
            print(f"{i}. Type: {doc['type']}")
            print(f"   Filename: {doc['filename']}")
            print(f"   Description: {doc['description']}")
            print(f"   Content Length: {doc['content_length']:,} characters")
            print()


if __name__ == "__main__":
    base_path = "sec-edgar-filings"
    parser = SECParser(base_path)

    symbol = "AAPL"
    # doc_type = "10-K"
    doc_type = "SC 13G"

    parser.get_docs(symbol, doc_type, limit=1)
    path = os.path.join(base_path, "sec-edgar-filings", symbol, doc_type)
    # print(path)
    #
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
    print(file_path)

    # modelXbrl = modelManager.load(file_path)
    parser = SECSubmissionParser(file_path)
    parser.print_summary()
    main_doc = parser.get_main_document()
    if main_doc:
        print("=== MAIN DOCUMENT CONTENT (first 1000 chars) ===")
        print(main_doc["content"][:1000])

    # Check for any XBRL documents
    xbrl_docs = parser.extract_xbrl_documents()
    if xbrl_docs:
        print(f"\n=== FOUND {len(xbrl_docs)} XBRL DOCUMENTS ===")
        for doc in xbrl_docs:
            print(f"XBRL Document: {doc['filename']} ({doc['type']})")
    else:
        print("\n=== NO XBRL DOCUMENTS FOUND ===")
        print("This filing type (SC 13G) typically doesn't contain XBRL data.")
        print(
            "SC 13G forms are usually plain text/HTML forms for beneficial ownership reporting."
        )
