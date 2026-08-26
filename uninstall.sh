#!/usr/bin/env bash
set -euo pipefail
SERVICE_NAME="mousekeyboardwifi"

systemctl --user stop "$SERVICE_NAME.service" 2>/dev/null || true
systemctl --user disable "$SERVICE_NAME.service" 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/$SERVICE_NAME.service"
systemctl --user daemon-reload

sudo rm -f /etc/udev/rules.d/99-mousekeyboardwifi.rules
sudo rm -f /etc/modules-load.d/uinput.conf
sudo udevadm control --reload-rules || true

echo "Removido. (O grupo 'input' e o venv/ foram mantidos; apague venv/ manualmente se quiser.)"
