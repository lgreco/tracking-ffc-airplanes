/*
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

*/
// Initialize the map - keeping your Chicago center but with FFC area
let map = L.map('map').setView([41.9200, -88.2417], 10); // centered on Fox Flying Club
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

let aircraftMarkers = [];
let autoRefreshInterval = null;

// existing loadData function, enhanced
async function loadData() {
    try {
        // Show loading state
        const aircraftList = document.getElementById('aircraftList');
        if (aircraftList) {
            aircraftList.innerHTML = '<div class="loading">Loading aircraft data...</div>';
        }

        let response = await fetch('/api/live/all');
        let data = await response.json();
        
        // Clear existing markers
        aircraftMarkers.forEach(marker => map.removeLayer(marker));
        aircraftMarkers = [];
        
        // Update stats if elements exist
        updateStats(data);
        
        // Process aircraft data
        if (data.aircraft && data.aircraft.length > 0) {
            data.aircraft.forEach(plane => {
                if (plane.latitude && plane.longitude) {
                    // Create a custom icon based on aircraft status
                    const icon = createAircraftIcon(plane);
                    
                    const marker = L.marker([plane.latitude, plane.longitude], { icon: icon })
                        .addTo(map)
                        .bindPopup(createPopupContent(plane));
                    
                    aircraftMarkers.push(marker);
                }
            });
            
            // Update aircraft list if element exists
            updateAircraftList(data.aircraft);
            
            // Adjust map view to show all aircraft
            if (aircraftMarkers.length > 0) {
                const group = new L.featureGroup(aircraftMarkers);
                map.fitBounds(group.getBounds().pad(0.1));
            }
        } else {
            // No aircraft found
            if (aircraftList) {
                aircraftList.innerHTML = '<div class="no-data">No aircraft currently transmitting data</div>';
            }
        }
        
        updateLastUpdate();
        
    } catch (error) {
        console.error('Error loading aircraft data:', error);
        const aircraftList = document.getElementById('aircraftList');
        if (aircraftList) {
            aircraftList.innerHTML = `<div class="error">Error loading data: ${error.message}</div>`;
        }
    }
}

// Create custom aircraft icon
function createAircraftIcon(plane) {
    let iconText = '✈️'; // Default icon
    
    if (plane.on_ground) {
        iconText = '🛬'; // On ground
    } else if (plane.vertical_rate > 0) {
        iconText = '🔼'; // Climbing
    } else if (plane.vertical_rate < 0) {
        iconText = '🔽'; // Descending
    }

    return L.divIcon({
        html: `<div style="font-size: 20px; transform: rotate(${plane.heading || 0}deg);">${iconText}</div>`,
        className: 'aircraft-marker',
        iconSize: [30, 30]
    });
}

// Create popup content
function createPopupContent(plane) {
    return `
        <div style="min-width: 200px;">
            <div style="font-weight: bold; margin-bottom: 8px;">${plane.callsign}</div>
            <div style="font-size: 0.9em;">
                <div><strong>Altitude:</strong> ${plane.altitude ? Math.round(plane.alitude) + ' ft' : 'N/A'}</div>
                <div><strong>Speed:</strong> ${plane.velocity ? Math.round(plane.velocity) + ' kt' : 'N/A'}</div>
                <div><strong>Heading:</strong> ${plane.heading ? Math.round(plane.heading) + '°' : 'N/A'}</div>
                <div><strong>Status:</strong> ${plane.on_ground ? 'On Ground' : 'In Flight'}</div>
            </div>
        </div>
    `;
}

// Update statistics
function updateStats(data) {
    const activeElement = document.getElementById('activeAircraft');
    const totalElement = document.getElementById('totalAircraft');
    
    if (activeElement) {
        activeElement.textContent = data.aircraft_count || 0;
    }
    if (totalElement) {
        // This would need to come from your AIRCRAFT_MAP - showing active count for now
        totalElement.textContent = data.aircraft_count || 0;
    }
}

// Update aircraft list in sidebar
function updateAircraftList(aircraft) {
    const aircraftList = document.getElementById('aircraftList');
    if (!aircraftList) return;

    aircraftList.innerHTML = aircraft.map(plane => `
        <div class="aircraft-item" onclick="focusOnAircraft(${plane.longitude}, ${plane.latitude})">
            <div class="aircraft-header">
                <span class="callsign">${plane.callsign}</span>
                <span class="altitude">${plane.altitude ? Math.round(plane.altitude) + ' ft' : 'N/A'}</span>
            </div>
            <div class="aircraft-details">
                <div class="detail">
                    <span class="label">Speed:</span>
                    <span class="value">${plane.velocity ? Math.round(plane.velocity) + ' kt' : 'N/A'}</span>
                </div>
                <div class="detail">
                    <span class="label">Heading:</span>
                    <span class="value">${plane.heading ? Math.round(plane.heading) + '°' : 'N/A'}</span>
                </div>
                <div class="detail">
                    <span class="label">Status:</span>
                    <span class="value">${plane.on_ground ? 'On Ground' : 'In Flight'}</span>
                </div>
            </div>
        </div>
    `).join('');
}

// Focus on specific aircraft
function focusOnAircraft(lon, lat) {
    map.setView([lat, lon], 13);
    // Find and open the marker popup
    aircraftMarkers.forEach(marker => {
        const markerLatLng = marker.getLatLng();
        if (markerLatLng.lat === lat && markerLatLng.lng === lon) {
            marker.openPopup();
        }
    });
}

// Update last update time
function updateLastUpdate() {
    const lastUpdate = document.getElementById('lastUpdate');
    if (lastUpdate) {
        lastUpdate.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
    }
}

// Auto-refresh functions
function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshInterval = setInterval(loadData, 30000); // 30 seconds
    alert('Auto-refresh started (every 30 seconds)');
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        alert('Auto-refresh stopped');
    }
}

// Manual refresh
function refreshData() {
    loadData();
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Set up event listeners for buttons if they exist
    const refreshBtn = document.getElementById('refreshBtn');
    const autoRefreshBtn = document.getElementById('autoRefreshBtn');
    const stopRefreshBtn = document.getElementById('stopRefreshBtn');
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshData);
    }
    if (autoRefreshBtn) {
        autoRefreshBtn.addEventListener('click', startAutoRefresh);
    }
    if (stopRefreshBtn) {
        stopRefreshBtn.addEventListener('click', stopAutoRefresh);
    }
    
    // Load initial data
    loadData();
    
    // Set up auto-refresh every 2 minutes
    setInterval(loadData, 120000);
});
