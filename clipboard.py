# clipboard.py: Cut/Copy/Paste and DnD support 
# arch-tag: Cut/Copy/Paste and DnD support 
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

import wx

_cornice_marker_format = wx.DataFormat('cornice_marker')

# True if our last operation was a cut
_cornice_cutting = False

# True if the dragging operation comes from within Cornice
_self_dragging = False


def copy(files):
    """\
    Returns True on success, False otherwise.
    """
    global _cornice_cutting
    _cornice_cutting = False
    if wx.TheClipboard.Open():
        try:
            cdo = wx.DataObjectComposite()
            fdo = wx.FileDataObject()
            for f in files:
                fdo.AddFile(f)
            cdo.Add(fdo)
            cdo.Add(wx.DataObjectSimple(_cornice_marker_format))
            if not wx.TheClipboard.SetData(cdo):
                print(_("Data can't be copied to the clipboard."))
                return False
            return True
        finally:
            wx.TheClipboard.Close()
    else:
        print(_("The clipboard can't be opened."))
        return False


def cut(files):
    """\
    Returns True on success, False otherwise.
    """
    global _cornice_cutting
    if copy(files):
        _cornice_cutting = True
        return True
    return False


def paste():
    """\
    Returns a tuple (list_of_files, cutting), even in case of failure (when
    the returned value is ([], False)
    """
    global _cornice_cutting
    cutting = _cornice_cutting
    _cornice_cutting = False
    if wx.TheClipboard.Open():
        try:
            cutting = cutting and \
                      wx.TheClipboard.IsSupported(_cornice_marker_format)
            fdo = wx.FileDataObject()
            if wx.TheClipboard.IsSupported(fdo.GetFormat()):
                if not wx.TheClipboard.GetData(fdo):
                    print(_("Data can't be copied from clipboard."))
                    return ([], False)
                return (fdo.GetFilenames(), cutting)
            else:
                print(_("Data can't be copied from the clipboard."))
                return ([], False)
        finally:
            wx.TheClipboard.Close()
    else:
        print(_("The clipboard can't be opened."))
        return ([], False)


_EVT_DROP_PATH = wx.NewEventType()

class DropPathEvent(wx.PyCommandEvent):
    def __init__(self, path):
        wx.PyCommandEvent.__init__(self)
        self.SetEventType(_EVT_DROP_PATH)
        self.path = path

# end of class DropPathEvent
        
if wx.VERSION[:2] >= (2, 5):
    EVT_DROP_PATH = wx.PyEventBinder(_EVT_DROP_PATH, 1)
else:
    def EVT_DROP_PATH(win, id, function):
        win.Connect(id, -1, _EVT_DROP_PATH, function)


class PathDropTarget(wx.FileDropTarget):
    def __init__(self, parent):
        wx.FileDropTarget.__init__(self)
        self.parent = parent

    def OnDragOver(self, x, y, default):
        if _self_dragging:
            return wx.DragNone
        return default

    OnEnter = OnDragOver
    OnLeave = OnDragOver

    def OnDropFiles(self, x, y, filenames):
        global _self_dragging
        if _self_dragging:
            _self_dragging = False
            return False
        if len(filenames) > 1:
            wx.MessageBox(_("Please only drop one file at a time"),
                         "Cornice", wx.ICON_ERROR)
            return False
        elif filenames:
            wx.PostEvent(self.parent, DropPathEvent(filenames[0]))
            return True
        else:
            return False

# end of class PathDropTarget
