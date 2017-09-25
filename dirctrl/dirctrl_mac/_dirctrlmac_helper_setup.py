#!/usr/bin/env python 

from distutils.core import setup, Extension

setup(name='dirctrl', version='0.1',
      description='MacOSX dir control helper',
      ext_modules=[Extension('_dirctrlmac_helper', ['_dirctrlmac_helper.c'],
                             include_dirs=['/Developer/Headers/FlatCarbon'],
                             extra_compile_args=['-g'],
                             extra_link_args=['-g', '-framework', 'Carbon'],
                             )]
      )
