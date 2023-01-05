from database import OLACDatabase, XMLArchive
from os.path import splitext
from harvester_common import OLACHarvester
from validator import OLACValidator
from util import secondsToTimeString
import time
import argparse
from sys import exit

def harvest(db: OLACDatabase, harvest: list[str] | None = None, force: bool = False):
    if harvest is not None:
        for single in harvest:
            archive = db.getXMLArchive(single)
            if archive is None:
                print('archive', single, 'not found')
            else:
                harvest_one(db, archive, force)
    else:
        harvestAll(db, force)

def harvestAll(db: OLACDatabase, force: bool = False):
    archivelist = db.getArchives()
    sucesscount = 0
    start = time.time()
    for archive in archivelist:
        harvestsuccess = harvest_one(db, archive, force)
        if harvestsuccess:
            sucesscount += 1
    elapsed = time.time() - start
    print('harvested', sucesscount, 'of', len(archivelist), 'archives in ', secondsToTimeString(elapsed))

def harvest_one(db: OLACDatabase, archive: XMLArchive, force: bool = False) -> bool:
    archivetype = 'static' if splitext(archive['baseURL'])[1] == '.xml' else 'dynamic'
    harvester = OLACHarvester(db, archive)
    status = harvester.harvest(force)
    if status is None or status['status'] == 'failed':
        print('!!! failed to harvest', archive['id'])
        return False
    if status['validated'] is True and not force:
        print('- archive is already validated')
    elif status['validated'] is False and len(status['validateErrors']) > 0:
        print('- archive previously failed validation')
    else: 
        print('- validating', archivetype, 'repository')
        validator = OLACValidator(db, archive['id'])
        isvalid = validator.validate()
        print('- archive is', 'valid' if isvalid else 'invalid')
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Execute the OLAC Harvester')
    parser.add_argument('--db', type=str, help='The database connection string', required=False, default='mongodb://olacdb:olacdbmonkey@127.0.0.1:27027') 
    parser.add_argument('--harvest', type=str, help='Archives to harverst', required=False, nargs='*', default=None) 
    parser.add_argument('--nuke', help='Nuke the database', required=False, action='store_true')
    parser.add_argument('--force', help='Force harvest', required=False, action='store_true')
    parser.add_argument('--initonly', help='Only initialise db', required=False, action='store_true')
    parser.add_argument('--rebuild', help='Rebuild languages', required=False, action='store_true')
    args = parser.parse_args()
    db = OLACDatabase(args.db)

    db.init(args.nuke, args.rebuild)
    if args.initonly:
        print('Only initialising db')
        exit()
    harvest(db, args.harvest, args.force)
    

