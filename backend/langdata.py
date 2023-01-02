import csv
from typing import TypedDict, NotRequired
import json
from os.path import join


class EthnoArea(TypedDict):
    countries: list[str]
    languages: list[str]


class EthnoLanguage(TypedDict):
    name: str
    country: NotRequired[str]
    area: NotRequired[str]
    altNames: list[str]
    dialects: list[str]



class EthnoCountry(TypedDict):
    name: str
    area: str
    languages: list[str]


class AreasDB(TypedDict):
    area: str
    countries: list[str]
    languages: list[str]


class LanguagesDB(TypedDict):
    lang: str
    name: str
    country: str
    area: str


class LanguageData():
    def __init__(self, glottopath: str):
        self.areas: dict[str, EthnoArea] = {}
        self.countries: dict[str, EthnoCountry] = {}
        with open(join(glottopath, 'CountryCodes.tab'), 'r') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                self.countries[row['CountryID']] = {
                    'name':  row['Name'],
                    'area': row['Area'],
                    'languages': []
                }
                if row['Area'] not in self.areas:
                    self.areas[row['Area']] = {
                        'countries': [row['CountryID']],
                        'languages': []
                    }
                else:
                    self.areas[row['Area']]['countries'].append(
                        row['CountryID'])

        self.languages: dict[str, EthnoLanguage] = {}
        with open(join(glottopath, 'LanguageCodes.tab'), 'r') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                area = self.countries[row['CountryID']]['area']
                self.languages[row['LangID']] = {
                    'name': row['Name'],
                    'country': row['CountryID'],
                    'area': area,
                    'altNames': [],
                    'dialects': []
                }
                self.areas[area]['languages'].append(row['LangID'])
                self.countries[row['CountryID']
                               ]['languages'].append(row['LangID'])
        # process the legit iso 693-3 codes to make a 693 -> 693-3 map 
        self.iso693map: dict[str, str] = {}
        with open(join(glottopath, 'iso-639-3.tab'), 'r') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                self.iso693map[row['Part1']] = row['Id']
                if row['Id'] not in self.languages:
                    self.languages[row['Id']] = {
                        'name': row['Ref_Name'],
                        'altNames': [],
                        'dialects': []
                    }

        with open(join(glottopath, 'LanguageIndex.tab'), 'r') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                if row['LangID'] in self.languages:
                    if row['NameType'] == 'LA' and row['LangID']:
                        self.languages[row['LangID']]['altNames'].append(row['Name'])
                    elif row['NameType'] == 'D' or row['NameType'] == 'DA':
                        self.languages[row['LangID']]['dialects'].append(row['Name'])

    def getAreas(self) -> list[str]:
        return list(self.areas.keys())

    def getLanguagesForArea(self, area: str) -> list[str]:
        return self.areas[area]['languages']

    def getLanguages(self) -> list[str]:
        return list(self.languages.keys())

    def getLanguage(self, lang: str) -> EthnoLanguage:
        return self.languages[lang]

    def getCountry(self, country: str) -> EthnoCountry:
        return self.countries[country]


if __name__ == '__main__':
    ld = LanguageData('testdata')
    print(json.dumps(ld.getAreas(), indent=4))
    firstarea = ld.getAreas()[0]
    #print(json.dumps(ld.getLanguagesForArea(firstarea), indent=4))
    #print(json.dumps(ld.getCountry('AF'), indent=4))
