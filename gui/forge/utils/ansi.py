# gui/utils/ansi.py
"""ANSI terminal escape-sequence stripping."""

import re

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[mABCDEFGHJKSTfhilmnqrsu]')


def strip_ansi(text: str) -> str:
    """Remove ANSI terminal escape sequences from *text*.

    forgejo-main (installer) emits coloured output via ANSI codes which
    look like garbage inside a Qt widget.  Strip them before display.
    """
    return _ANSI_RE.sub('', text)
