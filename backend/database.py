from typing import cast
from lxml import etree
from pymongo import MongoClient
from pymongo.collection import Collection
from datetime import datetime
from os.path import join
from csv import DictReader
from langdata import LanguageData
from datatypes import XMLArchive, FetchStatus, CustomSchemaStore, OLACArchive, OLACRecord, LanguageDB, AreaDB, CountryDB, ValidationErrors, CustomSchemaLoc
from inferred import InferredMetadata

XMLParser = etree.XMLParser(remove_blank_text=True,
                            recover=True, resolve_entities=False)
ethnologDataDirectory = 'testdata'


class OLACDatabase:
    def __init__(self, connstring):
        self.client = MongoClient(connstring)
        self.db = self.client["olac"]
        self.archives: Collection[OLACArchive] = self.db['archives']
        self.XMLarchives: Collection[XMLArchive] = self.db['XMLArchives']
        self.fetchStatus: Collection[FetchStatus] = self.db['fetchStatus']
        self.customSchemas: Collection[CustomSchemaStore] = self.db['customSchemas']
        self.records: Collection[OLACRecord] = self.db['records']
        self.languages: Collection[LanguageDB] = self.db['languages']
        self.areas: Collection[AreaDB] = self.db['areas']
        self.countries: Collection[CountryDB] = self.db['countries']
        self.langdata = LanguageData('testdata')
        self.inferred = InferredMetadata(self.langdata)

    def init(self, nuke: bool = False, rebuild: bool = False):
        print('Initialising database')
        if nuke:
            print('Nuking database')
            for coll in self.db.list_collection_names():
                self.db.drop_collection(coll)
        elif rebuild:
            print('Rebuilding languages')
            self.languages.drop()
            self.areas.drop()
            self.countries.drop()
        # Check if the archives collection exists
        if "XMLArchives" not in self.db.list_collection_names():
            self._initXMLArchives()
        if "languages" not in self.db.list_collection_names():
            self._initLanguages()
        if "records" not in self.db.list_collection_names():
            self.records.create_index('languages', sparse=True)
            self.records.create_index('countries', sparse=True)
            # for index in self.records.list_indexes():
            #     print(index)

    def _initXMLArchives(self):
        print('initialising db')
        archives = self._getArchivesFromXML()
        self.XMLarchives.insert_many(archives)

    def _initLanguages(self):
        print('initialising languages')
        areacountries: dict[str, list[str]] = {}
        arealanguages: dict[str, list[str]] = {}
        countries: list[CountryDB] = []
        # CountryID	Name	Area
        with open(join(ethnologDataDirectory, 'CountryCodes.tab'), 'r') as f:
            reader = DictReader(f, delimiter='\t')
            for row in reader:
                areaname = row['Area'].lower()
                countries.append({
                    'code': row['CountryID'],
                    'name': row['Name'],
                    'area': areaname
                })
                if areaname not in areacountries:
                    areacountries[areaname] = []
                areacountries[areaname].append(row['CountryID'])
        self.countries.insert_many(countries)

        languages: list[LanguageDB] = []
        for lang in self.langdata.getLanguages():
            thislang = self.langdata.getLanguage(lang)
            # This only works for entries from ethnologue
            if 'area' in thislang and 'country' in thislang:
                area = thislang['area'].lower()
                languages.append({
                    'code': lang,
                    'name': thislang['name'],
                    'country': thislang['country'],
                    'area': area,
                    'altNames': thislang['altNames'],
                    'dialects': thislang['dialects']
                })
                if thislang['area'] not in arealanguages:
                    arealanguages[area] = []
                arealanguages[area].append(lang)
            else:
                languages.append({
                    'code': lang,
                    'name': thislang['name'],
                    'country': None,
                    'area': None,
                    'altNames': [],
                    'dialects': []
                })

        self.languages.insert_many(languages)

        areasDB: list[AreaDB] = []
        for area in areacountries.keys():
            areasDB.append({
                'area': area,
                'countries': areacountries[area],
                'languages': arealanguages[area]  # this is lower case
            })
        self.areas.insert_many(areasDB)

    def _getArchivesFromXML(self) -> list[XMLArchive]:
        parser = etree.XMLParser(dtd_validation=False, ns_clean=True)
        tree = etree.parse("testdata/archive_list.php.xml", parser)
        archivetree = tree.getroot()
        archivelist = []
        for archiveelement in archivetree:
            archive = {
                "id": archiveelement.attrib["id"],
                "baseURL": archiveelement.attrib["baseURL"],
                "dateApproved": datetime.strptime(cast(str, archiveelement.attrib["dateApproved"]), "%Y-%m-%d")
            }
            archivelist.append(archive)
        return archivelist

    def getXMLArchive(self, id: str) -> XMLArchive | None:
        return self.XMLarchives.find_one({"id": id})

    def getArchives(self) -> list[XMLArchive]:
        return list(self.XMLarchives.find())

    def isArchiveStored(self, identifier) -> bool:
        result = self.archives.find_one({"id": identifier})
        return result is not None

    def getArchive(self, identifier: str) -> OLACArchive | None:
        return self.archives.find_one({"id": identifier})

    def storeArchive(self, identifier: str, baseurl: str, type: str, lastmodified: datetime, identify: dict, cschemas: list[CustomSchemaLoc]) -> OLACArchive | None:
        OLACArchiveDocument: OLACArchive = {
            "id": identifier,
            "baseURL": baseurl,
            "lastModified": lastmodified,
            "type": type,
            "identify": identify,
            "customSchemas": cschemas
        }
        self.archives.find_one_and_update(
            {"id": identifier}, {"$set": OLACArchiveDocument}, upsert=True)

    def hasCustomSchema(self, namespace) -> bool:
        result = self.customSchemas.find_one({"namespace": namespace})
        return result is not None

    def getCustomSchema(self, namespace: str) -> CustomSchemaStore | None:
        return self.customSchemas.find_one({"namespace": namespace})

    def storeCustomSchema(self, namespace: str, schema: bytes):
        customSchemaDocument: CustomSchemaStore = {
            "namespace": namespace,
            "schema": schema,
            "date": datetime.utcnow().replace(microsecond=0)
        }
        self.customSchemas.find_one_and_update(
            {"namespace": namespace}, {"$set": customSchemaDocument}, upsert=True)

    def getFetchStatus(self, identifier: str) -> FetchStatus | None:
        return self.fetchStatus.find_one({"id": identifier})

    def storeFetchStatus(self, identifier: str, archivetype: str, status: str = 'pending', lastfetch: datetime | None = None, lasterr: str | None = None, retryattempt: int = 0, validated: bool = False, validatereqs: bool = False, validateerror: list[ValidationErrors] = []):
        fetchStatusDocument: FetchStatus = {
            "id": identifier,
            "type": archivetype,
            "pages": 0 if archivetype == 'dynamic' else None,
            "status": status,
            "lastFetch": lastfetch,
            "lastError": lasterr,
            "retryAttempt": retryattempt,
            "validated": validated,
            "validatorPreReqs": validatereqs,
            "validateErrors": validateerror
        }
        self.fetchStatus.find_one_and_update(
            {"id": identifier}, {"$set": fetchStatusDocument}, upsert=True)

    def updateFetchStatus(self, identifier: str, update: dict) -> FetchStatus | None:
        return self.fetchStatus.find_one_and_update({"id": identifier}, {"$set": update})

    def storeRecords(self, identifier: str, records: list[dict]):
        for record in records:
            record.update({"id": identifier})
        olacrecords = cast(list[OLACRecord], records)
        self._addInferredMetadata(olacrecords)
        self.records.insert_many(olacrecords)

    def getRecords(self, identifier: str) -> list[OLACRecord] | None:
        return list(self.records.find({"id": identifier}))

    def _addInferredMetadata(self, olacrecords: list[OLACRecord]) -> list[OLACRecord]:
        for olacrecord in olacrecords:
            languages, countries = self.inferred.getInferred(olacrecord)
            if len(languages) > 0:
                olacrecord['languages'] = languages
            if len(countries) > 0:
                olacrecord['countries'] = countries
        return olacrecords
