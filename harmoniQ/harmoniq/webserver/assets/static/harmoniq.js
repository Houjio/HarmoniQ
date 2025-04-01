// Utility function to fetch data and handle errors
function fetchData(url, method = 'GET', data = null) {
    return fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: data ? JSON.stringify(data) : null
    }).then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
    });
}

// Utility function to toggle button state
function toggleButtonState(buttonId, state) {
    $(`#${buttonId}`).prop('disabled', !state);
}

// Utility function to update list items
function updateListItems(listElement, items, activeIds = []) {
    listElement.innerHTML = '';
    items.forEach(item => {
        const isActive = activeIds.includes(item.id.toString());
        listElement.innerHTML += `
            <li class="list-group-item list-group-item-action ${isActive ? 'list-group-item-secondary' : ''}" 
                role="button" elementid="${item.id}" 
                ${isActive ? 'active="true"' : ''} 
                onclick="add_infra(this)">
                ${item.nom}
            </li>`;
    });
}

// Unimplemented function alert
function unimplemented() {
    alert('Fonctionnalité non implémentée');
}

// Initialize dropdown lists
function initializeDropdown(apiUrl, dropdownId, noSelectionCallback) {
    fetchData(apiUrl)
        .then(data => {
            const dropdown = document.getElementById(dropdownId);
            dropdown.innerHTML = '';
            data.forEach(item => {
                const option = document.createElement('option');
                option.value = item.id;
                option.textContent = item.nom;
                dropdown.appendChild(option);
            });
            noSelectionCallback();
        })
        .catch(error => console.error(`Error loading ${dropdownId}:`, error));
}

// Initialize scenarios
function initialiserListeScenario() {
    initializeDropdown('/api/scenario', 'scenario-actif', no_selection_scenario);
}

// Initialize infrastructure groups
function initialiserListeInfra() {
    initializeDropdown('/api/listeinfrastructures', 'groupe-actif', no_selection_infra);
}

// Initialize wind parks
function initialiserListeParc(type, elementId) {
    const listeElement = document.getElementById(elementId).getElementsByTagName('ul')[0];
    
    const icons = {
        eolien: L.icon({
            iconUrl: '/static/icons/heolienne.png',
            iconSize: [40, 40],
            iconAnchor: [20, 20]
        }),
        solaire: L.icon({
            iconUrl: '/static/icons/solaire.png',
            iconSize: [40, 40],
            iconAnchor: [20, 20]
        }),
        thermique: L.icon({
            iconUrl: '/static/icons/thermique.png',
            iconSize: [40, 40],
            iconAnchor: [20, 20]
        }),
        barrage: L.icon({
            iconUrl: '/static/icons/barrage.png',
            iconSize: [40, 40],
            iconAnchor: [20, 20]
        })
    };
    function createElement({ nom, id }) {
        return `
            <li class="list-group-item list-group-item-action" role="button" elementid=${id} onclick="add_infra(this)">
                ${nom}
            </li>
        `;
    }
    fetch(`/api/${type}`)
        .then(response => response.json())
        .then(data => {
            console.log(`Liste des ${type}:`, data);
            data.forEach(parc => {
                listeElement.innerHTML += createElement(parc);

                // Ajouter un marqueur sur la carte pour chaque parc
                const { categorie, latitude, longitude, nom } = parc;

                // Vérifier si la catégorie a une icône définie
                if (icons[categorie]) {
                    L.marker([latitude, longitude], { icon: icons[categorie] })
                        .addTo(map)
                        .bindPopup(`<b>${nom}</b><br>Catégorie: ${categorie}`);
                } else {
                    console.warn(`Aucune icône définie pour la catégorie: ${categorie}`);
                }
            });
        })
        .catch(error => console.error(`Erreur lors du chargement des parcs ${type}:`, error));
}

function initialiserListeParcEolienne() {
    initialiserListeParc('eolienneparc', 'list-parc-eolien');
}

function initialiserListeParcSolaire() {
    initialiserListeParc('solaire', 'list-parc-solaire');
}

function initialiserListeThermique() {
    initialiserListeParc('thermique', 'list-parc-thermique');
}

window.onload = function() {
    initialiserListeScenario();
    initialiserListeInfra();
    initialiserListeParcEolienne();
    initialiserListeParcSolaire();
    initialiserListeThermique();
};



function changeInfra() {
    const selectedId = $("#groupe-actif option:selected").val();
    fetchData(`/api/listeinfrastructures/${selectedId}`)
        .then(data => {
            const categories = [
                { elementId: "list-parc-eolien", activeIds: data.parc_eoliens.split(',') },
                { elementId: "solarCollapse", activeIds: data.parc_solaires.split(',') },
                { elementId: "list-parc-thermique", activeIds: data.central_thermique.split(',') }
            ];

            categories.forEach(({ elementId, activeIds }) => {
                const elements = document.getElementById(elementId).getElementsByTagName("li");
                updateListItems(elements, Array.from(elements), activeIds);
            });

            $("#active-groupe-title").text(data.nom).removeClass('text-muted');
            $("#enregistrer-groupe").show();
            unblock_run();
        })
        .catch(error => console.error('Error loading infrastructure group:', error));
}

function changeScenario() {
    const id = $("#scenario-actif").val();
    fetchData(`/api/scenario/${id}`)
        .then(data => {
            const scenarioCard = $('#scenario-info');
            scenarioCard.show();
            scenarioCard.find('.scenario-nom').text(data.nom);
            scenarioCard.find('.description').text(data.description);
            scenarioCard.find('.scenario-debut').text(moment(data.date_de_debut).format('LL'));
            scenarioCard.find('.scenario-fin').text(moment(data.date_de_fin).format('LL'));
            scenarioCard.find('.scenario-pas').text(moment.duration(data.pas_de_temps).humanize());
            scenarioCard.find('.optimisme-social').text(['Pessimiste', 'Moyen', 'Optimiste'][data.optimisme_social - 1]);
            scenarioCard.find('.optimisme-ecologique').text(['Pessimiste', 'Moyen', 'Optimiste'][data.optimisme_ecologique - 1]);

            $("#active-scenario-title").text(data.nom).removeClass('text-muted');
            $("#delete-scenario").find("span").text(data.nom).show();
            unblock_run();
        })
        .catch(error => console.error('Error loading scenario:', error));
}

function save_groupe() {
    const values = load_groupe_ids();
    fetchData(`/api/listeinfrastructures/${$("#groupe-actif").val()}`, 'PUT', values)
        .then(response => console.log('Infrastructure group saved successfully:', response))
        .catch(error => console.error('Error saving infrastructure group:', error));
    toggleButtonState("enregistrer-groupe", false);
}

function unblock_run() {
    const scenarioActif = $('#scenario-actif').val();
    const groupeActif = $('#groupe-actif').val();
    toggleButtonState('run', scenarioActif && groupeActif);
}

function lancer_simulation() {
    let scenario = parseInt($('#scenario-actif').val(), 10);
    let groupe = parseInt($('#groupe-actif').val(), 10);

    if (scenario === '' || scenario === null || groupe === '' || groupe === null) {
        alert('Veuillez sélectionner un scenario et un groupe d\'infrastructures');
        return;
    }

    $.ajax({
        type: 'POST',
        url: `/api/simulation?scenario_id=${scenario}&liste_infra_id=${groupe}`,
        contentType: 'application/json',
        success: function(response) {
            console.log('Simulation lancée avec succès:', response);
        },
        error: function(error) {
            if (error.status === 501) {
                alert('Fonctionnalité non implémentée');
            }
            console.error('Erreur lors du lancement de la simulation:', error);
        }
    });
}

function add_infra(element) {
    // Fail if no group is selected
    if ($('#groupe-actif').val() === '' || $('#groupe-actif').val() === null) {
        alert('Veuillez sélectionner un groupe d\'infrastructures');
        return;
    }

    element.classList.toggle('list-group-item-secondary');
    if (element.getAttribute('active') === 'true') {
        element.removeAttribute('active');
    } else {
        element.setAttribute('active', 'true');
    }

    $("#enregistrer-groupe").prop("disabled", false);
}

$("button.select-all").on('click', function(target) {
    if ($('#groupe-actif').val() === '' || $('#groupe-actif').val() === null) {
        alert('Veuillez sélectionner un groupe d\'infrastructures');
        return;
    }

    let div = $(target.target).closest('.accordion-body');
    div.find('.list-group-item').each(function() {
        this.classList.add('list-group-item-secondary');
        this.setAttribute('active', 'true');
    });

    $("#enregistrer-groupe").prop("disabled", false);
});

$("button.select-none").on('click', function(target) {
    if ($('#groupe-actif').val() === '' || $('#groupe-actif').val() === null) {
        alert('Veuillez sélectionner un groupe d\'infrastructures');
        return;
    }

    let div = $(target.target).closest('.accordion-body');
    div.find('.list-group-item').each(function() {
        this.classList.remove('list-group-item-secondary');
        this.removeAttribute('active');
    });

    $("#enregistrer-groupe").prop("disabled", false);
});

function deleteScenario(id) {
    fetch('/api/scenario/' + id, {
        method: 'DELETE'
    })
    .then(response => {
        console.log('Scenario supprimé avec succès:', response);
        document.getElementById('scenario-actif').removeChild(document.getElementById('scenario-actif').selectedOptions[0]);
        no_selection_scenario();
    })
    .catch(error => console.error('Erreur lors de la suppression du scenario:', error));
}

function confirmDeleteScenario(id, nom) {
    if (confirm('Êtes-vous sûr de vouloir supprimer ' + nom + '?')) {
        deleteScenario(id);
    }
}

function load_groupe_ids() {
    const active_name = $("#groupe-actif option:selected").text();
    const categories = [
        { elementId: "list-parc-eolien", key: "selected_eolienes" },
        { elementId: "solarCollapse", key: "selected_solaires" },
        { elementId: "list-parc-thermique", key: "selected_thermiques" }
    ];

    const selectedItems = {};

    categories.forEach(({ elementId, key }) => {
        const elements = document.getElementById(elementId).getElementsByTagName("li");
        selectedItems[key] = Array.from(elements)
            .filter(element => element.getAttribute('active') === 'true')
            .map(element => element.getAttribute('elementid'))
            .join(',');
    });

    const { selected_eolienes, selected_solaires, selected_thermiques } = selectedItems;
    
    const data = {
        nom: active_name,
        parc_eoliens: selected_eolienes,
        parc_solaires: selected_solaires,
        central_hydroelectriques: "",
        central_thermique: selected_thermiques
    };

    return data;
}

function save_groupe() {
    var values = load_groupe_ids();

    $.ajax({
        type: 'PUT',
        url: '/api/listeinfrastructures/' + $("#groupe-actif").val(),
        data: JSON.stringify(values),
        contentType: 'application/json',
        success: function(response) {
            console.log('Groupe d\'infrastructures enregistré avec succès:', response);
        },
        error: function(error) {
            console.error('Erreur lors de l\'enregistrement du groupe d\'infrastructures:', error);
        }
    });

    $("#enregistrer-groupe").prop("disabled", true);
}

function no_selection_scenario() {
    let scenario_card = $('#scenario-info');
    scenario_card.hide();
    $('#scenario-actif').val('');
    $('#delete-scenario').hide();

    $("#active-scenario-title").text("N/A");
    $("#active-scenario-title").addClass('text-muted');
    $('#run').prop('disabled', true);
}

function no_selection_infra() {
    $("#groupe-actif").val('');
    $("#active-groupe-title").text("N/A");
    $("#active-groupe-title").addClass("text-muted");
    $("#enregistrer-groupe").hide();
    $('#run').prop('disabled', true);
}

function changeInfra() {
    let selectedId = $("#groupe-actif option:selected").val();

    fetch('/api/listeinfrastructures/' + selectedId)
        .then(response => response.json())
        .then(data => {
            console.log('Groupe d\'infrastructures actif:', data);

            const categories = [
                { elementId: "list-parc-eolien", activeIds: data.parc_eoliens.split(',') },
                { elementId: "list-parc-solaire", activeIds: data.parc_solaires.split(',') },
                { elementId: "list-parc-thermique", activeIds: data.central_thermique.split(',') }
            ];

            categories.forEach(({ elementId, activeIds }) => {
                const elements = document.getElementById(elementId).getElementsByTagName("li");
                Array.from(elements).forEach(element => {
                    if (activeIds.includes(element.getAttribute('elementid'))) {
                        element.classList.add('list-group-item-secondary');
                        element.setAttribute('active', 'true');
                    } else {
                        element.classList.remove('list-group-item-secondary');
                        element.removeAttribute('active');
                    }
                });
            });

            $("#active-groupe-title").text(data.nom);
            $("#active-groupe-title").removeClass('text-muted');
            $("#enregistrer-groupe").show();
            unblock_run();
        })
        .catch(error => console.error('Erreur lors du chargement du groupe d\'infrastructures:', error));
}

function updateOptimismeText(card, type, value) {
    const labels = ["Pessimiste", "Moyen", "Optimiste"];
    card.find(`.optimisme-${type}`).text(labels[value - 1]);
}

function changeScenario() {
    let id = $("#scenario-actif").val();
    
    // Get data from the scenario id
    fetch('/api/scenario/' + id)
        .then(response => response.json())
        .then(data => {
            console.log('Scenario actif:', data);
            let scenario_card = $('#scenario-info');
            scenario_card.show();
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

            updateOptimismeText(scenario_card, 'social', data.optimisme_social);
            updateOptimismeText(scenario_card, 'ecologique', data.optimisme_ecologique);

            $("#active-scenario-title").text(data.nom);
            $("#active-scenario-title").removeClass('text-muted');
            $("#delete-scenario").find("span").text(data.nom);
            $("#delete-scenario").show();

            unblock_run();
        })
        .catch(error => console.error('Erreur lors du chargement du scenario:', error));
}

function unblock_run() {
    let scenarioActif = $('#scenario-actif').val();
    let groupeActif = $('#groupe-actif').val();

    if (scenarioActif && groupeActif) {
        $('#run').prop('disabled', false);
    } else {
        $('#run').prop('disabled', true);
    }
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
                var option = document.createElement('option');
                option.value = response.id;
                option.textContent = response.nom;
                document.getElementById('scenario-actif').appendChild(option);
                $('#dataModal').modal('hide');
                setTimeout(function() {
                    no_selection_scenario()
                }
                , 50);
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
    if (nom === null || nom === "") {
        return;
    }

    var data = {
        nom: nom,
        parc_eoliens: "",
        parc_solaire: "",
        central_hydroelectriques: "",
        central_thermique: ""
    };

    $.ajax({
        type: 'POST',
        url: '/api/listeinfrastructures',
        data: JSON.stringify(data),
        contentType: 'application/json',
        success: function(response) {
            console.log('Groupe d\'infrastructures créé avec succès:', response);
            var option = document.createElement('option');
            option.value = response.id;
            option.textContent = response.nom;
            document.getElementById('groupe-actif').appendChild(option);
            setTimeout(function() {
                no_selection_infra()
            }
            , 50);
        },
        error: function(error) {
            console.error('Erreur lors de la création du groupe d\'infrastructures:', error);
        }
    });
});

$('#delete-scenario').on('click', function() {
    let id = $("#scenario-actif").val();
    let nom = $("#scenario-actif option:selected").text();
    confirmDeleteScenario(id, nom);
});

document.addEventListener("DOMContentLoaded", function() {
    var map = L.map('map-box', {
        zoomControl: true,
        attributionControl: true,
        maxZoom: 10,
        minZoom: 5
    }).setView([52.9399, -67], 4);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    var bounds = [
        [40.0, -90.0], 
        [65.0, -50.0] 
    ];
    map.setMaxBounds(bounds);
    map.on('drag', function() {
        map.panInsideBounds(bounds, { animate: false });
    });
});
