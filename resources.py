# resources.py: functions to set preferences, ...
# arch-tag: functions to set preferences, ...
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

import wx, wx.xrc
from PIL import Image
import os, sys, common

import collection


class BookMarksEditor:
    def __init__(self, ctrl, bmark_file):
        self.ctrl = ctrl
        self.bmark_file = bmark_file
        self.selected_index = -1
        res = wx.xrc.XmlResource.Get()
        self.dialog = res.LoadDialog(None, 'bookmarks_editor')
        self.fill_bookmarks_list()
        wx.EVT_LIST_ITEM_SELECTED(self.dialog,
                                  wx.xrc.XRCID('bookmarks_list'),
                                  self.on_item_selected)
        wx.EVT_BUTTON(self.dialog, wx.xrc.XRCID('add'), self.add_item)
        wx.EVT_BUTTON(self.dialog, wx.xrc.XRCID('remove'), self.remove_item)
        wx.EVT_BUTTON(self.dialog, wx.xrc.XRCID('move_up'), self.move_item_up)
        wx.EVT_BUTTON(self.dialog, wx.xrc.XRCID('move_down'),
                      self.move_item_down)
        wx.EVT_KILL_FOCUS(wx.xrc.XRCCTRL(self.dialog, 'name'),
                          self.update_item)
        wx.EVT_KILL_FOCUS(wx.xrc.XRCCTRL(self.dialog, 'path'),
                          self.update_item)
        if self.dialog.ShowModal() == wx.ID_OK:
            self.save_bookmarks()
        self.dialog.Destroy()

    def fill_bookmarks_list(self):
        list_ctrl = wx.xrc.XRCCTRL(self.dialog, 'bookmarks_list')
        list_ctrl.InsertColumn(0, _('Name'))
        list_ctrl.InsertColumn(1, _('Path'))
        try:
            bm = open(self.bmark_file)
        except:
            return
        item = -1
        list_ctrl.Freeze()
        list_ctrl.DeleteAllItems()
        for line in bm:
            line = line.strip()
            if line.startswith('#'):
                continue # ignore comments
            try:
                name, path = line.split('||', 1)
            except ValueError:
                continue # malformed entry, ignore it
            item = list_ctrl.InsertStringItem(item+1, name.strip())
            list_ctrl.SetStringItem(item, 1, path.strip())
        list_ctrl.SetColumnWidth(0, -1)
        list_ctrl.SetColumnWidth(1, -1)
        list_ctrl.Thaw()

    def add_item(self, event):
        wx.xrc.XRCCTRL(self.dialog, 'name').GetValue().strip()
        path = wx.xrc.XRCCTRL(self.dialog, 'path').GetValue().strip()
##         if not path or not os.path.isdir(path):
##             wx.MessageBox(_('You must insert a valid path!'), _('Error'),
##                           wx.OK|wx.CENTRE|wx.ICON_ERROR)
##             return
        if not name:
            name = path
        list_ctrl = wx.xrc.XRCCTRL(self.dialog, 'bookmarks_list')
        index = self.selected_index = self.selected_index + 1
        list_ctrl.InsertStringItem(index, name)
        list_ctrl.SetStringItem(index, 1, path)
        list_ctrl.SetItemState(index, wx.LIST_STATE_SELECTED,
                               wx.LIST_STATE_SELECTED)
        list_ctrl.SetColumnWidth(0, -1)
        list_ctrl.SetColumnWidth(1, -1)

    def update_item(self, event):
        name = wx.xrc.XRCCTRL(self.dialog, 'name').GetValue().strip()
        path = wx.xrc.XRCCTRL(self.dialog, 'path').GetValue().strip()
##         if not path or not os.path.isdir(path):
##             wx.MessageBox(_('You must insert a valid path!'), _('Error'),
##                           wx.OK|wx.CENTRE|wx.ICON_ERROR)
##             event.Skip()
##             return
        if not name:
            name = path
        list_ctrl = wx.xrc.XRCCTRL(self.dialog, 'bookmarks_list')
        list_ctrl.SetStringItem(self.selected_index, 0, name)
        list_ctrl.SetStringItem(self.selected_index, 1, path)
        list_ctrl.SetItemState(self.selected_index, wx.LIST_STATE_SELECTED,
                               wx.LIST_STATE_SELECTED)
        list_ctrl.SetColumnWidth(0, -1)
        list_ctrl.SetColumnWidth(1, -1)
        event.Skip()

    def on_item_selected(self, event):
        self.selected_index = event.GetIndex()
        list_ctrl = wx.xrc.XRCCTRL(self.dialog, 'bookmarks_list')
        name = wx.xrc.XRCCTRL(self.dialog, 'name')
        path = wx.xrc.XRCCTRL(self.dialog, 'path')
        name.SetValue(list_ctrl.GetItem(self.selected_index, 0).GetText())
        path.SetValue(list_ctrl.GetItem(self.selected_index, 1).GetText())
        event.Skip()

    def remove_item(self, event):
        list_ctrl = wx.xrc.XRCCTRL(self.dialog, 'bookmarks_list')
        name = wx.xrc.XRCCTRL(self.dialog, 'name')
        path = wx.xrc.XRCCTRL(self.dialog, 'path')
        if 0 <= self.selected_index < list_ctrl.GetItemCount():
            for s in (name, path):
                s.SetValue("")
            list_ctrl.DeleteItem(self.selected_index)
        list_ctrl.SetColumnWidth(0, -1)
        list_ctrl.SetColumnWidth(1, -1)

    def move_item_up(self, event):
        list_ctrl = wx.xrc.XRCCTRL(self.dialog, 'bookmarks_list')
        list_ctrl.SetFocus()
        if self.selected_index > 0:
            index = self.selected_index - 1
            n1 = list_ctrl.GetItem(self.selected_index, 0).GetText()
            p1 = list_ctrl.GetItem(self.selected_index, 1).GetText()
            n2 = list_ctrl.GetItem(index, 0).GetText()
            p2 = list_ctrl.GetItem(index, 1).GetText()
            list_ctrl.SetStringItem(self.selected_index, 0, n2)
            list_ctrl.SetStringItem(self.selected_index, 1, p2)
            list_ctrl.SetStringItem(index, 0, n1)
            list_ctrl.SetStringItem(index, 1, p1)
            state = wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED
            list_ctrl.SetItemState(index, state, state)

    def move_item_down(self, event):
        list_ctrl = wx.xrc.XRCCTRL(self.dialog, 'bookmarks_list')
        list_ctrl.SetFocus()
        if self.selected_index < list_ctrl.GetItemCount()-1:
            index = self.selected_index + 1
            n1 = list_ctrl.GetItem(self.selected_index, 0).GetText()
            p1 = list_ctrl.GetItem(self.selected_index, 1).GetText()
            n2 = list_ctrl.GetItem(index, 0).GetText()
            p2 = list_ctrl.GetItem(index, 1).GetText()
            list_ctrl.SetStringItem(self.selected_index, 0, n2)
            list_ctrl.SetStringItem(self.selected_index, 1, p2)
            list_ctrl.SetStringItem(index, 0, n1)
            list_ctrl.SetStringItem(index, 1, p1)
            state = wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED
            list_ctrl.SetItemState(index, state, state)

    def save_bookmarks(self):
        list_ctrl = wx.xrc.XRCCTRL(self.dialog, 'bookmarks_list')
        from time import asctime
        try:
            outfile = open(self.bmark_file, 'w')
            outfile.write('# bookmarks modified %s\n' % asctime())
            outfile.write('# format: name || path\n')
            for i in range(list_ctrl.GetItemCount()):
                name = list_ctrl.GetItem(i, 0).GetText()
                path = list_ctrl.GetItem(i, 1).GetText()
                outfile.write(name + '||' + path + '\n')
            outfile.close()
        except:
            wx.LogError(_('Unable to save bookmarks!'))
            return
        else:
            self.ctrl.load_bookmarks()

# end of class BookMarksEditor


class PreferencesEditor:
    def __init__(self, config, save_file_name):
        res = wx.xrc.XmlResource.Get()
        self.dialog = res.LoadDialog(None, 'prefs_dialog')
        if wx.Platform == '__WXMAC__':
            # ALB: there seems to be a bug: the initial size is too small
            # on the mac (for wx 2.5.3 at least...)
            self.dialog.SetSize((450, 400)) 
        self.config = config
        self.save_file_name = save_file_name
        self.update_view()
        if self.dialog.ShowModal() == wx.ID_OK:
            msg = _('Changes will take effect next time you start Cornice')
            wx.MessageBox(msg, _('Information'),
                          style=wx.OK|wx.ICON_INFORMATION)
            self.save_preferences()
        self.dialog.Destroy()

    def update_view(self):
        for option in self.config.options('cornice'):
            ctrl = wx.xrc.XRCCTRL(self.dialog, option)
            if ctrl is not None:
                try:
                    option = self.config.getint('cornice', option)
                except ValueError:
                    try:
                        option = self.config.getboolean('cornice', option)
                    except ValueError:
                        option = self.config.get('cornice', option)
                try:
                    ctrl.SetValue(option)
                except AttributeError:
                    ctrl.SetSelection(option)

    def save_preferences(self):
        for option in self.config.options('cornice'):
            ctrl = wx.xrc.XRCCTRL(self.dialog, option)
            if ctrl is not None:
                try:
                    value = ctrl.GetValue()
                except AttributeError:
                    value = ctrl.GetSelection()
                if isinstance(value, bool):
                    value = int(value)
                self.config.set('cornice', option, "%s" % value)
        try:
            out = open(self.save_file_name, 'w')
            self.config.write(out)
            out.close()
        except Exception as e:
            wx.LogError(_('Unable to save preferences (%s)') % e) 

# end of class PreferencesEditor


class ScrolledMessageDialog:
    def __init__(self, parent, message, title, cols=80, rows=24, modal=False):
        self.dialog = wx.Dialog(parent, -1, title)
        tc = wx.TextCtrl(self.dialog, -1, message,
                        style=wx.TE_READONLY|wx.TE_MULTILINE)
        tc.SetFont(wx.Font(12, wx.MODERN, wx.NORMAL, wx.NORMAL, False))
        w, h = tc.GetTextExtent('M')
        w *= cols
        h *= rows
        if wx.VERSION[:2] >= (2, 5):
            tc.SetMinSize((w, h))
        else:
            tc.SetSize((w, h))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(tc, 0, wx.ALL, 5)
        btn = wx.Button(self.dialog, wx.ID_OK, 'OK')
        btn.SetDefault()
        sizer.Add(btn, 0, wx.ALL|wx.ALIGN_CENTER, 15)
        self.dialog.SetAutoLayout(True)
        self.dialog.SetSizer(sizer)
        sizer.Fit(self.dialog)
        self.dialog.Layout()
        ###wx.EVT_CLOSE(self.dialog, self.on_close)
        wx.EvtHandler.Bind(self.dialog, wx.EVT_CLOSE, self.on_close)
        if parent:
            self.dialog.CenterOnParent()
        if modal:
            self.dialog.ShowModal()
        else:
            self.dialog.Show()

    def on_close(self, event):
        self.dialog.Destroy()

# end of class ScrolledMessageDialog


class ImageCopyDialog:
    THUMB_SIZE = 100, 100

    CANCEL, RENAME, SKIP, SKIP_ALL, OVERWRITE, OVERWRITE_ALL = list(range(6))
    
    def __init__(self):
        res = wx.xrc.XmlResource.Get()
        self.dialog = res.LoadDialog(None, 'image_copy_dialog')
        wx.EVT_BUTTON(self.dialog, wx.xrc.XRCID('rename'), self.on_rename)
        wx.EVT_BUTTON(self.dialog, wx.xrc.XRCID('skip'), self.on_skip)
        wx.EVT_BUTTON(self.dialog, wx.xrc.XRCID('auto_skip'), self.on_skip_all)
        wx.EVT_BUTTON(self.dialog, wx.xrc.XRCID('overwrite'),
                      self.on_overwrite)
        wx.EVT_BUTTON(self.dialog, wx.xrc.XRCID('overwrite_all'),
                      self.on_overwrite_all)
        wx.EVT_BUTTON(self.dialog, wx.xrc.XRCID('cancel'), self.on_cancel)
        wx.EVT_TEXT(self.dialog, wx.xrc.XRCID('new_image_name'),
                    self.on_new_name)

        self.new_image = wx.xrc.XRCCTRL(self.dialog, 'new_image')
        self.old_image = wx.xrc.XRCCTRL(self.dialog, 'orig_image')
        self.new_image_info = wx.xrc.XRCCTRL(self.dialog, 'new_image_info')
        self.old_image_info = wx.xrc.XRCCTRL(self.dialog, 'orig_image_info')
        self.new_file_info = wx.xrc.XRCCTRL(self.dialog, 'new_file_info')
        self.old_file_info = wx.xrc.XRCCTRL(self.dialog, 'orig_file_info')
        self.rename_button = wx.xrc.XRCCTRL(self.dialog, 'rename')
        self.new_image_name = wx.xrc.XRCCTRL(self.dialog, 'new_image_name')

        self.new_name = None
        self.dstdir = None

    def show(self, src, dst, multi):
        self.dstdir = os.path.dirname(dst)
        self.rename_button.Enable(False)
        self._set_image(src, False)
        self._set_image(dst, True)
        self.new_image_name.SetValue(os.path.basename(dst))
##         if not multi:
##             for name in ('auto_skip', 'overwrite_all'):
##                 wx.xrc.XRCCTRL(self.dialog, name).Enable(False)
        self.dialog.Layout()
        self.dialog.Fit()

        return self.dialog.ShowModal()

    def _set_image(self, image, is_new):
        if is_new:
            im = self.new_image
            im_info = self.new_image_info
            file_info = self.new_file_info
        else:
            im = self.old_image
            im_info = self.old_image_info
            file_info = self.old_file_info
        try:
            bmp = common.create_thumbnail(Image.open(image), self.THUMB_SIZE)
            im.SetBitmap(bmp)
            info = common.get_image_info(image)
            im_info.SetLabel(info[3])
            file_info.SetLabel(common.format_size_str(info[2]) + " " +
                               info[1])
        except:
            import time, fileops
            im.SetBitmap(wx.NullBitmap)
            im_info.SetLabel(_("UNSUPPORTED FORMAT"))
            info = fileops.get_path_info(image)
            file_info.SetLabel(common.format_size_str(info.size) + " " +
                               time.strftime('%Y/%m/%d %H:%M',
                                             time.localtime(info.mtime)))

    def on_new_name(self, event):
        val = self.new_image_name.GetValue()
        self.new_name = os.path.join(self.dstdir, val)
        if val and not os.path.exists(self.new_name):
            self.rename_button.Enable(True)
        else:
            self.rename_button.Enable(False)

    def on_rename(self, event):
        self.new_name = self.new_image_name.GetValue()
        self.dialog.EndModal(self.RENAME)

    def on_skip(self, event):
        self.dialog.EndModal(self.SKIP)

    def on_skip_all(self, event):
        self.dialog.EndModal(self.SKIP_ALL)

    def on_overwrite(self, event):
        self.dialog.EndModal(self.OVERWRITE)

    def on_overwrite_all(self, event):
        self.dialog.EndModal(self.OVERWRITE_ALL)

    def on_cancel(self, event):
        self.dialog.EndModal(self.CANCEL)

    def get_new_name(self):
        return self.new_name

    def destroy(self):
        if self.dialog:
            self.dialog.Destroy()
            self.dialog = None

# end of class ImageCopyDialog


class AboutDialog:
    def __init__(self):
        res = wx.xrc.XmlResource.Get()
        self.dialog = res.LoadDialog(None, 'about_dialog')
        about_msg = _("Cornice v%s: a Python + wxPython + PIL image viewer\n"
                      "Running on Python %s, wxPython %s and PIL %s\n"
                      "Author: Alberto Griggio "
                      "<agriggio@users.sourceforge.net>\n"
                      "Thanks to: see credits.txt\n"
                      "License: GPL (see license.txt)\n"
                      "THIS PROGRAM COMES WITH NO WARRANTY") % \
                      (common.__version__, '%s.%s.%s' % sys.version_info[:3],
                       wx.VERSION_STRING, Image.VERSION)
        wx.xrc.XRCCTRL(self.dialog, 'about_msg').SetLabel(about_msg)
        self.dialog.Fit()
        self.dialog.ShowModal()

# end of class AboutDialog


class AlbumsEditor:
    def __init__(self, ctrl):
        self.ctrl = ctrl
        res = wx.xrc.XmlResource.Get()
        self.dialog = res.LoadDialog(None, 'albums_editor')
        
        evts = (('albums_list', wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected),
                ('add', wx.EVT_BUTTON, self.add_item),
                ('remove', wx.EVT_BUTTON, self.remove_item),
                ('name', wx.EVT_KILL_FOCUS, self.update_item))

        for idString, e, func in evts:
            wx.EvtHandler.Bind(self.dialog, e, func, id=wx.xrc.XRCID(idString))

        list_ctrl = wx.xrc.XRCCTRL(self.dialog, 'albums_list')
        list_ctrl.InsertColumn(0, _('Name'))
        self.albumids = {}
        self.fill_albums_list()
        self.dialog.ShowModal()
        self.dialog.Destroy()

    def fill_albums_list(self):
        self.selected_index = -1
        self.albumids = {}
        item = -1
        list_ctrl = wx.xrc.XRCCTRL(self.dialog, 'albums_list')
        list_ctrl.Freeze()
        list_ctrl.DeleteAllItems()
        for (albumid, name) in collection.get_albums():
            item = list_ctrl.InsertItem(item+1, name)
            self.albumids[name] = albumid
        list_ctrl.SetColumnWidth(0, list_ctrl.GetClientSize()[0])
        list_ctrl.Thaw()

    def add_item(self, event):
        name = wx.xrc.XRCCTRL(self.dialog, 'name').GetValue().strip()
        if name:
            if not collection.add_album(name):
                wx.MessageBox(_("The album `%s' is already present.") % name,
                              _("Information"), wx.OK|wx.ICON_INFORMATION)
            else:
                self.fill_albums_list()

    def update_item(self, event):
        name = wx.xrc.XRCCTRL(self.dialog, 'name').GetValue().strip()
        list_ctrl = wx.xrc.XRCCTRL(self.dialog, 'albums_list')
        if name and self.selected_index >= 0:
            oldname = list_ctrl.GetItem(self.selected_index, 0).GetText()
            albumid = self.albumids[oldname]
            if not collection.rename_album(albumid, name):
                wx.MessageBox(_("The album `%s' is already present.") % name,
                              _("Information"), wx.OK|wx.ICON_INFORMATION)
            else:
                self.fill_albums_list()

    def on_item_selected(self, event):
        self.selected_index = event.GetIndex()
        list_ctrl = wx.xrc.XRCCTRL(self.dialog, 'albums_list')
        name = wx.xrc.XRCCTRL(self.dialog, 'name')
        name.SetValue(list_ctrl.GetItem(self.selected_index, 0).GetText())
        event.Skip()

    def remove_item(self, event):
        list_ctrl = wx.xrc.XRCCTRL(self.dialog, 'albums_list')
        name = wx.xrc.XRCCTRL(self.dialog, 'name')
        if 0 <= self.selected_index < list_ctrl.GetItemCount():
            name.SetValue("")
            oldname = list_ctrl.GetItem(self.selected_index, 0).GetText()
            albumid = self.albumids[oldname]
            list_ctrl.DeleteItem(self.selected_index)
            collection.remove_album(albumid)

# end of class AlbumsEditor


class AlbumChooser(object):
    def __init__(self, parent, choices):
        res = wx.xrc.XmlResource.Get()
        self.dialog = res.LoadDialog(parent, 'album_chooser')
        self.choices = wx.xrc.XRCCTRL(self.dialog, 'choices')
        for c in choices:
            self.choices.Append(c)

    def show_modal(self):
        return self.dialog.ShowModal()

    def get_selection(self):
        return self.choices.GetValue()

    def destroy(self):
        self.dialog.Destroy()

# end of class AlbumChooser
