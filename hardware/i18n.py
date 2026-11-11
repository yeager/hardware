"""Locale-aware gettext setup shared by UI and inventory code."""

from __future__ import annotations

import gettext
import sys
from pathlib import Path


def setup_translation() -> gettext.NullTranslations:
    package_root = Path(__file__).resolve().parent.parent
    candidates = (Path(__file__).resolve().parent / "locale", package_root / "po", Path(sys.prefix) / "share" / "locale")
    for localedir in candidates:
        if localedir.is_dir():
            catalog = gettext.translation("hardware", localedir=str(localedir), fallback=True)
            if not isinstance(catalog, gettext.NullTranslations) or any(localedir.glob("sv/LC_MESSAGES/hardware.mo")):
                return catalog
    return gettext.NullTranslations()


translation = setup_translation()
_ = translation.gettext
