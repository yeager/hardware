#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
command -v msgfmt >/dev/null 2>&1 || {
    echo "msgfmt is required to compile translations (install gettext)." >&2
    exit 1
}
mkdir -p build/locale/sv/LC_MESSAGES dist
msgfmt --check --check-format -o build/locale/sv/LC_MESSAGES/hardware.mo po/sv.po
python3 -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
