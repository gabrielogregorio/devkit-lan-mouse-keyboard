import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { PT_BR, detectLanguage, fill, translator } from '../../web/i18n.js';

const html = readFileSync(new URL('../../web/index.html', import.meta.url), 'utf8');
const app = readFileSync(new URL('../../web/app.js', import.meta.url), 'utf8');

// Every English string the page translates: t("...") calls in app.js and data-i18n / data-i18n-html elements.
const usedStrings = new Set([
  ...[...app.matchAll(/\bt\("((?:[^"\\]|\\.)*)"/g)].map((match) => match[1]),
  ...[...html.matchAll(/<(\w+)\b[^>]*\sdata-i18n(?:-html)?(?:\s[^>]*)?>([\s\S]*?)<\/\1>/g)]
    .map((match) => match[2].trim().replace(/&amp;/g, '&')),
]);

const placeholders = (text) => [...text.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort();

test('the page uses translated strings', () => {
  assert.ok(usedStrings.size >= 7, `found only ${usedStrings.size}`);
  assert.ok(usedStrings.has('Connected'));
  assert.ok(usedStrings.has('Left click'));
});

test('every string on the page has a pt-BR line', () => {
  const missing = [...usedStrings].filter((text) => !(text in PT_BR));
  assert.deepEqual(missing, []);
});

test('pt-BR lines keep the same {placeholders}', () => {
  for (const [english, portuguese] of Object.entries(PT_BR)) {
    assert.deepEqual(placeholders(portuguese), placeholders(english), english);
  }
});

test('no pt-BR line is left unused', () => {
  const unused = Object.keys(PT_BR).filter((text) => !usedStrings.has(text));
  assert.deepEqual(unused, []);
});

test('language follows the first browser language: pt* is pt-BR, anything else English', () => {
  assert.equal(detectLanguage('', ['pt-BR', 'en']), 'pt-BR');
  assert.equal(detectLanguage('', ['pt']), 'pt-BR');
  assert.equal(detectLanguage('', ['pt-PT']), 'pt-BR');
  assert.equal(detectLanguage('', ['en-US', 'pt-BR']), 'en');
  assert.equal(detectLanguage('', ['es']), 'en');
  assert.equal(detectLanguage('', []), 'en');
});

test('?lang= overrides the browser', () => {
  assert.equal(detectLanguage('?lang=en', ['pt-BR']), 'en');
  assert.equal(detectLanguage('?lang=pt-BR', ['en-US']), 'pt-BR');
  assert.equal(detectLanguage('?lang=pt_BR', ['en-US']), 'pt-BR');
});

test('translator falls back to English', () => {
  assert.equal(translator('pt-BR')('Connected'), 'Conectado');
  assert.equal(translator('en')('Connected'), 'Connected');
  assert.equal(translator('pt-BR')('not in the catalog'), 'not in the catalog');
  assert.equal(fill('{a} and {b}', { a: 1 }), '1 and {b}');
});
