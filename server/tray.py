"""Desktop integration: a persistent tray (status) icon and connection
notifications. Degrades gracefully to a headless blocking loop if the GTK /
AppIndicator stack is not available."""

import logging
import os
import subprocess
import threading

log = logging.getLogger(__name__)

_APP_NAME = "MouseKeyboard WiFi"


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
        # outro lançador já mostra o ícone deste app
        if os.environ.get("MKW_SEM_BANDEJA") == "1":
            log.info("MKW_SEM_BANDEJA=1: sem ícone próprio, só o loop headless")
            self._available = False
            return
        try:
            import gi

            gi.require_version("Gtk", "3.0")
            gi.require_version("AyatanaAppIndicator3", "0.1")
            from gi.repository import (  # noqa: E402
                Gtk,
                AyatanaAppIndicator3 as AppIndicator3,
                GLib,
            )

            self._gtk = Gtk
            self._glib = GLib

            menu = Gtk.Menu()

            self._status_item = Gtk.MenuItem(label="Aguardando conexão")
            self._status_item.set_sensitive(False)
            menu.append(self._status_item)

            addr_item = Gtk.MenuItem(label=f"http://{self.ip}:{self.port}")
            addr_item.set_sensitive(False)
            menu.append(addr_item)

            menu.append(Gtk.SeparatorMenuItem())

            quit_item = Gtk.MenuItem(label="Sair")
            quit_item.connect("activate", self._on_quit)
            menu.append(quit_item)

            menu.show_all()

            self._indicator = AppIndicator3.Indicator.new(
                "mousekeyboardwifi",
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

    def _on_quit(self, *_):
        self.stop()

    def set_connected(self, count: int):
        self.count = count
        if not self._available:
            return

        def _update():
            if count > 0:
                label = (
                    f"{count} dispositivo(s) conectado(s)"
                    if count != 1
                    else "1 dispositivo conectado"
                )
                icon = "input-mouse"
            else:
                label = "Aguardando conexão"
                icon = "input-mouse"
            self._status_item.set_label(label)
            self._indicator.set_icon_full(icon, label)
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
