# dirctrl.py: extended version of the GenericDirCtrl
# arch-tag: extended version of the GenericDirCtrl
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

import wx
import os, glob

import vfs
import fileops
import common


class DirCtrl(wx.GenericDirCtrl):
    def __init__(self, *args, **kwds):
        wx.GenericDirCtrl.__init__(self, *args, **kwds)
        self._handler = wx.EvtHandler()
        self.PushEventHandler(self._handler)
        self._added_items = {}
        self._virtual_tree_done = {}
        self.tree = self.GetTreeCtrl()
        imglist = self.tree.GetImageList()

        folder = common.get_bitmap_for_theme('folder')
        folder_open = common.get_bitmap_for_theme('folder_open')

        if folder:
            imglist.Replace(0, folder)
        if folder_open:
            imglist.Replace(1, folder_open)
            imglist.Replace(2, folder_open)
        bmp = common.get_bitmap_for_theme('zip')
        self.zip_image = imglist.Add(bmp)
        # events
        ###wx.EVT_TREE_ITEM_EXPANDING(self._handler, self.tree.GetId(),
        ###                           self.on_expand)
        ###wx.EVT_TREE_ITEM_COLLAPSED(self._handler, self.tree.GetId(),
        ###                           self.on_collapse)
        ###wx.EVT_TREE_SEL_CHANGED(self._handler, self.tree.GetId(),
        ###                        self.on_sel_changed)

    def build_path(self, node):
        if node == self.tree.GetRootItem():
            return self.tree.GetItemText(node) or ""
        elif self.tree.GetItemParent(node) == self.tree.GetRootItem():
            return self.tree.GetItemText(node)
        return os.path.join(self.build_path(self.tree.GetItemParent(node)),
                            self.tree.GetItemText(node))

    def add_virtual_tree(self, node, path, zipfilename):
        zvfs = vfs.get_dirtree(zipfilename)
        def add_rec(n, p, vfsn):
            for vfschild in vfsn.children:
                label = vfschild.name.replace('/', '')
                child = self.tree.AppendItem(n, label, 0, 1)
                p1 = p.replace('#zip:', '/')
                if not p1.endswith('/'): p1 += '/'
                p1 += label
                if p.endswith('#zip:'): p2 = p + label
                else: p2 = p + '/' + label
                self._added_items[p1] = (p2, child)
                add_rec(child, p2, vfschild)
        add_rec(node, path, zvfs.root)
        self._virtual_tree_done[path] = 1

    def on_expand(self, event):
        item = event.GetItem()
        if item.Ok():
            path = self.build_path(item)
            if path in self._added_items:
                return
            def go():
                # first search the subdirs without children, in case there
                # are some zipfiles there aswell (otherwise it will be
                # impossible to select them)
                if wx.VERSION[:2] >= (2, 5):
                    child, cookie = self.tree.GetFirstChild(item)
                else:
                    child, cookie = self.tree.GetFirstChild(item, 0)
                while True:
                    if not child.Ok(): break
                    if not self.tree.ItemHasChildren(child):
                        if glob.glob(os.path.join(
                            path, self.tree.GetItemText(child), '*.zip')):
                            self.tree.SetItemHasChildren(child)
                    child, cookie = self.tree.GetNextChild(item, cookie)
                # then add the zipfiles on this directory
                for name in glob.glob(os.path.join(path, '*.zip')):
                    i = self.tree.AppendItem(item, os.path.basename(name),
                                             self.zip_image)
                    self._added_items[name] = (name + '#zip:', i)
                
            wx.CallAfter(go)
        event.Skip()

    def on_collapse(self, event):
        item = event.GetItem()
        if self.build_path(item) in self._added_items:
            return
        event.Skip()

    def on_sel_changed(self, event):
        item = event.GetItem()
        path = self.build_path(item)
        if path in self._added_items:
            p, n = self._added_items[path]
            if p.endswith('#zip:') and p not in self._virtual_tree_done:
                self.add_virtual_tree(n, p, path)
        event.Skip()

    def GetPath(self):
        item = self.tree.GetSelection()
        if item != self.tree.GetRootItem():
            path = self.build_path(item)
            if path in self._added_items:
                return self._added_items[path][0]
        return wx.GenericDirCtrl.GetPath(self)

    def SetPath(self, path):
        index = path.find('#zip:')
        if index != -1: 
            if index == len(path)-5:
                path = path[:-5]
            else:
                path = path.replace('#zip:', '/')
            if path in self._added_items:
                item = self._added_items[path][1]
                self.tree.SelectItem(item)
                self.tree.EnsureVisible(item)
                return
            else:
                if vfs.is_virtual(path):
                    wx.GenericDirCtrl.SetPath(self, path)
                    # this is a zipfile, but not added to the tree yet:
                    # add it now...
                    if path.endswith('.zip'):
                        self.tree.SetItemHasChildren(self.tree.GetSelection(),
                                                     True)
                        self.tree.Expand(self.tree.GetSelection())
                        wx.CallAfter(self.SetPath, path + '#zip:')
                    return
        wx.GenericDirCtrl.SetPath(self, path)
        pth = wx.GenericDirCtrl.GetPath(self)
        def issame(p1, p2):
            try: return os.path.samefile(pth, path)
            except OSError: return False
        if not issame(pth, path):
            print("Unselecting all:", pth, path)
            self.tree.UnselectAll()

    def up_dir(self):
        sel = self.tree.GetSelection()
        if not sel.Ok(): return
        sel = self.tree.GetItemParent(sel)
        if not sel.Ok() or sel == self.tree.GetRootItem(): return
        self.tree.SelectItem(sel)

# end of class DirCtrl
