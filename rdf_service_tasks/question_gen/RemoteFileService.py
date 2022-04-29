# RemoteFileService.py

import binascii
import io
from urllib.request import urlopen

from fs import open_fs, opener
from fs.base import FS
from fs.info import Info
import fs.errors
import fs.path

import fs.opener
from fs.opener import Opener
from fs.opener.errors import OpenerError  # https://docs.pyfilesystem.org/en/latest/extension.html#extension


from rdflib import Graph, RDF



PATH_SEPARATORS = "/\\#;:";
PATH_LEGAL_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-";
PATH_ILLEGAL_NAMES = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",};  # in Windows



class HttpReadOnlyFS(FS):
    'Simple reader of data from remote HTTP location'
    def __init__(self, base, *args, **kw):
        super().__init__()
        self.base = base
    def getinfo(self, path, namespaces=None):
        return Info({})
    def listdir(self, path):
        return ['.']
    def makedir(self, path, permissions=None, recreate=False):
        # no dir created
        newpath = fs.path.combine(self.base, path)
        return type(self)(newpath)
    def openbin(self, path, mode='r', buffering=-1, **options):
        try:
            # read all data into memory
            data = urlopen(fs.path.combine(self.base, path)).read()
            return io.BytesIO(data)
        except Exception as e:
            raise fs.errors.FSError(str(e))
    def remove(self, path):
        raise fs.errors.ResourceNotFound('Deletion not supported')
    def removedir(self, path):
        raise fs.errors.ResourceNotFound('Deletion not supported')
    def setinfo(self, path, info):
        raise fs.errors.ResourceNotFound('Update operations not supported')


class HttpOpener(Opener):
    protocols = ['http']

    def open_fs(self, fs_url, parse_result, writeable, create, cwd):
        # bucket_name, _, dir_path = parse_result.resource.partition('/')
        # if not bucket_name:
        #     raise OpenerError(
        #         "invalid bucket name in '{}'".format(fs_url)
        #     )
        httpfs = HttpReadOnlyFS(
            fs_url
        )
        return httpfs

# global code:
fs.opener.registry.install(HttpOpener)


class RemoteFileService:
    def __init__(self, upload_base, download_base=None, dummyDirsForNewFile=2):
        download_base = download_base or upload_base
        self.dummyDirsForNewFile = dummyDirsForNewFile
        self.fs_download = open_fs(download_base)
        self.fs_upload   = open_fs(upload_base, create=False)
    def fetchModel(self, fullname) -> Graph:
        print('    fetchModel:', fullname)
        try:
	        stream = self.fs_download.openbin(fullname)
	        ttl = stream.read().decode()
	        return Graph().parse(format='n3', data=ttl)
        except fs.errors.ResourceNotFound:
	        print('              `-- not found')
        	return None
    def sendModel(self, fullname, g: Graph):
        print('    sendModel:', fullname)
        self.fs_upload.makedirs(fs.path.split(fullname)[0], recreate=True)
        self.fs_upload.writetext(fullname, g.serialize(format="turtle"))

    def insertDummyDirs(self, filepath):
        if (self.dummyDirsForNewFile <= 0):
            return filepath;

        # h = hash(filepath);
        h = binascii.crc32(filepath.encode('utf8')) & 0xffffffff  # same hash as in my Java code
        W, mask = 4, 0x0f
        dummy = ''.join('%x/' % (mask & (h >> W * i)) for i in range(self.dummyDirsForNewFile));

        slashIndex = filepath.rfind('/');
        return filepath[0:slashIndex + 1] + dummy + filepath[slashIndex + 1:];
    def prepareNameForFile(self, name, __makeUnique=False):
        try:
            name = self.normalizeName(name);
            name = self.insertDummyDirs(name);
            # if (makeUnique):
            #     name = self.uniqualizeName(name);
            return name;
        except Exception as e:
            print("    [WARN] in prepareNameForFile('%s'):" % name, e)
            return None
    def normalizeName(self, p):
        whole = "";
        word = "";
        previousNormal = True;
        for h in p:
            if h in PATH_SEPARATORS:
                if word:
                    if word.upper() in PATH_ILLEGAL_NAMES:
                        word += "_";  # avoid illegal names in Windows
                    whole += word + "/";
                    word = ''
                continue;
            if h not in PATH_LEGAL_CHARS:
                if (previousNormal):
                    word += "_";
                previousNormal = False;
            else:
                word += h;
                previousNormal = True;

        if word:
            if word.upper() in PATH_ILLEGAL_NAMES:
                word += "_";  # avoid illegal names in Windows
            whole += word;
        return whole


if __name__ == '__main__':

    # example

    FTP_BASE = "ftp://user:<pass>@vds84.server-1.biz/home/poas/ftp_dir/compp/control_flow";
    FTP_DOWNLOAD_BASE = "http://vds84.server-1.biz/misc/ftp/compp/control_flow";

    fileService = RemoteFileService(FTP_BASE, FTP_DOWNLOAD_BASE)
