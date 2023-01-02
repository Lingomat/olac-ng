from os.path import join
from lxml import etree

XMLParser = etree.XMLParser(remove_blank_text=True,
                            recover=True, resolve_entities=False)

def getxml(filename: str):
    with open(join('testdata', filename), 'rb') as f:
        xmlbytes = f.read()
    return etree.fromstring(xmlbytes, parser=XMLParser)
