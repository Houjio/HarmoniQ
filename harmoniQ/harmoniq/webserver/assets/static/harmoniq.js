let infraTimeout = null;
let scenarioFetchController = null;
var openApiJson = null;
const markers = {}; // Objet pour stocker les marqueurs par ID d'infrastructure

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
    }),

    eolienneparcgris: L.icon({
        iconUrl: '/static/icons/eolienne_gris.png',
        iconSize: [30, 30],
        iconAnchor: [20, 20]
    }),
    solairegris: L.icon({
        iconUrl: '/static/icons/solaire_gris.png',
        iconSize: [40, 40],
        iconAnchor: [20, 20]
    }),
    thermiquegris: L.icon({
        iconUrl: '/static/icons/thermique_gris.png',
        iconSize: [40, 40],
        iconAnchor: [20, 20]
    }),
    hydrogris: L.icon({
        iconUrl: '/static/icons/barrage_gris.png',
        iconSize: [50, 50],
        iconAnchor: [20, 20]
    }),
    nucleairegris: L.icon({
        iconUrl: '/static/icons/nucelaire_gris.png',
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
            type de barrage: ${data.type_barrage || 'N/A'} <br>
            Débit nominal: ${data.debits_nominal ? parseFloat(data.debits_nominal).toFixed(1) : 'N/A'} m³/s<br>
            Puissance nominale: ${data.puissance_nominal || 'N/A'} MW<br>
            Volume du réservoir: ${
                data.volume_reservoir
                ? data.volume_reservoir >= 1e9
                    ? (data.volume_reservoir / 1e9).toFixed(1) + ' Gm³' // Milliards de m³
                    : data.volume_reservoir >= 1e6
                        ? (data.volume_reservoir / 1e6).toFixed(1) + ' Mm³' // Millions de m³
                        : (data.volume_reservoir / 1e3).toFixed(1) + ' km³' // Milliers de m³
                : 'N/A'
            }<br>
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
    } else if (type === 'nucleaire') { // Ajout pour la catégorie nucléaire
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
    // Stocker le marqueur dans l'objet global
    const markerKey = `${type}-${data.id}`;
    markers[markerKey] = marker;
}

function createListElement({ nom, id, type }) {
    return `
        <li class="list-group-item d-flex justify-content-between align-items-center" 
            role="button" 
            elementid="${id}" 
            type="${type}" 
            style="display: flex; justify-content: space-between; align-items: center; padding: 10px; border: 1px solid #ddd; margin-bottom: 5px; border-radius: 5px;"
            onclick="add_infra(this)"
            title="Cliquez pour sélectionner ou désélectionner cette infrastructure">
            <span>${nom}</span>
            <div>
            <i 
                class="fas fa-line-chart" 
                style="color: #007bff; cursor: pointer;" 
                onclick="simulate_single(event, '${id}', '${type}', '${nom}')"
                title="Simuler cette infrastructure"
            ></i>
            <span class="mx-1"></span>
            <i 
                class="fas fa-info-circle" 
                style="color: #007bff; cursor: pointer;" 
                onclick="handleInfoClick(event, '${id}', '${type}')"
                title="Afficher les informations de cette infrastructure"
            ></i>
            </div>
        </li>
    `;
}

function handleInfoClick(event, infraId, type) {
    event.preventDefault(); // Empêche le comportement par défaut
    event.stopPropagation(); // Empêche la propagation de l'événement au parent
    showPopup(infraId, type); // Affiche le popup pour l'infrastructure
}


function showPopup(infraId, type) {
    const markerKey = `${type}-${infraId}`; // Générer la clé unique
    const marker = markers[markerKey]; // Récupérer le marqueur correspondant

    if (marker) {
        map.setView(marker.getLatLng(), 8); // Centrer la carte sur le marqueur
        marker.openPopup(); // Ouvrir le popup du marqueur
    } else {
        console.error(`Aucun marqueur trouvé pour l'infrastructure avec la clé ${markerKey}`);
    }
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
                listeElement.innerHTML += createListElement({ nom: parc.nom, id: parc.id, type: type });
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

function initialiserTooltips() {
    $(".icon-draggable").tooltip({
        title: "Glissez et déposez sur la carte pour ajouter une infrastructure",
        placement: "top",
        trigger: "hover"
    });
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
    initialiserTooltips();

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

    fetchData(`/api/reseau/production/?scenario_id=${scenario}&liste_infra_id=${groupe}&is_journalier=false`, 'POST')
        .then(data => {
            console.log('Simulation réussie:', data);
            production = data;
            updateTemporalGraph();

            $("#run").html('Lancer la simulation');
            $("#run").prop('disabled', false);
        })
        .catch(error => {
            if (error.message.includes('501')) {
                unimplemented();
            } else {
                console.error('Erreur lors de la simulation:', error);
                alert('Erreur lors de la simulation: ' + error.message);
                $("#run").html('Lancer la simulation');
                $("#run").prop('disabled', false);
            }
        }); 

    $("#run").html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>')
    $("#run").prop('disabled', true);
    alert("Ce processus peut prendre un certain temps (3-5 minutes).")
}

function simulate_single(event, infraId, type, name) {
    event.stopPropagation();

    // Check if scenario is selected
    if ($('#scenario-actif').val() === '' || $('#scenario-actif').val() === null) {
        alert('Veuillez sélectionner un scenario pour simuler cette infrastructure');
        return;
    }

    $("#graph-error").hide();
    $("#graph-loading").show();

    const modal = new bootstrap.Modal(document.getElementById("graphModal"));
    modal.show();

    let scenario_name = $("#scenario-actif option:selected").text();
    $("#graphModalLabel").text(`Production d'énergie de ${name} (Scénario: ${scenario_name})`);
    Plotly.purge("graph-plot");

    fetchData(`/api/${type}/${infraId}/production?scenario_id=${$('#scenario-actif').val()}`, 'POST')
        .then(data => {
            $("#graph-loading").hide();
            console.log('Simulation de l\'infrastructure réussie:', data);
            single_graph(type, data);
        })
        .catch(error => {
            if (error.message.includes('501')) {
                unimplemented();
                modal.hide();
            } else {
                $("#graph-loading").hide();
                console.error('Erreur lors de la simulation de l\'infrastructure:', error);
                $("#graph-error").show();
            }
        });
}

function single_graph(type, data) {
    var unit;
    var xval;
    var yval;
    console.log(type, data)
    if (type == "eolienneparc") {
        unit = "MW";
        xval = Object.values(data.tempsdate);
        yval = Object.values(data.puissance);
    } else if (type == "thermique" || type == "nucleaire") {
        unit = "MW";
        xval = Object.keys(data.production_mwh);
        yval = Object.values(data.production_mwh);
    } else if (type == "solaire") {
        unit = "W";
        xval = Object.keys(data.production_horaire_wh);
        yval = Object.values(data.production_horaire_wh);
    }

    const layout = {
        xaxis: {
            title: "Date",
            tickformat: "%d %b %Y"
        },
        yaxis: {
            title: "Production (" + unit + ")",
            autorange: true
        },
    }

    const trace = {
        x: xval,
        y: yval,
        type: 'scatter',
        mode: 'lines',
        marker: { color: 'blue' },
        line: { shape: 'spline' }
    };

    Plotly.newPlot("graph-plot", [trace], layout);
}

function add_infra(element) {
    // Vérifier si un groupe est sélectionné
    if ($('#groupe-actif').val() === '' || $('#groupe-actif').val() === null) {
        alert('Veuillez sélectionner un groupe d\'infrastructures');
        return;
    }

    // Basculer l'état de sélection de l'infrastructure
    element.classList.toggle('list-group-item-secondary');
    const isActive = element.getAttribute('active') === 'true';

    if (isActive) {
        element.removeAttribute('active');
    } else {
        element.setAttribute('active', 'true');
    }

    // Mettre à jour l'icône sur la carte
    const infraId = element.getAttribute('elementid');
    const type = element.getAttribute('type'); // Assurez-vous que le type est défini dans l'attribut HTML

    const markerKey = `${type}-${infraId}`;
    const marker = markers[markerKey];

    if (marker) {
        if (isActive) {
            // Restaurer l'icône d'origine si désélectionné
            marker.setIcon(map_icons[`${type}gris`]);
        } else {
            // Changer l'icône en noire si sélectionné
            marker.setIcon(map_icons[type]);
        }
    }

    // Sauvegarder les changements
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

        // Mettre à jour l'icône en noir pour les infrastructures sélectionnées
        const infraId = this.getAttribute('elementid');
        const type = this.getAttribute('type');
        const markerKey = `${type}-${infraId}`;
        const marker = markers[markerKey];

        if (marker) {
            marker.setIcon(map_icons[type]); // Icône noire pour les sélectionnées
        }
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

        // Mettre à jour l'icône en gris pour les infrastructures désélectionnées
        const infraId = this.getAttribute('elementid');
        const type = this.getAttribute('type');
        const markerKey = `${type}-${infraId}`;
        const marker = markers[markerKey];

        if (marker) {
            marker.setIcon(map_icons[`${type}gris`]); // Icône grise pour les désélectionnées
        }
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
    $("#lists-infras").show();

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
                    const infraId = element.getAttribute('elementid');
                    const type = element.getAttribute('type');
                    const markerKey = `${type}-${infraId}`;
                    const marker = markers[markerKey];

                    if (activeIds.includes(infraId)) {
                        element.classList.add('list-group-item-secondary');
                        element.setAttribute('active', 'true');

                        // Mettre à jour l'icône en grise
                        if (marker) {
                            marker.setIcon(map_icons[type]);
                        }
                    } else {
                        element.classList.remove('list-group-item-secondary');
                        element.removeAttribute('active');

                        // Restaurer l'icône d'origine
                        if (marker) {
                            marker.setIcon(map_icons[`${type}gris`]);

                        }
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


    fetchData(`/api/demande/sankey/?scenario_id=${scenario_id}&CUID=${mrc_id || ''}`, 'POST', signal)
        .then(data => {
            console.log('Demande Sankey chargée avec succès');
                demandeSankey = data;
                generateSankey();
            })
            .catch(error => {
                if (error.message.includes('404')) {
                    console.error('Demande non trouvée:', error);
                } else {
                    console.error('Erreur lors du chargement de la demande Sankey:', error);
                }
            });

    fetchData("/api/demande/temporal/?scenario_id=" + scenario_id, 'POST', signal)
        .then(data => {
            console.log('Demande temporelle chargée avec succès');

            demandeTemporal = data;
            generateTemporalPlot();
        })
        .catch(error => {
            if (error.message.includes('404')) {
                console.error('Demande non trouvée:', error);
            } else {
                console.error('Erreur lors du chargement de la demande temporelle:', error);
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
    // Fonction qui lit le fichier openapi.json pour pouvoir créer des formulaires
    // dynamiquement qui permet à un usager de créer une infrastructure
    const schema = openApiJson.components.schemas[create_class];
    const required = schema.required || [];
    const props = schema.properties;
    const upname = post_url.split("/").pop();

    // Pretty jankey
    if (upname === "hydro") {
        alert("La fonctionnalité pour les infrastructures hydroélectriques est en cours de développement. Cette démonstration est fournie à titre indicatif.");
    }
    const ppname = prettyNames[upname]

    let modalHTML = `
        <div class="modal-dialog" role="document">
            <form id="form-${create_class.toLowerCase()}">
                <div class="modal-content">
                    <div class="modal-header w-100 d-flex justify-content-between">
                        <h5 class="modal-title">Créer ${ppname}</h5>
                        <button type="button" class="close btn-primary" data-bs-dismiss="modal" aria-label="Close">
                            <span aria-hidden="true"><i class="fas fa-times"></i></span>
                        </button>
                    </div>
                    <div class="modal-body">
    `;

    for (const [key, prop] of Object.entries(props)) {
        if (!required.includes(key)) continue;

        let title = prop.title || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        const isLatLon = (key === "latitude" || key === "longitude");
        const inputType = (prop.type === "number" || prop.type === "integer") ? "number" : "text";
        const value = key === "latitude" ? lat : (key === "longitude" ? lon : "");
        const suggestion = prop["suggestion"] || null;

        let tooltip;
        if (prop.description) {
            tooltip = `<i class="fas fa-info-circle" data-toggle="tooltip" data-placement="top" title="${prop.description}"></i>`;
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

        if (prop["$ref"]) {
            let refPath = prop["$ref"].replace("#/components/schemas/", "");
            let enumSchema = openApiJson.components.schemas[refPath];
            if (enumSchema && enumSchema.enum) {
            modalHTML += `<select class="form-control" id="${key}" name="${key}" ${isLatLon ? "readonly disabled" : ""}>`;
            enumSchema.enum.forEach(val => {
                modalHTML += `<option value="${val}" ${suggestion === val ? "selected" : ""}>${val}</option>`;
            });
            modalHTML += `</select>`;
            }
        }
        else if (prop.enum) {
            modalHTML += `<select class="form-control" id="${key}" name="${key}" ${isLatLon ? "readonly disabled" : ""}>`;
            prop.enum.forEach(val => {
            modalHTML += `<option value="${val}" ${suggestion === val ? "selected" : ""}>${val}</option>`;
            });
            modalHTML += `</select>`;
        }
        else {
            modalHTML += `<input 
            type="${inputType}" 
            class="form-control" 
            id="${key}" 
            name="${key}" 
            value="${suggestion || value}" 
            ${isLatLon ? "readonly" : ""} 
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

    $(function () {
        $('[data-toggle="tooltip"]').tooltip()
    })

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
    const type = create_path.split('/').pop(); // Extraire le type d'infrastructure (ex: hydro, solaire, etc.)

    // Ajouter le marqueur sur la carte
    addMarker(lat, lon, type, data);

    // Ajouter l'infrastructure à la liste HTML
    const listElement = document.getElementById(`list-parc-${type}`);
    const list = listElement.getElementsByTagName('ul')[0];
    const newElement = createListElement({ nom: data.nom, id: data.id, type: type });
    list.insertAdjacentHTML('beforeend', newElement); // Ajouter dynamiquement l'élément HTML


    // Récupérer l'élément ajouté
    const addedElement = list.querySelector(`li[elementid="${data.id}"][type="${type}"]`);

    // Marquer l'élément comme sélectionné
    if (addedElement) {
        addedElement.classList.add('list-group-item-secondary'); // Ajouter la classe pour le style sélectionné
        addedElement.setAttribute('active', 'true'); // Ajouter l'attribut actif
    }

    // Définir l'icône de base sur noir (sélectionné)
    const markerKey = `${type}-${data.id}`;
    const marker = markers[markerKey];
    if (marker) {
        marker.setIcon(map_icons[type]); // Icône noire pour sélectionné
    }

 

    // Sauvegarder les changements
    infraUserAction();
    createListElement();
    mettreAJourIconesSelectionnees();
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

            // Stocker les points pour déterminer leur rôle
            const points = {};

            // Parcourir les lignes de données pour collecter les points uniquement pour les lignes avec un voltage de 735
            const lignesSelectionnees = lignes.slice(1).filter(line => {
                const values = line.split(',');
                const ligne = headers.reduce((acc, header, index) => {
                    acc[header] = values[index];
                    return acc;
                }, {});

                // Filtrer les lignes avec un voltage de 735
                return parseInt(ligne.voltage) === 80;
            });

            lignesSelectionnees.forEach(line => {
                const values = line.split(',');
                const ligne = headers.reduce((acc, header, index) => {
                    acc[header] = values[index];
                    return acc;
                }, {});

                const departKey = `${ligne.latitude_starting},${ligne.longitude_starting}`;
                const arriveeKey = `${ligne.latitude_ending},${ligne.longitude_ending}`;

                // Marquer les points comme départ ou arrivée et ajouter le nom
                points[departKey] = points[departKey] || { 
                    lat: ligne.latitude_starting, 
                    lon: ligne.longitude_starting, 
                    nom: ligne.network_node_name_starting || 'N/A', 
                    isDepart: false, 
                    isArrivee: false 
                };
                points[departKey].isDepart = true;

                points[arriveeKey] = points[arriveeKey] || { 
                    lat: ligne.latitude_ending, 
                    lon: ligne.longitude_ending, 
                    nom: ligne.network_node_name_ending || 'N/A', 
                    isDepart: false, 
                    isArrivee: false 
                };
                points[arriveeKey].isArrivee = true;
            });

            // Ajouter les points à la carte avec les couleurs appropriées
            Object.values(points).forEach(point => {
                let color = 'gray'; // Par défaut, gris pour les points à la fois départ et arrivée
                if (point.isDepart && !point.isArrivee) {
                    color = 'blue'; // Bleu pour les points uniquement départ
                } else if (!point.isDepart && point.isArrivee) {
                    color = 'red'; // Rouge pour les points uniquement arrivée
                }

                const popupContent = `
                    <b>Nom:</b> ${point.nom || 'N/A'}<br>
                    <b>Type:</b> ${point.isDepart && point.isArrivee ? 'Départ et Arrivée' : point.isDepart ? 'Départ' : 'Arrivée'}
                `;

                L.circleMarker([parseFloat(point.lat), parseFloat(point.lon)], {
                    radius: 2,
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.8
                }).addTo(map)
                .bindPopup(popupContent);
            });

            // Parcourir les lignes de données pour tracer les lignes
            lignesSelectionnees.forEach(line => {
                const values = line.split(',');
                const ligne = headers.reduce((acc, header, index) => {
                    acc[header] = values[index];
                    return acc;
                }, {});

                const busDepart = [parseFloat(ligne.latitude_starting), parseFloat(ligne.longitude_starting)];
                const busArrivee = [parseFloat(ligne.latitude_ending), parseFloat(ligne.longitude_ending)];

                // Construire le contenu du popup pour la ligne
                const popupContent = `
                    <b>Voltage:</b> ${ligne.voltage || 'N/A'} kV<br>
                    <b>Longueur:</b> ${ligne.line_length_km || 'N/A'} km<br>
                    <b>Point de départ:</b> ${ligne.network_node_name_starting || 'N/A'}<br>
                    <b>Point d'arrivée:</b> ${ligne.network_node_name_ending || 'N/A'}
                `;

                // Tracer une ligne entre les deux bus
                L.polyline([busDepart, busArrivee], {
                    color: 'gray',
                    weight: 1
                }).addTo(map)
                .bindPopup(popupContent)
                .on('click', function () {
                    this.openPopup();
                });
            });
        })
        .catch(error => console.error('Erreur lors du chargement des lignes électriques:', error));
}

function mettreAJourIconesSelectionnees() {
    const groupeActifId = $("#groupe-actif").val();

    if (!groupeActifId) {
        console.error("Aucun groupe d'infrastructures sélectionné.");
        return;
    }

    // Récupérer les infrastructures sélectionnées pour le groupe actif
    fetch(`/api/listeinfrastructures/${groupeActifId}`)
        .then(response => response.json())
        .then(data => {
            const selectedIds = [
                ...(data.parc_eoliens ? data.parc_eoliens.split(',') : []),
                ...(data.parc_solaires ? data.parc_solaires.split(',') : []),
                ...(data.central_hydroelectriques ? data.central_hydroelectriques.split(',') : []),
                ...(data.central_thermique ? data.central_thermique.split(',') : []),
                ...(data.central_nucleaire ? data.central_nucleaire.split(',') : [])
            ];

            // Mettre à jour les icônes des marqueurs et la liste
            Object.keys(markers).forEach(markerKey => {
                const marker = markers[markerKey];
                const [type, id] = markerKey.split('-'); // Extraire le type et l'ID de l'infrastructure

                const listElement = document.querySelector(`li[elementid="${id}"][type="${type}"]`);
                if (selectedIds.includes(id)) {
                    // Icône noire pour les infrastructures sélectionnées
                    marker.setIcon(map_icons[type]);

                    // Marquer comme sélectionné dans la liste
                    if (listElement) {
                        listElement.classList.add('list-group-item-secondary');
                        listElement.setAttribute('active', 'true');
                    }
                } else {
                    // Icône grise pour les infrastructures non sélectionnées
                    marker.setIcon(map_icons[`${type}gris`]);

                    // Marquer comme non sélectionné dans la liste
                    if (listElement) {
                        listElement.classList.remove('list-group-item-secondary');
                        listElement.removeAttribute('active');
                    }
                }
            });

            console.log("Icônes et liste mises à jour pour les infrastructures sélectionnées.");
        })
        .catch(error => console.error("Erreur lors de la mise à jour des icônes :", error));
}

function changeInfra() {
    $("#lists-infras").show();

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

            // Mettre à jour les icônes sur la carte
            mettreAJourIconesSelectionnees();
        })
        .catch(error => console.error('Erreur lors du chargement du groupe d\'infrastructures:', error));
}