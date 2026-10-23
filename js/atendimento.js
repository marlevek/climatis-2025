(function () {
    "use strict";

    const loaderScript = document.currentScript;
    const greetings = {
        "index.html": "Olá! Você procura instalação, manutenção de ar-condicionado ou refrigeração comercial? Como podemos ajudar?",
        "manutencao-de-camara-fria.html": "Olá! Sua câmara fria precisa de manutenção? Ela está com dificuldade para manter a temperatura, excesso de gelo ou você procura uma revisão preventiva?",
        "manutencao-de-freezer.html": "Olá! Você precisa de manutenção no freezer? Ele não está congelando, acumula gelo ou apresenta outro problema?",
        "manutencao-de-maquina-de-gelo.html": "Olá! Você precisa de manutenção na máquina de gelo? Ela parou de produzir, está produzindo pouco ou precisa de higienização?",
        "manutencao-de-climatizadores.html": "Olá! Seu climatizador precisa de manutenção? Você percebeu pouca ventilação, vazamento ou precisa de limpeza?",
        "manutencao-de-geladeira.html": "Olá! Você precisa de manutenção na geladeira? Ela não está refrigerando, faz barulho ou apresenta outro problema?",
        "manutencao-de-balcao-frigorifico.html": "Olá! Seu balcão frigorífico precisa de manutenção? Ele está com dificuldade para refrigerar ou você procura uma revisão preventiva?",
        "manutencao-buffet-quente-frio.html": "Olá! Você precisa de manutenção no buffet quente ou frio? Qual problema o equipamento está apresentando?",
        "manutencao-de-ar-condicionado.html": "Olá! Você procura manutenção preventiva ou reparo no ar-condicionado? Conte o que está acontecendo com o equipamento.",
        "instalacao-de-ar-condicionado.html": "Olá! Você está planejando instalar um ar-condicionado? Já tem o aparelho ou precisa de orientação para escolher?",
        "limpeza-de-ar-condicionado.html": "Olá! Você precisa de limpeza ou higienização do ar-condicionado? Quantos aparelhos deseja limpar?",
        "pmoc-para-ar-condicionado.html": "Olá! Você precisa de um PMOC para sua empresa? Quer saber como funciona o plano ou solicitar um orçamento?",
        "landing-page-pmoc.html": "Olá! Você quer conhecer ou contratar um PMOC? Qual é o tipo de estabelecimento e quantos aparelhos ele possui?",
        "infraestrutura-para-ar-condicionado.html": "Olá! Você está preparando a infraestrutura para ar-condicionado? O ambiente está em obra ou já está pronto?",
        "sistema-vrf.html": "Olá! Você quer saber mais sobre o sistema VRF? Procura instalação, manutenção ou uma avaliação para seu projeto?",
        "fancoil.html": "Olá! Você tem dúvidas sobre fancoil ou precisa de manutenção no sistema? Conte como podemos ajudar.",
        "refrigeracao-comercial.html": "Olá! Qual equipamento de refrigeração comercial precisa de atendimento: câmara fria, freezer, máquina de gelo ou climatizador?",
        "servicos-de-ar-condicionado-e-refrigeracao.html": "Olá! Qual serviço você procura: instalação, manutenção, limpeza, PMOC ou refrigeração comercial?",
        "ar-condicionado-para-comercio.html": "Olá! Você procura climatização para seu comércio? Qual é o tipo de estabelecimento e o que precisa melhorar no ambiente?",
        "aparelhos-de-ar-condicionado.html": "Olá! Você precisa de ajuda para escolher um ar-condicionado? Para qual ambiente está procurando um aparelho?",
        "tipos-de-ar-condicionado.html": "Olá! Quer entender qual tipo de ar-condicionado faz sentido para seu ambiente? Conte como é o local que deseja climatizar.",
        "simulador.html": "Olá! Precisa de ajuda para estimar os BTUs ou usar o simulador de ar-condicionado? Qual ambiente deseja climatizar?",
        "loja-de-servicos-para-ar-condicionado.html": "Olá! Você tem dúvidas sobre os serviços de ar-condicionado da Climátis? Qual serviço está procurando?",
        "garantia-climatis-instalacao-ar-condicionado.html": "Olá! Você tem dúvidas sobre a garantia de instalação do ar-condicionado? O que gostaria de esclarecer?",
        "geladeira-fazendo-barulho.html": "Olá! Sua geladeira está fazendo barulho? Como é o ruído e em que momento ele aparece?",
        "dicas-dia-a-dia-com-geladeiras.html": "Olá! Você tem alguma dúvida sobre o uso e os cuidados com a geladeira? Como podemos ajudar?",
        "empresa-climatis.html": "Olá! Quer conhecer melhor a Climátis, nossa equipe ou a região de atendimento? O que gostaria de saber?",
        "cursos-e-credenciamentos-climatis.html": "Olá! Você tem dúvidas sobre as qualificações e os credenciamentos da equipe Climátis? O que gostaria de saber?",
        "faq-ar-condicionado-e-refrigeracao.html": "Olá! Qual é sua dúvida sobre ar-condicionado ou refrigeração? Posso ajudar a encontrar a informação que procura.",
        "contato.html": "Olá! Você deseja solicitar um orçamento, agendar atendimento ou tirar alguma dúvida com a Climátis?",
        "politica-de-privacidade.html": "Olá! Você tem alguma dúvida sobre a política de privacidade e o uso de dados neste site?",
        "agradecimento-pmoc.html": "Olá! Sua solicitação de PMOC foi enviada. Você tem alguma dúvida sobre os próximos passos?",
        "resposta-contato.html": "Olá! Sua mensagem foi enviada. Você precisa de mais alguma informação sobre o atendimento?",
        "404.html": "Olá! Não encontrou a página que procurava? Qual informação ou serviço da Climátis deseja acessar?"
    };

    function init() {
        // As páginas antigas e as páginas com header/footer usam o mesmo carregador.
        if (document.querySelector('script[data-climatis-widget]')) return;

        let path = window.location.pathname;
        try {
            path = decodeURIComponent(path);
        } catch {
            // Uma URL malformada não deve interromper o restante do site.
        }
        const pageName = path.split("/").pop().toLowerCase() || "index.html";
        const heading = document.querySelector("main h1, h1");
        const pageTitle = heading ? heading.textContent.replace(/\s+/g, " ").trim() : "";
        const greeting = greetings[pageName] || (pageTitle
            ? `Olá! Você tem alguma dúvida sobre “${pageTitle}”? Como podemos ajudar?`
            : "Olá! Qual informação ou serviço da Climátis você está procurando?");

        const widget = document.createElement("script");
        widget.src = new URL("atende-ai-widget.js?v=climatis-1", loaderScript.src).href;
        widget.setAttribute("data-climatis-widget", "");
        widget.setAttribute("data-backend", "https://api.atendesite.com.br");
        widget.setAttribute("data-tenant", "climatis");
        widget.setAttribute("data-bottom", "180");
        widget.setAttribute("data-saudacao", greeting);
        widget.defer = true;
        document.body.appendChild(widget);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init, { once: true });
    } else {
        init();
    }
})();
