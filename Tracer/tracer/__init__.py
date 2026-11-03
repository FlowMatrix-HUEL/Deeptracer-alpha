# Copyright 2026 shuo'liu
# This program is distributed under the MIT license.

'''
Tracer - A lightweight intrusive Python function call tracer

Usage:

    import tracer

    @tracer.tracer(...)
    def function(x):
        ...

For more information, see https://github.com/Ricardo-shuo-liu/Tracer
'''


from .core.Tracer import tracer,Tracer


import collections
__VersionInfo = collections.namedtuple('VersionInfo',
                                       ('major', 'minor', 'micro'))
__version__ = '0.1.1'
__version_info__ = __VersionInfo(*(map(int, __version__.split('.'))))
del collections, __VersionInfo


__all__ = [
    "tracer",
    "Tracer"
]