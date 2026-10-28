#!/usr/bin/env bash
# Installs LAN Mouse & Keyboard: system deps, /dev/uinput permissions, a Python
# venv and a systemd *user* service. The service is only enabled at login with
# --autostart (default: installed but off; start it by hand or from a tray launcher).
set -euo pipefail

AUTOSTART=0
[ "${1:-}" = "--autostart" ] && AUTOSTART=1

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${LMK_PORT:-8765}"
SERVICE_NAME="lan-mouse-keyboard"

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
info() { printf '  \033[36m›\033[0m %s\n' "$*"; }

bold "LAN Mouse & Keyboard - install"

# ---------------------------------------------------------------------------
# 1. System packages
# ---------------------------------------------------------------------------
bold "1/5  System packages (sudo)"
sudo apt-get update -qq
sudo apt-get install -y -qq \
  python3-venv python3-pip python3-gi \
  gir1.2-ayatanaappindicator3-0.1 \
  libnotify-bin

# ---------------------------------------------------------------------------
# 2. uinput permissions (kernel input injection)
# ---------------------------------------------------------------------------
bold "2/5  /dev/uinput permissions"
echo 'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"' \
  | sudo tee /etc/udev/rules.d/99-lan-mouse-keyboard.rules >/dev/null
echo 'uinput' | sudo tee /etc/modules-load.d/uinput.conf >/dev/null
sudo modprobe uinput || true
sudo udevadm control --reload-rules && sudo udevadm trigger /dev/uinput || true

NEED_RELOGIN=0
if ! id -nG "$USER" | tr ' ' '\n' | grep -qx input; then
  sudo usermod -aG input "$USER"
  NEED_RELOGIN=1
  info "Added to the 'input' group (needs a new login)."
fi

# ---------------------------------------------------------------------------
# 3. Python virtualenv (system-site-packages so PyGObject/tray works)
# ---------------------------------------------------------------------------
bold "3/5  Python environment"
if [ ! -d "$REPO/venv" ]; then
  python3 -m venv --system-site-packages "$REPO/venv"
fi
"$REPO/venv/bin/pip" install -q --upgrade pip
"$REPO/venv/bin/pip" install -q -r "$REPO/requirements.txt"

# ---------------------------------------------------------------------------
# 4. systemd user service
# ---------------------------------------------------------------------------
bold "4/5  systemd service"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
cat > "$UNIT_DIR/$SERVICE_NAME.service" <<UNIT
[Unit]
Description=LAN Mouse & Keyboard - phone as mouse and keyboard over the local network
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=$REPO/venv/bin/python $REPO/server/main.py
Environment=LMK_PORT=$PORT
Restart=on-failure
RestartSec=2

[Install]
WantedBy=graphical-session.target
UNIT

systemctl --user daemon-reload
if [ "$AUTOSTART" -eq 1 ]; then
  systemctl --user enable "$SERVICE_NAME.service" >/dev/null
  info "Autostart on (starts with the session)."
else
  info "Autostart off (default). Start at login: ./install.sh --autostart"
fi

# ---------------------------------------------------------------------------
# 5. Start
# ---------------------------------------------------------------------------
bold "5/5  Done"
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
if [ "$NEED_RELOGIN" -eq 1 ]; then
  info "Log OUT and back IN (or reboot) so the 'input' group applies, then run:"
  info "    systemctl --user start $SERVICE_NAME"
elif [ "$AUTOSTART" -eq 1 ]; then
  systemctl --user restart "$SERVICE_NAME.service"
  info "Service started."
else
  info "To use it now:  systemctl --user start $SERVICE_NAME   (or ./run.sh)"
fi
echo
bold "On the phone (same network) open:  http://${IP:-YOUR_IP}:$PORT"
echo
info "Status:   systemctl --user status $SERVICE_NAME"
info "Logs:     journalctl --user -u $SERVICE_NAME -f"
info "Stop:     systemctl --user stop $SERVICE_NAME"
info "Autostart off: systemctl --user disable $SERVICE_NAME"
