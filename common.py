# common.py: global variables
# arch-tag: global variables
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

import wx
import os, sys, locale
from PIL import Image
import threading

__version__ = '0.6.1'

if os.path.expanduser('~') != '~':
    bookmarks_file = os.path.expanduser('~/.cornice/bookmarks')
    config_file = os.path.expanduser('~/.cornice/config')
    confdir = os.path.expanduser('~/.cornice')
    if not os.path.exists(confdir):
        try: os.mkdir(confdir)
        except (IOError, OSError): pass # this is not fatal...
else:
    confdir = os.path.dirname(sys.argv[0])
    bookmarks_file = os.path.join(confdir, 'bookmarks')
    config_file = os.path.join(confdir, 'config')

config = None # ConfigParser instance used to load/store options

try:
    interpolations = [ Image.NEAREST, Image.BILINEAR,
                       Image.BICUBIC, Image.ANTIALIAS ]
except AttributeError:
    # probably PIL < 1.1.3
    interpolations = [ Image.NEAREST, Image.BILINEAR,
                       Image.BICUBIC, Image.BICUBIC ]

icons_and_colors = {
    'GIF': ('file_gif.xpm', (208, 232, 208)),
    'ICO': ('file_ico.xpm', (249, 240, 208)),
    'JPEG': ('file_jpg.xpm', (224, 232, 192)),
    'PCX': ('file_pcx.xpm', (216, 231, 216)),
    'PNG': ('file_png.xpm', (224, 216, 208)),
    'PNM': ('file_pnm.xpm', (218, 237, 192)),
    'PSD': ('file_psd.xpm', (255, 255, 223)),
    'TIF': ('file_tif.xpm', (200, 200, 213)),
    'XBM': ('file_xbm.xpm', (224, 224, 224)),
    'XCF': ('file_xcf.xpm', (191, 239, 233)),
    'XPM': ('file_xpm.xpm', (222, 217, 234)),
    'BMP': ('file_bmp.xpm', (229, 213, 213)),
    }
default_icon_and_color = ('file_image.xpm', (240, 240, 240))
unknown_icon_and_color = ('file_unknown.xpm', (255, 255, 255))

# sort indexes
SORT_NAME = 0
SORT_DATE = 1
SORT_SIZE = 2
SORT_TYPE = 3

sort_index = 0
reverse_sort = False


def format_size_str(number):
    sf = ['bytes', 'KB', 'MB', 'GB']
    i = 0
    while number > 1000 and i < 4:
        number = number / 1024.0
        i += 1
    return '%s %s' % (locale.format('%.1f', number), sf[i])


has_alpha = wx.VERSION[:3] >= (2, 5, 2) and 'gtk1' not in wx.PlatformInfo


if wx.Platform == '__WXGTK__':
    _mask_table = [0]*128 + [255]*128
else:
    _mask_table = [255]*128 + [0]*128

def get_mask(pil_image):
    """\
    If the image has some transparency, returns a wx.Mask object used to mask
    the transparent pixels, otherwise returns None
    The function should always be called with only one argument
    """
    if pil_image.mode == 'RGBA' and not has_alpha:
        alpha = pil_image.split()[3]
        mask = wx.EmptyImage(*alpha.size)
        #mask.SetData(alpha.convert('1').convert('RGB').tostring())
        mask.SetData(alpha.point(_mask_table, '1').convert('RGB').tostring())
        return wx.Mask(wx.BitmapFromImage(mask, 1))
    elif pil_image.mode == 'P':
        # let's try to get the transparency value...
        transparency = pil_image.info.get('transparency')
        if transparency:
##             mode, data = pil_image.palette.getdata()
##             if 0: #mode[:3] == 'RGB':
##                 if mode == 'RGBA': n = 4
##                 else: n = 3
##                 rgb = data[transparency*n : transparency*n + n]
##                 mask = wx.EmptyImage(*pil_image.size)
##                 mask.SetData(pil_image.convert('RGB').tostring())
##                 color = wx.Colour(*[ord(c) for c in rgb[:3]])
##                 if wx.VERSION[:3] >= (2, 5, 2):
##                     return wx.Mask(mask.ConvertToBitmap(), color)
##                 else:
##                     return wx.MaskColour(mask.ConvertToBitmap(), color)
##             else:

            if wx.Platform != '__WXGTK__': c1, c2 = 255, 0
            else: c1, c2 = 0, 255
            palette = [c1] * 768 #[255] * 768
            palette[transparency*3 : transparency*3 + 3] = [c2, c2, c2]#[0, 0, 0]
            pil_image = pil_image.copy()
            pil_image.putpalette(palette)
            mask = wx.EmptyImage(*pil_image.size)
            mask.SetData(pil_image.convert('1').convert('RGB').tostring())
            return wx.Mask(wx.BitmapFromImage(mask, 1))
    return None


# custom event to update the menubar when the sorting of the PictureList
# changes
_SORT_CHANGED_EVENT = wx.NewEventType()

class _SortChangedEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(_SORT_CHANGED_EVENT)
        self.sort_index = sort_index
        self.reverse_sort = reverse_sort

# end of class _SortChangedEvent

_win_to_post = None

def EVT_SORT_CHANGED(win, func):
    global _win_to_post; _win_to_post = win
    win.Connect(-1, -1, _SORT_CHANGED_EVENT, func)

def send_sort_changed_event():
    wx.PostEvent(_win_to_post, _SortChangedEvent())


_exiting_lock = threading.RLock()
_is_exiting = False

def exiting(val=None):
    global _is_exiting
    _exiting_lock.acquire()
    if val is not None: _is_exiting = val
    retval = _is_exiting
    _exiting_lock.release()
    return retval

exit_app = None # reference to a function called to exit the app nicely
really_exit_app = None


_theme_dir = None

def load_from_theme(resource):
    global _theme_dir
    if _theme_dir is None:
        _theme_dir = config.get('cornice', 'theme', '')
    d = os.path.join(confdir, _theme_dir)
    if not os.path.isdir(d):
        d = os.path.join(os.getcwd(), 'icons', _theme_dir)
    if not os.path.isdir(d) or \
           not os.path.isfile(os.path.join(d, 'toolbars.xrc')):
        d = os.path.join(os.getcwd(), 'icons')
    old = os.getcwd()
    #resource = os.path.abspath(resource)
    os.chdir(d)
    res = wx.xrc.XmlResource.Get()
    res.Load(resource)
    os.chdir(old)


def get_theme_icon():
    global _theme_dir
    if _theme_dir is None:
        _theme_dir = config.get('cornice', 'theme')#, '')
    if wx.Platform == '__WXMSW__':
        name = 'icon.ico'
    else:
        name = 'icon.png'
    d = os.path.join(confdir, _theme_dir)
    if not os.path.isdir(d):
        d = os.path.join(os.getcwd(), 'icons', _theme_dir)
    if not os.path.isdir(d) or \
           not os.path.isfile(os.path.join(d, name)):
        d = os.path.join(os.getcwd(), 'icons')
    if wx.Platform == '__WXMSW__':
        icon = wx.Icon(os.path.join(d, name), wx.BITMAP_TYPE_ICO)
    else:
        #icon = wx.EmptyIcon()
        icon = wx.Icon()
        bmp = wx.Bitmap(os.path.join(d, name), wx.BITMAP_TYPE_PNG)
        icon.CopyFromBitmap(bmp)
    return icon


def get_bitmap_for_theme(imagepath):
    global _theme_dir
    if _theme_dir is None:
        _theme_dir = config.get('cornice', 'theme', '')
        
    name, ext = os.path.splitext(imagepath)
    if ext: extensions = [ext]
    else: extensions = ['.png', '.xpm']
    paths = [os.path.join(os.getcwd(), 'icons', _theme_dir),
             os.path.join(os.getcwd(), 'icons')]

    log_null = wx.LogNull()
    for path in paths:
        for ext in extensions:
            imagepath = os.path.join(path, name + ext)
            try:
                bmp = wx.Bitmap(imagepath, wx.BITMAP_TYPE_ANY)
                if bmp.IsOk():
                    return bmp
            except:
                pass
    return None


if wx.Platform != '__WXMSW__' or wx.VERSION[:2] >= (2, 5):
    def delete_dc(dc):
        pass
else:
    def delete_dc(dc):
        dc.Destroy()


def get_image_info(path):
    import fileops, time
    
    pi = fileops.get_path_info(path)
    im = Image.open(fileops.open(path))
    w, h = im.size
    if im.mode == '1': sdepth = '1'
    elif im.mode == 'P': sdepth = '256'
    else: sdepth = '16M'
    info = [
        fileops.basename(path),
        time.strftime('%Y/%m/%d %H:%M',
                      time.localtime(pi.mtime)),
        pi.size,
        '%sx%sx%s %s' % (w, h, sdepth, im.format)
        ]
    return info


def create_thumbnail(pil_image, thumb_size):
    """\
    Returns a bitmap with the thumbnail
    """
    pil_image.thumbnail(thumb_size, Image.NEAREST)
    mask = get_mask(pil_image)
    img = wx.EmptyImage(*pil_image.size)
    if has_alpha and pil_image.mode == 'RGBA':
        alpha = pil_image.split()[3].tostring()
        img.SetData(pil_image.convert('RGB').tostring())
        img.SetAlphaData(alpha)
    elif pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')    
        img.SetData(pil_image.tostring())
    else:
        img.SetData(pil_image.tostring())        
    bmp = wx.BitmapFromImage(img)
    if mask is not None:
        bmp.SetMask(mask)
    return bmp


import locale
def wxstr(s):
    if not isinstance(s, basestring):
        return str(s)
    return s.decode(locale.getpreferredencoding(), 'ignore')

