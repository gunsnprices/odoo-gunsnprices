"""Which copy of the gunsnprices title parser the module uses.

The module ships its own copy (lib/gunsnprices), so it installs by copying the folder into the addons path:
no pip, nothing to download. If a newer release of the same series is installed with pip
(``pip install -U gunsnprices`` or a requirements.txt on Odoo.sh), that one is used instead: same API, newer model
dictionaries. Another series (0.2, 1.0, ...) is ignored, since its API may differ.

This file does not import Odoo, so it can be tested without an Odoo server.
"""
from __future__ import annotations

import logging
import re

from .lib import gunsnprices as _bundled

_logger = logging.getLogger(__name__)

__all__ = ["gnp", "SOURCE", "VERSION", "version_tuple", "pick"]


def version_tuple(version: str) -> tuple:
    """"0.1.2" -> (0, 1, 2). Anything after the numbers ("0.1.3rc1", "0.1.3.dev0") is ignored."""
    return tuple(int(x) for x in re.findall(r"\d+", re.match(r"[\d.]*", version or "").group(0)))


def pick(bundled, installed):
    """Return (module, source): the installed package if it is a newer release of the bundled series."""
    if installed is not None:
        have = version_tuple(getattr(installed, "__version__", ""))
        ours = version_tuple(getattr(bundled, "__version__", ""))
        if len(have) >= 2 and have[:2] == ours[:2] and have > ours:
            return installed, "installed"
    return bundled, "bundled"


def _load():
    try:
        import gunsnprices as installed  # an absolute import: the pip package, not lib/gunsnprices
    except ImportError:
        installed = None
    except Exception:  # a broken install must not break the module
        _logger.warning("gunsnprices: the installed package failed to import, using the bundled copy", exc_info=True)
        installed = None
    return pick(_bundled, installed)


gnp, SOURCE = _load()
VERSION = gnp.__version__
