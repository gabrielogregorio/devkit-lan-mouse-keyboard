#!/usr/bin/env bash
# Installs MouseKeyboard WiFi: system deps, /dev/uinput permissions, a Python
# venv and a systemd *user* service. The service is only enabled at login with
# --autostart (default: installed but off; start it by hand or from the tray launcher).
set -euo pipefail

AUTOSTART=0
[ "${1:-}" = "--autostart" ] && AUTOSTART=1

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${MKW_PORT:-8765}"
SERVICE_NAME="mousekeyboardwifi"

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
info() { printf '  \033[36m›\033[0m %s\n' "$*"; }

bold "MouseKeyboard WiFi — instalação"

# ---------------------------------------------------------------------------
# 1. System packages
# ---------------------------------------------------------------------------
bold "1/5  Pacotes do sistema (sudo)"
sudo apt-get update -qq
sudo apt-get install -y -qq \
  python3-venv python3-pip python3-gi \
  gir1.2-ayatanaappindicator3-0.1 \
  libnotify-bin

# ---------------------------------------------------------------------------
# 2. uinput permissions (kernel input injection)
# ---------------------------------------------------------------------------
bold "2/5  Permissões do /dev/uinput"
echo 'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"' \
  | sudo tee /etc/udev/rules.d/99-mousekeyboardwifi.rules >/dev/null
echo 'uinput' | sudo tee /etc/modules-load.d/uinput.conf >/dev/null
sudo modprobe uinput || true
sudo udevadm control --reload-rules && sudo udevadm trigger /dev/uinput || true

NEED_RELOGIN=0
if ! id -nG "$USER" | tr ' ' '\n' | grep -qx input; then
  sudo usermod -aG input "$USER"
  NEED_RELOGIN=1
  info "Adicionado ao grupo 'input' (exige novo login)."
fi

# ---------------------------------------------------------------------------
# 3. Python virtualenv (system-site-packages so PyGObject/tray works)
# ---------------------------------------------------------------------------
bold "3/5  Ambiente Python"
if [ ! -d "$REPO/venv" ]; then
  python3 -m venv --system-site-packages "$REPO/venv"
fi
"$REPO/venv/bin/pip" install -q --upgrade pip
"$REPO/venv/bin/pip" install -q -r "$REPO/requirements.txt"

# ---------------------------------------------------------------------------
# 4. systemd user service (autostart)
# ---------------------------------------------------------------------------
bold "4/5  Serviço systemd"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
cat > "$UNIT_DIR/$SERVICE_NAME.service" <<EOF
[Unit]
Description=MouseKeyboard WiFi - controle remoto de mouse e teclado
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=$REPO/venv/bin/python $REPO/server/main.py
Environment=MKW_PORT=$PORT
Restart=on-failure
RestartSec=2

[Install]
WantedBy=graphical-session.target
EOF

systemctl --user daemon-reload
if [ "$AUTOSTART" -eq 1 ]; then
  systemctl --user enable "$SERVICE_NAME.service" >/dev/null
  info "Autostart ligado (sobe junto com a sessão)."
else
  info "Autostart desligado (padrão). Ligar no login: ./install.sh --autostart"
fi

# ---------------------------------------------------------------------------
# 5. Start
# ---------------------------------------------------------------------------
bold "5/5  Pronto"
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
if [ "$NEED_RELOGIN" -eq 1 ]; then
  info "Faça LOGOUT/LOGIN (ou reinicie) para o grupo 'input' valer, depois rode:"
  info "    systemctl --user start $SERVICE_NAME"
elif [ "$AUTOSTART" -eq 1 ]; then
  systemctl --user restart "$SERVICE_NAME.service"
  info "Serviço iniciado."
else
  info "Para usar agora:  systemctl --user start $SERVICE_NAME   (ou ./run.sh)"
fi
echo
bold "No celular (mesma rede Wi-Fi) abra:  http://${IP:-SEU_IP}:$PORT"
echo
info "Status:   systemctl --user status $SERVICE_NAME"
info "Logs:     journalctl --user -u $SERVICE_NAME -f"
info "Parar:    systemctl --user stop $SERVICE_NAME"
info "Desligar autostart: systemctl --user disable $SERVICE_NAME"
