from requests_cache import CachedSession
from requests import exceptions
from datetime import datetime, timedelta
from lxml import etree
import logging
from database import OLACDatabase, XMLArchive, CustomSchemaLoc
from lxml.etree import XMLSchema
from more_itertools import chunked
from typing import cast, Any
from filestore import FileStore
import xmltodict

logging.basicConfig(filename='testoutputs/oaipmh.log',
                    encoding='utf-8', level=logging.DEBUG)

OAISchema: XMLSchema = etree.XMLSchema(file='xsd/oaiolacschemas.xsd')
localNS = ['http://www.openarchives.org/OAI/2.0/static-repository',
           'http://www.language-archives.org/OLAC/1.1/', 'http://purl.org/dc/elements/1.1/', 'http://purl.org/dc/terms/']


maximumAge = timedelta(days=7)
backoffTime = timedelta(hours=2)


class OLACBase():
    def __init__(self, db: OLACDatabase, archive: XMLArchive):
        self.session = CachedSession(
            'demo_cache',
            use_cache_dir=True,                # Save files in the default user cache dir
            # Cache POST requests to avoid sending the same data twice
            allowable_methods=['GET', 'POST'],
            # In case of request errors, don't use stale cache data
            stale_if_error=False
        )
        self.db = db
        self.fileStore = FileStore('filestore/')
        self.baseurl = archive['baseURL']
        self.identifier = archive['id']
        self.XMLParser = etree.XMLParser(encoding='utf-8', remove_blank_text=True,
                                         recover=True, resolve_entities=False)
        self.stockNamespaces = ["http://www.openarchives.org/OAI/2.0/static-repository", "http://www.language-archives.org/OLAC/1.1/", "http://purl.org/dc/elements/1.1/",
                                "http://purl.org/dc/terms/",
                                "http://www.openarchives.org/OAI/2.0/",
                                "http://www.openarchives.org/OAI/2.0/oai-identifier",
                                "http://www.language-archives.org/OLAC/1.1/olac-archive"]

    def _shouldHarvest(self, archivetype: str) -> bool:
        fetchStatus = self.db.getFetchStatus(self.identifier)
        # If there is no record of a fetch, we should fetch
        if fetchStatus == None:
            print('- fetching because there is no record of a fetch')
            self.db.storeFetchStatus(self.identifier, archivetype)
            return True
        # If there is a record but no lastFetch, we should fetch (this shouldn't happen)
        if fetchStatus['lastFetch'] == None:
            print('- fetching because there is a record but no lastFetch')
            return True
        # Now it gets more complicated. Work out age of record of last fetch
        ageOfFetch = (datetime.utcnow() - fetchStatus['lastFetch'])
        print('- age of last fetch:', ageOfFetch)
        # If the last fetch failed, we should fetch if the age of the record of the last fetch exceeds the backoff retry window
        if fetchStatus['status'] == 'failed':
            backoffval = backoffTime * (fetchStatus['retryAttempt'] ** 2)
            print('- previous fetch failed, backoffval:', backoffval,
                  'retryAttempt:', fetchStatus['retryAttempt'])
            if (ageOfFetch < backoffval):
                print(
                    '- skipping because failed fetch is within backoff retry window')
                return False
            else:
                print(
                    '- fetching because age of record of failed fetch exceeds backoff retry window')
                return True
        # If the last fetch succeeded, we should fetch if the age of the record of the last fetch exceeds the maximum age
        if ageOfFetch > maximumAge:
            print('- fetching because age of last fetch exceeds maximum age')
            return True
        else:
            print('- skipping because age of last fetch is within maximum age')
            return False

    def _getCustomNamespacesFromXMLElement(self, element: etree._Element) -> list[CustomSchemaLoc]:
        xsi = element.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"]
        schemapairs = cast(list[str], xsi.split())
        schemapairs = list(chunked(schemapairs, 2))
        customNamespaces: list[CustomSchemaLoc] = [
            {"namespace": pair[0], "schema": pair[1]} for pair in schemapairs if pair[0] not in self.stockNamespaces]
        return customNamespaces

    # Wed, 05 Apr 2017 20:49:48 GMT
    def _getDateFromHeaders(self, headers) -> datetime:
        if 'Last-Modified' in headers:
            tzdt = datetime.strptime(
                headers['Last-Modified'], '%a, %d %b %Y %H:%M:%S %Z')
            return tzdt
        else:
            return datetime.utcnow()

    def _junkMetadata(self, metadata: dict[str, Any]):
        #print('stripping', metadata.keys())
        for key in list(metadata.keys()):
            if key.startswith('@xmlns') or key.startswith('@xsi') or key.endswith('XMLSchema-instance:schemaLocation'):
                del metadata[key]

    def _fetchCustomSchemas(self, cschemas: list[CustomSchemaLoc]):
        try:
            for customschema in cschemas:
                if not self.db.hasCustomSchema(customschema['namespace']):
                    print('- fetching custom schema', customschema['namespace'])
                    with self.session.cache_disabled():
                        http_response = self.session.get(customschema['schema'])
                    self.db.storeCustomSchema(
                        customschema['namespace'], http_response.content)
        except exceptions.RequestException as e:
            print('! custom fetch failed', e)
        else:
            if len(cschemas) > 0:
                print('- custom schemas fetched successfully')
            self.db.updateFetchStatus(self.identifier, {
                'validatorPreReqs': True
            })

    def _fetchIdentify(self):
        payload = {'verb': 'Identify'}
        http_response = self.session.get(self.baseurl, params=payload)
        http_response.raise_for_status()
        xmlcontent: bytes = http_response.content
        xml = etree.fromstring(xmlcontent, self.XMLParser)
        if xml.tag.endswith('Repository'):
            archivetype = 'static'
        elif xml.tag.endswith('OAI-PMH'):
            archivetype = 'dynamic'
        else:
            raise Exception('Not a static or dynamic repository')
        lmdate: datetime = self._getDateFromHeaders(http_response.headers)
        xmlelement = etree.fromstring(xmlcontent, parser=self.XMLParser)
        customNamespaces = self._getCustomNamespacesFromXMLElement(xmlelement)
        identify = xmlelement.find('.//{http://www.openarchives.org/OAI/2.0/static-repository}Identify')
        if identify == None:
            raise exceptions.HTTPError('No Identify element found')
        namespaces = {
            'http://www.openarchives.org/OAI/2.0/': 'oai',
        }
        identifydict = xmltodict.parse(etree.tostring(identify), process_namespaces=True, namespaces=namespaces)
        identifyobj = identifydict['oai:Identify']
        self._junkMetadata(identifyobj)
        return (archivetype, xmlcontent, lmdate, customNamespaces, identifyobj)

