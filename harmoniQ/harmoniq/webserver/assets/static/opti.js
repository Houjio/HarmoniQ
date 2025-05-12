window.onload = function() {
    // Load map
    const map = L.map('opti-map').setView([52.9399, -70], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Fetch and add optimal wind sites
    fetch('/api/opti/wind')
        .then(res => res.json())
        .then(data => {
            data.forEach(site => {
                L.marker([site.lat, site.lon]).addTo(map)
                    .bindPopup(`<b>${site.name}</b><br>Capacité: ${site.capacity} MW`);
            });
        });

    // Fetch and plot comparison data
    fetch('/api/opti/wind/compare')
        .then(res => res.json())
        .then(data => {
            Plotly.newPlot('opti-plot', data.traces, data.layout);
        });
};