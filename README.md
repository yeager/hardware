# Hardware

A GNOME application that shows your computer's hardware and the kernel drivers bound to each device. The interface and documentation use English by default; Swedish is available through gettext localization.

## Run

On Linux with Python 3, GTK 4, libadwaita, and PyGObject installed:

```sh
python3 -m hardware.app
```

To print the inventory as JSON without GTK:

```sh
python3 -m hardware.app --json
```

`lspci` improves PCI device names. Without it, the app uses PCI addresses and sysfs class data. PCI devices without a bound driver are marked as missing; USB and storage devices are marked unknown when sysfs cannot confirm a driver. This reports kernel binding, not whether a driver is optimal or up to date.

## Swedish localization and build

Translations live in `po/sv.po`; `po/hardware.pot` is the English message template. Compile the Swedish catalog and build a wheel with:

```sh
./build.sh
```

The script uses the system `msgfmt` command to compile `hardware/locale/sv/LC_MESSAGES/hardware.mo`, then builds the Python wheel and source archive. It does not install dependencies. To install runtime requirements on Debian or Ubuntu:

```sh
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 pciutils
```

The app detects the active process locale. Set `LANG=sv_SE.UTF-8` (with that locale generated on the system) to use Swedish; otherwise English strings are shown.
