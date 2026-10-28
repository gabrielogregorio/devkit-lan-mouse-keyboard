/*
 * Page strings. English is the source text and the key; PT_BR holds the Brazilian Portuguese line.
 * The language comes from ?lang=en|pt-BR or else from the browser's first preferred language:
 * pt* shows pt-BR, anything else shows English. tests/frontend/i18n.test.mjs fails on a missing
 * line, on different {placeholders} or on a line that is no longer used.
 */
export const PT_BR = {
  'LAN Mouse & Keyboard': 'LAN Mouse & Keyboard',
  'Connecting…': 'Conectando…',
  'Connected': 'Conectado',
  'Reconnecting…': 'Reconectando…',
  '<strong>Touchpad</strong> · drag to move · tap to click · 2 fingers scroll<br>hold a button and move here = drag / select':
    '<strong>Touchpad</strong> · arraste move · toque clica · 2 dedos rolam<br>segure um botão e mova aqui = arrastar / selecionar',
  'Left click': 'Clique Esquerdo',
  'Right click': 'Clique Direito',
};

const isPortuguese = (language) => /^pt([-_]|$)/i.test(language || '');

export function detectLanguage(search = '', languages = []) {
  const forced = new URLSearchParams(search).get('lang');
  if (forced) {
    return isPortuguese(forced) ? 'pt-BR' : 'en';
  }
  return isPortuguese(languages[0]) ? 'pt-BR' : 'en';
}

export const fill = (text, values = {}) =>
  text.replace(/\{(\w+)\}/g, (match, name) => (name in values ? String(values[name]) : match));

export const translator = (language) => (text, values) =>
  fill(language === 'pt-BR' ? (PT_BR[text] ?? text) : text, values);
