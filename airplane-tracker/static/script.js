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

        // Fetch comprehensive data (includes both live and history)
        let response = await fetch('/api/comprehensive/all');
        let comprehensiveData = await response.json();
        
        // Clear existing markers
        aircraftMarkers.forEach(marker => map.removeLayer(marker));
        aircraftMarkers = [];
        
        // Extract current aircraft for display
        let currentAircraft = [];
        let total24hFlights = 0;
        
        Object.keys(comprehensiveData.data).forEach(icao24 => {
            const aircraftData = comprehensiveData.data[icao24];
            
            // Count flights from last 24 hours
            if (aircraftData.flight_history) {
                total24hFlights += aircraftData.flight_history.length;
            }
            
            // Add to current aircraft list if transmitting
            if (aircraftData.current_state) {
                currentAircraft.push(aircraftData.current_state);
            }
        });
        
        // Update stats
        updateStats({
            aircraft_count: currentAircraft.length,
            total_tracked: Object.keys(comprehensiveData.data).length,
            flights_24h: total24hFlights
        });
        
        // Process aircraft data for map
        if (currentAircraft.length > 0) {
            currentAircraft.forEach(plane => {
                if (plane.latitude && plane.longitude) {
                    // Create a custom icon based on aircraft status
                    const icon = createAircraftIcon(plane);
                    
                    const marker = L.marker([plane.latitude, plane.longitude], { icon: icon })
                        .addTo(map)
                        .bindPopup(createPopupContent(plane));
                    
                    aircraftMarkers.push(marker);
                }
            });
            
            // Update aircraft list
            updateAircraftList(currentAircraft);
            
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
        
        // Update flight history list
        updateFlightHistoryList(comprehensiveData);
        
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
<<<<<<< HEAD
                <div><strong>Altitude:</strong> ${plane.altitude ? Math.round(plane.alitude) + ' ft' : 'N/A'}</div>
=======
                <div><strong>Altitude:</strong> ${plane.altitude ? Math.round(plane.altitude * 3.28084) + ' ft' : 'N/A'}</div>
>>>>>>> deeff6cfce083a78c69be62b3afcdca12b8fc927
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
    const flights24hElement = document.getElementById('flights24h');
    
    if (activeElement) {
        activeElement.textContent = data.aircraft_count || 0;
    }
    if (totalElement) {
        totalElement.textContent = data.total_tracked || 0;
    }
    if (flights24hElement) {
        flights24hElement.textContent = data.flights_24h || 0;
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

// Update flight history list
function updateFlightHistoryList(comprehensiveData) {
    const flightHistoryList = document.getElementById('flightHistoryList');
    if (!flightHistoryList) return;

    let allFlights = [];
    
    // Collect all flights from all aircraft
    Object.keys(comprehensiveData.data).forEach(icao24 => {
        const aircraftData = comprehensiveData.data[icao24];
        const registration = aircraftData.registration || icao24;
        
        if (aircraftData.flight_history && aircraftData.flight_history.length > 0) {
            aircraftData.flight_history.forEach(flight => {
                allFlights.push({
                    ...flight,
                    registration: registration,
                    icao24: icao24
                });
            });
        }
    });
    
    // Remove duplicates based on icao24, callsign, firstSeen, and lastSeen
    const uniqueFlights = [];
    const seenFlights = new Set();
    
    allFlights.forEach(flight => {
        // Create a unique key for each flight
        const flightKey = `${flight.icao24}-${flight.callsign}-${flight.firstSeen}-${flight.lastSeen}`;
        
        if (!seenFlights.has(flightKey)) {
            seenFlights.add(flightKey);
            uniqueFlights.push(flight);
        }
    });
    
    // Sort flights by first seen time (most recent first)
    uniqueFlights.sort((a, b) => (b.firstSeen || 0) - (a.firstSeen || 0));
    
    if (uniqueFlights.length === 0) {
        flightHistoryList.innerHTML = '<div class="no-data">No flights in the past 24 hours</div>';
        return;
    }
    
    // Display flights
    flightHistoryList.innerHTML = uniqueFlights.map(flight => {
        const callsign = (flight.callsign || 'N/A').trim();
        const departure = flight.estDepartureAirport || 'Unknown';
        const arrival = flight.estArrivalAirport || 'Unknown';
        
        // Format times
        const departureTime = flight.firstSeen 
            ? new Date(flight.firstSeen * 1000).toLocaleString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                hour: '2-digit', 
                minute: '2-digit' 
              })
            : 'N/A';
            
        const arrivalTime = flight.lastSeen 
            ? new Date(flight.lastSeen * 1000).toLocaleString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                hour: '2-digit', 
                minute: '2-digit' 
              })
            : 'N/A';
        
        // Calculate duration
        let duration = 'N/A';
        if (flight.firstSeen && flight.lastSeen) {
            const durationMin = Math.round((flight.lastSeen - flight.firstSeen) / 60);
            const hours = Math.floor(durationMin / 60);
            const minutes = durationMin % 60;
            duration = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
        }
        
        return `
            <div class="flight-item">
                <div class="flight-header">
                    <span class="flight-callsign">${callsign}</span>
                    <span class="flight-registration">${flight.registration}</span>
                </div>
                <div class="flight-route">
                    <span><strong>${departure}</strong></span>
                    <span>→</span>
                    <span><strong>${arrival}</strong></span>
                </div>
                <div class="flight-details">
                    <div>Departure: ${departureTime}</div>
                    <div>Arrival: ${arrivalTime}</div>
                    <div>Duration: ${duration}</div>
                </div>
            </div>
        `;
    }).join('');
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
