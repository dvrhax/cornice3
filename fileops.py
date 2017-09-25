# fileops.py: filesystem operations, with virtual fs support (zipfiles only
# at the moment)
# arch-tag: filesystem operations, with virtual fs support
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

#import wx
#import Image
import os, stat, time#, dircache
import zipfile, io
import urllib.request, urllib.parse, urllib.error

import picture, collection

__all__ = ['isdir', 'normpath', 'listdir', 'get_path_info',
           'open', 'get_icon_index']


def _check_end(path):
    return path.endswith('#zip:') or path.endswith('/')


def is_collection(path):
    return path.startswith('collection:')

def isdir(path):
    path = path.strip()
    if os.path.isdir(path) or \
       is_collection(path) or \
       (zipfile.is_zipfile(path.split('#zip:')[0]) and _check_end(path)):
        return True
    return False


def isfile(path):
    path = path.strip()
    if os.path.isfile(path) or \
       (zipfile.is_zipfile(path.split('#zip:')[0]) and not _check_end(path)):
        return True
    return False


def normpath(path):
    """\
    Returns a normalized version of the path. If it is virtual, it is not
    changed.
    """
    if os.path.isdir(path):
        path = os.path.normpath(path)
        if path and path[-1] != os.sep: path += os.sep
    return path


def basename(path):
    """\
    like os.path.basename, but understands also virtual file systems
    """
    if zipfile.is_zipfile(path.split('#zip:')[0]):
        path = path[path.find('#zip:')+5:]
        return path.split('/')[-1]
    return os.path.basename(path)


def dirname(path):
    """\
    like os.path.dirname, but understands also virtual file systems
    """
    if zipfile.is_zipfile(path.split('#zip:')[0]):
        z = path.find('#zip:')
        s = path.rfind('/')
        if s > z: return path[:s]
        else: return path[:z+5]
    return os.path.dirname(path)

    
def listdir(path):
    """\
    like os.listdir, but it works also for zipfiles (and in this case it
    returns only files, not subdirs)
    """
    out = []
    if os.path.isdir(path):
        #if os.name == 'nt': l = os.listdir(path) # dircache bug on win32??
        #else: l = dircache.listdir(path)
        l = os.listdir(path)
        for f in l:
            try:
                fullname = os.path.join(path, f)
                info = get_path_info(fullname)
                out.append(picture.Picture(fullname, info))
            except:
                pass
        return out
    elif path.startswith('collection:'):
        print('OK, setting path!', path)
        path = path[11:]
        print('path now:', path)
        if not path or path[0] != '?':
            return []
        params = {}
        for elem in path[1:].split('&'):
            key, val = [urllib.parse.unquote(s) for s in elem.split('=')]
            params[key] = val
        for res in collection.query(params):
            try:
                info = get_path_info(str(res[0]))
                img = picture.Picture(res[0], info)
                img.name = res[1]
                out.append(img)
            except:
                import traceback; traceback.print_exc()
        return out
    else:
        try:
            z, p = path.split('#zip:', 1)
        except ValueError as e:
            # this can happen if path is not a valid path at all (neither a
            # directory nor a valid zipfile...
            return []
        if not zipfile.is_zipfile(z):
            return []
        # otherwise, build the list of files in the archive
        # (no cache for now...)
        zf = zipfile.ZipFile(z)
        #ret = []
        if p and p[-1] != '/': p += '/'
        for name in zf.namelist():
            if name.startswith(p):
                name = name[len(p):]
                if name and '/' not in name:
                    try:
                        fullname = os.path.join(path, name)
                        info = get_path_info(fullname)
                        out.append(picture.Picture(fullname, info))
                    except:
                        pass
                    #print 'adding', name, 'to listdir'
                    #ret.append(name)
        return out #ret


class _PathInfo(object):
    __slots__ = ['isfile', 'size', 'mtime']

    def __init__(self, isfile, size=None, mtime=None):
        self.isfile = isfile
        self.size = size
        self.mtime = mtime

# end of class _PathInfo


def get_path_info(path):
    """\
    Returns information about the given path, in the form of a _PathInfo
    struct, with fields: isfile, size, mtime
    """
    try:
        info = os.stat(path)
        isfile = stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
        return _PathInfo(isfile, info.st_size, info.st_mtime)
    except OSError:
        #print 'getting info for', path
        p, name = path.split('#zip:', 1)
        if name.startswith('/'): name = name[1:]
        if not zipfile.is_zipfile(p):
            raise
        # otherwise, let's try to build the info ourselves...
        zf = zipfile.ZipFile(p)
        if zf is None:
            # this shouldn't happen, but it can (if the file has been deleted
            # for example)
            raise
        info = zf.getinfo(name)
        return _PathInfo(True, info.file_size,
                         int(time.mktime(info.date_time + (0, 1, -1))))



_builtinopen = open

def open(filename, mode='rb'):
    """\
    Replacement for the built-in open that understands virtual file system
    (zipfile only at the moment)
    """
    try:
        return _builtinopen(filename, mode)
    except IOError:
        path, name = filename.split('#zip:', 1)
        if name.startswith('/'): name = name[1:]
        zf = zipfile.ZipFile(path)
        f = io.StringIO(zf.read(name))
        zf.close()
        return f


def unlink(path):
    if isfile(path) and '#zip:' in path:
        import errno
        raise OSError(errno.EPERM, _("Can't delete on a virtual filesystem"))
    os.unlink(path)


def get_icon_index(path):
    """\
    Returns the index in the imagelist of bookmarksctrl of the icon associated
    with this path
    """
    if zipfile.is_zipfile(path.split('#zip:')[0]): return 1
    return 0


def delete_from(path, files):
    if not is_collection(path):
        for name in files:
            try:
                unlink(name)
            except (IOError, OSError) as e:
                #import traceback; traceback.print_exc(e)
                wx.LogError(str(e))
    else:
        path = path[11:]
        if path and path[0] == '?':
            params = {}
            for elem in path[1:].split('&'):
                key, val = [urllib.parse.unquote(s) for s in elem.split('=')]
                params[key] = val
            collection.remove_from(params, files)
