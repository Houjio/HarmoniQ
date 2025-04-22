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
        values.push(demandeSankey.total_electricity[i] / 1_000_000); // kWh → GWh

        // Gaz to sector
        sources.push(gazSourceIndex);
        targets.push(targetIndex);
        values.push(demandeSankey.total_gaz[i] / 1_000_000); // kWh → GWh
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
            value: values,
            hovertemplate: "%{source.label} → %{target.label}<br>%{value:.2f} GWh<extra></extra>"
        }
    }];

    const layout = {
        title: "Flux d'énergie vers les secteurs pour scénario " + $("#scenario-actif option:selected").text() + " (en GWh)",
        font: { size: 10 }
    };

    Plotly.newPlot("sankey-plot", sankeyData, layout);
}


function generateTemporalPlot() {
    const xval = Object.keys(demandeTemporal.total_electricity);
    const yval = Object.values(demandeTemporal.total_electricity).map(value => value/1000000);

    const layout = {
        title: "Demande pour scénario " + $("#scenario-actif option:selected").text(),
        xaxis: {
            title: "Date",
            tickformat: "%d %b %Y"
        },
        yaxis: {
            title: "Demande (GW)",
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
        hovertemplate: "%{x}<br>%{y:.2f} GW<extra></extra>"
    };

    Plotly.newPlot("temporal-plot", [trace], layout);
}

function updateTemporalGraph() {
    // Add production traces
    const productionData = production.production;
    let x = productionData.map(instance => (instance["snapshot"]));
    let y = productionData.map(instance => (instance["totale"]/ 1000));
    let eolien = productionData.map(instance => (instance["total_eolien"]/ 1000));
    let solaire = productionData.map(instance => (instance["total_solaire"]/ 1000));
    let hydro_fil = productionData.map(instance => (instance["total_hydro_fil"]/ 1000));
    let hydro_res = productionData.map(instance => (instance["total_hydro_reservoir"]/ 1000));
    let imports = productionData.map(instance => (instance["total_import"]/ 1000));
    let nucleaire = productionData.map(instance => (instance["total_nucleaire"]/ 1000));
    let thermique = productionData.map(instance => (instance["total_thermique"]/ 1000));

    let demandeX = Object.keys(demandeTemporal.total_electricity);
    let demandeY = Object.values(demandeTemporal.total_electricity).map(value => value / 1000000);

    const productionTraces = [
        {
            x: demandeX,
            y: demandeY,
            type: 'scatter',
            mode: 'lines',
            name: 'Demande',
            line: { shape: 'spline', color: 'black' },
            hovertemplate: "%{x}<br>%{y:.2f} GW<extra></extra>"
        },
        {
            x: x,
            y: y,
            type: 'scatter',
            mode: 'lines',
            name: 'Production totale',
            line: { shape: 'spline', color: 'green' },
            hovertemplate: "%{x}<br>%{y:.2f} GW<extra></extra>"
        },
        {
            x: x,
            y: eolien,
            type: 'scatter',
            mode: 'lines',
            name: 'Éolien',
            line: { shape: 'spline', color: 'orange' },
            hovertemplate: "%{x}<br>%{y:.2f} GW<extra></extra>"
        },
        {
            x: x,
            y: solaire,
            type: 'scatter',
            mode: 'lines',
            name: 'Solaire',
            line: { shape: 'spline', color: 'yellow' },
            hovertemplate: "%{x}<br>%{y:.2f} GW<extra></extra>"
        },
        {
            x: x,
            y: hydro_fil,
            type: 'scatter',
            mode: 'lines',
            name: 'Hydro (fil)',
            line: { shape: 'spline', color: 'blue' },
            hovertemplate: "%{x}<br>%{y:.2f} GW<extra></extra>"
        },
        {
            x: x,
            y: hydro_res,
            type: 'scatter',
            mode: 'lines',
            name: 'Hydro (réservoir)',
            line: { shape: 'spline', color: 'cyan' },
            hovertemplate: "%{x}<br>%{y:.2f} GW<extra></extra>"
        },
        {
            x: x,
            y: imports,
            type: 'scatter',
            mode: 'lines',
            name: 'Importations',
            line: { shape: 'spline', color: 'purple' },
            hovertemplate: "%{x}<br>%{y:.2f} GW<extra></extra>"
        },
        {
            x: x,
            y: nucleaire,
            type: 'scatter',
            mode: 'lines',
            name: 'Nucléaire',
            line: { shape: 'spline', color: 'red' },
            hovertemplate: "%{x}<br>%{y:.2f} GW<extra></extra>"
        },
        {
            x: x,
            y: thermique,
            type: 'scatter',
            mode: 'lines',
            name: 'Thermique',
            line: { shape: 'spline', color: 'brown' },
            hovertemplate: "%{x}<br>%{y:.2f} GW<extra></extra>"
        }
    ];

    Plotly.purge("temporal-plot");
    Plotly.newPlot("temporal-plot", productionTraces, {
        title: "Production et Demande pour scénario " + $("#scenario-actif option:selected").text(),
        xaxis: {
            title: "Date",
            tickformat: "%d %b %Y"
        },
        yaxis: {
            title: "Puissance (GW)",
            autorange: true
        },
        legend: {
            orientation: "h",
            yanchor: "bottom",
            y: 1.02,
            xanchor: "right",
            x: 1
        }
    });
}