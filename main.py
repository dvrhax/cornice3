# main.py: main module of cornice
# arch-tag: main module of cornice
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

import wx
import locale, os, sys
import glob

import resources, common, bmarks, preview, picture_list, viewer
import dirctrl, fileops, vfs
import clipboard
import exif_info

import collection, albums


class CorniceBrowser(wx.Frame):
    def __init__(self, img_viewer, path, **kwds):
        wx.Frame.__init__(self, None, -1, "")
        self.window_1 = wx.SplitterWindow(self, -1, style=0)
        self.window_1_pane_1 = wx.Panel(self.window_1, -1, style=0)
        self.window_2 = wx.SplitterWindow(self.window_1_pane_1, -1, style=0)
        self.window_2_pane_1 = wx.Panel(self.window_2, -1, style=0)
        if wx.Platform == '__WXGTK__':
            nbstyle = wx.NB_BOTTOM
        else:
            nbstyle = 0
        self.preview_notebook = wx.Notebook(self.window_2, -1, style=nbstyle)
        #self.preview_panel = preview.PreviewPanel(self.window_2, -1)
        self.preview_panel = preview.PreviewPanel(self.preview_notebook, -1)
        self.exif_info = exif_info.ExifInfo(self.preview_notebook)
        self.preview_notebook.AddPage(self.preview_panel, _("Preview"))
        self.preview_notebook.AddPage(self.exif_info, _("Exif data"))
        
        self.window_1_pane_2 = wx.Panel(self.window_1, -1, style=0)
        self.statusbar = self.CreateStatusBar(4)

        self.notebook = wx.Notebook(self.window_2_pane_1, -1)
        self.dir_ctrl = dirctrl.DirCtrl(self.notebook, -1, 
                                        style=wx.SUNKEN_BORDER |
                                        wx.DIRCTRL_DIR_ONLY)
        self.bookmarks = bmarks.BookMarksCtrl(self.notebook)
        self.albums = albums.AlbumsCtrl(self.notebook)
            
        self.viewer = img_viewer
        self.viewer.cornice_browser = self
        
        self.options = kwds
        self.picture_list = picture_list.PictureList(self.window_1_pane_2, -1,
                                                     self.options, self)
        self.albums.picture_list = self.picture_list
        
        # Menu Bar
        res = wx.xrc.XmlResource.Get()
        res.Load('resources.xrc')
        self.SetMenuBar(res.LoadMenuBar('menubar'))
        self.bind_menubar_events()
        
        if wx.Platform == '__WXMAC__':
            wx.App_SetMacAboutMenuItemId(wx.xrc.XRCID('about'))
            wx.App_SetMacPreferencesMenuItemId(wx.xrc.XRCID('preferences'))
            wx.App_SetMacExitMenuItemId(wx.xrc.XRCID('exit'))
            wx.App_SetMacHelpMenuTitleName('Help')
        # Tool Bar
##         res.Load('toolbars.xrc')
        common.load_from_theme('toolbars.xrc')
        self.SetToolBar(res.LoadToolBar(self, 'browser_toolbar'))
        index = common.config.getint('cornice', 'default_view')
        if index == 0:
            self.GetToolBar().ToggleTool(wx.xrc.XRCID('report_view'), True)
            self.GetMenuBar().Check(wx.xrc.XRCID('report_view'), True)
        else:
            self.GetToolBar().ToggleTool(wx.xrc.XRCID('thumbs_view'), True)
            self.GetMenuBar().Check(wx.xrc.XRCID('thumbs_view'), True)

        self.__do_layout()
        self.__set_properties()

        if common.config.getboolean('cornice', 'show_hidden'):
            self.GetMenuBar().Check(wx.xrc.XRCID('show_hidden'), True)
            self.dir_ctrl.ShowHidden(True)

        self.dir_ctrl.SetPath(path)
        #--- hack to fix bug of dir_ctrl ---
        tree = self.dir_ctrl.GetTreeCtrl()
        tree.EnsureVisible(tree.GetSelection())
        #-----------------------------------
        if common.config.getint('cornice', 'default_view') == 1: 
            # do this later, otherwise if started in thumbs view, the layout
            # is messed up...
            wx.CallAfter(self.picture_list.set_path, path)
        else:
            self.picture_list.set_path(path)

        # dir selection... and thumbs/report view
        TIMER_ID = wx.NewId()
        self.which_case = 0 # 0 = dir_selection, 1 = details, 2 = thumbnails
        self.set_path_timer = wx.Timer(self, TIMER_ID)
        ###wx.EVT_TIMER(self, TIMER_ID, self.on_timer)
        wx.EvtHandler.Bind(self, wx.EVT_TIMER, self.on_timer, id=TIMER_ID)
        ###wx.EVT_TREE_SEL_CHANGED(self.dir_ctrl, -1, #self.dir_ctrl.GetTreeCtrl().GetId(),
        ###                        self.on_tree_sel_changed)
        wx.EvtHandler.Bind(self.dir_ctrl, wx.EVT_TREE_SEL_CHANGED, self.on_tree_sel_changed, id=-1)
        
        ###wx.EVT_IDLE(self, self.on_idle)
        wx.EvtHandler.Bind(self, wx.EVT_IDLE, self.on_idle)

        ###picture_list.EVT_PL_CHANGE_PATH(self.picture_list, -1,
                                        ###self.on_pl_change_path)
        wx.EvtHandler.Bind(self.picture_list, picture_list.EVT_PL_CHANGE_PATH, self.on_pl_change_path, id=-1)

        ID_FOCUS_PATH = wx.NewId()
        self.SetAcceleratorTable(wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('l'), ID_FOCUS_PATH)
            ]))
        # focus the dircompleter...
        #wx.EVT_MENU(self, ID_FOCUS_PATH, self.picture_list.focus_path)
        wx.EvtHandler.Bind(self, wx.EVT_MENU, self.picture_list.focus_path, id=ID_FOCUS_PATH)

        self.show_exif(False)

    def on_idle(self, event):
        self.picture_list.update_statusbar_info()
        self.viewer.update_statusbar_info()
        
    def bind_menubar_events(self):

        def show_hidden(event):
            if event.IsChecked():
                self.dir_ctrl.ShowHidden(True)
            else:
                self.dir_ctrl.ShowHidden(False)

        def show_keybindings(event):
            print('kb')
            msg = _("""\
 SPACE or PG_DOWN:     Show next image
 BACKSPACE or PG_UP:   Show previous image
 HOME:                 Show first image
 END:                  Show last image
 LEFT_ARROW:           Scroll image left
 RIGHT_ARROW:          Scroll image right
 UP_ARROW:             Scroll image up
 DOWN_ARROW:           Scroll image down
 F:                    Fit image
 + or ]:               Zoom in
 - or [:               Zoom out
 1:                    Restore original image size
 K:                    Remember zoom and rotation settings
 F5:                   Refresh image
 R:                    Rotate image 90 degrees clockwise
 L:                    Rotate image 90 degrees counterclockwise
 S:                    Start/Stop slideshow
 F11:                  Toggle fullscreen mode
 ESC:                  Close viewer frame
""")
            resources.ScrolledMessageDialog(None, msg,
                                            _("Cornice Viewer Key Bindings"),
                                            67, 21)

        def report_view(event):
            if not wx.IsBusy():
                wx.BeginBusyCursor()
            self.which_case = 1
            self.set_path_timer.Start(150, True)
        def thumbs_view(event):
            if not wx.IsBusy():
                wx.BeginBusyCursor()
            self.which_case = 2
            self.set_path_timer.Start(150, True)

        def up_dir(event):
            try:
                self.dir_ctrl.up_dir()
            except AttributeError:
                self.dir_ctrl.SetPath(
                    os.path.split(self.dir_ctrl.GetPath())[0])

        def do_sort(index, reverse):
            common.sort_index = index
            common.reverse_sort = reverse
            self.picture_list.sort_items(index, reverse)

        # view tree and / or bookmarks
        def view_tab(which_tab):
            self.notebook.SetSelection(which_tab)
            page = self.notebook.GetPage(which_tab)
            if hasattr(page, 'GetTreeCtrl'): page = page.GetTreeCtrl()
            page.SetFocus()

        evts = (('view', lambda e: self.picture_list.on_item_activated()),
                ('exit', lambda e: wx.CallAfter(self.Close)),
                ('delete', lambda e: self.picture_list.delete_selection()),
                ('refresh', lambda e: self.picture_list.set_path(self.picture_list.path, True)),
                ('add_bookmark', lambda e: self.bookmarks.add_bookmark()),
                ('edit_bookmarks', lambda e: self.bookmarks.edit_bookmarks()),
                ('about', lambda e: resources.AboutDialog()),
                ('show_hidden', show_hidden),
                ('preferences', lambda e: resources.PreferencesEditor(common.config, common.config_file)),
                ('viewer_keybindings', show_keybindings),
                ('report_view', report_view),
                ('thumbs_view', thumbs_view),
                ('up_dir', up_dir),
                ('sort_name', lambda e: do_sort(common.SORT_NAME, common.reverse_sort)),
                ('sort_date', lambda e: do_sort(common.SORT_DATE, common.reverse_sort)),
                ('sort_size',lambda e: do_sort(common.SORT_SIZE, common.reverse_sort)),
                ('sort_type',lambda e: do_sort(common.SORT_TYPE, common.reverse_sort)),
                ('sort_descend',lambda e: do_sort(common.sort_index, not common.reverse_sort)),
                ('view_tree', lambda e: view_tab(0)),
                ('view_bookmarks', lambda e: view_tab(1)),
                ('open_archive', lambda e: self.open_archive()),
                ('cut', lambda e: self.picture_list.clipboard_cut()),
                ('copy', lambda e: self.picture_list.clipboard_copy()),
                ('paste', lambda e: self.picture_list.clipboard_paste()),
                ('create_album', lambda e: self.albums.add_album()),
                ('add_to_album', lambda e: self.add_to_album()),
                ('edit_albums', lambda e: self.albums.edit_albums()))

        for idString, func in evts:
            #print('Binding', idString, func)
            wx.EvtHandler.Bind(self, wx.EVT_MENU, func, id=wx.xrc.XRCID(idString))

        # event to update the sort menu
        def update_sort_menu(event):
            menu_to_check = {
                common.SORT_NAME: wx.xrc.XRCID('sort_name'),
                common.SORT_DATE: wx.xrc.XRCID('sort_date'),
                common.SORT_SIZE: wx.xrc.XRCID('sort_size'),
                common.SORT_TYPE: wx.xrc.XRCID('sort_type'),
                }
            mb = self.GetMenuBar()
            mb.Check(menu_to_check[event.sort_index], True)
            mb.Check(wx.xrc.XRCID('sort_descend'), event.reverse_sort)
        common.EVT_SORT_CHANGED(self, update_sort_menu)
        update_sort_menu(common._SortChangedEvent())

        # image popup menu...        
        mb = self.GetMenuBar()
        edit_menu = mb.GetMenu(mb.FindMenu(_('&Edit')))
        def popup_menu(event):
            self.picture_list.popup_menu(edit_menu, event.GetPosition())
            event.Skip()
        #picture_list.EVT_PICTURE_RIGHT_CLICK(self, -1, popup_menu)
        wx.EvtHandler.Bind(self, picture_list.EVT_PICTURE_RIGHT_CLICK, popup_menu, id=-1)

    def add_to_album(self):
        pictures = self.picture_list.get_selected_filenames()
        albumid, name = self.albums.choose_album()
        if albumid == 0:
            albumid = collection.add_album(name)
        if albumid > 0:
            collection.add_to_album(pictures, albumid)
            self.albums.load_albums()

    def open_archive(self, path=[None]):
        if path[0] is None:
            path[0] = common.config.get('cornice', 'initial_path')
        fileselector = wx.FileSelector
        if common.config.getboolean('cornice', 'use_system_dialogs') and \
               os.name == 'posix':
            import kdefiledialog
            if kdefiledialog.test_kde():
                fileselector = kdefiledialog.kde_file_selector
        archive = fileselector(
            _('Select ZIP archive to open'), path[0],
            wildcard='ZIP files (*.zip)|*.zip;*.ZIP|All files|*',
            flags=wx.OPEN|wx.FILE_MUST_EXIST, parent=self)
        if archive:
            # remember the path for next time...
            path[0] = os.path.split(archive)[0]
            # then try to read the contents...
            archive += '#zip:'
            self.picture_list.set_path(archive)
            self.dir_ctrl.SetPath(archive)

    def view_image(self, img):
        """\
        img is the path to the file to view
        """
        self.viewer.view_image(img)
        self.viewer.show()

    def set_path(self, path, refresh=True):
        self.picture_list.set_path(path, refresh)

    def on_tree_sel_changed(self, event):
        if getattr(self.dir_ctrl, 'dont_trigger_change_dir', False):
            # ugly hack (see PictureList.set_path), to avoid path changes
            # when the user visits a hidden dir, but the tree isn't showing
            # them
            return
        if not wx.IsBusy():
            wx.BeginBusyCursor()
        self.which_case = 0
        if not self.set_path_timer.Start(100, True):
            pass # wx.Timer.Start seems to return always False...
            #print 'impossible to start the timer!'
            #self.on_timer()
        event.Skip()

    def on_timer(self, *args):
        if self.which_case == 0:
            tree = self.dir_ctrl.GetTreeCtrl()
            item = tree.GetSelection()
            #if item != tree.GetRootItem():
            path = self.dir_ctrl.GetPath()
            self.picture_list.set_path(path)
        elif self.which_case == 1:
            tb = self.GetToolBar()
            tb.ToggleTool(wx.xrc.XRCID('report_view'), True)
            tb.ToggleTool(wx.xrc.XRCID('thumbs_view'), False)
            self.GetMenuBar().Check(wx.xrc.XRCID('report_view'), True)
            self.picture_list.show_details()
        elif self.which_case == 2:
            tb = self.GetToolBar()
            tb.ToggleTool(wx.xrc.XRCID('report_view'), False)
            tb.ToggleTool(wx.xrc.XRCID('thumbs_view'), True)
            self.GetMenuBar().Check(wx.xrc.XRCID('thumbs_view'), True)
            self.picture_list.show_thumbs()
        if wx.IsBusy(): wx.EndBusyCursor()
        
    def __set_properties(self):
        self.SetTitle(_("Picture Browser - Cornice"))
        try: w, h = [int(i) for i in
                     common.config.get('cornice', 'main_size').split(',')]
        except: w, h = 800, 600
        self.SetSize((w, h))
##         self.window_2.SplitHorizontally(self.window_2_pane_1,
##                                         self.preview_panel, 260)
        try: sp2 = common.config.getint('cornice', 'main_split_y')
        except: sp2 = 260
        self.window_2.SplitHorizontally(self.window_2_pane_1,
                                        self.preview_notebook, sp2)
        try: sp1 = common.config.getint('cornice', 'main_split_x')
        except: sp1 = 350
        self.window_1.SplitVertically(self.window_1_pane_1,
                                      self.window_1_pane_2, sp1)
        self.notebook.AddPage(self.dir_ctrl, _('Tree'))
        self.notebook.AddPage(self.bookmarks, _('Bookmarks'))
        self.notebook.AddPage(self.albums, _('Albums'))
        self.statusbar.SetStatusWidths([150, 200, -1, 150])
##         if wx.Platform == '__WXMSW__':
##             icon = wx.Icon('icons/icon.ico', wx.BITMAP_TYPE_ICO)
##         else:
##             icon = wx.EmptyIcon()
##             bmp = wx.Bitmap("icons/icon.xpm", wx.BITMAP_TYPE_XPM)
##             icon.CopyFromBitmap(bmp)
        icon = common.get_theme_icon()
        self.SetIcon(icon)
        self.Layout()
        self.window_2.SetSashPosition(sp2)
        self.window_1.SetSashPosition(sp1)

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_4 = wx.BoxSizer(wx.VERTICAL)
        sizer_2.Add(self.window_2, 1, wx.EXPAND, 0)
        self.window_1_pane_1.SetAutoLayout(1)
        self.window_1_pane_1.SetSizer(sizer_2)
        if wx.VERSION[:2] < (2, 6):
            sizer_3.Add(wx.NotebookSizer(self.notebook), 1, wx.EXPAND)
        else:
            sizer_3.Add(self.notebook, 1, wx.EXPAND)
        self.window_2_pane_1.SetAutoLayout(1)
        self.window_2_pane_1.SetSizer(sizer_3)
        sizer_4.Add(self.picture_list, 1, wx.EXPAND)
        self.window_1_pane_2.SetAutoLayout(1)
        self.window_1_pane_2.SetSizer(sizer_4)
        sizer_2.Fit(self.window_1_pane_1)
        sizer_1.Add(self.window_1, 1, wx.EXPAND, 0)
        self.SetAutoLayout(1)
        self.SetSizer(sizer_1)
        self.Layout()
        if wx.Platform == '__WXMAC__':
            wx.CallAfter(self.notebook.SetSelection, 0)

    def on_pl_change_path(self, event):
        mb = self.GetMenuBar()
        if vfs.is_virtual(event.path):
            oper = {'cut': False, 'paste': False, 'delete': False}
        else:
            oper = {}
        for name in 'cut', 'copy', 'paste', 'delete':
            mb.Enable(wx.xrc.XRCID(name), oper.get(name, True))

    def show_exif(self, show):
        if wx.Platform == '__WXMAC__':# or wx.VERSION[:2] < (2, 5):
            # Reparent doesn't work on the Mac, so just hide the exif tab...
            if show:
                if not self.exif_info.IsShown():
                    self.exif_info.Show()
                    self.preview_notebook.AddPage(self.exif_info,
                                                  _("Exif data"))
            else:
                if self.exif_info.IsShown():
                    self.exif_info.Hide()
                    self.preview_notebook.RemovePage(1)
        else:
            if show:
                if self.preview_notebook.IsShown():
                    return
                self.preview_panel.Reparent(self.preview_notebook)
                self.preview_notebook.InsertPage(0, self.preview_panel,
                                                 _("Preview"), True)
                self.preview_notebook.Layout()
                self.preview_notebook.Show()
                other = self.preview_notebook
            else:
                if not self.preview_notebook.IsShown():
                    return
                if wx.Platform == '__WXMSW__' or wx.VERSION[:2] < (2, 5):
                    self.preview_notebook.RemovePage(0)
                self.preview_panel.Reparent(self.window_2)
                self.preview_notebook.Hide()
                other = self.preview_panel
            self.window_2.ReplaceWindow(self.window_2.GetWindow2(), other)
            self.window_2.Layout()

# end of class CorniceBrowser


class CorniceArtProvider(wx.ArtProvider):
    def CreateBitmap(self, artid, client, size):
        if wx.Platform == '__WXGTK__' and artid == wx.ART_FOLDER:
            return wx.Bitmap(os.path.join('icons', 'closed_folder.xpm'),
                             wx.BITMAP_TYPE_XPM)
        return wx.NullBitmap

# end of class CorniceArtProvider


class Cornice(wx.App):
    def __init__(self, path, slideshow, quickstart):
        self.path = path
        self.slideshow = slideshow
        self.quickstart = quickstart
        self.main_frame = None
        self.viewer = None
        self.viewer_frame = None
        self.trayicon = None
        wx.App.__init__(self, 0)
    
    def init_preferences(self):
        import configparser
        defaults = {
            'fit_image': '1',
            'fit_enlarge': '0',
            'show_hidden': '0',
            'viewer_size': '800, 600',
            'fullscreen': '0',
            'initial_path': os.getcwd(),
            'remember_last_path': '1',
            'column_sort_index': '1',
            'reverse_sort': '1',
            'interpolation': '1', # Image.NEAREST
            'default_view': wx.Platform != '__WXMAC__' and '0' or '1',
            'slideshow_fullscreen': '1',
            'slideshow_delay': '2', # seconds
            'slideshow_fit': '1',
            'thumbs_cache_size': '5120', # in Kb
            'remember_settings': '1',
            'slideshow_cycle': '0',
            'slideshow_random': '0',
            'theme': self._get_default_theme(),
            'thumbs_size': '80, 60',
            'show_tray_icon': '0',
            'use_system_dialogs': '1',
            # thumbs_style: 0 = simple, 1 = button, 2 = frame
            'thumbs_style': wx.Platform != '__WXMAC__' and '1' or '2',
            'details_bg_color': '1',
            }
        common.config = configparser.ConfigParser(defaults)
        common.config.read(common.config_file)
        if not common.config.has_section('cornice'):
            common.config.add_section('cornice')
        common.sort_index = common.config.getint('cornice',
                                                 'column_sort_index')
        common.reverse_sort = common.config.getboolean('cornice',
                                                       'reverse_sort')
        import picture_thumbs
        picture_thumbs.init_from_preferences()

    def _get_default_theme(self):
        if os.name != 'posix':
            return 'win'
        # check if we are running under kde...
        if os.system('dcop kdesktop > /dev/null 2>&1') == 0:
            return 'kde'
        # ...otherwise return the default theme
        return ''

    def OnInit(self):
        self.init_preferences()
        wx.InitAllImageHandlers()
        try:
            locale.setlocale(locale.LC_ALL, '')
        except locale.Errori as e:
            pass # this is not that bad...
        # now, gettext initialization
        localedir = os.path.join(os.path.dirname(sys.argv[0]), 'i18n')
        # need to keep a reference to wx.Locale, otherwise dialogs created
        # later by XRC don't get translated
        global _wxloc 
        wx.Locale.AddCatalogLookupPathPrefix(localedir)
        _wxloc = wx.Locale(wx.LANGUAGE_DEFAULT)
        if wx.Platform == '__WXMAC__':
            _wxloc.AddCatalog('cornice_mac')
        else:
            _wxloc.AddCatalog('cornice')
        # just use the wxPython gettext, this is necessary for XRC and it's
        # sufficient for the rest. And it's also slightly better on win
        # (apparently it doesn't require LANG or simila to be set)
        import builtins
        setattr(builtins, '_', wx.GetTranslation)

        #wx.ArtProvider_PushProvider(CorniceArtProvider())
        wx.ArtProvider.Push(CorniceArtProvider())

        if common.config.getboolean('cornice', 'show_tray_icon'):
            import tray
            self.trayicon = tray.show_tray_icon(self)

        self.SetExitOnFrameDelete(False)

        if not self.quickstart:
            common.exit_app = self.exit_app
            common.really_exit_app = self.exit_app
            self.create_frames()
        else:
            common.exit_app = self.hide_all
            common.really_exit_app = self.exit_app
            
##         if self.path is not None:
##             path = fileops.dirname(self.path)
##             if not fileops.isdir(path):
##                 path = common.config.get('cornice', 'initial_path')
##         else:
##             path = common.config.get('cornice', 'initial_path')
##         viewer_frame = viewer.CorniceViewerFrame(
##             None, _("Picture Viewer - Cornice"))
##         panel = viewer.CorniceViewer(viewer_frame)
##         frame = CorniceBrowser(panel, path)

##         self._droptarget = clipboard.PathDropTarget(self)
##         frame.SetDropTarget(self._droptarget)
##         viewer_frame.SetDropTarget(self._droptarget)

##         if not self.quickstart:
##             common.exit_app = self.exit_app
##             common.really_exit_app = self.exit_app
##         else:
##             common.exit_app = self.hide_all
##             common.really_exit_app = self.exit_app
##         wx.EVT_CLOSE(frame, common.exit_app)

##         self.SetTopWindow(frame)
        #frame.SetPosition((0, 0)) # temporary, should be customizable
        
        if self.slideshow:
            self.main_frame.set_path(self.path, False)###Changed path to self.path
            self.viewer_frame.Show()
            self.viewer.slideshow()
        elif self.path is not None and fileops.isfile(self.path):
            try:
                self.viewer.view_image(
                    self.path, common.get_image_info(self.path))
                self.viewer.SetFocus()
            except Exception as e:
                print(e)
                self.main_frame.Show()
        elif not self.quickstart:
            self.main_frame.Show()
            # hack to make the current dir always visible... we do this after
            # the frame has been shown, as otherwise it doesn't always work
            # (due to layout problems...)
            tree = self.main_frame.dir_ctrl.GetTreeCtrl()
            tree.EnsureVisible(tree.GetSelection())

        # now let's add the remote code...
##         self.main_frame = frame
##         self.viewer = panel
##         self.viewer_frame = viewer_frame
        
        import remote
        thread = remote.init_server(self)
        ###remote.EVT_REMOTE_COMMAND(self, self.on_remote_command)
        wx.EvtHandler.Bind(self, remote.EVT_REMOTE_COMMAND, self.on_remote_command)
        thread.start()

        ###clipboard.EVT_DROP_PATH(self, -1, self.on_drop_path)
        wx.EvtHandler.Bind(self, clipboard.EVT_DROP_PATH, self.on_drop_path, id=-1)

        return True

    def create_frames(self):
        if self.path is not None:
            path = self.path
            if not fileops.isdir(self.path):
                path = fileops.dirname(self.path)
            if not fileops.isdir(path):
                path = common.config.get('cornice', 'initial_path')
        else:
            path = common.config.get('cornice', 'initial_path')
        self.viewer_frame = viewer.CorniceViewerFrame(
            None, _("Picture Viewer - Cornice"))
        self.viewer = viewer.CorniceViewer(self.viewer_frame)
        self.main_frame = CorniceBrowser(self.viewer, path)

        self._droptarget = clipboard.PathDropTarget(self)
        self.main_frame.SetDropTarget(self._droptarget)
        self.viewer_frame.SetDropTarget(self._droptarget)
        wx.EvtHandler.Bind(self.main_frame, wx.EVT_CLOSE, common.exit_app)

        self.SetTopWindow(self.main_frame)

    def exit_app(self, event=None):
        #print 'EXIT APP!!!', self.main_frame
        common.exiting(True)
        if common.config.getboolean('cornice', 'remember_last_path'):
            common.config.set(
                'cornice', 'initial_path', self.main_frame.picture_list.path)
        if self.main_frame is not None:
            w, h = self.main_frame.GetSize()
            common.config.set(
                'cornice', 'main_size', '%s, %s' % (w, h))
            common.config.set(
                'cornice', 'main_split_x',
                str(self.main_frame.window_1.GetSashPosition()))
            common.config.set(
                'cornice', 'main_split_y',
                str(self.main_frame.window_2.GetSashPosition()))
        if self.viewer_frame is not None:
            w, h = self.viewer_frame.GetSize()
            common.config.set(
                'cornice', 'viewer_size', '%s, %s' % (w, h))
        try:
            out = open(common.config_file, 'w')
            common.config.write(out)
            out.close()
        except Exception as e:
            wx.LogError(_('Unable to save preferences (%s)') % e)
        if self.viewer_frame is not None:
            self.viewer_frame.Destroy()
        if self.main_frame is not None:
            self.main_frame.Destroy()
        if self.trayicon is not None:
            self.trayicon.Destroy()
        import remote
        remote.shutdown_server()
        wx.CallAfter(self.ExitMainLoop)

    def hide_all(self, event=None):
        self.viewer_frame.Close()
        self.main_frame.Hide()

    def on_drop_path(self, event):
        def cmd_show(path):
            try:
                self.viewer.view_image(path, common.get_image_info(path))
                self.viewer_frame.Hide()
                self.viewer_frame.Show()
                self.viewer_frame.Raise()
                self.viewer.SetFocus()
            except Exception as e:
                import traceback
                traceback.print_exc()
        def cmd_browse(path):
            try:
                self.main_frame.Hide()
                self.main_frame.Show()
                self.main_frame.Raise()
                self.main_frame.set_path(path)
            except Exception as e:
                import traceback
                traceback.print_exc()

        if fileops.isfile(event.path):
            cmd_show(event.path)
        elif fileops.isdir(event.path):
            cmd_browse(event.path)
        

    def on_remote_command(self, event):
        if self.main_frame is None:
            self.create_frames()
            
        def cmd_ping(*args): pass
        def cmd_raise(*args):
            self.main_frame.Hide()
            self.main_frame.Show()
            self.main_frame.Raise()
        def cmd_show(*args):
            try:
                self.viewer.view_image(args[0], common.get_image_info(args[0]))
                self.viewer_frame.Hide()
                self.viewer_frame.Show()
                self.viewer_frame.Raise()
                self.viewer.SetFocus()
            except Exception as e:
                import traceback
                traceback.print_exc()
        def cmd_browse(*args):
            try:
                self.main_frame.Hide()
                self.main_frame.Show()
                self.main_frame.Raise()
                self.main_frame.set_path(args[0])
            except Exception as e:
                import traceback
                traceback.print_exc()

        commands = {
            'PING': cmd_ping,
            'RAISE': cmd_raise,
            'SHOW': cmd_show,
            'BROWSE': cmd_browse,
            }
        cmd = commands.get(event.cmd)
        if cmd is not None:
            cmd(*event.args)

# end of class Cornice

def setRandom(path):
    import random
    randomList = []
    for root, dirs, files in os.walk(path):
        randomList.append(root)
    return random.sample(randomList, 1)[0]
    
def main(path, slideshow, quickstart, random):
    os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])))
    
    if random:
        path = setRandom(path)

    app = Cornice(path, slideshow, quickstart)

    if wx.Platform != '__WXGTK__':
        viewer._blank_cursor = wx.StockCursor(wx.CURSOR_BLANK)
    else:
        try:
            viewer._blank_cursor = wx.Cursor(wx.Image(1, 1))
        except AttributeError:
            # wx.CursorFromImage was introduced after 2.4.0.2
            # (probably 2.4.0.4), so it may not be available
            viewer._blank_cursor = wx.NullCursor

    app.MainLoop()
