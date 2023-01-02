from harvester_base import OLACBase
from database import CustomSchemaLoc, FetchStatus
from requests import exceptions
from datetime import datetime, timezone
from typing import Any
from lxml import etree
import xmltodict

class OLACPMH(OLACBase):

    def harvest(self, force: bool = False) -> FetchStatus | None:
        print('*** harvesting dynamic', self.baseurl)
        shouldHarvest = self._shouldHarvest('static') # Run this always because it initialises fetchStatus
        if force or shouldHarvest:
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
        self.fileStore.storeFile(self.identifier, 'identify.xml', xml)

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
            self.fileStore.storeFile(self.identifier, 'listrecords'+str(i)+'.xml', xml[i])

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
        xmlelement = etree.fromstring(xmlcontent, parser=self.XMLParser)
        customNamespaces = self._getCustomNamespacesFromXMLElement(xmlelement)
        identify = xmlelement.find(
            './/{http://www.openarchives.org/OAI/2.0/}Identify')
        if identify == None:
            raise exceptions.HTTPError('No Identify element found')
        namespaces = {
            'http://www.openarchives.org/OAI/2.0/': 'oai',
            # 'http://purl.org/dc/elements/1.1/': None,
            # 'http://www.language-archives.org/OLAC/1.1/': 'olac',
            # 'http://www.language-archives.org/OLAC/1.0/': 'olac'
        }
        identifydict = xmltodict.parse(etree.tostring(identify), process_namespaces=True, namespaces=namespaces)
        identifyobj = identifydict['oai:Identify']
        self._junkMetadata(identifyobj)
        return (xmlcontent, lmdate, customNamespaces, identifyobj)

    def _listRecords(self) -> tuple[list[bytes], list[dict[str, Any]]]:
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
            print('- fetching', self.baseurl, 'with', payload)
            http_response = self.session.get(self.baseurl, params=payload)
            http_response.raise_for_status()
            xmlcontent: bytes = http_response.content
            xmlcontentlist.append(xmlcontent)
            if xmlcontent.find(b'OAI-PMH') == -1:
                raise exceptions.HTTPError('Not an OAI-PMH repository')
            xmlelement = etree.fromstring(xmlcontent, parser=self.XMLParser)
            records = xmlelement.findall(
                './/{http://www.openarchives.org/OAI/2.0/}record')
            for record in records:
                recdict = xmltodict.parse(etree.tostring(record), process_namespaces=True, namespaces=namespaces)
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

        return (xmlcontentlist, recordslist)
