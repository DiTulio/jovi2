const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { validarPacote } = require('../integracao.js');
const exemplo = JSON.parse(fs.readFileSync(path.join(__dirname, '../../exemplos/demonstracao.json'), 'utf8'));
const copiar = valor => JSON.parse(JSON.stringify(valor));

class Elemento {
  constructor(tag = 'div') {
    this.tagName = tag;
    this.children = [];
    this.handlers = {};
    this.hidden = false;
    this.disabled = false;
    this._text = '';
    this.classes = new Set();
    this.classList = {
      contains: valor => this.classes.has(valor),
      toggle: (valor, ligado) => ligado ? this.classes.add(valor) : this.classes.delete(valor)
    };
  }
  set textContent(valor) { this._text = String(valor); this.children = []; }
  get textContent() { return this._text + this.children.map(item => item.textContent).join('\n'); }
  append(...itens) { this.children.push(...itens); }
  replaceChildren(...itens) { this._text = ''; this.children = itens; }
  insertBefore(item, antes) { this.children.splice(Math.max(0, this.children.indexOf(antes)), 0, item); }
  addEventListener(nome, handler) { this.handlers[nome] = handler; }
  click() { if (this.handlers.click) return this.handlers.click(); }
}

function ambiente(memoria = new Map()) {
  const ids = Object.fromEntries(['python-status', 'python-content', 'python-clear', 'python-view',
    'python-home-summary', 'python-file', 'python-back', 's-python'].map(id => [id, new Elemento()]));
  const home = new Elemento();
  const scroll = new Elemento();
  scroll.append(ids['python-content']);
  const importar = [new Elemento('button'), new Elemento('button')];
  const sandbox = {
    module: { exports: {} }, URL, console, confirm: () => true,
    localStorage: { getItem: chave => memoria.get(chave) ?? null,
      setItem: (chave, valor) => memoria.set(chave, valor), removeItem: chave => memoria.delete(chave) },
    goTo: () => ids['s-python'].classes.add('active'), goBack: () => ids['s-python'].classes.delete('active'),
    document: { getElementById: id => ids[id], createElement: tag => new Elemento(tag),
      querySelectorAll: () => importar,
      querySelector: seletor => seletor === '.python-home-card' ? home : scroll }
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../integracao.js'), 'utf8'), sandbox);
  async function enviar(texto, size = Buffer.byteLength(texto)) {
    ids['python-file'].files = [{ size, text: async () => texto }];
    await ids['python-file'].handlers.change();
  }
  return { ids, enviar, memoria };
}

(async () => {
  assert.equal(validarPacote(exemplo), exemplo);
  for (const alterar of [
    p => p.versao_integracao = 1,
    p => p.perfil.modo_estudo = 'sim',
    p => p.perfil.simulados[0].acertos = 5,
    p => p.perfil.anotacoes[0].data = 'inválida',
    p => p.perfil.materias.Matemática['Geometria Plana'].flashcards[0][2][0] = -1
  ]) {
    const errado = copiar(exemplo); alterar(errado);
    assert.throws(() => validarPacote(errado));
  }
  const novo = copiar(exemplo);
  novo.perfil.materias.Biologia = { Células: { flashcards: [], questoes: [] } };
  assert.equal(validarPacote(novo), novo);
  const a = ambiente();
  await a.enviar(JSON.stringify(exemplo));
  assert.match(a.ids['python-content'].textContent, /3 acertos · 1 erros · 75%/);
  assert.match(a.ids['python-content'].textContent, /1\/1 acertos · 100%/);
  assert.match(a.ids['python-content'].textContent, /DADOS FICTÍCIOS/);
  assert.match(a.ids['python-status'].textContent, /sucesso/);
  const anterior = a.ids['python-content'].textContent;
  await a.enviar('{inválido');
  assert.match(a.ids['python-status'].textContent, /inválido/);
  assert.equal(a.ids['python-content'].textContent, anterior);
  await a.enviar('{}', 6 * 1024 * 1024);
  assert.match(a.ids['python-status'].textContent, /5 MB/);
  assert.equal(a.ids['python-content'].textContent, anterior);
  const b = ambiente(a.memoria);
  assert.equal(b.ids['python-content'].textContent, anterior);
  const muitos = copiar(exemplo);
  muitos.perfil.anotacoes = Array.from({ length: 12 }, (_, i) => ({ ...exemplo.perfil.anotacoes[0], texto: `Registro ${i}` }));
  await b.enviar(JSON.stringify(muitos));
  const secao = b.ids['python-content'].children.find(item => item.children[0]?.textContent === 'Anotações (12)');
  assert.equal(secao.children[1].children.length, 10);
  secao.children[2].children[2].click();
  assert.equal(secao.children[1].children.length, 2);
  await b.ids['python-clear'].click();
  assert.equal(a.memoria.size, 0);
  assert.match(b.ids['python-content'].textContent, /Importe um JSON/);
  const c = ambiente();
  const dadosTexto = copiar(exemplo);
  dadosTexto.perfil.anotacoes[0].texto = '<img src=x onerror="alert(1)">';
  await c.enviar(JSON.stringify(dadosTexto));
  assert.match(c.ids['python-content'].textContent, /<img src=x/);
  console.log('OK: contrato, rejeição de dados inválidos, catálogo flexível, importação real do JSON Python, placares, limite de tamanho, preservação após erro, armazenamento, paginação e remoção (DOM simulado).');
})().catch(erro => { console.error(erro); process.exitCode = 1; });
