from flask import Flask, render_template_string, jsonify
import database

app = Flask(__name__)

SVG_MAP_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>UWB 2-Floor SVG Map Viewer</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #181a24; color: #f4f4f9; }
        h1 { color: #00d8ff; margin-bottom: 5px; }
        p { color: #a0a5b8; margin-top: 0; }
        .controls {
            display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
            background: #242736; padding: 15px 20px; border-radius: 8px; margin-bottom: 20px;
            border: 1px solid #32364a;
        }
        select, input[type="number"] {
            padding: 8px 12px; border-radius: 5px; border: 1px solid #454a66;
            background: #181a24; color: #fff; font-size: 14px; font-weight: bold;
        }
        .layout { display: flex; gap: 20px; flex-wrap: wrap; }
        .map-card {
            flex: 2; min-width: 550px; background: #242736; padding: 20px;
            border-radius: 8px; border: 1px solid #32364a; text-align: center;
        }
        .sidebar {
            flex: 1; min-width: 320px; background: #242736; padding: 20px;
            border-radius: 8px; border: 1px solid #32364a;
        }
        svg {
            width: 100%; max-width: 650px; height: auto;
            background: #12141c; border: 2px solid #3c425c; border-radius: 6px;
        }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { padding: 8px; border: 1px solid #32364a; text-align: center; }
        th { background-color: #2f3346; color: #00d8ff; }
        .floor-badge {
            padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;
        }
        .f1-badge { background: rgba(46, 204, 113, 0.2); color: #2ecc71; border: 1px solid #2ecc71; }
        .f2-badge { background: rgba(155, 89, 182, 0.2); color: #bb6bd9; border: 1px solid #bb6bd9; }
        .legend { display: flex; justify-content: center; gap: 20px; margin-top: 12px; font-size: 13px; }
        .dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 5px; }
    </style>
</head>
<body>
    <h1>UWB Multi-Floor SVG Map</h1>
    <p>Live 2D floorplan projection from SQLite database. Tags automatically transition floors based on Z elevation.</p>

    <!-- Top Control Bar -->
    <div class="controls">
        <div>
            <label for="floor-select"><strong>Select View Floor:</strong></label>
            <select id="floor-select" onchange="renderAll()">
                <option value="1">Floor 1 (Ground Level)</option>
                <option value="2">Floor 2 (Upper Level)</option>
            </select>
        </div>

        <div>
            <label for="z-threshold"><strong>Floor 2 Threshold Z (m):</strong></label>
            <input type="number" id="z-threshold" value="2.0" step="0.1" min="0" max="10" style="width: 75px;" onchange="renderAll()">
        </div>

        <div id="floor-status" style="margin-left: auto; font-size: 14px; color: #00d8ff; font-weight: bold;">
            Viewing: Floor 1
        </div>
    </div>

    <div class="layout">
        <!-- SVG Floorplan Container -->
        <div class="map-card">
            <h3 id="map-title" style="margin-top: 0; color: #fff;">Floor 1 Plan (Z &le; 2.00 m)</h3>
            
            <svg id="uwb-svg" viewBox="0 0 600 600">
                <!-- Background Grid & Architectural Layout Layer -->
                <g id="floor-architecture"></g>
                <!-- Physical Anchors Layer -->
                <g id="anchors-layer"></g>
                <!-- Active Tags on Selected Floor Layer -->
                <g id="tags-layer"></g>
            </svg>

            <div class="legend">
                <span><span class="dot" style="background:#e74c3c;"></span>Hardware Anchor (Base Layer)</span>
                <span><span class="dot" style="background:#3498db;"></span>Calculated Position</span>
                <span><span class="dot" style="background:#2ecc71;"></span>True Position</span>
            </div>
        </div>

        <!-- Live Tag Status & Floor Assignment Table -->
        <div class="sidebar">
            <h3 style="margin-top: 0; color: #00d8ff;">Live Tag Floor Status</h3>
            <table>
                <thead>
                    <tr>
                        <th>Tag</th>
                        <th>Calc (X, Y)</th>
                        <th>Z (m)</th>
                        <th>Current Floor</th>
                    </tr>
                </thead>
                <tbody id="tag-status-body"></tbody>
            </table>

            <h3 style="margin-top: 25px; color: #00d8ff;">Anchor Reference (Base Layer)</h3>
            <table>
                <thead>
                    <tr><th>ID</th><th>X (m)</th><th>Y (m)</th><th>Z (m)</th></tr>
                </thead>
                <tbody id="anchor-status-body"></tbody>
            </table>
        </div>
    </div>

    <script>
        let latestPayload = { anchors: {}, tags: {} };

        async function fetchLiveData() {
            try {
                const res = await fetch('/api/live_data');
                latestPayload = await res.json();
                renderAll();
            } catch (err) {
                console.error("Failed to fetch live UWB data:", err);
            }
        }

        function getWorkspaceBounds(anchors) {
            const coords = Object.values(anchors);
            if (coords.length === 0) return { minX: 0, maxX: 5, minY: 0, maxY: 5 };
            const xs = coords.map(c => c[0]);
            const ys = coords.map(c => c[1]);
            const minX = Math.min(...xs);
            const maxX = Math.max(...xs);
            const minY = Math.min(...ys);
            const maxY = Math.max(...ys);
            return {
                minX,
                maxX: maxX === minX ? minX + 5 : maxX,
                minY,
                maxY: maxY === minY ? minY + 5 : maxY
            };
        }

        // Convert physical (X, Y) meters to SVG pixel coordinates (with 60px margin)
        function toSvgCoords(x, y, bounds) {
            const pad = 60;
            const usable = 600 - pad * 2;
            const normX = (x - bounds.minX) / (bounds.maxX - bounds.minX);
            const normY = (y - bounds.minY) / (bounds.maxY - bounds.minY);
            return {
                px: pad + normX * usable,
                py: (600 - pad) - normY * usable // Invert Y so +Y goes up on map
            };
        }

        function drawFloorArchitecture(selectedFloor, thresholdZ) {
            const archGroup = document.getElementById('floor-architecture');
            let svgContent = '';

            // Subtle coordinate grid lines
            for (let i = 60; i <= 540; i += 96) {
                svgContent += `<line x1="${i}" y1="60" x2="${i}" y2="540" stroke="#1f2333" stroke-width="1" />`;
                svgContent += `<line x1="60" y1="${i}" x2="540" y2="${i}" stroke="#1f2333" stroke-width="1" />`;
            }

            // Outer Building Perimeter
            svgContent += `<rect x="60" y="60" width="480" height="480" fill="none" stroke="#4a5173" stroke-width="4" />`;

            if (selectedFloor === 1) {
                // Floor 1 Layout: Lobby, Storage, Main Hall
                svgContent += `
                    <rect x="60" y="60" width="220" height="200" fill="rgba(46, 204, 113, 0.04)" stroke="#383e59" stroke-width="2" />
                    <text x="170" y="160" fill="#4f577a" font-size="14" text-anchor="middle">FLOOR 1 - ZONE A</text>
                    <rect x="280" y="60" width="260" height="200" fill="rgba(52, 152, 219, 0.04)" stroke="#383e59" stroke-width="2" />
                    <text x="410" y="160" fill="#4f577a" font-size="14" text-anchor="middle">FLOOR 1 - LOBBY</text>
                    <text x="300" y="420" fill="#4f577a" font-size="16" text-anchor="middle">GROUND FLOOR OPEN WORKSPACE</text>
                    <text x="300" y="38" fill="#2ecc71" font-size="14" font-weight="bold" text-anchor="middle">ACTIVE VIEW: FLOOR 1 (Z &le; ${thresholdZ.toFixed(1)}m)</text>
                `;
            } else {
                // Floor 2 Layout: Mezzanine, Control Room, Balcony
                svgContent += `
                    <rect x="60" y="320" width="480" height="220" fill="rgba(155, 89, 182, 0.06)" stroke="#4e3d63" stroke-width="2" stroke-dasharray="8,4" />
                    <text x="300" y="430" fill="#7c5fa1" font-size="15" text-anchor="middle">FLOOR 2 - UPPER MEZZANINE DECK</text>
                    <rect x="140" y="100" width="320" height="160" fill="rgba(155, 89, 182, 0.04)" stroke="#4e3d63" stroke-width="2" />
                    <text x="300" y="185" fill="#7c5fa1" font-size="14" text-anchor="middle">UPPER OBSERVATION GALLERY</text>
                    <text x="300" y="38" fill="#bb6bd9" font-size="14" font-weight="bold" text-anchor="middle">ACTIVE VIEW: FLOOR 2 (Z &gt; ${thresholdZ.toFixed(1)}m)</text>
                `;
            }

            archGroup.innerHTML = svgContent;
        }

        function renderAll() {
            const selectedFloor = parseInt(document.getElementById('floor-select').value, 10);
            const thresholdZ = parseFloat(document.getElementById('z-threshold').value) || 2.0;

            document.getElementById('floor-status').innerText = `Viewing: Floor ${selectedFloor}`;
            document.getElementById('map-title').innerHTML = selectedFloor === 1
                ? `Floor 1 Plan (Z &le; ${thresholdZ.toFixed(2)} m)`
                : `Floor 2 Plan (Z &gt; ${thresholdZ.toFixed(2)} m)`;

            const { anchors, tags } = latestPayload;
            const bounds = getWorkspaceBounds(anchors);

            drawFloorArchitecture(selectedFloor, thresholdZ);

            // 1. Render Anchors on SVG & Sidebar
            const anchorsLayer = document.getElementById('anchors-layer');
            const anchorTable = document.getElementById('anchor-status-body');
            let anchorSvg = '';
            let anchorRows = '';

            for (const [aid, pos] of Object.entries(anchors)) {
                const { px, py } = toSvgCoords(pos[0], pos[1], bounds);
                const opacity = selectedFloor === 1 ? "1.0" : "0.45"; // Dim base anchors when viewing Floor 2
                anchorSvg += `
                    <g opacity="${opacity}">
                        <polygon points="${px},${py-9} ${px-8},${py+7} ${px+8},${py+7}" fill="#e74c3c" stroke="#fff" stroke-width="1.5" />
                        <text x="${px}" y="${py-13}" fill="#ff7675" font-size="12" font-weight="bold" text-anchor="middle">${aid}</text>
                    </g>
                `;
                anchorRows += `<tr>
                    <td style="color:#e74c3c; font-weight:bold;">${aid}</td>
                    <td>${pos[0].toFixed(2)}</td>
                    <td>${pos[1].toFixed(2)}</td>
                    <td>${pos[2].toFixed(2)}</td>
                </tr>`;
            }
            anchorsLayer.innerHTML = anchorSvg;
            anchorTable.innerHTML = anchorRows;

            // 2. Render Tags on SVG (filtered by floor) & Sidebar (all tags)
            const tagsLayer = document.getElementById('tags-layer');
            const tagTable = document.getElementById('tag-status-body');
            let tagSvg = '';
            let tagRows = '';

            for (const [tid, info] of Object.entries(tags)) {
                const calc = info.calc_pos;
                const tru = info.true_pos;
                const tagFloor = calc[2] > thresholdZ ? 2 : 1;

                const badgeClass = tagFloor === 1 ? 'f1-badge' : 'f2-badge';
                tagRows += `<tr>
                    <td><strong>${tid}</strong></td>
                    <td>(${calc[0].toFixed(2)}, ${calc[1].toFixed(2)})</td>
                    <td><strong>${calc[2].toFixed(2)}</strong></td>
                    <td><span class="floor-badge ${badgeClass}">Floor ${tagFloor}</span></td>
                </tr>`;

                // Only draw on the SVG map if the tag is currently on the selected floor
                if (tagFloor === selectedFloor) {
                    const cPos = toSvgCoords(calc[0], calc[1], bounds);
                    const tPos = toSvgCoords(tru[0], tru[1], bounds);

                    tagSvg += `
                        <!-- True Position Marker -->
                        <circle cx="${tPos.px}" cy="${tPos.py}" r="5" fill="#2ecc71" opacity="0.8" />
                        <!-- Error Line between True & Calculated -->
                        <line x1="${tPos.px}" y1="${tPos.py}" x2="${cPos.px}" y2="${cPos.py}" stroke="#888" stroke-dasharray="2,2" stroke-width="1" />
                        <!-- Calculated Position Marker -->
                        <circle cx="${cPos.px}" cy="${cPos.py}" r="8" fill="#3498db" stroke="#ffffff" stroke-width="2" />
                        <text x="${cPos.px}" y="${cPos.py - 12}" fill="#ffffff" font-size="12" font-weight="bold" text-anchor="middle">
                            ${tid} (z:${calc[2].toFixed(1)}m)
                        </text>
                    `;
                }
            }
            tagsLayer.innerHTML = tagSvg;
            tagTable.innerHTML = tagRows;
        }

        setInterval(fetchLiveData, 400);
        fetchLiveData();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(SVG_MAP_HTML)

@app.route('/api/live_data')
def live_data():
    return jsonify({
        "anchors": database.get_anchors(),
        "tags": database.get_latest_positions()
    })

if __name__ == '__main__':
    database.init_db()
    app.run(debug=True, port=5002)