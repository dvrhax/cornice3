import EXIF
import wx, wx.lib.mixins.listctrl as wxlist
import wx.dataview as gizmos
import common
from PIL import Image

  
class ExifInfo(gizmos.TreeListCtrl):#, wxlist.ListCtrlAutoWidthMixin):
    def __init__(self, parent):
##         wx.ListCtrl.__init__(self, parent, -1,
        gizmos.TreeListCtrl.__init__(self, parent, -1,
                             style=wx.TR_DEFAULT_STYLE |
                             wx.TR_FULL_ROW_HIGHLIGHT | wx.TR_HIDE_ROOT)
##                              style=wx.LC_SINGLE_SEL|
##                              wx.LC_REPORT|wx.SUNKEN_BORDER)
##         wxlist.ListCtrlAutoWidthMixin.__init__(self)
##         self.InsertColumn(0, _("Name"))
##         self.InsertColumn(1, _("Value"))
        self.AppendColumn(_("Name"))
        self.AppendColumn(_("Value"))
        #self.SetMainColumn(0)
        self.SetSortColumn(0)

        #self.root = self.AddRoot("root")  ##Needs Fix

        # this seems to be necessary to make the mouse wheel work correctly...
        #wx.EVT_MOUSEWHEEL(self, lambda e: e.Skip())
        wx.EvtHandler.Bind(self, wx.EVT_MOUSEWHEEL, lambda e: e.Skip())

    def findexif(self, image):
        try:
            f = open(image, 'rb')
        except Exception as e:
            print(e)
            return False
        tags = EXIF.process_file(f)
        clef = list(tags.keys())
        if not clef:
            return False
        clef.sort()
        text = ""
        self.Freeze()
        #self.DeleteAllItems()
        self.DeleteChildren(self.root)
        item = -1
        i = 1
        old = "root"
        parent = self.root
        for name in clef:
            if name in ('JPEGThumbnail', 'TIFFThumbnail'):
                continue
            path = tags[name]
            n1, n2 = name.split(" ", 1)
            if n1 != old:
                old = n1
                parent = self.AppendItem(self.root, common.wxstr(n1))
##             item = self.InsertStringItem(item+1, common.wxstr(name))
##             self.SetStringItem(item, 1, common.wxstr(path))
            item = self.AppendItem(parent, common.wxstr(n2))
            self.SetItemText(item, common.wxstr(path), 1)
            i += 1
        #self.SetColumnWidth(0, -1)
##         self._doResize()
        self.Thaw()
        c, cookie = self.GetFirstChild(self.root)
        self.Expand(c)
        while True:
            c, cookie = self.GetNextChild(self.root, cookie)
            if not c.IsOk():
                break
            self.Expand(c)
        self.adjust_size()
        return True

    def adjust_size(self):
        w, h = self.GetClientSize()
        w -= wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
        self.SetColumnWidth(0, int(w / 2))
        self.SetColumnWidth(1, int(w / 2))

# end of class ExifInfo


_orientations = {
    2: Image.FLIP_LEFT_RIGHT,
    3: Image.ROTATE_180,
    4: Image.FLIP_TOP_BOTTOM,
    6: Image.ROTATE_90,
    8: Image.ROTATE_270,
    }

def exif_orient(image_file, pil_image):
    """\
    Rotates pil_image according to the exif Orientation tag (if present)
    """
    image_file.seek(0)
    tags = EXIF.process_file(image_file)
    keys = list(tags.keys())
    if not keys:
        return pil_image
    try:
        orientation = int(str(tags['Image Orientation']))
        if orientation in _orientations:
            pil_image = pil_image.transpose(_orientations[orientation])
        elif orientation != 1:
            print('Unsupported EXIF Image Orientation:', orientation)
    except Exception as e:
        import traceback; traceback.print_exc()
    return pil_image
