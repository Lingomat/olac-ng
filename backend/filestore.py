from os.path import join, basename, isfile, isdir
from os import makedirs

class FileStore():
    def __init__(self, fspath: str):
        self.fspath = fspath

    def storeFile(self, id: str, fullurl: str, data: bytes) -> None:
        dirpath = join(self.fspath, id)
        if not isdir(dirpath):
            makedirs(dirpath)
        path = join(self.fspath, id, basename(fullurl))
        with open(path, 'wb') as f:
            f.write(data)
        
    def getFile(self, id: str, fullurl: str) -> bytes | None:
        path = join(self.fspath, id, basename(fullurl))
        if not isfile(path):
            return None
        with open(path, 'rb') as f:
            return f.read()
        
    def nuke(self) -> None:
        print('not implemented yet')

