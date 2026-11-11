#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
command -v msgfmt >/dev/null 2>&1 || {
    echo "msgfmt is required to compile translations (install gettext)." >&2
    exit 1
}
mkdir -p hardware/locale/sv/LC_MESSAGES dist
msgfmt --check --check-format -o hardware/locale/sv/LC_MESSAGES/hardware.mo po/sv.po
python3 -m build --wheel --sdist --outdir dist .
