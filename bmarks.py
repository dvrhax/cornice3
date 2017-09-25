# bmarks.py: bookmarks control
# arch-tag: bookmarks control
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

import wx, wx.xrc, wx.lib.mixins.listctrl as wxlist
import os

import resources, common, fileops, vfs


class BookMarksCtrl(wx.ListCtrl, wxlist.ListCtrlAutoWidthMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_SINGLE_SEL|
                             wx.LC_REPORT|wx.SUNKEN_BORDER)
        wxlist.ListCtrlAutoWidthMixin.__init__(self)
        self.picture_list = None
        imglist = wx.ImageList(16, 16)

        folder = common.get_bitmap_for_theme('folder')
        if not folder:
            folder = wx.ArtProvider.GetBitmap(wx.ART_FOLDER, size=(16, 16))
        imglist.Add(folder)
        bmp = common.get_bitmap_for_theme('zip')
        imglist.Add(bmp)
        self.AssignImageList(imglist, wx.IMAGE_LIST_SMALL)
        self.InsertColumn(0, "")
        self.InsertColumn(1, _("Name"))
        self.InsertColumn(2, _("Path"))
        self.SetColumnWidth(0, 24)
        self.load_bookmarks()
        TIMER_ID = wx.NewId()
        self.set_path_timer = wx.Timer(self, TIMER_ID)
        self._selected_index = -1
        #wx.EVT_TIMER(self, TIMER_ID, self.on_timer)
        wx.EvtHandler.Bind(self, wx.EVT_TIMER, self.on_timer, id=TIMER_ID)
        #wx.EVT_LIST_ITEM_SELECTED(self, self.GetId(), self.on_item_selected)
        wx.EvtHandler.Bind(self, wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected, id=self.GetId())

    def load_bookmarks(self):
        try:
            bm = open(common.bookmarks_file)
        except:
            return
        item = -1
        self.Freeze()
        self.DeleteAllItems()
        for line in bm:
            line = line.strip()
            if line.startswith('#'):
                continue # ignore comments
            try:
                name, path = line.split('||', 1)
            except ValueError:
                continue # malformed entry, ignore it
            item = self.InsertItem(item+1, fileops.get_icon_index(path))
            self.SetItem(item, 1, name.strip())
            self.SetItem(item, 2, path.strip())
        self.SetColumnWidth(1, -1)
        self._doResize()
        self.Thaw()

    def set_path(self, path):
        path = path.strip()
        for i in range(self.GetItemCount()):
            ip = self.GetItem(i, 2).GetText()
            if ip == path:
                self.SetItemState(i, wx.LIST_STATE_SELECTED,
                                  wx.LIST_MASK_STATE)
            else:
                self.SetItemState(i, 0, wx.LIST_MASK_STATE)
                
    def on_item_selected(self, event):
        self._selected_index = event.GetIndex()
        if self.picture_list is not None:
            if not wx.IsBusy():
                wx.BeginBusyCursor()
            if not self.set_path_timer.Start(100, True):
                pass # wx.Timer.Start seems to return always False...
                #print 'impossible to start the timer! (bmarks)'
                #self.on_timer()
        event.Skip()

    def on_timer(self, *args):
        path = self.GetItem(self._selected_index, 2).GetText()
        self.picture_list.set_path(path)
        if wx.IsBusy(): wx.EndBusyCursor()

    def edit_bookmarks(self):
        resources.BookMarksEditor(self, common.bookmarks_file)

    def add_bookmark(self):
        if self.picture_list is not None:
            path = self.picture_list.path
            name = wx.GetTextFromUser(_("Select the name for the bookmark"),
                                      _("Add Bookmark"), path)
            if name != "":
                try:
                    outfile = open(common.bookmarks_file, 'a')
                    outfile.write(name + '||' + path + '\n')
                    outfile.close()
                except:
                    wx.LogError(_('Error adding bookmark!'))
                else:
                    self.load_bookmarks()

# end of class BookMarksCtrl
