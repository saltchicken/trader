import requests
from lxml import etree
from bs4 import BeautifulSoup
import pandas as pd
# pd.set_option("display.max_rows", None)      # Show all rows
# pd.set_option("display.max_columns", None)   # Show all columns
# pd.set_option("display.width", None)         # Don't wrap lines
# pd.set_option("display.max_colwidth", None)  # Show full column contents

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
# filtered_forms = allForms[allForms['form'].str.contains(r'(SCHEDULE 13|SC 13)', case=False, na=False)]
filtered_forms = allForms[allForms["primaryDocDescription"].str.contains(r'(SCHEDULE 13|SC 13)', case=False, na=False)]
# filtered_forms = allForms[allForms["primaryDocDescription"].str.contains(r'(10-K|10-Q)', case=False, na=False)]
print(filtered_forms)
# print(filtered_forms.iloc[11])
# print(allForms.columns)
form = filtered_forms.iloc[0]
accession_number = form['accessionNumber'].replace("-","")
# print(accession_number)
cik = cik
primary_document = form['primaryDocument']
# 10-Q metadata
# result = allForms.iloc[11]['primaryDocument']
# print(result)
#
url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number}/{primary_document}"
print(url)
# Download the XML content
response = requests.get(url, headers=headers)
print(response)
xml_content = response.content
# print(response.content)

# Try parsing with recovery in case of malformed XML
try:
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(xml_content, parser=parser)

    found_td = False

    for elem in root.iter():
        if not found_td:
            # Find the <td> with the target text
            if elem.tag == "td" and (elem.text and elem.text.strip() == "Names of Reporting Persons"):
                print("Found <td> with target text:", elem.text.strip())
                found_td = True
            if elem.tag == "font" and (elem.text and elem.text.strip() == "Names of Reporting Persons"):
                print("Found <font> with target text:", elem.text.strip())
                # found_td = True
        else:
            # After finding the td, look for the first <div>
            if elem.tag == "div":
                div_text = elem.text.strip() if elem.text else ''
                print("Found <div> after <td>:", div_text)
                break

    # Pretty-print all top-level tags
    # for elem in root.iter():
    #     text = elem.text.strip() if elem.text else ''
    #     # print(f"{elem.tag}: {text}")
    #     if text and text == 'Names of Reporting Persons':
    #         print("hello")

except etree.XMLSyntaxError as e:
    print("XMLSyntaxError:", e)
    print("Falling back to BeautifulSoup...")

    # Use BeautifulSoup as a fallback
    soup = BeautifulSoup(xml_content, "lxml-xml")
    # for elem in soup.find_all():
    #     text = elem.text.strip() if elem.text else ''
    #     print(f"{elem.name}: {text}")
    target_cell = soup.find('td', string=lambda t: t and 'Names of Reporting Persons' in t)

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
