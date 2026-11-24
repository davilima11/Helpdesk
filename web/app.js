/* Interface da versão web do Bit: abas, conversa e leitor da documentação. */
(function () {
  "use strict";

  const $ = (seletor, raiz = document) => raiz.querySelector(seletor);
  const reduzirMovimento = window.matchMedia("(prefers-reduced-motion: reduce)");

  // ---------- abas ----------
  const abas = [...document.querySelectorAll('[role="tab"]')];

  function selecionarAba(aba, focar) {
    for (const a of abas) {
      const ativa = a === aba;
      a.setAttribute("aria-selected", String(ativa));
      a.tabIndex = ativa ? 0 : -1;
      document.getElementById(a.dataset.painel).hidden = !ativa;
    }
    if (focar) aba.focus();
    if (aba.id === "aba-docs" && !docAtual) abrirDoc("1-especificacao");
  }

  abas.forEach((aba, i) => {
    aba.addEventListener("click", () => selecionarAba(aba));
    aba.addEventListener("keydown", (evento) => {
      const destino = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: abas.length - 1 }[evento.key];
      if (destino === undefined) return;
      evento.preventDefault();
      selecionarAba(abas[(destino + abas.length) % abas.length], true);
    });
  });

  // ---------- conversa ----------
  const log = $("#mensagens");
  const form = $("#form-chat");
  const campo = $("#campo");
  let agente = null;

  function armazenamentoSeguro() {
    try {
      window.localStorage.getItem("bit-teste");
      return window.localStorage;
    } catch (erro) {
      return null;
    }
  }

  function textoDoBit(texto) {
    const fragmento = document.createDocumentFragment();
    let lista = null;
    for (const linha of texto.split("\n")) {
      const item = linha.match(/^\d+\.\s+(.*)$/);
      if (item) {
        if (!lista) fragmento.append((lista = document.createElement("ol")));
        const li = document.createElement("li");
        li.textContent = item[1];
        lista.append(li);
      } else {
        lista = null;
        if (linha.trim()) {
          const p = document.createElement("p");
          p.textContent = linha;
          fragmento.append(p);
        }
      }
    }
    return fragmento;
  }

  function rolarParaFim() {
    log.scrollTo({ top: log.scrollHeight, behavior: reduzirMovimento.matches ? "auto" : "smooth" });
  }

  function mostrarMensagem(autor, texto, resultado) {
    const mensagem = document.createElement("div");
    mensagem.className = autor === "bit" ? "msg msg-bit" : "msg msg-voce";
    const quem = document.createElement("span");
    quem.className = "quem";
    quem.textContent = autor === "bit" ? "Bit" : "Você";
    const corpo = document.createElement("div");
    corpo.className = "corpo";

    if (autor === "bit") {
      corpo.append(textoDoBit(texto));
    } else {
      const p = document.createElement("p");
      p.textContent = texto;
      corpo.append(p);
    }

    if (resultado) {
      const detalhes = document.createElement("details");
      detalhes.className = "porque";
      const resumo = document.createElement("summary");
      resumo.textContent = "Por que o Bit respondeu isso?";
      const explicacao = document.createElement("p");
      explicacao.textContent = resultado.explicacao;
      detalhes.append(resumo, explicacao);
      corpo.append(detalhes);
    }

    mensagem.append(quem, corpo);
    log.append(mensagem);
    rolarParaFim();
    return corpo;
  }

  function removerFeedback() {
    log.querySelectorAll(".feedback").forEach((barra) => barra.remove());
  }

  function oferecerFeedback(corpo) {
    const barra = document.createElement("div");
    barra.className = "feedback";
    for (const [rotulo, frase] of [["Resolveu", "deu certo, obrigado"], ["Não resolveu", "não resolveu"]]) {
      const botao = document.createElement("button");
      botao.type = "button";
      botao.textContent = rotulo;
      botao.addEventListener("click", () => enviar(frase));
      barra.append(botao);
    }
    corpo.append(barra);
    rolarParaFim();
  }

  function enviar(texto) {
    if (!agente || !texto.trim()) return;
    removerFeedback();
    const resultado = agente.responder(texto);
    if (resultado.acao === "bloquear_dado") {
      // a mensagem com dado sensível nem aparece na tela
      const corpo = mostrarMensagem("voce", "[mensagem apagada: tinha um dado sensível]");
      corpo.classList.add("apagada");
    } else {
      mostrarMensagem("voce", texto);
    }
    const corpo = mostrarMensagem("bit", resultado.texto, resultado);
    const intencao = agente.intencoes[resultado.intencao];
    if ((resultado.acao === "responder" || resultado.acao === "responder_com_duvida") && intencao && intencao.tecnica) {
      oferecerFeedback(corpo);
    }
  }

  function iniciarConversa() {
    log.replaceChildren();
    if (agente) agente.memoria.limpar();
    mostrarMensagem("bit", agente ? agente.msgs.inicial : "Carregando...");
  }

  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    const texto = campo.value;
    campo.value = "";
    enviar(texto);
    campo.focus();
  });

  document.querySelectorAll(".sugestoes button").forEach((botao) => {
    botao.addEventListener("click", () => enviar(botao.textContent));
  });

  $("#limpar").addEventListener("click", () => {
    iniciarConversa();
    campo.focus();
  });

  fetch("data/base_conhecimento.json")
    .then((resposta) => {
      if (!resposta.ok) throw new Error(resposta.status);
      return resposta.json();
    })
    .then((base) => {
      agente = new Bit.Agente(base, armazenamentoSeguro());
      iniciarConversa();
    })
    .catch(() => {
      log.replaceChildren();
      mostrarMensagem("bit", "Não consegui carregar a base de conhecimento. Se você abriu o arquivo direto do computador, rode um servidor local na pasta do projeto (python -m http.server) e abra http://localhost:8000.");
      form.querySelectorAll("input, button").forEach((el) => (el.disabled = true));
    });

  // ---------- documentação ----------
  const visor = $("#visor");
  const linksDocs = [...document.querySelectorAll("[data-doc]")];
  const DOCS = linksDocs.map((link) => link.dataset.doc);
  let docAtual = null;

  // o GitHub desenha o diagrama mermaid sozinho; aqui o fluxo (que é linear) vira uma lista de caixas
  function desenharFluxo(codigo) {
    const nos = new Map();
    for (const achado of codigo.matchAll(/(\w+)\s*\[\s*"?([^"\]]+?)"?\s*\]/g)) {
      if (!nos.has(achado[1])) nos.set(achado[1], achado[2]);
    }
    const lista = document.createElement("ol");
    lista.className = "fluxo";
    for (const rotulo of nos.values()) {
      const item = document.createElement("li");
      rotulo.split(/<br\s*\/?>/i).forEach((parte, i) => {
        const el = document.createElement(i === 0 ? "strong" : "span");
        el.textContent = parte;
        item.append(el);
      });
      lista.append(item);
    }
    return lista;
  }

  async function abrirDoc(id) {
    if (!DOCS.includes(id)) id = DOCS[0];
    docAtual = id;
    linksDocs.forEach((link) => {
      if (link.dataset.doc === id) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    try {
      const resposta = await fetch(`docs/${id}.md`);
      if (!resposta.ok) throw new Error(resposta.status);
      const texto = await resposta.text();
      if (docAtual !== id) return; // a pessoa já clicou em outro documento
      visor.innerHTML = marked.parse(texto);
    } catch (erro) {
      visor.textContent = "Não consegui carregar este documento.";
      return;
    }
    visor.querySelectorAll("table").forEach((tabela) => {
      const caixa = document.createElement("div");
      caixa.className = "tabela";
      tabela.before(caixa);
      caixa.append(tabela);
    });
    visor.querySelectorAll("code.language-mermaid").forEach((codigo) => {
      codigo.parentElement.replaceWith(desenharFluxo(codigo.textContent));
    });
    visor.querySelectorAll("a[href]").forEach((link) => {
      const href = link.getAttribute("href");
      const outroDoc = href.match(/^(?:\.\/)?([\w-]+)\.md$/);
      if (outroDoc && DOCS.includes(outroDoc[1])) link.setAttribute("href", `#doc/${outroDoc[1]}`);
      else if (/^https?:/.test(href)) { link.target = "_blank"; link.rel = "noopener"; }
    });
  }

  function seguirEndereco() {
    const doc = location.hash.match(/^#doc\/([\w-]+)$/);
    if (!doc) return;
    docAtual = doc[1]; // evita que a aba abra o primeiro documento por cima
    selecionarAba($("#aba-docs"));
    abrirDoc(doc[1]).then(() => {
      visor.focus({ preventScroll: true });
      visor.scrollIntoView({ block: "start", behavior: reduzirMovimento.matches ? "auto" : "smooth" });
    });
  }

  window.addEventListener("hashchange", seguirEndereco);
  seguirEndereco();
})();
