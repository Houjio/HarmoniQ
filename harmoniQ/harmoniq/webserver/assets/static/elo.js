console.log("elo.js loaded correctly!");

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

  function generateSankey(consumptionData, productionData) {
    let source = [], target = [], value = [], labels = [];

    const nodeLabels = [
      "Gaz", "Électricité", "Transport", "Bâtiment", "Industrie",
      "Hydro", "Solaire", "Éolien", "Thermique", "Nucléaire"
    ];

    const colorMap = {
      Gaz: "#a9a9a9",
      Électricité: "#34c759",
      Transport: "#ff7f50",
      Bâtiment: "#20b2aa",
      Industrie: "#778899",
      Hydro: "#1e90ff",
      Solaire: "#ffd700",
      Éolien: "#87ceeb",
      Thermique: "#ff8c00",
      Nucléaire: "#9370db"
    };

    const nodeIndex = {
      Gaz: 0,
      Électricité: 1,
      Transport: 2,
      Bâtiment: 3,
      Industrie: 4,
      Hydro: 5,
      Solaire: 6,
      Éolien: 7,
      Thermique: 8,
      Nucléaire: 9
    };

    consumptionData.forEach((row) => {
      const [_, __, ___, secteur, energie, val] = row;
      if (secteur in nodeIndex && energie in nodeIndex) {
        source.push(nodeIndex[energie]);
        target.push(nodeIndex[secteur]);
        value.push(parseFloat(val));
        labels.push(`${energie} → ${secteur}: ${val} TWh`);
      }
    });

    productionData.forEach((row) => {
      const [_, __, ___, cible, sourceProd, val] = row;
      if (sourceProd in nodeIndex && cible in nodeIndex) {
        source.push(nodeIndex[sourceProd]);
        target.push(nodeIndex[cible]);
        value.push(parseFloat(val));
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
        x: [0.4, 0.4, 0.8, 0.8, 0.8, 0, 0, 0, 0, 0],  // Horizontal placement (0 to 1)
        y: [0.25, 0.7, 0.2, 0.5, 0.8, 0.0, 0.2, 0.4, 0.6, 0.8], // Vertical placement
        hovertemplate: "%{label}<extra></extra>"
      },
      link: {
        source,
        target,
        value,
        label: labels,
        color: source.map(s => colorMap[nodeLabels[s]]),
        hovertemplate: "%{label}<br>%{value} TWh<extra></extra>"
      }
    };

    const layout = {
      title: {
        text: "Flux de Production et de Consommation d'Énergie",
        font: { size: 22, family: "Arial", color: "#333" }
      },
      font: { size: 14, family: "Helvetica" },
      margin: { l: 20, r: 20, t: 60, b: 20 },
      paper_bgcolor: "#f8f9fa",
      plot_bgcolor: "#f8f9fa"
    };

    Plotly.react("sankeyDiagram", [data], layout, {
      transition: {
        duration: 500,
        easing: "cubic-in-out"
      }
    });
  }

  async function updateSankey() {
    const scenario = document.getElementById("climateScenario").value;
    const croissance = document.querySelector('input[name="growthScenario"]:checked').value;
    const effSlider = document.getElementById("transportEfficiency").value;
    const efficacite = effSlider === "1" ? "faible" : effSlider === "2" ? "moyen" : "elevee";

    const [consumptionRaw, productionRaw] = await Promise.all([
      loadCSV("/static/data_sankey.csv"),
      loadCSV("/static/data_sankey_prod.csv")
    ]);

    if (!consumptionRaw.trim() || !productionRaw.trim()) {
      console.error("One or both CSVs are empty.");
      return;
    }

    const consumptionData = parseCSV(consumptionRaw, scenario, croissance, efficacite);
    const productionData = parseCSV(productionRaw, scenario, croissance, efficacite);

    console.log("Filtering for:", scenario, croissance, efficacite);
    console.log("Matching rows (consumption):", consumptionData.length);
    console.log("Matching rows (production):", productionData.length);

    if (consumptionData.length === 0 && productionData.length === 0) {
      console.error("No data found for selected scenario.");
      return;
    }

    generateSankey(consumptionData, productionData);
  }

  document.getElementById("generateButton").addEventListener("click", updateSankey);

  document.getElementById("transportEfficiency").addEventListener("input", function () {
    const labelMap = { "1": "Faible", "2": "Moyen", "3": "Élevé" };
    document.getElementById("efficiencyLabel").textContent = labelMap[this.value];
  });

  updateSankey();
});