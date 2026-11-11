"""Read-only hardware inventory using Linux sysfs and standard system tools."""

from __future__ import annotations

import glob
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from .i18n import _


@dataclass
class Device:
    name: str
    category: str
    details: str = ""
    driver: str | None = None
    status: str = "unknown"
    source: str = ""


def _read(path: str | Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except (OSError, UnicodeError):
        return ""


def _run(args: list[str], timeout: int = 8) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return result.stdout if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _driver(path: str) -> str | None:
    try:
        target = os.path.realpath(os.path.join(path, "driver"))
        if os.path.exists(os.path.join(path, "driver")):
            return os.path.basename(target)
    except OSError:
        pass
    return None


def _pci_devices() -> list[Device]:
    if not Path("/sys/bus/pci/devices").exists():
        return []
    names: dict[str, str] = {}
    for line in _run(["lspci", "-D", "-nn"]).splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            names[parts[0]] = parts[1]
    result = []
    for path in sorted(glob.glob("/sys/bus/pci/devices/*")):
        address = os.path.basename(path)
        name = names.get(address, f"PCI-enhet {address}")
        category = _pci_category(_read(os.path.join(path, "class")))
        driver = _driver(path)
        result.append(Device(name=name, category=category, details=address, driver=driver,
                             status="active" if driver else "missing", source="PCI / sysfs"))
    return result


def _pci_category(raw: str) -> str:
    try:
        code = int(raw, 16) >> 16
    except ValueError:
        return _("Other PCI device")
    if code == 0x03: return _("Graphics")
    if code == 0x02: return _("Network")
    if code == 0x01: return _("Storage")
    if code == 0x0C03: return _("USB controller")
    if code == 0x0403: return _("Audio")
    if code == 0x0600: return _("Motherboard")
    return _("Other PCI device")


def _usb_devices() -> list[Device]:
    root = Path("/sys/bus/usb/devices")
    if not root.exists():
        return []
    result = []
    for path in sorted(root.iterdir()):
        vendor, product = _read(path / "idVendor"), _read(path / "idProduct")
        if not vendor or not product:
            continue
        name = _read(path / "product") or _("USB device {id}").format(id=f"{vendor}:{product}")
        manufacturer = _read(path / "manufacturer")
        if manufacturer and manufacturer.lower() not in name.lower():
            name = f"{manufacturer} {name}"
        driver = _driver(str(path))
        # USB interfaces often carry the actual driver; inspect their interface entries.
        if not driver:
            for interface in path.parent.glob(path.name + ":*"):
                driver = _driver(str(interface))
                if driver:
                    break
        result.append(Device(name=name, category="USB", details=f"{vendor}:{product} · {path.name}",
                             driver=driver, status="active" if driver else "unknown", source="USB / sysfs"))
    return result


def _system_summary() -> list[tuple[str, str]]:
    cpu = platform.processor()
    if not cpu and Path("/proc/cpuinfo").exists():
        for line in _read("/proc/cpuinfo").splitlines():
            if line.lower().startswith(("model name", "hardware", "processor")) and ":" in line:
                cpu = line.split(":", 1)[1].strip()
                if cpu:
                    break
    return [
        (_("Computer"), _read("/sys/class/dmi/id/product_name") or platform.node() or _("Unknown")),
        (_("Manufacturer"), _read("/sys/class/dmi/id/sys_vendor") or _("Unknown")),
        (_("Processor"), cpu or platform.machine()),
        (_("Kernel"), platform.release()),
        (_("Architecture"), platform.machine()),
        (_("Memory"), _memory()),
    ]


def _memory() -> str:
    for line in _read("/proc/meminfo").splitlines():
        if line.startswith("MemTotal:"):
            try:
                return f"{int(line.split()[1]) // 1024} MiB"
            except (ValueError, IndexError):
                break
    return _("Unknown")


def _block_devices() -> list[Device]:
    result = []
    for path in sorted(glob.glob("/sys/block/*")):
        name = os.path.basename(path)
        if name.startswith(("loop", "ram", "zram")):
            continue
        size = _read(os.path.join(path, "size"))
        try:
            capacity = f"{int(size) * 512 // (1024**3)} GiB" if size else ""
        except ValueError:
            capacity = ""
        dev_path = os.path.realpath(path)
        driver = _driver(os.path.join(path, "device"))
        result.append(Device(name=name, category=_("Storage"), details=capacity, driver=driver,
                             status="active" if driver else "unknown", source="Block / sysfs"))
    return result


def collect_inventory() -> dict:
    devices = _pci_devices() + _usb_devices() + _block_devices()
    counts = {"active": 0, "missing": 0, "unknown": 0}
    for device in devices:
        counts[device.status] = counts.get(device.status, 0) + 1
    return {
        "system": _system_summary(),
        "devices": [device.__dict__ for device in devices],
        "counts": counts,
        "tools": {name: shutil.which(name) is not None for name in ("lspci", "lsusb", "lshw")},
        "kernel": platform.system() == "Linux",
    }
