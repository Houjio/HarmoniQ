$('button[data-bs-target="#sankey"]').on('shown.bs.tab', function () {
    if (typeof demandeSankey === 'undefined' || demandeSankey === null) {
        return;
    }

    Plotly.Plots.resize('sankey-plot');
    Plotly.relayout('sankey-plot', { 'yaxis.autorange': true });
});

function initialise_temporal() {
    if (typeof demandeTemporel === 'undefined' || demandeTemporel === null) {
        return;
    }

    // Empty the plot
    $('#temporal-plot').empty();

    let trace = {
        x: [],
        y: [],
        type: 'scatter',
        mode: 'lines',
    };
    let data = [trace];
    let layout = {
        title: 'Production/Demande au Fil du Temps',
        xaxis: { title: 'Temps', tickformat: '%d/%m/%Y' },
        yaxis: { title: 'Production' },
        locale: 'fr',
    };
    Plotly.newPlot('temporal-plot', data, layout);
}

$('button[data-bs-target="#temporal"]').on('shown.bs.tab', function () {
    initialise_temporal();
});
