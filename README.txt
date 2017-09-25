                    Cornice3: a cross platform image viewer
                                  Version 0.1
-------------------------------------------------------------------------------

This is a fork of Cornice written by agriggio to port it to Python3 and wxPython
Phoenix.  It's a very well done viewer that was well written and so I decided to
use it as a basis for a photo frame that I'm working on and thought that I would 
update his source first and republish it on GIT.  Enjoy it and feel free to submit 
patches or bugs.  The following is the orginal README from the work that agriggio
had done.  Lastly, this has only been tested on Linux running python 3.5 and the
latest wxPython on PyPi which at this time is "4.0.0b1 gtk3 (phoenix)"

-------------------------------------------------------------------------------

Cornice is a cross-platform image viewer written in Python
(http://www.python.org) + wxPython (http://wxpython.org) + PIL
(http://www.pythonware.com/products/pil) . It doesn't pretend to be complete,
fast, or even useful, but I like it and it is the viewer I use on both Linux
and Windows. It has been inspired by the famous Windows-only ACDSee.

Why did I write it? Well, because I like ACDSee, but it's not free and it
doesn't run on Linux, which is my main platform. There already exists an
ACDsee-like viewer, GTKSee (http://www.regix.com/info/gtksee.shtml), but it is
unmaintained and it lacks some features I wanted (bookmarks, a good keyboard
navigation and zooming). First I tried to add such features to it, but then I
decided to rewrite it from scratch, so that I could use it also on windows (and
also because I had some troubles, especially when trying to port GTKSee to the
gdk_pixbuf lib, and also because Python is more fun than C, and... ;-)


Features
--------
Here are a list of the main features of Cornice:
  o Fully cross-platform: it should run wherever wxPython does (tested on
    Linux -  GTK+ 1.2.10 and 2.2.0 -, Win Me and NT 4 SP
    something)
  o Detail and thumbnail view for images
  o Image preview
  o Automatic recognition of images, with a variety of formats supported
  o Bookmarks
  o Full-screen view
  o Zooming and rotation
  o Slideshow
  o Good keyboard navigation (still not perfect, but this is true for all the
    features ;-)    
  o Image loading from zip archives (still limited: currently it handles only
    "flat" archives, i.e. without a directory structure)


Requirements
------------
Python >= 2.2.1, wxPython >= 2.4.0.1 and PIL >= 1.2.2


Installation
------------
Unpack the tarball, then "python cornice.py" at your shell's prompt.


Bugs and Issues
--------------- 
A lot, probably ;-) If you like the program and find one of them, it would be
nice if you reported it.  


License
-------
GNU GPL (see license.txt)


Feedback
--------
Always very welcome :-) You can reach me at agriggio@users.sourceforge.net
