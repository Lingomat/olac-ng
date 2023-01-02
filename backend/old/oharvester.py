import sys
import os
import re
import traceback
from StringIO import StringIO
import xml.sax.xmlreader
import xml.dom
import subprocess
import threading
import time
import datetime
import dateutil.parser
import tempfile
import MySQLdb
import pycurl
from curl import *
try:
    import olac
except ImportError:
    olac = None
try:
    from optionparser import OptionParser
except ImportError:
    print >>sys.stderr, """
Can't find the 'optionparser' module, which can be obtained from here:
http://olac.svn.sourceforge.net/viewvc/*checkout*/web/lib/python/optionparser.py
"""
    sys.exit(1)

XSI_SCHEMA = 'http://www.w3.org/2001/XMLSchema-instance'
OAI_SR_SCHEMA = 'http://www.openarchives.org/OAI/2.0/static-repository'

LOG = sys.stderr
USESYSLOG = False
class Logger:
    def log(self, msg):
        t = time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime())
        joiner = "\n%s " % t
        print >>LOG, t, joiner.join(msg.split('\n'))
        if USESYSLOG and olac:
            for line in msg.split('\n'):
                olac.log(line)


class DBI(Logger):
    """
    Datebase interface.

    The processIdentify function process an Identify response (in an
    intermediate format) to update the database.
    
    The processRecord function process an GetRecord response (stored as a
    Record object) to update the database.
    """
    
    def __init__(self, conn):
        self.con = conn
        self.cur = conn.cursor()
        self.count = 0

        self.recordCount = 0
        self.newRecordCount = 0
        self.updatedRecordCount = 0
        self.deletedRecordCount = 0
        self.ignoredRecordCount = 0
        self.recordCount0 = 0
        self.newRecordCount0 = 0
        self.updatedRecordCount0 = 0
        self.deletedRecordCount0 = 0
        self.ignoredRecordCount0 = 0

        self.repoid = None
        self.archiveid = None
        
        # OLAC schema ID table
        sql = "select Xmlns, Schema_ID from SCHEMA_VERSION"
        self.cur.execute(sql)
        self.olacschema = dict(self.cur.fetchall())

        # Metadata element tag ID table
        sql = "select TagName, Tag_ID from ELEMENT_DEFN"
        self.cur.execute(sql)
        self.tagids = dict(self.cur.fetchall())

        # Extension ID table
        sql = "select NS, Type, Extension_ID from EXTENSION"
        self.cur.execute(sql)
        self.extids = dict([((r[0],r[1]), r[2]) for r in self.cur.fetchall()])
        self.extids[None,None] = self.extids['','']

        # ISO 639-1 table
        sql = "select Part1, Id from ISO_639_3 where Part1 is not null"
        self.cur.execute(sql)
        self.ISO_639_1 = dict([r for r in self.cur.fetchall()])

        # ISO 639-2B table
        sql = "select Part2B, Id from ISO_639_3 where Part2B is not null"
        self.cur.execute(sql)
        self.ISO_639_2B = dict([r for r in self.cur.fetchall()])

        # ISO 639-2T table
        #sql = "select Part2T, Id from ISO_639_3 where Part2T is not null"
        #self.cur.execute(sql)
        #self.ISO_639_2T = dict([r for r in self.cur.fetchall()])

    def processIdentify(self, record):
        try:
            self._processIdentify(record)
        except:
            msg = traceback.format_exc()
            msg = "\nUnexpected error in the harvester code:\n\n%s\n\n" % msg
            self.log(msg)
            raise

    def processRecord(self, record):
        try:
            self._processRecord(record)
        except:
            msg = traceback.format_exc()
            msg = "\nUnexpected error in the harvester code:\n\n%s\n\n" % msg
            self.log(msg)
            raise
        
    def _processIdentify(self, record):
        dbrecord = {}
        dbfields = {}
        for dbfield in ('ArchiveURL',
                        'Curator',
                        'CuratorTitle',
                        'CuratorEmail',
                        'Institution',
                        'InstitutionURL',
                        'ShortLocation',
                        'Location',
                        'Synopsis',
                        'Access',
                        'ArchivalSubmissionPolicy',
                        'RepositoryName',
                        'BaseURL',
                        'OaiVersion',
                        'AdminEmail',
                        'RepositoryIdentifier',
                        'SampleIdentifier',
                        'ArchiveType',
                        'CurrentAsOf'):
            key = dbfield[0].lower() + dbfield[1:]
            dbrecord[dbfield] = record[key]

        repoid = dbrecord['RepositoryIdentifier']
        baseurl = dbrecord['BaseURL']
        self.log("repository id: %s" % repoid)
        sql = """
        select Archive_ID from OLAC_ARCHIVE
        where RepositoryIdentifier=%s and BaseURL=%s
        """
        self.cur.execute(sql, (repoid,baseurl))
        if self.cur.rowcount > 0:
            self.log("%s already exists" % repoid)
            # just update
            archiveid = self.cur.fetchone()[0]
            L = dbrecord.items()
            fields = ','.join(["%s=%%s" % r[0] for r in L])
            values = [r[1] for r in L] + [archiveid]
            sql = 'update OLAC_ARCHIVE set %s where Archive_ID=%%s' % fields
            self.cur.execute(sql, values)
            if self.cur.rowcount > 0:
                self.log("some fields of OLAC_ARCHIVE table have been updated")
            else:
                self.log("no changes made to the OLAC_ARCHIVE table")
        else:
            self.log("%s is a new archive" % repoid)
            # new archive
            L = dbrecord.items()
            fields = '(' + ','.join([r[0] for r in L]) +')'
            values = '(' + ','.join(['%s'] * len(L)) + ')'
            sql = 'insert into OLAC_ARCHIVE %s values %s' % (fields,values)
            self.cur.execute(sql, [r[1] for r in L])
            archiveid = self.cur.lastrowid

        sql = "select Name,Role,Email from ARCHIVE_PARTICIPANT where Archive_ID=%s"
        self.cur.execute(sql, (archiveid,))
        L = sorted(self.cur.fetchall())
        M = sorted([tuple(r) for r in record['participants']])
        if L != M:
            sql = "delete from ARCHIVE_PARTICIPANT where Archive_ID=%s"
            self.cur.execute(sql, (archiveid,))
            sql = "insert ignore into ARCHIVE_PARTICIPANT values (%s,%s,%s,%s)"
            for name, role, email in M:
                self.cur.execute(sql, (archiveid, name, role, email))
            self.log("participant list has changed")
    
        self.archiveid = archiveid
        self.repoid = repoid
        self.recordCount = 0
        self.newRecordCount = 0
        self.updatedRecordCount = 0
        self.deletedRecordCount = 0
        self.ignoredRecordCount = 0
        self.recordCount0 = 0
        self.newRecordCount0 = 0
        self.updatedRecordCount0 = 0
        self.deletedRecordCount0 = 0
        self.ignoredRecordCount0 = 0

        self.con.commit()

    def _processRecord(self, record):
        self.recordCount0 += 1

        try:
            if not record.deleted():
                schemaid = self.olacschema[record.olacSchema()]
        except KeyError:
            # this record uses unknown schema
            # --> do not harvest
            return

        sql = "select Item_ID,DateStamp from ARCHIVED_ITEM where OaiIdentifier=%s"
        oaiid = record.oaiId()
        self.cur.execute(sql, (oaiid,))
        flagUpdateMetadata = False
        if self.cur.rowcount > 0:
            # record with the same id exists
            rows = self.cur.fetchall()
            itemid = rows[0][0]
            dt = max([r[1] for r in rows])
            if record.deleted():
                # --> delete
                sql = "delete from METADATA_ELEM where Item_ID=%s"
                self.cur.execute(sql, (itemid,))
                sql = "delete from ARCHIVED_ITEM where Item_ID=%s"
                self.cur.execute(sql, (itemid,))
                self.deletedRecordCount0 += 1
            else:
                # --> update
                sql = "update ARCHIVED_ITEM set " \
                      "OaiIdentifier=%s,DateStamp=%s,Archive_ID=%s,Schema_ID=%s " \
                      "where Item_ID=%s"
                args = (oaiid, record.datestamp(), self.archiveid, schemaid, itemid)
                self.cur.execute(sql, args)
                dt1 = dateutil.parser.parse(record.datestamp())
                if self.cur.rowcount > 0 or dt<=dt1.date():
                    self.updatedRecordCount0 += 1
                    flagUpdateMetadata = True
                    sql = "delete from METADATA_ELEM where Item_ID=%s"
                    self.cur.execute(sql, (itemid,))
                else:
                    self.ignoredRecordCount0 += 1
        else:
            if record.deleted():
                # do nothing
                self.ignoredRecordCount0 += 1
            else:
                # new record
                # --> insert
                args = (oaiid, record.datestamp(), self.archiveid, schemaid)
                sql = "insert into ARCHIVED_ITEM " \
                      "(OaiIdentifier, DateStamp, Archive_ID, Schema_ID) " \
                      "values (%s, %s, %s, %s)"
                self.cur.execute(sql, args)
                itemid = self.cur.lastrowid
                flagUpdateMetadata = True
                self.newRecordCount0 += 1
        
        if flagUpdateMetadata:
            for row in record.metadataElements():
                tagName, extSchema, extType, extCode, content = row
                
                if (extCode is None or extCode.strip() == '') and \
                   (content is None or content.strip() == ''):
                    continue

                try:
                    tagid = self.tagids[tagName]
                except KeyError:
                    # this element uses invalid tag
                    # --> skip it
                    continue

                try:
                    extid = self.extids[extSchema, extType]
                except KeyError:
                    # this is a new extension
                    # --> add it
                    sql = "insert ignore into EXTENSION (Type, NS, NSSchema) values (%s, %s, %s)"
                    try:
                        self.cur.execute(sql, (extType, extSchema, extSchema.location()))
                    except Exception, e:
                        self.log("")
                        self.log("db error: error while executing a query")
                        self.log("db error: query:  %s" % sql)
                        self.log("db error: error:  %s" % e)
                        self.log("")
                        raise
                    extid = self.cur.lastrowid
                    self.extids[extSchema, extType] = extid

                # translate ISO 639-1/2B codes to 639-3 equivalets
                # NOTE: what about ISO 639-2T?
                if extType == 'language':
                    #if extCode in self.ISO_639_2T:
                    #    extCode = self.ISO_639_2T[extCode]
                    if extCode in self.ISO_639_2B:
                        extCode = self.ISO_639_2B[extCode]
                    elif extCode in self.ISO_639_1:
                        extCode = self.ISO_639_1[extCode]
                        
                sql = "insert into METADATA_ELEM " \
                      "(TagName, Content, Extension_ID, Type, Code, Item_ID, Tag_ID) " \
                      "values (%s, %s, %s, %s, %s, %s, %s)"
                args = (tagName, content, extid, extType, extCode, itemid, tagid)
                self.cur.execute(sql, args)
            
        self.count += 1
        if self.count % 100 == 0:
            self.commit()
            
    def counts(self):
        return self.recordCount, \
               self.newRecordCount, \
               self.updatedRecordCount, \
               self.deletedRecordCount, \
               self.ignoredRecordCount

    def repositoryId(self):
        return self.repoid

    def archiveId(self):
        return self.archiveid

    def lastHarvested(self):
        if self.archiveid is not None:
            sql = "select LastHarvested from OLAC_ARCHIVE where Archive_ID=%s"
            self.cur.execute(sql, (self.archiveid,))
            return self.cur.fetchone()[0]
        
    def commit(self):
        # NOTE: make sure that this gets called
        self.con.commit()
        self.recordCount += self.recordCount0
        self.newRecordCount += self.newRecordCount0
        self.updatedRecordCount += self.updatedRecordCount0
        self.deletedRecordCount += self.deletedRecordCount0
        self.ignoredRecordCount += self.ignoredRecordCount0
        self.recordCount0 = 0
        self.newRecordCount0 = 0
        self.updatedRecordCount0 = 0
        self.deletedRecordCount0 = 0
        self.ignoredRecordCount0 = 0


class Request:
    """
    Generate OAI request URLs.
    """
    
    def __init__(self, baseurl, metadataPrefix):
        """
        @param fromDate: a datetime.datetime object
        """
        self.baseurl = baseurl
        self.metadataPrefix = metadataPrefix

    def baseUrl(self):
        return self.baseurl
    
    def Identify(self):
        return "%s?verb=Identify" % self.baseurl
    
    def ListRecords(self, resumptionToken=None, fromDate=None):
        url = "%s?verb=ListRecords" % self.baseurl
        if resumptionToken:
            url += "&resumptionToken=%s" % resumptionToken
        else:
            url += "&metadataPrefix=%s" % self.metadataPrefix
            if fromDate:
                url += "&from=%s" % fromDate.strftime("%Y-%m-%d")
        return url


class Identify:
    """
    This is a dictionary-like representation of an Identify response.
    Fields can be accessed by the XML element name.
    """
    def __init__(self, xmldata):
        archiveType = None
        currentAsOf = None
        participants = []
        self.data = {}
        for name, atts, contents in xmldata:
            if name == 'olac-archive':
                for schema, attname, vschema, v in atts:
                    if attname == 'type':
                        archiveType = v
                    elif attname == 'currentAsOf':
                        currentAsOf = v
            elif name == 'participant':
                h = dict([(f,v) for _,f,_,v in atts])
                participants.append([h['name'],h['role'],h['email']])
            else:
                self.data[name] = ''.join(contents)
        self.data['type'] = archiveType
        self.data['archiveType'] = archiveType
        self.data['currentAsOf'] = currentAsOf
        try:
            self.data['oaiVersion'] = self.data['protocolVersion']
        except KeyError:
            self.data['oaiVersion'] = None
        self.data['participants'] = participants
            
    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]

    
class Record:
    """
    This represents an OLAC GetRecord element.
    """
    def __init__(self, header, olacdata=None):
        self.header = header    # (ns,name,attrs,body)
        self.olac = olacdata    # (ns,name,attrs,body)

        self.olacSchema_ = self._extract(header, 'name', 'olac', 'schema')
        self.oaiId_ = self._extract(header, 'name', 'identifier', 'body')
        if self.oaiId_:
            self.oaiId_ = self.oaiId_.strip()
        self.datestamp_ = self._extract(header, 'name', 'datestamp', 'body')

        self.deleted_ = False
        header_atts = self._extract(header, 'name', 'header', 'attributes')
        for attns, att, xsiTypeNs, attval in header_atts:
            if att == 'status' and attval == 'deleted':
                self.deleted_ = True
                break

    def _extract(self, L, searchField, searchValue, returnField):
        fields = ["schema", "name", "attributes", "body"]
        try:
            i = fields.index(searchField)
            j = fields.index(returnField)
        except ValueError:
            return
        for row in L:
            if row[i] == searchValue:
                return row[j]
            
    def metadataElements(self):
        if self.olac is None: return
        for ns, tagName, attrs, content in self.olac:
            extType = None
            extSchema = None
            extCode = None
            for attns, att, xsiTypeNs, attval in attrs:
                if attns==XSI_SCHEMA and att=='type' and xsiTypeNs is not None:
                    extType = attval
                    extSchema = xsiTypeNs
                    for a,b,c,d in attrs:
                        if a==extSchema and b=='code':
                            extCode = d
            yield tagName, extSchema, extType, extCode, content

    def olacSchema(self):
        return self.olacSchema_

    def oaiId(self):
        return self.oaiId_

    def datestamp(self):
        return self.datestamp_

    def deleted(self):
        return self.deleted_

    
class Schema:
    """
    Contains information on an XML schema.
    """
    
    def __init__(self, uri, loc=None):
        self.uri_ = uri
        self.loc_ = loc

    def __str__(self):
        return self.uri_

    def __hash__(self):
        return hash(self.uri_)

    def __cmp__(self, v):
        if isinstance(v,Schema):
            return cmp(self.uri_,v.uri_)
        else:
            return cmp(self.uri_,v)

    def __eq__(self, v):
        if isinstance(v,Schema):
            return self.uri_ == v.uri_
        else:
            return self.uri_ == v
    
    def uri(self):
        return self.uri_

    def location(self):
        return self.loc_

    def setLocation(self, loc):
        self.loc_ = loc


class Environment:
    """
    Nestable environment of variables.
    """
    
    def __init__(self):
        self.stack = []

    def push(self, dic=None):
        if dic is None:
            self.stack.append({})
        else:
            self.stack.append(dic)

    def pop(self):
        if self.stack:
            self.stack.pop()

    def toDict(self):
        h = {}
        for h1 in self.stack:
            h.update(h1)
        return h
    
    def __setitem__(self, name, value):
        if self.stack:
            self.stack[-1][name] = value

    def __getitem__(self, name):
        for i in range(len(self.stack)-1,-1,-1):
            h = self.stack[i]
            if name in h:
                return h[name]

    def __contains__(self, name):
        for i in range(len(self.stack)-1,-1,-1):
            if name in self.stack[i]:
                return True
        return False

    
class Namespace:
    """
    Namespace object keeps track of the XML namespaces in an XML document.
    """
    
    def __init__(self):
        self.schemaLocs = Environment()
        self.schemas = Environment()

    def push(self, tag, attrs):
        """
        Process namespace-related attributes and return unused attributes.
        """
        prefixDict = {}
        schemaLocationCands = []
        rest = {}   # unprocessed attributes
        for att in attrs.getNames():
            if att == 'xmlns':
                prefixDict[0] = attrs.getValue(att)
            elif att.startswith('xmlns'):
                _, prefix = att.split(':')
                prefixDict[prefix] = attrs.getValue(att)
            elif att.endswith(':schemaLocation'):
                prefix = att.split(':')[0]
                schemaLocationCands.append((prefix,attrs.getValue(att)))
            else:
                rest[att] = attrs.getValue(att)
        self.schemaLocs.push()
        for prefix, s in schemaLocationCands:
            if (prefix in prefixDict and prefixDict[prefix] == XSI_SCHEMA) or \
               (prefix in self.schemas and self.schemas[prefix] == XSI_SCHEMA):
                L = s.strip().split()
                # in case len(L) is an odd number
                if len(L)/2*2 != len(L): L.append(None)
                for i in range(0,len(L),2):
                    self.schemaLocs[L[i]] = L[i+1]
        self.schemas.push()
        for prefix, schema in prefixDict.items():
            schemaObj = Schema(schema, self.schemaLocs[schema])
            self.schemas[prefix] = schemaObj

        atts = []
        elSchema, elName = self.resolve(tag)
        for att, v in rest.items():
            if ':' in att:
                schema, att = self.resolve(att)
            else:
                schema = elSchema
            if schema is not None and str(schema) in XSI_SCHEMA and att=='type':
                vSchema, v = self.resolve(v)
            else:
                vSchema = None
            atts.append((schema, att, vSchema, v))
        return elSchema, elName, atts
    
    def pop(self):
        self.schemaLocs.pop()
        self.schemas.pop()

    def find(self, prefix):
        return self.schemas[prefix]

    def findSchemeLocation(self, schema):
        return self.schemaLocs[schema]

    def prefixes(self):
        return self.schemas.toDict()

    def schemaLocations(self):
        return self.schemaLocs.toDict()

    def resolve(self, qname):
        if ':' in qname:
            prefix, name = qname.split(':')
        else:
            prefix = 0
            name = qname
        schema = self.find(prefix)
        return schema, name

    def resolveAttribute(self, qname, tag):
        """
        @param qname: Here qname should come from an attribute value.
        @param tag: The tag of the element to which the qname belongs.
        """
        if ':' in qname:
            prefix, name = qname.split(':')
            schema = self.find(prefix)
        else:
            name = qname
            schema, _ = self.resolve(tag)
        return schema, name


class HandlerError(Exception): pass

def create_record(build):
    result = []
    for L in build:
        x = []      # (na,name,attrs,body)
        for r in L:
            schema, elName, atts = r[0]
            body = ''.join(r[1:])
            x.append((schema, elName, atts, body))
        result.append(x)
    if len(result) == 2:
        return Record(result[0], result[1])
    elif len(result) == 1:
        return Record(result[0])

class IdentifyHandler(Logger, xml.sax.handler.ContentHandler):
    """
    An SAX handler.
    Calls identifyHandler with an Identify object (defined above)
    after parsing the Identify reponse.
    """
    def __init__(self, identifyHandler):
        xml.sax.handler.ContentHandler.__init__(self)
        self.identifyHandler = identifyHandler
        self.reset()

    def reset(self):
        self.data = []
        self.stack = []
        self.ns = Namespace()
        self.names = []
        self.error = {}
        
    def startElement(self, tag, attrs):
        schema, name, atts = self.ns.push(tag, attrs)
        self.names.append(name)
        self.data.append([name, atts, []])
        self.stack.append(len(self.data)-1)
        if name == 'error':
            self.error = {}
            for _, attNam, _, attVal in atts:
                if attNam == 'code':
                    self.error['code'] = attVal

    def characters(self, content):
        self.data[self.stack[-1]][-1].append(content)
        if self.names[-1] == 'error':
            if 'message' in self.error:
                self.error['message'] += content
            else:
                self.error['message'] = content

    def endElement(self, tag):
        #schema, schemaLoc, name = self.ns.resolve(tag)
        self.stack.pop()
        self.ns.pop()
        self.names.pop()

    def endDocument(self):
        self.log("parsing Identify response done")
        if self.data[0][0] != 'OAI-PMH':
            raise HandlerError("invalid Identify response")
        else:
            self.log("processing Identify response")
            identify = Identify(self.data)
            self.identifyHandler(identify)

            
class ListRecordsHandler(Logger, xml.sax.handler.ContentHandler):
    """
    An SAX Handler.
    Calls recordHandler with a Record object as it parses through
    the ListRecords response.
    """
    def __init__(self, recordHandler, resumptionTokenHandler):
        xml.sax.handler.ContentHandler.__init__(self)
        self.recordHandler = recordHandler
        self.resumptionTokenHandler = resumptionTokenHandler
        self.reset()

    def reset(self):
        self.flag = False
        self.names = []
        self.ns = Namespace()
        self.error = {}
        
    def startElement(self, tag, attrs):
        schema, name, atts = self.ns.push(tag, attrs)

        self.names.append(name)
        if name == 'record':
            self.build = []
        elif name == 'header':
            self.build.append([[(schema,name,atts)]])
            self.flag = True
        elif name == 'olac':
            # append the opening element to the 'header' record
            # this is used to figure out the version of olac schema
            self.build[-1].append([(schema,name,atts)])
            # create a new 'olac' record
            self.build.append([])
            self.flag = True
        elif name == 'resumptionToken':
            self.resumptionToken = ''
        elif name == 'error':
            self.error = {}
            for _, attNam, _, attVal in atts:
                if attNam == 'code':
                    self.error['code'] = attVal
        elif self.flag:
            self.build[-1].append([(schema,name,atts)])

    def characters(self, content):
        if self.flag:
            if self.names[-1] not in ('header','olac'):
                self.build[-1][-1].append(content)
        elif self.names[-1] == 'resumptionToken':
            self.resumptionToken += content
        elif self.names[-1] == 'error':
            if 'message' in self.error:
                self.error['message'] += content
            else:
                self.error['message'] = content
            
    def endElement(self, tag):
        schema, name = self.ns.resolve(tag)
        
        if name == 'record':
            record = create_record(self.build)
            #self.log("processing record: %s" % record.oaiId())
            if record: self.recordHandler(record)
        elif name in ('header','olac'):
            self.flag = False
        elif name == 'resumptionToken':
            token = self.resumptionToken.strip()
            if token:
                #self.log("resumption token found: %s" % token)
                self.resumptionTokenHandler(token)
        self.names.pop()
        self.ns.pop()


class SrHandler(Logger, xml.sax.handler.ContentHandler):
    """
    An SAX handler for static repository.
    """

    ID_MODE = 1  # inside Identify element
    LR_MODE = 2  # inside ListRecords element
    
    def __init__(self, dbi, fullHarvest):
        xml.sax.handler.ContentHandler.__init__(self)
        self.dbi = dbi
        self.fullHarvest = fullHarvest
        self.identifyHandler = dbi.processIdentify
        self.recordHandler = dbi.processRecord
        self.reset()
        
    def reset(self):
        self.flag = False # indicates whether a record is open
        self.error = {}
        self.mode = None
        self.ns = Namespace()
        self.identify_data = []
        self.names = []
        self.ptr = []
        self.recordids = set()

    def startElement(self, tag, attrs):
        #print "< >", tag
        schema, name, atts = self.ns.push(tag, attrs)

        self.names.append(name)
        if self.mode == self.LR_MODE:
            if name == 'record':
                self.build = []
            elif name == 'header':
                self.build.append([[(schema,name,atts)]])
                self.flag = True
            elif name == 'olac':
                # append the opening element to the 'header' record
                # this is used to figure out the version of olac schema
                self.build[-1].append([(schema,name,atts)])
                # create a new 'olac' record
                self.build.append([])
                self.flag = True
            elif self.flag:
                self.build[-1].append([(schema,name,atts)])
        elif self.mode == self.ID_MODE:
            self.identify_data.append([name, atts, []])
            self.ptr.append(len(self.identify_data)-1)
        else:
            if name == 'Identify' and schema == OAI_SR_SCHEMA:
                self.mode = self.ID_MODE
                self.identify_data.append([name, atts, []])
                self.ptr.append(0)
            elif name == 'ListRecords' and schema == OAI_SR_SCHEMA:
                self.mode = self.LR_MODE
                self.log("parsing ListRecords element...")
                self.fromDate = ''
                if not self.fullHarvest:
                    last_harvested = self.dbi.lastHarvested()
                    if last_harvested is not None:
                        self.fromDate = last_harvested.strftime("%Y-%m-%d")
            
    def characters(self, content):
        if self.mode == self.LR_MODE:
            if self.flag:
                if self.names[-1] not in ('header','olac'):
                    self.build[-1][-1].append(content)
        elif self.mode == self.ID_MODE:
            self.identify_data[self.ptr[-1]][-1].append(content)
            
    def endElement(self, tag):
        #print "</>", tag
        schema, name = self.ns.resolve(tag)

        if self.mode == self.LR_MODE:
            if name == 'record':
                record = create_record(self.build)
                self.recordids.add(record.oaiId())
                if record and record.datestamp() >= self.fromDate:
                    self.recordHandler(record)
            elif name in ('header','olac'):
                self.flag = False
            elif name == 'ListRecords' and schema == OAI_SR_SCHEMA:
                self.mode = None
        elif self.mode == self.ID_MODE:
            if name == 'Identify' and schema == OAI_SR_SCHEMA:
                self.log("done parsing Identify element")
                self.log("processing Identify element...")
                identify = Identify(self.identify_data)
                self.identifyHandler(identify)
                self.mode = None
            self.ptr.pop()
        self.names.pop()
        self.ns.pop()

     
class ExternalProgram:
    def __init__(self, path, args):
        """
        @param path: path to the program
        @param args: a list of command line arguments, e.g. ["-f", "abc", "-d"]
        """
        self.path = path
        self.args = args

    def getPath(self):
        return self.path

    def getArgs(self):
        return self.args


class Utf8Filter:
    def __init__(self, prog, nextStep):
        """
        @param prog: an ExternalProgram, which should be a filter (takes input
                     from stdin and produces output on stdout)
        @param nextStep: an object providing feed(str) method
        """
        self.nextStep = nextStep
        self.lock = threading.Lock()
        self.data = []
        self.datasize = 0
        self.pipe = subprocess.Popen([prog.getPath()] + prog.getArgs(),
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE)
        self.thread = threading.Thread(target=self._threadAction)
        self.thread.start()
        
    def feed(self, data=None):
        if data: self.pipe.stdin.write(data)

        if self.datasize > 0:
            self.lock.acquire()
            s = "".join(self.data)
            self.data = []
            self.datasize = 0
            self.lock.release()
            # -1 for fatal error
            return self.nextStep.feed(s)

    def close(self):
        self.pipe.stdin.close()
        self.pipe.wait()
        self.thread.join()
        # push out remaining data in the buffer
        if self.feed() == -1: return False
        return self.nextStep.close()
    
    def _threadAction(self):
        while True:
            data = self.pipe.stdout.read(128)
            if not data: break
            self.lock.acquire()
            self.datasize += len(data)
            self.data.append(data)
            self.lock.release()

        
class StreamParser(Logger):
    def __init__(self, handler):
        self.xmlReader = xml.sax.make_parser()
        self.xmlReader.setContentHandler(handler)

    def feed(self, data):
        try:
            self.xmlReader.feed(data)
            # it's okay to return None instead of the size consumed data
        except xml.sax.SAXParseException, e:
            msg = "parse error: %s" % e.getException()
            self.log(msg)
            return -1

    def close(self):
        try:
            self.xmlReader.close()
            return True
        except xml.sax._exceptions.SAXParseException, e:
            self.log("document closed unexpectedly: %s" % e)
            return False


class Data:
    def __init__(self):
        self.dat = StringIO()
        self.n = 0
    def reset(self):
        self.dat.seek(0)
        self.dat.truncate()
        self.n = 0
    def write(self, s):
        self.n += len(s)
        self.dat.write(s)
    def dump(self):
        return self.dat.getvalue()
    

class HarvesterBase(Logger):

    def __init__(self, url, handler, fullHarvest=False, streamFilter=None):
        self.url = url
        self.handler = handler
        self.fullHarvest = fullHarvest
        self.filter = lambda next: Utf8Filter(streamFilter, next)
        
    def _httpStatus(self, data):
        code = data.split()[1]
        if code != '200' and code !='302':
            self.log("http error %s; continue nevertheless" % code)
            #raise StopFetching()

    def _download(self, handler, url, retry, saver=None):
        self.log("downloading the url...")
        dat = Data()
        curl = MyCurl(dat.write, self._httpStatus, dat.reset)
        try:
            curl.fetch(MyUrl(url))
        except pycurl.error, e:
            self.log("pycurl error: %s" % e)
            if e[0] == 28 and retry > 0:
                self.log("retrying...")
                return self._download(handler, url, retry-1)
            else:
                self.log("download failed")
                return False
        self.log("processing downloaded data...")
        if self.filter:
            parser = self.filter(StreamParser(handler))
        else:
            parser = StreamParser(handler)
        try:
            ret = parser.feed(dat.dump())
            ret2 = parser.close()
            if saver is not None:
                saver(dat.dump())
            if ret == -1 or ret2 == False:
                self.log("xml parse error has occurred")
                return False
            else: 
                return True
        except HandlerError, e:
            self.log("error: %s" %e)
            parser.close()
            return False

    def harvest(self):
        pass

    
class Harvester(HarvesterBase):
    """
    Dynamic repository harvester.
    """
    
    def harvest(self):
        request = Request(self.url, 'olac')
        self.log("harvester running on %s" % os.uname()[1])
        self.log("harvesting from %s" % request.baseUrl())
        handler = IdentifyHandler(self.handler.processIdentify)
        url = request.Identify()
        self.log("fetching and processing: %s" % url)
        if not self._download(handler, url, 2, keep_download):
            return False
        if handler.error:
            if 'message' in handler.error:
                self.log('OAI-PMH Error: %(code)s: %(message)s' % handler.error)
            else:
                self.log('OAI-PMH Error: %(code)s' % handler.error)
            return False

        if self.fullHarvest:
            fromDate = None
        else:
            fromDate = self.handler.lastHarvested()
        urls = [request.ListRecords(fromDate=fromDate)]
        rtHandler = lambda x: urls.append(request.ListRecords(x))
        while urls:
            handler = ListRecordsHandler(self.handler.processRecord, rtHandler)
            url = urls.pop()
            self.log("fetching and processing: %s" % url)
            if not self._download(handler, url, 2):
                return False
            if handler.error:
                if 'message' in handler.error:
                    self.log('OAI-PMH Error: %(code)s: %(message)s' % handler.error)
                else:
                    self.log('OAI-PMH Error: %(code)s' % handler.error)
                if handler.error['code'] != 'noRecordsMatch':
                    return False

        return True


class SrHarvester(HarvesterBase):
    """
    Static repository harvester.
    """

    def harvest(self):
        self.log("harvester running on %s" % os.uname()[1])
        self.log("harvesting from %s" % self.url)
        handler = SrHandler(self.handler, self.fullHarvest)
        if not self._download(handler, self.url, 1, keep_download):
            return False
        self.recordOaiIds = handler.recordids
        return True


def keep_download(data):
    directory = os.path.join(olac.olacvar('static/root'), 'identify_downloads')
    if not os.path.exists(directory):
        os.makedirs(directory)
    fd, path = tempfile.mkstemp(dir=directory, prefix="")
    os.write(fd, data)
    os.close(fd)


def set_hfc(con, archiveid):
    """
    Set HFC code for the given archive
    """
    if archiveid:
        cur = con.cursor()
        sql = "delete from INTEGRITY_CHECK where Object_ID=%s and Problem_Code='HFC'"
        cur.execute(sql, (archiveid,))
        sql = "insert into INTEGRITY_CHECK (Object_ID, Problem_Code) values (%s, 'HFC')"
        cur.execute(sql, (archiveid,))
        cur.close()


def mark_success(con, archiveid, date):
    """
    Set LastHarvested date and clear HFC error.
    """
    if archiveid:
        cur = con.cursor()
        sql = "update OLAC_ARCHIVE set LastHarvested=%s where Archive_ID=%s"
        cur.execute(sql, (date, archiveid))
        sql = "delete from INTEGRITY_CHECK where Object_ID=%s and Problem_Code='HFC'"
        cur.execute(sql, (archiveid,))
        cur.close()


def do_implicit_deletion(con, archiveid, harvested_ids):
    cur = con.cursor()
    sql = "select OaiIdentifier from ARCHIVED_ITEM where Archive_ID=%s"
    cur.execute(sql, (archiveid,))
    for oaiid, in cur.fetchall():
        if oaiid not in harvested_ids:
            sql = """
            delete me.* from ARCHIVED_ITEM ai, METADATA_ELEM me
            where ai.OaiIdentifier=%s and ai.Item_ID=me.Item_ID
            """
            cur.execute(sql, (oaiid,))
            sql = "delete from ARCHIVED_ITEM where OaiIdentifier=%s"
            cur.execute(sql, (oaiid,))
    cur.close()


def get_last_modified(url):
    f = lambda x: None
    curl = MyCurl(f,f)
    for row in curl.fetch(MyUrl(url),head=True):
        if row.split(':')[0].lower() == 'last-modified':
            return ":".join(row.split(':')[1:]).strip()


######################################################################
## Application code starts here
##

def harvest(url, con, full=False, stream_filter=None, static=False):
    try:
        dbi = DBI(con)
        if static:
            h = SrHarvester(url, dbi, full, stream_filter)
        else:
            h = Harvester(url, dbi, full, stream_filter)
        cur = con.cursor()
        now = datetime.datetime.now().date()
        if h.harvest():
            h.log("harvest successful")
            mark_success(con, dbi.archiveId(), now)
            if static:
                archiveid = dbi.archiveId()
                if archiveid is not None:
                    do_implicit_deletion(con, archiveid, h.recordOaiIds)
        else:
            h.log("harvest failed")
            # dbi can provide archive id only when it has successfully
            # processed identify response
            archiveid = dbi.archiveId()
            if archiveid is None:
                cur.execute("select Archive_ID from OLAC_ARCHIVE where BaseURL=%s", (url,))
                if cur.rowcount > 0:
                    archiveid = cur.fetchone()[0]
            if archiveid:
                set_hfc(con, archiveid)
        cur.close()
        dbi.commit()
        rc, nrc, urc, drc, irc = dbi.counts()
        h.log("processed %d records (this may include retries)" % rc)
        h.log("new records: %d" % nrc)
        h.log("updated records: %d" % urc)
        h.log("deleted records: %d" % drc)
        h.log("ignored records: %d" % irc)

    except:
        msg = traceback.format_exc()
        msg = "\nUnexpected error in the harvester code:\n\n%s\n\n" % msg
        try:
            h.log(msg)
        except:
            print msg


def harvest_single(url,
                   mycnf,
                   host=None,
                   db=None,
                   full=False,
                   stream_filter=None,
                   static=False):
    opts = {"use_unicode":True, "charset":"utf8"}
    if mycnf is None:
        if olac:
            opts['host'] = olac.olacvar('mysql/host')
            opts['db'] = olac.olacvar('mysql/olacdb')
            opts['user'] = olac.olacvar('mysql/user')
            opts['passwd'] = olac.olacvar('mysql/passwd')
    else:
        opts['read_default_file'] = mycnf
    if host: opts["host"] = host
    if db: opts["db"] = db
    con = MySQLdb.connect(**opts)

    logger = Logger()
    logger.log("begin: %s" % url)
    if static:
        cur = con.cursor()
        sql = "select Archive_ID, LastHarvested from OLAC_ARCHIVE where BaseURL=%s"
        cur.execute(sql, (url,))
        if cur.rowcount > 0:
            archiveid, last_harvested = cur.fetchone()

        if cur.rowcount == 0 or last_harvested is None:
            # this is a new archive
            harvest(url, con, full, stream_filter, static)
        else:
            # check if the file has a new last-modified date
            logger.log("last harvested on %s" % last_harvested)
            logger.log("checking Last-Modified date...")
            s = get_last_modified(url)
            if s is None:
                logger.log("failed checking")
                logger.log("repository will be harvester")
                t = time.mktime(time.localtime())
            else:
                logger.log("got Last-Modified: %s" % s)
                tstruct = time.strptime(s, "%a, %d %b %Y %H:%M:%S %Z") # GMT
                t = time.mktime(tstruct) - time.altzone
            t0 = time.mktime(last_harvested.timetuple())
            if t >= t0 or full:
                # the file has been modified or unable to check timestamp
                harvest(url, con, full, stream_filter, static)
            else:
                logger.log("assume no changes to harvest")
                now = datetime.datetime.now().date()
                mark_success(con, archiveid, now)
                con.commit()
        cur.close()
    else:
        harvest(url, con, full, stream_filter, static)
    con.close()


def harvest_all(mycnf,
                host=None,
                db=None,
                full=False,
                numProc=5,
                url=None,
                stream_filter=None,
                static=False,
                usesyslog=False,
                stdout=False):
    opts = {"use_unicode":True, "charset":"utf8"}
    if mycnf is None:
        if olac:
            opts['host'] = olac.olacvar('mysql/host')
            opts['db'] = olac.olacvar('mysql/olacdb')
            opts['user'] = olac.olacvar('mysql/user')
            opts['passwd'] = olac.olacvar('mysql/passwd')
    else:
        opts['read_default_file'] = mycnf
    if host: opts["host"] = host
    if db: opts["db"] = db
    if url:
        urls = [(url,static)]
    else:
        con = MySQLdb.connect(**opts)
        cur = con.cursor()
        cur.execute("select BASEURL, Type from ARCHIVES "
                    "where dateApproved is not null "
                    "order by rand()")
        urls = list([(x[0],x[1]=='Static') for x in cur.fetchall()])
        cur.close()
        con.close()
    
    logs = {}
    P = {}
    def printlog(pid):
        url = P[pid]
        log = logs[url]
        print >>sys.stderr, "*" * 79
        print >>sys.stderr, url
        print >>sys.stderr, "*" * 79
        print >>sys.stderr, file(log).read()
        print >>sys.stderr
        print >>sys.stderr
        os.unlink(log)
    N = min(10, max(1, numProc))
    while urls:
        url, static = urls.pop()
        logs[url] = tempfile.mktemp()

        pid = os.fork()
        if pid == 0:
            global LOG
            global USESYSLOG
            USESYSLOG = False
            if usesyslog:
                if olac:
                    logname = olac.olacvar('harvester/main_logname')
                    if logname == '/null/value': logname='harvester'
                    olac.openlog(logname)
                    USESYSLOG = True
                else:
                    USESYSLOG = False
                    sys.stderr.write("WARNING: Failed to import olac\n")
                    sys.stderr.write("WARNING: Logging to syslogd disabled\n")
            if stdout:
                LOG = sys.stdout
            else:
                LOG = file(logs[url], "w")
            harvest_single(url, mycnf, host, db, full, stream_filter, static)
            sys.exit(0)
        else:
            P[pid] = url
            if len(P) >= N:
                pid, status = os.wait()
                if not stdout:
                    printlog(pid)
                del P[pid]

    while P:
        pid, status = os.wait()
        if not stdout:
            printlog(pid)
        del P[pid]

        

if __name__ == "__main__":
    usageString = """\
Usage: %(prog)s [options]

    options:

      -h        print this message and exit
      -c mycnf  mycnf file. If not given, OLAC configuration DB is tried.
      -H host   hostname of the mysql server
      -d db     name of the olac database
      -f        full harvest if this option presents
      -s url    harvest a single repository
      --static  used in conjunction with -s, indicates the given URL is
                an OAI static repository
      -u        turn on utf-8 cleaner, which is searched in the system config
      -U path   use the program specified by path as a utf-8 cleaner; implies -u
      -l        use syslogd to log messages
      --stdout  output to stdout

""" % {"prog":os.path.basename(sys.argv[0])}
    
    def usage(msg=None):
        print >>sys.stderr, usageString
        if msg:
            print >>sys.stderr, "ERROR:", msg
            print >>sys.stderr
        sys.exit(1)
        
    op = OptionParser(
        "*-h",
        "*-c:",
        "*-H:",
        "*-d:",
        "*-f",
        "*-s:",
        "*-t:",
        "*-u",
        "*-U:",
        "*-l",
        "*--static",
        "*--stdout",
        )
    
    try:
        op.parse(sys.argv[1:])
    except OptionParser.ParseError, e:
        usage(e.message)
        
    if op.get('-h'): usage()

    if bool(op.get('-l')): USESYSLOG = True
        
    mycnf = op.getOne('-c')
    host = op.getOne('-H')
    db = op.getOne('-d')
    full = bool(op.get('-f'))
    url = op.getOne('-s')
    sf = None
    if bool(op.get('-U')):
        sf = op.getOne('-U')
        if not os.path.exists(sf):
            Logger().log("ERROR: utf-8 cleaner not found")
            sys.exit(1)
    elif bool(op.get('-u')):
        if olac:
            uf = olac.olacvar('utf8filter')
            if uf == '/null/value' or not os.path.exists(uf):
                uf = None
                Logger().log("ERROR: utf-8 cleaner not found")
                sys.exit(1)
            sf = ExternalProgram(uf, ["-q"])

    static = bool(op.get('--static'))
    stdout = bool(op.get('--stdout'))

    harvest_all(mycnf, host, db, full=full, url=url, stream_filter=sf,
                static=static, usesyslog=bool(op.get('-l')),
                stdout=stdout)