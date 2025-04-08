let infraTimeout = null;
let scenarioFetchController = null;
var map;
var openApiJson = null;

const map_icons = {
    eolienneparc: L.icon({
        iconUrl: '/static/icons/eolienne.png',
        iconSize: [30, 30],
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
    hydro: L.icon({
        iconUrl: '/static/icons/barrage.png',
        iconSize: [50, 50],
        iconAnchor: [20, 20]
    }),
    nucleaire: L.icon({
        iconUrl: '/static/icons/nucelaire.png',
        iconSize: [40, 40],
        iconAnchor: [20, 20]
    })
};

var prettyNames = {
    eolienneparc: "Parc éolien",
    solaire: "Parc solaire",
    thermique: "Centale thermique",
    nucleaire: "Centrale nucléaire",
    hydro: "Barrage hydroélectrique"
}


// Utility function to fetch data and handle errors
function fetchData(url, method = 'GET', data = null, signal = null) {
    return fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: data ? JSON.stringify(data) : null,
        signal: signal
    })
    .then(response => {
        if (!response.ok) throw new Error(response.statusText);
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

function unimplemented() {
    alert('Fonctionnalité non implémentée');
}

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

function addMarker(lat, lon, type, data) {
    const icon = map_icons[type];

    // Construire le contenu du popup en fonction du type
    let popupContent = `<b>${data.nom}</b><br>Catégorie: ${prettyNames[type]}<br>`;

    if (type === 'eolienneparc') {
        popupContent += `
            Nombre d'éoliennes: ${data.nombre_eoliennes || 'N/A'}<br>
            Puissance nominale: ${data.puissance_nominal || 'N/A'} MW<br>
            Capacité totale: ${data.capacite_total || 'N/A'} MW
        `;
    } else if (type === 'hydro') {
        popupContent += `
            Débit nominal: ${data.debits_nominal || 'N/A'} m³/s<br>
            Nombre de turbines: ${data.nb_turbines || 'N/A'}<br>
            Puissance nominale: ${data.puissance_nominal || 'N/A'} MW<br>
            Volume du réservoir: ${data.volume_reservoir || 'N/A'} m³
        `;
    } else if (type === 'solaire') {
        popupContent += `
            Nombre de panneaux: ${data.nombre_panneau || 'N/A'}<br>
            Orientation des panneaux: ${data.orientation_panneau || 'N/A'}<br>
            Puissance nominale: ${data.puissance_nominal || 'N/A'} MW
        `;
    } else if (type === 'thermique') {
        popupContent += `
            Puissance nominale: ${data.puissance_nominal || 'N/A'} MW<br>
            Type d'intrant: ${data.type_intrant || 'N/A'}
        `;
    }

    // Ajouter le marqueur à la carte avec le popup
    const marker = L.marker([lat, lon], { icon: icon })
        .addTo(map)
        .bindPopup(popupContent);

    marker.on('click', function () {
        this.openPopup();
    });
}

function createListElement({ nom, id }) {
    return `
        <li class="list-group-item list-group-item-action" role="button" elementid=${id} onclick="add_infra(this)">
            ${nom}
        </li>
    `;
}

function initialiserListeParc(type, elementId) {
    const listeElement = document.getElementById(elementId).getElementsByTagName('ul')[0];
    
    fetch(`/api/${type}`)
        .then(response => {
            if (!response.ok) throw new Error(`Erreur HTTP: ${response.status}`);
            return response.json();
        })
        .then(data => {
            console.log(`Liste des ${type}:`, data);
            data.forEach(parc => {
                listeElement.innerHTML += createListElement({ nom: parc.nom, id: parc.id });
                addMarker(parc.latitude, parc.longitude, type, parc);
        });
    })
    .catch(error => console.error(`Erreur lors du chargement des parcs ${type}:`, error));
}

function initialiserListeHydro() {
    initialiserListeParc('hydro', 'list-parc-hydro');
}

function initialiserListeParcEolienne() {
    initialiserListeParc('eolienneparc', 'list-parc-eolienneparc');
}

function initialiserListeParcSolaire() {
    initialiserListeParc('solaire', 'list-parc-solaire');
}

function initialiserListeThermique() {
    initialiserListeParc('thermique', 'list-parc-thermique');
}

function initialiserListeParcNucleaire() {
    initialiserListeParc('nucleaire', 'list-parc-nucleaire');
}

function loadMap() {
    map = L.map('map-box', {
        zoomControl: true,
        attributionControl: true,
        maxZoom: 12,
        minZoom: 5
    }).setView([52.9399, -67], 4);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    var bounds = [
        [40.0, -90.0], 
        [65.0, -50.0] 
    ];
    map.setMaxBounds(bounds);
    map.on('drag', function() {
        map.panInsideBounds(bounds, { animate: false });
    });

    const draggableIcons = document.querySelectorAll(".icon-draggable");

    draggableIcons.forEach(iconEl => {
        iconEl.addEventListener("dragstart", function (e) {
            let create_class = e.target.getAttribute('createClass');
            let post_url = e.target.getAttribute('createApi');

            e.dataTransfer.setData("text/plain", `${create_class},${post_url}`);
        });
    });

    // Prevent map from blocking drop events
    map.getContainer().addEventListener("dragover", function (e) {
        e.preventDefault();
    });

    map.getContainer().addEventListener("drop", function (e) {
        e.preventDefault();
        const [create_class, post_url] =  e.dataTransfer.getData("text/plain").split(",");

        const mapPos = map.getContainer().getBoundingClientRect();
        const x = e.clientX - mapPos.left;
        const y = e.clientY - mapPos.top;

        const latlng = map.containerPointToLatLng([x, y]);

        const lat = parseFloat(latlng.lat.toFixed(6));
        const lng = parseFloat(latlng.lng.toFixed(6));

        infraModal(create_class, post_url, lat, lng);
    });
}

function loadOpenApi() {
    fetch('/openapi.json')
        .then(response => {
            if (!response.ok) throw new Error(`Erreur HTTP: ${response.status}`);
            return response.json();
        })
        .then(data => {
            openApiJson = data;
        })
        .catch(error => console.error('Erreur lors du chargement du fichier OpenAPI:', error));
}

window.onload = function() {
    initialiserListeHydro();
    initialiserListeScenario();
    initialiserListeInfra();
    initialiserListeParcEolienne();
    initialiserListeParcSolaire();
    initialiserListeThermique();
    initialiserListeParcNucleaire();
    modeliserLignes(); 

    loadMap();
    loadOpenApi();
};

function infraUserAction() {
    if (infraTimeout) {
        clearTimeout(infraTimeout);
    }

    infraTimeout = setTimeout(() => {
        save_groupe();
    }, 800);
}

async function save_groupe() {
    const values = load_groupe_ids();
    fetchData(`/api/listeinfrastructures/${$("#groupe-actif").val()}`, 'PUT', values)
        .then(_ => console.log('Infrastructure group auto saved successfully:'))
        .catch(error => console.error('Error saving infrastructure group:', error));
}

function unblock_run() {
    const scenarioActif = $('#scenario-actif').val();
    const groupeActif = $('#groupe-actif').val();
    toggleButtonState('run', scenarioActif && groupeActif);
}

function lancer_simulation() {
    let scenario = parseInt($('#scenario-actif').val());
    let groupe = parseInt($('#groupe-actif').val());

    if (scenario === '' || scenario === null || groupe === '' || groupe === null) {
        alert('Veuillez sélectionner un scenario et un groupe d\'infrastructures');
        return;
    }

    alert("Le graphique est purement à titre indicatif et ne représente pas les données réelles.");
    charger_production(scenario);

    // $.ajax({
    //     type: 'POST',
    //     url: `/api/simulation?scenario_id=${scenario}&liste_infra_id=${groupe}`,
    //     contentType: 'application/json',
    //     success: function(response) {
    //         console.log('Simulation lancée avec succès:', response);
    //     },
    //     error: function(error) {
    //         if (error.status === 501) {
    //             unimplemented();
    //         }
    //         console.error('Erreur lors du lancement de la simulation:', error);
    //     }
    // });
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


    infraUserAction();
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

    infraUserAction();
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

    infraUserAction();
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
        { elementId: "list-parc-hydro", key: "selected_hydro" },
        { elementId: "list-parc-eolienneparc", key: "selected_eolienes" },
        { elementId: "list-parc-solaire", key: "selected_solaires" },
        { elementId: "list-parc-thermique", key: "selected_thermiques" },
        { elementId: "list-parc-nucleaire", key: "selected_nucleaire" }
    ];

    const selectedItems = {};

    categories.forEach(({ elementId, key }) => {
        const elements = document.getElementById(elementId).getElementsByTagName("li");
        selectedItems[key] = Array.from(elements)
            .filter(element => element.getAttribute('active') === 'true')
            .map(element => element.getAttribute('elementid'))
            .join(',');
    });

    const { selected_hydro, selected_eolienes, selected_solaires, selected_thermiques , selected_nucleaire } = selectedItems;
    
    const data = {
        nom: active_name,
        parc_eoliens: selected_eolienes,
        parc_solaires: selected_solaires,
        central_hydroelectriques: selected_hydro,
        central_thermique: selected_thermiques,
        central_nucleaire: selected_nucleaire,
    };

    return data;
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
    $('#run').prop('disabled', true);
}

function changeInfra() {
    let selectedId = $("#groupe-actif option:selected").val();

    fetch('/api/listeinfrastructures/' + selectedId)
        .then(response => response.json())
        .then(data => {
            console.log('Groupe d\'infrastructures actif:', data);

            const categories = [
                { elementId: "list-parc-eolienneparc", activeIds: data.parc_eoliens ? data.parc_eoliens.split(',') : [] },
                { elementId: "list-parc-solaire", activeIds: data.parc_solaires ? data.parc_solaires.split(',') : [] },
                { elementId: "list-parc-thermique", activeIds: data.central_thermique ? data.central_thermique.split(',') : [] },
                { elementId: "list-parc-nucleaire", activeIds: data.central_nucleaire ? data.central_nucleaire.split(',') : [] },
                { elementId: "list-parc-hydro", activeIds: data.central_hydroelectriques ? data.central_hydroelectriques.split(',') : [] }
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
            unblock_run();
        })
        .catch(error => console.error('Erreur lors du chargement du groupe d\'infrastructures:', error));
}

function updateOptimismeText(card, type, value) {
    const labels = ["Pessimiste", "Moyen", "Optimiste"];
    card.find(`.optimisme-${type}`).text(labels[value - 1]);
}

function charger_demande(scenario_id, mrc_id) {
    if (!mrc_id) {
        mrc_id = 1;
    }

    demandeFetchController = new AbortController();
    const signal = demandeFetchController.signal;

    fetchData(`/api/demande/?scenario_id=${scenario_id}&CUID=${mrc_id || ''}`, 'POST', null, signal)
        .then(data => {
            console.log('Demande chargée avec succès:', data);
        })
        .catch(error => {
            if (error.message.includes('404')) {
                console.error('Demande non trouvée:', error);
            } else {
                console.error('Erreur lors du chargement de la demande:', error);
            }
        });
}

function changeScenario() {
    let id = $("#scenario-actif").val();
    
    // Get data from the scenario id
    fetch('/api/scenario/' + id)
        .then(response => response.json())
        .then(data => {
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
            scenario_card.find('.consommation-scenario').text(
                data.consomation === 1 ? 'Normal' : 'Conservateur'
            );
            scenario_card.find('.meteo-scenario').text(
                data.weather === 1 ? 'Chaude' : data.weather === 2 ? 'Typique' : 'Froide'
            );

            updateOptimismeText(scenario_card, 'social', data.optimisme_social);
            updateOptimismeText(scenario_card, 'ecologique', data.optimisme_ecologique);

            $("#active-scenario-title").text(data.nom);
            $("#active-scenario-title").removeClass('text-muted');
            $("#delete-scenario").find("span").text(data.nom);
            $("#delete-scenario").show();

            setTimeout(() => charger_demande(id, 1), 0);
            console.log("Chargement de la demande pour le scenario:", id);

            unblock_run();
        })
        .catch(error => console.error('Erreur lors du chargement du scenario:', error));
}

function infraModal(create_class, post_url, lat, lon) {
    const schema = openApiJson.components.schemas[create_class];
    const required = schema.required || [];
    const props = schema.properties;

    let modalHTML = `
        <div class="modal-dialog" role="document">
            <form id="form-${create_class.toLowerCase()}">
                <div class="modal-content">
                    <div class="modal-header w-100 d-flex justify-content-between">
                        <h5 class="modal-title">Créer Infrastructure</h5>
                        <button type="button" class="close btn-primary" data-bs-dismiss="modal" aria-label="Close">
                            <span aria-hidden="true"><i class="fas fa-times"></i></span>
                        </button>
                    </div>
                    <div class="modal-body">
    `;

    for (const [key, prop] of Object.entries(props)) {
        if (!required.includes(key)) continue;

        const title = prop.title || key;
        const isLatLon = (key === "latitude" || key === "longitude");
        const inputType = (prop.type === "number" || prop.type === "integer") ? "number" : "text";
        const value = key === "latitude" ? lat : (key === "longitude" ? lon : "");
        let tooltip;
        if (prop.description) {
            tooltip = `<i class="fas fa-info-circle" title="${prop.description}"></i>`;
        } else {
            tooltip = "";
        }

        modalHTML += `
            <div class="form-group">
                <label for="${key}">
                    ${title}
                    ${tooltip}
                </label>
        `;

        if (prop.enum) {
            modalHTML += `<select class="form-control" id="${key}" name="${key}" ${isLatLon ? "readonly disabled" : ""}>`;
            prop.enum.forEach(val => {
                modalHTML += `<option value="${val}">${val}</option>`;
            });
            modalHTML += `</select>`;
        } else {
            modalHTML += `<input 
                type="${inputType}" 
                class="form-control" 
                id="${key}" 
                name="${key}" 
                value="${value}" 
                ${isLatLon ? "disabled" : ""} 
                required
            >`;
        }

        modalHTML += `</div>`;
    }

    modalHTML += `
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fermer</button>
                        <input type="submit" class="btn btn-primary" value="Créer">
                    </div>
                </div>
            </form>
        </div>
    `;

    document.getElementById("dataModal").innerHTML = modalHTML;

    const modal = new bootstrap.Modal(document.getElementById("dataModal"));
    modal.show();

    $("#form-" + create_class.toLowerCase()).submit(function(event) {
        event.preventDefault();
        const formData = $(this).serializeArray();
        const data = {};
        formData.forEach(item => {
            data[item.name] = item.value;
        });

        data["latitude"] = lat;
        data["longitude"] = lon;

        fetch(post_url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(response => {
            console.log(`${create_class} créé avec succès:`, response);
            modal.hide();

            new_infra_dropped(response, post_url, lat, lon);
        })
        .catch(error => {
            console.error(`Erreur lors de la création de ${create_class}:`, error);
        });
    });
        
}

function new_infra_dropped(data, create_path, lat, lon) {
    const type = create_path.split('/').pop();
    addMarker(lat, lon, type, data);

    const listElement = document.getElementById(`list-parc-${type}`);
    const list = listElement.getElementsByTagName('ul')[0];
    const newElement = createListElement({ nom: data.nom, id: data.id });
    list.innerHTML += newElement;
}

function nouveauScenario() {
    function creerModal() {
        return `
            <div class="modal-dialog" role="document">
            <form id="form-nouveau-scenario">
                <div class="modal-content">
                    <div class="modal-header w-100 d-flex justify-content-between">
                        <h5 class="modal-title">Créer nouveau scenario</h5>
                        <button type="button" class="close btn-primary" data-bs-dismiss="modal" aria-label="Close">
                            <span aria-hidden="true"><i class="fas fa-times"></i></span>
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
                                <option value="PT15M" disabled>15 minutes</option>
                                <option value="PT1H" selected>1 heure</option>
                                <option value="PT4H" disabled>4 heures</option>
                                <option value="P1D" disabled>1 jour</option>
                                <opton value="P7D" disabled>7 jours</option>
                            </select>
                            <label for="weather">Meteo (consomation)</label>
                            <select class="form-control" id="scenario-weather">
                                <option value="3">Froid</option>
                                <option value="2" selected>Typique</option>
                                <option value="1">Chaud</option>
                            </select>
                            <label for="consomation">Modèle de consomation</label>
                            <select class="form-control" id="scenario-consomation">
                                <option value="2">Conservateur</option>
                                <option value="1" selected>Normal</option>
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
        let weather = parseInt($('#scenario-weather').val());
        let consomation = parseInt($('#scenario-consomation').val());
        let optimisme_social = parseInt($('#scenario-optimisme_social').val());
        let optimisme_ecologique = parseInt($('#scenario-optimisme_ecologique').val());

        let data = {
            nom: nom,
            description: description,
            date_de_debut: date_de_debut,
            date_de_fin: date_de_fin,
            pas_de_temps: pas_de_temps,
            weather: weather,
            consomation: consomation,
            optimisme_social: optimisme_social,
            optimisme_ecologique: optimisme_ecologique
        };

        // Validation des données
        if (nom === '' || pas_de_temps === '' || date_de_debut === '' || date_de_fin === '') {
            alert('Veuillez remplir tous les champs');
            return;
        }

        fetch('/api/scenario', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(response => {
            console.log('Scenario créé avec succès:', response);
            var option = document.createElement('option');
            option.value = response.id;
            option.textContent = response.nom;
            document.getElementById('scenario-actif').appendChild(option);
            $('#dataModal').modal('hide');

            $("#scenario-actif").val(response.id);
            changeScenario();
        })
        .catch(error => {
            console.error('Erreur lors de la création du scenario:', error);
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
        central_thermique: "",
        central_nucleaire: "",
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

            $("#groupe-actif").val(response.id);
            changeInfra();
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

function modeliserLignes() {
    // Charger le fichier CSV
    fetch('/static/lignes_quebec.csv')
        .then(response => {
            if (!response.ok) throw new Error(`Erreur HTTP: ${response.status}`);
            return response.text();
        })
        .then(csvData => {
            // Diviser le CSV en lignes
            const lignes = csvData.split('\n').map(line => line.trim()).filter(line => line.length > 0);

            // Extraire les en-têtes
            const headers = lignes[0].split(',');

            // Parcourir les lignes de données
            lignes.slice(1).forEach(line => {
                const values = line.split(',');
                const ligne = headers.reduce((acc, header, index) => {
                    acc[header] = values[index];
                    return acc;
                }, {});

                // Filtrer uniquement les lignes avec un voltage de 735
                // ou 120, 161, 230, 315, 735 kV
                if ([120, 161, 230, 315, 735].includes(parseInt(ligne.voltage))) {                    const busDepart = [parseFloat(ligne.latitude_starting), parseFloat(ligne.longitude_starting)];
                    const busArrivee = [parseFloat(ligne.latitude_ending), parseFloat(ligne.longitude_ending)];

                    // Construire le contenu du popup
                    const popupContent2 = `
                        <b>Voltage:</b> ${ligne.voltage || 'N/A'} kV<br>
                        <b>Longueur:</b> ${ligne.line_length_km || 'N/A'} km<br>
                        <b>Point de départ:</b> ${ligne.network_node_name_starting || 'N/A'}<br>
                        <b>Point d'arrivée:</b> ${ligne.network_node_name_ending || 'N/A'}
                    `;
                    const depart = `
                        <b>Point de départ:</b> ${ligne.network_node_name_starting || 'N/A'}<br>
                    `;

                    const ARRIVE = `
                        <b>Point d'arrivée:</b> ${ligne.network_node_name_ending || 'N/A'}
                    `;

                    // Ajouter un point pour le bus de départ
                    const bus0= L.circleMarker(busDepart, {
                        radius: 5,
                        color: 'blue',
                        fillColor: 'blue',
                        fillOpacity: 0.8
                    }).addTo(map)
                    .bindPopup(depart); 

                    // Lier le popup à la ligne
                    bus0.on('click', function () {
                        this.openPopup();
                    });

                    // Ajouter un point pour le bus d'arrivée
                    const bus1= L.circleMarker(busArrivee, {
                        radius: 5,
                        color: 'red',
                        fillColor: 'red',
                        fillOpacity: 0.8
                    }).addTo(map)
                    .bindPopup(ARRIVE); 
                    
                    // Lier le popup à la ligne
                    bus1.on('click', function () {
                        this.openPopup();
                    });

                    // Tracer une ligne entre les deux bus
                    const polyline = L.polyline([busDepart, busArrivee], {
                        color: 'green',
                        weight: 3
                    }).addTo(map)
                    .bindPopup(popupContent2); 
                    
                    // Lier le popup à la ligne
                    polyline.on('click', function () {
                        this.openPopup();
                    });

                }
            });
        })
        .catch(error => console.error('Erreur lors du chargement des lignes électriques:', error));
}

