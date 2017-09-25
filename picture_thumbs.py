# picture_thumbs.py: thumbnail view of the pictures in the current directory
# arch-tag: thumbnail view of the pictures in the current directory
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL



import wx
import os, stat, time, locale, math
from PIL import Image
import threading, weakref

import common, fileops

import picture

CACHE_SIZE = None
THUMBS_SIZE = None


def init_from_preferences():
    global CACHE_SIZE, THUMBS_SIZE
    try:
        CACHE_SIZE = common.config.getint(
            'cornice', 'thumbs_cache_size') * 1024
    except:
        CACHE_SIZE = 5120 * 1024 # 5 MB

    try:
        THUMBS_SIZE = [int(t) for t in common.config.get(
            'cornice', 'thumbs_size').split(',', 1)]
        if len(THUMBS_SIZE) != 2:
            THUMBS_SIZE = 80, 60
    except:
        import traceback
        traceback.print_exc()
        THUMBS_SIZE = 80, 60


def get_thumbs_style():
    THUMBS_STYLES = ['simple', 'button', 'frame']
    try:
        return THUMBS_STYLES[common.config.getint('cornice', 'thumbs_style')]
    except:
        return 'frame' #wx.Platform == '__WXMAC__' and 'frame' or 'button'  


# cache of thumbnails: the key is the full pathname, the value is a
# thumb_info: let's see if this speeds things up
class _ThumbsCache(dict):
    def __init__(self, *args):
        super(_ThumbsCache, self).__init__(*args)
        self.size = 0
        # dictionary used to keep info about the items in cache:
        # the keys are the same as self, the values are 2-tuples
        # (last_access_time, size)
        self._shadow = {}
        
    def __setitem__(self, key, item):
        try:
            bmp = item.bitmap
            depth = max(bmp.GetDepth(), 8)
            size = bmp.GetWidth() * bmp.GetHeight() * depth//8
            self.size += size
        except:
            size = 0
        if self.size >= CACHE_SIZE:
            # need to clean up, remove half of the items (the least used ones)
            # this is linear, need to find a better way
            tmp = [(t, key) for key, (t, size) in self._shadow.items()]
            tmp.sort()
            for i in range(len(tmp)//2):
                del self[tmp[i][1]]
            del tmp
        super(_ThumbsCache, self).__setitem__(key, item)
        self._shadow[key] = [time.time(), size]
        #print 'sizes:', self.size, CACHE_SIZE

    def __getitem__(self, key):
        try:
            item = super(_ThumbsCache, self).__getitem__(key)
        except:
            raise
        else:
            self._shadow[key][0] = time.time() # new access time
            return item

    def get(self, key, default=None):
        if key in self:
            return self[key]
        else:
            return default

    def __delitem__(self, key):
        try:
            super(_ThumbsCache, self).__delitem__(key)
        except:
            raise
        else:
            self.size -= self._shadow[key][1]
            del self._shadow[key]

# end of class _ThumbsCache

_thumbs_cache = _ThumbsCache()


class _ThumbInfo:
    """\
    An entry of the _ThumbsCache
    """
    def __init__(self, bitmap, mtime): #image_size, image_depth, image_format):
        self.bitmap = bitmap
        self.mtime = mtime
##         self.size = image_size
##         self.depth = image_depth
##         self.format = image_format
##         self.img = img

# end of class _ThumbInfo
        

def _create_thumbnail(pil_image):
    """\
    Returns a bitmap with the thumbnail
    """
    return common.create_thumbnail(pil_image, THUMBS_SIZE)


class InvalidBitmap:
    pass

INVALID = InvalidBitmap()


class _Thumb(wx.PyControl):
    def __init__(self, parent, pos, img): #filename='', stat_info=None):
        wx.PyControl.__init__(self, parent, -1, pos=pos,
                              style=wx.WANTS_CHARS|wx.NO_BORDER)
        self.bitmap = None
        self.focused = False
        #self.filename = filename
        self.img = img
        #self.image_type = ''
        #self.mtime = stat_info.mtime #stat_info[stat.ST_MTIME]

        style = get_thumbs_style()
        import thumbs_painters
        try:
            self.painter = getattr(thumbs_painters, '_paint_%s_style' % style)
        except:
            self.painter = thumbs_painters._paint_button_style

        #self.info = stat_info
        self.sortinfo = [
            self.img.name,
            time.strftime('%Y/%m/%d %H:%M', time.localtime(self.img.mtime)),
            self.img.filesize,
            self.img.get_format_string()
            ]
        self._moving = False
        self.SetSize(self.DoGetBestSize())
        wx.EVT_PAINT(self, self.on_paint)
        wx.EVT_LEFT_DOWN(self, self.on_left_down)
        wx.EVT_CHAR(self, self.on_char)
        wx.EVT_LEFT_DCLICK(self, self.on_left_dclick)
        wx.EVT_MOUSEWHEEL(self, self.on_mouse_wheel)
        wx.EVT_MOTION(self, self.on_motion)
        wx.EVT_LEFT_UP(self, self.on_left_up)
        wx.EVT_RIGHT_UP(self, self.on_right_up)

    def DoGetBestSize(self):
        w, h = THUMBS_SIZE
        return wx.Size(w + 10, h + 10 + (self.GetTextExtent('Mp')[1] + 6))

    def AcceptsFocus(self):
        return True

    def on_mouse_wheel(self, event):
        parent = self.GetParent()
        x, y = parent.GetViewStart()
        # why GetWheelDelta returns 0 (at least on Linux/GTK)?
        y -= event.GetWheelRotation() // (event.GetWheelDelta() or 120)
        #print event.GetWheelRotation(), event.GetWheelDelta()
        parent.Scroll(-1, y)

    def on_paint(self, event):
        # first, create the bitmap if needed
        if self.bitmap is None:
            self.create_image()
        bitmap = self.bitmap()
        if bitmap is None: # the weak reference expired, create it again
            #print 'creating again', self.filename
            self.create_image()
            bitmap = self.bitmap()
        dc = wx.PaintDC(self)
        buffer = wx.EmptyBitmap(*self.GetSize())
        memdc = wx.MemoryDC()
        memdc.SelectObject(buffer)
        self.painter(self, memdc, bitmap)
        memdc.SelectObject(wx.NullBitmap)
        dc.DrawBitmap(buffer, 0, 0)

    def create_image(self):
        #print 'create_image', self.filename
        #img = _thumbs_cache.get(self.filename)
        img = _thumbs_cache.get(self.img.path)
        if img and (self.img and img.mtime >= self.img.mtime):
            bitmap = img.bitmap
            #self.img = picture.Picture(self.filename, self.info)
            #self.image_type = img.format
            #self.info[3] = '%sx%sx%s %s' % (img.size + (img.depth, img.format))
        else:
            # no cache found, create the image
            try:
                #self.img = picture.Picture(self.filename, self.info)
                #self.img.load()
                #pil_image = Image.open(fileops.open(self.filename))
                #w, h = pil_image.size
                #bitmap = _create_thumbnail(pil_image)
                w, h = self.img.size
                bitmap = _create_thumbnail(self.img.pil_image)
                #self.image_type = pil_image.format
                #if pil_image.mode == '1': sdepth = '1'
                #elif pil_image.mode == 'P': sdepth = '256'
                #else: sdepth = '16M'
                #self.info[3] = '%sx%sx%s %s' % (w, h, sdepth, pil_image.format)
##                 _thumbs_cache[self.filename] = _ThumbInfo(
##                     bitmap, self.mtime, (w, h), sdepth,
##                     pil_image.format)
                _thumbs_cache[self.img.path] = _ThumbInfo(
                    bitmap, self.img.mtime)
##                 _thumbs_cache[self.filename] = _ThumbInfo(
##                     bitmap, self.img.mtime)
            except:
                import traceback; traceback.print_exc()
                bitmap = INVALID
        # get a weak reference to the bitmap
        self.sortinfo = [
            self.img.name,
            time.strftime('%Y/%m/%d %H:%M', time.localtime(self.img.mtime)),
            self.img.filesize,
            self.img.get_format_string()
            ]
        self.bitmap = weakref.ref(bitmap)
        #self.SetToolTip(wx.ToolTip(self.info[0]))
        self.SetToolTip(wx.ToolTip(self.img.name))
        
    def on_left_down(self, event):
        self.focused = True
        if event.ControlDown():
            self.GetParent().add_to_focused(self)
        elif event.ShiftDown():
            self.GetParent().extend_focused_until(self)
        else:
            self.GetParent().set_focused(self)

    def on_right_up(self, event):
        self.on_left_down(event)
        p = self.GetParent()
        pos = p.ScreenToClient(self.ClientToScreen(event.GetPosition()))
        p.handle_right_up(pos)

    def paint_focus(self):
        w, h = THUMBS_SIZE
        th = self.GetTextExtent('Mp')[1]
##         if wx.Platform != '__WXMAC__':
##             self.RefreshRect((0, h+12, w+10, h+th+16))
##         else:
        self.Refresh()

    def on_char(self, event):
        key = event.GetKeyCode()
        modifiers = [event.ShiftDown(), event.ControlDown(), event.AltDown()]
        parent = self.GetParent()
        if event.HasModifiers():
            parent.handle_key_down(key, modifiers)
        else:
            dispatch = {
                wx.WXK_RETURN: parent.handle_activated,
                wx.WXK_LEFT: parent.select_prev_thumb,
                wx.WXK_RIGHT: parent.select_next_thumb,
                wx.WXK_UP: parent.select_thumb_above,
                wx.WXK_DOWN: parent.select_thumb_below,
                wx.WXK_HOME: parent.select_first_thumb,
                wx.WXK_END: parent.select_last_thumb,
                wx.WXK_PRIOR: parent.page_up,
                wx.WXK_NEXT: parent.page_down,
                }
            function = dispatch.get(key)
            if function is not None:
                return function(modifiers)
            else:
                parent.handle_key_down(key, modifiers)
        event.Skip()

    def on_left_dclick(self, event):
        parent = self.GetParent()
        if not self.focused:
            parent.set_focused(self)
        parent.handle_activated()

    def on_motion(self, event):
        if event.ControlDown() and event.Dragging():
            self.GetParent().handle_dragging()
        elif event.Dragging() and self.GetParent().can_move():
            self._moving = True
            self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        event.Skip()

    def on_left_up(self, event):
        if self._moving:
            self._moving = False
            pos = self.ClientToScreen(event.GetPosition())
            self.SetCursor(wx.NullCursor)
            self.GetParent().move_thumb(
                self, self.GetParent().ScreenToClient(pos))
            
# end of class _Thumb


# event for lazy thumbnails creation in the background: this seems to work
# decently well :)

_CREATE_THUMB_EVENT = wx.NewEventType()


class _CreateThumbEvent(wx.PyEvent):
    def __init__(self, pos, img): #fullname, info):
        wx.PyEvent.__init__(self)
        self.SetEventType(_CREATE_THUMB_EVENT)
        self.pos = pos
        #self.fullname = fullname
        #self.info = info
        self.img = img

# end of class _CreateThumbEvent

def EVT_CREATE_THUMB(win, func):
    win.Connect(-1, -1, _CREATE_THUMB_EVENT, func)

class _ThumbsCreator(threading.Thread):
    def __init__(self, win, thumbs=None, path=""):
        threading.Thread.__init__(self)
        self.win = win
        self.thumbs = thumbs or []
        self.path = path
        self._aborted = False
        self.lock = threading.RLock()
        self._finish = True
        self.cond = threading.Condition()

    def __is_aborted(self):
        try:
            self.lock.acquire()
            return self._aborted
        finally:
            self.lock.release()

    def __set_aborted(self, yes):
        self.lock.acquire()
        #print 'aborted:', self, yes, self.path
        self._aborted = yes
        self.lock.release()

    aborted = property(__is_aborted, __set_aborted)

    def notify_finish(self):
        self.cond.acquire()
        self._finish = True
        self.cond.notify()
        self.cond.release()

    def wait_finish(self):
        self.cond.acquire()
        while not self._finish:
            self.cond.wait()
        self.cond.release()

    def run(self):
        #print 'run', self, self.aborted, self.path
        try:
            for thumb in self.thumbs:
                if common.exiting():
                    return # the user wants to exit the app, stop the job
                elif self.aborted:
                    print('ok, esco!')
                    #_thumbs_monitor.notify_stopped()
                    return
                wx.PostEvent(self.win, _CreateThumbEvent(*thumb))
                time.sleep(0.001)
        finally:
            self.notify_finish()

# end of class _ThumbsCreator


XGAP, YGAP = 10, 10

class PictureThumbs(wx.ScrolledWindow):
    def __init__(self, parent, id):
        wx.ScrolledWindow.__init__(self, parent, id,
                                   style=wx.SUNKEN_BORDER|wx.TAB_TRAVERSAL)
        self.thumbs = []
        self.focused_thumbs = [] #-1
        self.path = None
        self.cols = 0
        self._handlers = {} # PictureList ``event'' handlers (see below)
        self._skip_on_size = False
        self.EnableScrolling(True, True)
        if get_thumbs_style() != 'button':
            self.SetBackgroundColour(wx.WHITE)
        #wx.EVT_SIZE(self, self.on_size)
        wx.EvtHandler.Bind(self, wx.EVT_SIZE, self.on_size)
        EVT_CREATE_THUMB(self, self.on_create_thumb)

        self._lock = threading.RLock()
        self.total_files_and_size = None#0, 0
        self.current_thumb_thread = None

    def on_create_thumb(self, event):
        p = [event.pos[0], event.pos[1]]
        p[1] -= self.GetViewStart()[1] * self.GetScrollPixelsPerUnit()[1]
        #self.thumbs.append(_Thumb(self, p, event.fullname, event.info))
        self.thumbs.append(_Thumb(self, p, event.img))
        
    def on_size(self, event):
        self._width = event.GetSize()[0] - \
                      wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X) - XGAP * 2
        if self._skip_on_size:
            self._skip_on_size = False
        else:
            self._do_layout()
        event.Skip()

    def _do_layout(self, keep_scroll_pos=False):
        """re-layout of the thumbs"""
        if not self.thumbs:
            return
        sx, sy = self.GetViewStart()
        self.Scroll(0, 0)
        thumb_size = self.thumbs[0].GetBestSize()
        width = self._width
        self.cols = (width+XGAP) // (THUMBS_SIZE[0]+XGAP)
        h_space = (width - (THUMBS_SIZE[0]+XGAP) * self.cols) // (self.cols-1)
        #pos = [1, 1]
        pos = [XGAP, YGAP]
        cur_col = 0
        for thumb in self.thumbs:
            thumb.SetPosition(pos)
            cur_col += 1
            if cur_col < self.cols:
                pos[0] += thumb_size[0] + h_space
            else:
                cur_col = 0
                pos[0] = XGAP
                pos[1] += thumb_size[1] + YGAP
        w = self.cols * thumb_size[0] + h_space * (self.cols-1)
        h = pos[1] + thumb_size[1]
        if pos[0] == 1:
            h -= thumb_size[1] + YGAP
        self.SetScrollbars(25, 25, w//25, int(round(h/25)+1), 0, 0, False)
        if keep_scroll_pos:
            self.Scroll(sx, sy)

    def set_path(self, path):
        try:
            self.SetCursor(wx.HOURGLASS_CURSOR)
            self.CaptureMouse()

            # first, clear everything
            self.Scroll(0, 0)
            for thumb in self.thumbs:
                thumb.Destroy()
            self.thumbs = []

            self.focused_thumbs = []

            thumbs_later = []

            w, height = self.GetClientSize()
            width = self._width
            self.cols = (width+XGAP) // (THUMBS_SIZE[0]+XGAP)
            h_space = (width - (THUMBS_SIZE[0]+XGAP)*self.cols) // (self.cols-1)
            thumb_size = None
            #pos = [1, 1]
            pos = [XGAP, YGAP]
            cur_col = 0

            self.path = path
            total_files, total_size = 0, 0
            try:
                dir_list = fileops.listdir(path)
            except OSError:
                return 0, 0

##             if not wx.IsBusy():
##                 wx.BeginBusyCursor()
            call_yield = True
            counter = 0
##             for name in self._sort_filenames(dir_list):
            for img in self._sort_filenames(dir_list):
##                 fullname = os.path.join(path, name)
##                 try:
##                     info = fileops.get_path_info(fullname)
##                 except OSError:
##                     continue
                fullname = img.path #name
                try:
##                     if not info.isfile:
##                         continue
##                     f = fileops.open(fullname)
##                     try: img = Image.open(f)
##                     finally: f.close()
                    if pos[1] <= height:
                        thumb = _Thumb(self, pos, img) #fullname, info)
                        if thumb_size is None:
                            thumb_size = thumb.GetBestSize()
                        self.thumbs.append(thumb)
                    else:
                        # we create these in a background thread
                        thumbs_later.append((pos[:], img)) #fullname, info))
                    cur_col += 1
                    counter += 1
                    if cur_col < self.cols:
                        pos[0] += thumb_size[0] + h_space
                        if call_yield and pos[1] > height:
                            call_yield = False
                    else:
                        cur_col = 0
                        pos[0] = XGAP
                        pos[1] += thumb_size[1] + YGAP
                    if call_yield:
                        wx.Yield() # otherwise, this is not necessary
                    total_files += 1
                    total_size += img.filesize #info.size #info[stat.ST_SIZE]
                except:
                    # the can't be read or is not an image
                    import traceback; traceback.print_exc()
                    pass
            if thumb_size is not None:
                w = self.cols * thumb_size[0] + h_space * (self.cols-1)
                h = pos[1] + thumb_size[1]
                #if h > self.GetClientSize()[1]:
                self._skip_on_size = True            
                if pos[0] == 1:
                    h -= thumb_size[1] + YGAP
                self.SetScrollbars(
                    25, 25, w//25, int(round(h/25)+1), 0, 0, True)
            #self.sort_items(common.sort_index, common.reverse_sort)
            #wx.EndBusyCursor()
            #wx.Yield()
            if thumbs_later:
                # start the thread that will create the rest of thumbnails
                _ThumbsCreator(self, thumbs_later).start()
            return total_files, total_size
        finally:
            self.ReleaseMouse()
            self.SetCursor(wx.NullCursor)

    def _sort_filenames(self, dir_list):
        """\
        Auxiliary method used to sort the list of files in the current dir,
        according to the current sorting. Returns the sorted list
        """
        index = common.sort_index
        if index == common.SORT_TYPE:
            return dir_list # impossible to sort now
        if index == common.SORT_NAME:
            dir_list = list(zip([i.name for i in dir_list], dir_list)) #dir_list[:]
            dir_list.sort()
            dir_list = [t[1] for t in dir_list]
        else:
##             stat_list = [os.stat(os.path.join(self.path, name)) for name in
##                          dir_list]
##             stat_list = [fileops.get_path_info(os.path.join(self.path, name))
##                          for name in dir_list]
            if index == common.SORT_DATE:
                #tmp = zip([i.mtime for i in stat_list], dir_list)
                tmp = list(zip([i.mtime for i in dir_list], dir_list))
            elif index == common.SORT_SIZE:
                #tmp = zip([i.size for i in stat_list], dir_list)
                tmp = list(zip([i.filesize for i in dir_list], dir_list))
            else:
                raise ValueError("Invalid sort_index: %s" % sort_index)
            tmp.sort()
            dir_list = [t[1] for t in tmp]
        if common.reverse_sort:
            dir_list.reverse()
        return dir_list

    def set_focused(self, thumb):
        try:
            self._set_focused_index(self.thumbs.index(thumb))
        except ValueError:
            pass

    def set_all_focused(self):
        self.focused_thumbs = list(range(len(self.thumbs)))
        for t in self.thumbs:
            t.focused = True
            t.paint_focus()

    def add_to_focused(self, thumb):
        index = self.thumbs.index(thumb)
        self.focused_thumbs.append(index)
        thumb.SetFocus()
        thumb.focused = True
        thumb.paint_focus()
        self._ensure_visible(thumb)
        handler = self._handlers.get('selected')
        if handler:
            handler(index)

    def extend_focused_until(self, thumb):
        old_focused = set(self.focused_thumbs)
        index = self.thumbs.index(thumb)
        if index in old_focused:
            i = self.focused_thumbs.index(index)
            for j in range(i+1, len(self.focused_thumbs)):
                t = self.thumbs[self.focused_thumbs[j]]
                t.focused = False
                t.paint_focus()
            self.focused_thumbs = self.focused_thumbs[:i+1]
        else:
            if self.focused_thumbs:
                last = self.focused_thumbs[-1]
            else:
                last = 0
            if index < last: r = list(range(index+1, last))
            else: r = list(range(last, index))
            for i in r:
                if i not in old_focused:
                    self.focused_thumbs.append(i)
                    t = self.thumbs[i]
                    t.focused = True
                    t.paint_focus()
            self.add_to_focused(thumb)

    def _set_focused_index(self, index):
##         if 0 <= self.focused_thumb < len(self.thumbs):
##             old_focused = self.thumbs[self.focused_thumb]
##             old_focused.focused = False
##             old_focused.paint_focus()
        for i in self.focused_thumbs:
            if i != index:
                t = self.thumbs[i]
                t.focused = False
                t.paint_focus()
        self.focused_thumbs = []
        self.add_to_focused(self.thumbs[index])
##         try:
##             self.focused_thumbs.append(index)
##             thumb = self.thumbs[index]
##             thumb.focused = True
##             thumb.SetFocus()
##             thumb.paint_focus()
##             self._ensure_visible(thumb)
##             handler = self._handlers.get('selected')
##             if handler:
##                 handler(index)
##         except ValueError:
##             self.focused_thumb = -1

    def page_up(self, arg=None):
        y = self.GetViewStart()[1]
        h = self.GetClientSize()[1]
        yu = self.GetScrollPixelsPerUnit()[1]
        self.Scroll(-1, math.floor(y - h/yu))

    def page_down(self, arg=None):
        y = self.GetViewStart()[1]
        h = self.GetClientSize()[1]
        yu = self.GetScrollPixelsPerUnit()[1]
        self.Scroll(-1, math.ceil(y + h/yu))

    def _ensure_visible(self, thumb):
        assert thumb is not None
        x, y = thumb.GetPosition()
        ux, uy = self.CalcUnscrolledPosition(x, y)
        w, h = thumb.GetSize()
        mx, my = self.GetViewStart()
        mw, mh = self.GetClientSize()
        xu, yu = self.GetScrollPixelsPerUnit()
        if y < 0:
            scroll_y = math.floor(uy / yu)
        elif y + h > mh:
            gap = (uy+h) - mh
            scroll_y = math.ceil((my + gap) / yu)
        else:
            scroll_y = -1
        if x < 0:
            scroll_x = math.floor(ux / xu)
        elif x + w > mw:
            gap = (x+w) - mw
            scroll_x = ((mx + gap) / xu)
        else:
            scroll_x = -1
        self.Scroll(scroll_x, scroll_y)

    def select_first_thumb(self, modifiers=None):
        if self.thumbs:
            if modifiers and modifiers[0]:
                self.extend_focused_until(self.thumbs[0])
            else:
                self._set_focused_index(0)

    def select_last_thumb(self, modifiers=None):
        if self.thumbs:
            if modifiers and modifiers[0]:
                self.extend_focused_until(self.thumbs[-1])
            else:
                self._set_focused_index(len(self.thumbs)-1)
            
    def select_next_thumb(self, modifiers=None):
        if self.focused_thumbs:
            index = self.focused_thumbs[-1] + 1
        else:
            index = len(self.thumbs)
        #index = self.focused_thumb + 1
        if index < len(self.thumbs):
            if modifiers and modifiers[0]:
                self.extend_focused_until(self.thumbs[index])
            else:
                self._set_focused_index(index)

    def select_prev_thumb(self, modifiers=None):
        if self.focused_thumbs:
            index = self.focused_thumbs[-1] - 1
        else:
            index = -1
        #index = self.focused_thumb - 1
        if index >= 0:
            if modifiers and modifiers[0]:
                self.extend_focused_until(self.thumbs[index])
            else:
                self._set_focused_index(index)

    def select_thumb_above(self, modifiers=None):
        cols = self.cols 
        if self.focused_thumbs:
            index = self.focused_thumbs[-1] - cols
        else:
            index = -1
        #index = self.focused_thumb - cols
        if index >= 0:
            if modifiers and modifiers[0]:
                self.extend_focused_until(self.thumbs[index])
            else:
                self._set_focused_index(index)
            
    def select_thumb_below(self, modifiers=None):
        cols = self.cols 
        if self.focused_thumbs:
            index = self.focused_thumbs[-1] + cols
        else:
            index = -1
        #index = self.focused_thumb + cols
        if index < len(self.thumbs):
            if modifiers and modifiers[0]: # shift down
                self.extend_focused_until(self.thumbs[index])
            else:
                self._set_focused_index(index)

    def handle_key_down(self, key, modifiers):
        handler = self._handlers.get('key_down')
        if handler:
            handler(key, modifiers)

    def handle_activated(self, modifiers=None):
        handler = self._handlers.get('activated')
        if handler:
            if self.focused_thumbs: index = self.focused_thumbs[-1]
            else: index = -1
            handler(index) #self.focused_thumb)

    def handle_dragging(self):
        handler = self._handlers.get('dragging')
        if handler:
            handler()

    def handle_right_up(self, position):
        handler = self._handlers.get('right_click')
        if handler:
            handler(position)

    def can_move(self):
        return False

    def move_thumb(self, thumb, xxx_todo_changeme):
        (x, y) = xxx_todo_changeme
        for i, t in enumerate(self.thumbs):
            xx, yy = t.GetPosition()
            ww, hh = t.GetSize()
            if x < xx+ww and y < yy+hh:
                if t is not thumb:
                    idx = self.thumbs.index(thumb)
                    for f in self.focused_thumbs:
                        self.thumbs[f].focused = False
                        self.thumbs[f].paint_focus()
                    self.thumbs.remove(thumb)
                    if idx < i:
                        self.thumbs.insert(i-1, thumb)
                        self.focused_thumbs = [i-1]
                    else:
                        self.thumbs.insert(i, thumb)
                        self.focused_thumbs = [i]
                    self._do_layout(True)
                    thumb.focused = True
                    thumb.SetFocus()
                    thumb.paint_focus()
                    return

    # the following methods are the interface exposed to PictureList

    def sort_items(self, sort_index=common.SORT_NAME, reverse=False):
        assert self.thumbs is not None
        for i in self.focused_thumbs:
            self.thumbs[i].focused = False
        self.focused_thumbs = []
        if sort_index == common.SORT_DATE:
            tmp = [(t.img.mtime, t) for t in self.thumbs]
        else:
            tmp = [(t.sortinfo[sort_index], t) for t in self.thumbs]
        tmp.sort()
        if reverse:
            tmp.reverse()
        self.thumbs = [t[1] for t in tmp]
        self._do_layout(True)
        
    def get_selected_filenames(self):
        """\
        Returns a list of the selected filenames, to perform deletion and
        (in the future) cut & paste. In thumbnail mode we disallow multiple
        selections.
        """
##         if self.focused_thumb >= 0:
##             return [self.thumbs[self.focused_thumb].filename]
##         else:
##             return []
        return list(set([self.thumbs[i].img.path for i in self.focused_thumbs]))

    def get_active_item_info(self):
        """\
        Returns the info associated with the current item:
        (name, date, size, properties)
        """
        if self.focused_thumbs: index = self.focused_thumbs[-1]
        else: index = -1
        return self.get_item_info(index) #self.focused_thumb)

    def get_active_item_path(self):
        if self.focused_thumbs: index = self.focused_thumbs[-1]
        else: index = -1
        if index >= 0:
            return self.thumbs[index].img.path

    def get_item_path(self, index):
        return self.thumbs[index].img.path

    def get_item_info(self, index):
        """\
        Returns the info associated with the item at index:
        (name, date, size, properties)
        """
        if 0 <= index < len(self.thumbs):
            return self.thumbs[index].sortinfo
        else:
            return ['', '', 0, '']
            
    def get_selected_item_index(self):
        #return self.focused_thumb
        if self.focused_thumbs: return self.focused_thumbs[-1]
        else: return -1

    # binders for event handlers supplied by the PictureList
    # we do this way instead of generating custom events and let the
    # PictureList handle them because it's easier
    def bind_item_selected(self, handler):
        self._handlers['selected'] = handler

    def bind_item_activated(self, handler):
        self._handlers['activated'] = handler

    def bind_key_down(self, handler):
        self._handlers['key_down'] = handler

    def bind_begin_dragging(self, handler):
        self._handlers['dragging'] = handler

    def bind_right_click(self, handler):
        self._handlers['right_click'] = handler

# end of class PictureThumbs


if __name__ == '__main__':
    # test
    app = wx.PySimpleApp(0)
    frame = wx.Frame(None, -1, "Test thumbs")
    win = PictureThumbs(frame, -1)
    frame.SetSize((400, 300))
    app.SetTopWindow(frame)
    frame.Show()
    import time
    time.sleep(2)
    wx.CallAfter(win.set_path, '/home/alb/img')
    app.MainLoop()
