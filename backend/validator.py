from database import OLACDatabase, CustomSchemaLoc
import xmlschema
from filestore import FileStore

schemadir = "xsd"
locmap = {
    "http://www.openarchives.org/OAI/2.0/static-repository": "static-repository.xsd",
    "http://www.language-archives.org/OLAC/1.1/": "olac.xsd",
    "http://purl.org/dc/elements/1.1/": "dc.xsd",
    "http://purl.org/dc/terms/": "dcterms.xsd",
    "http://www.openarchives.org/OAI/2.0/": "OAI-PMH.xsd",
    "http://www.openarchives.org/OAI/2.0/oai-identifier": "oai-identifier.xsd",
    "http://www.language-archives.org/OLAC/1.1/olac-archive": "olac-archive.xsd"
}

fileStore = FileStore('filestore/')

# This class  validates static archives.


class OLACValidator():
    def __init__(self, db: OLACDatabase, id: str):
        self.db = db
        self.id = id
        self.archive = db.getArchive(id)
        if self.archive == None:
            raise Exception("No such archive")

    def _validateFile(self, schema: xmlschema.XMLSchema, filename: str) -> None | str:
        xml = fileStore.getFile(self.id, filename)
        if xml is None:
            raise Exception("Validator: No XML file found!", self.id, filename)
        try:
            schema.validate(xml)
        except Exception as e:
            return str(e)
        else:
            print("- validated", filename)
            return None

    def validate(self) -> bool:
        fetchStatus = self.db.getFetchStatus(self.id)
        assert fetchStatus is not None  # because we ran the fetcher first
        if fetchStatus['validatorPreReqs'] == False:
            print("! validatorPreReqs unmet, not validating")
            return False
        schema = xmlschema.XMLSchema(
            'srschemas.xsd', base_url=schemadir, build=False, locations=locmap)
        assert self.archive is not None
        try:
            for customschema in self.archive['customSchemas']:
                schemadata = self.db.getCustomSchema(customschema['namespace'])
                assert schemadata is not None
                _ = schema.add_schema(source=schemadata['schema'].decode('utf-8'), namespace=customschema['namespace'], build=False)
        except xmlschema.validators.exceptions.XMLSchemaParseError as e:
            self.db.updateFetchStatus(self.id, {
                'validated': False,
                'validateErrors': [
                    {
                        'baseURL': self.archive['baseURL'],
                        'error': str(e)
                    }
                ]
            })
            return False
        schema.build()
        validateErrors = []

        if self.archive['type'] == "static":
            valresult = self._validateFile(schema, self.archive['baseURL'])
            if valresult is not None:
                validateErrors.append({
                    'baseURL': self.archive['baseURL'],
                    'error': valresult
                })
        elif self.archive['type'] == "dynamic":
            pagecount = fetchStatus['pages']
            if type(pagecount) is not int:
                print("Validator: pagecount is not an integer!")
                return False
            for p in range(0, pagecount):
                filename = 'listrecords' + str(p) + '.xml'
                valresult = self._validateFile(schema, filename)
                if valresult is not None:
                    validateErrors.append({
                        'baseURL': filename,
                        'error': valresult
                    })
        if len(validateErrors) > 0:
            self.db.updateFetchStatus(self.id, {
                'validated': False,
                'validateErrors': validateErrors
            })
            return False
        else:
            self.db.updateFetchStatus(self.id, {
                'validated': True,
                'validateErrors': []
            })
            return True
