"""Desktop strings (tray menu and notifications). English is the source text and the key;
PT_BR holds the Brazilian Portuguese line. The language comes from LMK_LANG, then the usual
LANGUAGE / LC_ALL / LC_MESSAGES / LANG: pt* shows pt-BR, anything else English.
tests/test_i18n.py fails on a missing line or on different {placeholders}. Logs stay English."""

import os

PT_BR = {
    "LAN Mouse & Keyboard": "LAN Mouse & Keyboard",
    "Waiting for a connection": "Aguardando conexão",
    "1 device connected": "1 dispositivo conectado",
    "{count} devices connected": "{count} dispositivos conectados",
    "New device connected": "Novo dispositivo conectado",
    "{ip} is controlling your PC": "{ip} está controlando seu PC",
}


def detect_language(env=None) -> str:
    env = os.environ if env is None else env
    for name in ("LMK_LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = env.get(name, "")
        if value:
            first = value.split(":")[0]
            return "pt-BR" if first.lower().startswith("pt") else "en"
    return "en"


LANG = detect_language()


def tr(text: str, lang: str | None = None, **values) -> str:
    lang = LANG if lang is None else lang
    line = PT_BR.get(text, text) if lang == "pt-BR" else text
    return line.format(**values) if values else line
