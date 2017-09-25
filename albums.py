# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

import wx, wx.xrc, wx.lib.mixins.listctrl as wxlist
import os

import collection
import resources, common, fileops, vfs


class AlbumsCtrl(wx.ListCtrl, wxlist.ListCtrlAutoWidthMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_SINGLE_SEL|
                             wx.LC_REPORT|wx.SUNKEN_BORDER)
        wxlist.ListCtrlAutoWidthMixin.__init__(self)
        self.picture_list = None
        imglist = wx.ImageList(16, 16)

        folder = common.get_bitmap_for_theme('album')
        if not folder:
            folder = wx.ArtProvider.GetBitmap(wx.ART_HELP_BOOK, size=(16, 16))
        imglist.Add(folder)
        #bmp = common.get_bitmap_for_theme('zip')
        #imglist.Add(bmp)
        self.AssignImageList(imglist, wx.IMAGE_LIST_SMALL)
        self.InsertColumn(0, "")
        self.InsertColumn(1, _("Album"))
        self.SetColumnWidth(0, 24)
        self.load_albums()
        TIMER_ID = wx.NewId()
        self.set_path_timer = wx.Timer(self, TIMER_ID)
        self._selected_index = -1
        #wx.EVT_TIMER(self, TIMER_ID, self.on_timer)
        #wx.EVT_LIST_ITEM_SELECTED(self, -1, self.on_item_selected)
        wx.EvtHandler.Bind(self, wx.EVT_TIMER, self.on_timer, id=TIMER_ID)
        wx.EvtHandler.Bind(self, wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected, id=-1)

    def load_albums(self):
        return
    
        item = -1
        self.Freeze()
        self.DeleteAllItems()
        for (albumid, name) in collection.get_albums():
            item = self.InsertImageItem(item+1, 0)
            self.SetStringItem(item, 1, name)
            self.SetItemData(item, albumid)
        self.SetColumnWidth(1, -1)
        self._doResize()
        self.Thaw()

    def set_path(self, path):
        path = path.strip()
        for i in range(self.GetItemCount()):
##             ip = self.GetItem(i, 2).GetText()
##             if ip == path:
##                 self.SetItemState(i, wx.LIST_STATE_SELECTED,
##                                   wx.LIST_MASK_STATE)
##             else:
            # TODO
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
        album = self.GetItem(self._selected_index, 1).GetText()
        self.picture_list.set_path('collection:?album=%s' % album)
        if wx.IsBusy(): wx.EndBusyCursor()

    def edit_albums(self):
        resources.AlbumsEditor(self)
        self.load_albums()

    def add_album(self):
        name = wx.GetTextFromUser(_("Select the name for the Album"),
                                  _("Add Album"), "")
        if name != "":
            if not collection.add_album(name):
                wx.MessageBox(_("The album `%s' is already present.") % name,
                              _("Information"), wx.OK|wx.ICON_INFORMATION)
            else:
                self.load_albums()

    def choose_album(self):
        albums = dict([(a[1], a) for a in collection.get_albums()])
        # make the dialog..
        dlg = resources.AlbumChooser(self, albums.keys())
        if dlg.show_modal() == wx.ID_OK:
            try:
                retval = albums[dlg.get_selection()]
            except KeyError:
                retval = 0, dlg.get_selection()
        else:
            retval = -1, None
        dlg.destroy()
        return retval
        
# end of class AlbumsCtrl
