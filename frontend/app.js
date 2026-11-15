const API = "/api";

let map;
let floorLayer;
let tagMarkers = {};
let anchorMarkers = {};
let trails = {};
let zoneLayers = {};
let zoneData = [];
let tagData = {};
let selectedTagId = null;

const floorBounds = [[0, 0], [1000, 1000]];

// -----------------------------------------------------------------------------
// Utility
// -----------------------------------------------------------------------------

function setConnection(online, text) {
    const dot = document.getElementById("connectionDot");
    const label = document.getElementById("connectionText");

    dot.classList.toggle("online", online);
    dot.classList.toggle("offline", !online);
    label.textContent = text;
}

function formatTime(value) {
    if (!value) return "-";
    return new Date(value).toLocaleTimeString();
}

function xToLeafletY(x) {
    // Leaflet uses [latitude, longitude].
    // We use y as latitude and x as longitude in a 0..10 meter coordinate system.
    return x * 100;
}

function xyToLatLng(x, y) {
    return [yToLeafletY(y), xToLeafletY(x)];
}

function latLngToXY(lat, lng) {
    return {
        x: lng / 100,
        y: lat / 100
    };
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

// -----------------------------------------------------------------------------
// Map
// -----------------------------------------------------------------------------

function initMap() {
    map = L.map("map", {
        crs: L.CRS.Simple,
        minZoom: -2,
        maxZoom: 4,
        zoomControl: true
    });

    // Local indoor floor plan. No public map tiles are used.
    floorLayer = L.imageOverlay(
        "/floorplan/factory-floorplan.svg",
        floorBounds
    ).addTo(map);

    map.fitBounds(floorBounds);

    map.on("click", (event) => {
        const xy = latLngToXY(event.latlng.lat, event.latlng.lng);
        console.log("Clicked floor coordinate:", xy);
    });
}

function makeTagIcon() {
    return L.divIcon({
        className: "",
        html: '<div style="width:18px;height:18px;border-radius:50%;background:#1f6feb;border:3px solid white;box-shadow:0 1px 5px rgba(0,0,0,.45)"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 9]
    });
}

function makeAnchorIcon() {
    return L.divIcon({
        className: "",
        html: '<div style="width:16px;height:16px;background:#17202a;border:2px solid white;box-shadow:0 1px 5px rgba(0,0,0,.35)"></div>',
        iconSize: [16, 16],
        iconAnchor: [8, 8]
    });
}

// -----------------------------------------------------------------------------
// API
// -----------------------------------------------------------------------------

async function apiFetch(path, options = {}) {
    const response = await fetch(API + path, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        },
        ...options
    });

    if (!response.ok) {
        let message = response.statusText;
        try {
            const body = await response.json();
            message = body.detail || message;
        } catch {}
        throw new Error(message);
    }

    return response.json();
}

async function loadHealth() {
    try {
        const health = await apiFetch("/health");
        document.getElementById("backendStatus").textContent = "OK";
        document.getElementById("dbStatus").textContent =
            health.database === "connected" ? "Connected" : "Error";
    } catch (error) {
        document.getElementById("backendStatus").textContent = "Error";
        document.getElementById("dbStatus").textContent = "Error";
    }
}

async function loadAnchors() {
    const anchors = await apiFetch("/anchors");

    for (const anchor of anchors) {
        const marker = L.marker(
            xyToLatLng(anchor.x, anchor.y),
            { icon: makeAnchorIcon() }
        ).addTo(map);

        marker.bindTooltip(
            `${escapeHtml(anchor.name)} (${anchor.anchor_id})`,
            { permanent: true, direction: "top", className: "marker-label" }
        );

        anchorMarkers[anchor.anchor_id] = marker;
    }
}

async function loadZones() {
    zoneData = await apiFetch("/zones");

    for (const zone of zoneData) {
        const southWest = xyToLeafletY(zone.min_y);
        const northEast = xyToLeafletY(zone.max_y);
        const west = xToLeafletY(zone.min_x);
        const east = xToLeafletY(zone.max_x);

        const rectangle = L.rectangle(
            [[southWest, west], [northEast, east]],
            {
                weight: 2,
                fillOpacity: 0.18,
                color: "#e74c3c"
            }
        ).addTo(map);

        rectangle.bindPopup(
            `<strong>${escapeHtml(zone.name)}</strong><br>` +
            `ID: ${escapeHtml(zone.zone_id)}`
        );

        zoneLayers[zone.zone_id] = rectangle;
    }
}

async function loadTags() {
    const tags = await apiFetch("/tags");
    tagData = {};

    for (const tag of tags) {
        tagData[tag.tag_id] = tag;
    }

    renderTagEditor();
}

async function loadLatest() {
    const positions = await apiFetch("/positions/latest");

    for (const position of positions) {
        updatePosition(position);
    }
}

async function loadAlerts() {
    const events = await apiFetch("/geofence-events?limit=20");
    renderAlerts(events);
}

// -----------------------------------------------------------------------------
// Editable database GUI
// -----------------------------------------------------------------------------

function renderTagEditor() {
    const container = document.getElementById("tagEditor");
    container.innerHTML = "";

    for (const tag of Object.values(tagData)) {
        const wrapper = document.createElement("div");
        wrapper.className = "tag-editor";

        wrapper.innerHTML = `
            <strong>${escapeHtml(tag.tag_id)}</strong>

            <label>Name</label>
            <input id="name-${escapeHtml(tag.tag_id)}"
                   value="${escapeHtml(tag.name)}">

            <label>Type</label>
            <select id="type-${escapeHtml(tag.tag_id)}">
                <option value="person">person</option>
                <option value="vehicle">vehicle</option>
                <option value="asset">asset</option>
            </select>

            <label>Status</label>
            <select id="status-${escapeHtml(tag.tag_id)}">
                <option value="active">active</option>
                <option value="inactive">inactive</option>
            </select>

            <button class="small-button" data-save="${escapeHtml(tag.tag_id)}">
                Save
            </button>
        `;

        container.appendChild(wrapper);

        document.getElementById(`type-${tag.tag_id}`).value = tag.tag_type;
        document.getElementById(`status-${tag.tag_id}`).value = tag.status;
    }

    container.querySelectorAll("[data-save]").forEach(button => {
        button.addEventListener("click", () => saveTag(button.dataset.save));
    });
}

async function saveTag(tagId) {
    const payload = {
        tag_id: tagId,
        name: document.getElementById(`name-${tagId}`).value,
        tag_type: document.getElementById(`type-${tagId}`).value,
        status: document.getElementById(`status-${tagId}`).value
    };

    try {
        await apiFetch(`/tags/${encodeURIComponent(tagId)}`, {
            method: "PUT",
            body: JSON.stringify(payload)
        });

        await loadTags();
        alert(`Saved ${tagId} to PostgreSQL.`);
    } catch (error) {
        alert("Save failed: " + error.message);
    }
}

async function addTag() {
    const tagId = prompt("New tag ID, e.g. TAG004");
    if (!tagId) return;

    const name = prompt("Tag name", "New Tag");
    if (!name) return;

    try {
        await apiFetch("/tags", {
            method: "POST",
            body: JSON.stringify({
                tag_id: tagId,
                name: name,
                tag_type: "person",
                status: "active"
            })
        });

        await loadTags();
    } catch (error) {
        alert("Could not create tag: " + error.message);
    }
}

// -----------------------------------------------------------------------------
// Live position + Leaflet
// -----------------------------------------------------------------------------

function updatePosition(position) {
    const latLng = xyToLatLng(position.x, position.y);

    if (!tagMarkers[position.tag_id]) {
        const marker = L.marker(latLng, {
            icon: makeTagIcon()
        }).addTo(map);

        marker.bindTooltip(
            escapeHtml(position.name || position.tag_id),
            { direction: "top", offset: [0, -10] }
        );

        marker.on("click", () => {
            selectedTagId = position.tag_id;
            showHistory(position.tag_id);
        });

        tagMarkers[position.tag_id] = marker;

        const trail = L.polyline([], {
            weight: 3,
            opacity: 0.55
        }).addTo(map);

        trails[position.tag_id] = trail;
    } else {
        tagMarkers[position.tag_id].setLatLng(latLng);
        tagMarkers[position.tag_id].setTooltipContent(
            escapeHtml(position.name || position.tag_id)
        );
    }

    trails[position.tag_id].addLatLng(latLng);

    // Keep the trail at a reasonable size in this demo.
    const latLngs = trails[position.tag_id].getLatLngs();
    if (latLngs.length > 150) {
        trails[position.tag_id].setLatLngs(latLngs.slice(-150));
    }

    renderPositionRow(position);

    document.getElementById("lastUpdate").textContent =
        `${position.tag_id} @ ${formatTime(position.timestamp)}`;

    // Client-side Turf geofence check.
    runTurfCheck(position);
}

function renderPositionRow(position) {
    const table = document.getElementById("positionsTable");
    let row = document.getElementById(`row-${position.tag_id}`);

    if (!row) {
        row = document.createElement("tr");
        row.id = `row-${position.tag_id}`;
        table.appendChild(row);
    }

    row.innerHTML = `
        <td><strong>${escapeHtml(position.name || position.tag_id)}</strong></td>
        <td>${Number(position.x).toFixed(2)}</td>
        <td>${Number(position.y).toFixed(2)}</td>
        <td>${position.accuracy == null ? "-" : Number(position.accuracy).toFixed(2) + " m"}</td>
        <td>${escapeHtml(position.source || "-")}</td>
        <td>${formatTime(position.timestamp)}</td>
    `;
}

// -----------------------------------------------------------------------------
// Turf.js
// -----------------------------------------------------------------------------

function zoneToTurfPolygon(zone) {
    return turf.polygon([[
        [zone.min_x, zone.min_y],
        [zone.max_x, zone.min_y],
        [zone.max_x, zone.max_y],
        [zone.min_x, zone.max_y],
        [zone.min_x, zone.min_y]
    ]]);
}

function runTurfCheck(position) {
    const point = turf.point([position.x, position.y]);

    for (const zone of zoneData) {
        const polygon = zoneToTurfPolygon(zone);
        const inside = turf.booleanPointInPolygon(point, polygon);

        const layer = zoneLayers[zone.zone_id];
        if (layer) {
            layer.setStyle({
                weight: inside ? 4 : 2,
                fillOpacity: inside ? 0.30 : 0.18
            });
        }
    }
}

// -----------------------------------------------------------------------------
// History
// -----------------------------------------------------------------------------

async function showHistory(tagId) {
    selectedTagId = tagId;

    try {
        const history = await apiFetch(
            `/positions/history/${encodeURIComponent(tagId)}?limit=100`
        );

        const points = history.map(item => xyToLatLng(item.x, item.y));

        if (trails[tagId]) {
            trails[tagId].setLatLngs(points);
        }

        const latest = history[history.length - 1];

        document.getElementById("selectedTagInfo").innerHTML = `
            <strong>${escapeHtml(tagId)}</strong><br>
            Samples: ${history.length}<br>
            Last X: ${latest ? Number(latest.x).toFixed(2) : "-"} m<br>
            Last Y: ${latest ? Number(latest.y).toFixed(2) : "-"} m<br>
            Last accuracy:
            ${latest && latest.accuracy != null
                ? Number(latest.accuracy).toFixed(2) + " m"
                : "-"}
        `;
    } catch (error) {
        document.getElementById("selectedTagInfo").textContent =
            "Could not load history: " + error.message;
    }
}

// -----------------------------------------------------------------------------
// Alerts
// -----------------------------------------------------------------------------

function renderAlerts(events) {
    const container = document.getElementById("alerts");

    if (!events.length) {
        container.innerHTML = "<div class='alert'>No geofence events yet.</div>";
        return;
    }

    container.innerHTML = events.map(event => `
        <div class="alert ${event.event.toLowerCase()}">
            <strong>${escapeHtml(event.event)}</strong>
            — ${escapeHtml(event.tag_name)}
            → ${escapeHtml(event.zone_name)}
            <br>
            <small>${formatTime(event.timestamp)}</small>
        </div>
    `).join("");
}

function addLiveAlerts(events) {
    if (!events || !events.length) return;

    loadAlerts();
}

// -----------------------------------------------------------------------------
// WebSocket
// -----------------------------------------------------------------------------

function connectWebSocket() {
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${location.host}/ws/live`);

    ws.onopen = () => {
        document.getElementById("liveStatus").textContent = "Connected";
        setConnection(true, "Live connected");

        // Server expects text frames to keep the socket alive.
        window.wsHeartbeat = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send("ping");
            }
        }, 20000);
    };

    ws.onmessage = event => {
        const payload = JSON.parse(event.data);

        if (payload.type === "position") {
            const position = payload.position;

            // Add the tag name if it is known locally.
            if (tagData[position.tag_id]) {
                position.name = tagData[position.tag_id].name;
            }

            updatePosition(position);
            addLiveAlerts(payload.events);
        }
    };

    ws.onclose = () => {
        document.getElementById("liveStatus").textContent = "Disconnected";
        setConnection(false, "Reconnecting...");
        clearInterval(window.wsHeartbeat);

        setTimeout(connectWebSocket, 1500);
    };

    ws.onerror = () => {
        ws.close();
    };
}

// -----------------------------------------------------------------------------
// Startup
// -----------------------------------------------------------------------------

async function start() {
    initMap();

    try {
        await loadHealth();
        await loadTags();
        await loadAnchors();
        await loadZones();
        await loadLatest();
        await loadAlerts();
    } catch (error) {
        console.error(error);
    }

    connectWebSocket();

    document.getElementById("refreshBtn").addEventListener("click", async () => {
        await loadTags();
        await loadLatest();
        await loadAlerts();
    });

    document.getElementById("addTagBtn").addEventListener("click", addTag);
}

start();
