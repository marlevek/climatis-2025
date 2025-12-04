async function loadComponent(id, file) { 
    try {
        const response = await fetch(`/partials/${file}`);
        if (!response.ok) throw new Error(`Erro ao carregar ${file}`);
        const content = await response.text();
        document.getElementById(id).innerHTML = content;
    } catch (error) {
        console.error("❌ Erro ao carregar componente:", error);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadComponent("header", "header.html");
    loadComponent("footer", "footer.html");
});
