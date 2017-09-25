#!/usr/bin/env python 

from distutils.core import setup, Extension

setup(name='dirctrl', version='0.1',
      description='Windows dir control helper',
      ext_modules=[Extension('_dirctrlhelper', ['_dirctrlhelper.cpp'],
                             extra_compile_args=['-g', '-fvtable-thunks'],
                             extra_link_args=['-g'],
                             libraries=['shell32', 'shfolder', 'shlwapi'],
                             )]
      )
