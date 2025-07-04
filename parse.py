import requests
from lxml import etree
from bs4 import BeautifulSoup

# URL of the XML document
headers = {'User-Agent': "john.eicher89@gmail.com"}
url = "https://www.sec.gov/Archives/edgar/data/1045810/000104581025000103/xslSCHEDULE_13G_X01/primary_doc.xml"

# Download the XML content
response = requests.get(url, headers=headers)
xml_content = response.content

# Try parsing with recovery in case of malformed XML
try:
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(xml_content, parser=parser)

    found_td = False

    for elem in root.iter():
        if not found_td:
            # Find the <td> with the target text
            if elem.tag == "td" and (elem.text and elem.text.strip() == "Names of Reporting Persons"):
                found_td = True
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

    # if target_cell:
    #     # Look for the next <td> or sibling that holds the value
    #     value_cell = target_cell.find_next('td')
    #     if value_cell:
    #         print("Names of Reporting Persons:", value_cell.text.strip())
    #     else:
    #         print("Value cell not found.")
    # else:
    #     print("Label <td> not found.")
