"""SENTINEL analytics package."""

import sys

# Windows consoles (and redirected/piped output on Windows, e.g.
# `python -m src.pipelines.master_pipeline *> log.txt`) default to the
# legacy cp1252 codepage, which cannot encode the status symbols
# (checkmark/cross/warning glyphs, etc.) used throughout this package's
# print statements. Force UTF-8 here, once, so it applies no matter which
# module in `src` is imported or run first, instead of crashing partway
# through a run with a UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")