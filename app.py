from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import database

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
	<title>UWB Dropdown Control Dashboard</title>
	<style>
		body { font-family: Arial, sans-serif; margin: 20px; background: #f4f4f9; color: #333; }
		h1, h2, h3 { color: #2c3e50; }
		table { width: 100%; border-collapse: collapse; background: #fff; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
		th, td { padding: 10px; border: 1px solid #ddd; text-align: center; }
		th { background-color: #34495e; color: white; }
		select, input[type="text"], input[type="number"], input[type="file"] { padding: 6px; margin: 2px; border: 1px solid #ccc; border-radius: 4px; }
		button { background: #3498db; color: white; border: none; padding: 7px 14px; cursor: pointer; border-radius: 4px; font-weight: bold; }
		button:hover { background: #2980b9; }
		button.secondary { background: #7f8c8d; }
		button.secondary:hover { background: #636e72; }
		button.delete { background: #e74c3c; }
		button.delete:hover { background: #c0392b; }
		.container { display: flex; gap: 20px; flex-wrap: wrap; }
		.pane { flex: 1; min-width: 350px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
		.section { margin-bottom: 20px; padding: 12px; background: #fafafa; border: 1px solid #eee; border-radius: 6px; }
		.hint { font-size: 11px; color: #666; margin-bottom: 8px; display: block; }

		/* Floorplan X/Y Interactive Editor */
		.fp-workspace { display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-start; margin-top: 15px; }
		.fp-canvas-box { flex: 1.5; min-width: 420px; text-align: center; background: #181a24; padding: 15px; border-radius: 8px; }
		.fp-controls-box { flex: 1; min-width: 260px; background: #fafafa; padding: 15px; border: 1px solid #ddd; border-radius: 8px; }
		svg#xy-editor-svg {
			width: 100%; max-width: 500px; height: auto;
			background: #12141c; border: 2px solid #34495e; border-radius: 6px;
			user-select: none;
		}
		.edge-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 12px 0; }
		.edge-grid label { display: block; font-size: 12px; font-weight: bold; color: #555; }
		.edge-grid input { width: 85%; }
		.edge-handle { fill: #00d8ff; stroke: #12141c; stroke-width: 1.5; }
		.edge-handle:hover { fill: #f1c40f; }
		.move-handle { fill: rgba(0, 216, 255, 0.12); stroke: #00d8ff; stroke-dasharray: 4,4; cursor: move; }
	</style>
</head>
<body>
	<h1>UWB Control & Floorplan Management Dashboard</h1>
	
	<div class="container">
		<!-- ANCHORS MANAGEMENT -->
		<div class="pane">
			<h2>Anchor Management</h2>
			
			<div class="section">
				<h3>Edit / Rename / Move Existing Anchor</h3>
				<span class="hint">Leave boxes blank to keep their current values. Only fill what you want to change.</span>
				<form action="/modify_anchor" method="POST">
					<label>Select Anchor:</label><br>
					<select name="old_id" required>
						{% for aid in anchors.keys() %}
						<option value="{{ aid }}">{{ aid }}</option>
						{% endfor %}
					</select><br><br>
					<label>New Name ID (optional):</label><br>
					<input type="text" name="new_id" placeholder="Leave blank to keep same"><br>
					<label>X, Y, Z Coordinates (optional):</label><br>
					<input type="text" name="x" placeholder="X" size="5">
					<input type="text" name="y" placeholder="Y" size="5">
					<input type="text" name="z" placeholder="Z" size="5"><br><br>
					<button type="submit">Save Changes</button>
					<button type="submit" name="action" value="delete" class="delete" onclick="return confirm('Are you sure you want to delete this anchor?');">Delete Anchor</button>
				</form>
			</div>

			<div class="section">
				<h3>Add New Anchor</h3>
				<form action="/add_anchor" method="POST">
					<input type="text" name="aid" placeholder="ID (e.g. A4)" size="6" required>
					<input type="text" name="x" placeholder="X" size="5" required>
					<input type="text" name="y" placeholder="Y" size="5" required>
					<input type="text" name="z" placeholder="Z" size="5" required>
					<button type="submit">Add</button>
				</form>
			</div>
		</div>

		<!-- TAGS MANAGEMENT -->
		<div class="pane">
			<h2>Tag Management</h2>
			
			<div class="section">
				<h3>Edit / Rename Existing Tag</h3>
				<span class="hint">Leave boxes blank to keep their current values. Only fill what you want to change.</span>
				<form action="/modify_tag" method="POST">
					<label>Select Tag:</label><br>
					<select name="old_id" required>
						{% for tid in tags.keys() %}
						<option value="{{ tid }}">{{ tid }}</option>
						{% endfor %}
					</select><br><br>
					<label>New Name ID (optional):</label><br>
					<input type="text" name="new_id" placeholder="Leave blank to keep same"><br>
					<label>Tilt (°), Radius (optional):</label><br>
					<input type="text" name="tilt" placeholder="Tilt" size="5">
					<input type="text" name="radius" placeholder="Radius" size="5"><br>
					<label>Center (X, Y, Z) (optional):</label><br>
					<input type="text" name="cx" placeholder="X" size="4">
					<input type="text" name="cy" placeholder="Y" size="4">
					<input type="text" name="cz" placeholder="Z" size="4"><br><br>
					<button type="submit">Save Changes</button>
					<button type="submit" name="action" value="delete" class="delete" onclick="return confirm('Are you sure you want to delete this tag?');">Delete Tag</button>
				</form>
			</div>

			<div class="section">
				<h3>Add New Tag</h3>
				<form action="/add_tag" method="POST">
					<input type="text" name="tid" placeholder="ID (T5)" size="5" required>
					<input type="text" name="tilt" placeholder="Tilt" size="4" required>
					<input type="text" name="radius" placeholder="Rad" size="4" required><br>
					Center: <input type="text" name="cx" placeholder="X" size="3" required>
					<input type="text" name="cy" placeholder="Y" size="3" required>
					<input type="text" name="cz" placeholder="Z" size="3" required>
					<button type="submit">Add</button>
				</form>
			</div>
		</div>
	</div>

	<!-- SVG FLOORPLAN CALIBRATOR -->
	<div class="pane" style="margin-top: 20px; max-width: 100%;">
		<h2>SVG Floorplan Upload & X/Y Plane Calibration</h2>
		<p style="color: #666; margin-top: -10px;">Upload an .svg file to pop it onto the X/Y anchor plane. Drag any side handle or edit an edge coordinate below.</p>
		
		<div style="display: flex; gap: 15px; align-items: center; flex-wrap: wrap;">
			<div>
				<label><strong>Target Floor:</strong></label>
				<select id="fp-floor-select" onchange="loadFloorplan()">
					<option value="1">Floor 1 (Ground)</option>
					<option value="2">Floor 2 (Upper)</option>
				</select>
			</div>
			<div>
				<label><strong>Upload .SVG File:</strong></label>
				<input type="file" id="fp-svg-input" accept=".svg" onchange="handleSvgUpload(event)">
			</div>
			<span id="fp-status-msg" style="color: #27ae60; font-weight: bold; font-size: 13px;"></span>
		</div>

		<!-- Interactive X/Y Plane Pop-Up Area -->
		<div class="fp-workspace" id="fp-editor-workspace" style="display: none;">
			<div class="fp-canvas-box">
				<div style="color: #00d8ff; font-size: 13px; font-weight: bold; margin-bottom: 8px;">
					X/Y Coordinate Plane (Drag Cyan Edge Handles or Center Box)
				</div>
				<svg id="xy-editor-svg" viewBox="0 0 500 500">
					<g id="ed-grid-layer"></g>
					<g id="ed-svg-layer"></g>
					<g id="ed-anchors-layer"></g>
					<g id="ed-handles-layer"></g>
				</svg>
			</div>

			<div class="fp-controls-box">
				<h3 style="margin-top: 0;">Edit Edge Positions (Meters)</h3>
				<div class="edge-grid">
					<div>
						<label>Left Edge (Min X)</label>
						<input type="number" id="ed-min-x" step="0.1" oninput="onEdgeInput()">
					</div>
					<div>
						<label>Right Edge (Max X)</label>
						<input type="number" id="ed-max-x" step="0.1" oninput="onEdgeInput()">
					</div>
					<div>
						<label>Bottom Edge (Min Y)</label>
						<input type="number" id="ed-min-y" step="0.1" oninput="onEdgeInput()">
					</div>
					<div>
						<label>Top Edge (Max Y)</label>
						<input type="number" id="ed-max-y" step="0.1" oninput="onEdgeInput()">
					</div>
				</div>

				<div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 15px;">
					<button type="button" onclick="saveFloorplan()">Save to Database</button>
					<button type="button" class="secondary" onclick="snapToAnchors()">Snap to Anchors</button>
					<button type="button" class="delete" onclick="if(confirm('Remove SVG floorplan for this floor?')) deleteFloorplan()">Remove SVG</button>
				</div>
			</div>
		</div>
	</div>

	<!-- LIVE MOVEMENT LOGS -->
	<div class="pane" style="margin-top: 20px; max-width: 100%;">
		<h2>Live Movement Logs</h2>
		<table>
			<tr><th>Step</th><th>Tag</th><th>True Pos (X, Y, Z)</th><th>Calculated Pos (X, Y, Z)</th><th>Distances</th></tr>
			{% for row in logs %}
			<tr>
				<td>{{ row[0] }}</td>
				<td><strong>{{ row[1] }}</strong></td>
				<td>[{{ "%.2f"|format(row[2]) }}, {{ "%.2f"|format(row[3]) }}, {{ "%.2f"|format(row[4]) }}]</td>
				<td>[{{ "%.2f"|format(row[5]) }}, {{ "%.2f"|format(row[6]) }}, {{ "%.2f"|format(row[7]) }}]</td>
				<td style="font-size: 11px;">{{ row[8] }}</td>
			</tr>
			{% endfor %}
		</table>
	</div>

	<script>
		const dbAnchors = {{ anchors | tojson }};
		let currentFp = null;
		let dragState = null;

		function getAnchorBounds() {
			const coords = Object.values(dbAnchors);
			if (coords.length === 0) return { minX: 0, maxX: 5, minY: 0, maxY: 5 };
			const xs = coords.map(c => c[0]);
			const ys = coords.map(c => c[1]);
			const minX = Math.min(...xs), maxX = Math.max(...xs);
			const minY = Math.min(...ys), maxY = Math.max(...ys);
			return {
				minX,
				maxX: maxX === minX ? minX + 5 : maxX,
				minY,
				maxY: maxY === minY ? minY + 5 : maxY
			};
		}

		function getPlaneBounds() {
			const base = getAnchorBounds();
			let xs = [base.minX, base.maxX];
			let ys = [base.minY, base.maxY];
			if (currentFp) {
				xs.push(currentFp.min_x, currentFp.max_x);
				ys.push(currentFp.min_y, currentFp.max_y);
			}
			const minX = Math.min(...xs), maxX = Math.max(...xs);
			const minY = Math.min(...ys), maxY = Math.max(...ys);
			// Add 10% padding around bounds so edges are easy to grab
			const padX = (maxX - minX) * 0.1 || 0.5;
			const padY = (maxY - minY) * 0.1 || 0.5;
			return {
				minX: minX - padX,
				maxX: maxX + padX,
				minY: minY - padY,
				maxY: maxY + padY
			};
		}

		function toSvgPx(x, y, bounds) {
			const pad = 45;
			const usable = 500 - pad * 2;
			const nx = (x - bounds.minX) / (bounds.maxX - bounds.minX);
			const ny = (y - bounds.minY) / (bounds.maxY - bounds.minY);
			return {
				px: pad + nx * usable,
				py: (500 - pad) - ny * usable
			};
		}

		function fromSvgPx(px, py, bounds) {
			const pad = 45;
			const usable = 500 - pad * 2;
			const nx = (px - pad) / usable;
			const ny = ((500 - pad) - py) / usable;
			return {
				x: bounds.minX + nx * (bounds.maxX - bounds.minX),
				y: bounds.minY + ny * (bounds.maxY - bounds.minY)
			};
		}

		async function loadFloorplan() {
			const floor = document.getElementById('fp-floor-select').value;
			const res = await fetch(`/api/floorplan/${floor}`);
			const data = await res.json();
			currentFp = data.floorplan;
			document.getElementById('fp-editor-workspace').style.display = currentFp ? 'flex' : 'none';
			if (currentFp) {
				syncInputs();
				renderEditor();
			}
		}

		function handleSvgUpload(evt) {
			const file = evt.target.files[0];
			if (!file) return;
			const reader = new FileReader();
			reader.onload = async function(e) {
				const aBounds = getAnchorBounds();
				currentFp = {
					svg_data: e.target.result,
					min_x: aBounds.minX,
					max_x: aBounds.maxX,
					min_y: aBounds.minY,
					max_y: aBounds.maxY
				};
				document.getElementById('fp-editor-workspace').style.display = 'flex';
				syncInputs();
				renderEditor();
				await saveFloorplan();
			};
			reader.readAsText(file);
			evt.target.value = '';
		}

		function syncInputs() {
			if (!currentFp) return;
			document.getElementById('ed-min-x').value = currentFp.min_x.toFixed(2);
			document.getElementById('ed-max-x').value = currentFp.max_x.toFixed(2);
			document.getElementById('ed-min-y').value = currentFp.min_y.toFixed(2);
			document.getElementById('ed-max-y').value = currentFp.max_y.toFixed(2);
		}

		function onEdgeInput() {
			if (!currentFp) return;
			const minX = parseFloat(document.getElementById('ed-min-x').value);
			const maxX = parseFloat(document.getElementById('ed-max-x').value);
			const minY = parseFloat(document.getElementById('ed-min-y').value);
			const maxY = parseFloat(document.getElementById('ed-max-y').value);
			if (!isNaN(minX)) currentFp.min_x = minX;
			if (!isNaN(maxX)) currentFp.max_x = maxX;
			if (!isNaN(minY)) currentFp.min_y = minY;
			if (!isNaN(maxY)) currentFp.max_y = maxY;
			renderEditor();
		}

		function snapToAnchors() {
			if (!currentFp) return;
			const aBounds = getAnchorBounds();
			currentFp.min_x = aBounds.minX;
			currentFp.max_x = aBounds.maxX;
			currentFp.min_y = aBounds.minY;
			currentFp.max_y = aBounds.maxY;
			syncInputs();
			renderEditor();
		}

		async function saveFloorplan() {
			if (!currentFp) return;
			const floor = document.getElementById('fp-floor-select').value;
			await fetch(`/api/floorplan/${floor}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(currentFp)
			});
			const msg = document.getElementById('fp-status-msg');
			msg.innerText = `Saved Floor ${floor} layout!`;
			setTimeout(() => msg.innerText = '', 2500);
		}

		async function deleteFloorplan() {
			const floor = document.getElementById('fp-floor-select').value;
			await fetch(`/api/floorplan/${floor}`, { method: 'DELETE' });
			currentFp = null;
			document.getElementById('fp-editor-workspace').style.display = 'none';
		}

		function renderEditor() {
			if (!currentFp) return;
			const bounds = getPlaneBounds();

			// 1. Draw X/Y Grid
			let gridHtml = '';
			for (let i = 0; i <= 5; i++) {
				const pos = 45 + i * 82;
				const xv = bounds.minX + (i / 5) * (bounds.maxX - bounds.minX);
				const yv = bounds.maxY - (i / 5) * (bounds.maxY - bounds.minY);
				gridHtml += `<line x1="${pos}" y1="45" x2="${pos}" y2="455" stroke="#1f2333" stroke-width="1" />`;
				gridHtml += `<line x1="45" y1="${pos}" x2="455" y2="${pos}" stroke="#1f2333" stroke-width="1" />`;
				gridHtml += `<text x="${pos}" y="472" fill="#8892b0" font-size="10" text-anchor="middle">${xv.toFixed(1)}m</text>`;
				gridHtml += `<text x="38" y="${pos + 3}" fill="#8892b0" font-size="10" text-anchor="end">${yv.toFixed(1)}m</text>`;
			}
			document.getElementById('ed-grid-layer').innerHTML = gridHtml;

			// 2. Render Uploaded SVG inside bounding box
			const tl = toSvgPx(currentFp.min_x, currentFp.max_y, bounds);
			const br = toSvgPx(currentFp.max_x, currentFp.min_y, bounds);
			const x = Math.min(tl.px, br.px);
			const y = Math.min(tl.py, br.py);
			const w = Math.max(10, Math.abs(br.px - tl.px));
			const h = Math.max(10, Math.abs(br.py - tl.py));

			const parser = new DOMParser();
			const doc = parser.parseFromString(currentFp.svg_data, "image/svg+xml");
			const parsedSvg = doc.querySelector("svg");
			if (parsedSvg) {
				let vb = parsedSvg.getAttribute("viewBox");
				if (!vb) {
					const uw = parseFloat(parsedSvg.getAttribute("width")) || 500;
					const uh = parseFloat(parsedSvg.getAttribute("height")) || 500;
					vb = `0 0 ${uw} ${uh}`;
				}
				document.getElementById('ed-svg-layer').innerHTML = `
					<svg x="${x}" y="${y}" width="${w}" height="${h}" viewBox="${vb}" preserveAspectRatio="none" opacity="0.85">
						${parsedSvg.innerHTML}
					</svg>
				`;
			}

			// 3. Render Anchors for Reference
			let anchorHtml = '';
			for (const [aid, pos] of Object.entries(dbAnchors)) {
				const pt = toSvgPx(pos[0], pos[1], bounds);
				anchorHtml += `
					<polygon points="${pt.px},${pt.py-7} ${pt.px-6},${pt.py+5} ${pt.px+6},${pt.py+5}" fill="#e74c3c" stroke="#fff" stroke-width="1" />
					<text x="${pt.px}" y="${pt.py-10}" fill="#ff7675" font-size="11" font-weight="bold" text-anchor="middle">${aid}</text>
				`;
			}
			document.getElementById('ed-anchors-layer').innerHTML = anchorHtml;

			// 4. Render Draggable Side Handles & Move Box
			const midX = x + w / 2;
			const midY = y + h / 2;
			document.getElementById('ed-handles-layer').innerHTML = `
				<rect class="move-handle" x="${x}" y="${y}" width="${w}" height="${h}" onmousedown="startDrag(event, 'move')" />
				<rect class="edge-handle" x="${x - 5}" y="${midY - 12}" width="10" height="24" rx="2" style="cursor: ew-resize;" onmousedown="startDrag(event, 'left')" />
				<rect class="edge-handle" x="${x + w - 5}" y="${midY - 12}" width="10" height="24" rx="2" style="cursor: ew-resize;" onmousedown="startDrag(event, 'right')" />
				<rect class="edge-handle" x="${midX - 12}" y="${y - 5}" width="24" height="10" rx="2" style="cursor: ns-resize;" onmousedown="startDrag(event, 'top')" />
				<rect class="edge-handle" x="${midX - 12}" y="${y + h - 5}" width="24" height="10" rx="2" style="cursor: ns-resize;" onmousedown="startDrag(event, 'bottom')" />
			`;
		}

		function getMouseSvgPt(evt) {
			const svg = document.getElementById('xy-editor-svg');
			const pt = svg.createSVGPoint();
			pt.x = evt.clientX;
			pt.y = evt.clientY;
			return pt.matrixTransform(svg.getScreenCTM().inverse());
		}

		function startDrag(evt, edge) {
			evt.stopPropagation();
			const pt = getMouseSvgPt(evt);
			const bounds = getPlaneBounds();
			dragState = {
				edge,
				start: fromSvgPx(pt.x, pt.y, bounds),
				orig: { ...currentFp }
			};
		}

		window.addEventListener('mousemove', (evt) => {
			if (!dragState || !currentFp) return;
			const pt = getMouseSvgPt(evt);
			const bounds = getPlaneBounds();
			const curr = fromSvgPx(pt.x, pt.y, bounds);
			const dx = curr.x - dragState.start.x;
			const dy = curr.y - dragState.start.y;

			if (dragState.edge === 'move') {
				currentFp.min_x = dragState.orig.min_x + dx;
				currentFp.max_x = dragState.orig.max_x + dx;
				currentFp.min_y = dragState.orig.min_y + dy;
				currentFp.max_y = dragState.orig.max_y + dy;
			} else if (dragState.edge === 'left') {
				currentFp.min_x = Math.min(dragState.orig.max_x - 0.2, dragState.orig.min_x + dx);
			} else if (dragState.edge === 'right') {
				currentFp.max_x = Math.max(dragState.orig.min_x + 0.2, dragState.orig.max_x + dx);
			} else if (dragState.edge === 'top') {
				currentFp.max_y = Math.max(dragState.orig.min_y + 0.2, dragState.orig.max_y + dy);
			} else if (dragState.edge === 'bottom') {
				currentFp.min_y = Math.min(dragState.orig.max_y - 0.2, dragState.orig.min_y + dy);
			}
			syncInputs();
			renderEditor();
		});

		window.addEventListener('mouseup', () => {
			if (dragState) {
				dragState = null;
				saveFloorplan();
			}
		});

		loadFloorplan();
	</script>
</body>
</html>
"""

@app.route('/')
def index():
	return render_template_string(HTML_TEMPLATE, anchors=database.get_anchors(), tags=database.get_tags(), logs=database.get_recent_logs(limit=15))

@app.route('/api/floorplan/<int:floor_num>', methods=['GET', 'POST', 'DELETE'])
def manage_floorplan(floor_num):
	if request.method == 'GET':
		return jsonify({"floorplan": database.get_floorplan(floor_num)})
	elif request.method == 'POST':
		data = request.json
		database.save_floorplan(
			floor_num,
			data.get('svg_data'),
			float(data.get('min_x', 0.0)),
			float(data.get('max_x', 5.0)),
			float(data.get('min_y', 0.0)),
			float(data.get('max_y', 5.0))
		)
		return jsonify({"status": "saved"})
	elif request.method == 'DELETE':
		database.delete_floorplan(floor_num)
		return jsonify({"status": "deleted"})

@app.route('/modify_anchor', methods=['POST'])
def modify_anchor():
	old_id = request.form.get('old_id')
	action = request.form.get('action')
	if action == 'delete':
		database.delete_anchor(old_id)
	else:
		# Fetch current anchor details so we can fall back on them if fields are blank
		anchors = database.get_anchors()
		current_pos = anchors.get(old_id, [0.0, 0.0, 0.0])

		new_id = request.form.get('new_id').strip()
		if not new_id:
			new_id = old_id

		try:
			x_val = request.form.get('x').strip()
			y_val = request.form.get('y').strip()
			z_val = request.form.get('z').strip()

			x = float(x_val) if x_val else current_pos[0]
			y = float(y_val) if y_val else current_pos[1]
			z = float(z_val) if z_val else current_pos[2]

			database.update_anchor(old_id, new_id, x, y, z)
		except ValueError:
			pass
	return redirect(url_for('index'))

@app.route('/add_anchor', methods=['POST'])
def add_anchor():
	aid = request.form.get('aid')
	try:
		x, y, z = float(request.form.get('x')), float(request.form.get('y')), float(request.form.get('z'))
		database.add_anchor(aid, x, y, z)
	except ValueError:
		pass
	return redirect(url_for('index'))

@app.route('/modify_tag', methods=['POST'])
def modify_tag():
	old_id = request.form.get('old_id')
	action = request.form.get('action')
	if action == 'delete':
		database.delete_tag(old_id)
	else:
		# Fetch current tag details so we can fall back on them if fields are blank
		tags = database.get_tags()
		curr = tags.get(old_id, {"tilt_deg": 0.0, "radius": 1.0, "center": [0.0, 0.0, 0.0]})

		new_id = request.form.get('new_id').strip()
		if not new_id:
			new_id = old_id

		try:
			tilt_val = request.form.get('tilt').strip()
			radius_val = request.form.get('radius').strip()
			cx_val = request.form.get('cx').strip()
			cy_val = request.form.get('cy').strip()
			cz_val = request.form.get('cz').strip()

			tilt = float(tilt_val) if tilt_val else curr.get("tilt_deg", 0.0)
			radius = float(radius_val) if radius_val else curr.get("radius", 1.0)
			
			curr_center = curr.get("center", [0.0, 0.0, 0.0])
			cx = float(cx_val) if cx_val else curr_center[0]
			cy = float(cy_val) if cy_val else curr_center[1]
			cz = float(cz_val) if cz_val else curr_center[2]

			database.update_tag(old_id, new_id, tilt, radius, cx, cy, cz)
		except ValueError:
			pass
	return redirect(url_for('index'))

@app.route('/add_tag', methods=['POST'])
def add_tag():
	tid = request.form.get('tid')
	try:
		tilt = float(request.form.get('tilt'))
		radius = float(request.form.get('radius'))
		cx, cy, cz = float(request.form.get('cx')), float(request.form.get('cy')), float(request.form.get('cz'))
		database.add_tag(tid, tilt, radius, cx, cy, cz)
	except ValueError:
		pass
	return redirect(url_for('index'))

if __name__ == '__main__':
	database.init_db()
	app.run(debug=True, port=5000)