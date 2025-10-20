let map = L.map('map').setView([41.8781, -87.6298], 5); // centered on Chicago
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

async function loadData() {
    let response = await fetch('/data');
    let planes = await response.json();
    planes.forEach(p => {
        if (p.latitude && p.longitude) {
            L.marker([p.latitude, p.longitude])
             .addTo(map)
             .bindPopup(`${p.callsign || 'N/A'} (${p.origin_country})`);
        }
    });
}
loadData();
