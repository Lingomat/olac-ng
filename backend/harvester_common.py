from requests_cache import CachedSession, disabled
import requests
from datetime import datetime, timedelta, timezone
from lxml import etree
import logging
from database import OLACDatabase, XMLArchive, CustomSchemaLoc, FetchStatus
from more_itertools import chunked
from typing import cast, Any
from filestore import FileStore
import xmltodict
from time import sleep
from util import XMLDateToDatetime

logging.basicConfig(filename='testoutputs/oaipmh.log',
                    encoding='utf-8', level=logging.DEBUG)

OAISchema: etree.XMLSchema = etree.XMLSchema(file='xsd/oaiolacschemas.xsd')
localNS = ['http://www.openarchives.org/OAI/2.0/static-repository',
           'http://www.language-archives.org/OLAC/1.1/', 'http://purl.org/dc/elements/1.1/', 'http://purl.org/dc/terms/']


maximumAge = timedelta(days=7)
backoffTime = timedelta(hours=2)
badCacheActors = ['sil.org']

class OLACHarvester():
    def __init__(self, db: OLACDatabase, archive: XMLArchive):
        self.session = CachedSession(
            'demo_cache',
            use_cache_dir=True,                # Save files in the default user cache dir
            # Cache POST requests to avoid sending the same data twice
            allowable_methods=['GET', 'POST'],
            # In case of request errors, don't use stale cache data
            stale_if_error=True
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

    def _shouldHarvest(self) -> bool:
        fetchStatus = self.db.getFetchStatus(self.identifier)
        # If there is no record of a fetch, we should fetch
        if fetchStatus == None:
            print('- fetching because there is no record of a fetch')
            #self.db.storeFetchStatus(self.identifier, archivetype)
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
        except requests.exceptions.RequestException as e:
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
            namespace = 'http://www.openarchives.org/OAI/2.0/static-repository'
        elif xml.tag.endswith('OAI-PMH'):
            archivetype = 'dynamic'
            namespace = 'http://www.openarchives.org/OAI/2.0/'
        else:
            raise Exception('Not a static or dynamic repository')
        lmdate: datetime = self._getDateFromHeaders(http_response.headers)
        xmlelement = etree.fromstring(xmlcontent, parser=self.XMLParser)
        customNamespaces = self._getCustomNamespacesFromXMLElement(xmlelement)
        identify = xmlelement.find('.//{'+namespace+'}Identify')
        if identify == None:
            raise requests.exceptions.HTTPError('No Identify element found')
        namespaces = {
            'http://www.openarchives.org/OAI/2.0/': 'oai',
        }
        identifydict = xmltodict.parse(etree.tostring(identify), process_namespaces=True, namespaces=namespaces)
        identifykey: str | None = None
        for key in identifydict.keys():
            if key.endswith('Identify'):
                identifykey = key
                break
        if identifykey == None:
            print('identifydict', identifydict)
            raise requests.exceptions.HTTPError('No Identify element found')
        identifyobj = identifydict[identifykey]
        self._junkMetadata(identifyobj)
        return (archivetype, xmlelement, lmdate, customNamespaces, identifyobj)

    def harvest(self, force: bool = False) -> FetchStatus | None:
        print('*** harvesting ', self.baseurl)
        shouldHarvest = self._shouldHarvest() # Run this always because it initialises fetchStatus
        if force or shouldHarvest:
            self._executeHarvest()
        return self.db.getFetchStatus(self.identifier)
    
    def _executeHarvest(self):
        try:
            archivetype, xmlE, lmdate, cschemas, identify = self._fetchIdentify()
        except Exception as e:
            print('!!! identify failed', e)
            fstatus = self.db.getFetchStatus(self.identifier)
            if fstatus == None:
                self.db.storeFetchStatus(self.identifier, 'unknown', 'failed', datetime.utcnow().replace(microsecond=0), str(e))
            else: 
                self.db.updateFetchStatus(self.identifier, {
                    'status': 'failed',
                    'retryAttempt': fstatus['retryAttempt'] + 1,
                    'lastFetch': datetime.utcnow().replace(microsecond=0),
                    'lastError': str(e)
                })
            return
        print('- identify succeeded - archive type is', archivetype)
        fstatus = self.db.getFetchStatus(self.identifier)
        if fstatus == None:
            self.db.storeFetchStatus(self.identifier, 'archivetype')
        if archivetype == 'static':
            records = self._recordHarvestStatic(xmlE, identify)
            self.db.storeArchive(self.identifier, self.baseurl,
                                'static', lmdate, identify, cschemas)
            self.db.storeRecords(self.identifier, records)
            self.fileStore.storeFile(self.identifier, self.baseurl, etree.tostring(xmlE, pretty_print=True, encoding='utf-8'))
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
        elif archivetype == 'dynamic':
            self.db.storeArchive(self.identifier, self.baseurl, 'dynamic', lmdate, identify, cschemas)
            try:
                xmllist, records = self._recordHarvestDynamic()
            except requests.exceptions.RequestException as e:
                print('!!! listRecords failed', e)
                fstatus = self.db.getFetchStatus(self.identifier)
                self.db.updateFetchStatus(self.identifier, {
                    'status': 'failed',
                    'retryAttempt': 0,
                    'lastFetch': datetime.utcnow().replace(microsecond=0),
                    'lastError': str(e)
                })
                return
            print('- listRecords succeeded with', len(records), 'records')
            if len(records) > 0:
                self.db.storeRecords(self.identifier, records)
            else:
                print('- no records to store!')
            for i in range(0, len(xmllist)):
                self.fileStore.storeFile(self.identifier, 'listrecords'+str(i)+'.xml', xmllist[i])

            self.db.updateFetchStatus(self.identifier, {
                'status': 'success',
                'pages': len(xmllist),
                'retryAttempt': 0,
                'lastFetch': datetime.utcnow().replace(microsecond=0),
                'lastError': None
            })
        # Attempt to fetch custom schemas - if successful update the fetch status
        self._fetchCustomSchemas(cschemas)

    
    def _recordHarvestStatic(self, xmlElement: etree._Element, identify: dict[str, Any]) -> list[dict]:
        for field in identify['oai:description']:
            self._junkMetadata(field)
        records = xmlElement.findall(
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
            datestamp = XMLDateToDatetime(recdict['record']['header']['datestamp'])
            metadata = recdict['record']['metadata']['olac:olac']
            if metadata == None:
                print('!!! wtf, no olac metadata?', recdict)
                continue
            recorddate = XMLDateToDatetime(metadata['dc:date']) if 'dc:date' in metadata else None
            self._junkMetadata(metadata)
            recordslist.append({
                'identifier': recdict['record']['header']['identifier'],
                'datestamp': datestamp,
                'metadata': metadata,
                'recorddate': recorddate
            })
        return recordslist
    

       
    def _recordHarvestDynamic(self) -> tuple[list[bytes],list[dict]]:
        recordslist: list[dict] = []
        xmlcontentlist: list[bytes] = []
        resumptionToken = None
        # Strip these namespaces from the dict keys (passed to xmltodict)
        namespaces = {
            'http://www.openarchives.org/OAI/2.0/': None,
            'http://purl.org/dc/elements/1.1/': 'dc',
            'http://purl.org/dc/terms/': 'dcterms',
            'http://www.language-archives.org/OLAC/1.1/': 'olac',
            'http://www.language-archives.org/OLAC/1.0/': 'olac'
        }
        while True:
            payload = {'verb': 'ListRecords'}
            # List records sends metadata prefix once, then resumption token
            if resumptionToken == None:
                payload['metadataPrefix'] = 'olac'
            else: 
                payload['resumptionToken'] = resumptionToken
            print('- fetching', self.identifier, '-', self.baseurl, 'with', payload)
            if self.identifier in badCacheActors:
                print('! bypassing cache for', self.identifier)
                with disabled():
                    http_response = requests.get(self.baseurl, params=payload)
            else: 
                http_response = self.session.get(self.baseurl, params=payload)
            if http_response.status_code >=400:
                print('!!!', http_response.status_code, http_response.text)
            http_response.raise_for_status()
            xmlcontent: bytes = http_response.content
            #print(xmlcontent)
            xmlelement = etree.fromstring(xmlcontent, parser=self.XMLParser)
            errorelement = xmlelement.find('.//{http://www.openarchives.org/OAI/2.0/}error')
            if errorelement != None:
                print('!!!', errorelement.text)
                raise requests.exceptions.HTTPError(errorelement.text)
            xmlcontentlist.append(etree.tostring(xmlelement, pretty_print=True, encoding='utf-8'))
            if xmlcontent.find(b'OAI-PMH') == -1:
                raise requests.exceptions.HTTPError('Not an OAI-PMH repository')
            xmlelement = etree.fromstring(xmlcontent, parser=self.XMLParser)
            records = xmlelement.findall(
                './/{http://www.openarchives.org/OAI/2.0/}record')
            for record in records:
                recdict = xmltodict.parse(etree.tostring(record), process_namespaces=True, namespaces=namespaces)
                datestamp = XMLDateToDatetime(recdict['record']['header']['datestamp'])
                if 'metadata' not in recdict['record']:
                    print('!!! wtf, no olac metadata?', recdict)
                    continue
                if 'olac:olac' not in recdict['record']['metadata']:
                    print('!!! wtf, no olac:olac metadata?', recdict)
                    continue
                metadata = recdict['record']['metadata']['olac:olac']
                recorddate = XMLDateToDatetime(metadata['dc:date']) if 'dc:date' in metadata else None
                self._junkMetadata(metadata)
                recordslist.append({
                    'identifier': recdict['record']['header']['identifier'],
                    'datestamp': datestamp,
                    'metadata': metadata,
                    'recorddate': recorddate
                })
            resumptionTokenElement = xmlelement.find('.//{http://www.openarchives.org/OAI/2.0/}resumptionToken')
            print('resumptionToken', resumptionTokenElement)
            if resumptionTokenElement == None  or resumptionTokenElement.text == None:
                break
            resumptionToken = resumptionTokenElement.text
            sleep(3)

        return (xmlcontentlist, recordslist)
    

