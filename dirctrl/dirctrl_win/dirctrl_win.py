# dirctrl.py: versione migliorata di wx.GenericDirCtrl specifica per windows
# autore: Alberto Griggio <agriggio@users.sourceforge.net>
# data di creazione: 2004-10-09

import os
import wx
from . import _dirctrlhelper as _dc


class _DirItemInfo:
    def __init__(self, attrs):
        self.pidl = attrs[0]
        self.path = attrs[1]
        self.display_name = attrs[2]
        self.icon_info = tuple(attrs[3:5])
        self.open_icon_info = tuple(attrs[5:7])
        self.has_subfolders = attrs[7]
        self.special_sort_index = attrs[8]

# end of class _DirItemInfo


class DirCtrl(wx.TreeCtrl):
    def __init__(self, parent, id=-1, path=None, style=wx.SUNKEN_BORDER):
        wx.TreeCtrl.__init__(self, parent, id, style=style|wx.TR_DEFAULT_STYLE)
        self.path = None
        root = _DirItemInfo(_dc.get_root())
        self.imglist = wx.ImageList(16, 16)
        self.icons = {} # dizionario delle icone presenti in imglist, con
                        # chiave (location, index)
        self._added = {} # insieme di cartelle gia' processate
                         # (cioe' il contenuto delle quali e' gia'
                         # stato aggiunto all'albero)
        self.AssignImageList(self.imglist)

        self._add_icons(root)
        
        r = self.AddRoot(root.display_name, self.icons[root.icon_info])
        self.SetPyData(r, root)
        self.SetItemImage(r, self.icons[root.open_icon_info],
                          wx.TreeItemIcon_Expanded)
        self.SetItemHasChildren(r, root.has_subfolders)
        wx.EVT_TREE_ITEM_EXPANDING(self, -1, self.on_expanding)
        wx.EVT_TREE_ITEM_COLLAPSED(self, -1, self.on_collapsed)
        wx.EVT_TREE_SEL_CHANGING(self, -1, self.on_sel_changing)

        if path is not None:
            self.SetPath(path)
        else:
            self.SelectItem(r)

    #--------------------------------------------------------------------------
    # Interfaccia (identica a quella di wx.GenericTreeCtrl, ma alcuni metodi
    # non fanno nulla)
    #--------------------------------------------------------------------------

    def ExpandPath(self, path):
        while path and not os.path.isdir(path):
            p = os.path.dirname(path)
            if p != path:
                path = p
            else:
                return False
        if path:
            self.SetPath(path)
            return True
        else:
            return False

    def GetPath(self):
        return self.path

    def GetDefaultPath(self):
        return self.path

    def GetFilePath(self):
        return ""

    def GetFilter(self):
        return ""

    def GetFilterIndex(self):
        return -1

    def GetFilterListCtrl(self):
        return None

    def GetRootId(self):
        return self.GetRootItem()

    def GetTreeCtrl(self):
        return self

    def SetPath(self, path):
        return self._set_path(path)

    def SetDefaultPath(self, path):
        pass

    def SetFilter(self, filter):
        pass

    def SetFilterIndex(self, index):
        pass

    def ShowHidden(self, yes):
        pass

    #--------------------------------------------------------------------------
    # da qui in poi implementazione
    #--------------------------------------------------------------------------

    def Destroy(self):
        self._free_pidls(self.GetRootItem(), 0)

    def on_expanding(self, event):
        if not wx.IsBusy():
            wx.BeginBusyCursor()
        item = event.GetItem()
        if item.Ok():
            iteminfo = self.GetPyData(event.GetItem())
            # aggiungiamo il contenuto della cartella all'albero
            # lo facciamo tutte le volte in modo che se i contenuti cambiano
            # si puo' fare refresh collassando e espandendo il nodo...
            if iteminfo.pidl not in self._added:
                try:
##                     contents = [(c[2].lower(), _DirItemInfo(c)) for c in
##                                 _dc.get_subfolders_of(iteminfo.pidl)]
                    contents = [(c[8], c[1].lower(), c[2], _DirItemInfo(c))
                                for c in _dc.get_subfolders_of(iteminfo.pidl)]
                    contents.sort()
                    #contents = [c[1] for c in contents]
                    for s, n1, n2, i in contents:
                        #print s, n, i.pidl
                        self._add_item(item, i)
                    if not contents:
                        self.SetItemHasChildren(item, False)
                except Exception as xxx_todo_changeme:
                    #print "PYTHON, EXCEPTION:", errno, strerr
                    (errno, strerr) = xxx_todo_changeme.args
                    #print "PYTHON, EXCEPTION:", errno, strerr
                    if errno:
                        wx.MessageBox(strerr, "Errore",
                                      style=wx.OK|wx.ICON_ERROR)
                    self.SetItemHasChildren(item, False)
                self._added[iteminfo.pidl] = 1
        if wx.IsBusy():
            wx.EndBusyCursor()
        event.Skip()

    def on_sel_changing(self, event):
        item = event.GetItem()
        if item.Ok():
            iteminfo = self.GetPyData(item)
            if iteminfo.path:
                self.path = os.path.normcase(os.path.normpath(iteminfo.path))
            else:
                self.path = ""
        event.Skip()

    def on_collapsed(self, event):
        item = event.GetItem()
        iteminfo = self.GetPyData(item)
        if iteminfo.pidl in self._added:  
            self._free_pidls(item, 0)
            del self._added[iteminfo.pidl]
        self.DeleteChildren(item)
        event.Skip()

    def _get_first_child(self, item, cookie):
        if wx.VERSION[:2] >= (2, 5):
            return self.GetFirstChild(item)
        else:
            return self.GetFirstChild(item, cookie)

    def _free_pidls(self, item, cookie):
        c, cookie = self._get_first_child(item, cookie)
        while c.Ok():
            data = self.GetPyData(c)
            try: del self._added[data.pidl]
            except KeyError: pass
            _dc.free_pidl(data.pidl)
            if wx.VERSION[:2] < (2, 5): cookie += 1
            self._free_pidls(c, cookie)
            c, cookie = self.GetNextChild(item, cookie)

    def _add_item(self, parent, iteminfo):
        self._add_icons(iteminfo)
        i = self.AppendItem(parent, iteminfo.display_name,
                            self.icons[iteminfo.icon_info])
        self.SetPyData(i, iteminfo)
        self.SetItemImage(i, self.icons[iteminfo.open_icon_info],
                          wx.TreeItemIcon_Expanded)
        self.SetItemHasChildren(i, iteminfo.has_subfolders)

    def _add_icons(self, iteminfo):
        log_null = wx.LogNull()
        retval = True
        if iteminfo.icon_info not in self.icons:
            icon = wx.EmptyIcon()
            icon.SetSize((16, 16))
            hicon = _dc.get_hicon(iteminfo.pidl, 0)
            icon.SetHandle(hicon)
##             icon.SetDepth(32)
##             print 'Depth of normal icon:', icon.GetDepth()
            res = self.imglist.AddIcon(icon)
            self.icons[iteminfo.icon_info] = res
            if res < 0: retval = False
        if iteminfo.open_icon_info not in self.icons:
            icon = wx.EmptyIcon()
            icon.SetSize((16, 16))
            hicon = _dc.get_hicon(iteminfo.pidl, 1)
            icon.SetHandle(hicon)
            res = self.imglist.AddIcon(icon)
            self.icons[iteminfo.open_icon_info] = res
            if res < 0: retval = False
        return retval

    def _set_path(self, path):
        if path and os.path.isdir(path):
            path = os.path.normcase(os.path.normpath(path))
            if path == self.path:
                return
            def do_rec(item):
                cookie = 0
                while item.Ok():
                    iteminfo = self.GetPyData(item)
                    itempath = os.path.normcase(os.path.normpath(
                        iteminfo.path))
##                     print itempath, ("'%s'" % iteminfo.path),
##                     print iteminfo.display_name
                    if not iteminfo.path:
                        if iteminfo.has_subfolders:
                            self.Expand(item)
                            child, cookie = self._get_first_child(item, cookie)
                            if do_rec(child):
                                return True
                            else:
                                self.Collapse(item)
                                item = self.GetNextSibling(item)
                        else:
                            item = self.GetNextSibling(item)
                    elif path == itempath:
                        self.path = path
                        self.SelectItem(item)
                        self.EnsureVisible(item)
                        return True
                    elif self.check_prefix(path, itempath):
##                         print 'OK, vado sotto...', itempath
                        self.Expand(item)
                        item, cookie = self._get_first_child(item, cookie)
                    else:
##                         print 'avanti:', itempath
                        item = self.GetNextSibling(item)
                return False
            # special case per il desktop
            item = self.GetRootItem()
            desktop = self.GetPyData(item)
            if path == os.path.normcase(os.path.normpath(desktop.path)):
                self.path = path
                self.SelectItem(desktop)
            else:
                self.Expand(item)
                item, c = self._get_first_child(item, 0)
                do_rec(item)

    def check_prefix(self, path, itempath):
        prefix = os.path.commonprefix([path, itempath])
        return prefix == itempath and (
            path[len(prefix):].startswith(os.sep) or prefix.endswith(os.sep))
    
# end of class DirCtrl


if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = wx.Frame(None, -1,
                     "Prova DirCtrl - wxPython %s" % wx.VERSION_STRING,
                     size=(350, 500))
    tree = DirCtrl(frame, -1)
    icon = wx.EmptyIcon()
    icon.SetSize((16, 16))
    icon.SetHandle(_dc.get_hicon(0, 0))
    frame.SetIcon(icon)
    import sys
    tree.SetPath(sys.argv[1]) #os.getcwd())

    def on_item_selected(event):
        print('selected:', tree.GetPath())

    wx.EVT_TREE_SEL_CHANGED(tree.GetTreeCtrl(), -1, on_item_selected)
    
    app.SetTopWindow(frame)
    frame.Show()

    app.MainLoop()
