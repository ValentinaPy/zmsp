#

# The Mingle Structured Prediction (v0plus) package
# by zzs (from 2018.02 - now)

# dependencies: pytorch, numpy, scipy, gensim, cython

VERSION_MAJOR = 0
VERSION_MINOR = 0
VERSION_PATCH = 1


def version():
    return (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)


__version__ = ".".join(str(z) for z in version())

# basic principles
# 0. shared pattern: make it re-usable
# 1. lazy eval: calc as need & with cache
# 2. cpp style: maybe transfer to other lang (c++) in the future
# 3. search oriented: focus should be at the searching part
# 4. others: avoid-early-opt, checking&snapshot, clear-code&locality, table-driven&oo
# !!: (renewed) composition rather than inheritance, that is, some useful pieces rather than a framework
# !!: (again-corrected) The goal is not to build a whole framework, but several useful pieces.

# conventions
# todo(0)/todo(warn): simply warning
# todo(+N): need what level of efforts
# TODO(!): unfinished, real todo

# hierarchically: msp -> scripts / tasks, no reverse ref allowed!

"""
Driver -- Utils
Data -- Model (nn) -- Search
"""

# -- full-usage init order (example: tasks.zdpar.common.confs.init_everything)
# ** no need to init if only use default ones
# top-level
# utils
# nn
