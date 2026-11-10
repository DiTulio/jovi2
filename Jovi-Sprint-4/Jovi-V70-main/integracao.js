(() => {
  'use strict';

  const CHAVE = 'jovi.python.v2';
  const LIMITE = 5 * 1024 * 1024;
  const TAMANHO_PAGINA = 10;
  let pacoteAtual = null;

  function exigir(condicao, mensagem) {
    if (!condicao) throw new Error(mensagem || 'O arquivo contém dados inválidos.');
  }

  function objeto(valor) {
    return valor !== null && typeof valor === 'object' && !Array.isArray(valor);
  }

  function texto(valor) {
    return typeof valor === 'string' && valor.trim().length > 0;
  }

  function natural(valor) {
    return Number.isSafeInteger(valor) && valor >= 0;
  }

  function dataValida(valor) {
    return texto(valor) && Number.isFinite(Date.parse(valor));
  }

  function validarPacote(pacote) {
    exigir(objeto(pacote) && pacote.sistema === 'Jovi V70' && pacote.versao_integracao === 2,
      'Selecione o JSON gerado pela opção 7 do Python (formato v2).');
    exigir(texto(pacote.usuario) && /^[a-z0-9_]{3,30}$/.test(pacote.usuario));
    exigir(dataValida(pacote.exportado_em));
    const perfil = pacote.perfil;
    exigir(objeto(perfil) && typeof perfil.modo_estudo === 'boolean');
    exigir(objeto(perfil.materias) && Object.keys(perfil.materias).length > 0);
    for (const [materia, topicos] of Object.entries(perfil.materias)) {
      exigir(texto(materia) && objeto(topicos) && Object.keys(topicos).length > 0);
      for (const [topico, conteudo] of Object.entries(topicos)) {
        exigir(texto(topico) && objeto(conteudo));
        exigir(Array.isArray(conteudo.flashcards) && Array.isArray(conteudo.questoes));
        for (const card of conteudo.flashcards) {
          exigir(Array.isArray(card) && card.length === 3 && texto(card[0]) && texto(card[1]));
          exigir(Array.isArray(card[2]) && card[2].length === 2 && card[2].every(natural));
        }
        for (const questao of conteudo.questoes) {
          exigir(Array.isArray(questao) && questao.length === 3 && texto(questao[0]));
          exigir(Array.isArray(questao[1]) && questao[1].length >= 2 && questao[1].every(texto));
          exigir(natural(questao[2]) && questao[2] < questao[1].length);
        }
      }
    }
    for (const tipo of ['anotacoes', 'simulados', 'pesquisas']) {
      exigir(Array.isArray(perfil[tipo]));
      for (const registro of perfil[tipo]) {
        exigir(objeto(registro) && dataValida(registro.data));
        if (tipo === 'pesquisas') {
          exigir(['termo', 'titulo', 'resumo', 'url'].every(campo => texto(registro[campo])));
        } else {
          exigir(texto(registro.materia) && texto(registro.topico));
          if (tipo === 'anotacoes') exigir(texto(registro.texto));
          else exigir(natural(registro.acertos) && natural(registro.total) &&
            registro.total > 0 && registro.acertos <= registro.total);
        }
      }
    }
    return pacote;
  }

  function elemento(tag, classe, conteudo) {
    const item = document.createElement(tag);
    if (classe) item.className = classe;
    if (conteudo !== undefined) item.textContent = conteudo;
    return item;
  }

  function formatarData(valor) {
    return new Date(valor).toLocaleString('pt-BR');
  }

  function mensagem(textoMensagem, erro = false) {
    const alvo = document.getElementById('python-status');
    alvo.textContent = textoMensagem;
    alvo.classList.toggle('python-error', erro);
  }

  function renderizarRegistro(registro, tipo) {
    const item = elemento('article', 'python-record');
    item.append(elemento('p', 'python-date', formatarData(registro.data)));
    if (tipo === 'pesquisas') {
      item.append(elemento('h3', '', registro.titulo), elemento('p', 'python-text', registro.resumo));
      try {
        const url = new URL(registro.url);
        if (url.protocol === 'https:' && url.hostname === 'pt.wikipedia.org') {
          const link = elemento('a', 'python-link', 'Ler fonte na Wikipédia ↗');
          link.href = url.href;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          item.append(link);
        }
      } catch {}
    } else {
      item.append(elemento('h3', '', `${registro.materia} · ${registro.topico}`));
      item.append(elemento('p', 'python-text', tipo === 'anotacoes' ? registro.texto :
        `${registro.acertos}/${registro.total} acertos · ${Math.round(registro.acertos / registro.total * 100)}%`));
    }
    return item;
  }

  function listaPaginada(titulo, registros, criarItem) {
    const secao = elemento('section', 'python-section');
    secao.append(elemento('h2', '', `${titulo} (${registros.length})`));
    const lista = elemento('div', 'python-list');
    const controles = elemento('div', 'python-pagination');
    const anterior = elemento('button', 'python-btn secondary', 'Anterior');
    const proxima = elemento('button', 'python-btn secondary', 'Próxima');
    const indicador = elemento('span', 'python-date');
    anterior.type = proxima.type = 'button';
    let pagina = 0;
    function mostrar() {
      lista.replaceChildren();
      if (!registros.length) lista.append(elemento('p', 'python-muted', 'Nenhum registro salvo.'));
      registros.slice(pagina * TAMANHO_PAGINA, (pagina + 1) * TAMANHO_PAGINA)
        .forEach(registro => lista.append(criarItem(registro)));
      anterior.disabled = pagina === 0;
      proxima.disabled = (pagina + 1) * TAMANHO_PAGINA >= registros.length;
      indicador.textContent = `${pagina + 1}/${Math.max(1, Math.ceil(registros.length / TAMANHO_PAGINA))}`;
      controles.hidden = registros.length <= TAMANHO_PAGINA;
    }
    anterior.addEventListener('click', () => { pagina--; mostrar(); });
    proxima.addEventListener('click', () => { pagina++; mostrar(); });
    controles.append(anterior, indicador, proxima);
    secao.append(lista, controles);
    mostrar();
    return secao;
  }

  function renderizar() {
    const conteudo = document.getElementById('python-content');
    conteudo.replaceChildren();
    document.getElementById('python-clear').hidden = !pacoteAtual;
    document.getElementById('python-view').disabled = !pacoteAtual;
    const resumo = document.getElementById('python-home-summary');
    if (!pacoteAtual) {
      resumo.textContent = 'Importe seu progresso, anotações e pesquisas salvos no Python.';
      conteudo.append(elemento('p', 'python-muted', 'Importe um JSON para consultar seu progresso.'));
      return;
    }
    const { usuario, exportado_em, perfil } = pacoteAtual;
    resumo.textContent = `${usuario} · ${perfil.simulados.length} simulado(s) · ${perfil.anotacoes.length} anotação(ões)`;
    conteudo.append(elemento('h2', 'python-user', usuario));
    conteudo.append(elemento('p', 'python-muted', `Exportado em ${formatarData(exportado_em)}`));
    conteudo.append(elemento('p', 'python-muted', `Modo de estudo no Python: ${perfil.modo_estudo ? 'ativado' : 'desativado'} (simulação).`));
    const cards = [];
    for (const [materia, topicos] of Object.entries(perfil.materias)) {
      for (const [topico, dados] of Object.entries(topicos)) {
        dados.flashcards.forEach(card => cards.push({ materia, topico, card }));
      }
    }
    conteudo.append(listaPaginada('Flashcards', cards, ({ materia, topico, card }) => {
      const item = elemento('article', 'python-record');
      const total = card[2][0] + card[2][1];
      item.append(elemento('p', 'python-date', `${materia} · ${topico}`));
      item.append(elemento('h3', '', card[0]));
      item.append(elemento('p', 'python-text', card[1]));
      item.append(elemento('p', 'python-score', `${card[2][0]} acertos · ${card[2][1]} erros · ${total ? Math.round(card[2][0] / total * 100) + '%' : 'sem tentativas'}`));
      return item;
    }));
    for (const [tipo, titulo] of [['simulados', 'Simulados'], ['anotacoes', 'Anotações'], ['pesquisas', 'Pesquisas da Wikipédia']]) {
      conteudo.append(listaPaginada(titulo, [...perfil[tipo]].reverse(), item => renderizarRegistro(item, tipo)));
    }
  }

  async function importarArquivo(arquivo) {
    if (!arquivo) return;
    const status = document.getElementById('python-status');
    const tela = document.getElementById('s-python');
    if (!tela.classList.contains('active')) document.querySelector('.python-home-card').append(status);
    try {
      exigir(arquivo.size <= LIMITE, 'O arquivo deve ter no máximo 5 MB.');
      const novo = validarPacote(JSON.parse(await arquivo.text()));
      pacoteAtual = novo;
      renderizar();
      let aviso = '';
      try { localStorage.setItem(CHAVE, JSON.stringify(novo)); }
      catch { aviso = ' O navegador não permitiu guardar a cópia; importe novamente na próxima visita.'; }
      document.querySelector('#s-python .python-scroll').insertBefore(document.getElementById('python-status'), document.getElementById('python-content'));
      mensagem(`Dados de ${novo.usuario} importados com sucesso.${aviso}`);
      goTo('s-python');
    } catch (erro) {
      mensagem(erro instanceof SyntaxError ? 'Arquivo JSON inválido. Exporte novamente pela opção 7 do Python.' : erro.message, true);
    }
  }

  function iniciar() {
    const seletor = document.getElementById('python-file');
    document.querySelectorAll('[data-python-import]').forEach(botao => {
      botao.addEventListener('click', () => seletor.click());
    });
    seletor.addEventListener('change', async () => {
      await importarArquivo(seletor.files[0]);
      seletor.value = '';
    });
    document.getElementById('python-view').addEventListener('click', () => goTo('s-python'));
    document.getElementById('python-back').addEventListener('click', () => goBack());
    document.getElementById('python-clear').addEventListener('click', () => {
      if (!confirm('Remover a cópia importada deste navegador? O arquivo do Python será preservado.')) return;
      try { localStorage.removeItem(CHAVE); }
      catch { mensagem('Não foi possível remover a cópia do navegador.', true); return; }
      pacoteAtual = null;
      renderizar();
      mensagem('Cópia removida do navegador.');
    });
    try {
      const salvo = localStorage.getItem(CHAVE);
      if (salvo && salvo.length <= LIMITE) pacoteAtual = validarPacote(JSON.parse(salvo));
    } catch { mensagem('A cópia anterior não pôde ser carregada. Importe um JSON válido.', true); }
    renderizar();
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = { validarPacote };
  if (typeof document !== 'undefined') iniciar();
})();
