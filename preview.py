# preview.py: image preview panel
# arch-tag: image preview panel
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

import wx
from PIL import Image

import common, fileops

import exif_info


if wx.Platform == '__WXMSW__':
    _sb_offset = 0
    _sb_gap = 10
else:
    _sb_offset = 5
    _sb_gap = 5

if wx.Platform == '__WXMSW__':
    class _PreviewPanel(wx.Window):
        def __init__(self, *args, **kwds):
            wx.Window.__init__(self, *args, **kwds)
            self.image_file = None
            self.bitmap = None
            wx.EVT_SIZE(self, self.on_size)
            wx.EVT_PAINT(self, self.on_paint)

        def set_image(self, image_file, refresh=True):
            f = fileops.open(image_file)
            pil_image = Image.open(f)
            w, h = self.GetClientSize()
            pil_image.thumbnail((w-10, h-_sb_gap*2), Image.NEAREST)
            pil_image = exif_info.exif_orient(f, pil_image)
            img = wx.EmptyImage(*pil_image.size)
            mask = common.get_mask(pil_image)
            if common.has_alpha and pil_image.mode == 'RGBA':
                alpha = pil_image.split()[3].tobytes()
                img.SetData(pil_image.convert('RGB').tobytes())
                img.SetAlphaData(alpha)
            elif pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
                img.SetData(pil_image.tobytes())
            else:
                img.SetData(pil_image.tobytes())
            self.bitmap = wx.BitmapFromImage(img)
            if mask is not None:
                self.bitmap.SetMask(mask)
            self.image_file = image_file
            if refresh:
                self.Refresh()

        def on_size(self, event):
            w, h = event.GetSize()
            if self.image_file is not None:
                self.set_image(self.image_file, False)

        def on_paint(self, event):
            dc = wx.PaintDC(self)
            dc.BeginDrawing()
            if self.bitmap is not None:
                parent = self.GetParent()
                x, y = 0, 0
                w, h = self.GetClientSize()
                dc.DrawBitmap(self.bitmap, x + (w - self.bitmap.GetWidth()) / 2,
                              y + (h - self.bitmap.GetHeight()) / 2, True)
            dc.EndDrawing()
            event.Skip()

    # end of class _PreviewPanel


    class PreviewPanel(wx.Window):
        def __init__(self, *args, **kwds):
            wx.Window.__init__(self, *args, **kwds)
            self.panel = wx.Panel(self, -1)
            szr = wx.StaticBoxSizer(
                wx.StaticBox(self.panel, -1, "", (5, _sb_offset)), wx.VERTICAL)
            self.preview = _PreviewPanel(self.panel, -1)
            szr.Add(self.preview, 1, wx.EXPAND)
            self.panel.SetAutoLayout(True)
            self.panel.SetSizer(szr)
            wx.EVT_SIZE(self, self.on_size)

        def set_image(self, *args, **kwds):
            self.preview.set_image(*args, **kwds)

        def on_size(self, event):
            self.panel.SetSize(event.GetSize())
            event.Skip()

    # end of class PreviewPanel

else:
    class PreviewPanel(wx.Panel):
        def __init__(self, *args, **kwds):
            wx.Panel.__init__(self, *args, **kwds)
            self.image_file = None
            self.static_box = wx.StaticBox(self, -1, "", (5, _sb_offset))
            self.bitmap = None
            #wx.EVT_SIZE(self, self.on_size)
            wx.EvtHandler.Bind(self, wx.EVT_SIZE, self.on_size)
            #wx.EVT_PAINT(self, self.on_paint)
            wx.EvtHandler.Bind(self, wx.EVT_PAINT, self.on_paint)

        def set_image(self, image_file, refresh=True):
            f = fileops.open(image_file, 'rb')
            pil_image = Image.open(f)
            w, h = self.static_box.GetClientSize()
            pil_image = exif_info.exif_orient(f, pil_image)
            pil_image.thumbnail((w-10, h-_sb_gap*2), Image.NEAREST)
            img = wx.Image(*pil_image.size)
            mask = common.get_mask(pil_image)
            if common.has_alpha and pil_image.mode == 'RGBA':
                alpha = pil_image.split()[3].tobytes()
                img.SetData(pil_image.convert('RGB').tobytes())
                img.SetAlphaBuffer(alpha)###Changed Data to Buffer
            elif pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
                img.SetData(pil_image.tobytes())
            else:
                img.SetData(pil_image.tobytes())
            self.bitmap = wx.Bitmap(img)
            if mask is not None:
                self.bitmap.SetMask(mask)
            self.image_file = image_file
            if refresh:
                self.Refresh()

        def on_size(self, event):
            w, h = event.GetSize()
            self.static_box.SetSize((w-10, h-_sb_gap))
            if self.image_file is not None:
                self.set_image(self.image_file, False)

        def on_paint(self, event):
            dc = wx.PaintDC(self)
            #dc.BeginDrawing()
            if self.bitmap is not None:
                x, y = self.static_box.GetPosition()
                w, h = self.static_box.GetClientSize()
                dc.DrawBitmap(self.bitmap, x + (w - self.bitmap.GetWidth()) / 2,
                              y + (h - self.bitmap.GetHeight()) / 2, True)
            #dc.EndDrawing()

    # end of class PreviewPanel
    
