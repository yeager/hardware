"""GTK 4 / libadwaita interface for Hardware."""

from __future__ import annotations

import json
import sys

from .i18n import _
from .inventory import collect_inventory

try:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gio, Gtk
except (ImportError, ValueError):
    Adw = Gio = Gtk = None


APP_ID = "se.yeager.Hardware"
STATUS = {
    "active": (_("Driver active"), "emblem-ok-symbolic"),
    "missing": (_("No driver"), "dialog-warning-symbolic"),
    "unknown": (_("Unknown status"), "dialog-question-symbolic"),
}


def _category_icon(category: str) -> str:
    return {
        _("Graphics"): "video-display-symbolic",
        _("Network"): "network-wired-symbolic",
        _("Storage"): "drive-harddisk-symbolic",
        "USB": "drive-removable-media-symbolic",
        _("USB controller"): "usb-symbolic",
        _("Audio"): "audio-card-symbolic",
        _("Motherboard"): "computer-symbolic",
        _("Other PCI device"): "computer-symbolic",
    }.get(category, "computer-symbolic")


if Gtk:
    class DeviceRow(Gtk.ListBoxRow):
        def __init__(self, device: dict):
            super().__init__()
            self.device = device
            root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            for setter in (root.set_margin_top, root.set_margin_bottom): setter(10)
            for setter in (root.set_margin_start, root.set_margin_end): setter(12)
            icon = Gtk.Image.new_from_icon_name(_category_icon(device["category"]))
            icon.set_pixel_size(24)
            root.append(icon)
            labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            title = Gtk.Label(label=device["name"], xalign=0, wrap=True)
            title.add_css_class("heading")
            labels.append(title)
            parts = (device.get("category"), device.get("details"),
                     _("Driver: {driver}").format(driver=device["driver"]) if device.get("driver") else None)
            labels.append(Gtk.Label(label=" · ".join(x for x in parts if x), xalign=0, wrap=True, selectable=True))
            root.append(labels)
            root.set_hexpand(True)
            status_text, status_icon = STATUS.get(device.get("status"), STATUS["unknown"])
            badge = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            badge.append(Gtk.Image.new_from_icon_name(status_icon))
            badge.append(Gtk.Label(label=status_text))
            badge.add_css_class({"active": "success", "missing": "warning", "unknown": "dim-label"}.get(device.get("status"), "dim-label"))
            root.append(badge)
            self.set_child(root)


    class HardwareWindow(Adw.ApplicationWindow):
        def __init__(self, app):
            super().__init__(application=app, title=_("Hardware"), default_width=980, default_height=700)
            self.data = {}
            toolbar = Adw.ToolbarView()
            header = Adw.HeaderBar()
            self.search = Gtk.SearchEntry(placeholder_text=_("Search devices…"), hexpand=True)
            self.search.set_max_width_chars(32)
            header.set_title_widget(self.search)
            refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text=_("Refresh inventory"))
            refresh.connect("clicked", lambda *_: self.refresh())
            header.pack_end(refresh)
            menu = Gio.Menu()
            menu.append(_("About Hardware"), "app.about")
            header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu, tooltip_text=_("Menu")))
            toolbar.add_top_bar(header)

            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            self.summary = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            self.summary.set_margin_top(18); self.summary.set_margin_bottom(8)
            self.summary.set_margin_start(20); self.summary.set_margin_end(20)
            outer.append(self.summary)
            self.system_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
            self.system_box.set_margin_start(20); self.system_box.set_margin_end(20)
            self.system_box.set_margin_top(8); self.system_box.set_margin_bottom(16)
            self.system_box.add_css_class("card")
            outer.append(self.system_box)
            bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            bar.set_margin_start(20); bar.set_margin_end(20); bar.set_margin_bottom(8)
            bar.append(Gtk.Label(label=_("Devices"), xalign=0, hexpand=True))
            self.filter = Gtk.DropDown.new_from_strings([_("All"), STATUS["active"][0], STATUS["missing"][0], STATUS["unknown"][0]])
            self.filter.connect("notify::selected", lambda *_: self.populate())
            bar.append(self.filter)
            outer.append(bar)
            self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
            self.listbox.add_css_class("boxed-list")
            self.listbox.set_margin_start(20); self.listbox.set_margin_end(20); self.listbox.set_margin_bottom(18)
            self.listbox.set_filter_func(self._filter_row)
            scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
            scroll.set_child(self.listbox)
            outer.append(scroll)
            self.notice = Adw.Banner()
            self.notice.set_title(_("Hardware inventory requires Linux"))
            self.notice.set_revealed(False)
            outer.prepend(self.notice)
            self.empty = Gtk.Label(label=_("No devices found. Check that /sys is mounted."), wrap=True)
            self.empty.add_css_class("dim-label")
            self.empty.set_margin_top(18)
            outer.append(self.empty)
            self.search.connect("search-changed", lambda *_: self.listbox.invalidate_filter())
            toolbar.set_content(outer)
            self.set_content(toolbar)
            self.refresh()

        def refresh(self):
            self.data = collect_inventory()
            self.notice.set_revealed(not self.data.get("kernel"))
            self.empty.set_visible(bool(self.data.get("kernel")) and not self.data.get("devices"))
            self.update_summary()
            self.populate()

        def update_summary(self):
            while child := self.summary.get_first_child(): self.summary.remove(child)
            counts = self.data.get("counts", {})
            tiles = ((_("Devices"), sum(counts.values()), "card"),
                     (STATUS["active"][0], counts.get("active", 0), "success"),
                     (STATUS["missing"][0], counts.get("missing", 0), "warning"),
                     (STATUS["unknown"][0], counts.get("unknown", 0), "dim-label"))
            for label, value, css in tiles:
                tile = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                tile.set_hexpand(True); tile.set_margin_top(10); tile.set_margin_bottom(10)
                tile.set_margin_start(12); tile.set_margin_end(12); tile.add_css_class("card")
                number = Gtk.Label(label=str(value), xalign=0)
                number.add_css_class("title-1"); number.add_css_class(css)
                tile.append(number); tile.append(Gtk.Label(label=label, xalign=0, wrap=True))
                self.summary.append(tile)
            while child := self.system_box.get_first_child(): self.system_box.remove(child)
            for label, value in self.data.get("system", []):
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
                box.set_hexpand(True); box.set_margin_top(12); box.set_margin_bottom(12)
                key = Gtk.Label(label=label, xalign=0); key.add_css_class("dim-label")
                box.append(key); box.append(Gtk.Label(label=value, xalign=0, wrap=True, selectable=True))
                self.system_box.append(box)

        def populate(self):
            while child := self.listbox.get_first_child(): self.listbox.remove(child)
            for device in self.data.get("devices", []): self.listbox.append(DeviceRow(device))
            self.listbox.invalidate_filter()

        def _filter_row(self, row):
            device = row.device
            query = self.search.get_text().strip().casefold()
            searchable = " ".join(str(device.get(k, "")) for k in ("name", "category", "details", "driver", "source")).casefold()
            selected = self.filter.get_selected()
            wanted = {1: "active", 2: "missing", 3: "unknown"}.get(selected)
            return (not query or query in searchable) and (not wanted or device.get("status") == wanted)


    class HardwareApp(Adw.Application):
        def __init__(self):
            super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
            action = Gio.SimpleAction.new("about", None)
            action.connect("activate", self.about)
            self.add_action(action)

        def do_activate(self):
            window = self.props.active_window or HardwareWindow(self)
            window.present()

        def about(self, *_):
            dialog = Adw.AboutWindow(application_name=_("Hardware"), application_icon="computer",
                                     developer_name="Daniel Nylander", version="0.1.0",
                                     comments=_("View your computer's hardware and driver status."),
                                     license_type=Gtk.License.GPL_3_0)
            dialog.present(self.props.active_window)


def main() -> int:
    if "--json" in sys.argv:
        print(json.dumps(collect_inventory(), ensure_ascii=False, indent=2))
        return 0
    if not Gtk:
        print(_("GTK 4 and PyGObject are required. Install GTK/libadwaita Python bindings, or run `hardware --json`."), file=sys.stderr)
        return 1
    return HardwareApp().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
