"""
This module will do surgery on the wx.DC class in wxPython 2.5.1.5 to
make it act like the wx.DC class in later versions will.  In a
nutshell, the old 2.4.x style of method names, where the 'normal' name
takes separate parameters for x, y, width and height will be restored,
and the new methods that take wx.Point and/or wx.Size (which can also
be converted from 2-element sequences) will be given new non-default
method names.  The new names are:

    * FloodFillPoint
    * GetPixelPoint
    * DrawLinePoint
    * CrossHairPoint
    * DrawArcPoint
    * DrawCheckMarkRect
    * DrawEllipticArcPointSize
    * DrawPointPoint
    * DrawRectanglePointSize
    * DrawRoundedRectanglePointSize
    * DrawCirclePoint
    * DrawEllipsePointSize
    * DrawIconPoint
    * DrawBitmapPoint
    * DrawTextPoint
    * DrawRotatedTextPoint
    * BlitPointSize

WARNING: If you import this module the the wx.DC class will be changed
         for the entire application, so if you use code from the
         wx.lib package or 3rd party modules that have already been
         converted to the doomed 2.5.1.5 implementaion of the DC Draw
         methods then that code will break.  This is an all-or-nothing
         fix, (just like the next version of wxPython will be,) so you
         *will* need to do something to resolve this situation if you
         run into it.  The best thing to do of course is to correct
         the library module to work with the corrected DC semantics and
         then send me a patch. 

--Robin
"""

import wx

_names = [
    ("FloodFillXY",             "FloodFill",            "FloodFillPoint"),
    ("GetPixelXY",              "GetPixel",             "GetPixelPoint"),
    ("DrawLineXY",              "DrawLine",             "DrawLinePoint"),
    ("CrossHairXY",             "CrossHair",            "CrossHairPoint"),
    ("DrawArcXY",               "DrawArc",              "DrawArcPoint"),
    ("DrawCheckMarkXY",         "DrawCheckMark",        "DrawCheckMarkRect"),
    ("DrawEllipticArcXY",       "DrawEllipticArc",      "DrawEllipticArcPointSize"),
    ("DrawPointXY",             "DrawPoint",            "DrawPointPoint"),
    ("DrawRectangleXY",         "DrawRectangle",        "DrawRectanglePointSize"),
    ("DrawRoundedRectangleXY",  "DrawRoundedRectangle", "DrawRoundedRectanglePointSize"),
    ("DrawCircleXY",            "DrawCircle",           "DrawCirclePoint"),
    ("DrawEllipseXY",           "DrawEllipse",          "DrawEllipsePointSize"),
    ("DrawIconXY",              "DrawIcon",             "DrawIconPoint"),
    ("DrawBitmapXY",            "DrawBitmap",           "DrawBitmapPoint"),
    ("DrawTextXY",              "DrawText",             "DrawTextPoint"),
    ("DrawRotatedTextXY",       "DrawRotatedText",      "DrawRotatedTextPoint"),
    ("BlitXY",                  "Blit",                 "BlitPointSize"),
    ("SetClippingRegionXY",     "SetClippingRegion",    "SetClippingRegionPointSize"),
]

if wx.VERSION[:3] == (2, 5, 1) and wx.VERSION[3] <= 5:
    cls = wx.DC
    for old, norm, new in _names:
        m_old  = getattr(cls, old)
        m_norm = getattr(cls, norm)
        setattr(cls, new, m_norm)
        setattr(cls, norm, m_old)
        delattr(cls, old)
