$('button[data-bs-target="#plot"]').on('shown.bs.tab', function () {
    let trace = {
        x: [],
        y: [],
        type: 'scatter'
    };
    let data = [trace];
    let layout = {
        title: 'Production d\'énergie',
        xaxis: { title: 'Production (MW)' },
        yaxis: { title: 'Temps' },
        margin: { t: 0 },

    };
    Plotly.newPlot('production-plot', data, layout);
});