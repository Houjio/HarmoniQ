// $(window).on('resize', function () {
//     Plotly.Plots.resize('sankey-plot');
//     Plotly.relayout('sankey-plot', { 'yaxis.autorange': true });

//     Plotly.Plots.resize('production-plot');
//     Plotly.relayout('production-plot', { 'yaxis.autorange': true });
// });

// function initialise_sankey() {
//     let trace = {
//         x: [],
//         y: [],
//         type: 'sankey',
//     };
//     let data = [trace];
//     let layout = {
//         title: 'Sankey',
//     };
//     Plotly.newPlot('sankey-plot', data, layout);
// };

// $('button[data-bs-target="#production"]').on('shown.bs.tab', function () {
//     Plotly.Plots.resize('production-plot');
//     Plotly.relayout('production-plot', { 'yaxis.autorange': true });
// });

// function charger_production(scenario_id) {
//     $.post(`api/faker/production?scenario_id=${scenario_id}`, function (response) {
//         console.log('Temps: ', response.temps);
//         console.log('Production: ', response.production);
//         let trace = {
//             x: Object.values(response.temps),
//             y: Object.values(response.production),
//             type: 'scatter',
//             mode: 'lines',
//             name: 'Production'
//         };

//         let data = [trace];
//         let layout = {
//             title: 'Production au Fil du Temps',
//             xaxis: { title: 'Temps', tickformat: '%d/%m/%Y' },
//             yaxis: { title: 'Production' },
//             locale: 'fr',
//         };
//         Plotly.newPlot('production-plot', data, layout);
//     }).fail(function (error) {
//         console.error('Error loading production data:', error);
//     });
// }