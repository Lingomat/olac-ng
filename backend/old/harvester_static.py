from harvester_base import OLACBase
from database import OLACDatabase, XMLArchive, CustomSchemaLoc, FetchStatus
from requests import exceptions
from datetime import datetime
from lxml import etree
import xmltodict

class OLACStatic(OLACBase):
    # Harvest first assesses whether we need to fetch the archive
    def __init__(self, db: OLACDatabase, archive: XMLArchive):
        super().__init__(db, archive)

    def harvest(self, force: bool = False) -> FetchStatus | None:
        print('*** harvesting static', self.baseurl)
        shouldHarvest = self._shouldHarvest('static') # Run this always because it initialises fetchStatus
        if force or shouldHarvest:
            self._doHarvest()
        return self.db.getFetchStatus(self.identifier)

    # We need to fetch the archive
    def _doHarvest(self):
        try:
            xml, lmdate, cschemas, records, identify = self._fetch()
        except exceptions.RequestException as e:
            print('!!! fetch failed', e)
            fstatus = self.db.getFetchStatus(self.identifier)
            assert fstatus != None  # because _shouldHarvest() initializes the fetch status
            self.db.updateFetchStatus(self.identifier, {
                'status': 'failed',
                'retryAttempt': fstatus['retryAttempt'] + 1,
                'lastFetch': datetime.utcnow().replace(microsecond=0),
                'lastError': str(e)
            })
            return

        # Note we are storing the archive regardless of validation succcess.

        self.db.storeArchive(self.identifier, self.baseurl,
                             'static', lmdate, identify, cschemas)
        self.db.storeRecords(self.identifier, records)
        self.fileStore.storeFile(self.identifier, self.baseurl, xml)

        self.db.updateFetchStatus(self.identifier, {
            'status': 'success',
            'retryAttempt': 0,
            'lastFetch': datetime.utcnow().replace(microsecond=0),
            'lastError': None,
            'validated': False,
            # If there are no custom schemas, we're good to go
            'validatorPreReqs': len(cschemas) == 0,
            'validateErrors': []
        })

        # Attempt to fetch custom schemas - if successful update the fetch status
        self._fetchCustomSchemas(cschemas)


    def _fetch(self) -> tuple[bytes, datetime, list[CustomSchemaLoc], list[dict], dict]:
        http_response = self.session.get(self.baseurl)
        http_response.raise_for_status()
        xmlcontent: bytes = http_response.content
        if xmlcontent.find(b'<oai:repositoryName>') == -1:
            raise exceptions.HTTPError('Not an OAI-PMH repository')
        lmdate: datetime = self._getDateFromHeaders(http_response.headers)
        xmlelement = etree.fromstring(xmlcontent, parser=self.XMLParser)
        customNamespaces = self._getCustomNamespacesFromXMLElement(xmlelement)
        identify = xmlelement.find('.//{http://www.openarchives.org/OAI/2.0/static-repository}Identify')
        if identify == None:
            raise exceptions.HTTPError('No Identify element found')
        identifydict = xmltodict.parse(etree.tostring(identify))
        identifykey = list(identifydict.keys())[0] # This is ridiculous but xml can completely make-up the namespace prefix
        identifyobj = identifydict[identifykey]
        self._junkMetadata(identifyobj)
        #print('*** identify', identifyobj)
        for field in identifyobj['oai:description']:
            self._junkMetadata(field)
        records = xmlelement.findall(
            './/{http://www.openarchives.org/OAI/2.0/}record')
        recordslist: list[dict] = []
        # Strip these namespaces from the dict keys (passed to xmltodict)
        namespaces = {
            'http://www.openarchives.org/OAI/2.0/': None,
            'http://purl.org/dc/elements/1.1/': 'dc',
            'http://purl.org/dc/terms/': 'dcterms',
            'http://www.language-archives.org/OLAC/1.1/': 'olac',
            'http://www.language-archives.org/OLAC/1.0/': 'olac'
        }
        for record in records:
            recdict = xmltodict.parse(etree.tostring(record), process_namespaces=True, namespaces=namespaces)

            datestamp = datetime.strptime(recdict['record']['header']['datestamp'], "%Y-%m-%d")
            metadata = recdict['record']['metadata']['olac:olac']
            if metadata == None:
                print('!!! wtf, no olac metadata?', recdict)
                continue
            self._junkMetadata(metadata)
            recordslist.append({
                'identifier': recdict['record']['header']['identifier'],
                'datestamp': datestamp,
                'metadata': metadata
            })
        return (xmlcontent, lmdate, customNamespaces, recordslist, identifyobj)
    