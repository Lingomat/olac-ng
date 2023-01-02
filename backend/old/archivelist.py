from lxml import etree
from typing import TypedDict

class OLACArchive(TypedDict):
    id: str
    baseURL: str
    dateApproved: str

def getArchives() -> list[OLACArchive]:
    parser = etree.XMLParser(dtd_validation=False, ns_clean=True)
    tree = etree.parse("archive_list.php.xml", parser)
    archivetree = tree.getroot() 
    archivelist = []
    for archiveelement in archivetree:
        archive = {
            "id": archiveelement.attrib["id"],
            "baseURL": archiveelement.attrib["baseURL"],
            "dateApproved": archiveelement.attrib["dateApproved"]
        }
        archivelist.append(archive)
    return archivelist

