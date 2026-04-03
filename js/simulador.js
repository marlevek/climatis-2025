document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("simulador-form");
    const result = document.getElementById("simulador-resultado");

    if (!form || !result) {
        return;
    }

    const btuSteps = [9000, 12000, 18000, 24000, 30000, 36000, 48000, 60000];

    const typeLabels = {
        inverter: "Split Hi Wall Inverter",
        cassete: "Split Cassete",
        piso_teto: "Split Piso Teto"
    };

    const equipmentRanges = {
        inverter: {
            9000: [1946, 2300],
            12000: [2250, 2800],
            18000: [3200, 4100],
            24000: [4500, 5800],
            30000: [5600, 7000],
            36000: [7000, 8700],
            48000: [9900, 12900],
            60000: [12900, 16900]
        },
        cassete: {
            24000: [6200, 8400],
            30000: [7600, 9800],
            36000: [8600, 11200],
            48000: [11000, 14500],
            60000: [14500, 19200]
        },
        piso_teto: {
            24000: [5900, 7900],
            30000: [7200, 9300],
            36000: [8200, 10800],
            48000: [10600, 13900],
            60000: [14100, 18800]
        }
    };

    const installBase = {
        9000: 850,
        12000: 950,
        18000: 1250,
        24000: 1650,
        30000: 2150,
        36000: 2650,
        48000: 3900,
        60000: 5400
    };

    const environmentFactors = {
        residencial: { area: 600, person: 600, included: 1, installMultiplier: 1 },
        comercial: { area: 750, person: 700, included: 2, installMultiplier: 1.08 },
        industrial: { area: 900, person: 800, included: 3, installMultiplier: 1.18 }
    };

    const sunFactors = { baixa: 1, media: 1.1, alta: 1.2 };
    const usageFactors = { leve: 1, medio: 1.05, intenso: 1.12 };

    form.addEventListener("submit", (event) => {
        event.preventDefault();

        if (!form.reportValidity()) {
            return;
        }

        const data = new FormData(form);
        const answers = Object.fromEntries(data.entries());
        const rawBtu = calculateRawBtu(answers);
        const recommendedBtu = pickBtu(rawBtu);
        const recommendation = chooseSystem(answers, recommendedBtu);
        const equipmentRange = pickEquipmentRange(recommendation.type, recommendedBtu);
        const installation = calculateInstallation(answers, recommendation.type, recommendedBtu);
        const totalMin = equipmentRange[0] + installation.price;
        const totalMax = equipmentRange[1] + installation.price;
        const whatsappUrl = buildWhatsAppUrl({
            ...answers,
            rawBtu,
            recommendedBtu,
            recommendation,
            equipmentRange,
            installation,
            totalMin,
            totalMax
        });

        renderResult({
            rawBtu,
            recommendedBtu,
            recommendation,
            equipmentRange,
            installation,
            totalMin,
            totalMax,
            whatsappUrl
        });
    });

    function calculateRawBtu(answers) {
        const profile = environmentFactors[answers.tipoAmbiente];
        const area = Number(answers.metragem);
        const people = Number(answers.pessoas);
        const occupancyLoad = Math.max(0, people - profile.included) * profile.person;
        const baseLoad = area * profile.area + occupancyLoad;

        return Math.round(baseLoad * sunFactors[answers.sol] * usageFactors[answers.uso]);
    }

    function pickBtu(rawBtu) {
        return btuSteps.find((step) => rawBtu <= step) || btuSteps[btuSteps.length - 1];
    }

    function chooseSystem(answers, recommendedBtu) {
        const preferred = answers.preferencia;
        const environment = answers.tipoAmbiente;
        let type = "inverter";
        let note = "";

        if (preferred === "cassete" && recommendedBtu >= 24000) {
            type = "cassete";
        } else if (preferred === "piso_teto" && recommendedBtu >= 24000) {
            type = "piso_teto";
        } else if (preferred === "inverter") {
            type = "inverter";
        } else if (environment === "industrial") {
            type = recommendedBtu >= 36000 ? "piso_teto" : "cassete";
            note = "Ambientes industriais costumam exigir distribuição de ar mais robusta e equipamentos de maior vazão.";
        } else if (environment === "comercial") {
            type = recommendedBtu >= 36000 ? "cassete" : recommendedBtu >= 24000 ? "piso_teto" : "inverter";
            note = recommendedBtu >= 24000
                ? "Para áreas comerciais maiores, sistemas cassete ou piso teto tendem a distribuir melhor o ar."
                : "";
        } else {
            type = "inverter";
            note = "Para residências, o inverter costuma oferecer melhor equilíbrio entre conforto e economia.";
        }

        if ((preferred === "cassete" || preferred === "piso_teto") && recommendedBtu < 24000) {
            note = "Para a carga térmica informada, um sistema hi wall tende a ser mais eficiente e econômico.";
        }

        return {
            type,
            label: `${typeLabels[type]} ${formatBtu(recommendedBtu)}`,
            note
        };
    }

    function pickEquipmentRange(type, recommendedBtu) {
        const table = equipmentRanges[type];
        const supported = Object.keys(table).map(Number).sort((a, b) => a - b);
        const matchedTier = supported.find((value) => recommendedBtu <= value) || supported[supported.length - 1];

        return table[matchedTier];
    }

    function calculateInstallation(answers, type, recommendedBtu) {
        const profile = environmentFactors[answers.tipoAmbiente];
        let price = installBase[recommendedBtu] || installBase[60000];

        price = Math.round(price * profile.installMultiplier);

        if (answers.infra === "parcial") {
            price += recommendedBtu <= 18000 ? 350 : 650;
        }

        if (answers.infra === "nao") {
            price += recommendedBtu <= 18000 ? 650 : 1100;
        }

        if (type === "cassete" || type === "piso_teto") {
            price += 750;
        }

        return {
            price,
            label: "Instalação completa, com materiais inclusos.",
            note: "Esse valor é uma estimativa, podendo variar para mais ou para menos.",
            eta: "Tempo da instalação, em média 5 horas."
        };
    }

    function buildWhatsAppUrl(data) {
        const message = [
            "Olá, Climatis! Fiz a simulação no site e gostaria de confirmar este orçamento estimado.",
            `Ambiente: ${capitalize(data.tipoAmbiente)}`,
            `Área: ${data.metragem} m²`,
            `Pessoas: ${data.pessoas}`,
            `Sol: ${capitalize(data.sol)}`,
            `Infraestrutura: ${normalizeInfra(data.infra)}`,
            `BTU calculado: ${formatBtu(data.recommendedBtu)}`,
            `Equipamento sugerido: ${data.recommendation.label}`,
            `Instalação sugerida: ${data.installation.label}`,
            `Obs.: ${data.installation.note}`,
            `Faixa do equipamento: ${formatCurrencyRange(data.equipmentRange[0], data.equipmentRange[1])}`,
            `Instalação estimada: ${formatCurrency(data.installation.price)}`,
            `Total estimado: ${formatCurrencyRange(data.totalMin, data.totalMax)}`,
            data.installation.eta
        ].join("\n");

        return `https://wa.me/5541988956598?text=${encodeURIComponent(message)}`;
    }

    function renderResult(data) {
        result.innerHTML = `
            <p class="simulador-result-title">Recomendação principal</p>
            <h4>${data.recommendation.label}</h4>
            <p>
                Pela carga térmica estimada, a faixa mais adequada para este ambiente fica em
                <strong>${formatBtu(data.recommendedBtu)}</strong>.
            </p>
            <div class="simulador-result-summary">
                <div class="simulador-result-box">
                    <span>BTU calculado</span>
                    <strong>${formatBtu(data.rawBtu)}</strong>
                </div>
                <div class="simulador-result-box">
                    <span>BTU recomendado</span>
                    <strong>${formatBtu(data.recommendedBtu)}</strong>
                </div>
                <div class="simulador-result-box">
                    <span>Aparelho estimado</span>
                    <strong>${formatCurrencyRange(data.equipmentRange[0], data.equipmentRange[1])}</strong>
                </div>
                <div class="simulador-result-box">
                    <span>Instalação estimada</span>
                    <strong>${formatCurrency(data.installation.price)}</strong>
                </div>
            </div>
            <p><strong>Tipo de instalação:</strong> ${data.installation.label}</p>
            <p><strong>Obs.:</strong> ${data.installation.note}</p>
            <p><strong>${data.installation.eta}</strong></p>
            <p><strong>Total estimado:</strong> ${formatCurrencyRange(data.totalMin, data.totalMax)}</p>
            ${data.recommendation.note ? `<div class="simulador-result-note">${data.recommendation.note}</div>` : ""}
            <div class="simulador-result-actions">
                <a class="btn btn-success" href="${data.whatsappUrl}" target="_blank" rel="noopener">
                    <i class="fab fa-whatsapp p-1"></i> Falar no WhatsApp
                </a>
                <a class="btn btn-outline-primary" href="instalacao-de-ar-condicionado.html">
                    <i class="fas fa-tools p-1"></i> Ver instala&ccedil;&atilde;o
                </a>
            </div>
        `;

        result.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function formatBtu(value) {
        return `${value.toLocaleString("pt-BR")} BTU/h`;
    }

    function formatCurrency(value) {
        return value.toLocaleString("pt-BR", {
            style: "currency",
            currency: "BRL"
        });
    }

    function formatCurrencyRange(min, max) {
        return `${formatCurrency(min)} a ${formatCurrency(max)}`;
    }

    function capitalize(value) {
        return value.charAt(0).toUpperCase() + value.slice(1);
    }

    function normalizeInfra(value) {
        if (value === "sim") {
            return "Pronta";
        }

        if (value === "parcial") {
            return "Parcial";
        }

        return "Não possui";
    }
});
