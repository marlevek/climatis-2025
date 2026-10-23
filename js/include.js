async function loadComponent(id, file) { 
    try {
        const response = await fetch(`partials/${file}`);
        if (!response.ok) throw new Error(`Erro ao carregar ${file}`);
        const content = await response.text();
        document.getElementById(id).innerHTML = content;
    } catch (error) {
        console.error("❌ Erro ao carregar componente:", error);
    }
}

function loadWidget() {
    // O carregador compartilhado define a saudação conforme a página atual.
    if (document.querySelector('script[src*="js/atendimento.js"]')) return;
    const widget = document.createElement("script");
    widget.src = "js/atendimento.js?v=1";
    widget.defer = true;
    document.body.appendChild(widget);
}

document.addEventListener("DOMContentLoaded", () => {
    loadComponent("header", "header.html");
    loadComponent("footer", "footer.html");
    loadWidget();
});
