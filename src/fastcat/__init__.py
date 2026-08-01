#!/usr/bin/env python

from importlib.metadata import PackageNotFoundError, version

from fastcat.interface import FastCat

try:
    __version__ = version("fastcat")
except PackageNotFoundError:  # running straight from a source checkout
    __version__ = "0.0.0.dev0"

__all__ = ["FastCat", "__version__"]
