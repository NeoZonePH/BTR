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
        // Refresh active responder positions periodically so other accounts (RESCOM, CDC, etc.) see live movement
        if (!window.__activeRespondersRefreshInterval) {
            window.__activeRespondersRefreshInterval = setInterval(loadActiveResponders, 10000);
        }
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
 * @param {Object} [options] - Optional. { simple: true } for location-picker maps (no incident reload).
 *   When simple, options.onStyleChanged(map) is called after style load so the page can re-add markers.
 */
class StyleToggleControl {
    constructor(options) {
        this._options = options || {};
    }

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

        const self = this;
        this._map.once('styledata', function () {
            // Restore camera
            self._map.setCenter(center);
            self._map.setZoom(zoom);
            if (self._options.simple && typeof self._options.onStyleChanged === 'function') {
                self._options.onStyleChanged(self._map);
            } else {
                setTimeout(function () {
                    if (currentApiUrl) loadIncidents(currentApiUrl);
                    const mapEl = document.getElementById('incidentMap');
                    if (mapEl) addHQMarker(mapEl);
                    if (mapEl) addReservistMarker(mapEl);
                    addRcdgMarkers();
                    addCdcMarkers();
                    addReservistListMarkers();
                }, 200);
            }
        });
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

    const lat = parseFloat(container.dataset.reservistLat || container.dataset.userLat);
    const lng = parseFloat(container.dataset.reservistLng || container.dataset.userLng);
    if (isNaN(lat) || isNaN(lng)) return;
    const locationLabel = window.__USER_LOCATION_LABEL__ || 'My Home Address';
    const roleLabel = window.__USER_ROLE_LABEL__ || 'Reservist';

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
                <div style="font-weight:700;font-size:0.88rem;">${locationLabel}</div>
                <div style="font-size:0.72rem;color:#94a3b8;">${roleLabel}</div>
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
    // Clear existing incident markers and responder markers (so filter changes show only current incidents' responders)
    currentMarkers.forEach((m) => m.remove());
    currentMarkers = [];
    clearActiveResponderMarkers();
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

        // Respond / Stop Button — show for reservists, PDRRMO, and MDRRMO (supports multiple responders per incident)
        let respondBtnHTML = '';
        if (window.__IS_RESERVIST__ === true || window.__CAN_RESPOND_TO_INCIDENT__ === true) {
            const isRespondingToThis = (typeof currentRespondingIncidentId !== 'undefined' && currentRespondingIncidentId != null && String(props.id) === String(currentRespondingIncidentId));
            if (isRespondingToThis) {
                respondBtnHTML = `
            <button onclick="stopRespondingAndNotify(event, '${props.id}')" style="
            display:inline-block;padding:4px 12px;border-radius:6px;font-size:0.75rem;font-weight:600;
            background:linear-gradient(135deg,#dc2626,#b91c1c);color:#ffffff;border:none;cursor:pointer;
            ">Stop ⏹</button>`;
            } else {
                respondBtnHTML = `
            <button onclick="startResponding(event, '${props.id}')" style="
            display:inline-block;padding:4px 12px;border-radius:6px;font-size:0.75rem;font-weight:600;
            background:linear-gradient(135deg,#10b981,#059669);color:#ffffff;border:none;cursor:pointer;
            ">Respond 🏃</button>`;
            }
        }

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
        <div style="display:flex;gap:8px;">
          <a href="${props.detail_url}" class="btn-target" style="
            display:inline-block;padding:4px 12px;border-radius:6px;font-size:0.75rem;font-weight:600;
            background:linear-gradient(135deg,#00d4ff,#0099cc);color:#0a0e17;text-decoration:none;
          ">View Full Report →</a>
          ${respondBtnHTML}
        </div>
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

    // Command dashboards (and reservists) observe updates for incidents on the map
    if (typeof observeIncidentTrackers === 'function') {
        observeIncidentTrackers(geojson.features);
    }

    // Restore active responder markers from API so they persist after page refresh (RESCOM, CDC, RCDG, PDRRMO, MDRRMO)
    loadActiveResponders();
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

// ── Responder Tracking Logic ──
let activeWatchId = null;
let activeLocationPollId = null;
let trackingSocket = null;
let currentRespondingIncidentId = null; // Which incident the current user is responding to (for showing Stop in popup)
let activeResponderMarkers = {}; // Store by reservist_id to handle multiple responders
let lastResponderCoords = null;

function getResponderMarkerDisplayCoords(lat, lng, index, total) {
    if (total <= 1) {
        return [lng, lat];
    }

    // Spread responders with the same coordinates into a small circle so
    // command dashboards can still see each active responder separately.
    const radiusDegrees = 0.00018;
    const angle = (Math.PI * 2 * index) / total;
    const latOffset = radiusDegrees * Math.sin(angle);
    const lngScale = Math.max(Math.cos((lat * Math.PI) / 180), 0.2);
    const lngOffset = (radiusDegrees * Math.cos(angle)) / lngScale;

    return [lng + lngOffset, lat + latOffset];
}

function refreshResponderMarkerPositions() {
    const markers = Object.values(activeResponderMarkers).filter(Boolean);
    if (!markers.length) return;

    const groups = {};
    markers.forEach((marker) => {
        const data = marker.__responderData;
        if (!data) return;
        const key = `${data.latitude.toFixed(5)}:${data.longitude.toFixed(5)}`;
        if (!groups[key]) groups[key] = [];
        groups[key].push(marker);
    });

    Object.values(groups).forEach((group) => {
        group.forEach((marker, index) => {
            const data = marker.__responderData;
            if (!data) return;
            const displayCoords = getResponderMarkerDisplayCoords(
                data.latitude,
                data.longitude,
                index,
                group.length
            );
            marker.setLngLat(displayCoords);
        });
    });
}

function getResponderFallbackCoords() {
    const mapEl = document.getElementById('incidentMap');
    if (!mapEl) return null;

    const lat = parseFloat(mapEl.dataset.userLat);
    const lng = parseFloat(mapEl.dataset.userLng);
    if (!Number.isNaN(lat) && !Number.isNaN(lng)) {
        return { lat, lng, source: 'saved account location' };
    }

    return null;
}

/** Remove a single responder's marker and route from the map (e.g. when they click Stop). */
function removeResponderMarker(reservistId) {
    if (!targetMap || !reservistId) return;
    const rid = String(reservistId);
    const m = activeResponderMarkers[rid];
    if (m) {
        m.remove();
        delete activeResponderMarkers[rid];
    }
    const routeId = 'route_' + rid;
    if (targetMap.getLayer(routeId)) targetMap.removeLayer(routeId);
    if (targetMap.getSource(routeId)) targetMap.removeSource(routeId);
    refreshResponderMarkerPositions();
}

/** Remove all responder markers and their route layers so they can be repopulated (e.g. after filter change or load). */
function clearActiveResponderMarkers() {
    if (!targetMap) return;
    for (const rid of Object.keys(activeResponderMarkers)) {
        const m = activeResponderMarkers[rid];
        if (m) m.remove();
        const routeId = 'route_' + rid;
        if (targetMap.getLayer(routeId)) targetMap.removeLayer(routeId);
        if (targetMap.getSource(routeId)) targetMap.removeSource(routeId);
    }
    activeResponderMarkers = {};
}

/**
 * Load current active responders from the API and draw them on the map.
 * Ensures responder markers persist after page refresh for RESCOM, CDC, RCDG, PDRRMO, MDRRMO.
 */
function loadActiveResponders() {
    if (!targetMap || !currentGeojsonFeatures || currentGeojsonFeatures.length === 0) return;
    const incidentIds = new Set(currentGeojsonFeatures.map(f => String(f.properties.id)));
    fetch('/api/responders/active/', {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
        .then((res) => res.json())
        .then((data) => {
            const responders = data.responders || [];
            const currentUserId = (typeof window.__USER_ID__ !== 'undefined' && window.__USER_ID__ != null)
                ? String(window.__USER_ID__)
                : null;
            let currentUserActiveIncidentId = null;

            responders.forEach((r) => {
                if (incidentIds.has(String(r.incident_id))) {
                    updateResponderOnMap(r, true);
                    if (currentUserId && String(r.reservist_id) === currentUserId) {
                        currentUserActiveIncidentId = String(r.incident_id);
                    }
                }
            });

            // Rehydrate the responder's own active-response state after refresh so the
            // popup can still show Stop while the tracking row remains active.
            currentRespondingIncidentId = currentUserActiveIncidentId;
        })
        .catch((err) => console.error('Failed to load active responders:', err));
}

function startResponding(event, incidentId) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    const fallbackCoords = getResponderFallbackCoords();

    if (!navigator.geolocation && !fallbackCoords) {
        alert("Geolocation is not supported by your browser, and no saved account location is available.");
        return;
    }

    if (activeWatchId) {
        if (!confirm("You are already tracking an incident. Switch to this one?")) {
            return;
        }
        stopResponding();
    }

    if (event && event.target) {
        event.target.textContent = "Connecting...";
        event.target.disabled = true;
    }

    // Connect WebSocket
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    trackingSocket = new WebSocket(`${wsProtocol}//${window.location.host}/ws/incident/${incidentId}/tracking/`);

    currentRespondingIncidentId = incidentId;

    trackingSocket.onopen = function (e) {
        console.log("Tracking WebSocket connected for incident", incidentId);
        if (event && event.target) {
            const statusBtn = event.target;
            statusBtn.textContent = "Responding 🏃";
            statusBtn.style.background = 'linear-gradient(135deg,#f59e0b,#d97706)';
            statusBtn.style.color = '#fff';
            statusBtn.onclick = null;
            statusBtn.disabled = true;
            // Add a dedicated Stop button so the user can always cancel (visible even when status becomes "On Scene")
            if (!statusBtn.parentNode.querySelector('.respond-stop-btn')) {
                const stopBtn = document.createElement('button');
                stopBtn.type = 'button';
                stopBtn.className = 'respond-stop-btn';
                stopBtn.textContent = 'Stop ⏹';
                stopBtn.style.cssText = 'display:inline-block;padding:4px 12px;border-radius:6px;font-size:0.75rem;font-weight:600;background:linear-gradient(135deg,#dc2626,#b91c1c);color:#ffffff;border:none;cursor:pointer;';
                stopBtn.onclick = function (ev) {
                    ev.preventDefault();
                    ev.stopPropagation();
                    stopRespondingAndNotify(ev, incidentId);
                };
                statusBtn.parentNode.appendChild(stopBtn);
            }
        }
    };

    trackingSocket.onmessage = function (e) {
        const payload = JSON.parse(e.data);
        if (payload.type === 'responder_stopped' && payload.data && payload.data.reservist_id) {
            removeResponderMarker(payload.data.reservist_id);
            return;
        }
        const actualData = payload.data ? payload.data : payload;
        console.log("Tracking update received:", actualData);
        updateResponderOnMap(actualData, true);
    };

    trackingSocket.onclose = function (e) {
        console.log("Tracking WebSocket closed");
    };

    // Helper: update map with current position (so marker appears and moves in real time for the reservist)
    function applyPositionToMap(lat, lng, status) {
        const uid = (typeof window.__USER_ID__ !== 'undefined' && window.__USER_ID__ != null) ? String(window.__USER_ID__) : null;
        if (!uid) return;
        updateResponderOnMap({
            reservist_id: uid,
            reservist_name: (typeof window.__USER_NAME__ !== 'undefined' && window.__USER_NAME__) ? window.__USER_NAME__ : 'You',
            latitude: lat,
            longitude: lng,
            status: status || 'Responding',
            incident_id: incidentId,
        }, true);
    }

    function shouldSendResponderPosition(lat, lng, force = false) {
        if (force || !lastResponderCoords) {
            lastResponderCoords = { lat, lng };
            return true;
        }
        const latChanged = Math.abs(lastResponderCoords.lat - lat) > 0.000005;
        const lngChanged = Math.abs(lastResponderCoords.lng - lng) > 0.000005;
        if (latChanged || lngChanged) {
            lastResponderCoords = { lat, lng };
            return true;
        }
        return false;
    }

    function syncResponderPosition(lat, lng, force = false) {
        applyPositionToMap(lat, lng, 'Responding');

        const uid = (typeof window.__USER_ID__ !== 'undefined' && window.__USER_ID__ != null) ? String(window.__USER_ID__) : null;
        if (!shouldSendResponderPosition(lat, lng, force)) {
            return;
        }

        fetch('/api/responder/update-location/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                incident_id: incidentId,
                latitude: lat,
                longitude: lng
            })
        })
            .then(res => res.json())
            .then(data => {
                if (data.success && data.status === 'On Scene') {
                    // Update status button (first button in the popup actions) to "On Scene" — Stop button stays visible
                    if (event && event.target) {
                        event.target.textContent = "On Scene ✅";
                        event.target.style.background = 'linear-gradient(135deg,#3b82f6,#2563eb)';
                    }
                    // Update responder marker label to "On Scene"
                    if (uid && activeResponderMarkers[uid]) {
                        const markerEl = activeResponderMarkers[uid].getElement();
                        if (markerEl) {
                            const statusNode = markerEl.querySelector('.resp-status');
                            if (statusNode) statusNode.textContent = 'On Scene';
                        }
                    }
                }
            })
            .catch(err => console.error("Error updating location:", err));
    }

    function useFallbackLocation(message) {
        if (!fallbackCoords) {
            alert(message || "Error getting location. Ensure location permissions are enabled.");
            stopResponding();
            if (event && event.target) {
                event.target.textContent = "Respond 🏃";
                event.target.disabled = false;
                event.target.style.background = 'linear-gradient(135deg,#10b981,#059669)';
            }
            return false;
        }

        console.warn(message || "Using fallback responder location.");
        syncResponderPosition(fallbackCoords.lat, fallbackCoords.lng, true);

        if (event && event.target) {
            event.target.textContent = "Responding 🏃";
            event.target.disabled = true;
            event.target.style.background = 'linear-gradient(135deg,#f59e0b,#d97706)';
            event.target.title = 'Using saved account location because browser location is unavailable.';
        }

        return true;
    }

    // Get initial position so the marker appears right away (watchPosition may take a moment)
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                syncResponderPosition(lat, lng, true);
            },
            () => {
                useFallbackLocation("Initial browser location unavailable. Using saved account location instead.");
            },
            { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
        );

        // Start GPS watch so marker moves as you move
        activeWatchId = navigator.geolocation.watchPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                syncResponderPosition(lat, lng);
            },
            (error) => {
                console.error("Geolocation error:", error);
                if (useFallbackLocation("Browser location permission denied or unavailable. Using saved account location instead.")) {
                    if (activeWatchId) {
                        navigator.geolocation.clearWatch(activeWatchId);
                        activeWatchId = null;
                    }
                    if (activeLocationPollId) {
                        window.clearInterval(activeLocationPollId);
                        activeLocationPollId = null;
                    }
                }
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );

        // Fallback polling keeps live movement reliable on browsers/devices where watchPosition is sparse.
        activeLocationPollId = window.setInterval(() => {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    syncResponderPosition(lat, lng);
                },
                () => {},
                { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
            );
        }, 3000);
    } else {
        useFallbackLocation("Browser geolocation is not supported. Using saved account location instead.");
    }
}

function stopResponding() {
    currentRespondingIncidentId = null;
    lastResponderCoords = null;
    if (activeWatchId) {
        navigator.geolocation.clearWatch(activeWatchId);
        activeWatchId = null;
    }
    if (activeLocationPollId) {
        window.clearInterval(activeLocationPollId);
        activeLocationPollId = null;
    }
    if (trackingSocket) {
        trackingSocket.close();
        trackingSocket = null;
    }
}

/**
 * Stop responding and notify backend so all dashboards remove this responder's marker.
 * Then remove the current user's marker from this map and clear tracking state.
 */
function stopRespondingAndNotify(event, incidentId) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const stopBtn = event && event.target;
    if (stopBtn) {
        stopBtn.textContent = "Stopping...";
        stopBtn.disabled = true;
    }
    fetch('/api/responder/stop/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ incident_id: incidentId }),
    })
        .then(() => {
            stopResponding();
            const uid = (typeof window.__USER_ID__ !== 'undefined' && window.__USER_ID__ != null) ? String(window.__USER_ID__) : null;
            if (uid) removeResponderMarker(uid);
        })
        .catch((err) => console.error('Error stopping responder:', err))
        .finally(() => {
            // Remove the Stop button and restore the status button to "Respond" so the popup can be used again
            if (stopBtn && stopBtn.parentNode) {
                const statusBtn = stopBtn.previousElementSibling;
                stopBtn.remove();
                if (statusBtn && typeof statusBtn !== 'undefined') {
                    statusBtn.textContent = "Respond 🏃";
                    statusBtn.disabled = false;
                    statusBtn.style.background = 'linear-gradient(135deg,#10b981,#059669)';
                    statusBtn.style.color = '#ffffff';
                    statusBtn.onclick = function (ev) {
                        startResponding(ev, incidentId);
                    };
                }
            }
        });
}

function getDistanceToIncident(respLat, respLng, incidentId) {
    if (!currentGeojsonFeatures || currentGeojsonFeatures.length === 0) return null;
    const f = currentGeojsonFeatures.find(feat => String(feat.properties.id) === String(incidentId));
    if (!f) return null;
    const incLat = f.geometry.coordinates[1];
    const incLng = f.geometry.coordinates[0];
    const dist = calculateDistance(respLat, respLng, incLat, incLng);
    if (dist === null) return null;
    const km = parseFloat(dist);
    if (km < 1) return (km * 1000).toFixed(0) + ' m';
    return km.toFixed(2) + ' km';
}

function updateResponderOnMap(data, drawRoute = false) {
    if (!targetMap) return;

    const lng = parseFloat(data.longitude);
    const lat = parseFloat(data.latitude);
    if (Number.isNaN(lat) || Number.isNaN(lng)) return;
    const coords = [lng, lat];
    const rid = data.reservist_id;
    const distText = getDistanceToIncident(lat, lng, data.incident_id) || '';

    if (!activeResponderMarkers[rid]) {
        if (!document.getElementById('responderMarkerStyle')) {
            const style = document.createElement('style');
            style.id = 'responderMarkerStyle';
            style.textContent = `
                .responder-pulse-marker {
                    position: relative;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .resp-dot {
                    width: 16px;
                    height: 16px;
                    background-color: #f59e0b;
                    border-radius: 50%;
                    box-shadow: 0 0 10px rgba(245, 158, 11, 0.8);
                    position: absolute;
                    z-index: 2;
                    border: 2px solid white;
                }
                .resp-pulse {
                    width: 70px;
                    height: 70px;
                    background-color: rgba(245, 158, 11, 0.5);
                    border-radius: 50%;
                    position: absolute;
                    z-index: 1;
                    animation: respPulseAnim 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
                }
                @keyframes respPulseAnim {
                    0% { transform: scale(0.5); opacity: 1; }
                    100% { transform: scale(1.5); opacity: 0; }
                }
                .resp-label {
                    position: absolute;
                    top: 25px;
                    background: rgba(0,0,0,0.85);
                    color: #fff;
                    padding: 6px 12px;
                    border-radius: 6px;
                    font-size: 0.75rem;
                    white-space: nowrap;
                    backdrop-filter: blur(6px);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    z-index: 3;
                    border: 1px solid rgba(255,255,255,0.15);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
                }
                .resp-distance {
                    font-size: 0.7rem;
                    font-weight: 700;
                    color: #00d4ff;
                    margin-top: 3px;
                    padding: 2px 8px;
                    background: rgba(0, 212, 255, 0.1);
                    border-radius: 4px;
                }
            `;
            document.head.appendChild(style);
        }

        const el = document.createElement('div');
        el.className = 'responder-pulse-marker';
        el.style.width = '0px';
        el.style.height = '0px';
        el.style.cursor = 'pointer';
        el.innerHTML = `
            <div class="resp-pulse"></div>
            <div class="resp-dot"></div>
            <div class="resp-label">
                <strong style="color:var(--accent,#f59e0b);font-size:0.7rem;text-transform:uppercase;">Responder</strong>
                <span style="font-weight:700;font-size:0.8rem;">${data.reservist_name}</span>
                <span class="resp-status" style="font-size:0.65rem;color:#94a3b8;margin-top:2px;">${data.status}</span>
                ${distText ? `<span class="resp-distance">📍 ${distText} away</span>` : '<span class="resp-distance"></span>'}
            </div>
        `;

        activeResponderMarkers[rid] = new maplibregl.Marker({ element: el, anchor: 'center' })
            .setLngLat(coords)
            .addTo(targetMap);
        activeResponderMarkers[rid].__responderData = {
            latitude: lat,
            longitude: lng,
            incidentId: String(data.incident_id || ''),
        };
    } else {
        activeResponderMarkers[rid].__responderData = {
            latitude: lat,
            longitude: lng,
            incidentId: String(data.incident_id || ''),
        };

        const el = activeResponderMarkers[rid].getElement();
        if (el) {
            const statusNode = el.querySelector('.resp-status');
            if (statusNode) statusNode.textContent = data.status;
            const distNode = el.querySelector('.resp-distance');
            if (distNode) {
                distNode.innerHTML = distText ? `📍 ${distText} away` : '';
            }
        }
    }

    refreshResponderMarkerPositions();

    if (drawRoute) {
        drawRouteToIncident(coords, data.incident_id, rid);
    }
}

function drawRouteToIncident(startCoords, incidentId, reservistId) {
    if (!currentGeojsonFeatures) return;
    const incidentFeature = currentGeojsonFeatures.find(f => f.properties.id == incidentId);
    if (!incidentFeature) return;

    const endCoords = incidentFeature.geometry.coordinates; // [lng, lat]
    const url = `https://router.project-osrm.org/route/v1/driving/${startCoords[0]},${startCoords[1]};${endCoords[0]},${endCoords[1]}?overview=full&geometries=geojson`;

    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.routes && data.routes.length > 0) {
                const route = data.routes[0].geometry;
                const routeId = 'route_' + reservistId;

                if (targetMap.getSource(routeId)) {
                    targetMap.getSource(routeId).setData(route);
                } else {
                    targetMap.addSource(routeId, {
                        'type': 'geojson',
                        'data': route
                    });

                    targetMap.addLayer({
                        'id': routeId,
                        'type': 'line',
                        'source': routeId,
                        'layout': {
                            'line-join': 'round',
                            'line-cap': 'round'
                        },
                        'paint': {
                            'line-color': '#00d4ff',
                            'line-width': 4,
                            'line-opacity': 0.8,
                            'line-dasharray': [2, 2]
                        }
                    });
                }
            }
        })
        .catch(err => console.error("OSRM Error:", err));
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Function to establish observation WebSockets so other accounts (RESCOM, CDC, RCDG, etc.) see responders' live movement
function observeIncidentTrackers(incidents) {
    incidents.forEach(inc => {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const incidentId = inc.properties ? inc.properties.id : inc.id;
        const socket = new WebSocket(`${wsProtocol}//${window.location.host}/ws/incident/${incidentId}/tracking/`);
        socket.onmessage = function (e) {
            let payload;
            try {
                payload = JSON.parse(e.data);
            } catch (err) {
                return;
            }
            if (payload.type === 'responder_stopped' && payload.data && payload.data.reservist_id) {
                removeResponderMarker(payload.data.reservist_id);
                return;
            }
            // Live location update: move responder marker and route on this map
            const actualData = payload.data ? payload.data : payload;
            if (actualData && actualData.latitude != null && actualData.longitude != null && actualData.reservist_id) {
                updateResponderOnMap(actualData, true);
            }
        };
    });
}

