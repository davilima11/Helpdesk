/*
 * Versão web do Bit: a mesma lógica de bot/agente.py, em JavaScript,
 * para rodar direto no navegador (GitHub Pages não roda Python).
 * Usa a mesma base: data/base_conhecimento.json.
 * O teste tests/test_versao_web.py confere que as duas versões dão o mesmo resultado.
 */
(function (global) {
  "use strict";

  const LIMIAR_ALTO = 0.55;
  const LIMIAR_BAIXO = 0.35;
  const PADRAO_PROTOCOLO = /\bCH-\d{1,6}\b/i;
  const NEGACOES = new Set(["nao", "nada", "nem", "sem", "nunca", "continua", "ainda"]);

  // mesma ordem de bot/privacidade.py (cartão antes de CPF)
  const PADROES_SENSIVEIS = [
    ["uma senha", /\bsenha\s*(?:é|eh|:|=|era|seria)\s*\S+/i],
    ["um código de verificação", /\b(?:c[oó]digo|token|2fa|verifica[cç][aã]o)\D{0,20}\d{4,8}\b/i],
    ["um número de cartão", /\b(?:\d[ -]?){15,16}\b/],
    ["um CPF", /\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b/],
  ];

  function encontrarDadoSensivel(texto) {
    for (const [tipo, padrao] of PADROES_SENSIVEIS) {
      if (padrao.test(texto || "")) return tipo;
    }
    return null;
  }

  function semAcento(texto) {
    return texto.normalize("NFD").replace(/\p{Mn}/gu, "");
  }

  function formatar(modelo, valores) {
    return modelo.replace(/\{(\w+)\}/g, (_, chave) => (chave in valores ? valores[chave] : ""));
  }

  function virgula(numero) {
    return numero.toFixed(2).replace(".", ",");
  }

  // ---------- TF-IDF igual ao TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4)) ----------
  function ngramas(texto) {
    const resultado = [];
    const limpo = texto.replace(/\s\s+/g, " ");
    for (const palavra of limpo.split(/\s+/).filter(Boolean)) {
      const w = " " + palavra + " ";
      for (let n = 2; n <= 4; n++) {
        let inicio = 0;
        resultado.push(w.slice(inicio, inicio + n));
        while (inicio + n < w.length) {
          inicio += 1;
          resultado.push(w.slice(inicio, inicio + n));
        }
        if (inicio === 0) break; // palavra curta conta uma vez só
      }
    }
    return resultado;
  }

  function contar(lista) {
    const contagem = new Map();
    for (const item of lista) contagem.set(item, (contagem.get(item) || 0) + 1);
    return contagem;
  }

  class Vetorizador {
    ajustar(frases) {
      const contagens = frases.map((f) => contar(ngramas(f)));
      const df = new Map();
      for (const c of contagens) for (const termo of c.keys()) df.set(termo, (df.get(termo) || 0) + 1);
      const n = frases.length;
      this.idf = new Map();
      for (const [termo, freq] of df) this.idf.set(termo, Math.log((1 + n) / (1 + freq)) + 1);
      return contagens.map((c) => this.pesar(c));
    }

    transformar(frase) {
      return this.pesar(contar(ngramas(frase)));
    }

    pesar(contagem) {
      const vetor = new Map();
      let soma = 0;
      for (const [termo, tf] of contagem) {
        const idf = this.idf.get(termo);
        if (idf === undefined) continue;
        const peso = tf * idf;
        vetor.set(termo, peso);
        soma += peso * peso;
      }
      const norma = Math.sqrt(soma);
      if (norma > 0) for (const [termo, peso] of vetor) vetor.set(termo, peso / norma);
      return vetor;
    }
  }

  function cosseno(a, b) {
    const [menor, maior] = a.size < b.size ? [a, b] : [b, a];
    let total = 0;
    for (const [termo, peso] of menor) {
      const outro = maior.get(termo);
      if (outro !== undefined) total += peso * outro;
    }
    return total;
  }

  // ---------- chamados (no navegador ficam no localStorage, só com o tema) ----------
  class Chamados {
    constructor(armazenamento) {
      this.armazenamento = armazenamento || null;
      this.lista = this.carregar();
    }

    carregar() {
      try {
        const salvo = this.armazenamento && this.armazenamento.getItem("bit-chamados");
        return salvo ? JSON.parse(salvo) : [];
      } catch (erro) {
        return [];
      }
    }

    salvar() {
      try {
        if (this.armazenamento) this.armazenamento.setItem("bit-chamados", JSON.stringify(this.lista));
      } catch (erro) {
        /* sem armazenamento, os chamados ficam só nesta aba */
      }
    }

    abrir(tema, resumo, prioridade) {
      const agora = new Date();
      const doisDigitos = (x) => String(x).padStart(2, "0");
      const data = `${doisDigitos(agora.getDate())}/${doisDigitos(agora.getMonth() + 1)}/${agora.getFullYear()} ` +
        `${doisDigitos(agora.getHours())}:${doisDigitos(agora.getMinutes())}`;
      const id = this.lista.length + 1;
      this.lista.push({ id, tema, resumo, prioridade: prioridade || "normal", status: "aberto", data });
      this.salvar();
      return "CH-" + String(id).padStart(4, "0");
    }

    consultar(protocolo) {
      const numero = parseInt(protocolo.toUpperCase().replace("CH-", ""), 10);
      const chamado = this.lista.find((c) => c.id === numero);
      return chamado ? { ...chamado, protocolo: protocolo.toUpperCase() } : null;
    }
  }

  // ---------- memória: curta e média, sem longa ----------
  class Memoria {
    constructor() {
      this.TAMANHO_CURTA = 6;
      this.limpar();
    }
    registrar(autor, texto) {
      this.curta.push([autor, texto]);
      if (this.curta.length > this.TAMANHO_CURTA) this.curta.shift();
    }
    definirProblema(intencao) { this.problemaAtual = intencao; }
    limparMedia() { this.problemaAtual = null; }
    limpar() { this.curta = []; this.limparMedia(); }
  }

  // ---------- o agente, nas 4 camadas ----------
  class Agente {
    constructor(base, armazenamento) {
      this.intencoes = base.intencoes;
      this.msgs = base.mensagens;
      this.sinonimos = base.sinonimos;
      this.ofensas = base.palavras_ofensivas;
      this.memoria = new Memoria();
      this.chamados = new Chamados(armazenamento);
      this.treinar();
    }

    treinar() {
      const frases = [];
      this.rotulos = [];
      for (const [nome, dados] of Object.entries(this.intencoes)) {
        for (const exemplo of dados.exemplos) {
          frases.push(this.normalizar(exemplo));
          this.rotulos.push(nome);
        }
      }
      this.vetorizador = new Vetorizador();
      this.matriz = this.vetorizador.ajustar(frases);
    }

    normalizar(texto) {
      let limpo = semAcento(texto.toLowerCase());
      limpo = limpo.replace(/[^\p{L}\p{N}_\s-]/gu, " ");
      return limpo.split(/\s+/).filter(Boolean).map((p) => (p in this.sinonimos ? this.sinonimos[p] : p)).join(" ");
    }

    // 1. perceptiva
    perceber(texto) {
      const original = (texto || "").trim();
      const protocolo = original.match(PADRAO_PROTOCOLO);
      return {
        original,
        normalizado: this.normalizar(original),
        dadoSensivel: encontrarDadoSensivel(original),
        protocolo: protocolo ? protocolo[0].toUpperCase() : null,
      };
    }

    // 2. cognitiva
    entender(percepcao) {
      if (!percepcao.normalizado || percepcao.dadoSensivel) return [null, 0];
      const vetor = this.vetorizador.transformar(percepcao.normalizado);
      let melhor = 0;
      let maior = -1;
      this.matriz.forEach((linha, i) => {
        const similaridade = cosseno(vetor, linha);
        if (similaridade > maior) { maior = similaridade; melhor = i; }
      });
      let intencao = this.rotulos[melhor];
      const palavras = percepcao.normalizado.split(" ");
      if (intencao === "agradecimento" && palavras.some((p) => NEGACOES.has(p))) intencao = "nao_resolveu";
      return [intencao, Math.max(maior, 0)];
    }

    // 3. decisória
    decidir(percepcao, intencao, confianca) {
      if (percepcao.dadoSensivel) return "bloquear_dado";
      if (percepcao.protocolo) return "consultar_chamado";
      if (confianca < LIMIAR_BAIXO) return this.temOfensa(percepcao.normalizado) ? "acalmar" : "nao_entendi";
      if (intencao === "seguranca") return "escalar";
      if ((intencao === "nao_resolveu" || intencao === "abrir_chamado") && confianca < LIMIAR_ALTO) return "nao_entendi";
      if (intencao === "nao_resolveu") return this.memoria.problemaAtual ? "abrir_chamado" : "perguntar_problema";
      if (intencao === "abrir_chamado") return "abrir_chamado";
      if (confianca < LIMIAR_ALTO) return "responder_com_duvida";
      return "responder";
    }

    temOfensa(texto) {
      return this.ofensas.some((p) => new RegExp(`\\b${p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`).test(texto));
    }

    // 4. executiva
    executar(acao, intencao) {
      const dados = this.intencoes[intencao] || {};
      let protocolo = null;
      let texto;
      if (acao === "nao_entendi") texto = this.msgs.nao_entendi;
      else if (acao === "acalmar") texto = this.msgs.acalmar;
      else if (acao === "perguntar_problema") texto = this.msgs.perguntar_problema;
      else if (acao === "escalar") {
        protocolo = this.chamados.abrir(dados.tema, "Possível incidente relatado no chat.", "alta");
        texto = formatar(dados.resposta, { protocolo });
        this.memoria.limparMedia();
      } else if (acao === "abrir_chamado") {
        const problema = this.memoria.problemaAtual;
        const tema = problema ? this.intencoes[problema].tema : "não informado";
        const resumo = problema
          ? `Usuário seguiu o passo a passo do Bit para ${tema} e não resolveu.`
          : "Usuário pediu para abrir chamado sem dizer o problema.";
        protocolo = this.chamados.abrir(tema, resumo);
        texto = formatar(this.msgs.chamado_aberto, { protocolo, tema });
        this.memoria.limparMedia();
      } else {
        texto = dados.resposta;
        if (acao === "responder_com_duvida") texto = formatar(this.msgs.com_duvida, { tema: dados.tema }) + texto;
        if (dados.tecnica) this.memoria.definirProblema(intencao);
        if (intencao === "agradecimento") this.memoria.limparMedia();
      }
      return [texto, protocolo];
    }

    consultar(protocolo) {
      const chamado = this.chamados.consultar(protocolo);
      if (!chamado) return formatar(this.msgs.chamado_nao_encontrado, { protocolo });
      return formatar(this.msgs.chamado_encontrado, chamado);
    }

    explicar(acao, intencao, confianca) {
      const tema = (this.intencoes[intencao] || {}).tema || "nenhum";
      const conf = virgula(confianca);
      const alto = virgula(LIMIAR_ALTO);
      const baixo = virgula(LIMIAR_BAIXO);
      return {
        bloquear_dado: "A mensagem parecia ter um dado sensível, então foi descartada antes de qualquer análise.",
        consultar_chamado: "Encontrei um número de protocolo na mensagem e consultei o chamado.",
        nao_entendi: `O assunto mais parecido foi '${tema}', mas a confiança (${conf}) ficou abaixo do mínimo (${baixo}). Preferi admitir que não sei a chutar.`,
        acalmar: "Não identifiquei um problema técnico e a mensagem tinha uma palavra ofensiva.",
        escalar: `Identifiquei '${tema}' (confiança ${conf}). Segurança é escalada na hora, mesmo com dúvida.`,
        perguntar_problema: "Você disse que não resolveu, mas eu ainda não sabia qual era o problema.",
        abrir_chamado: "Abri um chamado para uma pessoa do suporte assumir.",
        responder_com_duvida: `Identifiquei '${tema}', mas com confiança média (${conf}). Respondi avisando que posso ter entendido errado.`,
        responder: `Identifiquei '${tema}' com confiança ${conf} (acima de ${alto}).`,
      }[acao];
    }

    responder(texto) {
      const percepcao = this.perceber(texto);
      const [intencao, confianca] = this.entender(percepcao);
      const acao = this.decidir(percepcao, intencao, confianca);
      let resposta;
      let protocolo;
      if (acao === "bloquear_dado") {
        resposta = formatar(this.msgs.dado_sensivel, { tipo: percepcao.dadoSensivel });
        protocolo = null;
      } else if (acao === "consultar_chamado") {
        resposta = this.consultar(percepcao.protocolo);
        protocolo = percepcao.protocolo;
      } else {
        [resposta, protocolo] = this.executar(acao, intencao);
      }
      // a mensagem com dado sensível nunca entra na memória
      if (acao !== "bloquear_dado") this.memoria.registrar("usuario", percepcao.original);
      this.memoria.registrar("bit", resposta);
      return {
        texto: resposta,
        intencao,
        confianca: Math.round(confianca * 100) / 100,
        acao,
        protocolo,
        explicacao: this.explicar(acao, intencao, confianca),
      };
    }
  }

  const Bit = { Agente, encontrarDadoSensivel, LIMIAR_ALTO, LIMIAR_BAIXO };
  if (typeof module !== "undefined" && module.exports) module.exports = Bit;
  else global.Bit = Bit;
})(typeof globalThis !== "undefined" ? globalThis : this);
