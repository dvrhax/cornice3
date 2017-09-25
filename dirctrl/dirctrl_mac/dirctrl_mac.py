# dirctrl_mac.py: versione migliorata di wx.GenericDirCtrl specifica per mac
# autore: Alberto Griggio <agriggio@users.sourceforge.net>
# data di creazione: 2005-01-04

import os
import wx
import _dirctrlmac_helper as _dc
from . import icons


class _DirItemInfo(object):
    def __init__(self, path, display_name, has_subfolders=True,
                 icon_index=0):
        self.path = path
        self.display_name = display_name
        self.has_subfolders = has_subfolders
        self.icon_index = icon_index

    def get_subdirs(self, hidden=False):
        tmp = [(j.lower(), (i, j)) for (i, j) in
               _dc.enum_folder(self.path, hidden)]
        tmp.sort()
        if not hidden:
            return [_DirItemInfo(*i[1]) for i in tmp
                    if not i[0].startswith('.')]
        else:
            return [_DirItemInfo(*i[1]) for i in tmp]

    def matches_path(self, path):
##         print 'matches_path(%s): %s, %s' % (self.display_name, self.path, path)
        if _check_prefix(self.path, path):
            return len(os.path.commonprefix([self.path, path]))
        return -1

# end of class _DirItemInfo


class _UserDesktopItemInfo(_DirItemInfo):
    def __init__(self):
        super(_UserDesktopItemInfo, self).__init__(*_dc.get_user_desktop())
        self.icon_index = 1

# end of class _UserDesktopItemInfo


class _UserHomeItemInfo(_DirItemInfo):
    def __init__(self):
        super(_UserHomeItemInfo, self).__init__(*_dc.get_user_home())
        self.icon_index = 2
    
# end of class _UserHomeItemInfo


class _VolumesItemInfo(_DirItemInfo):
    def __init__(self):
        super(_VolumesItemInfo, self).__init__("", "Volumi")
        self.icon_index = 3

    def get_subdirs(self, hidden=False):
        return [_DirItemInfo(*(vol + (True, self.icon_index)))
                for vol in _dc.enum_volumes()]

    def matches_path(self, path):
        def _mp(p):
##             print 'matches_path(%s): %s, %s' % (self.display_name, p, path)
            if _check_prefix(p, path):
                return len(os.path.commonprefix([p, path]))
            return -1
        return max([_mp(info.path) for info in self.get_subdirs()])

# end of class _VolumesItemInfo


class _RootItemInfo(_DirItemInfo):
    def __init__(self):
        try:
            import socket
            name = socket.gethostname().split('.')[0]
        except Exception as e:
            print('Exception while determining host name:', e)
            name = 'Computer'
        super(_RootItemInfo, self).__init__("", name)
        self.icon_index = 4
        
    def get_subdirs(self, hidden=False):
        return [_UserDesktopItemInfo(), _UserHomeItemInfo(),
                _VolumesItemInfo()]
        
    def matches_path(self, path):
        def _mp(p):
            if _check_prefix(p, path):
                return len(os.path.commonprefix([p, path]))
            return -1
        return max([_mp(info.path) for info in self.get_subdirs()])

# end of class _RootItemInfo


def _check_prefix(p1, p2):
    if p1 == p2:
        return True
    prefix = os.path.commonprefix([p1, p2])
##     print 'prefix(%s, %s): %s' % (p1, p2, prefix)
##     print '\t%s: "%s", %s' % (len(prefix), p1[len(prefix):], os.sep)
    return (len(p1) > len(p2) and p1 or p2)[len(prefix):].startswith(os.sep) \
           or prefix.endswith(os.sep)


class DirCtrl(wx.TreeCtrl):
    def __init__(self, parent, id=-1, path=None, style=wx.SUNKEN_BORDER):
        style = style|wx.TR_DEFAULT_STYLE
        style &= ~wx.TR_ROW_LINES
        wx.TreeCtrl.__init__(self, parent, id, style=style)
        self.path = None
        self._show_hidden = False
        root = _RootItemInfo()
        self.imglist = wx.ImageList(16, 16)
        self.icons = {} # dizionario delle icone presenti in imglist, con
                        # chiave (location, index)
        self._added = {} # insieme di cartelle gia' processate
                         # (cioe' il contenuto delle quali e' gia'
                         # stato aggiunto all'albero)
        self.AssignImageList(self.imglist)

        self._add_icons(root)
        
        r = self.AddRoot(root.display_name, self.icons[root.icon_index])
        self.SetPyData(r, root)
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

    def ShowHidden(self, hidden=True):
        if self._show_hidden != hidden:
            self._show_hidden = hidden
            path = self.path
            self.path = ""
            self.Freeze()
            self.Collapse(self.GetRootItem())
            self.SetPath(path)
            self.Thaw()

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

    #--------------------------------------------------------------------------
    # da qui in poi implementazione
    #--------------------------------------------------------------------------

    def on_expanding(self, event):
        if not wx.IsBusy():
            wx.BeginBusyCursor()
        item = event.GetItem()
        if item.Ok():
            iteminfo = self.GetPyData(event.GetItem())
            # aggiungiamo il contenuto della cartella all'albero
            # lo facciamo tutte le volte in modo che se i contenuti cambiano
            # si puo' fare refresh collassando e espandendo il nodo...
            if id(iteminfo) not in self._added:
                try:
                    contents = iteminfo.get_subdirs(self._show_hidden)
                    for i in contents:
                        self._add_item(item, i)
                    if not contents:
                        self.SetItemHasChildren(item, False)
                except OSError as e:
                    #print "PYTHON, EXCEPTION:", errno, strerr
                    wx.MessageBox(str(e), "Errore",
                                  style=wx.OK|wx.ICON_ERROR)
                    self.SetItemHasChildren(item, False)
                except Exception:
                    import traceback
                    traceback.print_exc()
                    self.SetItemHasChildren(item, False)                    
                self._added[id(iteminfo)] = 1
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
        if id(iteminfo) in self._added:  
            del self._added[id(iteminfo)]
        self.DeleteChildren(item)
        event.Skip()

    def _get_first_child(self, item, cookie):
        if wx.VERSION[:2] >= (2, 5):
            return self.GetFirstChild(item)
        else:
            return self.GetFirstChild(item, cookie)

    def _add_item(self, parent, iteminfo):
        self._add_icons(iteminfo)
        i = self.AppendItem(parent, iteminfo.display_name,
                            self.icons[iteminfo.icon_index])
        self.SetPyData(i, iteminfo)
        self.SetItemHasChildren(i, iteminfo.has_subfolders)

    def _add_icons(self, iteminfo):
        log_null = wx.LogNull()
        retval = True
        if iteminfo.icon_index not in self.icons:
            try:
                key = icons.index[iteminfo.icon_index]
                icon = icons.catalog[key].getIcon()
                res = self.imglist.AddIcon(icon)
                self.icons[iteminfo.icon_index] = res
                if res < 0: retval = False
            except (TypeError, IndexError, KeyError):
                import traceback
                traceback.print_exc()
                retval = False
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

            item = self.GetRootItem()
            self.Expand(item)
            def pick_best(start):
                item, c = self._get_first_child(start, 0)
                if not item.Ok():
                    return start
                start = item
                iteminfo = self.GetPyData(item)
                match = iteminfo.matches_path(path)
##                 print 'match con %s: %s' % (iteminfo.display_name, match)
                while item.Ok():
                    item = self.GetNextSibling(item)
                    if not item.Ok():
                        break
                    iteminfo = self.GetPyData(item)
                    m = iteminfo.matches_path(path)
##                     print 'match con %s: %s' % (iteminfo.display_name, match)
                    if m > match:
                        start = item
                        match = m
                return start

            start = pick_best(item)
            iteminfo = self.GetPyData(start)
            if isinstance(iteminfo, _VolumesItemInfo):
                self.Expand(start)
                start = pick_best(start)

            do_rec(start)

    def check_prefix(self, path, itempath):
        prefix = os.path.commonprefix([path, itempath])
        return prefix == itempath and (
            path[len(prefix):].startswith(os.sep) or prefix.endswith(os.sep))
    
##     def _set_path(self, path):
##         if path and os.path.isdir(path):
##             path = os.path.normcase(os.path.normpath(path))
##             if path == self.path:
##                 return
##             def do_rec(item):
##                 cookie = 0
##                 while item.Ok():
##                     iteminfo = self.GetPyData(item)
##                     itempath = os.path.normcase(os.path.normpath(
##                         iteminfo.path))
##                     print itempath, ("'%s'" % iteminfo.path),
##                     print iteminfo.display_name
##                     if not iteminfo.path:
##                         if iteminfo.has_subfolders:
##                             self.Expand(item)
##                             child, cookie = self._get_first_child(item, cookie)
##                             if do_rec(child):
##                                 return True
##                             else:
##                                 self.Collapse(item)
##                                 item = self.GetNextSibling(item)
##                         else:
##                             item = self.GetNextSibling(item)
##                     elif path == itempath:
##                         self.path = path
##                         self.SelectItem(item)
##                         self.EnsureVisible(item)
##                         return True
##                     elif os.path.commonprefix([path, itempath]) == itempath:
##                         self.Expand(item)
##                         item, cookie = self._get_first_child(item, cookie)
##                     else:
##                         item = self.GetNextSibling(item)
##                 return False
##             # special case per il desktop
##             item = self.GetRootItem()
##             self.Expand(item)
##             item, c = self._get_first_child(item, 0)
##             do_rec(item)

# end of class DirCtrl


if __name__ == '__main__':
    import sys
    
    app = wx.PySimpleApp()
    frame = wx.Frame(None, -1,
                     "DirCtrl Test - wxPython %s" % wx.VERSION_STRING,
                     size=(350, 500))
    szr = wx.BoxSizer(wx.VERTICAL)
    tree = DirCtrl(frame, -1)
    if len(sys.argv) > 1:
        tree.SetPath(sys.argv[1])
    else:
        tree.SetPath(os.path.expanduser('~'))

    szr.Add(tree, 1, wx.EXPAND)

    b = wx.Button(frame, -1, "Toggle Hidden")

    wx.EVT_BUTTON(b, -1, lambda e: tree.ShowHidden(not tree._show_hidden))

    szr.Add(b, 0, wx.ALL|wx.ALIGN_CENTER, 3)

    frame.SetSizer(szr)

    def on_item_selected(event):
        print('selected:', tree.GetPath())

    wx.EVT_TREE_SEL_CHANGED(tree.GetTreeCtrl(), -1, on_item_selected)
    
    app.SetTopWindow(frame)
    frame.Show()

    app.MainLoop()

