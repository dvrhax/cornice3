import os
from PIL import Image
import fileops

class Picture:
    def __init__(self, path, info):
        f = fileops.open(path)
        self.pil_image = Image.open(f)
        self.path = path
        self.format = self.pil_image.format
        self.mode = self.pil_image.mode
        if self.mode == '1':
            self.depth = 1
        elif self.mode == 'P':
            self.depth = 256
        else:
            self.depth = 16000000
        self.filesize = info.size
        self.size = self.pil_image.size
        self.mtime = info.mtime
        self.name = os.path.basename(path)
        # other attributes here...

    def get_format_string(self):
        w, h = self.size
        if self.mode == '1':
            sdepth = '1'
        elif self.mode == 'P':
            sdepth = '256'
        else:
            sdepth = '16M'
        return '%sx%sx%s %s' % (w, h, sdepth, self.format)

    def load(self):
        self.pil_image.load()

    def convert_to_native(self, size):
        pass

# end of class Picture
