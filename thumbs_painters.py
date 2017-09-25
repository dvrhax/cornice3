import wx
import common
from picture_thumbs import THUMBS_SIZE, INVALID


def _paint_simple_style(thumb, dc, image):
    bitmap = image
    w, h = THUMBS_SIZE
    dc.BeginDrawing()
    brush = wx.TheBrushList.FindOrCreateBrush(
        thumb.GetParent().GetBackgroundColour(), wx.TRANSPARENT)
    dc.SetBackground(brush)
    dc.SetBrush(brush)
    dc.Clear()
    # now, the image (if any)
    dc.SetPen(wx.TRANSPARENT_PEN)
    if bitmap is not INVALID:
        ww, hh = bitmap.GetWidth(), bitmap.GetHeight()
        dc.DrawBitmap(bitmap, (w+10 - ww)//2, (h+10 - hh)//2, True)
        dc.DrawRectangle((w+10 - ww)//2, (h+10 - hh)//2, ww, hh)
    # the label...
    tw, th = dc.GetTextExtent(thumb.img.name) #info[0])
    if thumb.focused:
        dc.SetTextForeground(wx.SystemSettings_GetColour(
            wx.SYS_COLOUR_HIGHLIGHTTEXT))
    if thumb.focused:
        brush = wx.TheBrushList.FindOrCreateBrush(
            wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT), wx.SOLID)
    else:
        brush = wx.TRANSPARENT_BRUSH
    dc.SetBrush(brush)
    dc.SetBackgroundMode(wx.TRANSPARENT)
    dc.SetFont(thumb.GetFont())
    if thumb.focused:
        pen_style = wx.SOLID
    else:
        pen_style = wx.TRANSPARENT
    dc.SetPen(wx.ThePenList.FindOrCreatePen(wx.BLACK, 0, pen_style))
    # draw the text centered...
    tw = dc.GetTextExtent(thumb.img.name) #info[0])[0]    
    if tw < w-1:
        x, y = (w-1 - tw)/2 + 4,  h+13
    else:
        x, y = 4, h+13
    if thumb.focused:
        dc.DrawRectangle(x-2, y-2, tw+4, th+4)
    dc.SetClippingRegion(4, h+15, w+3, th)
    dc.DrawText(thumb.img.name, x, y) #info[0], x, y)
    dc.DestroyClippingRegion()
    dc.EndDrawing()


def _paint_button_style(thumb, dc, image):
    bitmap = image
    w, h = THUMBS_SIZE
    dc.BeginDrawing()
    brush = wx.TheBrushList.FindOrCreateBrush(
        thumb.GetParent().GetBackgroundColour(), wx.TRANSPARENT) #SOLID)
    dc.SetBackground(brush)
    dc.SetBrush(brush)
    dc.Clear()
    # the thumbnail box
    dc.SetPen(wx.ThePenList.FindOrCreatePen(wx.BLACK, 0,
                                            wx.TRANSPARENT))
    dc.DrawRectangle(0, 0, w+10, h+10)
    # the borders...
    dc.SetPen(wx.ThePenList.FindOrCreatePen(
        wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DHILIGHT), 1,
        wx.SOLID))
    dc.DrawLine(0, 0, w+9, 0)
    dc.DrawLine(0, 0, 0, h+10)
    dc.SetPen(wx.BLACK_PEN)
    ww, hh = w+9, h+10
    dc.DrawLine(ww, 0, ww, hh+1)
    dc.DrawLine(0, hh, ww, hh)
    dc.SetPen(wx.ThePenList.FindOrCreatePen(
        wx.SystemSettings_GetColour(wx.SYS_COLOUR_BTNSHADOW), 1,
        wx.SOLID))
    ww, hh = w+8, h+9
    dc.DrawLine(2, hh, ww, hh)
    dc.DrawLine(ww, 2, ww, hh+1)
    # the label with the image name...
    try:
        bg = common.icons_and_colors[thumb.img.format][1] #image_type][1]
    except KeyError:
        bg = common.default_icon_and_color[1]
    if thumb.focused:
        brush = wx.TheBrushList.FindOrCreateBrush(
            wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT), wx.SOLID)
    else:
        brush = wx.TheBrushList.FindOrCreateBrush(wx.Colour(*bg), wx.SOLID)
    dc.SetBrush(brush)
    dc.SetBackgroundMode(wx.TRANSPARENT)
    dc.SetFont(thumb.GetFont())
    th = dc.GetTextExtent('Mp')[1]
    dc.SetPen(wx.ThePenList.FindOrCreatePen(wx.BLACK, 0, wx.TRANSPARENT))
    dc.DrawRectangle(0, h+12, w+10, h+th+16)
    # the label box
    dc.SetPen(wx.ThePenList.FindOrCreatePen(
        wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DHILIGHT), 1,
        wx.SOLID))
    ww, hh = w+9, h+th+15
    dc.DrawLine(ww, h+13, ww, hh+1)
    dc.DrawLine(1, hh, ww+1, hh)
    dc.SetPen(wx.ThePenList.FindOrCreatePen(
        wx.SystemSettings_GetColour(wx.SYS_COLOUR_BTNFACE), 1,
        wx.SOLID))
    ww, hh = w+8, h+th+14
    dc.DrawLine(2, hh, ww+1, hh)
    dc.DrawLine(ww, h+14, ww, hh)
    dc.SetPen(wx.ThePenList.FindOrCreatePen(
        wx.SystemSettings_GetColour(wx.SYS_COLOUR_BTNSHADOW), 1,
        wx.SOLID))
    ww, hh = w+10, h+th+16
    dc.DrawLine(0, h+12, ww, h+12)
    dc.DrawLine(0, h+12, 0, hh)
    dc.SetPen(wx.BLACK_PEN)
    ww, hh = w+9, h+th+15
    dc.DrawLine(1, h+13, ww, h+13)
    dc.DrawLine(1, h+13, 1, hh)
    # now, the image (if any)
    # moved before the drawing of the label because on windows there are
    # weird problems with SetClippingRegion: the Region seems not to be
    # destroyed correctly when it is near the right-end of the screen...
    # :-( 
    #if thumb.bitmap is not INVALID:
    if bitmap is not INVALID:
        ww, hh = bitmap.GetWidth(), bitmap.GetHeight()
        dc.DrawBitmap(bitmap, (w+10 - ww)//2, (h+10 - hh)//2, True) 
    # the label...
    dc.SetClippingRegion(4, h+15, w+3, th)
    if thumb.focused:
        dc.SetTextForeground(wx.SystemSettings_GetColour(
            wx.SYS_COLOUR_HIGHLIGHTTEXT))
    # draw the text centered...
    tw = dc.GetTextExtent(thumb.img.name)[0] #info[0])[0]
    if tw < w-1:
        #dc.DrawText(thumb.info[0], (w-1 - tw)/2 + 4, h+13)
        dc.DrawText(thumb.img.name, (w-1 - tw)/2 + 4, h+13)
    else:
        #dc.DrawText(thumb.info[0], 4, h+13)
        dc.DrawText(thumb.img.name, 4, h+13)
    dc.DestroyClippingRegion()
    dc.EndDrawing()


def _paint_frame_style(thumb, dc, image):
    bitmap = image
    w, h = THUMBS_SIZE
    dc.BeginDrawing()
    brush = wx.TheBrushList.FindOrCreateBrush(
        thumb.GetParent().GetBackgroundColour(), wx.TRANSPARENT) #SOLID)
    dc.SetBackground(brush)
    dc.SetBrush(brush)
    dc.Clear()
    # the label with the image name...
    try:
        bg = common.icons_and_colors[thumb.img.format][1] #image_type][1]
    except KeyError:
        bg = common.default_icon_and_color[1]
    if thumb.focused:
        brush = wx.TheBrushList.FindOrCreateBrush(
            wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT), wx.SOLID)
    else:
        brush = wx.TheBrushList.FindOrCreateBrush(wx.Colour(*bg), wx.SOLID)
    dc.SetBrush(brush)
    dc.SetBackgroundMode(wx.TRANSPARENT)
    dc.SetFont(thumb.GetFont())
    th = dc.GetTextExtent('Mp')[1]
    dc.SetPen(wx.ThePenList.FindOrCreatePen(wx.BLACK, 0, wx.TRANSPARENT))
    dc.DrawRectangle(0, h+12, w+10, h+th+16)
    # now, the image (if any)
    if bitmap is not INVALID:
        ww, hh = bitmap.GetWidth(), bitmap.GetHeight()
        dc.DrawBitmap(bitmap, (w+10 - ww)//2, (h+10 - hh)//2, True) 
    # the label...
    dc.SetClippingRegion(4, h+15, w+3, th)
    if thumb.focused:
        dc.SetTextForeground(wx.SystemSettings_GetColour(
            wx.SYS_COLOUR_HIGHLIGHTTEXT))
    # draw the text centered...
    tw = dc.GetTextExtent(thumb.img.name)[0] #info[0])[0]
    if tw < w-1:
        #dc.DrawText(thumb.info[0], (w-1 - tw)/2 + 4, h+13)
        dc.DrawText(thumb.img.name, (w-1 - tw)/2 + 4, h+13)
    else:
        #dc.DrawText(thumb.info[0], 4, h+13)
        dc.DrawText(thumb.img.name, 4, h+13)
    dc.DestroyClippingRegion()
    # the slide border for the mac...
    dc.SetBrush(wx.TRANSPARENT_BRUSH)
    if thumb.focused:
        color = wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT)
    else:
        color = wx.Colour(*bg)
    dc.SetPen(wx.ThePenList.FindOrCreatePen(color, 2, wx.SOLID))
    w, h = thumb.GetSize()
##     if wx.Platform == '__WXMSW__':
##         dc.DrawRectangle(0, 0, w, h)
##     else:
    dc.DrawRectangle(1, 1, w-1, h-1)
    dc.DrawPoint(0, 0)
    dc.EndDrawing()        

