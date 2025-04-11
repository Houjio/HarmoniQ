$('button[data-bs-target="#sankey"]').on('shown.bs.tab', function () {
    if (typeof demandeSankey === 'undefined' || demandeSankey === null) {
        return;
    }

    Plotly.Plots.resize('sankey-plot');
    Plotly.relayout('sankey-plot', { 'yaxis.autorange': true });
});

$('button[data-bs-target="#temporal"]').on('shown.bs.tab', function () {
    if (typeof demandeTemporal === 'undefined' || demandeTemporal === null) {
        return;
    }

    Plotly.Plots.resize('temporal-plot');
    Plotly.relayout('temporal-plot', { 'yaxis.autorange': true });
});

function generateSankey() {
    // Generate Sankey diagram
    const sectorLabels = Object.values(demandeSankey.sector);
    const energyLabels = ["Electricity", "Gaz"];
    const allLabels = energyLabels.concat(sectorLabels);

    const electricitySourceIndex = 0; // Electricité
    const gazSourceIndex = 1;         // Gaz

    const sources = [];
    const targets = [];
    const values = [];

    for (let i = 0; i < sectorLabels.length; i++) {
        const targetIndex = i + energyLabels.length;

        // Electricity to sector
        sources.push(electricitySourceIndex);
        targets.push(targetIndex);
        values.push(demandeSankey.total_electricity[i]);

        // Gaz to sector
        sources.push(gazSourceIndex);
        targets.push(targetIndex);
        values.push(demandeSankey.total_gaz[i]);
        }

    const sankeyData = [{
        type: "sankey",
        orientation: "h",
        node: {
            pad: 15,
            thickness: 20,
            label: allLabels
        },
        link: {
            source: sources,
            target: targets,
            value: values
        }
    }];

    const layout = {
        title: "Flux d'énergie vers les secteurs pour scénario " + $("#scenario-actif option:selected").text(),
        font: { size: 10 }
    };

    Plotly.newPlot("sankey-plot", sankeyData, layout);
}


function generateTemporalPlot() {
    const xval = Object.keys(demandeTemporal.total_electricity);
    const yval = Object.values(demandeTemporal.total_electricity);

    const layout = {
        title: "Demande et production pour scénario " + $("#scenario-actif option:selected").text(),
        xaxis: {
            title: "Date",
            tickformat: "%d %b %Y"
        },
        yaxis: {
            title: "Demande/Production (MW)",
            autorange: true
        },
        legend: {
            orientation: "h",
            yanchor: "bottom",
            y: 1.02,
            xanchor: "right",
            x: 1
        },
    };

    const trace = {
        x: xval,
        y: yval,
        type: 'scatter',
        mode: 'lines',
        marker: { color: 'blue' },
        line: { shape: 'spline' },
        name: "Demande électrique",
        hovertemplate: "%{x}<br>%{y:.2f} MW<extra></extra>"
    };

    Plotly.newPlot("temporal-plot", [trace], layout);
}

function updateTemporalGraph() {
    // Add production traces
    const productionTraces = [];
    const productionData = demandeTemporal.production;
    const productionNames = Object.keys(productionData);
    const productionColors = ['red', 'green', 'orange', 'purple', 'pink'];
    const productionColorMap = {};
    productionNames.forEach((name, index) => {
        productionColorMap[name] = productionColors[index % productionColors.length];
    });
    for (const name in productionData) {
        const trace = {
            x: Object.keys(productionData[name]),
            y: Object.values(productionData[name]),
            type: 'scatter',
            mode: 'lines',
            marker: { color: productionColorMap[name] },
            line: { shape: 'spline' },
            name: name,
            hovertemplate: "%{x}<br>%{y:.2f} MW<extra></extra>"
        };
        productionTraces.push(trace);
    }
    // Add production traces to the plot
    Plotly.addTraces('temporal-plot', productionTraces);
}