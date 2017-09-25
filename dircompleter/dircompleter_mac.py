import wx
import os

from dircompleter import ChangePathEvent, EVT_CHANGE_PATH


class DirCompleter(wx.Choice):
    def __init__(self, parent, id, val):
        wx.Choice.__init__(self, parent, id)
        self._history = {}
        wx.EVT_CHOICE(self, -1, self.on_choice)

    def add_to_history(self, path):
        path = os.path.normcase(os.path.normpath(path))
        if path not in self._history:
            self._history[path] = 1
            self.Append(path)

    def SetValue(self, path):
        self.add_to_history(path)
        self.SetStringSelection(os.path.normcase(os.path.normpath(path)))

    def __getattr__(self, name):
        return lambda *args, **kwds: None

    def on_choice(self, event):
        evt = ChangePathEvent(self.GetId(), self.GetStringSelection())
        wx.PostEvent(self, evt)

# end of class DirCompleter
