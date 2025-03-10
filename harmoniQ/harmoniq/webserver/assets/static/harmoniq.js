function plot_results_parc_eolien(data) {
    let layout = {
        title: 'Production éolienne',
        xaxis: {
            title: 'Temps'
        },
        yaxis: {
            title: 'Production (MW)'
        }
    };

    let production = data.production

    let traces = [{
        x: Object.keys(production).map(timestamp => moment.unix(parseInt(timestamp)).format('LLL')),
        y: Object.values(production).map(value => value / 1000000), // Convert W to MW
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Production'
    }];

    Plotly.newPlot('plots', traces, layout);
}

function simuler(id, type) {
    // Check scenario actif
    let scenario_actif = $("#scenario").attr("scenario-actif");
    if (!scenario_actif) {
        alert("Veuillez choisir un scenario actif");
        return;
    }

    if (type === 'eolienne') {
        let eolienne = $("#eolienne-" + id);
        let button = eolienne.find('button.btn-primary');
        button.prop('disabled', true);
        button.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Simulation...');

        setTimeout(function() {
            $.ajax({
                type: 'POST',
                url: '/api/eolienneparc/' + id + '/production?scenario_id=' + parseInt(scenario_actif),
                contentType: 'application/json',
                async: false,
                timeout: 50000,
                success: function(response) {
                    response = JSON.parse(response);
                    console.log('Simulation réussie:', response);

                    plot_results_parc_eolien(response);
                },
                error: function(error) {
                    console.error('Erreur lors de la simulation:', error);
                    alert('Erreur lors de la simulation');
                },
                complete: function() {
                    button.prop('disabled', false);
                    button.html('Simuler');
                }
            });
        }, 10);
    }
}

function initialiserListeParcEolienne() {
    const listeParcEolienne = document.getElementById('list-parc-eolien');

    function creerElement({ id, nom, capacite_total, nombre_eoliennes }) {
        return `
            <div class="card mb-3" id="eolienne-${id}">
                <div class="card-body">
                    <h5 class="card-title">${nom}</h5>
                    <table class="table table-borderless mb-3">
                        <tbody>
                            <tr>
                                <td style="background-color: transparent; padding: 0;">Capacité:</td>
                                <td style="background-color: transparent; padding: 0;">${capacite_total.toFixed(2)} MW</td>
                            </tr>
                            <tr>
                                <td style="background-color: transparent; padding: 0;"># d'éoliennes:</td>
                                <td style="background-color: transparent; padding: 0;">${nombre_eoliennes}</td>
                            </tr>
                        </tbody>
                    </table>
                    <div class="d-flex w-100 justify-content-end">
                        <button class="btn btn-secondary mx-2" onclick="eolienne_modal(${id}, '${nom}')">Détails</button>
                        <button class="btn btn-primary" onclick="simuler(${id}, 'eolienne')">Simuler</button>
                    </div>
                </div>
            </div>
        `;
    }
    
    fetch('/api/eolienneparc/')
        .then(response => response.json())
        .then(data => {
            listeParcEolienne.innerHTML = data.map(creerElement).join('');
        })
        .catch(error => console.error('Erreur lors du chargement des parcs éoliens:', error));
}


function eolienne_modal(id, nom_proj) {
    function creerModal(data, nom_proj) {
        let model = data[0].modele_turbine;
        let turbine_count = data.length;
        return `
             <div class="modal-dialog" role="document">
                <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">${nom_proj}</h5>
                    <button type="button" class="close" data-bs-dismiss="modal" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div class="modal-body">
                    <p>${turbine_count} éolienne de type ${model}</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fermer</button>
                </div>
                </div>
            </div>
        `;
    }

    fetch('/api/eolienne/parc/' + id)
        .then(response => response.json())
        .then(data => {

            document.getElementById('dataModal').innerHTML = creerModal(data, nom_proj);
            $('#dataModal').modal('show');
        })
        .catch(error => console.error('Erreur lors du chargement des détails du parc éolien:', error));
}

function deleteScenario(id) {
    fetch('/api/scenario/' + id, {
        method: 'DELETE'
    })
    .then(response => {
        console.log('Scenario supprimé avec succès:', response);
        document.getElementById('scenario-' + id).remove();
    })
    .catch(error => console.error('Erreur lors de la suppression du scenario:', error));
}

function confirmDeleteScenario(id, nom) {
    if (confirm('Êtes-vous sûr de vouloir supprimer ' + nom + '?')) {
        deleteScenario(id);
    }
}

function scenarioActif(id) {
    $("#scenario-actif-text").text("Actif: " + $("#scenario-" + id).find("p").first().text());

    
    let prev_active = $("#scenario").attr("scenario-actif");
    if (prev_active) {
        document.getElementById('scenario-' + prev_active).classList.remove('alert-info');
        document.getElementById('scenario-' + prev_active).querySelector('button.btn-primary').disabled = false;
    }

    document.getElementById('scenario-' + id).classList.add('alert-info');
    $("#scenario").attr("scenario-actif", id);
    document.getElementById('scenario-' + id).querySelector('button.btn-primary').disabled = true;
}

function creerElementListScenario({ id, nom, description, date_de_debut, date_de_fin, pas_de_temps, optimisme_social, optimisme_ecologique }) {
    // Convert the times and dates to a more readable format
    date_de_debut = moment(date_de_debut).format('LL');
    date_de_fin = moment(date_de_fin).format('LL');
    pas_de_temps = moment.duration(pas_de_temps).humanize();

    // Convert the optimism values to a more readable format
    switch (optimisme_social) {
        case 1:
            optimisme_social = 'Pessimisme social';
            break;
        case 2:
            optimisme_social = 'Neutre social';
            break;
        case 3:
            optimisme_social = 'Optimisme social';
            break;
    }

    switch (optimisme_ecologique) {
        case 1:
            optimisme_ecologique = 'Pessimisme écologique';
            break;
        case 2:
            optimisme_ecologique = 'Neutre écologique';
            break;
        case 3:
            optimisme_ecologique = 'Optimisme écologique';
            break;
    }

    return `
        <li class="list-group-item" id="scenario-${id}">
            <div class="d-flex w-100 justify-content-between">
                <p class="fw-bold">${nom}</p>
                <p>${date_de_debut} à ${date_de_fin} (int. ${pas_de_temps})</p>
            </div>
            <div class="d-flex w-100 justify-content-between">
                <p>${description}</p>
                <p>${optimisme_social}, ${optimisme_ecologique}</p>
            </div>
            <div class="d-flex w-100 justify-content-end">
                <button class="btn btn-danger mx-2" style="font-size: 0.75rem;" onclick="confirmDeleteScenario(${id}, '${nom}')"><i class="fa fa-trash"></i></button>
                <button class="btn btn-primary" style="font-size: 0.75rem;" onclick="scenarioActif(${id})">Rendre Actif</button>
        </li>
    `;
}   


function initialiserListeScenario() {
    fetch('/api/scenario')
        .then(response => response.json())
        .then(data => {
            document.getElementById('scenario-list').innerHTML = data.map(creerElementListScenario).join('');
        })
        .catch(error => console.error('Erreur lors du chargement des scenario:', error));
}

function nouveauScenario() {
    function creerModal() {
        return `
            <div class="modal-dialog" role="document">
            <form id="form-nouveau-scenario">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Créer nouveau scenario</h5>
                        <button type="button" class="close" data-bs-dismiss="modal" aria-label="Close">
                            <span aria-hidden="true">&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group">
                            <label for="nom">Nom du scenario</label>
                            <input type="text" class="form-control" id="scenario-nom" placeholder="Nom du scenario">
                            <label for="description">Description</label>
                            <textarea class="form-control" id="scenario-description" rows="3"></textarea>
                            <label for="etendue_de_temps">Étendue de temps</label>
                            <input type="text" name="etendue_de_temps" class="form-control" id="scenario-etendue_de_temps">
                            <label for="pas_de_temps">Pas de temps</label>
                            <select class="form-control" id="scenario-pas_de_temps">
                                <option value="PT15M">15 minutes</option>
                                <option value="PT1H" selected>1 heure</option>
                                <option value="PT4H">4 heures</option>
                                <option value="P1D">1 jour</option>
                                <opton value="P7D">7 jours</option>
                            </select>
                            <label for="optimisme_social">Optimisme social</label>
                            <select class="form-control" id="scenario-optimisme_social">
                                <option value="1">Pessimiste</option>
                                <option value="2" selected>Moyen</option>
                                <option value="3">Optimiste</option>
                            </select>
                            <label for="optimisme_ecologique">Optimisme écologique</label>
                            <select class="form-control" id="scenario-optimisme_ecologique">
                                <option value="1">Pessimiste</option>
                                <option value="2" selected>Moyen</option>
                                <option value="3">Optimiste</option>
                            </select>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fermer</button>
                        <input type="submit" class="btn btn-primary" value="Créer">
                    </div>
                </div>
                </form>
            </div>
        `;
    }

    document.getElementById('dataModal').innerHTML = creerModal();

    // Fonction pour initialiser le datepicker
    $('#scenario-etendue_de_temps').daterangepicker({
        format: "dd/mm/yyyy",
        showDropdowns: true,
        minYear: 2010,
        maxYear: 2050,
        locale: {
            applyLabel: "Sélectionner",
            cancelLabel: "Annuler",
        },
    });

    // Fonction pour envoyer le formulaire
    $("#form-nouveau-scenario").submit(function(event) {
        event.preventDefault();
        let nom = $('#scenario-nom').val();
        let description = $('#scenario-description').val();
        let pas_de_temps = $('#scenario-pas_de_temps').val();
        let date_de_debut = $('#scenario-etendue_de_temps').data('daterangepicker').startDate.format('YYYY-MM-DD');
        let date_de_fin = $('#scenario-etendue_de_temps').data('daterangepicker').endDate.format('YYYY-MM-DD');
        let optimisme_social = parseInt($('#scenario-optimisme_social').val());
        let optimisme_ecologique = parseInt($('#scenario-optimisme_ecologique').val());

        let data = {
            nom: nom,
            description: description,
            date_de_debut: date_de_debut,
            date_de_fin: date_de_fin,
            pas_de_temps: pas_de_temps,
            optimisme_social: optimisme_social,
            optimisme_ecologique: optimisme_ecologique
        };

        // Validation des données
        if (nom === '' || description === '' || pas_de_temps === '' || date_de_debut === '' || date_de_fin === '') {
            alert('Veuillez remplir tous les champs');
            return;
        }

        $.ajax({
            type: 'POST',
            url: '/api/scenario',
            data: JSON.stringify(data),
            contentType: 'application/json',
            success: function(response) {
                console.log('Scenario créé avec succès:', response);
                var liElement = creerElementListScenario(response);
                document.getElementById('scenario-list').innerHTML += liElement;
                $('#dataModal').modal('hide');
            },
            error: function(error) {
                console.error('Erreur lors de la création du scenario:', error);
            }
        });
    });

    $('#dataModal').modal('show');
}

$('#add-scenario').on('click', function() {
    nouveauScenario();
});

window.onload = function() {
    initialiserListeScenario();
    initialiserListeParcEolienne();
};