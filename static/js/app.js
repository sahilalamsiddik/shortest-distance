/**
 * Bengaluru Local Delivery Route Planner - Client Application
 */

let allLocations = [];
let leafletMap = null;
let leafletRouteLayer = null;
let leafletMarkersLayer = null;
let currentCriteria = 'time';
let selectedSosType = 'hospital';
let currentActiveRoute = null;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    setupEventListeners();
    await checkSystemStatus();
    await loadLocations();
    initLeaflet();
    await loadTrafficDelays();
    await loadHistory();
    // Load default base map image
    updateMapImage();
}

function setupEventListeners() {
    // Mode toggles
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');
            currentCriteria = e.currentTarget.dataset.mode;
        });
    });

    // Calculate route button
    document.getElementById('btnCalculateRoute').addEventListener('click', handleCalculateRoute);

    // Swap locations
    document.getElementById('btnSwapLocations').addEventListener('click', () => {
        const orig = document.getElementById('selectOrigin');
        const dest = document.getElementById('selectDestination');
        const tmp = orig.value;
        orig.value = dest.value;
        dest.value = tmp;
    });

    // SOS Modal triggers
    document.getElementById('btnOpenSos').addEventListener('click', () => {
        document.getElementById('sosModal').style.display = 'flex';
        // Auto-select origin in SOS modal if selected
        const currentOrig = document.getElementById('selectOrigin').value;
        if (currentOrig) {
            document.getElementById('sosLocationSelect').value = currentOrig;
        }
    });

    document.getElementById('btnCloseSosModal').addEventListener('click', () => {
        document.getElementById('sosModal').style.display = 'none';
    });

    // Choice cards inside SOS modal
    document.querySelectorAll('.choice-card').forEach(card => {
        card.addEventListener('click', (e) => {
            document.querySelectorAll('.choice-card').forEach(c => c.classList.remove('selected'));
            const target = e.currentTarget;
            target.classList.add('selected');
            selectedSosType = target.dataset.type;
        });
    });

    document.getElementById('btnDispatchSos').addEventListener('click', handleDispatchSos);

    // Reload CSV traffic
    document.getElementById('btnReloadTraffic').addEventListener('click', handleReloadTraffic);

    // Clear history
    document.getElementById('btnClearHistory').addEventListener('click', handleClearHistory);

    // Map view tab switching
    document.querySelectorAll('.tab-btn').forEach(tab => {
        tab.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
            e.currentTarget.classList.add('active');
            const view = e.currentTarget.dataset.view;
            switchMapView(view);
        });
    });
}

function switchMapView(view) {
    const imgView = document.getElementById('generatedMapImage');
    const leafView = document.getElementById('leafletMap');

    if (view === 'image') {
        imgView.style.display = 'block';
        leafView.style.display = 'none';
    } else if (view === 'leaflet') {
        imgView.style.display = 'none';
        leafView.style.display = 'block';
        if (leafletMap) {
            setTimeout(() => leafletMap.invalidateSize(), 200);
        }
    }
}

async function checkSystemStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        const dbBadge = document.getElementById('dbStatusBadge');
        if (data.database && data.database.is_mysql) {
            dbBadge.innerHTML = `<span class="status-indicator"></span> DB: MySQL`;
            dbBadge.title = `Connected to MySQL: ${data.database.active_database}`;
        } else {
            dbBadge.innerHTML = `<span class="status-indicator" style="background-color: #d97706;"></span> DB: SQLite Fallback`;
            dbBadge.title = `Running on SQLite. To use MySQL, set credentials in .env.`;
        }

        const trafficBadge = document.getElementById('trafficStatusBadge');
        trafficBadge.innerHTML = `<span class="status-indicator"></span> Delays: ${data.traffic_active_bottlenecks} active`;
    } catch (err) {
        console.error('Failed to get status:', err);
    }
}

async function loadLocations() {
    try {
        const res = await fetch('/api/locations');
        allLocations = await res.json();

        const selectOrigin = document.getElementById('selectOrigin');
        const selectDest = document.getElementById('selectDestination');
        const sosSelect = document.getElementById('sosLocationSelect');

        selectOrigin.innerHTML = '<option value="">-- Choose Starting Hub --</option>';
        selectDest.innerHTML = '<option value="">-- Choose Destination Hub --</option>';
        sosSelect.innerHTML = '<option value="">-- Choose Current Location --</option>';

        // Group into delivery hubs, hospitals, police stations
        const groups = {
            'Delivery Hubs': allLocations.filter(l => l.category === 'hub'),
            'Hospitals': allLocations.filter(l => l.category === 'hospital'),
            'Police Stations': allLocations.filter(l => l.category === 'police_station')
        };

        for (const [groupName, locList] of Object.entries(groups)) {
            const optGroupOrig = document.createElement('optgroup');
            optGroupOrig.label = groupName;

            const optGroupDest = document.createElement('optgroup');
            optGroupDest.label = groupName;

            const optGroupSos = document.createElement('optgroup');
            optGroupSos.label = groupName;

            locList.forEach(loc => {
                const opt1 = new Option(loc.name, loc.name);
                const opt2 = new Option(loc.name, loc.name);
                const opt3 = new Option(loc.name, loc.name);

                optGroupOrig.appendChild(opt1);
                optGroupDest.appendChild(opt2);
                optGroupSos.appendChild(opt3);
            });

            selectOrigin.appendChild(optGroupOrig);
            selectDest.appendChild(optGroupDest);
            sosSelect.appendChild(optGroupSos);
        }

        // Set sensible defaults
        selectOrigin.value = 'Majestic';
        selectDest.value = 'Whitefield';
    } catch (err) {
        console.error('Failed to load locations:', err);
    }
}

function initLeaflet() {
    // Bengaluru center coordinates
    leafletMap = L.map('leafletMap').setView([12.9716, 77.5946], 12);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap contributors',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(leafletMap);

    leafletMarkersLayer = L.layerGroup().addTo(leafletMap);
    leafletRouteLayer = L.layerGroup().addTo(leafletMap);

    // Plot all initial markers
    plotLocationMarkers();
}

function plotLocationMarkers() {
    if (!leafletMarkersLayer) return;
    leafletMarkersLayer.clearLayers();

    allLocations.forEach(loc => {
        let iconHtml = '📍';
        let color = '#2563eb';
        if (loc.category === 'hospital') {
            iconHtml = '🏥';
            color = '#dc2626';
        } else if (loc.category === 'police_station') {
            iconHtml = '🚓';
            color = '#4338ca';
        }

        const customIcon = L.divIcon({
            className: 'custom-map-pin',
            html: `<div style="background: white; border: 2px solid ${color}; border-radius: 50%; width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; font-size: 13px; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">${iconHtml}</div>`,
            iconSize: [26, 26],
            iconAnchor: [13, 13]
        });

        const marker = L.marker([loc.latitude, loc.longitude], { icon: customIcon });
        marker.bindPopup(`<strong>${loc.name}</strong><br><small>${loc.address || loc.category}</small>`);
        leafletMarkersLayer.addLayer(marker);
    });
}

async function handleCalculateRoute() {
    const origin = document.getElementById('selectOrigin').value;
    const destination = document.getElementById('selectDestination').value;

    if (!origin || !destination) {
        alert('Please select both starting point and destination.');
        return;
    }

    const btn = document.getElementById('btnCalculateRoute');
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Calculating optimal path...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/route', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                origin: origin,
                destination: destination,
                criteria: currentCriteria
            })
        });

        const data = await res.json();
        renderRouteResult(data);
        await loadHistory();
    } catch (err) {
        console.error('Error calculating route:', err);
        alert('Failed to calculate route. Check backend connection.');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function handleDispatchSos() {
    const location = document.getElementById('sosLocationSelect').value;
    if (!location) {
        alert('Please select your current location for emergency dispatch.');
        return;
    }

    const btn = document.getElementById('btnDispatchSos');
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Locating closest responder...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/sos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_location: location,
                service_type: selectedSosType
            })
        });

        const data = await res.json();
        document.getElementById('sosModal').style.display = 'none';
        renderRouteResult(data);
        await loadHistory();
    } catch (err) {
        console.error('Error in SOS dispatch:', err);
        alert('SOS dispatch failed. Please check network.');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function renderRouteResult(data) {
    currentActiveRoute = data;
    const container = document.getElementById('resultsContainer');
    container.style.display = 'block';

    const alertBanner = document.getElementById('routeAlertBanner');
    const statsRow = document.getElementById('statsRow');
    const itineraryList = document.getElementById('itineraryList');

    if (!data.found) {
        alertBanner.className = 'alert-banner danger';
        alertBanner.innerHTML = `⚠️ <strong>Route Unreachable:</strong> ${data.message}`;
        statsRow.style.display = 'none';
        itineraryList.innerHTML = '<div style="padding: 12px; color: #dc2626; font-size: 13px;">No traversable path connects these locations. Possible reasons include isolated depot, road network disconnect, or complete roadblock closures.</div>';
        
        // Update map image showing unreachable notice
        updateMapImage(data.origin, data.destination, data.criteria, false, null);
        if (leafletRouteLayer) leafletRouteLayer.clearLayers();
        return;
    }

    statsRow.style.display = 'grid';
    document.getElementById('statDistance').textContent = `${data.total_distance_km} km`;
    document.getElementById('statTime').textContent = `${data.total_time_minutes} min`;
    
    const delayElem = document.getElementById('statDelay');
    if (data.traffic_delay_minutes > 0) {
        delayElem.textContent = `+${data.traffic_delay_minutes} min`;
        delayElem.style.color = '#dc2626';
    } else {
        delayElem.textContent = '0 min';
        delayElem.style.color = '#16a34a';
    }

    if (data.is_emergency) {
        alertBanner.className = 'alert-banner danger';
        alertBanner.innerHTML = `🚨 <strong>EMERGENCY DISPATCH:</strong> Shortest route to nearest ${data.emergency_type} (<strong>${data.destination}</strong>). Clear emergency path!`;
    } else if (data.traffic_delay_minutes > 15) {
        alertBanner.className = 'alert-banner warning';
        alertBanner.innerHTML = `⚠️ <strong>High Traffic Alert:</strong> Heavy congestion adds ~${data.traffic_delay_minutes} min delay over free-flow conditions.`;
    } else {
        alertBanner.className = 'alert-banner info';
        alertBanner.innerHTML = `✅ <strong>Optimal Route:</strong> Calculated via ${data.criteria === 'time' ? 'fastest travel time with dynamic traffic' : 'shortest distance in km'}.`;
    }

    // Populate turn-by-turn directions
    itineraryList.innerHTML = '';
    data.directions.forEach(d => {
        const item = document.createElement('div');
        item.className = 'itinerary-item';
        
        const delayBadge = d.delay_minutes > 0
            ? `<span class="delay-badge delay-high">+${d.delay_minutes}m delay</span>`
            : `<span class="delay-badge delay-low">Clear</span>`;

        item.innerHTML = `
            <div>
                <span class="step-num">${d.step}</span>
                <strong>${d.road_name}</strong>
                <div style="color: var(--text-muted); font-size: 11px; margin-left: 28px;">
                    ${d.from_node} ➔ ${d.to_node} (${d.distance_km} km, ~${d.time_minutes} min)
                </div>
            </div>
            <div>${delayBadge}</div>
        `;
        itineraryList.appendChild(item);
    });

    // Update generated map image
    updateMapImage(
        data.origin,
        data.destination,
        data.criteria,
        data.is_emergency,
        data.emergency_type
    );

    // Update Leaflet Route
    updateLeafletRoute(data.path, data.is_emergency);
}

function updateMapImage(origin, destination, criteria, isEmergency, emergencyType) {
    const img = document.getElementById('generatedMapImage');
    let url = `/api/route/map-image?t=${new Date().getTime()}`;
    if (origin && destination) {
        url += `&origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}`;
    }
    if (criteria) {
        url += `&criteria=${encodeURIComponent(criteria)}`;
    }
    if (isEmergency) {
        url += `&is_emergency=true&emergency_type=${encodeURIComponent(emergencyType || 'hospital')}`;
    }
    img.src = url;
}

function updateLeafletRoute(pathNames, isEmergency) {
    if (!leafletMap || !leafletRouteLayer) return;
    leafletRouteLayer.clearLayers();

    if (!pathNames || pathNames.length < 2) return;

    const locMap = {};
    allLocations.forEach(l => { locMap[l.name] = l; });

    const latLngs = [];
    pathNames.forEach(name => {
        const loc = locMap[name];
        if (loc) {
            latLngs.push([loc.latitude, loc.longitude]);
        }
    });

    if (latLngs.length > 1) {
        const routeColor = isEmergency ? '#dc2626' : '#2563eb';
        const polyline = L.polyline(latLngs, {
            color: routeColor,
            weight: 5,
            opacity: 0.85,
            lineJoin: 'round'
        }).addTo(leafletRouteLayer);

        leafletMap.fitBounds(polyline.getBounds(), { padding: [40, 40] });
    }
}

async function loadTrafficDelays() {
    try {
        const res = await fetch('/api/traffic');
        const list = await res.json();
        const tbody = document.getElementById('trafficTableBody');
        tbody.innerHTML = '';

        list.forEach(item => {
            const tr = document.createElement('tr');
            
            let badgeClass = 'delay-low';
            if (item.delay_minutes >= 20) badgeClass = 'delay-high';
            else if (item.delay_minutes >= 10) badgeClass = 'delay-med';

            tr.innerHTML = `
                <td><strong>${item.road_name}</strong></td>
                <td>${item.from_location} ➔ ${item.to_location}</td>
                <td><span class="delay-badge ${badgeClass}">+${item.delay_minutes} min (${item.traffic_factor}x)</span></td>
                <td>${item.condition}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Failed to load traffic delays:', err);
    }
}

async function handleReloadTraffic() {
    const btn = document.getElementById('btnReloadTraffic');
    btn.disabled = true;
    btn.innerHTML = 'Reloading CSV...';

    try {
        const res = await fetch('/api/traffic/reload', { method: 'POST' });
        const data = await res.json();
        await loadTrafficDelays();
        await checkSystemStatus();

        // If there is an active route, recalculate with updated traffic
        if (currentActiveRoute && currentActiveRoute.found) {
            if (currentActiveRoute.is_emergency) {
                handleDispatchSos();
            } else {
                handleCalculateRoute();
            }
        }
        alert(`Success: ${data.message} (${data.records_loaded} records). Route re-evaluated!`);
    } catch (err) {
        console.error('Failed to reload traffic:', err);
        alert('Failed to reload CSV.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🔄 Reload CSV';
    }
}

async function loadHistory() {
    try {
        const res = await fetch('/api/history?limit=15');
        const history = await res.json();
        const tbody = document.getElementById('historyTableBody');
        tbody.innerHTML = '';

        if (history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 16px;">No recent searches recorded.</td></tr>';
            return;
        }

        history.forEach(item => {
            const tr = document.createElement('tr');
            const isEmg = item.is_emergency;
            const emgBadge = isEmg ? `<span class="delay-badge delay-high">🚨 SOS (${item.emergency_type})</span>` : `<span class="delay-badge delay-low">Delivery</span>`;

            tr.innerHTML = `
                <td>${item.created_at || 'Just now'}</td>
                <td><strong>${item.origin_name}</strong> ➔ <strong>${item.destination_name}</strong></td>
                <td>${emgBadge}</td>
                <td>${item.total_distance_km} km</td>
                <td>~${item.total_time_minutes} min (${item.criteria})</td>
                <td><button class="btn-table-action" onclick="replayHistory('${item.origin_name}', '${item.destination_name}', '${item.criteria}')">Re-run</button></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Failed to load history:', err);
    }
}

window.replayHistory = function(orig, dest, criteria) {
    document.getElementById('selectOrigin').value = orig;
    document.getElementById('selectDestination').value = dest;
    currentCriteria = criteria;
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === criteria);
    });
    handleCalculateRoute();
};

async function handleClearHistory() {
    if (!confirm('Are you sure you want to clear past route search history?')) return;
    try {
        await fetch('/api/history/clear', { method: 'POST' });
        await loadHistory();
    } catch (err) {
        console.error('Failed to clear history:', err);
    }
}
