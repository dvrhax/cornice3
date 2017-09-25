# vfs.py: Virtual File Systems support (zipfiles only at the moment)
# arch-tag: Virtual File Systems support
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

#import wx
import os, sys, zipfile


class Tree(object):
    class Node(object):
        def __init__(self, name):
            self.name = name
            self.children = []

    def __init__(self, filename):
        self.root = self.Node(filename)

# end of class Tree


def get_dirtree(filename):
    """
    Returns a tree corresponding to the vfs of the given filename. If the file
    can't be handled, the tree is empty
    """
    t = Tree(filename)
    if not zipfile.is_zipfile(filename):
        return t
    zf = zipfile.ZipFile(filename)
    dirs = {}
    for name in zf.namelist():
        bits = name.split('/')[:-1]
        dd = dirs
        for b in bits:
            dd = dd.setdefault(b, {})
    #print 'get_dirtree:', dirs
    def add_rec(node, d):
        for name in d:
            child = Tree.Node(name + '/')
            node.children.append(child)
            add_rec(child, d[name])
    add_rec(t.root, dirs)
    return t


def is_virtual(path):
    """\
    Returns True if the given path is a vfs.
    """
    return zipfile.is_zipfile(path.split('#zip:')[0])
