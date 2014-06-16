# -*- coding: utf-8 -*-

"""
Compatability module for various pythons and environments.
"""


try:
    import cPickle
except ImportError: # pragma: no cover
    # python 3 pickle module
    import pickle as cPickle
