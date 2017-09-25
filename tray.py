# tray.py: system tray support
# arch-tag: system tray support
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

import wx
import common

__all__ = ['show_tray_icon']

_supported = getattr(wx, 'TaskBarIcon', None) is not None

if _supported:
    def show_tray_icon(app):
        tbicon = wx.TaskBarIcon()
        tbicon.SetIcon(common.get_theme_icon())

        ID_MINIMIZE = wx.NewId()
        ID_HIDE = wx.NewId()
        ID_QUIT = wx.NewId()
        
        def on_right_down(event):
            menu = wx.Menu('Cornice')
            menu.Append(ID_HIDE, _('Show/Hide'))
            menu.Append(ID_MINIMIZE, _('Minimize/Restore'))
            menu.AppendSeparator()
            menu.Append(ID_QUIT, _('Quit'))
            tbicon.PopupMenu(menu)
            menu.Destroy()

        def on_minimize(event):
            if app.main_frame is None:
                app.create_frames()
                
            if app.main_frame.IsShown():
                app.main_frame.Iconize(not app.main_frame.IsIconized())
            if app.viewer_frame.IsShown():
                app.viewer_frame.Iconize(not app.viewer_frame.IsIconized())

        def on_hide(event):
            if app.main_frame is None:
                app.create_frames()

            if app.main_frame.IsShown():
                app.main_frame.Hide()
                app.viewer_frame.Hide()
            elif app.viewer_frame.IsShown():
                app.viewer_frame.Hide()
            else:
                app.main_frame.Show()

        def on_quit(event):
            common.really_exit_app()
            
        wx.EVT_TASKBAR_LEFT_DOWN(tbicon, on_hide)
        wx.EVT_TASKBAR_RIGHT_DOWN(tbicon, on_right_down)
        wx.EVT_MENU(tbicon, ID_MINIMIZE, on_minimize)
        wx.EVT_MENU(tbicon, ID_HIDE, on_hide)
        wx.EVT_MENU(tbicon, ID_QUIT, on_quit)

        return tbicon
    
else:
    def show_tray_icon(app):
        class TbIcon:
            def Destroy(self):
                pass
        return TbIcon()

