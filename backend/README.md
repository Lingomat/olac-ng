# OLAC-NG Backend

This backend is experimental and is not yet packaged for production. The following is a description of contents as they stand.

## Directories

- `old/` - obsolete stuff, kept because there might be some secret knowledge remaining
- `testdata/` - more accurately, this directory contains required dependencies
- `xsd/` - consolidated OLAC XSD schema to avoid external fetches
- `filestore/` - raw harvested XML is written here

## root

- `harvest.py `- imports OLACDatabase form database.py and harvests a static as a test
- `database.py` - OLACDatabase class
- `harvester_common.py` - OLACPMH class used in harvester
- `langdata.py` - LanguageData class reads Ethnologue and ISO 693-3 tables in `testdata/`
- `inferred.py` - InferredMetadata class adds language/country associations based on the metadata structure
- `testxml.py` - Intended to be imported in an interactive session to query harvested raw XML files

## `testdata/`

- archive_list.php.xml - List of current OLAC archives
- test_sr.xml - Childes complete static repo

## `old/` 

- archivelist.py - exports a list of archives based on archive_list.php.xml, seems to be integrated into database.py
- oharvester.py - the ancient OLAC one
- dbobjects.py - some SQLacademy stuff, deprecated
- catalog.xml - attempt to use the catalog mechanism to validate against pre-supplied schemas (never seemed to work) 
- testvalidate.py - one in a long line of etree validators that never worked
- testolacschema.xsd - used by testvalidate.py
- previous versions of the harvester with separate classes for static and dynamic harvesting

## Reinstall

Set up deadsnakes PPA for modern Python distributions

```
sudo apt install python3.11 python3.11-dev python3.11-venv
cd backend
mkdir testoutputs
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

To-do: move this to a Makefile

## Injecting time into Mongo

`datetime.utcnow().replace(microsecond=0)`
