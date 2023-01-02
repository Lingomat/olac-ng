import xmlschema
import os
from urllib.request import pathname2url

#https://stackoverflow.com/questions/55615382/lxml-include-relative-path
# catalog_path = f"file:{pathname2url(os.path.join(os.getcwd(), 'catalog.xml'))}"
# print('setting catalog to', catalog_path)
# os.environ['XML_CATALOG_FILES'] = catalog_path

print('importing xsd/srschemas')
locmap = {
    "http://www.openarchives.org/OAI/2.0/static-repository": "static-repository.xsd",
    "http://www.language-archives.org/OLAC/1.1/": "olac.xsd",
    "http://purl.org/dc/elements/1.1/": "dc.xsd",
    "http://purl.org/dc/terms/": "dcterms.xsd",
    "http://www.openarchives.org/OAI/2.0/": "OAI-PMH.xsd",
    "http://www.openarchives.org/OAI/2.0/oai-identifier": "oai-identifier.xsd",
    "http://www.language-archives.org/OLAC/1.1/olac-archive": "olac-archive.xsd"
}
schema = xmlschema.XMLSchema('srschemas.xsd', base_url = 'xsd', build=False, locations=locmap)
print('importing childes')
_ = schema.add_schema('childes.xsd')
print('building')
schema.build()
schema.validate('testdata/test_sr.xml')


