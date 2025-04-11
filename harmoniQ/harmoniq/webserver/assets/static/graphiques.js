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
