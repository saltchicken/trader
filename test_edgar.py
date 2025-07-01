from edgar import *
set_identity("john.eicher89@gmail.com")  # Required by SEC

# Method 1: Search for SC 13 filings by company
company = Company("AAPL")  # Example: Apple
filings = company.get_filings(form="SC 13")  # Get all SC 13 filings

# Method 2: Search more broadly for SC 13 filings
filings = get_filings(form="SC 13")

# Get a specific filing
filing = filings[0]  # Get the most recent filing

# Convert to structured data object
sc13_data = filing.obj()

# Access reporting party information
# The exact method will depend on the specific SC 13 variant (SC 13D, SC 13G, etc.)
print(f"Filing form: {filing.form}")
print(f"Filing date: {filing.filing_date}")
print(f"Company: {filing.company}")

# Extract text content for parsing
text_content = filing.text()

# For more detailed parsing, you might need to access specific sections
# SC 13 filings typically contain reporting party info in structured format
