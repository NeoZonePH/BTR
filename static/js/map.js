/**
 * TARGET — MapLibre GL JS Integration
 * Interactive incident map with markers, popups, clustering, filtering,
 * map style switching (Light / Dark / Satellite), and pulsing HQ marker.
 */

let targetMap = null;
let currentMarkers = [];
let hqMarker = null;
let reservistMarker = null;
let rcdgMarkers = [];
let cdcMarkers = [];
let reservistListMarkers = [];
let currentApiUrl = null;
let currentGeojsonFeatures = [];

// ── Distance calculations ──
function calculateDistance(lat1, lon1, lat2, lon2) {
    if (lat1 == null || lon1 == null || lat2 == null || lon2 == null) return null;
    const R = 6371; // Radius of the earth in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return (R * c).toFixed(2);
}

function getReservistDistanceHtml(lat, lng) {
    if (!currentGeojsonFeatures || currentGeojsonFeatures.length === 0) return '';

    // Calculate distances to all incidents on the map
    const distances = currentGeojsonFeatures.map(f => {
        const incLat = f.geometry.coordinates[1];
        const incLng = f.geometry.coordinates[0];
        const dist = calculateDistance(lat, lng, incLat, incLng);
        return { feature: f, distance: parseFloat(dist) };
    }).filter(d => !isNaN(d.distance));

    if (distances.length === 0) return '';

    // Sort by distance ascending
    distances.sort((a, b) => a.distance - b.distance);

    // Take top 3 nearest
    const top3 = distances.slice(0, 3);

    let html = '<div style="margin-top:12px;border-top:1px solid rgba(255,255,255,0.1);padding-top:10px;text-align:left;">';
    html += '<div style="font-size:0.75rem;font-weight:700;color:#94a3b8;margin-bottom:6px;">Nearest Incidents:</div>';

    top3.forEach(d => {
        const title = d.feature.properties.title || 'Incident';
        html += `<div style="font-size:0.75rem;display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;background:rgba(255,255,255,0.05);padding:4px 6px;border-radius:4px;">
            <span style="color:#cbd5e1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:140px;" title="${title}">${title}</span>
            <span style="color:var(--accent);font-weight:700;">${d.distance} km</span>
        </div>`;
    });

    html += '</div>';
    return html;
}

// ── Map styles ──
const MAP_STYLES = {
    dark: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
    light: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
    streets: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
    osm: {
        version: 8,
        sources: {
            osm: {
                type: 'raster',
                tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                tileSize: 256,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            },
        },
        layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
    },
    satellite: {
        version: 8,
        sources: {
            satellite: {
                type: 'raster',
                tiles: [
                    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                ],
                tileSize: 256,
                attribution: '&copy; Esri, Maxar, Earthstar Geographics',
            },
        },
        layers: [{ id: 'satellite', type: 'raster', source: 'satellite' }],
    },
};

/**
 * Initialize the incident map.
 * @param {string} containerId - The DOM element ID for the map
 * @param {string} apiUrl - The GeoJSON API endpoint URL
 */
function initIncidentMap(containerId, apiUrl) {
    const container = document.getElementById(containerId);
    if (!container) return;

    currentApiUrl = apiUrl;

    const userLat = container.getAttribute('data-user-lat');
    const userLng = container.getAttribute('data-user-lng');
    const hqLat = container.getAttribute('data-hq-lat');
    const hqLng = container.getAttribute('data-hq-lng');

    let centerLng = window.__MOCK_MAP_CENTER__ ? window.__MOCK_MAP_CENTER__[0] : 121.774;
    let centerLat = window.__MOCK_MAP_CENTER__ ? window.__MOCK_MAP_CENTER__[1] : 12.8797;
    let initialZoom = 6;

    if (userLat && userLng) {
        centerLat = parseFloat(userLat);
        centerLng = parseFloat(userLng);
        initialZoom = 8;
    } else if (hqLat && hqLng) {
        centerLat = parseFloat(hqLat);
        centerLng = parseFloat(hqLng);
        initialZoom = 8;
    }

    targetMap = new maplibregl.Map({
        container: containerId,
        style: MAP_STYLES.dark,
        center: [centerLng, centerLat],
        zoom: initialZoom,
        maxZoom: 18,
    });

    targetMap.addControl(new maplibregl.NavigationControl(), 'top-right');
    targetMap.addControl(new maplibregl.FullscreenControl(), 'top-right');
    targetMap.addControl(new IncidentListControl(), 'top-left');
    targetMap.addControl(new StyleToggleControl(), 'bottom-left');

    // Hide the external HTML toggle since it's now inside the map
    const externalToggle = document.getElementById('mapStyleToggle');
    if (externalToggle) externalToggle.style.display = 'none';

    // Load initial data + markers (HQ, reservist, RCDG, CDC, reservist list)
    targetMap.on('load', function () {
        loadIncidents(apiUrl);
        addHQMarker(container);
        addReservistMarker(container);
        addRcdgMarkers();
        addCdcMarkers();
        addReservistListMarkers();
    });

    // Filter listeners
    const timeFilter = document.getElementById('mapTimeFilter');
    const typeFilter = document.getElementById('mapTypeFilter');
    const regionFilter = document.getElementById('mapRegionFilter');

    if (timeFilter) timeFilter.addEventListener('change', () => loadIncidents(apiUrl));
    if (typeFilter) typeFilter.addEventListener('change', () => loadIncidents(apiUrl));
    if (regionFilter) {
        let debounce;
        regionFilter.addEventListener('input', () => {
            clearTimeout(debounce);
            debounce = setTimeout(() => loadIncidents(apiUrl), 400);
        });
    }
}

/**
 * MapLibre custom control: Style Toggle (Light / Dark / Satellite / Streets / OSM)
 * Renders inside the map container so it remains visible in fullscreen mode.
 */
class StyleToggleControl {
    onAdd(map) {
        this._map = map;
        this._container = document.createElement('div');
        this._container.className = 'maplibregl-ctrl map-style-toggle-ctrl';

        const styles = [
            { key: 'light', icon: 'bi-sun-fill', label: 'Light' },
            { key: 'dark', icon: 'bi-moon-fill', label: 'Dark' },
            { key: 'satellite', icon: 'bi-globe-americas', label: 'Satellite' },
            { key: 'streets', icon: 'bi-signpost-split-fill', label: 'Streets' },
            { key: 'osm', icon: 'bi-map-fill', label: 'OSM' },
        ];

        styles.forEach(s => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'map-style-ctrl-btn' + (s.key === 'dark' ? ' active' : '');
            btn.dataset.style = s.key;
            btn.title = s.label;
            btn.innerHTML = `<i class="bi ${s.icon}"></i> ${s.label}`;
            btn.addEventListener('click', () => this._switchStyle(s.key));
            this._container.appendChild(btn);
        });

        // Inject styles
        if (!document.getElementById('mapStyleToggleCtrlCSS')) {
            const css = document.createElement('style');
            css.id = 'mapStyleToggleCtrlCSS';
            css.textContent = `
                .map-style-toggle-ctrl {
                    display: flex;
                    gap: 3px;
                    background: rgba(10, 14, 23, 0.9);
                    backdrop-filter: blur(12px);
                    -webkit-backdrop-filter: blur(12px);
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 10px;
                    padding: 4px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
                    pointer-events: auto;
                    margin: 10px;
                }
                .map-style-ctrl-btn {
                    background: transparent;
                    border: none;
                    color: rgba(255,255,255,0.6);
                    font-size: 0.72rem;
                    padding: 6px 10px;
                    border-radius: 7px;
                    cursor: pointer;
                    transition: all 0.2s;
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    white-space: nowrap;
                }
                .map-style-ctrl-btn:hover {
                    background: rgba(255,255,255,0.08);
                    color: rgba(255,255,255,0.9);
                }
                .map-style-ctrl-btn.active {
                    background: rgba(0, 212, 255, 0.15);
                    color: #00d4ff;
                    font-weight: 600;
                }
                .map-style-ctrl-btn i {
                    font-size: 0.8rem;
                }
            `;
            document.head.appendChild(css);
        }

        return this._container;
    }

    _switchStyle(styleKey) {
        // Update active button
        this._container.querySelectorAll('.map-style-ctrl-btn').forEach(b => b.classList.remove('active'));
        this._container.querySelector(`[data-style="${styleKey}"]`).classList.add('active');

        // Save current state
        const center = this._map.getCenter();
        const zoom = this._map.getZoom();

        // Set new style
        this._map.setStyle(MAP_STYLES[styleKey]);

        // Re-add data after style loads
        this._map.once('styledata', function () {
            setTimeout(function () {
                if (currentApiUrl) loadIncidents(currentApiUrl);
                const mapEl = document.getElementById('incidentMap');
                if (mapEl) addHQMarker(mapEl);
                if (mapEl) addReservistMarker(mapEl);
                addRcdgMarkers();
                addCdcMarkers();
                addReservistListMarkers();
            }, 200);
        });

        // Restore camera
        this._map.setCenter(center);
        this._map.setZoom(zoom);
    }

    onRemove() {
        if (this._container && this._container.parentNode) {
            this._container.parentNode.removeChild(this._container);
        }
        this._map = undefined;
    }
}

/**
 * Add the pulsing HQ marker if coordinates exist on the map container.
 */
function addHQMarker(container) {
    // Remove existing HQ marker
    if (hqMarker) {
        hqMarker.remove();
        hqMarker = null;
    }

    const lat = parseFloat(container.dataset.hqLat);
    const lng = parseFloat(container.dataset.hqLng);
    const name = container.dataset.hqName || 'Headquarters';

    if (isNaN(lat) || isNaN(lng)) return;

    // Create pulsing marker element
    const el = document.createElement('div');
    el.className = 'hq-marker';
    el.style.width = '0px';
    el.style.height = '0px';
    el.innerHTML = '<div class="hq-dot"></div>';

    // Popup
    const popup = new maplibregl.Popup({ offset: 14, maxWidth: '240px' }).setHTML(`
        <div style="text-align:center;">
            <div style="font-size:1.2rem;margin-bottom:4px;">🏛️</div>
            <div style="font-weight:700;font-size:0.88rem;">${name}</div>
            <div style="font-size:0.72rem;color:#94a3b8;">Command Headquarters</div>
            <div style="font-size:0.7rem;color:#64748b;margin-top:4px;font-family:monospace;">
                ${lat.toFixed(7)}, ${lng.toFixed(7)}
            </div>
        </div>
    `);

    hqMarker = new maplibregl.Marker({ element: el, anchor: 'center' })
        .setLngLat([lng, lat])
        .setPopup(popup)
        .addTo(targetMap);
}

/**
 * Add reservist (user) location marker when data-reservist-lat/lng are set (e.g. reservist dashboard).
 */
function addReservistMarker(container) {
    if (!container || !targetMap) return;
    if (reservistMarker) {
        reservistMarker.remove();
        reservistMarker = null;
    }

    const lat = parseFloat(container.dataset.reservistLat);
    const lng = parseFloat(container.dataset.reservistLng);
    if (isNaN(lat) || isNaN(lng)) return;

    const el = document.createElement('div');
    el.className = 'reservist-marker';
    el.style.width = '0px';
    el.style.height = '0px';
    el.innerHTML = '<div class="reservist-dot"></div>';

    const popup = new maplibregl.Popup({ offset: 14, maxWidth: '240px' });
    popup.on('open', () => {
        const distHtml = getReservistDistanceHtml(lat, lng);
        popup.setHTML(`
            <div style="text-align:center;">
                <div style="font-size:1.2rem;margin-bottom:4px;">📍</div>
                <div style="font-weight:700;font-size:0.88rem;">My Home Address</div>
                <div style="font-size:0.72rem;color:#94a3b8;">Reservist</div>
                <div style="font-size:0.7rem;color:#64748b;margin-top:4px;font-family:monospace;">
                    ${lat.toFixed(7)}, ${lng.toFixed(7)}
                </div>
            </div>
            ${distHtml}
        `);
    });

    reservistMarker = new maplibregl.Marker({ element: el, anchor: 'center' })
        .setLngLat([lng, lat])
        .setPopup(popup)
        .addTo(targetMap);
}

/**
 * Add green pulsing markers for each RCDG location.
 */
function addRcdgMarkers() {
    // Remove existing RCDG markers
    rcdgMarkers.forEach(m => m.remove());
    rcdgMarkers = [];

    const locations = window.__RCDG_LOCATIONS__ || [];
    locations.forEach(rcdg => {
        const lat = parseFloat(rcdg.latitude);
        const lng = parseFloat(rcdg.longitude);
        if (isNaN(lat) || isNaN(lng)) return;

        const el = document.createElement('div');
        el.className = 'rcdg-pulse-marker';
        el.style.width = '0px';
        el.style.height = '0px';
        el.innerHTML = '<div class="rcdg-dot"></div>';

        const popup = new maplibregl.Popup({ offset: 14, maxWidth: '260px' }).setHTML(`
            <div style="text-align:center;">
                <div style="font-size:1.2rem;margin-bottom:4px;">🟢</div>
                <div style="font-weight:700;font-size:0.88rem;">${rcdg.rcdg_desc}</div>
                <div style="font-size:0.75rem;color:#94a3b8;">${rcdg.rcdg_address || ''}</div>
                <div style="font-size:0.72rem;color:#64748b;margin-top:2px;">Commander: ${rcdg.rcdg_commander || '—'}</div>
                <div style="font-size:0.7rem;color:#64748b;margin-top:4px;font-family:monospace;">
                    ${lat.toFixed(7)}, ${lng.toFixed(7)}
                </div>
            </div>
        `);

        const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat([lng, lat])
            .setPopup(popup)
            .addTo(targetMap);
        rcdgMarkers.push(marker);
    });
}

/**
 * Add purple pulsing markers for each CDC location.
 */
function addCdcMarkers() {
    // Remove existing CDC markers
    cdcMarkers.forEach(m => m.remove());
    cdcMarkers = [];

    const locations = window.__CDC_LOCATIONS__ || [];
    locations.forEach(cdc => {
        const lat = parseFloat(cdc.latitude);
        const lng = parseFloat(cdc.longitude);
        if (isNaN(lat) || isNaN(lng)) return;

        const el = document.createElement('div');
        el.className = 'cdc-pulse-marker';
        el.style.width = '0px';
        el.style.height = '0px';
        el.innerHTML = '<div class="cdc-dot"></div>';

        const popup = new maplibregl.Popup({ offset: 14, maxWidth: '260px' }).setHTML(`
            <div style="text-align:center;">
                <div style="font-size:1.2rem;margin-bottom:4px;">🟣</div>
                <div style="font-weight:700;font-size:0.88rem;">${cdc.cdc_code}</div>
                <div style="font-size:0.75rem;color:#94a3b8;">${cdc.cdc_desc || ''}</div>
                <div style="font-size:0.75rem;color:#94a3b8;">${cdc.cdc_address || ''}</div>
                <div style="font-size:0.72rem;color:#64748b;margin-top:2px;">Director: ${cdc.cdc_director || '—'}</div>
                <div style="font-size:0.7rem;color:#64748b;margin-top:4px;font-family:monospace;">
                    ${lat.toFixed(7)}, ${lng.toFixed(7)}
                </div>
            </div>
        `);

        const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat([lng, lat])
            .setPopup(popup)
            .addTo(targetMap);
        cdcMarkers.push(marker);
    });
}

/**
 * Add markers for reservists (on command dashboards: RESCOM all, RCDG/CDC their own).
 */
function addReservistListMarkers() {
    reservistListMarkers.forEach(m => m.remove());
    reservistListMarkers = [];

    const locations = window.__RESERVIST_LOCATIONS__ || [];
    if (!targetMap) return;

    locations.forEach(r => {
        const lat = parseFloat(r.latitude);
        const lng = parseFloat(r.longitude);
        if (isNaN(lat) || isNaN(lng)) return;

        const el = document.createElement('div');
        el.className = 'reservist-list-marker';
        el.style.width = '0px';
        el.style.height = '0px';
        el.innerHTML = '<div class="reservist-list-dot"></div>';

        const name = (r.full_name || 'Reservist').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const rank = (r.rank || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const popup = new maplibregl.Popup({ offset: 14, maxWidth: '260px' });
        popup.on('open', () => {
            const distHtml = getReservistDistanceHtml(lat, lng);
            popup.setHTML(`
                <div style="text-align:center;">
                    <div style="font-size:1.2rem;margin-bottom:4px;">📍</div>
                    <div style="font-weight:700;font-size:0.88rem;">${name}'s Home Address</div>
                    <div style="font-size:0.72rem;color:#94a3b8;">Reservist${rank ? ' · ' + rank : ''}</div>
                    <div style="font-size:0.7rem;color:#64748b;margin-top:4px;font-family:monospace;">
                        ${lat.toFixed(7)}, ${lng.toFixed(7)}
                    </div>
                </div>
                ${distHtml}
            `);
        });

        const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat([lng, lat])
            .setPopup(popup)
            .addTo(targetMap);
        reservistListMarkers.push(marker);
    });
}

/**
 * Load incidents from the API and render markers.
 */
function loadIncidents(apiUrl) {
    // Build query params from filters
    const params = new URLSearchParams();
    const time = document.getElementById('mapTimeFilter')?.value;
    const type = document.getElementById('mapTypeFilter')?.value;
    const region = document.getElementById('mapRegionFilter')?.value;

    if (time) params.set('time', time);
    if (type) params.set('type', type);
    if (region) params.set('region', region);

    const url = apiUrl + (params.toString() ? '?' + params.toString() : '');

    fetch(url, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        },
    })
        .then((response) => response.json())
        .then((geojson) => {
            renderMarkers(geojson);
        })
        .catch((err) => {
            console.error('Failed to load incidents:', err);
        });
}

/**
 * Render markers on the map from GeoJSON data.
 */
function renderMarkers(geojson) {
    // Clear existing markers
    currentMarkers.forEach((m) => m.remove());
    currentMarkers = [];
    currentGeojsonFeatures = geojson.features || [];

    if (!geojson.features || geojson.features.length === 0) return;

    const bounds = new maplibregl.LngLatBounds();

    geojson.features.forEach((feature) => {
        const coords = feature.geometry.coordinates;
        const props = feature.properties;

        // Create pulsing red dot marker
        const el = document.createElement('div');
        el.className = 'incident-pulse-marker';
        el.style.width = '0px';
        el.style.height = '0px';
        el.innerHTML = '<div class="inc-pulse"></div><div class="inc-dot"></div>';
        el.style.cursor = 'pointer';

        // Popup content
        const popupHTML = `
      <div style="min-width:200px;">
        <h6 style="margin:0 0 6px;font-size:0.9rem;font-weight:700;">${props.title}</h6>
        <div style="margin-bottom:6px;">
          <span style="display:inline-block;padding:2px 8px;border-radius:12px;font-size:0.7rem;font-weight:600;
            background:${props.marker_color}22;color:${props.marker_color};">
            ${props.incident_type_display}
          </span>
          <span style="display:inline-block;padding:2px 8px;border-radius:12px;font-size:0.7rem;font-weight:600;
            background:rgba(100,116,139,0.2);color:#94a3b8;">
            ${props.status_display}
          </span>
        </div>
        <div style="font-size:0.78rem;color:#94a3b8;margin-bottom:4px;">
          📍 ${props.municipality || ''}, ${props.province || ''}, ${props.region || ''}
        </div>
        <div style="font-size:0.78rem;color:#94a3b8;margin-bottom:4px;">
          🕐 ${props.created_at}
        </div>
        <div style="font-size:0.75rem;color:#64748b;margin-bottom:8px;">
          Lat: ${props.latitude}, Lng: ${props.longitude}
        </div>
        <a href="${props.detail_url}" style="
          display:inline-block;padding:4px 12px;border-radius:6px;font-size:0.75rem;font-weight:600;
          background:linear-gradient(135deg,#00d4ff,#0099cc);color:#0a0e17;text-decoration:none;
        ">View Full Report →</a>
      </div>
    `;

        const popup = new maplibregl.Popup({
            offset: 16,
            maxWidth: '320px',
        }).setHTML(popupHTML);

        const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat(coords)
            .setPopup(popup)
            .addTo(targetMap);

        currentMarkers.push(marker);
        bounds.extend(coords);
    });

    // Focus map on the latest incident
    if (geojson.features && geojson.features.length > 0) {
        const latestIncidentCoords = geojson.features[0].geometry.coordinates;
        targetMap.flyTo({ center: latestIncidentCoords, zoom: 14, duration: 1500 });
    }

    updateIncidentListPanel(geojson.features);
}

/**
 * Handle updating the dynamic incident list panel shown in fullscreen mode.
 */
function updateIncidentListPanel(features) {
    const listContainer = document.getElementById('mapIncidentListItems');
    const countBadge = document.getElementById('mapIncidentCount');
    if (!listContainer) return;

    countBadge.textContent = features ? features.length : 0;
    listContainer.innerHTML = '';

    if (!features || features.length === 0) {
        listContainer.innerHTML = '<div style="padding:16px;text-align:center;color:#64748b;font-size:0.8rem;">No incidents found.</div>';
        return;
    }

    features.forEach(feature => {
        const props = feature.properties;
        const item = document.createElement('div');
        item.className = 'map-incident-item';
        item.onclick = () => {
            targetMap.flyTo({ center: feature.geometry.coordinates, zoom: 15 });
        };
        item.innerHTML = `
            <div style="font-weight:700;font-size:0.85rem;margin-bottom:2px;color:white;">${props.title}</div>
            <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:4px;">
                <span style="color:${props.marker_color};">${props.incident_type_display}</span> • ${props.status_display}
            </div>
            <div style="font-size:0.7rem;color:#64748b;margin-bottom:2px;">📍 ${props.municipality || 'Location'}, ${props.province || ''}</div>
            <div style="font-size:0.7rem;color:#64748b;display:flex;justify-content:space-between;align-items:center;">
                <span>🕐 ${props.created_at.split(' ')[0]} ${props.created_at.split(' ')[1]}</span>
                <a href="${props.detail_url}" class="detail-link" target="_blank" style="color:var(--accent);text-decoration:none;padding:2px 6px;border-radius:4px;background:rgba(0, 212, 255, 0.1);">View <i class="bi bi-box-arrow-up-right"></i></a>
            </div>
        `;
        // Prevent link click from triggering the flyTo
        const link = item.querySelector('.detail-link');
        if (link) {
            link.onclick = (e) => e.stopPropagation();
        }
        listContainer.appendChild(item);
    });
}

/**
 * Custom MapLibre Control to display the Incident List natively within the map container.
 * Uses JavaScript fullscreenchange event for reliable cross-browser visibility toggling.
 */
class IncidentListControl {
    onAdd(map) {
        this._map = map;
        this._container = document.createElement('div');
        this._container.className = 'maplibregl-ctrl map-incident-list-panel';
        this._container.id = 'mapIncidentListPanel';

        this._container.innerHTML = `
            <div style="padding:12px 16px;border-bottom:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;align-items:center;background:rgba(0,0,0,0.2);">
                <h6 style="margin:0;font-size:0.9rem;font-weight:700;color:white;"><i class="bi bi-list-ul"></i> Live Incidents</h6>
                <span class="badge" id="mapIncidentCount" style="background:var(--accent);color:#000;font-size:0.75rem;padding:4px 8px;border-radius:10px;">0</span>
            </div>
            <div id="mapIncidentListItems" style="flex:1;overflow-y:auto;padding:8px;"></div>
        `;

        // Inject styles
        if (!document.getElementById('mapListPanelStyles')) {
            const style = document.createElement('style');
            style.id = 'mapListPanelStyles';
            style.textContent = `
                .map-incident-list-panel {
                    display: none;
                    width: 300px;
                    max-height: calc(100vh - 80px);
                    background: rgba(10, 14, 23, 0.95);
                    backdrop-filter: blur(12px);
                    -webkit-backdrop-filter: blur(12px);
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 8px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
                    flex-direction: column;
                    pointer-events: auto;
                    margin: 10px;
                }
                .map-incident-list-panel.is-fullscreen {
                    display: flex !important;
                }
                .map-incident-item {
                    padding: 12px;
                    border-bottom: 1px solid rgba(255,255,255,0.05);
                    cursor: pointer;
                    transition: background 0.2s;
                    border-radius: 6px;
                }
                .map-incident-item:hover {
                    background: rgba(255,255,255,0.08);
                }
                .map-incident-item:last-child {
                    border-bottom: none;
                }
                .map-incident-list-panel #mapIncidentListItems {
                    overflow-y: auto;
                    max-height: calc(100vh - 140px);
                    scrollbar-width: thin;
                    scrollbar-color: rgba(255,255,255,0.2) transparent;
                }
                .map-incident-list-panel #mapIncidentListItems::-webkit-scrollbar {
                    width: 6px;
                }
                .map-incident-list-panel #mapIncidentListItems::-webkit-scrollbar-track {
                    background: transparent;
                }
                .map-incident-list-panel #mapIncidentListItems::-webkit-scrollbar-thumb {
                    background: rgba(255,255,255,0.2);
                    border-radius: 3px;
                }
                .map-incident-list-panel #mapIncidentListItems::-webkit-scrollbar-thumb:hover {
                    background: rgba(255,255,255,0.35);
                }
            `;
            document.head.appendChild(style);
        }

        // Listen for fullscreen changes to toggle panel visibility via JS
        const panel = this._container;
        document.addEventListener('fullscreenchange', function () {
            if (document.fullscreenElement) {
                panel.classList.add('is-fullscreen');
            } else {
                panel.classList.remove('is-fullscreen');
            }
        });
        document.addEventListener('webkitfullscreenchange', function () {
            if (document.webkitFullscreenElement) {
                panel.classList.add('is-fullscreen');
            } else {
                panel.classList.remove('is-fullscreen');
            }
        });

        return this._container;
    }
    onRemove() {
        if (this._container && this._container.parentNode) {
            this._container.parentNode.removeChild(this._container);
        }
        this._map = undefined;
    }
}
