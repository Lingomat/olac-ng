from datatypes import OLACRecord
from langdata import LanguageData

class InferredMetadata():
    def __init__(self, langdata: LanguageData):
        self.langdata = langdata

    def _getOLACCodes(self, property: str, xtype: str | None, xvalue: dict | list) -> set[str]:
        codes: set[str] = set()
        xsi = '@http://www.w3.org/2001/XMLSchema-instance:type'
        if isinstance(xvalue, dict):
            if (property in xvalue) and ((xtype == None) or ((xsi in xvalue) and xvalue[xsi] == xtype)):
                codes.add(xvalue[property])
        elif isinstance(xvalue, list):
            for item in xvalue:
                coderes = self._getOLACCodes(property, xtype, item)
                if len(coderes) > 0:
                    codes = codes.union(coderes)
        return codes
    
    # We'll fix this up later
    def _isGlobalLanguage(self, langcode: str) -> bool:
        return langcode == 'eng'
    
    # The logic here is that if there are any non-global languages, we only want to keep those
    # This is because coverage/country is massively unreliable so we can't simply ignore global languages
    # if the language isn't the native country of a global language, like GB = eng
    def _filterLanguages(self, languages: set[str]) -> set[str]:
        filtered: set[str] = set()
        haveNonGlobal = False
        for lang in languages:
            if not self._isGlobalLanguage(lang):
                haveNonGlobal = True
                break
        for lang in languages:
            if haveNonGlobal:
                if not self._isGlobalLanguage(lang):
                    filtered.add(lang)
            else: 
                filtered.add(lang)
        return filtered

    def getInferred(self, olacrecord: OLACRecord) -> tuple[list[str], list[str]]:
        languages: set[str] = set()
        countries: set[str] = set()
        for metakey in olacrecord['metadata']:
            if metakey == 'dc:language' or metakey == 'dc:subject':
                langs = self._getOLACCodes(
                    '@olac:code', 'olac:language', olacrecord['metadata'][metakey])
                if len(langs) > 0:
                    for lang in langs:
                        if len(lang) == 2:
                            iso693_3 = self.langdata.iso693map.get(lang)
                            if iso693_3 is not None:
                                languages.add(iso693_3)
                        elif len(lang) == 3:
                            if lang in self.langdata.languages:
                                languages.add(lang)
                            else:
                                print('!!! Unknown language code: ' + lang)
                        else:
                            print('!!! Invalid language code length: ' + lang)
            if metakey == 'dc:coverage':
                cnts = self._getOLACCodes(
                    '#text', None, olacrecord['metadata'][metakey])
                # This field is usually free text so on the off chance it matches the full name of the country
                for cnt in cnts:
                    # In case it's an actual country code
                    if cnt in self.langdata.countries:
                        countries.add(cnt)
                        continue
                    # otherwise try to match the name
                    for country in self.langdata.countries:
                        if self.langdata.countries[country]['name'].lower() == cnt.lower():
                            countries.add(country)
                            continue
        languages = self._filterLanguages(languages)
        # add the primary country for any found languages
        for language in languages:
            langentry = self.langdata.languages[language]
            if language in self.langdata.languages and 'country' in langentry:
                countries.add(langentry['country'])
            else:
                print('!!! error: language not found in langdata: ' + language)
        return list(languages), list(countries)

