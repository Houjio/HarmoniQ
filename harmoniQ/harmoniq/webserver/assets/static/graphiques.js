// $(window).on('resize', function () {
//     Plotly.Plots.resize('sankey-plot');
//     Plotly.relayout('sankey-plot', { 'yaxis.autorange': true });

//     Plotly.Plots.resize('temporal-plot');
//     Plotly.relayout('temporal-plot', { 'yaxis.autorange': true });
// });

function initialise_sankey() {
    let trace = {
        x: [],
        y: [],
        type: 'sankey',
    };
    let data = [trace];
    let layout = {
        title: 'Sankey',
    };
    Plotly.newPlot('sankey-plot', data, layout);
};

// $('button[data-bs-target="#sankey"]').on('shown.bs.tab', function () {
//     Plotly.Plots.resize('sankey-plot');
//     Plotly.relayout('sankey-plot', { 'yaxis.autorange': true });
// });

function initialise_temporal() {
    if (typeof demande === 'undefined' || demande === null) {
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

// window.onload = function () {
//     // initialise_sankey();
//     // initialise_temporal();
// };
