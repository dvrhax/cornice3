# picture_list.py: list of pictures in the current directory
# arch-tag: list of pictures in the current directory
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL



import wx, wx.lib.mixins.listctrl as wxlist
import os, stat, time, locale
from PIL import Image
import random

import common, picture_thumbs
import dircompleter.dircompleter as dircompleter
import fileops, vfs, clipboard
import resources

import picture
import exif_info


_PICTURE_RIGHT_CLICK_EVENT = wx.NewEventType()

class PictureRightClickEvent(wx.PyCommandEvent):
    def __init__(self, id, pos):
        wx.PyCommandEvent.__init__(self)
        self.SetId(id)
        self.SetEventType(_PICTURE_RIGHT_CLICK_EVENT)
        self.pos = pos

    def GetPosition(self):
        return self.pos

# end of class PictureRightClickEvent


EVT_PICTURE_RIGHT_CLICK = wx.PyEventBinder(_PICTURE_RIGHT_CLICK_EVENT, 1)


class PictureListCtrl(wx.ListCtrl, wxlist.ListCtrlAutoWidthMixin,
                      wxlist.ColumnSorterMixin):
    def __init__(self, parent, id, options):
        style = options.get('style', wx.LC_REPORT)
        style |= wx.SUNKEN_BORDER
        try:
            self.details_bg_color = common.config.getint(
                'cornice', 'details_bg_color')
        except:
            self.details_bg_color = 1
        if self.details_bg_color:
            style |= wx.LC_HRULES
        wx.ListCtrl.__init__(self, parent, id, style=style)
        wxlist.ListCtrlAutoWidthMixin.__init__(self)
        self.InsertColumn(0, _('Name'), width=150)
        self.InsertColumn(1, _('Date'))
        self.InsertColumn(2, _('Size'), wx.LIST_FORMAT_RIGHT)
        self.InsertColumn(3, _('Image Properties'), wx.LIST_FORMAT_RIGHT)
        self.parent = parent
        self.default_color = (240, 240, 240)
        self.default_icon = -1
        self.unknown_icon = -1
        self.up = -1
        self.down = -1
        self.icons = {}
        self._set_image_list()
        self.selected_item = -1

        self.data = {}
        
        # now we can initialize the column sorter
        self.itemDataMap = {}
        wxlist.ColumnSorterMixin.__init__(self, 4)

        # this seems to be necessary to make the mouse wheel work correctly...
        #wx.EVT_MOUSEWHEEL(self, lambda e: e.Skip())
        wx.EvtHandler.Bind(self, wx.EVT_MOUSEWHEEL, lambda e: e.Skip())

    def GetListCtrl(self):
        return self

    def GetSortImages(self):
        return self.down, self.up

    def _set_image_list(self):
        imglist = wx.ImageList(16, 16)
        self.up = imglist.Add(wx.Bitmap(os.path.join('icons', 'up.xpm'),
                                        wx.BITMAP_TYPE_XPM))
        self.down = imglist.Add(wx.Bitmap(os.path.join('icons', 'down.xpm'),
                                          wx.BITMAP_TYPE_XPM))
        for key, (name, color) in common.icons_and_colors.items():
            i = imglist.Add(wx.Bitmap(os.path.join('icons', name),
                                      wx.BITMAP_TYPE_XPM))
            self.icons[key] = i
        self.default_icon = imglist.Add(wx.Bitmap(
            os.path.join('icons', 'file_image.xpm'), wx.BITMAP_TYPE_XPM))
        self.unknown_icon = imglist.Add(wx.Bitmap(
            os.path.join('icons', 'file_unknown.xpm'), wx.BITMAP_TYPE_XPM))
        self.AssignImageList(imglist, wx.IMAGE_LIST_SMALL)
        
    def set_path(self, path, first_time=[True]):
        """\
        Updates the control with the images in the given dir.
        Returns a tuple (total_files, total_size) to show infos in the
        statusbar
        """
        self.Freeze()
        self.DeleteAllItems()
        self.data = {}
        total_files = 0
        total_size = 0
        item_map = {}
        i = 0
        try:
            dir_list = fileops.listdir(path)
        except OSError:
            self.itemDataMap = {}
            self.Thaw()
            return 0, 0
##         for name in dir_list:
        for img in dir_list:
##             fullname = os.path.join(path, name)
##             try: info = fileops.get_path_info(fullname) #os.stat(fullname)
##             except OSError: continue
            fullname = img.path
            try:
##                 if not (stat.S_ISREG(info[stat.ST_MODE]) or \
##                         stat.S_ISLNK(info[stat.ST_MODE])):
##                     continue
                #if not info.isfile: continue
##                 try:
##                     f = fileops.open(fullname)
##                 except:
##                     import traceback; traceback.print_exc()                
##                 img = Image.open(f)
##                 f.close()
                #img = picture.Picture(fullname, info)
                item = wx.ListItem()
                item.SetMask(wx.LIST_MASK_TEXT | wx.LIST_MASK_IMAGE |
                             wx.LIST_MASK_DATA)
                item.SetText(img.name)
                item.SetId(i)
                item.SetData(i)
                icon = self.icons.get(img.format, self.default_icon)
                color = common.icons_and_colors.get(
                    img.format,('', self.default_color))[1]
                item.SetImage(icon)
                #if wx.Platform != '__WXMAC__':
                if self.details_bg_color:
                    item.SetBackgroundColour(wx.Colour(*color))
                #item = self.InsertStringItem(i, name)
                item = self.InsertItem(item)
                mtime = time.strftime('%Y/%m/%d %H:%M',
                                      time.localtime(img.mtime)) #[stat.ST_MTIME]))
                self.SetItem(item, 1, mtime)
                size = img.filesize #info[stat.ST_SIZE]
                self.SetItem(item, 2, locale.format("%.0f",
                                                          float(size), 1))
                w, h = img.size
                if img.mode == '1':
                    sdepth = '1'
                    depth = 1
                elif img.mode == 'P':
                    sdepth = '256'
                    depth = 256
                else:
                    sdepth = '16M'
                    depth = 16000000
                self.SetItem(item, 3, img.get_format_string())
                #self.SetItemData(item, id(img))
                self.SetItemData(item, i)
                self.data[i] = img
                #item_map[i] = (name, info[stat.ST_MTIME], size, (w, h, depth))
                #print item
                item_map[i] = (img.name, img.mtime, img.size,
                               (img.size[0], img.size[1], img.depth))
                i += 1
                total_files += 1
                total_size += size
            except:
                # the can't be read or is not an image
                import traceback; traceback.print_exc()
                pass
        self.itemDataMap = item_map
        if self.GetItemCount():
            self.SetColumnWidth(1, wx.LIST_AUTOSIZE) # resize the date column
        else:
            self.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
            self.SetColumnWidth(1, self.GetColumnWidth(1) + 16)
        self._doResize() # inherited from wxlist.ListCtrlAutoWidthMixin
        self.Thaw()
        self.SortListItems(common.sort_index, not common.reverse_sort)
        return total_files, total_size

    def GetColumnSorter(self):
        # we override this to update the global sort infos
        common.sort_index = self._col
        # _colSortFlag inherited by ColumnSorterMixin
        common.reverse_sort = not self._colSortFlag[self._col]
        # now send the event to update the menubar...
        common.send_sort_changed_event()
        return wxlist.ColumnSorterMixin.GetColumnSorter(self)

    # the following methods are the interface exposed to PictureList

    def sort_items(self, sort_index=common.SORT_NAME, reverse=False):
        self.SortListItems(sort_index, not reverse)

    def SortItems(self, callable):
        wx.ListCtrl.SortItems(self, callable)
        if not self.details_bg_color:
            odd_c = wx.WHITE
            even_c = wx.Colour(0xEE, 0xF6, 0xFF)
            odd = True
            self.Freeze()
            for i in range(self.GetItemCount()):
                if odd:
                    self.SetItemBackgroundColour(i, odd_c)
                else:
                    self.SetItemBackgroundColour(i, even_c)
                odd = not odd
            self.Thaw()
                
    def get_selected_filenames(self):
        index = -1
        items = []
        while True:
            index = self.GetNextItem(index, wx.LIST_NEXT_ALL,
                                     wx.LIST_STATE_SELECTED)
            if index == -1:
                break
            img = self.data[self.GetItemData(index)]
            #items.append(self.GetItemText(index))
            #items.append(os.path.basename(img.path))
            items.append(img.path)
        return items

    def get_item_info(self, index):
        if index >= 0:
            img = self.data[self.GetItemData(index)]
##             name = self.GetItemText(index)
##             type = self.GetItem(index, 3).GetText()
##             mtime = self.GetItem(index, 1).GetText()
##             size = locale.atoi(self.GetItem(index, 2).GetText())
            name = img.name
            type = img.get_format_string()
            mtime = time.strftime('%Y/%m/%d %H:%M', time.localtime(img.mtime))
            size = locale.atoi(str(img.filesize))
            return [name, mtime, size, type]
        else:
            return ['', '', 0, '']

    def get_active_item_path(self):
        if self.selected_item >= 0:
            return self.data[self.GetItemData(self.selected_item)].path
        return ""

    def get_item_path(self, index):
        return self.data[self.GetItemData(index)].path

    def get_active_item_info(self):
        return self.get_item_info(self.selected_item)

    def get_selected_item_index(self):
        return self.selected_item

    def bind_item_selected(self, handler):
        def func(event):
            self.selected_item = event.GetIndex()
            handler(self.selected_item)
        wx.EvtHandler.Bind(self, wx.EVT_LIST_ITEM_SELECTED, func, id=self.GetId())

    def bind_item_activated(self, handler):
        def func(event):
            self.selected_item = event.GetIndex()
            handler(self.selected_item)
        wx.EvtHandler.Bind(self, wx.EVT_LIST_ITEM_ACTIVATED, func, id=self.GetId())

    def bind_key_down(self, handler):
        def func(event):
            key = event.GetKeyCode()
            modifiers = [0, 0, 0] # listctrl events doesn't support modifiers
            handler(key, modifiers)
            #event.Skip()
        wx.EvtHandler.Bind(self, wx.EVT_LIST_KEY_DOWN, func, id=self.GetId())

    def bind_begin_dragging(self, handler):
        def func(event):
            handler()
        wx.EvtHandler.Bind(self, wx.EVT_LIST_BEGIN_DRAG, func, id=self.GetId())

    def bind_right_click(self, handler):
        def func(event):
            handler(event.GetPosition())
        wx.EvtHandler.Bind(self, wx.EVT_LIST_ITEM_RIGHT_CLICK, func, id=self.GetId())

# end of class PictureListCtrl


_EVT_PL_CHANGE_PATH = wx.NewEventType()

class PictureListChangePathEvent(wx.PyCommandEvent):
    def __init__(self, path):
        wx.PyCommandEvent.__init__(self)
        self.SetEventType(_EVT_PL_CHANGE_PATH)
        self.path = path

# end of class PictureListChangePathEvent

if wx.VERSION[:2] >= (2, 5):
    EVT_PL_CHANGE_PATH = wx.PyEventBinder(_EVT_PL_CHANGE_PATH, 1)
else:
    def EVT_PL_CHANGE_PATH(win, id, function):
        win.Connect(id, -1, _EVT_PL_CHANGE_PATH, function)


class PictureList(wx.Panel):
    def __init__(self, parent, id, options, owner):
        wx.Panel.__init__(self, parent, id)
        self.path_text = dircompleter.DirCompleter(self, -1, "")
        self._lists = [
            PictureListCtrl(self, -1, options),
            picture_thumbs.PictureThumbs(self, -1),
            ]
        index = common.config.getint('cornice', 'default_view')
        self._lists[(index+1) % 2].Hide()
        self.list = self._lists[index]

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.path_text, 0, wx.TOP|wx.BOTTOM|wx.RIGHT|wx.EXPAND, 3)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetAutoLayout(1)
        self.SetSizer(sizer)

        self.path = ''
        self.preview_panel = owner.preview_panel
        self.selected_item = None
        self.owner = owner
        self.viewer = owner.viewer
        self.statusbar = owner.statusbar
        self.dir_ctrl = owner.dir_ctrl
        self.bookmarks = owner.bookmarks
        self.bookmarks.picture_list = self
        self.viewer.picture_list = self
        self.total_files, self.total_size = 0, 0
        TIMER_ID = wx.NewId()
        self.timer = wx.Timer(self, TIMER_ID)

        for l in self._lists:
            l.bind_item_selected(self.on_item_selected)
            l.bind_item_activated(self.on_item_activated)
            l.bind_key_down(self.on_char)
            l.bind_begin_dragging(self.on_dragging)
            l.bind_right_click(self.on_right_click)
        wx.EvtHandler.Bind(self, wx.EVT_TIMER, self.show_preview, id=TIMER_ID)

        dircompleter.EVT_CHANGE_PATH(self, self.path_text.GetId(),
                                     self.on_text_enter)

        self._random_iter = None

    def on_text_enter(self, event):
        path = event.GetPath()
        #if os.path.isdir(path):
        if fileops.isdir(path):
            self.set_path(path)
        event.Skip()

    def set_path(self, path, refresh=False):
        #if path and path[-1] != os.sep: path += os.sep
        path = fileops.normpath(path)
        if self.path == path and not refresh:
            return # nothing to do
        self.path = path
        self.total_files, self.total_size = self.list.set_path(path)
        self.path_text.add_to_history(path)
        self.path_text.SetValue(self.path)

        # we use this evil hack of setting an attribute that says to ignore
        # the next "chage selection" event, because if the user selects a
        # hidden dir and it's not visible in the tree, the old path is
        # restored
        self.dir_ctrl.dont_trigger_change_dir = True
        self.dir_ctrl.SetPath(self.path)
        self.dir_ctrl.dont_trigger_change_dir = False

        self.bookmarks.set_path(self.path)
        self.path_text.SetInsertionPointEnd()
        #self.path_text.SetFocus()
        wx.CallAfter(self.list.SetFocus)

        wx.PostEvent(self, PictureListChangePathEvent(self.path))
        
    def focus_path(self, *args):
        self.path_text.SetInsertionPointEnd()
        self.path_text.SetFocus()    

    def update_statusbar_info(self):
        val = _("Total %s file(s), (%s)") % \
              (self.total_files, common.format_size_str(self.total_size))
        if val != self.statusbar.GetStatusText(0):
            self.statusbar.SetStatusText(val, 0)

    def get_selected_filenames(self):
        return self.list.get_selected_filenames()

    def delete_selection(self):
        items = self.list.get_selected_filenames()
        if items:
            msg = _("Delete %s picture(s)?") % len(items)
            if fileops.is_collection(self.path):
                msg = _("Remove %s picture(s) from the collection?") % \
                      len(items)
        if items and \
               wx.MessageBox(msg, _("Are you sure?"),
                             wx.YES_NO|wx.CENTRE|wx.ICON_QUESTION) == wx.YES:
            fileops.delete_from(self.path, items)
##             for item in items:
##                 try:
##                     fileops.unlink(item) #os.path.join(self.path, item))
##                 except (IOError, OSError), e:
##                     import traceback; traceback.print_exc(e)
##                     wx.LogError(str(e))
            self.set_path(self.path, True) # refresh the list

    def clipboard_cut(self):
        files = self.list.get_selected_filenames()
        if files:
            clipboard.cut(files) #[os.path.join(self.path, f) for f in files])

    def clipboard_copy(self):
        files = self.list.get_selected_filenames()
        if files:
            clipboard.copy(files) #[os.path.join(self.path, f) for f in files])

    def clipboard_paste(self):
        if vfs.is_virtual(self.path):
            wx.MessageBox(_('Error'),
                          _("Can't paste on this path: %s") % self.path,
                          style=wx.OK|wx.ICON_ERROR)
            return
        if not wx.IsBusy():
            wx.BeginBusyCursor()
        files, cutting = clipboard.paste()
        dialog = None
        go_on = False
        action = None
        needs_refresh = False
        for f in files:
            dst = os.path.join(self.path, os.path.basename(f))
            if f == dst:
                continue
            if os.path.exists(dst):
                if not go_on:
                    if dialog is None: dialog = resources.ImageCopyDialog()
                    action = dialog.show(dst, f, len(files) > 1)
                if action == dialog.CANCEL:
                    break
                if action == dialog.SKIP_ALL:
                    action = dialog.SKIP
                    go_on = True
                elif action == dialog.OVERWRITE_ALL:
                    action = dialog.OVERWRITE
                    go_on = True
                # process actions...
                if action == dialog.RENAME:
                    dst = os.path.join(os.path.dirname(dst),
                                       dialog.get_new_name())
                elif action == dialog.SKIP:
                    continue
            try:
                src = fileops.open(f)
                out = open(dst, 'wb')
                for line in src:
                    out.write(line)
                src.close()
                out.close()
                needs_refresh = True
                if cutting:
                    fileops.unlink(f)
            except (IOError, OSError) as e:
                wx.LogError(str(e))
        if dialog is not None:
            dialog.destroy()
        if wx.IsBusy():
            wx.EndBusyCursor()
        if files and needs_refresh:
            self.set_path(self.path, True) # refresh the list
                
    def on_char(self, key, modifiers):
        # key down on the list of pics
        if key == wx.WXK_DELETE and not vfs.is_virtual(self.path):
            self.delete_selection()
                
    def on_item_selected(self, index):
        self.selected_item = index
        self.timer.Start(30, True)
        if self.selected_item is not None:
            name, mtime, size, type = self.list.get_active_item_info()
            self.statusbar.SetStatusText(common.format_size_str(size) +
                                         ', ' + mtime, 1)
            self.statusbar.SetStatusText(name, 2)
            self.statusbar.SetStatusText(type, 3)

    def on_item_activated(self, *args):
        if self.selected_item is None:
            return
        info = self.list.get_active_item_info()
        #image_file = os.path.join(self.path, info[0])
        image_file = self.list.get_active_item_path()
        try:
            #img = Image.open(image_file)
            self.viewer.clear_flags()
            #self.viewer.view_image(img, info)
            self.viewer.view_image(image_file, info)
            self.viewer.SetFocus()
            if wx.Platform == '__WXMAC__':
                wx.CallAfter(self.viewer.GetParent().Raise)
        except:
            import traceback; traceback.print_exc()

    def on_dragging(self):
        drag_source = wx.DropSource(self)
        data = wx.FileDataObject()
        for f in self.list.get_selected_filenames():
            try:
                data.AddFile(f) #os.path.join(self.path, f))
            except AttributeError:
                pass # AddFile could be unsupported on wx2.4
        drag_source.SetData(data)
        clipboard._self_dragging = True
        result = drag_source.DoDragDrop(True)

    def on_right_click(self, position):
        wx.PostEvent(self, PictureRightClickEvent(self.GetId(), position))

    def popup_menu(self, menu, position):
        self.list.PopupMenu(menu, position)
        
    def show_preview(self, event):
##         image_file = os.path.join(self.path,
##                                   self.list.get_active_item_info()[0])
        image_file = self.list.get_active_item_path()
        try:
            #img = Image.open(image_file)
            #self.preview_panel.set_image(img)
            self.preview_panel.set_image(image_file)
            if self.owner.exif_info.findexif(image_file):
                self.owner.show_exif(True)
            else:
                self.owner.show_exif(False)
            self.list.SetFocus()
        except Exception as e:
            import traceback; traceback.print_exc()
            wx.LogError(str(e))
           
    def _view_image(self, index):
        if -1 < index < self.total_files:
            self.selected_item = index
            info = self.list.get_item_info(index)
            try:
                #image_file = os.path.join(self.path, info[0])
                image_file = fileops.open(self.list.get_item_path(index))
                img = exif_info.exif_orient(image_file, Image.open(image_file))
                return img, info
            except Exception as e:
                #import traceback; traceback.print_exc()
                wx.LogError(str(e))
        return None, None

    def view_current_image(self):
        assert self.selected_item is not None
        return self._view_image(self.selected_item)

    def view_prev_image(self):
        if self.selected_item is None: return None, None
        return self._view_image(self.selected_item - 1)

    def view_next_image(self):
        if self.selected_item is None: return None, None
        return self._view_image(self.selected_item + 1)

    def view_first_image(self):
        return self._view_image(0)

    def view_last_image(self):
        return self._view_image(self.total_files-1)

    def _restore_selected_image(self):
        self.selected_item = self.list.get_selected_item_index()
        if wx.Platform == '__WXGTK__':
            # otherwise the list has a gray highlight line...
            self.path_text.SetFocus()
            self.path_text.SetInsertionPointEnd()
            self.list.SetFocus()

    def _do_swap(self, index_to_show, index_to_hide):
        l1 = self._lists[index_to_show]
        l2 = self._lists[index_to_hide]
        sizeritem = self.GetSizer().GetChildren()[1]
        l2.Hide()
        l1.Show()
        l1.SetFocus()
        sizeritem.SetWindow(l1)
        self.list = l1
        self.GetSizer().Layout()
        self.list.set_path(self.path)
        #self.path_text.SetFocus()
        self.path_text.SetInsertionPointEnd()
        self.path_text.SetMark(self.path_text.GetInsertionPoint(), -1)

    def show_thumbs(self):
        if self.list is self._lists[1]:
            return # nothing to do
        self._do_swap(1, 0)

    def show_details(self):
        if self.list is self._lists[0]:
            return # nothing to do
        self._do_swap(0, 1)

    def swap_view(self):
        if self.list is self._lists[0]:
            self._do_swap(1, 0)
        else:
            self._do_swap(0, 1)

    def sort_items(self, sort_index=common.SORT_NAME, reverse=False):
        self.list.sort_items(sort_index, reverse)

    def next_random_image(self):
        def gen():
            l = list(range(self.total_files))
            random.shuffle(l)
            for i in l: yield i
        if self._random_iter is None:
            self._random_iter = gen()
        try:
            return self._view_image(next(self._random_iter))
        except StopIteration:
            self._random_iter = None
            return (None, None)

# end of class PictureList
