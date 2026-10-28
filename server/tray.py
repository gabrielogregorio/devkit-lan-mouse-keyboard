"""Desktop integration: a persistent tray (status) icon and connection
notifications. Degrades gracefully to a headless blocking loop if the GTK /
AppIndicator stack is not available."""

import logging
import os
import subprocess
import threading

from i18n import tr

log = logging.getLogger(__name__)

_APP_NAME = tr("LAN Mouse & Keyboard")


def notify(title: str, body: str = ""):
    """Fire a desktop notification via notify-send (best effort)."""
    try:
        subprocess.Popen(
            ["notify-send", "-a", _APP_NAME, "-i", "input-mouse", title, body]
        )
    except FileNotFoundError:
        log.warning("notify-send not installed; skipping notification")


class Tray:
    """Persistent indicator showing whether a phone is connected."""

    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.count = 0
        self._available = False
        self._stop = threading.Event()
        self._glib = None
        self._indicator = None
        self._status_item = None
        self._gtk = None
        self._setup()

    def _setup(self):
        # another launcher already shows this app's icon
        if os.environ.get("LMK_NO_TRAY") == "1":
            log.info("LMK_NO_TRAY=1: no own icon, headless loop only")
            self._available = False
            return
        try:
            import gi

            gi.require_version("Gtk", "3.0")
            gi.require_version("AyatanaAppIndicator3", "0.1")
            from gi.repository import (
                AyatanaAppIndicator3 as AppIndicator3,
            )
            from gi.repository import (  # noqa: E402
                GLib,
                Gtk,
            )

            self._gtk = Gtk
            self._glib = GLib

            menu = Gtk.Menu()

            self._status_item = Gtk.MenuItem(label=tr("Waiting for a connection"))
            self._status_item.set_sensitive(False)
            menu.append(self._status_item)

            addr_item = Gtk.MenuItem(label=f"http://{self.ip}:{self.port}")
            addr_item.set_sensitive(False)
            menu.append(addr_item)

            # no Quit item: the icon always stays; stop the service to turn it off
            menu.show_all()

            self._indicator = AppIndicator3.Indicator.new(
                "lan-mouse-keyboard",
                "input-mouse",
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )
            self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            self._indicator.set_title(_APP_NAME)
            self._indicator.set_menu(menu)
            self._available = True
            log.info("Tray indicator ready")
        except Exception as ex:  # noqa: BLE001
            log.warning("Tray unavailable (%s); running headless", ex)
            self._available = False

    def set_connected(self, count: int):
        self.count = count
        if not self._available:
            return

        def _update():
            if count == 1:
                label = tr("1 device connected")
            elif count > 1:
                label = tr("{count} devices connected", count=count)
            else:
                label = tr("Waiting for a connection")
            self._status_item.set_label(label)
            self._indicator.set_icon_full("input-mouse", label)
            return False

        self._glib.idle_add(_update)

    def run(self):
        """Block the main thread (GTK loop, or an Event wait if headless)."""
        if self._available:
            try:
                self._gtk.main()
            except KeyboardInterrupt:
                pass
        else:
            try:
                self._stop.wait()
            except KeyboardInterrupt:
                pass

    def stop(self):
        if self._available and self._gtk is not None:
            self._gtk.main_quit()
        self._stop.set()
