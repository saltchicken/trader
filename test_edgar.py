# from edgar import *
# set_identity("john.eicher89@gmail.com")  # Required by SEC
#
# # Method 1: Search for SC 13 filings by company
# company = Company("AAPL")  # Example: Apple
# filings = company.get_filings(form="SC 13")  # Get all SC 13 filings
#
# # Method 2: Search more broadly for SC 13 filings
# filings = get_filings(form="SC 13")
#
# # Get a specific filing
# filing = filings[0]  # Get the most recent filing
#
# # Convert to structured data object
# sc13_data = filing.obj()
#
# # Access reporting party information
# # The exact method will depend on the specific SC 13 variant (SC 13D, SC 13G, etc.)
# print(f"Filing form: {filing.form}")
# print(f"Filing date: {filing.filing_date}")
# print(f"Company: {filing.company}")
#
# # Extract text content for parsing
# text_content = filing.text()
#
# For more detailed parsing, you might need to access specific sections
#
## -*- coding: utf-8 -*-
"""

SEC Filing Scraper
@author: AdamGetbags

"""

# import modules
import requests
import pandas as pd
# pd.set_option("display.max_rows", None)      # Show all rows
# pd.set_option("display.max_columns", None)   # Show all columns
# pd.set_option("display.width", None)         # Don't wrap lines
# pd.set_option("display.max_colwidth", None)  # Show full column contents

# create request header
headers = {'User-Agent': "john.eicher89@gmail.com"}


# get all companies data
companyTickers = requests.get(
    "https://www.sec.gov/files/company_tickers.json",
    headers=headers
    )

# review response / keys
# print(companyTickers.json().keys())

# format response to dictionary and get first key/value
firstEntry = companyTickers.json()['0']

# parse CIK // without leading zeros
directCik = companyTickers.json()['0']['cik_str']

# dictionary to dataframe
companyData = pd.DataFrame.from_dict(companyTickers.json(),
                                     orient='index')

# add leading zeros to CIK
companyData['cik_str'] = companyData['cik_str'].astype(
                           str).str.zfill(10)

# review data
# print(companyData[:1])

cik = companyData[0:1].cik_str[0]
print("XXXXXXXXXX")
print(cik)

# get company specific filing metadata
filingMetadata = requests.get(
    f'https://data.sec.gov/submissions/CIK{cik}.json',
    headers=headers
    )

# review json 
# print(filingMetadata.json().keys())
filingMetadata.json()['filings']
filingMetadata.json()['filings'].keys()
filingMetadata.json()['filings']['recent']
filingMetadata.json()['filings']['recent'].keys()

# dictionary to dataframe
allForms = pd.DataFrame.from_dict(
             filingMetadata.json()['filings']['recent']
             )

# review columns
allForms.columns
allForms[['accessionNumber', 'reportDate', 'form']].head(50)
# print(allForms['form'])
filtered_forms = allForms[allForms['form'].str.contains(r'(SCHEDULE 13|SC 13)', case=False, na=False)]
print(filtered_forms.iloc[0])
# print(filtered_forms.iloc[11])
# print(allForms.columns)

# 10-Q metadata
# result = allForms.iloc[11]['primaryDocument']
# print(result)

# get company facts data
companyFacts = requests.get(
    f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json',
    headers=headers
    )

#review data
companyFacts.json().keys()
companyFacts.json()['facts']
companyFacts.json()['facts'].keys()

# filing metadata
companyFacts.json()['facts']['dei'][
    'EntityCommonStockSharesOutstanding']
companyFacts.json()['facts']['dei'][
    'EntityCommonStockSharesOutstanding'].keys()
companyFacts.json()['facts']['dei'][
    'EntityCommonStockSharesOutstanding']['units']
companyFacts.json()['facts']['dei'][
    'EntityCommonStockSharesOutstanding']['units']['shares']
companyFacts.json()['facts']['dei'][
    'EntityCommonStockSharesOutstanding']['units']['shares'][0]

# concept data // financial statement line items
companyFacts.json()['facts']['us-gaap']
companyFacts.json()['facts']['us-gaap'].keys()

# different amounts of data available per concept
# companyFacts.json()['facts']['us-gaap']['AccountsPayable']
# companyFacts.json()['facts']['us-gaap']['Revenues']
# companyFacts.json()['facts']['us-gaap']['Assets']

# get company concept data
companyConcept = requests.get(
    (
    f'https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}'
     f'/us-gaap/Assets.json'
    ),
    headers=headers
    )

# review data
companyConcept.json().keys()
companyConcept.json()['units']
companyConcept.json()['units'].keys()
companyConcept.json()['units']['USD']
companyConcept.json()['units']['USD'][0]

# parse assets from single filing
companyConcept.json()['units']['USD'][0]['val']

# get all filings data 
assetsData = pd.DataFrame.from_dict((
               companyConcept.json()['units']['USD']))

# review data

assetsData.form

# get assets from 10Q forms and reset index
assets10Q = assetsData[assetsData.form == '10-Q']
assets10Q = assets10Q.reset_index(drop=True)

# plot 
assets10Q.plot(x='end', y='val')

# SC 13 filings typically contain reporting party info in structured format
