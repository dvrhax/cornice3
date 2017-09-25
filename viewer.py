# viewer.py: image viewer
# arch-tag: image viewer
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL



import wx, wx.xrc
import os, math, time
from PIL import Image

import common, fileops
import exif_info


# initialized in main.py...
_blank_cursor = None


_really_skip_size = wx.Platform == '__WXGTK__' and wx.VERSION[:2] < (2, 5)


class CorniceViewer(wx.ScrolledWindow):
    zoom_levels = [ 0.1, 0.25, 0.5, 0.75, 1, 1.1, 1.3, 1.5, 1.7, 2, 2.5,
                    3, 4, 5, 6, 7, 8 ]
    DEFAULT_ZOOM = 4 # index in the zoom_levels list
    rotation_levels = [ 180, 90, 0, 270 ]
    DEFAULT_ROTATION = 2
    
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent, -1,
                                   style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.bitmap = wx.Bitmap(1, 1)
        self.SetBackgroundColour(wx.BLACK)
        self.picture_list = None
        self.cornice_browser = None # reference to the browser window

        self.dib = None
        self.dibsize = None
        
        self.pil_image = None
        self.fit_image = common.config.getboolean('cornice', 'fit_image')
        self.fit_enlarge = common.config.getboolean('cornice', 'fit_enlarge')
        self._changed = False
        self._wait_a_minute = False
        self._skip_on_size = False
        self.zoom_index = self.DEFAULT_ZOOM
        self.rotation_index = self.DEFAULT_ROTATION
        self.default_fullscreen = common.config.getboolean('cornice',
                                                           'fullscreen')
        self.keep_settings = common.config.getboolean('cornice',
                                                  'remember_settings')
        self._current_file_name = '' # to update the statusbar
        try:
            self.interpolation = common.interpolations[
                common.config.getint('cornice', 'interpolation')]
        except:
            self.interpolation = Image.NEAREST
        # slideshow-related variables
        self.slideshow_fullscreen = common.config.getboolean(
            'cornice', 'slideshow_fullscreen')
        self.slideshow_delay = common.config.getint(
            'cornice', 'slideshow_delay') # in seconds
        self.slideshow_fit = common.config.getboolean(
            'cornice', 'slideshow_fit')
        self.slideshow_cycle = common.config.getboolean(
            'cornice', 'slideshow_cycle')
        self.slideshow_random = common.config.getboolean(
            'cornice', 'slideshow_random')
        self._was_fullscreen = False # to restore the previous state
        # timer to show slides
        SLIDESHOW_ID = wx.NewId()
        self.slideshow_timer = wx.Timer(self, SLIDESHOW_ID)        
        #wx.EVT_TIMER(self, SLIDESHOW_ID, self._next_slide)
        wx.EvtHandler.Bind(self, wx.EVT_TIMER, self._next_slide, id=SLIDESHOW_ID)
        # timer to hide the mouse cursor in fullscreen mode
        HIDE_CURSOR_ID = wx.NewId()
        self.hide_cursor_timer = wx.Timer(self, HIDE_CURSOR_ID)
        #wx.EVT_TIMER(self, HIDE_CURSOR_ID, self._hide_mouse_cursor)
        wx.EvtHandler.Bind(self, wx.EVT_TIMER, self._hide_mouse_cursor, id=HIDE_CURSOR_ID)
        #wx.EVT_MOTION(self, self.on_mouse_move)
        wx.EvtHandler.Bind(self, wx.EVT_MOTION, self.on_mouse_move)
        self._drag_start = 0, 0
        #wx.EVT_LEFT_DOWN(self, self.on_left_down)
        wx.EvtHandler.Bind(self, wx.EVT_LEFT_DOWN, self.on_left_down)
        #wx.EVT_LEFT_UP(self, self.on_left_up)
        wx.EvtHandler.Bind(self, wx.EVT_LEFT_UP, self.on_left_up)
        
        def hide(event):
            # free memory...
            self.bitmap = wx.Bitmap(1, 1)
            self.pil_image = None
            self.dib = None
            
            if parent.IsFullScreen():
                self.toggle_fullscreen()
            if self.slideshow_timer.IsRunning():
                self.slideshow()
            parent.Hide()
            if self.picture_list is not None:
                self.picture_list._restore_selected_image()
            if self.cornice_browser is not None:
                self.cornice_browser.Show()
        evtList = ((wx.EVT_PAINT, self.on_paint),
                   (wx.EVT_SIZE, self.on_size),
                   (wx.EVT_CHAR, self.on_char))
        #wx.EVT_CLOSE(parent, hide)
        wx.EvtHandler.Bind(parent, wx.EVT_CLOSE, hide)
        #wx.EVT_PAINT(self, self.on_paint)
        #wx.EVT_SIZE(self, self.on_size)
        #wx.EVT_CHAR(self, self.on_char)
        for e in evtList:
            wx.EvtHandler.Bind(self, e[0], e[1])
        self._bind_toolbar_events()
        self.SetScrollbars(5, 5, 0, 0)

    def _bind_toolbar_events(self):
        parent = self.GetParent()
        ###wx.EVT_MENU(parent, wx.xrc.XRCID('first_image'),
        ###            lambda e: self.view_first_image())
        ###wx.EvtHandler.Bind(parent, wx.EVT_MENU, lambda e: self.view_first_image(), id=wx.xrc.XRCID('first_image'))
        evts = (('first_image', lambda e: self.view_first_image()),
                ('prev_image', lambda e: self.view_prev_image()),
                ('next_image', lambda e: self.view_next_image()),
                ('last_image', lambda e: self.view_last_image()),
                ('zoom_out', lambda e: self.zoom_out()),
                ('zoom_in', lambda e: self.zoom_in()),
                ('fit_screen', lambda e: self.fit_screen()),
                ('rotate_left', lambda e: self.rotate_left()),
                ('rotate_right', lambda e: self.rotate_right()),
                ('full_screen', lambda e: self.toggle_fullscreen()),
                ('refresh_image', lambda e: self.refresh_image()),
                ('default_zoom', lambda e: self.default_zoom()),
                ('slideshow', self.slideshow),
                ('remember_settings', lambda e: self.toggle_remember_settings(False)))

        for ids, func in evts:
            wx.EvtHandler.Bind(parent, wx.EVT_MENU, func, id=wx.xrc.XRCID(ids))

        ###wx.EVT_MENU(parent, wx.xrc.XRCID('prev_image'),
        ###            lambda e: self.view_prev_image())
        ###wx.EVT_MENU(parent, wx.xrc.XRCID('next_image'),
                    ###lambda e: self.view_next_image())
        ###wx.EVT_MENU(parent, wx.xrc.XRCID('last_image'),
                    ###lambda e: self.view_last_image())
        ###wx.EVT_MENU(parent, wx.xrc.XRCID('zoom_out'),
                    ###lambda e: self.zoom_out())
        ###wx.EVT_MENU(parent, wx.xrc.XRCID('zoom_in'),
                    ###lambda e: self.zoom_in())
        ###wx.EVT_MENU(parent, wx.xrc.XRCID('fit_screen'),
                    ###lambda e: self.fit_screen())
        ###wx.EVT_MENU(parent, wx.xrc.XRCID('rotate_left'),
                    ###lambda e: self.rotate_left())
        ###wx.EVT_MENU(parent, wx.xrc.XRCID('rotate_right'),
                    ###lambda e: self.rotate_right())
        ###wx.EVT_MENU(parent, wx.xrc.XRCID('full_screen'),
                    ###lambda e: self.toggle_fullscreen())
        ###wx.EVT_MENU(parent, wx.xrc.XRCID('refresh_image'),
                    ######lambda e: self.refresh_image())
        ###wx.EVT_MENU(parent, wx.xrc.XRCID('default_zoom'),
                    ###lambda e: self.default_zoom())
        ###wx.EVT_MENU(parent, wx.xrc.XRCID('slideshow'),
                    ###self.slideshow)
        ###wx.EVT_MENU(parent, wx.xrc.XRCID('remember_settings'),
                    ###lambda e: self.toggle_remember_settings(False))

    def toggle_remember_settings(self, update_tool=True):
        self.keep_settings = not self.keep_settings
        if update_tool:
            self.GetParent().GetToolBar().ToggleTool(
                wx.xrc.XRCID('remember_settings'), self.keep_settings)
            

    def update_statusbar_info(self):
        # idle handler, to update the first field of the statusbar which is
        # cleared when the mouse is over some toolbar button
        sb = self.GetParent().GetStatusBar()
        if sb.GetStatusText(0) != self._current_file_name:
            sb.SetStatusText(self._current_file_name, 0)
        
    def _navigate_image(self, function):
        self.clear_flags()
        image, info = function()
        if image is not None:
            wx.CallAfter(self._view_image_internal, image, info)

    def view_first_image(self):
        self._navigate_image(self.picture_list.view_first_image)
        
    def view_prev_image(self):
        self._navigate_image(self.picture_list.view_prev_image)
        
    def view_next_image(self):
        self._navigate_image(self.picture_list.view_next_image)

    def view_last_image(self):
        self._navigate_image(self.picture_list.view_last_image)

    def refresh_image(self):
        self._navigate_image(self.picture_list.view_current_image)

    def zoom_out(self):
        self.GetParent().GetToolBar().ToggleTool(wx.xrc.XRCID('fit_screen'),
                                                 False)
        if self.zoom_index > 0:
            self.fit_image = False
            self.zoom_index -= 1
            wx.CallAfter(self._view_image_internal, self.pil_image)

    def zoom_in(self):
        self.GetParent().GetToolBar().ToggleTool(wx.xrc.XRCID('fit_screen'),
                                                 False)
        if self.zoom_index < len(self.zoom_levels)-1:
            self.fit_image = False
            self.zoom_index += 1
            wx.CallAfter(self._view_image_internal, self.pil_image)

    def default_zoom(self):
        self.GetParent().GetToolBar().ToggleTool(
            wx.xrc.XRCID('fit_screen'), False)
        self.zoom_index = self.DEFAULT_ZOOM
        self.fit_image = False
        self._skip_on_size = _really_skip_size
        wx.CallAfter(self._view_image_internal, self.pil_image)       

    def fit_screen(self):
        self.fit_image = not self.fit_image
        self._skip_on_size = _really_skip_size
        self.GetParent().GetToolBar().ToggleTool(wx.xrc.XRCID('fit_screen'),
                                                 self.fit_image)
        wx.CallAfter(self._view_image_internal, self.pil_image)

    def rotate_left(self):
        self.rotation_index = (self.rotation_index - 1) % \
                              len(self.rotation_levels)
        wx.CallAfter(self._view_image_internal, self.pil_image)
        
    def rotate_right(self):
        self.rotation_index = (self.rotation_index + 1) % \
                              len(self.rotation_levels)
        wx.CallAfter(self._view_image_internal, self.pil_image)

    def on_size(self, event):
        if self._skip_on_size:
            self._skip_on_size = False
            if wx.Platform != '__WXMAC__':
                return
        self._changed = True
        self._wait_a_minute = True
        w, h = self.paint_image()
        if not self.fit_image:
            self.SetScrollbars(10, 10, int(round(w/10)+1), int(round(h/10)+1))
        else:
            self.SetScrollbars(5, 5, 1, 1)
        if not self.pil_image:
            zoom = 0
        else:
            if self.rotation_index % 2:
                zoom = h / self.pil_image.size[0] * 100
            else:
                zoom = w / self.pil_image.size[0] * 100
        self.GetParent().GetStatusBar().SetStatusText('%.0f%%' % zoom, 3)
        self._wait_a_minute = False

    def paint_image(self):
        if not self._changed or not self.pil_image:
            return 0, 0
        self._changed = False
        if not self.fit_image and self.zoom_index != self.DEFAULT_ZOOM:
            size = [ int(c * self.zoom_levels[self.zoom_index]) for c in
                     self.pil_image.size ]
            pil_image = self.pil_image.resize(size, self.interpolation)
        else:
            pil_image = self.pil_image.copy()

        if self.rotation_index != self.DEFAULT_ROTATION:
            degree = self.rotation_levels[self.rotation_index]
            pil_image = pil_image.rotate(degree)

        if self.fit_image:
            self.zoom_index = self.DEFAULT_ZOOM # reset to default
            if self.fit_enlarge:
                client_size = self.GetParent().GetClientSize()
                try:
                    ratio = min([ c / i  for c,i in zip(client_size,
                                                        pil_image.size)])
                except ZeroDivisionError:
                    ratio = 0
                size = [ int(ratio * s) for s in self.pil_image.size ]
                pil_image = pil_image.resize(size, self.interpolation)
            else:
                if self.rotation_index == self.DEFAULT_ROTATION:
                    pil_image = pil_image.copy()
                pil_image.thumbnail(self.GetParent().GetClientSize(),
                                    self.interpolation)
##             pil_image.thumbnail(self.GetParent().GetClientSize(),
##                                 self.interpolation)

        #--------------------------------------------------
        if wx.Platform == '__WXMSW__' and hasattr(wx.DC, 'GetHDC'):
            def later():
                import ImageWin
                if pil_image.mode not in ('RGB', 'RGBA'):
                    self.dib = ImageWin.Dib(pil_image.convert('RGB'))
                else:
                    self.dib = ImageWin.Dib(pil_image)
                self.dibsize = pil_image.size
                self.Refresh()
        else:
            def later():
                img = wx.Image(*pil_image.size)
                if common.has_alpha and pil_image.mode == 'RGBA':
                    alpha = pil_image.split()[3].tobytes()
                    img.SetData(pil_image.convert('RGB').tobytes())
                    img.SetAlphaBuffer(alpha)
                elif pil_image.mode != 'RGB':
                    img.SetData(pil_image.convert('RGB').tobytes())
                else:
                    img.SetData(pil_image.tobytes())
                self.bitmap = wx.Bitmap(img)
                mask = common.get_mask(pil_image)
                if mask is not None:
                    self.bitmap.SetMask(mask)
                self.Refresh()
        #--------------------------------------------------
        wx.CallAfter(later) # the actual drawing happens on idle time
        return pil_image.size
        
    def on_paint(self, event):
        dc = wx.PaintDC(self)
        if self._wait_a_minute: return
        self.PrepareDC(dc)
        ###dc.BeginDrawing()
        if wx.Platform == '__WXMSW__' and self.dib is not None \
               and hasattr(dc, 'GetHDC'):
            w, h = self.GetClientSize()
            iw, ih = self.dibsize
            x, y = max((w - iw)//2, 0), max((h - ih)//2, 0)
            self.dib.draw(dc.GetHDC(), (x, y, x+iw, y+ih))
        else:
            iw, ih = self.bitmap.GetWidth(), self.bitmap.GetHeight()
            w, h = self.GetClientSize()
            dc.DrawBitmap(self.bitmap, max((w - iw)//2, 0),
                          max((h - ih)//2, 0), True)
        ###dc.EndDrawing()

    def view_image(self, image_file, info):
        parent = self.GetParent()
        if not parent.IsShown():
            parent.Show()
            if self.default_fullscreen:
                self._show_parent_fullscreen()
        def go():
            f = fileops.open(image_file)
            try:
                pil_image = exif_info.exif_orient(f, Image.open(f))
                self._view_image_internal(pil_image, info)
            finally:
                del f
        wx.CallAfter(go)
        
    def _view_image_internal(self, pil_image, info=None):
        parent = self.GetParent()
        self.pil_image = pil_image
        self._changed = True
        if info is not None:
            self._current_file_name = info[0]
            parent.SetTitle(info[0] + ' - Cornice')
            sb = parent.GetStatusBar()
            sb.SetStatusText(info[0], 0)
            sb.SetStatusText(common.format_size_str(info[2]), 1)
            sb.SetStatusText(info[3], 2)
        if not (wx.IsBusy() or self.slideshow_timer.IsRunning()):
            wx.BeginBusyCursor()
        def go():
            try:
                w, h = self.paint_image()
            except Exception as e:
                wx.LogError(str(e))
                return
            self._skip_on_size = _really_skip_size
            if not self.fit_image:
                self.SetScrollbars(10, 10, int(round(w/10)+1),
                                   int(round(h/10)+1))
            else:
                self.SetScrollbars(5, 5, 1, 1)
            if not parent.IsShown():
                parent.Show()
                if self.default_fullscreen:
                    self._show_parent_fullscreen()
            if self.rotation_index % 2:
                zoom = h / pil_image.size[0] * 100
            else:
                zoom = w / pil_image.size[0] * 100
            parent.GetStatusBar().SetStatusText('%.0f%%' % zoom, 3)
            if wx.IsBusy():
                wx.EndBusyCursor()
        wx.CallAfter(go)

    def on_char(self, event):
        x, y = self.GetViewStart()
        key = event.GetKeyCode()
        nav_functions = {
            wx.WXK_PAGEDOWN: self.view_next_image,
            wx.WXK_SPACE: self.view_next_image,
            wx.WXK_PAGEUP: self.view_prev_image,
            wx.WXK_BACK: self.view_prev_image,
            wx.WXK_HOME: self.view_first_image,
            wx.WXK_END: self.view_last_image,
            wx.WXK_F5: self.refresh_image,
            ord('f'): self.fit_screen,
            ord('-'): self.zoom_out,
            ord('['): self.zoom_out,
            ord('+'): self.zoom_in,
            ord(']'): self.zoom_in,
            ord('1'): self.default_zoom,
            ord('l'): self.rotate_left,
            ord('r'): self.rotate_right,
            ord('s'): self.slideshow,
            ord('k'): self.toggle_remember_settings,
            }
        if key in nav_functions and not event.HasModifiers():
            nav_functions[key]()
        elif key == wx.WXK_LEFT:
            self.Scroll(max(0, x-1), y)
        elif key == wx.WXK_RIGHT:
            self.Scroll(x+1, y)
        elif key == wx.WXK_UP:
            self.Scroll(x, max(0, y-1))
        elif key == wx.WXK_DOWN:
            self.Scroll(x, y+1)
        elif key == wx.WXK_ESCAPE:
            if self.slideshow_timer.IsRunning():
                self.slideshow()
            self.GetParent().Close()
            if self.picture_list is not None:
                self.picture_list.SetFocus()
        elif (wx.Platform != '__WXMAC__' and key == wx.WXK_F11) or \
                 (wx.Platform == '__WXMAC__' and key == wx.WXK_F12 and \
                  wx.VERSION[:2] >= (2, 5)):
            self.toggle_fullscreen()
        elif event.ControlDown() and key in (ord('q'), ord('q')-ord('a')+1):
            try:
                common.exit_app()
            except Exception as e:
                print(e)

    def clear_flags(self):
        if not self.keep_settings:
            self.rotation_index = self.DEFAULT_ROTATION
            self.zoom_index = self.DEFAULT_ZOOM
            
    def on_scroll(self, event):
        self.bitmap.Refresh(False)
        event.Skip()

    def toggle_fullscreen(self):
        parent = self.GetParent()
        if parent.IsFullScreen():
            parent.GetStatusBar().Show()
            parent.GetToolBar().Show()
            parent.ShowFullScreen(False)
            # restore the mouse cursor
            self.SetCursor(wx.NullCursor)
            self.hide_cursor_timer.Stop()
        else:
            self._show_parent_fullscreen()
        self.SetFocus()

    def _show_parent_fullscreen(self):
        parent = self.GetParent()
        parent.GetStatusBar().Hide()
        parent.GetToolBar().Hide()
        self._skip_on_size = wx.Platform == '__WXGTK__'
        parent.ShowFullScreen(True)
        # start the timer to hide the cursor
        #self.SetCursor(wx.StockCursor(wx.CURSOR_BLANK))
        self.hide_cursor_timer.Start(1500)
        # these two 'hidden' adjust options are needed because on GTK
        # wxWindows keeps window decorations even in fullscreen mode,
        # so we let the user tune the size/position of the frame to
        # hide them
        if common.config.has_option('cornice', 'adjust_fullscreen_size'):
            try:
                dw, dh = [int(v) for v in common.config.get(
                    'cornice', 'adjust_fullscreen_size').split(',')]
                w = wx.SystemSettings_GetMetric(wx.SYS_SCREEN_X)
                h = wx.SystemSettings_GetMetric(wx.SYS_SCREEN_Y)
                parent.SetClientSize((w+dw, h+dh))
            except ValueError:
                pass
        if common.config.has_option('cornice', 'adjust_fullscreen_position'):
            try:
                x, y = [int(v) for v in common.config.get(
                    'cornice', 'adjust_fullscreen_position').split(',')]
                parent.SetPosition((x, y))
            except ValueError:
                pass

    def on_left_down(self, event):
        self._drag_start = event.GetPosition()
        event.Skip()

    def on_left_up(self, event):
        self.SetCursor(wx.NullCursor)

    def on_mouse_move(self, event):
        if event.LeftIsDown() and event.Dragging():
            self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
            x, y = self._drag_start
            self._drag_start = xx, yy = event.GetPosition()
            px, py = self.GetScrollPixelsPerUnit()
            vx, vy = self.GetViewStart()
            self.Scroll(vx + (x - xx) // 5, vy + (y - yy) // 5)
        elif self.GetParent().IsFullScreen():
            self.SetCursor(wx.NullCursor)
            self.hide_cursor_timer.Start()
        event.Skip()
        
    def _hide_mouse_cursor(self, *args):
        try:
            self.SetCursor(_blank_cursor) #wx.StockCursor(wx.CURSOR_BLANK))
        except wx.PyAssertionError:
            raise

    def _start_slideshow(self):
        # start the show
        parent = self.GetParent()
        if self.slideshow_fit:
            self.fit_image = True
        self._was_fullscreen = parent.IsFullScreen()
        if self.slideshow_fullscreen:
            self._show_parent_fullscreen()
            self.SetFocus()
        # start from the beginning...
        def go():
            if not self.slideshow_random:
                self.view_first_image()
            else:
                self._navigate_image(self.picture_list.next_random_image)

            self.slideshow_timer.Start(self.slideshow_delay * 1000)
            self.GetParent().GetToolBar().ToggleTool(
                wx.xrc.XRCID('slideshow'), True)
        wx.CallAfter(go)

    def _stop_slideshow(self):
        # stop the show
        self.slideshow_timer.Stop()
        if self._was_fullscreen != self.GetParent().IsFullScreen():
            self.toggle_fullscreen()
        self.GetParent().GetToolBar().ToggleTool(
            wx.xrc.XRCID('slideshow'), False)

    def slideshow(self, *args):
        """\
        Starts or stops a slideshow
        """
        if self.slideshow_timer.IsRunning():
            self._stop_slideshow()
        else:
            self._start_slideshow()

    def _next_slide(self, event):
        if not self.slideshow_random:
            image, info = self.picture_list.view_next_image()
        else:
            image, info = self.picture_list.next_random_image()
        if image is None:
            if self.slideshow_cycle:
                self._start_slideshow()
            else:
                self._stop_slideshow() 
        else:
            wx.CallAfter(self._view_image_internal, image, info)

# end of class CorniceViewer


class CorniceViewerFrame(wx.Frame):
    def __init__(self, parent, title):
        try:
            w, h = [int(v) for v in
                    common.config.get('cornice', 'viewer_size').split(',')]
        except ValueError:
            w, h = -1, -1
        wx.Frame.__init__(self, parent, -1, title, size=(w, h),
                          name='cornice_viewer')
        if wx.Platform == '__WXMAC__':
            self._size_before_fullscreen = None
            self._pos_before_fullscreen = None
        icon = common.get_theme_icon()
        self.SetIcon(icon)

        res = wx.xrc.XmlResource.Get()
        common.load_from_theme('toolbars.xrc')
        toolbar = res.LoadToolBar(self, 'viewer_toolbar')
        if wx.Platform == '__WXMAC__' and wx.VERSION[:2] < (2, 5):
            # remove the fullscreen button because it doesn't work :-(
            toolbar.RemoveTool(wx.xrc.XRCID('full_screen'))
        self.SetToolBar(toolbar)
        toolbar.ToggleTool(wx.xrc.XRCID('fit_screen'),
                           common.config.getboolean('cornice', 'fit_image'))
        toolbar.ToggleTool(wx.xrc.XRCID('remember_settings'),
                           common.config.getboolean('cornice',
                                                'remember_settings'))
        
        statusbar = self.CreateStatusBar(4)
        # fields: name, size, properties, zoom
        statusbar.SetStatusWidths([-1, 150, 200, 50])

        bg = self.GetBackgroundColour()
        self.SetBackgroundColour(wx.BLACK)
        statusbar.SetBackgroundColour(bg)
        
    def Show(self, show=True, first=[True]):
        wx.Frame.Show(self, show)
        if wx.Platform == '__WXMAC__' and show and first[0]:
            w, h = self.GetClientSize()
            self.SetClientSize((w+1, h))
            self.SetClientSize((w, h))
            first[0] = False

# end of class CorniceViewerFrame
