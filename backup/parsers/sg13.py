import re
from typing import Dict, List, Optional


class SC13GParser:
    """Specialized parser for SEC SC 13G forms"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.content = self._read_file()
        self.documents = self._parse_documents()
        self.main_document = self._get_main_document()

    def _read_file(self) -> str:
        """Read the submission file"""
        try:
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(self.file_path, "r", encoding="latin1") as f:
                return f.read()

    def _parse_documents(self) -> List[Dict[str, str]]:
        """Parse individual documents within the submission"""
        documents = []
        doc_pattern = r"<DOCUMENT>\s*<TYPE>([^<]+)<SEQUENCE>([^<]+)<FILENAME>([^<]+)<DESCRIPTION>([^<]*)<TEXT>\s*(.*?)\s*</TEXT>\s*</DOCUMENT>"

        for match in re.finditer(doc_pattern, self.content, re.DOTALL):
            documents.append(
                {
                    "type": match.group(1).strip(),
                    "sequence": match.group(2).strip(),
                    "filename": match.group(3).strip(),
                    "description": match.group(4).strip(),
                    "content": match.group(5).strip(),
                }
            )

        return documents

    def _get_main_document(self) -> Optional[str]:
        """Get the main SC 13G document content"""
        for doc in self.documents:
            if doc["type"] in ["SC 13G", "SC 13G/A"] or doc["sequence"] == "1":
                return doc["content"]
        return None

    def get_reporting_person(self) -> Optional[str]:
        """Extract the reporting person's name from the SC 13G form"""
        if not self.main_document:
            return None

        content = self.main_document

        # Multiple patterns to find the reporting person
        patterns = [
            # Item 1 - Name of Reporting Person
            r"Item\s+1\s*[:\.\-\s]*Name\s+of\s+Reporting\s+Person[:\.\-\s]*\n\s*([^\n]+)",
            r"Item\s+1\s*[:\.\-\s]*([^\n]+(?:\n(?!\s*Item)[^\n]+)*)",
            # Item 2 - Check the domicile paragraph
            r"Item\s+2\s*[:\.\-\s]*Check\s+the\s+appropriate\s+box.*?\n\s*([^\n]+)",
            # Look for "Name of Reporting Person" directly
            r"Name\s+of\s+Reporting\s+Person[:\.\-\s]*\n?\s*([^\n]+)",
            # Look for names in the header section
            r"REPORTING\s+PERSON[:\.\-\s]*\n\s*([^\n]+)",
            # Pattern for structured format
            r"1\s*\.\s*Name\s+of\s+[Rr]eporting\s+[Pp]erson[:\.\-\s]*\n?\s*([^\n]+)",
            # Generic pattern looking for capitalized names after "Item 1"
            r"Item\s+1[^\n]*\n\s*([A-Z][A-Z\s&,\.]+(?:LLC|INC|CORP|COMPANY|LP|LTD|FUND|TRUST|CAPITAL|MANAGEMENT|PARTNERS|GROUP)?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                # Clean up the name
                name = re.sub(r"\s+", " ", name)  # Normalize whitespace
                name = name.strip(".,;:")  # Remove trailing punctuation

                # Skip if it's clearly not a name (too short, all caps instructions, etc.)
                if (
                    len(name) > 3
                    and not re.match(r"^[A-Z\s]+$", name)  # Not all caps
                    and "ITEM" not in name.upper()
                    and "CHECK" not in name.upper()
                    and "APPROPRIATE" not in name.upper()
                ):
                    return name

        return None

    def get_all_sc13g_data(self) -> Dict[str, str]:
        """Extract all key information from SC 13G form"""
        if not self.main_document:
            return {}

        content = self.main_document
        extracted_data = {}

        # Get reporting person
        extracted_data["reporting_person"] = self.get_reporting_person()

        # Other key SC 13G fields
        patterns = {
            "shares_beneficially_owned": [
                r"Item\s+(?:5|6)[^\n]*beneficial[^\n]*\n\s*([0-9,]+)",
                r"Item\s+(?:5|6)[^\n]*\n\s*([0-9,]+)\s*shares",
                r"beneficially\s+own[^\n]*\n\s*([0-9,]+)",
            ],
            "percent_of_class": [
                r"Item\s+(?:11|13)[^\n]*percent[^\n]*\n\s*([0-9\.]+)%?",
                r"percent\s+of\s+class[^\n]*\n\s*([0-9\.]+)%?",
                r"([0-9\.]+)%\s+of\s+the\s+outstanding",
            ],
            "cusip_number": [
                r"CUSIP\s+No\.?\s*([A-Z0-9]{9})",
                r"CUSIP[:\s]+([A-Z0-9]{9})",
            ],
            "date_of_event": [
                r"Item\s+3[^\n]*date[^\n]*\n\s*([0-9/\-]+)",
                r"Date\s+of\s+Event[^\n]*\n\s*([0-9/\-]+)",
            ],
            "citizenship": [
                r"Item\s+4[^\n]*citizenship[^\n]*\n\s*([^\n]+)",
                r"Citizenship\s+or\s+place\s+of\s+organization[^\n]*\n\s*([^\n]+)",
            ],
        }

        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    extracted_data[field] = value
                    break

        return extracted_data

    def print_sc13g_summary(self):
        """Print a summary of the SC 13G data"""
        data = self.get_all_sc13g_data()

        print("=== SC 13G FORM DATA ===")
        print(f"Reporting Person: {data.get('reporting_person', 'Not found')}")
        print(f"CUSIP Number: {data.get('cusip_number', 'Not found')}")
        print(
            f"Shares Beneficially Owned: {data.get('shares_beneficially_owned', 'Not found')}"
        )
        print(f"Percent of Class: {data.get('percent_of_class', 'Not found')}")
        print(f"Date of Event: {data.get('date_of_event', 'Not found')}")
        print(f"Citizenship: {data.get('citizenship', 'Not found')}")

    def search_content(self, search_term: str, context_lines: int = 3) -> List[str]:
        """Search for specific terms in the document and return surrounding context"""
        if not self.main_document:
            return []

        lines = self.main_document.split("\n")
        results = []

        for i, line in enumerate(lines):
            if search_term.lower() in line.lower():
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = "\n".join(lines[start:end])
                results.append(f"--- Match {len(results) + 1} ---\n{context}\n")

        return results

    def debug_content(self, max_chars: int = 3000):
        """Print the first part of the main document for debugging"""
        if not self.main_document:
            print("No main document found")
            return

        print("=== DOCUMENT CONTENT (for debugging) ===")
        print(self.main_document[:max_chars])
        if len(self.main_document) > max_chars:
            print(
                f"\n... (truncated, showing first {max_chars} of {len(self.main_document)} characters)"
            )


# Usage Example
if __name__ == "__main__":
    # Parse the SC 13G filing
    file_path = "sec-edgar-filings/sec-edgar-filings/AAPL/SC 13G/0001193125-19-041014/full-submission.txt"
    parser = SC13GParser(file_path)

    # Get just the reporting person
    reporting_person = parser.get_reporting_person()
    print(f"Reporting Person: {reporting_person}")

    # Get all SC 13G data
    parser.print_sc13g_summary()

    # If you need to debug, uncomment this:
    # parser.debug_content()

    # Search for specific terms
    print("\n=== SEARCHING FOR 'NAME' ===")
    name_matches = parser.search_content("name", context_lines=2)
    for match in name_matches[:3]:  # Show first 3 matches
        print(match)
