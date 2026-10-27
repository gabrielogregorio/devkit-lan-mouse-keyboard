<div align="center">

# MouseKeyboard WiFi

**O celular vira mouse e teclado do PC pela rede local, só abrindo um endereço no navegador.**

![Python](https://img.shields.io/badge/Python-3.12-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![uinput](https://img.shields.io/badge/Linux-uinput-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)
![LAN](https://img.shields.io/badge/só%20rede%20local-sem%20nuvem-555555?style=for-the-badge)

</div>

## Sobre o projeto

Controle o **mouse e o teclado** do seu PC Ubuntu pelo celular, na rede local,
abrindo só um endereço no navegador — **sem app, sem senha**.

- 🖱️ Touchpad por gestos: arrastar move, tocar clica, 2 dedos rolam, 2 dedos
  tocando = botão direito.
- ⌨️ Teclado completo **na própria tela** (QWERTY + símbolos + setas), funciona
  em **retrato e paisagem**.
- 🔒 Aceita conexões **apenas da rede local** (IPs privados). Nada é enviado de
  volta — o serviço só *recebe* comandos.
- 🔔 **Notificação do Ubuntu** a cada novo dispositivo conectado.
- 📌 Ícone **persistente na bandeja** mostrando se há alguém conectado.
- 🚀 Roda como **serviço do systemd**; subir no login é opcional (`./install.sh --autostart`).

## Configurar num PC novo

```bash
git clone <url-do-repo> devkit-wifi-web-mouse
cd devkit-wifi-web-mouse
./install.sh              # pacotes (sudo), /dev/uinput, venv e serviço systemd (desligado)
```

- Na 1ª vez ele põe você no grupo `input`: **faça logout/login** antes de usar.
- O serviço fica **instalado mas desligado** no login. Para usar agora:
  `systemctl --user start mousekeyboardwifi` ou `./run.sh`. Para subir sempre no login:
  `./install.sh --autostart`.
- Funciona em X11 e Wayland (a entrada vai pelo `/dev/uinput`).
- Ícone próprio na barra: precisa da extensão AppIndicator do GNOME (vem no Ubuntu).
  `MKW_SEM_BANDEJA=1` tira o ícone (usado quando outro lançador já mostra um).

**Fora do repositório:** `venv/` (ignorado pelo git), `~/.config/systemd/user/mousekeyboardwifi.service`,
`/etc/udev/rules.d/99-mousekeyboardwifi.rules` e `/etc/modules-load.d/uinput.conf`.
Mudou a pasta de lugar? Rode `./install.sh` de novo (o serviço guarda o caminho).

## Scripts disponíveis

```bash
# Rodar
./run.sh                                       # primeiro plano (teste)
systemctl --user start mousekeyboardwifi       # como serviço
systemctl --user status mousekeyboardwifi
journalctl --user -u mousekeyboardwifi -f      # logs
MKW_PORT=9000 ./run.sh                         # outra porta

# Instalar / remover
./install.sh                # serviço instalado, desligado no login
./install.sh --autostart    # sobe junto com a sessão
./uninstall.sh

# Testar
venv/bin/pip install -e '.[test]' && venv/bin/python -m pytest
cd tests/frontend && npm install && npx playwright install chromium && npm test
```

## Como funciona

A injeção de mouse/teclado é feita via `/dev/uinput` (nível de kernel), então
funciona igual em **X11 e Wayland**. O celular abre uma página web servida pelo
PC; os comandos viajam por WebSocket.


## Uso

No celular (mesma rede Wi-Fi), abra:

```
http://SEU_IP:8765
```

O IP aparece no fim do `install.sh` e no log do serviço.


## Segurança

- Conexões de IPs não-privados são recusadas (HTTP **403** e WebSocket fechado).
- O dispositivo virtual só **escreve** eventos de entrada; não há leitura de
  tela, arquivos ou qualquer retorno de dados ao celular.
- Como não há senha, mantenha-se em redes Wi-Fi confiáveis.
