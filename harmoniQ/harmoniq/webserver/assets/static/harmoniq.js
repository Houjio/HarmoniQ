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
        x: Object.keys(production).map(timestamp => new Date(parseInt(timestamp) * 1000).toLocaleString()),
    y: Object.values(production).map(value => value / 1000000), // Convert W to MW
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Production'
    }];

    layout.xaxis.tickformat = '%d-%m-%Y %H:%M';
    layout.width = '100%';
    layout.height = '100%';
    Plotly.newPlot('plot-box', traces, layout);
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
        no_selection_scenario();
    })
    .catch(error => console.error('Erreur lors de la suppression du scenario:', error));
}

function confirmDeleteScenario(id, nom) {
    if (confirm('Êtes-vous sûr de vouloir supprimer ' + nom + '?')) {
        deleteScenario(id);
    }
}

function initialiserListeScenario() {
    fetch('/api/scenario')
        .then(response => response.json())
        .then(data => {
            data.forEach(scenario => {
                let option = document.createElement('option');
                option.value = scenario.id;
                option.textContent = scenario.nom;
                document.getElementById('scenario-actif').appendChild(option);
                no_selection_scenario();
            });
        })
        
        .catch(error => console.error('Erreur lors du chargement des scenario:', error));
}

function initialiserListeInfra() {
    fetch('/api/listeinfrastructures')
        .then(response => response.json())
        .then(data => {
            data.forEach(groupeinfra => {
                let option = document.createElement('option');
                option.value = groupeinfra.id;
                option.textContent = groupeinfra.nom;
                document.getElementById('groupe-actif').appendChild(option);
                no_slection_infra();
            });
        })
        
        .catch(error => console.error('Erreur lors du chargement des groupes d\'infrastructures:', error));
}

function no_selection_scenario() {
    let scenario_card = $('#scenario-info');
    scenario_card.hide();
    $('#scenario-actif').val('');
    $('#delete-scenario').hide();
}

function no_slection_infra() {
    $("#groupe-actif").val('');
}

function changeScenario() {
    let id = $("#scenario-actif").val();
    
    // Get data from the scenario id
    fetch('/api/scenario/' + id)
        .then(response => response.json())
        .then(data => {
            console.log('Scenario actif:', data);
            let scenario_card = $('#scenario-info');
            scenario_card.show()
            scenario_card.find('.scenario-nom').text(data.nom);
            scenario_card.find('.description').text(data.description);  
            scenario_card.find('.scenario-debut').text(
                moment(data.date_de_debut).format('LL')
            );
            scenario_card.find('.scenario-fin').text(
                moment(data.date_de_fin).format('LL')
            );
            scenario_card.find('.scenario-pas').text(
                moment.duration(data.pas_de_temps).humanize()
            );

            switch (data.optimisme_ecologique) {
                case 1:
                    scenario_card.find('.optimisme-social').text("Pessimiste");
                    break;
                case 2:
                    scenario_card.find('.optimisme-social').text("Moyen");
                    break;
                case 3:
                    scenario_card.find('.optimisme-social').text("Optimiste");
                    break;
            }

            switch (data.optimisme_ecologique) {
                case 1:
                    scenario_card.find('.optimisme-ecologique').text("Pessimiste");
                    break;
                case 2:
                    scenario_card.find('.optimisme-ecologique').text("Moyen");
                    break;
                case 3:
                    scenario_card.find('.optimisme-ecologique').text("Optimiste");
                    break;
            }

            $("#delete-scenario").find("span").text(data.nom);
            $("#delete-scenario").show();
        })
        .catch(error => console.error('Erreur lors du chargement du scenario:', error));
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

$('#add-infra-liste').on('click', function() {
    var nom = window.prompt("Nom du nouveaux groupe: ");
});

$('#delete-scenario').on('click', function() {
    let id = $("#scenario-actif").val();
    let nom = $("#scenario-actif option:selected").text();
    confirmDeleteScenario(id, nom);
});

window.onload = function() {
    initialiserListeScenario();
    initialiserListeInfra();
    initialiserListeParcEolienne();
};