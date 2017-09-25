# dircompleter.py: DirCompleter class, a combo box with autocompleting of
# directories and history
# arch-tag: DirCompleter class
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

import wx
import os#, dircache

_CHANGE_PATH_EVENT = wx.NewEventType()

class ChangePathEvent(wx.PyCommandEvent):
    def __init__(self, id, path):
        wx.PyCommandEvent.__init__(self)
        self.SetId(id)
        self.SetEventType(_CHANGE_PATH_EVENT)
        self.path = path

    def GetPath(self):
        return self.path

# end of class ChangePathEvent


def EVT_CHANGE_PATH(win, id, function):
    win.Connect(id, -1, _CHANGE_PATH_EVENT, function)


class DirCompleter(wx.ComboBox):
    def __init__(self, *args, **kwds):
        wx.ComboBox.__init__(self, *args, **kwds)
        #wx.EVT_CHAR(self, self.on_char)
        #wx.EVT_TEXT(self, -1, self.on_text)
        #wx.EVT_COMBOBOX(self, -1, self.on_combo)
        wx.EvtHandler.Bind(self, wx.EVT_CHAR, self.on_char)
        wx.EvtHandler.Bind(self, wx.EVT_TEXT, self.on_text, id=-1)
        wx.EvtHandler.Bind(self, wx.EVT_COMBOBOX, self.on_combo, id=-1)

        if wx.Platform == '__WXMAC__':
            wx.EVT_TEXT_ENTER(self, -1, self.on_text_enter)
        self.want_completion = False
        self.olddir = None
        self.completions = None
        self._skip_on_combo = False
        self._dont_reset_insertion_point = False
        self._history = {}

    def SetValue(self, value):
        self.want_completion = False
        wx.ComboBox.SetValue(self, value)
        def go():
            self.SetFocus()
            self.SetInsertionPointEnd()
            ###self.SetMark(self.GetInsertionPoint(), -1)
            self.SetTextSelection(self.GetInsertionPoint(), -1)
        if not self._dont_reset_insertion_point:
            wx.CallAfter(go)

    def on_text_enter(self, event):
        evt = ChangePathEvent(self.GetId(), self.GetValue().strip())
        wx.PostEvent(self, evt)

    def on_char(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_TAB and event.ControlDown():
            self.complete_path()
        elif key == wx.WXK_RETURN:
            # post the appropriate event
            #evt = wx.CommandEvent(_CHANGE_PATH_EVENT, self.GetId())
            evt = ChangePathEvent(self.GetId(), self.GetValue().strip())
            wx.PostEvent(self, evt)
            return
        elif key not in (wx.WXK_DELETE, wx.WXK_BACK):
            self.want_completion = True
        self._skip_on_combo = wx.Platform == '__WXGTK__'
        event.Skip()

    def on_combo(self, event):
        if not self._skip_on_combo:
            val = event.GetString()
            wx.PostEvent(self, ChangePathEvent(self.GetId(), val))
        else:
            self._skip_on_combo = wx.Platform == '__WXGTK__'

    def on_text(self, event):
        if wx.Platform == '__WXMAC__':
            self.want_completion = len(self.GetValue()) > len(event.GetString())
        if self.want_completion:
            self.want_completion = False
            if wx.Platform == '__WXMAC__':
                ip = len(os.path.commonprefix([self.GetValue(),
                                               event.GetString()]))
            else:
                ip = None
            wx.CallAfter(self.complete_path, ip)

    def complete_path(self, ip=None):
        if ip is None:
            ip = self.GetInsertionPoint()
        text = os.path.expanduser(self.GetValue())
        if os.path.isdir(text):
            if text[-1] not in (os.sep, '.'):
                #ip = self.GetInsertionPoint()
                self._dont_reset_insertion_point = True
                self.SetValue(text + os.sep)
                self._dont_reset_insertion_point = False
                self.SetInsertionPoint(ip-1)
                self.SetMark(ip, len(text)+1) #ip+1)
            return
        curdir, curname = os.path.split(text)
        if not curdir or not os.path.isdir(curdir) or not curname:
            return
        if curdir != self.olddir:
            self.olddir = curdir
            self.completions = [ d for d in os.listdir(curdir) if
                                 os.path.isdir(os.path.join(curdir, d)) ]
            self.completions.sort()
        completion = None
        for name in self.completions:
            #if name.startswith(curname):
            if startswith(name, curname):
                completion = name + os.sep
                break
        if completion is not None:
            #ip = self.GetInsertionPoint()
            self._dont_reset_insertion_point = True
            self.SetValue(os.path.join(curdir, completion))
            self._dont_reset_insertion_point = False
            self.SetInsertionPoint(ip)
            self.SetMark(ip, self.GetLastPosition()+1)

    def add_to_history(self, path):
        path = os.path.normcase(os.path.normpath(path))
        if path not in self._history:
            self._history[path] = 1
            self._skip_on_combo = wx.Platform == '__WXGTK__'
            self.Append(path)

# end of class DirCompleter


if wx.Platform != '__WXGTK__':
    def startswith(s, val):
        return s.lower().startswith(val.lower())
else:
    def startswith(s, val):
        return s.startswith(val)

