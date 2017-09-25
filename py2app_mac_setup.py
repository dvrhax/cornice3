from distutils.core import setup
from itertools import imap, chain
import glob
import py2app
import os, sys
try:
    set
except NameError:
    from sets import Set as set

CORNICE_DIR = '.' #Cornice'

def get_data_files(paths):
    lst = []
    for f in paths:
        lst.extend(glob.glob(os.path.join(CORNICE_DIR, f)))
    return [('', lst)]


setup(
    app = ['cornice.py'],
    data_files = get_data_files([
        '*.txt', 'i18n', '*.xrc', 'icons',
    ]),
    options = dict(py2app=dict(
        argv_emulation=True,
        compressed=True,
    )),
)
