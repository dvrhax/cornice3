# dirctrl: extended version of the GenericDirCtrl
# arch-tag: extended version of the GenericDirCtrl
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

import wx

try:
    if wx.Platform == '__WXMSW__':
        from .dirctrl_win import *
    elif wx.Platform == '__WXMAC__':
        from .dirctrl_mac import *
    else:
        from .dirctrl_gen import *
except ImportError:
    from .dirctrl_gen import *
