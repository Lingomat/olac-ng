# Experiments

## directories

- old obsolete stuff
- testdata imported data for testing
- testoutputs written data for inspecting outputs
- xsd various xsd schema, a bit of a mess

## old 

- archivelist.py - exports a list of archives based on archive_list.php.xml, seems to be integrated into database.py
- oharvester.py - the ancient OLAC one
- dbobjects.py - some SQLacademy stuff, deprecated
- catalog.xml - attempt to use the catalog mechanism to validate against pre-supplied schemas (never seemed to work) 
- testvalidate.py - one in a long line of etree validators that never worked
- testolacschema.xsd - used by testvalidate.py


## current ?

- harvester.py - imports OLACDatabase form database.py and harvests a static as a test
- database.py - OLACDatabase on start imports archive_list.php.xml and injects it into Mongo
- oaipmh.py - OLACPMH class and OLACStatic used in harvester
- testvalidate.py
- testvalidate2.py - seems to be a working validator

## testdata

- archive_list.php.xml - List of current OLAC archives
- test_sr.xml - Childes complete static repo

## xsd

- childes.xsd - olac extension schema for childes used to thrash out static validation for an olac extension schema


## reinstall (makefile)

```
apt python3.10 python3.10-dev python3.10-venv
python3.10 -m venv .venv
~pip install -e ./sickle~
pip install pymongo
pip install requests-cache
pip install zstandard
pip install xmltodict
```

## Injecting time into Mongo

`datetime.utcnow().replace(microsecond=0)`
