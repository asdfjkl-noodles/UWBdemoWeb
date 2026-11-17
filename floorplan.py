from flask import Flask, render_template_string, jsonify
import database

app = Flask(__name__)

SVG_MAP_HTML = """
<!DOCTYPE html>
<html>
<head>
	<title>UWB Multi-Floor SVG Map Viewer</title>
	<style>
		body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #181a24; color: #f4f4f9; }
		h1 { color: #00d8ff; margin-bottom: 5px; }
		p { color: #a0a5b8; margin-top: 0; }
		.controls {
			display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
			background: #242736; padding: 15px 20px; border-radius: 8px; margin-bottom: 20px;
			border: 1px solid #32364a;
		}
		select {
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
			background: rgba(0, 216, 255, 0.15); color: #00d8ff; border: 1px solid #00d8ff;
		}
		.legend { display: flex; justify-content: center; gap: 20px; margin-top: 12px; font-size: 13px; }
		.dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 5px; }
	</style>
</head>
<body>
	<div style="background: #242736; padding: 10px 20px; display: flex; gap: 15px; align-items: center; border-bottom: 2px solid #32364a; font-family: Arial, sans-serif;">
        <strong style="color: #00d8ff;">UWB System:</strong>
        <a href="http://127.0.0.1:5002" style="color: #fff; text-decoration: none; padding: 5px 10px; background: #181a24; border-radius: 4px;">🗺️ Floorplan Map (:5002)</a>
        <a href="http://127.0.0.1:5001" style="color: #fff; text-decoration: none; padding: 5px 10px; background: #181a24; border-radius: 4px;">🧊 3D Visualizer (:5001)</a>
        <a href="http://127.0.0.1:5000" style="color: #fff; text-decoration: none; padding: 5px 10px; background: #181a24; border-radius: 4px;">⚙️ Admin Dashboard (:5000)</a>
    </div>

    <h1>Live 3D UWB Position Visualizer</h1>
    <p>Real-time rendering from local SQLite database...</p>
	
	<h1>UWB Multi-Floor SVG Map</h1>
	<p>Live 2D floorplan projection. Add/remove floors, set floor heights, and upload SVGs on port 5000.</p>

	<div class="controls">
		<div>
			<label for="floor-select"><strong>Select View Floor:</strong></label>
			<select id="floor-select" onchange="renderAll()"></select>
		</div>

		<div id="floor-status" style="margin-left: auto; font-size: 14px; color: #00d8ff; font-weight: bold;">
			Loading floors...
		</div>
	</div>

	<div class="layout">
		<div class="map-card">
			<h3 id="map-title" style="margin-top: 0; color: #fff;">Floor 1 Plan</h3>
			<svg id="uwb-svg" viewBox="0 0 600 600">
				<g id="floor-architecture"></g>
				<g id="anchors-layer"></g>
				<g id="tags-layer"></g>
			</svg>
			<div class="legend">
				<span><span class="dot" style="background:#e74c3c;"></span>Hardware Anchor</span>
				<span><span class="dot" style="background:#3498db;"></span>Calculated Position</span>
				<span><span class="dot" style="background:#2ecc71;"></span>True Position</span>
			</div>
		</div>

		<div class="sidebar">
			<h3 style="margin-top: 0; color: #00d8ff;">Live Tag Floor Status</h3>
			<table>
				<thead>
					<tr><th>Tag</th><th>Calc (X, Y)</th><th>Z (m)</th><th>Current Floor</th></tr>
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
		let latestPayload = { anchors: {}, tags: {}, floors: [] };

		async function fetchLiveData() {
			try {
				const res = await fetch('/api/live_data');
				latestPayload = await res.json();
				syncFloorDropdown(latestPayload.floors || []);
				renderAll();
			} catch (err) {
				console.error("Failed to fetch live UWB data:", err);
			}
		}

		function syncFloorDropdown(floors) {
			const select = document.getElementById('floor-select');
			const prevVal = parseInt(select.value, 10) || 1;
			const signature = floors.map(f => `${f.floor_num}:${f.z_min}-${f.z_max}`).join('|');

			if (select.dataset.sig !== signature) {
				select.dataset.sig = signature;
				select.innerHTML = '';
				floors.forEach((f, idx) => {
					const isTop = idx === floors.length - 1;
					const rangeText = isTop
						? `${f.z_min.toFixed(1)}m – ${f.z_max.toFixed(1)}m+`
						: `${f.z_min.toFixed(1)}m – ${f.z_max.toFixed(1)}m`;
					const opt = document.createElement('option');
					opt.value = f.floor_num;
					opt.text = `Floor ${f.floor_num} (${rangeText})`;
					select.appendChild(opt);
				});
				if (floors.some(f => f.floor_num === prevVal)) {
					select.value = prevVal;
				} else if (floors.length > 0) {
					select.value = floors[0].floor_num;
				}
			}
		}

		function getTagFloorNum(z, floors) {
			if (!floors || floors.length === 0) return 1;
			for (let i = 0; i < floors.length; i++) {
				const f = floors[i];
				if (i === floors.length - 1) {
					// Top floor captures everything above its z_min
					if (z >= f.z_min) return f.floor_num;
				} else {
					if (z >= f.z_min && z < f.z_max) return f.floor_num;
				}
			}
			return floors[0].floor_num;
		}

		function getWorkspaceBounds(anchors, customFp) {
			const coords = Object.values(anchors);
			let xs = coords.length ? coords.map(c => c[0]) : [0, 5];
			let ys = coords.length ? coords.map(c => c[1]) : [0, 5];

			if (customFp && customFp.svg_data) {
				xs.push(customFp.min_x, customFp.max_x);
				ys.push(customFp.min_y, customFp.max_y);
			}

			const minX = Math.min(...xs), maxX = Math.max(...xs);
			const minY = Math.min(...ys), maxY = Math.max(...ys);
			return {
				minX,
				maxX: maxX === minX ? minX + 5 : maxX,
				minY,
				maxY: maxY === minY ? minY + 5 : maxY
			};
		}

		function toSvgCoords(x, y, bounds) {
			const pad = 60;
			const usable = 600 - pad * 2;
			const normX = (x - bounds.minX) / (bounds.maxX - bounds.minX);
			const normY = (y - bounds.minY) / (bounds.maxY - bounds.minY);
			return {
				px: pad + normX * usable,
				py: (600 - pad) - normY * usable
			};
		}

		function drawFloorArchitecture(selectedFloor, bounds, floorObj) {
			const archGroup = document.getElementById('floor-architecture');
			let svgContent = '';

			for (let i = 60; i <= 540; i += 96) {
				svgContent += `<line x1="${i}" y1="60" x2="${i}" y2="540" stroke="#1f2333" stroke-width="1" />`;
				svgContent += `<line x1="60" y1="${i}" x2="540" y2="${i}" stroke="#1f2333" stroke-width="1" />`;
			}

			if (floorObj && floorObj.svg_data) {
				const tl = toSvgCoords(floorObj.min_x, floorObj.max_y, bounds);
				const br = toSvgCoords(floorObj.max_x, floorObj.min_y, bounds);
				const x = Math.min(tl.px, br.px);
				const y = Math.min(tl.py, br.py);
				const w = Math.max(10, Math.abs(br.px - tl.px));
				const h = Math.max(10, Math.abs(br.py - tl.py));

				const parser = new DOMParser();
				const doc = parser.parseFromString(floorObj.svg_data, "image/svg+xml");
				const uploadedSvg = doc.querySelector("svg");

				if (uploadedSvg) {
					let vb = uploadedSvg.getAttribute("viewBox");
					if (!vb) {
						const uw = parseFloat(uploadedSvg.getAttribute("width")) || 500;
						const uh = parseFloat(uploadedSvg.getAttribute("height")) || 500;
						vb = `0 0 ${uw} ${uh}`;
					}
					svgContent += `
						<svg x="${x}" y="${y}" width="${w}" height="${h}" viewBox="${vb}" preserveAspectRatio="none" opacity="0.85">
							${uploadedSvg.innerHTML}
						</svg>
					`;
				}
				archGroup.innerHTML = svgContent;
				return;
			}

			svgContent += `<rect x="60" y="60" width="480" height="480" fill="none" stroke="#4a5173" stroke-width="4" />`;
			svgContent += `<text x="300" y="300" fill="#4f577a" font-size="15" text-anchor="middle">FLOOR ${selectedFloor} - NO CUSTOM SVG UPLOADED</text>`;
			archGroup.innerHTML = svgContent;
		}

		function renderAll() {
			const { anchors, tags, floors } = latestPayload;
			if (!floors || floors.length === 0) return;

			const selectedFloor = parseInt(document.getElementById('floor-select').value, 10) || floors[0].floor_num;
			const floorIdx = floors.findIndex(f => f.floor_num === selectedFloor);
			const floorObj = floorIdx >= 0 ? floors[floorIdx] : floors[0];
			const isTop = floorIdx === floors.length - 1;

			const rangeLabel = isTop
				? `Z &ge; ${floorObj.z_min.toFixed(2)} m (Height: ${floorObj.height.toFixed(1)} m)`
				: `${floorObj.z_min.toFixed(2)} m &le; Z &lt; ${floorObj.z_max.toFixed(2)} m (Height: ${floorObj.height.toFixed(1)} m)`;

			document.getElementById('floor-status').innerText = `Viewing: Floor ${floorObj.floor_num} (Height ${floorObj.height.toFixed(1)}m)`;
			document.getElementById('map-title').innerHTML = `Floor ${floorObj.floor_num} Plan (${rangeLabel})`;

			const bounds = getWorkspaceBounds(anchors, floorObj);
			drawFloorArchitecture(floorObj.floor_num, bounds, floorObj);

			const anchorsLayer = document.getElementById('anchors-layer');
			const anchorTable = document.getElementById('anchor-status-body');
			let anchorSvg = '';
			let anchorRows = '';

			for (const [aid, pos] of Object.entries(anchors)) {
				const { px, py } = toSvgCoords(pos[0], pos[1], bounds);
				const opacity = floorObj.floor_num === 1 ? "1.0" : "0.45";
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

			const tagsLayer = document.getElementById('tags-layer');
			const tagTable = document.getElementById('tag-status-body');
			let tagSvg = '';
			let tagRows = '';

			for (const [tid, info] of Object.entries(tags)) {
				const calc = info.calc_pos;
				const tru = info.true_pos;
				const tagFloor = getTagFloorNum(calc[2], floors);

				tagRows += `<tr>
					<td><strong>${tid}</strong></td>
					<td>(${calc[0].toFixed(2)}, ${calc[1].toFixed(2)})</td>
					<td><strong>${calc[2].toFixed(2)}</strong></td>
					<td><span class="floor-badge">Floor ${tagFloor}</span></td>
				</tr>`;

				if (tagFloor === floorObj.floor_num) {
					const cPos = toSvgCoords(calc[0], calc[1], bounds);
					const tPos = toSvgCoords(tru[0], tru[1], bounds);

					tagSvg += `
						<circle cx="${tPos.px}" cy="${tPos.py}" r="5" fill="#2ecc71" opacity="0.8" />
						<line x1="${tPos.px}" y1="${tPos.py}" x2="${cPos.px}" y2="${cPos.py}" stroke="#888" stroke-dasharray="2,2" stroke-width="1" />
						<circle cx="${cPos.px}" cy="${cPos.py}" r="8" fill="#3498db" stroke="#ffffff" stroke-width="2" />
						<text x="${cPos.px}" y="${cPos.py - 12}" fill="#ffffff" font-size="12" font-weight="bold" text-anchor="middle">
							${tid} (${calc[0].toFixed(2)}, ${calc[1].toFixed(2)})
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
		"tags": database.get_latest_positions(),
		"floors": database.get_all_floors()
	})

if __name__ == '__main__':
	database.init_db()
	app.run(debug=True, port=5002)