# virtualtree.py: DirCtrl for virtual file systems (zip archives,...)
# arch-tag: DirCtrl for virtual file systems (zip archives,...)
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

import wx
import os, sys, zipfile




class VirtualTree(wx.TreeCtrl):
    def __init__(self, parent, zipfilename):
        wx.TreeCtrl.__init__(self, parent, -1,
                             style=wx.TR_DEFAULT_STYLE|wx.SUNKEN_BORDER)
        imglist = wx.ImageList(16, 16)
        if wx.Platform == '__WXGTK__': bmpfile = 'zip.xpm'
        else: bmpfile = 'zip_win.xpm'
        bmp = wx.Bitmap(os.path.join('icons', bmpfile), wx.BITMAP_TYPE_XPM)
        imglist.Add(bmp)        
        imglist.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER, size=(16, 16)))
        # no open folder in ArtProvider??
        self.AssignImageList(imglist)
        self.populate(ZipVFS(zipfilename))

    def populate(self, vfs):
        def populate_rec(node):
            if node is None:
                node = self.AddRoot(vfs.root.name, 0)
                self.SetPyData(node, vfs.root)
            vfsnode = self.GetPyData(node)
            for vfschild in vfsnode.children:
                if vfschild.isdir:
                    child = self.AppendItem(
                        node, vfschild.name.split(os.sep)[-2], 1)
                    self.SetPyData(child, vfschild)
                    populate_rec(child)
        populate_rec(None)
        self.Expand(self.GetRootItem())

    def set_zipfile(self, zipfilename):
        self.DeleteAllItems()
        self.populate(ZipVFS(zipfilename))

    def GetPath(self):
        root = self.GetRootItem()
        prefix = self.GetPyData(root).name + '#zip:'
        sel = self.GetSelection()
        if sel.Ok():
            ret = self.GetPyData(sel).name
            if sel != root: return prefix + ret
            else: return prefix
        return ""

# end of class VirtualTree


def test():
    app = wx.PySimpleApp(0)
    f = wx.Frame(None, -1, "Test")
    tree = VirtualTree(f, sys.argv[1])
    def on_sel_changed(event):
        print 'selected:', tree.GetPath()
    wx.EVT_TREE_SEL_CHANGED(tree, tree.GetId(), on_sel_changed)
    f.SetSize((600, 400))
    app.SetTopWindow(f)
    f.Show()
    app.MainLoop()

if __name__ == '__main__' and len(sys.argv) > 1:
    test()

