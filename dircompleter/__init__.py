# dircompleter: DirCompleter class, a combo box with autocompleting of
# directories and history
# arch-tag: DirCompleter class
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

import wx

if wx.Platform != '__WXMAC__':
    from dircompleter import *
else:
    from dircompleter_mac import *
