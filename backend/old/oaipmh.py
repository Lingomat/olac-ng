from requests_cache import CachedSession
from requests import Response, exceptions
from datetime import datetime, timedelta, timezone
from lxml import etree
import xmltodict
import logging
from database import OLACDatabase, XMLArchive, CustomSchemaLoc, OLACArchive, FetchStatus
from lxml.etree import XMLSchema
from more_itertools import chunked
from typing import cast, Any
from filestore import FileStore

logging.basicConfig(filename='testoutputs/oaipmh.log',
                    encoding='utf-8', level=logging.DEBUG)
XMLParser = etree.XMLParser(remove_blank_text=True,
                            recover=True, resolve_entities=False)
OAISchema: XMLSchema = etree.XMLSchema(file='xsd/oaiolacschemas.xsd')
localNS = ['http://www.openarchives.org/OAI/2.0/static-repository',
           'http://www.language-archives.org/OLAC/1.1/', 'http://purl.org/dc/elements/1.1/', 'http://purl.org/dc/terms/']


stockNamespaces = ["http://www.openarchives.org/OAI/2.0/static-repository", "http://www.language-archives.org/OLAC/1.1/", "http://purl.org/dc/elements/1.1/",
                   "http://purl.org/dc/terms/",
                   "http://www.openarchives.org/OAI/2.0/",
                   "http://www.openarchives.org/OAI/2.0/oai-identifier",
                   "http://www.language-archives.org/OLAC/1.1/olac-archive"]

maximumAge = timedelta(days=7)
backoffTime = timedelta(hours=2)

fileStore = FileStore('filestore/')

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
        self.baseurl = archive['baseURL']
        self.identifier = archive['id']

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

    # Wed, 05 Apr 2017 20:49:48 GMT
    def _getDateFromHeaders(self, headers) -> datetime:
        if 'Last-Modified' in headers:
            tzdt = datetime.strptime(
                headers['Last-Modified'], '%a, %d %b %Y %H:%M:%S %Z')
            return tzdt
        else:
            return datetime.utcnow()

    def _junkMetadata(self, metadata: dict[str, Any]):
        # Strip out this repetitive garbage
        # for junkmeta in ['@xmlns:dc', '@xmlns:dcterms', '@xmlns:olac', '@xmlns:software', '@xsi:schemaLocation']:
        #     if junkmeta in metadata:
        #         del metadata[junkmeta]
        for key in list(metadata.keys()):
            if key.startswith('@xmlns') or key.startswith('@xsi'):
                del metadata[key]

    def _fetchCustomSchemas(self, cschemas: list[CustomSchemaLoc]):
        try:
            for customschema in cschemas:
                if not self.db.hasCustomSchema(customschema['namespace']):
                    print('- fetching custom schema', )
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


class OLACPMH(OLACBase):

    def getRecords(self, ):
        pass

    def harvest(self, force: bool = False) -> FetchStatus | None:
        print('*** harvesting dynamic', self.baseurl)
        if force or self._shouldHarvest('dynamic'):
            self._doHarvest()
        return self.db.getFetchStatus(self.identifier)

    def _doHarvest(self):
        try:
            xml, lmdate, cschemas, identify = self._identify()
        except exceptions.RequestException as e:
            print('!!! identify failed', e)
            fstatus = self.db.getFetchStatus(self.identifier)
            assert fstatus != None  # because _shouldHarvest() initializes the fetch status
            self.db.updateFetchStatus(self.identifier, {
                'status': 'failed',
                'retryAttempt': fstatus['retryAttempt'] + 1,
                'lastFetch': datetime.utcnow().replace(microsecond=0),
                'lastError': str(e)
            })
            return (None, None)
        print('- identify succeeded')
        self.db.updateFetchStatus(self.identifier, {
            'status': 'identifysucceeded',
            'retryAttempt': 0,
            'lastFetch': datetime.utcnow().replace(microsecond=0),
            'lastError': None
        })
        self.db.storeArchive(self.identifier, self.baseurl,
                             'dynamic', lmdate, identify, cschemas)
        fileStore.storeFile(self.identifier, 'identify.xml', xml)

        try:
            xml, records = self._listRecords()
        except exceptions.RequestException as e:
            print('!!! listRecords failed', e)
            self.db.updateFetchStatus(self.identifier, {
                'status': 'failed',
                'retryAttempt': 0,  # because identify worked to get this far
                'lastFetch': datetime.utcnow().replace(microsecond=0),
                'lastError': str(e)
            })
            return
        print('- listRecords succeeded with', len(records), 'records')
        if len(records) > 0:
            self.db.storeRecords(self.identifier, records)
        else:
            print('- no records to store!')
        for i in range(0, len(xml)):
            fileStore.storeFile(self.identifier, 'listrecords'+str(i)+'.xml', xml[i])

        self.db.updateFetchStatus(self.identifier, {
            'status': 'success',
            'pages': len(xml),
            'retryAttempt': 0,
            'lastFetch': datetime.utcnow().replace(microsecond=0),
            'lastError': None
        })

        # Attempt to fetch custom schemas - if successful update the fetch status
        self._fetchCustomSchemas(cschemas)

    # Returns the same as static fetch but without the records

    def _identify(self) -> tuple[bytes, datetime, list[CustomSchemaLoc], dict[str, Any]]:
        payload = {'verb': 'Identify'}
        http_response = self.session.get(self.baseurl, params=payload)
        http_response.raise_for_status()
        xmlcontent: bytes = http_response.content
        if xmlcontent.find(b'OAI-PMH') == -1:
            raise exceptions.HTTPError('Not an OAI-PMH repository')
        lmdate: datetime = self._getDateFromHeaders(http_response.headers)
        xmlelement = etree.fromstring(xmlcontent, parser=XMLParser)
        xsi = xmlelement.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"]
        schemapairs = cast(list[str], xsi.split())
        schemapairs = list(chunked(schemapairs, 2))
        customNamespaces: list[CustomSchemaLoc] = [
            {"namespace": pair[0], "schema": pair[1]} for pair in schemapairs if pair[0] not in stockNamespaces]
        identify = xmlelement.find(
            './/{http://www.openarchives.org/OAI/2.0/}Identify')
        if identify == None:
            raise exceptions.HTTPError('No Identify element found')
        namespaces = {
            'http://www.openarchives.org/OAI/2.0/': None,
            # 'http://purl.org/dc/elements/1.1/': None,
            # 'http://www.language-archives.org/OLAC/1.1/': 'olac',
            # 'http://www.language-archives.org/OLAC/1.0/': 'olac'
        }
        identifydict = xmltodict.parse(etree.tostring(identify), process_namespaces=True, namespaces=namespaces)
        print('identifydict', identifydict)

        # This is ridiculous but xml can completely make-up the namespace prefix
        identifykey = list(identifydict.keys())[0]
        identifyobj = identifydict[identifykey]
        #print('identifydict', identifyobj)
        self._junkMetadata(identifyobj)
        # for field in identifyobj['description']:
        #     self._junkMetadata(field)
        return (xmlcontent, lmdate, customNamespaces, identifyobj)

    def _listRecords(self) -> tuple[list[bytes], list[dict[str, Any]]]:
        recordslist: list[dict] = []
        xmlcontentlist: list[bytes] = []
        resumptionToken = None
        # Strip these namespaces from the dict keys (passed to xmltodict)
        namespaces = {
            'http://www.openarchives.org/OAI/2.0/': None,
            'http://purl.org/dc/elements/1.1/': None,
            'http://www.language-archives.org/OLAC/1.1/': 'olac',
            'http://www.language-archives.org/OLAC/1.0/': 'olac'
        }
        pagecounter = 0
        while True:
            payload = {'verb': 'ListRecords'}
            # List records sends metadata prefix once, then resumption token
            if resumptionToken == None:
                payload['metadataPrefix'] = 'olac'
            else: 
                payload['resumptionToken'] = resumptionToken
            print('- fetching', self.baseurl, 'with', payload)
            http_response = self.session.get(self.baseurl, params=payload)
            http_response.raise_for_status()
            xmlcontent: bytes = http_response.content
            xmlcontentlist.append(xmlcontent)
            if xmlcontent.find(b'OAI-PMH') == -1:
                raise exceptions.HTTPError('Not an OAI-PMH repository')
            xmlelement = etree.fromstring(xmlcontent, parser=XMLParser)
            records = xmlelement.findall(
                './/{http://www.openarchives.org/OAI/2.0/}record')
            for record in records:
                recdict = xmltodict.parse(etree.tostring(record), process_namespaces=True, namespaces=namespaces)
                # print('string', etree.tostring(record))
                # print('recdict', recdict)
                datestr = recdict['record']['header']['datestamp']
                if 'T' in datestr:
                    # screw your TZ info, it's supposed to be UTC
                    datestamp = datetime.strptime(
                        datestr, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                else:
                    datestamp = datetime.strptime(datestr, "%Y-%m-%d")
                if 'metadata' not in recdict['record']:
                    print('!!! wtf, no olac metadata?', recdict)
                    continue
                if 'olac:olac' not in recdict['record']['metadata']:
                    print('!!! wtf, no olac:olac metadata?', recdict)
                    continue
                metadata = recdict['record']['metadata']['olac:olac']
                self._junkMetadata(metadata)
                recordslist.append({
                    'identifier': recdict['record']['header']['identifier'],
                    'datestamp': datestamp,
                    'metadata': metadata
                })
            resumptionTokenElement = xmlelement.find('.//{http://www.openarchives.org/OAI/2.0/}resumptionToken')
            if resumptionTokenElement == None  or resumptionTokenElement.text == None:
                break
            resumptionToken = resumptionTokenElement.text
            if pagecounter == 100:
                print('!!! stopping after 100 pages')
                break
            pagecounter += 1

        return (xmlcontentlist, recordslist)


class OLACStatic(OLACBase):
    # Harvest first assesses whether we need to fetch the archive
    def __init__(self, db: OLACDatabase, archive: XMLArchive):
        super().__init__(db, archive)

    def harvest(self, force: bool = False) -> FetchStatus | None:
        print('*** harvesting static', self.baseurl)
        if force or self._shouldHarvest('static'):
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
        fileStore.storeFile(self.identifier, self.baseurl, xml)

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
        xmlelement = etree.fromstring(xmlcontent, parser=XMLParser)
        xsi = xmlelement.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"]
        schemapairs = cast(list[str], xsi.split())
        schemapairs = list(chunked(schemapairs, 2))
        customNamespaces: list[CustomSchemaLoc] = [{"namespace": pair[0], "schema": pair[1]} for pair in schemapairs if pair[0] not in stockNamespaces]
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
            'http://purl.org/dc/elements/1.1/': None,
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
    