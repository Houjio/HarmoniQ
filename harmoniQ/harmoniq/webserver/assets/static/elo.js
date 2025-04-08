console.log("elo.js loaded correctly!");
let currentMode = "annuel";

document.addEventListener("DOMContentLoaded", function () {
  async function loadCSV(fileName) {
    try {
      const response = await fetch(fileName);
      if (!response.ok) throw new Error(`Error loading ${fileName}`);
      return await response.text();
    } catch (error) {
      console.error("Fetch error:", error);
      return "";
    }
  }

  const modeDescriptions = {
    annuel: "Ce diagramme représente la production et la consommation totale d’électricité au Québec sur une année complète. L’hydroélectricité domine largement, soutenue par l’éolien et d’autres sources renouvelables. C’est une vue d’ensemble du système énergétique du Québec",
    hiver: "En hiver, la demande d’électricité atteint des sommets en raison du chauffage électrique. L’hydroélectricité joue un rôle clé pour répondre à ces besoins accrus, tandis que l’éolien et les sources thermiques apportent un soutien important lors des vagues de froid et des pointes de consommation.",
    ete: "En été, la consommation d’électricité diminue considérablement en l’absence de chauffage. La production hydroélectrique reste élevée, l’énergie solaire atteint son rendement maximal, et l’éolien continue de contribuer régulièrement.",
    pic: "Ce diagramme illustre l’heure unique de l’année où la demande en électricité est la plus élevée. Il démontre l’importance des sources fiables comme l’hydroélectricité et le nucléaire, ainsi que le rôle des centrales thermiques pour faire face à la pointe de consommation."
  };

  function updateDescription(mode) {
    const description = modeDescriptions[mode] || "Le diagramme Sankey ci-dessus illustre les flux d'énergie entre la production et la consommation pour le scénario sélectionné.";
    const descElement = document.getElementById("sankeyDescription");
    if (descElement) {
      descElement.style.opacity = 0;
      setTimeout(() => {
        descElement.textContent = description;
        descElement.style.opacity = 1;
      }, 250);
    }
  }

  function parseCSV(data, scenario, croissance, efficacite) {
    const rows = data.replace(/\r/g, "").split("\n").slice(1);
    return rows
      .map((row) => row.split(",").map((cell) => cell.trim()))
      .filter(
        (row) =>
          row.length >= 6 &&
          row[0].toLowerCase() === scenario.toLowerCase() &&
          row[1].toLowerCase() === croissance.toLowerCase() &&
          row[2].toLowerCase() === efficacite.toLowerCase()
      );
  }

  function generateSankey(consumptionData, productionData, year) {
    let source = [], target = [], value = [], labels = [];

    const nodeLabels = [
      "Énergies fossiles", "Électricité", "Transport", "Bâtiment", "Commercial",
      "Hydro", "Solaire", "Éolien", "Thermique", "Nucléaire", "Importations", "Exportations", "Pertes"
    ];

    const colorMap = {
      "Énergies fossiles": "#a9a9a9",
      Électricité: "#34c759",
      Transport: "#ff7f50",
      Bâtiment: "#20b2aa",
      Commercial: "#778899",
      Hydro: "#1e90ff",
      Solaire: "#ffd700",
      Éolien: "#87ceeb",
      Thermique: "#ff8c00",
      Nucléaire: "#9370db",
      Importations: "#ff6347",
      Exportations: "#4682b4",
      Pertes: "#dcdcdc"
    };

    const nodeIndex = Object.fromEntries(nodeLabels.map((label, idx) => [label, idx]));

    consumptionData.forEach((row) => {
      const [_, __, ___, secteur, energie, val] = row;
      const parsedValue = parseFloat(val);
      if (secteur in nodeIndex && energie in nodeIndex && !isNaN(parsedValue)) {
        source.push(nodeIndex[energie]);
        target.push(nodeIndex[secteur]);
        value.push(parsedValue);
        labels.push(`${energie} → ${secteur}: ${val} TWh`);
      }
    });

    productionData.forEach((row) => {
      const [_, __, ___, cible, sourceProd, val] = row;
      const parsedValue = parseFloat(val);
      if (sourceProd in nodeIndex && cible in nodeIndex && !isNaN(parsedValue)) {
        source.push(nodeIndex[sourceProd]);
        target.push(nodeIndex[cible]);
        value.push(parsedValue);
        labels.push(`${sourceProd} → ${cible}: ${val} TWh`);
      }
    });

    const data = {
      type: "sankey",
      orientation: "h",
      node: {
        pad: 20,
        thickness: 25,
        line: { color: "black", width: 0.7 },
        label: nodeLabels,
        color: nodeLabels.map(label => colorMap[label]),
        x: [0.5, 0.5, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1],
        y: [0.7, 0.3, 0.1, 0.4, 0.7, 0.2, 0.4, 0.6, 0.8, 0.9, 1, 0.9, 1],
        hovertemplate: "%{label}<extra></extra>"
      },
      link: {
        source,
        target,
        value,
        label: labels,
        color: source.map(s => colorMap[nodeLabels[s]] || "#cccccc"),
        hovertemplate: "%{label}<br>Flux: %{value} TWh<extra></extra>"
      }
    };

    const layout = {
      title: {
        text: `Flux de Production et de Consommation d'Énergie (${year})`,
        font: { size: 22, family: "Arial", color: "#333" }
      },
      font: { size: 14, family: "Helvetica" },
      margin: { l: 20, r: 20, t: 60, b: 20 },
      paper_bgcolor: "#f8f9fa",
      plot_bgcolor: "#f8f9fa"
    };

    Plotly.newPlot("sankeyDiagram", [data], layout);
  }

  async function updateSankey() {
    const year = document.getElementById("yearSelector").value;
    const scenario = document.getElementById("climateScenario").value;
    const growthValue = document.querySelector('input[name="growthScenario"]:checked').value;
    let croissance = growthValue.includes("faible") ? "faible" : "elevee";
    let efficacite = document.getElementById("transportEfficiency").value;

    const [consumptionRaw, productionRaw] = await Promise.all([
      loadCSV(`/static/data_sankey/data_sankey_${year}_${currentMode}.csv`),
      loadCSV(`/static/data_sankey/data_sankey_prod_${year}_${currentMode}.csv`)
    ]);

    if (!consumptionRaw.trim() || !productionRaw.trim()) return;

    const consumptionData = parseCSV(consumptionRaw, scenario, croissance, efficacite);
    const productionData = parseCSV(productionRaw, scenario, croissance, efficacite);

    if (consumptionData.length === 0 && productionData.length === 0) return;

    generateSankey(consumptionData, productionData, year);
  }

  document.getElementById("generateButton").addEventListener("click", updateSankey);
  document.querySelectorAll("#viewTabs .nav-link").forEach(button => {
    button.addEventListener("click", (e) => {
      e.preventDefault();
      currentMode = button.dataset.view;
      document.querySelectorAll("#viewTabs .nav-link").forEach(btn => btn.classList.remove("active"));
      button.classList.add("active");
      updateDescription(currentMode);
      updateSankey();
    });
  });

  document.getElementById("downloadPNG").addEventListener("click", async () => {
    const sankeyDiagram = document.getElementById("sankeyDiagram");
    if (sankeyDiagram) {
      try {
        const pngData = await Plotly.toImage(sankeyDiagram, { format: "png", width: 1200, height: 800 });
        const link = document.createElement("a");
        link.href = pngData;
        link.download = "sankey_diagram.png";
        link.click();
      } catch (error) {
        console.error("Error generating PNG:", error);
      }
    }
  });

  updateDescription(currentMode);
  updateSankey();
});