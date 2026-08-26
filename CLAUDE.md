# CLAUDE.md — MouseKeyboard WiFi

Guia para o Claude (e humanos) trabalharem neste repositório. Descreve o que o
projeto é, como está montado, o protocolo, as decisões de design e os comandos
de operação/teste.

---

## 1. Visão geral

App que permite **controlar o mouse e o teclado de um PC Ubuntu pelo celular**,
na rede local, abrindo apenas um endereço no navegador do celular — **sem app,
sem senha, sem login**.

Requisitos originais (todos atendidos):

- Controla **mouse e teclado** do PC via Wi-Fi.
- **Só funciona na rede local** (aceita apenas IPs privados/loopback/link-local).
- **Notificação do Ubuntu** a cada novo dispositivo conectado.
- Ícone **persistente na bandeja** indicando se há alguém conectado.
- No celular: **touchpad** (deslizar move, tocar clica, scroll) e **teclado**.
- Tudo replicado fielmente no Ubuntu.
- **Serviço com autostart** (systemd user), iniciável pelo terminal.
- UI **moderna e simples**.
- **Só recebe comandos** — nunca envia dados de volta (sem captura de tela,
  arquivos, etc.).
- Conexão **sem senha**: digita o IP e usa.

Funcionalidades adicionais pedidas depois:

- Teclado **HTML próprio** (não o do celular), com QWERTY + camada de símbolos +
  setas, responsivo em **retrato e paisagem**.
- Teclas estilo PC: **Ctrl, Alt, Super, Esc, Tab, Del** + **combinações reais**
  (Ctrl+C, Ctrl+Alt+T, Alt+Tab…).
- Teclado e touchpad **sempre visíveis juntos** (sem precisar abrir nada).
- **Multitouch**: segurar um botão de clique com um dedo e mover outro dedo no
  touchpad ao mesmo tempo (arrastar/selecionar).

> Nota: houve uma versão com gesto de "toque-e-meio" (tap-and-drag estilo
> libinput) que **foi revertida** a pedido do usuário, em favor do multitouch
> "segura o botão + move". Não reintroduzir sem pedido explícito.

---

## 2. Arquitetura

```
┌─────────────┐   HTTP (UI)      ┌──────────────────────────────────────┐
│  Navegador  │ ───────────────▶ │  FastAPI (web.py)                    │
│  do celular │   WebSocket /ws  │   - serve web/ (UI estática)         │
│  (web/)     │ ◀──────────────▶ │   - recebe comandos JSON             │
└─────────────┘   comandos JSON  │   - trava: só IP da rede local       │
                                 └───────────────┬──────────────────────┘
                                                 │ chama
                                                 ▼
                                 ┌──────────────────────────────────────┐
                                 │ InputController (input_device.py)    │
                                 │   evdev UInput → /dev/uinput         │
                                 │   (injeção a nível de kernel)        │
                                 └──────────────────────────────────────┘
            main.py orquestra: servidor (thread) + Tray/notificações (GTK main)
```

- **Injeção de entrada** é feita via `/dev/uinput` (evdev `UInput`), a nível de
  kernel — por isso funciona **igual em X11 e Wayland**. Não depende de
  `pynput`/`xdotool`/`ydotool`.
- A **UI mobile é uma página web** servida pelo próprio PC; o celular só precisa
  de um navegador. Os comandos trafegam por **WebSocket** (baixa latência).
- O fluxo é **unidirecional em dados de usuário**: o servidor só *recebe*
  comandos e os injeta. Nada é lido nem devolvido ao celular.

---

## 3. Estrutura de arquivos

```
mousekeyboardwifi/
├── CLAUDE.md            # este arquivo
├── README.md           # instruções de uso para o usuário final (PT-BR)
├── requirements.txt    # fastapi, uvicorn[standard], evdev
├── install.sh          # deps + permissão uinput + serviço systemd (autostart)
├── uninstall.sh        # remove serviço e regras
├── run.sh              # roda em primeiro plano (teste)
├── .gitignore          # venv, __pycache__
├── server/
│   ├── main.py         # entry point: monta tudo, watchdog de bind, callbacks
│   ├── input_device.py # mouse+teclado virtual via uinput; mapas de teclas
│   ├── web.py          # FastAPI: estáticos + /ws + trava de rede local
│   └── tray.py         # ícone de bandeja (AppIndicator) + notify-send
└── web/                # UI mobile (servida estaticamente)
    ├── index.html
    ├── style.css
    └── app.js          # WebSocket, gestos do touchpad, teclado on-screen
```

---

## 4. Backend (Python)

### `server/input_device.py` — `InputController`
- Cria um dispositivo virtual `UInput` chamado `mousekeyboardwifi` com
  capacidades: `EV_REL` (REL_X, REL_Y, REL_WHEEL, REL_HWHEEL) e `EV_KEY` (todas
  as teclas usadas + botões do mouse + modificadores).
- Métodos:
  - `move(dx, dy)` — movimento relativo do cursor.
  - `scroll(dx, dy)` — roda vertical/horizontal.
  - `button(name, pressed)` / `click(name)` — `left|right|middle`.
  - `type_text(text)` — digita uma string char-a-char (layout **US**).
  - `key(name)` — tecla especial nomeada.
  - `combo(mods, key)` — segura modificadores, bate a tecla, solta (atalhos).
  - `close()`.
- Um `threading.Lock` serializa as escritas no uinput (o dispatch roda em
  thread via `asyncio.to_thread`).
- **Mapa de caracteres** (`CHAR_MAP`): construído para layout **US QWERTY**,
  inclui letras (com shift p/ maiúsculas), dígitos, símbolos do shift+número e
  pontuação com pares shiftados. ~97 entradas.

### `server/web.py` — FastAPI
- `create_app(controller, on_connect, on_disconnect)` monta o app.
- `is_local(host)`: aceita apenas `ip.is_private | is_loopback | is_link_local`
  (trata IPv4-mapped IPv6). **Toda** requisição HTTP passa por um middleware que
  retorna **403** se não for local; o handler do WebSocket fecha com código
  **1008** se não for local.
- Endpoints:
  - `GET /` e estáticos → servidos de `web/` via `StaticFiles(html=True)`.
  - `WS /ws` → loop de recepção; cada mensagem JSON é despachada em
    `asyncio.to_thread(_dispatch, ...)` (uinput é bloqueante).
- `_dispatch` traduz a mensagem JSON em chamadas do `InputController`.

### `server/tray.py`
- `Tray(ip, port)`: ícone de bandeja via `gi` + `AyatanaAppIndicator3` (GTK3).
  Menu mostra status (nº de conectados), endereço e "Sair".
- `set_connected(n)` atualiza o rótulo (via `GLib.idle_add`, thread-safe).
- **Degradação graciosa**: se o stack GTK/AppIndicator não existir, roda
  *headless* (sem ícone) bloqueando num `Event`.
- `notify(title, body)`: dispara `notify-send` (best-effort).

### `server/main.py` — orquestração
- Lê `MKW_HOST` (default `0.0.0.0`) e `MKW_PORT` (default **8765**).
- Cria `InputController` (sai com erro claro se faltar permissão no uinput).
- Sobe o uvicorn numa **thread** e aguarda `server.started` por ~5s — se não
  subir (ex.: porta ocupada), **encerra com exit(1)** para o systemd reportar
  falha (em vez de ficar "active" mas morto).
- Callbacks `on_connect`/`on_disconnect` mantêm um contador (com lock),
  disparam notificação e atualizam a bandeja.
- `tray.run()` bloqueia a thread principal (loop do GTK ou espera headless).

---

## 5. Protocolo WebSocket

Cliente → servidor, mensagens **JSON**, campo `t` = tipo. Nunca há resposta de
dados (o servidor não envia comandos de volta).

| `t`     | Campos                       | Ação                                   |
|---------|------------------------------|----------------------------------------|
| `m`     | `dx`, `dy`                   | Move o cursor (relativo)               |
| `s`     | `dx`, `dy`                   | Scroll (wheel / hwheel)                |
| `c`     | `b` (`left`/`right`/`middle`)| Clique (down+up)                       |
| `d`     | `b`                          | Botão **pressiona** (segura)           |
| `u`     | `b`                          | Botão **solta**                        |
| `k`     | `text`                       | Digita o texto (char-a-char, US)       |
| `key`   | `code`                       | Tecla especial nomeada                 |
| `combo` | `mods` (lista), `key`        | Atalho: segura `mods`, bate `key`, solta |

**Botões**: `left`, `right`, `middle`.

**Teclas especiais (`key.code`)**: `backspace`, `enter`, `tab`, `space`,
`esc`/`escape`, `up`, `down`, `left`, `right`, `home`, `end`, `pageup`,
`pagedown`, `delete`/`del`.

**Modificadores (`combo.mods`)**: `ctrl`/`control`, `alt`, `altgr`, `shift`,
`super`/`meta`/`win`. Em `combo`, `key` pode ser um caractere (`"c"`) ou uma
tecla especial (`"tab"`). Se o caractere exigir shift no layout, o shift é
adicionado automaticamente.

---

## 6. Frontend (`web/`)

UI dark, moderna, sem dependências externas. Tudo em `app.js` (vanilla JS).

### Layout (sempre visível, sem abrir nada)
`header` (status da conexão) → **touchpad** (flex) → **2 botões de clique** →
**teclado on-screen**. Responsivo: em paisagem e telas baixas as teclas encolhem
(media queries por `orientation` e `max-height`).

### Touchpad (gestos)
- **Arrastar 1 dedo** → move o cursor (`m`), com sensibilidade `SENS=1.6` e
  acumulação de deltas por `requestAnimationFrame` (suaviza e reduz mensagens).
- **Toque rápido** (curto, sem mover) → clique esquerdo (`c`).
- **2 dedos** → scroll (`s`); **2 dedos toque** → clique direito.
- Usa **`e.targetTouches`** (não `e.touches`): conta só os dedos que tocam no
  *próprio* touchpad — essencial para o multitouch (ver abaixo).

### Botões de clique (multitouch — pressionar e segurar)
- `bindHold(id, b)`: usa **pointer events**. `pointerdown` → `{t:'d'}` (segura),
  `pointerup`/`pointerleave`/`pointercancel` → `{t:'u'}` (solta).
- **Toque rápido** = down+up = clique normal.
- **Segurar o botão com um dedo + mover outro dedo no touchpad** = arrastar /
  selecionar (os dois toques coexistem porque o pad só conta `targetTouches`).

### Teclado on-screen
- Duas camadas: `abc` (QWERTY) e `sym` (símbolos), alternadas por `?123`/`ABC`.
- **Fileira de função** (em ambas): `Esc Tab Ctrl Alt ⊞(Super) ◀ ▲ ▼ ▶ Del`.
- **Shift** one-shot; **Caps Lock** com duplo-toque no Shift.
- **Modificadores** `Ctrl/Alt/Super` ficam **armados** (destacados) até a próxima
  tecla; aí enviam um `combo` e limpam. Suporta múltiplos juntos (Ctrl+Alt+Del).
  Shift entra no combo se estiver armado (Ctrl+Shift+T).
- **Repetição ao segurar** (`repeat: true`) em Backspace e setas.
- Render via `render()` a partir de `LAYERS`/`SPECIAL`; cada tecla tem
  `pointerdown` para resposta imediata.

### Conexão
- `ws://<host>/ws` (ou `wss` se https), com **reconexão automática** (1s) e
  indicador de status (bolinha verde/vermelha).

---

## 7. Segurança e modelo de confiança

- **Sem senha por design** — o usuário quis "digita o IP e usa".
- Defesa = **rede local apenas**: HTTP não-local → 403; WS não-local → close
  1008. `is_local` cobre privado/loopback/link-local.
- Dispositivo virtual **só escreve** eventos. Não há leitura de tela, arquivos,
  clipboard nem qualquer canal de volta ao celular.
- Recomendação: usar apenas em **Wi-Fi confiável** (qualquer um na mesma rede
  que souber o IP:porta pode controlar). Documentado no README.

---

## 8. Serviço, autostart e permissões

### systemd **user** service
- Unit: `~/.config/systemd/user/mousekeyboardwifi.service`.
- `WantedBy=graphical-session.target` (precisa da sessão gráfica para bandeja e
  notificações). `Restart=on-failure`. `Environment=MKW_PORT=8765`.
- É **user service** (não system) porque depende do DBus/sessão do usuário para
  bandeja + notificações; sobe no login.

### Permissão do `/dev/uinput`
- `install.sh` cria udev rule `99-mousekeyboardwifi.rules`
  (`KERNEL=="uinput", GROUP="input", MODE="0660"`), garante o módulo `uinput`
  carregado, e adiciona o usuário ao grupo `input` (exige relogin **uma vez**).
- **Importante (uaccess)**: numa sessão local ativa o `systemd-logind` já dá uma
  **ACL** `user:<você>:rw-` em `/dev/uinput`, então funciona na sessão atual
  mesmo antes do relogin. O grupo `input` é a garantia que **persiste após
  reboot**. Conferir com `getfacl /dev/uinput`.

### venv
- Criado com **`--system-site-packages`** para o `PyGObject` (gi/AppIndicator)
  do sistema ficar acessível dentro do venv. O tray **não** funciona sem o
  pacote apt `gir1.2-ayatanaappindicator3-0.1`.

---

## 9. Configuração

| Variável   | Default     | Descrição                          |
|------------|-------------|------------------------------------|
| `MKW_HOST` | `0.0.0.0`   | Interface de bind                  |
| `MKW_PORT` | `8765`      | Porta HTTP/WebSocket               |

> A porta **8765** foi escolhida porque **8000 estava ocupada** por outro app
> na máquina do usuário. Se mudar, atualize a unit (`Environment=`),
> o `install.sh` e o README.

---

## 10. Operação (comandos)

```bash
# Instalar tudo (deps + permissões + serviço + autostart). Precisa de sudo.
./install.sh

# Operar o serviço (user scope)
systemctl --user status  mousekeyboardwifi
systemctl --user restart mousekeyboardwifi
systemctl --user stop    mousekeyboardwifi
journalctl  --user -u    mousekeyboardwifi -f

# Rodar em primeiro plano (debug)
./run.sh        # = venv/bin/python server/main.py

# Remover
./uninstall.sh
```

Acesso no celular: `http://<IP-do-PC>:8765` (mesma Wi-Fi).

> Em ambientes shell sem sessão de usuário exportada, prefixe os `systemctl
> --user` com `XDG_RUNTIME_DIR=/run/user/$(id -u)`.

---

## 11. Desenvolvimento e testes

- **Web** (`web/`) é servida estática: editar e **dar refresh no celular** —
  **não precisa reiniciar** o serviço. Backend (`server/`) sim precisa restart.
- Checagens rápidas:
  ```bash
  node --check web/app.js          # sintaxe JS
  python3 -m py_compile server/*.py # sintaxe Python
  ```
- Smoke test (sem precisar de celular) — exercita uinput de verdade (a sessão do
  Ubuntu tem acesso ao /dev/uinput via ACL):
  ```bash
  ./venv/bin/python - <<'PY'
  import sys; sys.path.insert(0,"server")
  from input_device import InputController
  c = InputController()
  c.move(7,0); c.move(-7,0); c.scroll(0,1); c.key("left")
  c.type_text("hi"); c.combo(["ctrl"],"c"); c.close()
  print("ok")
  PY
  ```
- Teste do servidor + trava de rede via `fastapi.testclient.TestClient`
  (passar um controller fake e checar `GET /` = 200, IP público = 403).

---

## 12. Decisões de design e armadilhas (gotchas)

- **uinput em vez de pynput/xdotool**: única abordagem que funciona em X11 **e**
  Wayland de forma idêntica. Custo: precisa de permissão no `/dev/uinput`.
- **`is_private` no Python 3.12**: ranges de documentação (ex.: `203.0.113.0/24`)
  são classificados como privados. Inofensivo aqui; só atrapalha testes — use
  `8.8.8.8`/`1.1.1.1` como exemplos de "público".
- **`self.ui.device` pode ser `None`** (evdev não reabre o nó). Não acessar
  `.device.path` sem `getattr` — já tratado no log.
- **Watchdog de bind**: sem ele, falha de porta deixava o processo "active" mas
  sem servidor. `main.py` agora sai com 1 se não subir.
- **`targetTouches` vs `touches`**: `touches` é global (tela toda) — um dedo no
  botão seria contado como "2º dedo" no pad e viraria scroll. `targetTouches`
  resolve e habilita o multitouch botão+pad.
- **Pointer events nos botões**: dão captura implícita no touch, então segurar é
  estável e `pointerleave` não dispara no meio do hold.
- **Layout de teclado é US**: `type_text` assume US QWERTY. Caracteres fora do
  mapa são ignorados. Para outros layouts seria preciso um mapa configurável ou
  o protocolo de teclado virtual do Wayland (complexo) — não implementado.

---

## 13. Limitações conhecidas / ideias futuras

- Teclado físico/IME: o teclado é o **on-screen HTML** (decisão do usuário); não
  capturamos o teclado nativo do celular.
- `type_text` limitado ao layout US (acentos/IME não suportados).
- Sem autenticação (intencional). Se um dia quiser, dá para adicionar um PIN
  opcional sem quebrar o "sem senha" como default.
- Possíveis extensões: sensibilidade ajustável na UI, clique do meio na UI,
  teclas de mídia, F1–F12, modo "drag lock", gestos de 3 dedos.

---

## 14. Convenções para o Claude neste repo

- **Idioma**: UI, README e mensagens ao usuário em **PT-BR**. Código/comentários
  podem ficar em inglês (como já estão).
- **Não reintroduzir** o gesto tap-and-drag revertido sem pedido explícito.
- Ao mudar o **protocolo**, atualizar os três pontos: `_dispatch` (web.py),
  o método em `input_device.py` e o emissor em `app.js` — e a tabela na seção 5.
- Ao mudar a **porta** ou **env**, sincronizar `main.py`, `install.sh`, a unit e
  o README.
- Mudou só `web/`? Basta refresh no celular. Mudou `server/`? `systemctl --user
  restart mousekeyboardwifi`.
- Validar com `node --check` e `py_compile` antes de concluir.
