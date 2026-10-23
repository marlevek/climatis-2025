/**
 * Cópia local do widget AtendeSite, consultada em 23/10/2026.
 * Origem: https://api.atendesite.com.br/widget.js?v=2
 * Adaptação Climátis: data-saudacao tem precedência na abertura do chat e no balão.
 * A API, o contexto enviado por path e o restante do atendimento são os originais.
 * Ao atualizar esta cópia, preservar a leitura de data-saudacao em montarUI().
 */
/**
 * atende-ai — widget de chat flutuante
 *
 * Como instalar no site do cliente:
 *   <script src="https://api.atendesite.com.br/widget.js" data-tenant="climatis" defer></script>
 *
 * Site multilíngue: acrescentar data-lang="pt" | "en" | "es" na tag. Sem o
 * atributo, o widget cai no <html lang> da página e, se nem isso existir, em pt.
 *
 * O que faz:
 *  - Lê `data-tenant` do <script> e descobre o BACKEND_URL pela mesma origin do script
 *  - Busca /api/v1/config/<slug>/ → cores, whatsapp, saudação (contextual ao path)
 *  - Renderiza botão flutuante + painel de chat dentro de Shadow DOM (isolamento total)
 *  - POST /api/v1/buscar/ com a pergunta → mostra resposta + card do serviço + WhatsApp
 *
 * Princípios:
 *  - Vanilla JS, zero dependências
 *  - Shadow DOM para não vazar/herdar CSS do site
 *  - Falha silenciosa: erro nunca quebra o site do cliente
 *  - Acessível: foco no input ao abrir, ESC fecha, aria-labels
 */
(function () {
  "use strict";

  // ───────────────────────────────────────────────────────────────────────
  // Bootstrap: ler config do <script> e descobrir backend
  // ───────────────────────────────────────────────────────────────────────
  const scriptEl =
    document.currentScript ||
    document.querySelector('script[src*="widget.js"][data-tenant]');

  if (!scriptEl) {
    console.warn("[atende-ai] tag <script> não encontrada — abortando.");
    return;
  }

  const TENANT_SLUG = scriptEl.getAttribute("data-tenant");
  if (!TENANT_SLUG) {
    console.warn("[atende-ai] data-tenant ausente no <script> — abortando.");
    return;
  }

  // BACKEND_URL = origin do próprio script (api.atendesite.com.br, por ex).
  // Permite override por data-backend para casos de teste.
  const BACKEND_URL =
    scriptEl.getAttribute("data-backend") ||
    new URL(scriptEl.src, window.location.href).origin;

  // ── Customizações visuais via data-attributes (todas opcionais) ──────────
  // data-bottom="100"  → distância do bottom em px (default 20). Útil quando
  //                      o site já tem outro botão flutuante (WhatsApp etc).
  // data-side="left"   → joga pro canto esquerdo (default "right").
  // data-proativo="off"→ desativa o balãozinho que aparece sozinho após 4s.
  // data-lang="en"    → idioma da UI e da resposta da IA (default: <html lang>, senão pt).
  const POS_BOTTOM = parseInt(scriptEl.getAttribute("data-bottom") || "20", 10);
  const POS_SIDE = (scriptEl.getAttribute("data-side") || "right").toLowerCase() === "left" ? "left" : "right";
  const PROATIVO_LIGADO = (scriptEl.getAttribute("data-proativo") || "on").toLowerCase() !== "off";
  const PROATIVO_DELAY_MS = parseInt(scriptEl.getAttribute("data-proativo-delay") || "4000", 10);

  // ───────────────────────────────────────────────────────────────────────
  // Idioma (i18n)
  //
  // Mesma regra do backend (apps/core/idiomas.py): reduz "pt-BR"/"en_US"/
  // "es-419" à base e cai em pt no que não conhecemos. Idioma desconhecido
  // nunca quebra o widget — no pior caso o visitante vê português.
  // ───────────────────────────────────────────────────────────────────────
  const IDIOMAS_SUPORTADOS = ["pt", "en", "es"];
  const IDIOMA_PADRAO = "pt";

  function normalizarIdioma(valor) {
    if (!valor) return IDIOMA_PADRAO;
    const base = String(valor).trim().toLowerCase().replace(/_/g, "-").split("-")[0];
    return IDIOMAS_SUPORTADOS.indexOf(base) >= 0 ? base : IDIOMA_PADRAO;
  }

  // Precedência: data-lang > <html lang> > pt. O data-lang existe porque o
  // site pode servir /en/ com <html lang="pt-BR"> por descuido do template.
  const LANG = normalizarIdioma(
    scriptEl.getAttribute("data-lang") || document.documentElement.lang,
  );

  // Todas as strings de UI. A marca "atende-ai" não traduz.
  const TEXTOS = {
    pt: {
      abrirAtendimento: "Abrir atendimento",
      botao: "💬 Como podemos ajudar?",
      balaoAria: "Mensagem do atendente — clique para conversar",
      fecharMensagem: "Fechar mensagem",
      painelAria: (nome) => (nome ? `Atendimento ${nome}` : "Atendimento"),
      tituloPadrao: "Atendimento",
      fecharAtendimento: "Fechar atendimento",
      placeholder: "Digite sua dúvida...",
      inputAria: "Sua pergunta",
      enviar: "Enviar",
      rodape: "atendido por",
      saudacaoPadrao: "Como podemos ajudar?",
      erroRede: "Tivemos um problema. Fala com a gente direto pelo WhatsApp.",
      respostaVazia: "Posso te ajudar com algo mais?",
      verServico: "Ver serviço",
      falarWhatsapp: "Falar no WhatsApp",
    },
    en: {
      abrirAtendimento: "Open chat",
      botao: "💬 How can we help?",
      balaoAria: "Message from our team — click to chat",
      fecharMensagem: "Dismiss message",
      painelAria: (nome) => (nome ? `${nome} chat` : "Chat"),
      tituloPadrao: "Chat",
      fecharAtendimento: "Close chat",
      placeholder: "Type your question...",
      inputAria: "Your question",
      enviar: "Send",
      rodape: "powered by",
      saudacaoPadrao: "How can we help?",
      erroRede: "Something went wrong. Talk to us directly on WhatsApp.",
      respostaVazia: "Anything else I can help you with?",
      verServico: "View service",
      falarWhatsapp: "Chat on WhatsApp",
    },
    es: {
      abrirAtendimento: "Abrir atención",
      botao: "💬 ¿Cómo podemos ayudarte?",
      balaoAria: "Mensaje del equipo — haz clic para conversar",
      fecharMensagem: "Cerrar mensaje",
      painelAria: (nome) => (nome ? `Atención ${nome}` : "Atención"),
      tituloPadrao: "Atención",
      fecharAtendimento: "Cerrar atención",
      placeholder: "Escribe tu duda...",
      inputAria: "Tu pregunta",
      enviar: "Enviar",
      rodape: "atendido por",
      saudacaoPadrao: "¿En qué podemos ayudarte?",
      erroRede: "Tuvimos un problema. Habla con nosotros por WhatsApp.",
      respostaVazia: "¿Puedo ayudarte en algo más?",
      verServico: "Ver servicio",
      falarWhatsapp: "Hablar por WhatsApp",
    },
  };

  const T = TEXTOS[LANG] || TEXTOS[IDIOMA_PADRAO];

  // Evita injeção dupla se o script for incluído mais de uma vez.
  if (window.__atendeAiCarregado) return;
  window.__atendeAiCarregado = true;

  // ───────────────────────────────────────────────────────────────────────
  // Estado em memória
  // ───────────────────────────────────────────────────────────────────────
  const state = {
    config: null,    // {nome, cor_primaria, cor_secundaria, whatsapp, mensagem_saudacao, saudacao_contextual}
    aberto: false,
    enviando: false,
  };

  // ───────────────────────────────────────────────────────────────────────
  // Host + Shadow DOM
  // ───────────────────────────────────────────────────────────────────────
  const host = document.createElement("div");
  host.id = "atende-ai-host";
  host.style.cssText =
    `all: initial; position: fixed; bottom: 0; ${POS_SIDE}: 0; z-index: 2147483647;`;
  document.body.appendChild(host);

  const shadow = host.attachShadow({ mode: "closed" });

  // Templates: definidos como funções para usar as cores do tenant.
  const renderEstilos = (corPrimaria, corSecundaria) => `
    :host { all: initial; }
    * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont,
        "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }

    .botao {
      position: fixed; bottom: ${POS_BOTTOM}px; ${POS_SIDE}: 20px;
      background: ${corPrimaria}; color: #fff; border: none;
      border-radius: 999px; padding: 14px 22px; font-size: 15px; font-weight: 600;
      cursor: pointer; box-shadow: 0 6px 24px rgba(0,0,0,.18);
      transition: transform .15s ease, box-shadow .15s ease;
    }
    .botao:hover { transform: translateY(-1px); box-shadow: 0 8px 28px rgba(0,0,0,.22); }
    .botao:focus-visible { outline: 3px solid ${corSecundaria}; outline-offset: 2px; }

    .painel {
      position: fixed; bottom: ${POS_BOTTOM}px; ${POS_SIDE}: 20px;
      width: 380px; max-width: calc(100vw - 32px);
      height: 560px; max-height: calc(100vh - 40px);
      background: #fff; border-radius: 16px;
      box-shadow: 0 20px 60px rgba(0,0,0,.25);
      display: none; flex-direction: column; overflow: hidden;
    }
    .painel.aberto { display: flex; }

    /* ── Balãozinho proativo (saudação que aparece sozinha após X seg) ─── */
    .balao {
      position: fixed; bottom: ${POS_BOTTOM + 72}px; ${POS_SIDE}: 20px;
      background: #fff; color: #1a2530;
      max-width: 280px; padding: 12px 36px 12px 14px;
      border-radius: 14px; font-size: 14px; line-height: 1.4;
      box-shadow: 0 10px 30px rgba(0,0,0,.18);
      border: 1px solid #e6eaee;
      cursor: pointer; opacity: 0; transform: translateY(8px);
      transition: opacity .25s ease, transform .25s ease;
      pointer-events: none;
    }
    .balao.visivel { opacity: 1; transform: translateY(0); pointer-events: auto; }
    .balao::after {
      content: ""; position: absolute; bottom: -6px; ${POS_SIDE}: 30px;
      width: 12px; height: 12px; background: #fff; transform: rotate(45deg);
      border-${POS_SIDE === "right" ? "right" : "left"}: 1px solid #e6eaee;
      border-bottom: 1px solid #e6eaee;
    }
    .balao-close {
      position: absolute; top: 6px; right: 6px;
      background: transparent; border: none; color: #8a96a3;
      width: 24px; height: 24px; border-radius: 6px; cursor: pointer;
      font-size: 18px; line-height: 1; padding: 0;
    }
    .balao-close:hover { background: #f0f3f6; color: #1a2530; }

    .cabecalho {
      background: ${corPrimaria}; color: #fff;
      padding: 16px 18px; display: flex; align-items: center; justify-content: space-between;
    }
    .cabecalho-titulo { font-size: 16px; font-weight: 600; margin: 0; }
    .cabecalho-fechar {
      background: transparent; border: none; color: #fff; cursor: pointer;
      font-size: 22px; line-height: 1; padding: 4px 8px; border-radius: 6px;
    }
    .cabecalho-fechar:hover { background: rgba(255,255,255,.15); }
    .cabecalho-fechar:focus-visible { outline: 2px solid #fff; outline-offset: 1px; }

    .mensagens {
      flex: 1; overflow-y: auto; padding: 16px;
      background: #f7f9fb; display: flex; flex-direction: column; gap: 10px;
    }
    .msg { max-width: 85%; padding: 10px 14px; border-radius: 14px; font-size: 14px; line-height: 1.45; word-wrap: break-word; }
    .msg-bot { background: #fff; border: 1px solid #e6eaee; align-self: flex-start; border-bottom-left-radius: 4px; }
    .msg-usuario { background: ${corPrimaria}; color: #fff; align-self: flex-end; border-bottom-right-radius: 4px; }
    .msg-erro { background: #fdecea; color: #8a1f15; align-self: flex-start; border: 1px solid #f5c6c1; }

    .digitando { display: flex; gap: 4px; padding: 12px 14px; background: #fff; border: 1px solid #e6eaee; border-radius: 14px; align-self: flex-start; }
    .digitando span { width: 7px; height: 7px; background: #b0b8c0; border-radius: 50%; animation: pulsar 1s infinite ease-in-out; }
    .digitando span:nth-child(2) { animation-delay: .15s; }
    .digitando span:nth-child(3) { animation-delay: .3s; }
    @keyframes pulsar { 0%,80%,100% { opacity: .3; transform: scale(.8); } 40% { opacity: 1; transform: scale(1); } }

    .card-servico {
      margin-top: 6px; padding: 12px; background: #fff; border: 1px solid #e6eaee;
      border-radius: 12px; display: flex; flex-direction: column; gap: 8px;
    }
    .card-servico-nome { font-weight: 600; font-size: 14px; color: ${corPrimaria}; }
    .card-acoes { display: flex; gap: 8px; flex-wrap: wrap; }
    .acao { text-decoration: none; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 600; display: inline-block; }
    .acao-servico { background: ${corSecundaria}; color: #fff; }
    .acao-whatsapp { background: #25D366; color: #fff; }
    .acao:focus-visible { outline: 2px solid ${corPrimaria}; outline-offset: 2px; }

    .formulario {
      display: flex; gap: 8px; padding: 12px; border-top: 1px solid #e6eaee; background: #fff;
    }
    .input {
      flex: 1; border: 1px solid #d6dce2; border-radius: 10px;
      padding: 10px 12px; font-size: 14px; outline: none;
    }
    .input:focus { border-color: ${corPrimaria}; box-shadow: 0 0 0 3px ${corPrimaria}22; }
    .enviar {
      background: ${corPrimaria}; color: #fff; border: none; border-radius: 10px;
      padding: 0 16px; font-weight: 600; cursor: pointer;
    }
    .enviar:disabled { opacity: .5; cursor: not-allowed; }
    .enviar:focus-visible { outline: 2px solid ${corSecundaria}; outline-offset: 2px; }

    .rodape { text-align: center; font-size: 11px; color: #8a96a3; padding: 6px; background: #fff; border-top: 1px solid #f0f3f6; }
    .rodape a { color: #8a96a3; text-decoration: none; }

    @media (max-width: 480px) {
      .painel { width: 100vw; height: 100vh; max-width: 100vw; max-height: 100vh; bottom: 0; ${POS_SIDE}: 0; border-radius: 0; }
      .botao { bottom: ${Math.max(POS_BOTTOM - 4, 12)}px; ${POS_SIDE}: 16px; }
      .balao { bottom: ${Math.max(POS_BOTTOM - 4, 12) + 64}px; ${POS_SIDE}: 16px; max-width: calc(100vw - 48px); }
    }
  `;

  // ───────────────────────────────────────────────────────────────────────
  // Inicialização: busca config e monta UI
  // ───────────────────────────────────────────────────────────────────────
  async function init() {
    try {
      const url = `${BACKEND_URL}/api/v1/config/${encodeURIComponent(TENANT_SLUG)}/`
        + `?path=${encodeURIComponent(window.location.pathname)}`
        + `&lang=${encodeURIComponent(LANG)}`;
      const resp = await fetch(url, { method: "GET", mode: "cors" });
      if (!resp.ok) throw new Error(`config http ${resp.status}`);
      state.config = await resp.json();
    } catch (err) {
      // Falha silenciosa: sem config, não renderiza. Não quebra o site.
      console.warn("[atende-ai] não foi possível carregar config:", err);
      return;
    }

    if (!state.config || state.config.ativo === false) {
      // Tenant inativo: não renderiza widget. Pagamento em dia volta sozinho.
      return;
    }

    montarUI();
  }

  // ───────────────────────────────────────────────────────────────────────
  // Construção da UI dentro do Shadow DOM
  // ───────────────────────────────────────────────────────────────────────
  function montarUI() {
    const cfg = state.config;
    const corPrimaria = cfg.cor_primaria || "#0a3d62";
    const corSecundaria = cfg.cor_secundaria || "#2e86de";
    // O backend já devolve mensagem_saudacao traduzida para LANG; o default
    // local só vale se o tenant não tiver nenhuma cadastrada.
    const saudacao = (scriptEl.getAttribute("data-saudacao") || "").trim()
      || cfg.saudacao_contextual || cfg.mensagem_saudacao || T.saudacaoPadrao;

    const styleEl = document.createElement("style");
    styleEl.textContent = renderEstilos(corPrimaria, corSecundaria);
    shadow.appendChild(styleEl);

    // Botão flutuante
    const botao = document.createElement("button");
    botao.className = "botao";
    botao.type = "button";
    botao.setAttribute("aria-label", T.abrirAtendimento);
    botao.textContent = T.botao;
    shadow.appendChild(botao);

    // Balãozinho proativo (saudação que aparece sozinha após X segundos).
    // Não recria se o visitante já fechou nesta mesma página (localStorage).
    const balao = document.createElement("div");
    balao.className = "balao";
    balao.setAttribute("role", "button");
    balao.setAttribute("tabindex", "0");
    balao.setAttribute("aria-label", T.balaoAria);
    balao.setAttribute("lang", LANG);
    balao.innerHTML = `
      <button class="balao-close" type="button" aria-label="${escaparHtml(T.fecharMensagem)}">×</button>
      <div class="balao-texto"></div>
    `;
    balao.querySelector(".balao-texto").textContent = saudacao;
    shadow.appendChild(balao);

    // Painel
    const painel = document.createElement("div");
    painel.className = "painel";
    painel.setAttribute("role", "dialog");
    painel.setAttribute("aria-label", T.painelAria(cfg.nome || ""));
    // lang no painel: leitor de tela pronuncia a resposta da IA com a
    // fonética certa, já que o conteúdo vem no idioma do visitante.
    painel.setAttribute("lang", LANG);
    painel.innerHTML = `
      <div class="cabecalho">
        <p class="cabecalho-titulo">${escaparHtml(cfg.nome || T.tituloPadrao)}</p>
        <button class="cabecalho-fechar" type="button" aria-label="${escaparHtml(T.fecharAtendimento)}">×</button>
      </div>
      <div class="mensagens" id="ai-mensagens" aria-live="polite"></div>
      <form class="formulario" id="ai-form" autocomplete="off">
        <input class="input" id="ai-input" type="text" placeholder="${escaparHtml(T.placeholder)}"
               aria-label="${escaparHtml(T.inputAria)}" maxlength="1000" required />
        <button class="enviar" id="ai-enviar" type="submit"
                aria-label="${escaparHtml(T.enviar)}">${escaparHtml(T.enviar)}</button>
      </form>
      <div class="rodape">${escaparHtml(T.rodape)} <strong>atende-ai</strong></div>
    `;
    shadow.appendChild(painel);

    const elMensagens = shadow.getElementById("ai-mensagens");
    const elInput = shadow.getElementById("ai-input");
    const elEnviar = shadow.getElementById("ai-enviar");
    const elForm = shadow.getElementById("ai-form");
    const elFechar = painel.querySelector(".cabecalho-fechar");

    adicionarMensagemBot(elMensagens, saudacao);

    // ── Eventos
    botao.addEventListener("click", () => abrir(painel, botao, elInput, balao));
    elFechar.addEventListener("click", () => fechar(painel, botao));

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && state.aberto) fechar(painel, botao);
    });

    // ── Balãozinho proativo: clicar abre o painel; X esconde sem abrir.
    const balaoClose = balao.querySelector(".balao-close");
    const esconderBalao = () => balao.classList.remove("visivel");
    balao.addEventListener("click", (e) => {
      if (e.target === balaoClose) return; // X é tratado separado
      esconderBalao();
      abrir(painel, botao, elInput, balao);
    });
    balao.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        esconderBalao();
        abrir(painel, botao, elInput, balao);
      }
    });
    balaoClose.addEventListener("click", (e) => {
      e.stopPropagation();
      esconderBalao();
      // Marca pra não mostrar de novo nesta página por 24h (UX: respeitar o "não").
      try {
        const chave = `atende-ai-balao-${TENANT_SLUG}-${window.location.pathname}`;
        localStorage.setItem(chave, String(Date.now()));
      } catch { /* localStorage pode estar bloqueado — ignora */ }
    });

    // Mostra o balão após o delay (se proativo ligado, não foi dismissado
    // recentemente e o painel ainda não estiver aberto).
    if (PROATIVO_LIGADO) {
      let dismissadoRecentemente = false;
      try {
        const chave = `atende-ai-balao-${TENANT_SLUG}-${window.location.pathname}`;
        const dismissadoEm = parseInt(localStorage.getItem(chave) || "0", 10);
        dismissadoRecentemente = (Date.now() - dismissadoEm) < 24 * 60 * 60 * 1000;
      } catch { /* ignora */ }

      if (!dismissadoRecentemente) {
        setTimeout(() => {
          if (!state.aberto) balao.classList.add("visivel");
        }, PROATIVO_DELAY_MS);
      }
    }

    elForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const pergunta = elInput.value.trim();
      if (!pergunta || state.enviando) return;

      adicionarMensagemUsuario(elMensagens, pergunta);
      elInput.value = "";
      state.enviando = true;
      elEnviar.disabled = true;

      const indicador = adicionarDigitando(elMensagens);
      try {
        const resposta = await enviarPergunta(pergunta);
        indicador.remove();
        renderizarResposta(elMensagens, resposta, corPrimaria, corSecundaria);
      } catch (err) {
        indicador.remove();
        adicionarMensagemErro(elMensagens, T.erroRede, cfg.whatsapp);
      } finally {
        state.enviando = false;
        elEnviar.disabled = false;
        elInput.focus();
      }
    });
  }

  // ───────────────────────────────────────────────────────────────────────
  // Helpers de UI
  // ───────────────────────────────────────────────────────────────────────
  function abrir(painel, botao, input, balao) {
    painel.classList.add("aberto");
    botao.style.display = "none";
    if (balao) balao.classList.remove("visivel");
    state.aberto = true;
    setTimeout(() => input.focus(), 50);
  }
  function fechar(painel, botao) {
    painel.classList.remove("aberto");
    botao.style.display = "";
    state.aberto = false;
    botao.focus();
  }

  function escaparHtml(texto) {
    const div = document.createElement("div");
    div.textContent = texto == null ? "" : String(texto);
    return div.innerHTML;
  }

  function adicionarMensagemBot(container, texto) {
    const el = document.createElement("div");
    el.className = "msg msg-bot";
    el.textContent = texto;
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
    return el;
  }
  function adicionarMensagemUsuario(container, texto) {
    const el = document.createElement("div");
    el.className = "msg msg-usuario";
    el.textContent = texto;
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
  }
  function adicionarMensagemErro(container, texto, whatsapp) {
    const el = document.createElement("div");
    el.className = "msg msg-erro";
    el.textContent = texto;
    container.appendChild(el);
    if (whatsapp) renderizarBotaoWhats(container, whatsapp);
    container.scrollTop = container.scrollHeight;
  }
  function adicionarDigitando(container) {
    const el = document.createElement("div");
    el.className = "digitando";
    el.innerHTML = "<span></span><span></span><span></span>";
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
    return el;
  }

  function renderizarResposta(container, dados, corPrimaria, corSecundaria) {
    adicionarMensagemBot(container, dados.resposta || T.respostaVazia);

    if (dados.servico || dados.whatsapp) {
      const card = document.createElement("div");
      card.className = "card-servico";

      if (dados.servico && dados.servico.nome) {
        const nome = document.createElement("div");
        nome.className = "card-servico-nome";
        nome.textContent = dados.servico.nome;
        card.appendChild(nome);
      }

      const acoes = document.createElement("div");
      acoes.className = "card-acoes";

      // "Ver serviço" só aparece quando:
      //  1. O tenant permite (config.mostrar_botao_servico !== false) — nichos
      //     como psicologia/terapia escolhem ocultar pra não quebrar o fluxo
      //     emocional do visitante levando-o pra outra página.
      //  2. Tem URL de serviço no payload.
      //  3. O visitante NÃO está na própria página do serviço (evita botão
      //     redundante que abriria a mesma página em nova aba).
      const permiteBotaoServico = state.config.mostrar_botao_servico !== false;
      if (
        permiteBotaoServico
        && dados.servico
        && dados.servico.url
        && !mesmaPaginaQueServico(dados.servico.url)
      ) {
        const linkServico = document.createElement("a");
        linkServico.className = "acao acao-servico";
        linkServico.href = dados.servico.url;
        linkServico.target = "_blank";
        linkServico.rel = "noopener";
        linkServico.textContent = T.verServico;
        acoes.appendChild(linkServico);
      }

      if (dados.whatsapp) {
        acoes.appendChild(criarBotaoWhats(dados.whatsapp, dados.log_id));
      }

      if (acoes.childElementCount > 0) card.appendChild(acoes);
      container.appendChild(card);
      container.scrollTop = container.scrollHeight;
    }
  }

  // Compara o pathname da URL do servico com o pathname atual. Se forem iguais,
  // o visitante ja esta nessa pagina e nao faz sentido mostrar "Ver servico".
  function mesmaPaginaQueServico(urlServico) {
    try {
      const u = new URL(urlServico, window.location.href);
      return u.pathname === window.location.pathname;
    } catch {
      return false;
    }
  }

  function criarBotaoWhats(numero, logId) {
    const a = document.createElement("a");
    a.className = "acao acao-whatsapp";
    a.href = `https://wa.me/${encodeURIComponent(numero)}`;
    a.target = "_blank";
    a.rel = "noopener";
    a.textContent = T.falarWhatsapp;
    // Telemetria (F8): registra o clique no WhatsApp ligado a esta busca.
    // Usa closure no logId daquela resposta — buscas seguintes não interferem.
    if (logId) {
      a.addEventListener("click", () => enviarCliqueWhatsapp(logId));
    }
    return a;
  }

  // Beacon de clique no WhatsApp. Best-effort: nunca atrapalha a navegação.
  // text/plain evita preflight CORS; sendBeacon sobrevive à troca de aba/página.
  function enviarCliqueWhatsapp(logId) {
    if (!logId || !navigator.sendBeacon) return;
    try {
      const corpo = new Blob(
        [JSON.stringify({ tenant_slug: TENANT_SLUG, log_id: logId })],
        { type: "text/plain" },
      );
      navigator.sendBeacon(`${BACKEND_URL}/api/v1/evento/clique-whatsapp/`, corpo);
    } catch (_e) {
      /* tracking é opcional — silêncio total se falhar */
    }
  }
  function renderizarBotaoWhats(container, numero) {
    const wrap = document.createElement("div");
    wrap.className = "card-servico";
    const acoes = document.createElement("div");
    acoes.className = "card-acoes";
    acoes.appendChild(criarBotaoWhats(numero));
    wrap.appendChild(acoes);
    container.appendChild(wrap);
  }

  // ───────────────────────────────────────────────────────────────────────
  // Chamada ao backend
  // ───────────────────────────────────────────────────────────────────────
  async function enviarPergunta(pergunta) {
    const url = `${BACKEND_URL}/api/v1/buscar/`;
    const corpo = {
      tenant_slug: TENANT_SLUG,
      pergunta: pergunta,
      path: window.location.pathname,
      idioma: LANG,
    };
    const resp = await fetch(url, {
      method: "POST",
      mode: "cors",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    });
    // Status 429/4xx ainda retornam JSON com resposta amigável — tratamos como sucesso.
    const dados = await resp.json().catch(() => ({}));
    return dados;
  }

  // ───────────────────────────────────────────────────────────────────────
  // Boot
  // ───────────────────────────────────────────────────────────────────────
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
