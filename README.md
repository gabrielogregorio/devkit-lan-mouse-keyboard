# MouseKeyboard WiFi

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
- 🚀 Roda como **serviço do systemd** com **autostart** no login.

## Como funciona

A injeção de mouse/teclado é feita via `/dev/uinput` (nível de kernel), então
funciona igual em **X11 e Wayland**. O celular abre uma página web servida pelo
PC; os comandos viajam por WebSocket.

## Instalação

```bash
cd mousekeyboardwifi
./install.sh
```

O script instala dependências, configura a permissão do `/dev/uinput`, cria o
ambiente Python e registra o serviço com autostart.

> ⚠️ Se for a primeira vez, ele adiciona você ao grupo `input`. **Faça
> logout/login** uma vez e depois: `systemctl --user start mousekeyboardwifi`.

## Uso

No celular (mesma rede Wi-Fi), abra:

```
http://SEU_IP:8765
```

O IP é mostrado no fim do `install.sh` e na notificação ao iniciar.

## Comandos úteis

```bash
systemctl --user status  mousekeyboardwifi   # estado
journalctl  --user -u    mousekeyboardwifi -f # logs
systemctl --user restart mousekeyboardwifi   # reiniciar
systemctl --user stop    mousekeyboardwifi   # parar
./run.sh                                      # rodar em primeiro plano (teste)
./uninstall.sh                                # remover serviço e regras
```

Porta configurável com `MKW_PORT` (padrão `8765`).

## Segurança

- Conexões de IPs não-privados são recusadas (HTTP **403** e WebSocket fechado).
- O dispositivo virtual só **escreve** eventos de entrada; não há leitura de
  tela, arquivos ou qualquer retorno de dados ao celular.
- Como não há senha, mantenha-se em redes Wi-Fi confiáveis.
