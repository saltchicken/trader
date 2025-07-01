import os
from sec_edgar_downloader import Downloader
from arelle import Cntlr
from arelle.ModelManager import ModelManager
from arelle import FileSource

import re
from typing import Dict, List, Optional
import json

# Create controller
ctrl = Cntlr.Cntlr()
modelManager = ModelManager(ctrl)


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
        """Get a specific document by type (e.g., '10-K', 'EX-99.1')"""
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

    def parse_xbrl_from_documents(self):
        """Extract and parse XBRL data from documents in this filing"""
        from arelle import Cntlr
        from arelle.ModelManager import ModelManager
        import tempfile
        import os

        results = []

        # Get potential XBRL documents - focus on the main instance document
        xbrl_docs = self.extract_xbrl_documents()

        # Filter to only process the main instance document (typically ends with .htm and contains the company ticker)
        main_xbrl_docs = []
        for doc in xbrl_docs:
            filename = doc["filename"].lower()
            # Look for main instance document (usually company-date.htm)
            if (
                filename.endswith(".htm")
                and not filename.startswith("r")
                and not filename.startswith("a10-k")
            ):
                main_xbrl_docs.append(doc)

        if not main_xbrl_docs:
            print("No main XBRL instance documents found.")
            return results

        # Set up Arelle
        ctrl = Cntlr.Cntlr()
        modelManager = ModelManager(ctrl)

        for doc in main_xbrl_docs:
            print(f"Processing main XBRL document: {doc['filename']}")

            # Create temporary file with the XBRL content
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".xml", delete=False, encoding="utf-8"
            ) as temp_file:
                temp_file.write(doc["content"])
                temp_path = temp_file.name

            try:
                # Load with Arelle
                modelXbrl = modelManager.load(temp_path)

                if modelXbrl and len(modelXbrl.facts) > 0:
                    doc_facts = self._extract_facts_from_model(
                        modelXbrl, doc["filename"]
                    )
                    results.append({"document": doc["filename"], "facts": doc_facts})
                    print(f"  Found {len(doc_facts)} facts")
                else:
                    print(f"  No facts found in {doc['filename']}")

            except Exception as e:
                print(f"  Error processing {doc['filename']}: {e}")
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass

        return results

    def _extract_facts_from_model(self, modelXbrl, document_name):
        """Extract facts from an Arelle ModelXbrl object"""
        facts_data = []

        for fact in modelXbrl.facts:
            fact_info = {
                "concept": fact.concept.name
                if hasattr(fact, "concept") and fact.concept
                else "Unknown",
                "value": fact.value if hasattr(fact, "value") else None,
                "context_id": fact.contextID if hasattr(fact, "contextID") else None,
                "unit_id": fact.unitID if hasattr(fact, "unitID") else None,
                "decimals": fact.decimals if hasattr(fact, "decimals") else None,
                "precision": fact.precision if hasattr(fact, "precision") else None,
                "period": None,
                "entity": None,
                "unit": None,
            }

            # Get context information
            if (
                fact_info["context_id"]
                and fact_info["context_id"] in modelXbrl.contexts
            ):
                context = modelXbrl.contexts[fact_info["context_id"]]
                fact_info["period"] = (
                    str(context.period) if hasattr(context, "period") else None
                )
                fact_info["entity"] = (
                    str(context.entity) if hasattr(context, "entity") else None
                )

            # Get unit information
            if fact_info["unit_id"] and fact_info["unit_id"] in modelXbrl.units:
                unit = modelXbrl.units[fact_info["unit_id"]]
                # Fix the FutureWarning by checking length instead of truth value
                fact_info["unit"] = (
                    str(unit) if unit is not None and len(str(unit)) > 0 else None
                )

            facts_data.append(fact_info)

        return facts_data

    def analyze_xbrl_concepts(self, xbrl_results):
        """Analyze all XBRL concepts to understand what's available"""
        if not xbrl_results:
            return {}

        concept_analysis = {}

        for result in xbrl_results:
            facts = result["facts"]

            for fact in facts:
                concept = fact["concept"]
                value = fact["value"]

                if concept not in concept_analysis:
                    concept_analysis[concept] = {
                        "count": 0,
                        "sample_values": [],
                        "periods": set(),
                        "units": set(),
                    }

                concept_analysis[concept]["count"] += 1

                # Store sample values (up to 3)
                if len(concept_analysis[concept]["sample_values"]) < 3:
                    concept_analysis[concept]["sample_values"].append(str(value))

                # Track periods and units
                if fact.get("period"):
                    concept_analysis[concept]["periods"].add(str(fact["period"]))
                if fact.get("unit"):
                    concept_analysis[concept]["units"].add(str(fact["unit"]))

        return concept_analysis

    def extract_key_financial_metrics(self, xbrl_results):
        """Extract key financial metrics from XBRL facts"""
        if not xbrl_results:
            return {}

        key_metrics = {}

        # More comprehensive financial statement concepts including Apple-specific patterns
        concept_mappings = {
            # Income Statement - expanded patterns
            "Revenues": [
                "Revenues",
                "Revenue",
                "SalesRevenueNet",
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueGoodsNet",
                "SalesRevenueServicesNet",
            ],
            "NetIncome": [
                "NetIncomeLoss",
                "NetIncome",
                "ProfitLoss",
                "NetIncomeLossAvailableToCommonStockholdersBasic",
            ],
            "GrossProfit": ["GrossProfit"],
            "OperatingIncome": ["OperatingIncomeLoss", "OperatingIncome"],
            "EarningsPerShare": ["EarningsPerShareBasic", "EarningsPerShareDiluted"],
            "ResearchAndDevelopment": ["ResearchAndDevelopmentExpense"],
            "SellingGeneralAdministrative": ["SellingGeneralAndAdministrativeExpense"],
            # Balance Sheet - expanded patterns
            "TotalAssets": [
                "Assets",
                "AssetsCurrent",
                "AssetsTotal",
                "AssetsCurrent",
                "AssetsNoncurrent",
            ],
            "TotalLiabilities": [
                "Liabilities",
                "LiabilitiesAndStockholdersEquity",
                "LiabilitiesCurrent",
                "LiabilitiesNoncurrent",
            ],
            "StockholdersEquity": [
                "StockholdersEquity",
                "Equity",
                "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            ],
            "Cash": [
                "Cash",
                "CashAndCashEquivalentsAtCarryingValue",
                "CashCashEquivalentsAndShortTermInvestments",
            ],
            "TotalDebt": [
                "DebtCurrent",
                "LongTermDebt",
                "LongTermDebtCurrent",
                "LongTermDebtNoncurrent",
            ],
            "Inventory": ["InventoryNet"],
            "PropertyPlantEquipment": ["PropertyPlantAndEquipmentNet"],
            # Cash Flow - expanded patterns
            "OperatingCashFlow": [
                "NetCashProvidedByUsedInOperatingActivities",
                "CashProvidedByUsedInOperatingActivities",
            ],
            "InvestingCashFlow": ["NetCashProvidedByUsedInInvestingActivities"],
            "FinancingCashFlow": ["NetCashProvidedByUsedInFinancingActivities"],
            "CapitalExpenditures": [
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "CapitalExpendituresIncurredButNotYetPaid",
            ],
            "FreeCashFlow": ["FreeCashFlow"],
            # Share information
            "SharesOutstanding": [
                "CommonStockSharesOutstanding",
                "WeightedAverageNumberOfSharesOutstandingBasic",
            ],
            "SharesIssued": ["CommonStockSharesIssued"],
        }

        # First, let's see what concepts are actually available
        print("\n=== ANALYZING AVAILABLE XBRL CONCEPTS ===")
        concept_analysis = self.analyze_xbrl_concepts(xbrl_results)

        # Show concepts that might be financial metrics (contain numeric values)
        numeric_concepts = []
        for concept, data in concept_analysis.items():
            # Check if any sample values are numeric
            has_numeric = False
            for sample in data["sample_values"]:
                try:
                    float(sample)
                    has_numeric = True
                    break
                except (ValueError, TypeError):
                    continue

            if has_numeric:
                numeric_concepts.append((concept, data))

        print(f"Found {len(numeric_concepts)} concepts with numeric values")

        # Show top 20 numeric concepts by frequency
        numeric_concepts.sort(key=lambda x: x[1]["count"], reverse=True)
        print("\nTop 20 numeric concepts:")
        for i, (concept, data) in enumerate(numeric_concepts[:20]):
            print(
                f"{i + 1:2d}. {concept} (count: {data['count']}, sample: {data['sample_values'][0] if data['sample_values'] else 'N/A'})"
            )

        # Now try to match concepts
        for result in xbrl_results:
            facts = result["facts"]

            for fact in facts:
                concept = fact["concept"]
                value = fact["value"]
                period = fact["period"]

                # Skip if no value or not a number
                if value is None:
                    continue

                try:
                    numeric_value = float(value)
                except (ValueError, TypeError):
                    continue

                # Check if this concept matches any of our key metrics
                for metric_name, concept_variations in concept_mappings.items():
                    for variation in concept_variations:
                        if variation.lower() in concept.lower():
                            if metric_name not in key_metrics:
                                key_metrics[metric_name] = []

                            key_metrics[metric_name].append(
                                {
                                    "value": numeric_value,
                                    "period": period,
                                    "concept": concept,
                                    "unit": fact.get("unit"),
                                }
                            )
                            break

    def find_largest_financial_values(self, xbrl_results, top_n=20):
        """Find the largest financial values to identify key metrics"""
        if not xbrl_results:
            return []

        all_values = []

        for result in xbrl_results:
            facts = result["facts"]

            for fact in facts:
                concept = fact["concept"]
                value = fact["value"]
                period = fact["period"]
                unit = fact.get("unit")

                # Skip if no value or not a number
                if value is None:
                    continue

                try:
                    numeric_value = float(value)
                    # Only consider large values (> 1 million) to focus on key metrics
                    if abs(numeric_value) > 1000000:
                        all_values.append(
                            {
                                "concept": concept,
                                "value": numeric_value,
                                "period": period,
                                "unit": unit,
                                "abs_value": abs(numeric_value),
                            }
                        )
                except (ValueError, TypeError):
                    continue

        # Sort by absolute value (largest first)
        all_values.sort(key=lambda x: x["abs_value"], reverse=True)

        return all_values[:top_n]

    def print_concept_analysis(self, xbrl_results):
        """Print detailed analysis of XBRL concepts"""
        print("\n=== DETAILED XBRL CONCEPT ANALYSIS ===")

        # Show largest values
        largest_values = self.find_largest_financial_values(xbrl_results, top_n=15)

        print("\nLargest Financial Values (likely key metrics):")
        for i, item in enumerate(largest_values, 1):
            value = item["value"]
            concept = item["concept"]
            period = item["period"]
            unit = item.get("unit", "")

            # Format value
            if abs(value) >= 1e9:
                formatted_value = f"${value / 1e9:.2f}B"
            elif abs(value) >= 1e6:
                formatted_value = f"${value / 1e6:.2f}M"
            else:
                formatted_value = f"${value:,.0f}"

            print(f"{i:2d}. {concept}")
            print(f"    Value: {formatted_value} {unit}")
            print(f"    Period: {period}")
            print()

    def extract_apple_specific_metrics(self, xbrl_results):
        """Extract metrics using Apple's specific XBRL concept names"""
        if not xbrl_results:
            return {}

        # First, let's identify Apple's actual concept names
        concept_analysis = self.analyze_xbrl_concepts(xbrl_results)

        # Look for Apple-specific patterns based on common naming
        apple_metrics = {}

        # Keywords that often appear in Apple's financial concepts
        revenue_keywords = ["revenue", "sales", "net sales"]
        income_keywords = ["income", "earnings", "profit"]
        asset_keywords = ["assets", "total assets"]
        cash_keywords = ["cash", "equivalents"]

        for result in xbrl_results:
            facts = result["facts"]

            for fact in facts:
                concept = fact["concept"].lower()
                value = fact["value"]
                period = fact["period"]

                if value is None:
                    continue

                try:
                    numeric_value = float(value)
                    # Only consider significant values
                    if abs(numeric_value) < 1000000:
                        continue
                except (ValueError, TypeError):
                    continue

                # Categorize based on concept name
                original_concept = fact["concept"]

                if any(keyword in concept for keyword in revenue_keywords):
                    if "Revenue" not in apple_metrics:
                        apple_metrics["Revenue"] = []
                    apple_metrics["Revenue"].append(
                        {
                            "value": numeric_value,
                            "period": period,
                            "concept": original_concept,
                            "unit": fact.get("unit"),
                        }
                    )

                elif (
                    any(keyword in concept for keyword in income_keywords)
                    and "loss" not in concept
                ):
                    if "Net Income" not in apple_metrics:
                        apple_metrics["Net Income"] = []
                    apple_metrics["Net Income"].append(
                        {
                            "value": numeric_value,
                            "period": period,
                            "concept": original_concept,
                            "unit": fact.get("unit"),
                        }
                    )

                elif any(keyword in concept for keyword in asset_keywords):
                    if "Total Assets" not in apple_metrics:
                        apple_metrics["Total Assets"] = []
                    apple_metrics["Total Assets"].append(
                        {
                            "value": numeric_value,
                            "period": period,
                            "concept": original_concept,
                            "unit": fact.get("unit"),
                        }
                    )

                elif any(keyword in concept for keyword in cash_keywords):
                    if "Cash" not in apple_metrics:
                        apple_metrics["Cash"] = []
                    apple_metrics["Cash"].append(
                        {
                            "value": numeric_value,
                            "period": period,
                            "concept": original_concept,
                            "unit": fact.get("unit"),
                        }
                    )

        return apple_metrics

    def print_financial_summary(self, key_metrics):
        """Print a summary of key financial metrics"""
        if not key_metrics:
            print("No key financial metrics found.")
            return

        print("\n=== KEY FINANCIAL METRICS SUMMARY ===")

        for metric_name, metric_data in key_metrics.items():
            print(f"\n{metric_name}:")

            # Sort by period (most recent first if possible)
            metric_data.sort(key=lambda x: str(x["period"]), reverse=True)

            # Show up to 3 most recent values
            for item in metric_data[:3]:
                value = item["value"]
                period = item["period"]
                unit = item.get("unit", "")

                # Format large numbers
                if abs(value) >= 1e9:
                    formatted_value = f"${value / 1e9:.2f}B"
                elif abs(value) >= 1e6:
                    formatted_value = f"${value / 1e6:.2f}M"
                elif abs(value) >= 1e3:
                    formatted_value = f"${value / 1e3:.2f}K"
                else:
                    formatted_value = f"${value:.2f}"

                print(f"  {period}: {formatted_value} {unit}")

    def parse_10k_sections(self):
        """Extract specific sections from 10-K filing"""
        main_doc = self.get_main_document()
        if not main_doc:
            return {}

        content = main_doc["content"]

        # 10-K section patterns
        section_patterns = {
            "Business": r"Item\s+1\.\s*Business(.*?)(?=Item\s+1A|Item\s+2|$)",
            "Risk_Factors": r"Item\s+1A\.\s*Risk\s+Factors(.*?)(?=Item\s+1B|Item\s+2|$)",
            "Properties": r"Item\s+2\.\s*Properties(.*?)(?=Item\s+3|$)",
            "Legal_Proceedings": r"Item\s+3\.\s*Legal\s+Proceedings(.*?)(?=Item\s+4|$)",
            "MD_A": r"Item\s+7\.\s*Management['\u2019]?s\s+Discussion\s+and\s+Analysis(.*?)(?=Item\s+7A|Item\s+8|$)",
            "Financial_Statements": r"Item\s+8\.\s*Financial\s+Statements(.*?)(?=Item\s+9|$)",
        }

        extracted_sections = {}
        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                section_content = match.group(1).strip()
                extracted_sections[section_name] = {
                    "content": section_content[:5000],  # First 5000 chars
                    "full_length": len(section_content),
                }

        return extracted_sections

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
    doc_type = "10-K"

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

    if len(txt_files) == 0:
        print("no txt files")
        exit()
    if len(txt_files) > 1:
        print("too many txt files")
        exit()

    file_path = os.path.join(filing_path, txt_files[0])
    print(f"Processing file: {file_path}")

    parser = SECSubmissionParser(file_path)

    # Print summary
    parser.print_summary()

    # Extract 10-K sections
    print("\n=== EXTRACTING 10-K SECTIONS ===")
    sections = parser.parse_10k_sections()

    if sections:
        for section_name, section_data in sections.items():
            print(f"\n{section_name.replace('_', ' ').title()}:")
            print(f"  Full length: {section_data['full_length']:,} characters")
            print(f"  Preview: {section_data['content'][:200]}...")
    else:
        print("No standard 10-K sections found.")

    # Try to extract XBRL facts (focus on main document only)
    print("\n=== ATTEMPTING XBRL EXTRACTION ===")
    xbrl_results = parser.parse_xbrl_from_documents()

    if xbrl_results:
        print(f"Successfully extracted XBRL data from {len(xbrl_results)} documents")

        # First, do detailed concept analysis
        parser.print_concept_analysis(xbrl_results)

        # Try to extract key financial metrics using generic patterns
        print("\n=== ATTEMPTING GENERIC FINANCIAL METRICS EXTRACTION ===")
        key_metrics = parser.extract_key_financial_metrics(xbrl_results)

        if key_metrics:
            parser.print_financial_summary(key_metrics)
        else:
            print("No metrics found with generic patterns.")

        # Try Apple-specific extraction
        print("\n=== ATTEMPTING APPLE-SPECIFIC METRICS EXTRACTION ===")
        apple_metrics = parser.extract_apple_specific_metrics(xbrl_results)

        if apple_metrics:
            print("Found Apple-specific metrics:")
            parser.print_financial_summary(apple_metrics)
        else:
            print("No Apple-specific metrics found.")

        # Save detailed facts to JSON for further analysis
        with open("xbrl_facts_detailed.json", "w") as f:
            json.dump(xbrl_results, f, indent=2, default=str)
        print(f"\nDetailed XBRL facts saved to xbrl_facts_detailed.json")

    else:
        print("No XBRL data found.")

    # Save key documents
    print(f"\n=== SAVING KEY DOCUMENTS ===")
    main_doc = parser.get_main_document()
    if main_doc:
        with open("10k_main_document.txt", "w", encoding="utf-8") as f:
            f.write(main_doc["content"])
        print("Saved main 10-K document to 10k_main_document.txt")
