console.log("elo.js loaded correctly!");

document.addEventListener("DOMContentLoaded", function () {
    // Load CSV from /static folder
    async function loadCSV() {
        const response = await fetch("/static/data_sankey.csv");
        if (!response.ok) {
            console.error("Error loading CSV.");
            return [];
        }
        const data = await response.text();
        return data;
    }

    // Parse CSV and filter based on user selection
    function parseCSV(data, scenario, croissance, efficacite) {
        const rows = data.split("\n").slice(1); // Skip header row
        console.log("Rows:", rows); // Log all rows for debugging

        let filteredData = rows
            .map(row => row.split(","))
            .filter(row => {
                console.log(
                    `Checking row: ${row[0]} | ${row[1]} | ${row[2]}`
                ); // Check row values
                return (
                    row[0].trim() === scenario &&
                    row[1].trim().toLowerCase() === croissance.toLowerCase() &&
                    row[2].trim().toLowerCase() === efficacite.toLowerCase()
                );
            });

        console.log("Filtered Data:", filteredData); // Check filtered data
        return filteredData;
    }

    // Generate Sankey diagram with filtered data
    function generateSankey(filteredData) {
        let source = [];
        let target = [];
        let value = [];

        // Define mapping for sectors and energy types
        const sectorMap = {
            "Transport": 0,
            "Batiment": 1,
            "Industrie": 2
        };
        const energyMap = {
            "gaz": 3,
            "electrique": 4
        };

        // Populate Sankey data
        filteredData.forEach(row => {
            let secteur = row[3].trim(); // Secteur
            let energie = row[4].trim(); // Type_Energie
            let valeur = parseFloat(row[5].trim()); // Valeur (kWh)

            source.push(sectorMap[secteur]);
            target.push(energyMap[energie]);
            value.push(valeur);
        });

        console.log("Source:", source);
        console.log("Target:", target);
        console.log("Value:", value);

        // Sankey data structure
        let data = {
            type: "sankey",
            orientation: "h",
            node: {
                pad: 15,
                thickness: 20,
                line: {
                    color: "black",
                    width: 0.5
                },
                label: ["Transport", "Bâtiment", "Industrie", "Gaz", "Électricité"],
                color: ["#FFA07A", "#20B2AA", "#778899", "#FF6347", "#4682B4"]
            },
            link: {
                source: source,
                target: target,
                value: value
            }
        };

        let layout = {
            title: "Répartition de la Consommation Énergétique",
            font: {
                size: 14
            }
        };

        Plotly.newPlot("sankeyDiagram", [data], layout);
    }

    // Update Sankey based on user selection
    async function updateSankey() {
        const sankeyDiv = document.getElementById("sankeyDiagram");
        if (!sankeyDiv) {
            console.error("sankeyDiagram div not found.");
            return;
        }

        const scenario = document.getElementById("climateScenario").value;
        const croissance = document.querySelector('input[name="growthScenario"]:checked').value;
        const efficacite =
            document.getElementById("transportEfficiency").value == 1
                ? "Faible"
                : document.getElementById("transportEfficiency").value == 2
                ? "Moyen"
                : "Élevée";

        console.log("Selected Scenario:", scenario);
        console.log("Selected Croissance:", croissance);
        console.log("Selected Efficacité:", efficacite);

        // Load and parse CSV data
        const csvData = await loadCSV();
        console.log("CSV Data Loaded:", csvData); // Check if data is loaded
        const filteredData = parseCSV(csvData, scenario, croissance, efficacite);

        console.log("Filtered Data:", filteredData); // Check if data is filtered
        if (filteredData.length === 0) {
            console.error("No matching data found for the selected criteria.");
            return;
        }

        // Generate Sankey diagram
        generateSankey(filteredData);
    }

    // Event listeners to update Sankey when user changes input
    document.getElementById("climateScenario").addEventListener("change", updateSankey);
    document.querySelectorAll('input[name="growthScenario"]').forEach(radio => {
        radio.addEventListener("change", updateSankey);
    });
    document.getElementById("transportEfficiency").addEventListener("input", updateSankey);

    // Initial Sankey load
    updateSankey();
});

// Add this code to handle the favicon request
const express = require('express');
const app = express();
const path = require('path');

app.get('/favicon.ico', (req, res) => {
    res.sendFile(path.join(__dirname, 'favicon.ico'));
});

app.listen(3000, () => {
    console.log('Server is running on port 3000');
});