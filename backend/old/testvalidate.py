import os
from urllib.request import pathname2url
from lxml import etree



# https://stackoverflow.com/questions/55615382/lxml-include-relative-path
# catalog_path = f"file:{pathname2url(os.path.join(os.getcwd(), 'catalog.xml'))}"
# print('setting catalog to', catalog_path)
# os.environ['XML_CATALOG_FILES'] = catalog_path


class TestResolver(etree.Resolver):
    def __init__(self):
        print('resolver active')

    def resolve(self, url, pubid, context):
        print('trying to resolve')
        print(url, pubid, context)
        basefn = os.path.basename(url)
        basefnpath = os.path.join(os.getcwd(), 'xsd', basefn)
        locals = ['static-repository.xsd', 'OLAC-PMH.xsd', 'olac.xsd', 'dc.xsd',
                  'olac-discourse-type.xsd', 'olac-extension.xsd', 'olac-language.xsd', 'olac-linguistic-field.xsd', 'olac-linguistic-type.xsd', 'olac-role.xsd', 'olac-archive.xsd', 'oai-identifier.xsd']
        if (basefn in locals) and os.path.exists(basefnpath):
            fname = os.path.join(os.getcwd(), 'xsd', os.path.basename(url))
            print('mapping to', fname)
            with open(fname, 'r') as fp:
                xstring = fp.read()
            return self.resolve_string(xstring, context)
        else:
            return None

XMLParser = etree.XMLParser(remove_blank_text=True)
XMLParser.resolvers.add(TestResolver())
print('parsing testolacschema')
schemadoc = etree.parse('testolacschema.xsd', parser=XMLParser)
print('making a schema')
SRSchema = etree.XMLSchema(schemadoc)
xml = etree.parse('test_sr.xml', parser=XMLParser)
print(SRSchema.validate(xml))
print(SRSchema.error_log.filter_from_errors())


