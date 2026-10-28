"""Tests for i18n.py: every tr() string has a pt-BR line, placeholders match, language detection."""
import re
from pathlib import Path

import i18n

SERVER = Path(__file__).resolve().parent.parent / "server"


def _used_strings():
    used = set()
    for path in SERVER.glob("*.py"):
        used |= set(re.findall(r'\btr\(\s*"((?:[^"\\]|\\.)*)"', path.read_text()))
    return used


def _placeholders(text):
    return sorted(re.findall(r"\{(\w+)\}", text))


def test_every_tr_string_has_a_pt_br_line():
    used = _used_strings()
    assert len(used) >= 5
    assert sorted(used - set(i18n.PT_BR)) == []


def test_no_pt_br_line_is_left_unused():
    assert sorted(set(i18n.PT_BR) - _used_strings()) == []


def test_placeholders_match():
    for english, portuguese in i18n.PT_BR.items():
        assert _placeholders(portuguese) == _placeholders(english), english


def test_detect_language():
    assert i18n.detect_language({"LANG": "pt_BR.UTF-8"}) == "pt-BR"
    assert i18n.detect_language({"LANGUAGE": "pt_BR:en", "LANG": "en_US.UTF-8"}) == "pt-BR"
    assert i18n.detect_language({"LANG": "en_US.UTF-8"}) == "en"
    assert i18n.detect_language({"LMK_LANG": "en", "LANG": "pt_BR.UTF-8"}) == "en"
    assert i18n.detect_language({}) == "en"


def test_tr_fills_and_translates():
    assert i18n.tr("{ip} is controlling your PC", lang="pt-BR", ip="10.0.0.2") == "10.0.0.2 está controlando seu PC"
    assert i18n.tr("{ip} is controlling your PC", lang="en", ip="10.0.0.2") == "10.0.0.2 is controlling your PC"
    assert i18n.tr("not in the catalog", lang="pt-BR") == "not in the catalog"
