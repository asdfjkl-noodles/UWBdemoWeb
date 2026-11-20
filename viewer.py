from flask import Flask, render_template_string, jsonify
import database

app = Flask(__name__)

VIEWER_HTML = """
<!DOCTYPE html>
<html>
<head>
	<title>Live 3D UWB Workspace Visualizer</title>
	<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
	<style>
		body { font-family: Arial, sans-serif; margin: 20px; background: #1e1e2f; color: #f4f4f9; padding-bottom: 110px; }
		h1 { color: #00d8ff; margin-bottom: 5px; }
		p { color: #aaa; margin-top: 0; }
		.toolbar {
			display: flex; align-items: center; gap: 15px; flex-wrap: wrap;
			background: #27293d; padding: 12px 18px; border-radius: 8px; margin-bottom: 15px;
			border: 1px solid #3c3f58;
		}
		button {
			background: #3498db; color: #fff; border: none; padding: 8px 14px;
			border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 13px;
		}
		button:hover { background: #2980b9; }
		button.active-history { background: #f39c12; color: #12141c; }
		select, input[type="number"] {
			padding: 7px 10px; border-radius: 5px; border: 1px solid #3c3f58;
			background: #181a24; color: #fff; font-weight: bold; font-size: 13px;
		}
		.layout { display: flex; gap: 20px; flex-wrap: wrap; }
		#plot-container { flex: 2; min-width: 600px; height: 620px; background: #27293d; border-radius: 8px; padding: 10px; cursor: grab; }
		#plot-container:active { cursor: grabbing; }
		#data-panel { flex: 1; min-width: 320px; background: #27293d; border-radius: 8px; padding: 20px; }
		table { width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; font-size: 13px; }
		th, td { padding: 8px; border: 1px solid #3c3f58; text-align: center; }
		th { background-color: #34495e; color: #00d8ff; }
		.badge-true { color: #2ecc71; font-weight: bold; }
		.badge-calc { color: #3498db; font-weight: bold; }
		.badge-anchor { color: #e74c3c; font-weight: bold; }
		.instruction-box { background: #2f3346; border-left: 4px solid #00d8ff; padding: 10px 15px; margin-bottom: 15px; border-radius: 4px; font-size: 13px; }

		/* Bottom Fixed History Scrubber Bar */
		.history-bar {
			position: fixed; bottom: 0; left: 0; right: 0;
			background: #181a24; border-top: 2px solid #f39c12;
			padding: 12px 25px; display: none; flex-direction: column; gap: 8px;
			box-shadow: 0 -4px 12px rgba(0,0,0,0.4); z-index: 1000;
		}
		.history-bar-top { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 15px; font-size: 13px; }
		.history-slider { width: 100%; cursor: pointer; accent-color: #f39c12; }
	</style>
</head>
<body>
	<div style="background: #242736; padding: 10px 20px; display: flex; gap: 15px; align-items: center; border-bottom: 2px solid #32364a; font-family: Arial, sans-serif; margin-bottom: 15px;">
		<strong style="color: #00d8ff;">UWB System:</strong>
		<a href="http://127.0.0.1:5002" style="color: #fff; text-decoration: none; padding: 5px 10px; background: #181a24; border-radius: 4px;">🗺️ Floorplan Map (:5002)</a>
		<a href="http://127.0.0.1:5001" style="color: #fff; text-decoration: none; padding: 5px 10px; background: #181a24; border-radius: 4px;">🧊 3D Visualizer (:5001)</a>
		<a href="http://127.0.0.1:5000" style="color: #fff; text-decoration: none; padding: 5px 10px; background: #181a24; border-radius: 4px;">⚙️ Admin Dashboard (:5000)</a>
	</div>

	<h1>Live 3D UWB Position Visualizer</h1>
	<p>Real-time rendering from local SQLite database. Smooth manual rotation enabled.</p>

	<!-- History Controls Bar -->
	<div class="toolbar">
		<button id="toggle-history-btn" onclick="toggleHistoryMode()">⏱️ History Mode: OFF</button>
		
		<div id="history-tag-group" style="display: none; align-items: center; gap: 10px;">
			<label for="history-tag-select"><strong>Select Tag:</strong></label>
			<select id="history-tag-select" onchange="loadTagHistory()"></select>
			<button onclick="loadTagHistory()" style="background: #2ecc71; color: #12141c;">↻ Refresh</button>
		</div>

		<div id="mode-status" style="margin-left: auto; font-weight: bold; color: #2ecc71; font-size: 13px;">
			● LIVE STREAMING
		</div>
	</div>
	
	<div class="instruction-box">
		💡 <strong>Tip:</strong> Click & drag to rotate freely. Toggle <strong>History Mode</strong> above to select a tag and scrub through up to {{ history_limit }} minutes of recorded movement at the bottom.
	</div>

	<div class="layout">
		<div id="plot-container"></div>

		<div id="data-panel">
			<h3>Active Anchors (Database)</h3>
			<table id="anchor-table">
				<thead><tr><th>ID</th><th>X (m)</th><th>Y (m)</th><th>Z (m)</th></tr></thead>
				<tbody></tbody>
			</table>

			<h3 id="tag-table-title">Live Tag Coordinates</h3>
			<table id="tag-table">
				<thead>
					<tr>
						<th>Tag</th>
						<th><span class="badge-true">True XYZ</span></th>
						<th><span class="badge-calc">Calc XYZ</span></th>
					</tr>
				</thead>
				<tbody></tbody>
			</table>
		</div>
	</div>

	<!-- Bottom Scrollable History Bar -->
	<div class="history-bar" id="history-bar">
		<div class="history-bar-top">
			<div>
				<strong style="color: #f39c12;">📜 Playback Time:</strong>
				<span id="hist-display-time" style="font-size: 15px; font-weight: bold; color: #fff; margin-left: 6px;">--:--:--</span>
				<span id="hist-step-info" style="color: #aaa; margin-left: 10px;">(Point 0 / 0)</span>
			</div>
			<div style="display: flex; align-items: center; gap: 10px;">
				<label for="time-format-select"><strong>Time Display:</strong></label>
				<select id="time-format-select" onchange="renderHistoryFrame()">
					<option value="clock">Clock (HH:MM:SS)</option>
					<option value="relative">Relative (-MM:SS ago)</option>
					<option value="both">Clock + Relative</option>
				</select>
			</div>
		</div>
		<input type="range" id="history-slider" class="history-slider" min="0" max="0" value="0" oninput="renderHistoryFrame()">
	</div>

	<script>
		let isInitialized = false;
		let isUserDragging = false;
		let historyMode = false;
		let cachedAnchors = {};
		let liveTags = {};
		let historyRecords = [];
		const plotDiv = document.getElementById('plot-container');

		plotDiv.addEventListener('mousedown', () => { isUserDragging = true; });
		window.addEventListener('mouseup', () => { isUserDragging = false; });
		plotDiv.addEventListener('touchstart', () => { isUserDragging = true; });
		window.addEventListener('touchend', () => { isUserDragging = false; });

		function formatHistoryTimestamp(rec, latestTs) {
			const mode = document.getElementById('time-format-select').value;
			const diffSec = Math.max(0, Math.round(latestTs - rec.timestamp));
			const mins = String(Math.floor(diffSec / 60)).padStart(2, '0');
			const secs = String(diffSec % 60).padStart(2, '0');
			const relStr = diffSec === 0 ? "Latest" : `-${mins}:${secs} ago`;

			if (mode === 'relative') return relStr;
			if (mode === 'both') return `${rec.display_time} (${relStr})`;
			return rec.display_time;
		}

		function syncTagDropdown(tagIds) {
			const select = document.getElementById('history-tag-select');
			const prev = select.value;
			const sig = tagIds.join('|');
			if (select.dataset.sig !== sig) {
				select.dataset.sig = sig;
				select.innerHTML = '';
				tagIds.forEach(tid => {
					const opt = document.createElement('option');
					opt.value = tid;
					opt.text = tid;
					select.appendChild(opt);
				});
				if (tagIds.includes(prev)) select.value = prev;
			}
		}

		async function toggleHistoryMode() {
			historyMode = !historyMode;
			const btn = document.getElementById('toggle-history-btn');
			const tagGroup = document.getElementById('history-tag-group');
			const bar = document.getElementById('history-bar');
			const status = document.getElementById('mode-status');

			if (historyMode) {
				btn.innerText = "⏱️ History Mode: ON";
				btn.classList.add('active-history');
				tagGroup.style.display = 'flex';
				bar.style.display = 'flex';
				status.innerText = "⏸ HISTORY PLAYBACK";
				status.style.color = "#f39c12";
				document.getElementById('tag-table-title').innerText = "Historical Tag Coordinates";
				await loadTagHistory();
			} else {
				btn.innerText = "⏱️ History Mode: OFF";
				btn.classList.remove('active-history');
				tagGroup.style.display = 'none';
				bar.style.display = 'none';
				status.innerText = "● LIVE STREAMING";
				status.style.color = "#2ecc71";
				document.getElementById('tag-table-title').innerText = "Live Tag Coordinates";
				fetchAndUpdate();
			}
		}

		async function loadTagHistory() {
			const tid = document.getElementById('history-tag-select').value;
			if (!tid) return;
			try {
				const res = await fetch(`/api/history/${encodeURIComponent(tid)}`);
				const data = await res.json();
				historyRecords = data.history || [];
				const slider = document.getElementById('history-slider');
				slider.min = 0;
				slider.max = Math.max(0, historyRecords.length - 1);
				slider.value = slider.max;
				renderHistoryFrame();
			} catch (err) {
				console.error("Error loading tag history:", err);
			}
		}

		function renderHistoryFrame() {
			if (!historyMode) return;
			const tid = document.getElementById('history-tag-select').value;
			const slider = document.getElementById('history-slider');
			const idx = parseInt(slider.value, 10) || 0;

			if (historyRecords.length === 0) {
				document.getElementById('hist-display-time').innerText = "No history data";
				document.getElementById('hist-step-info').innerText = "(0 records)";
				return;
			}

			const rec = historyRecords[idx];
			const firstTs = historyRecords[0].timestamp;
			const latestTs = historyRecords[historyRecords.length - 1].timestamp;
			const spanSec = Math.max(0, Math.round(latestTs - firstTs));
			const spanMins = String(Math.floor(spanSec / 60)).padStart(2, '0');
			const spanRemSecs = String(spanSec % 60).padStart(2, '0');

			document.getElementById('hist-display-time').innerText = formatHistoryTimestamp(rec, latestTs);
			document.getElementById('hist-step-info').innerText = `(Point ${idx + 1} / ${historyRecords.length} • Recorded: ${spanMins}:${spanRemSecs} / {{ history_limit }}:00)`;

			const singleTagMap = { [tid]: rec };
			updateTables(cachedAnchors, singleTagMap);

			if (!isUserDragging) {
				update3DPlot(cachedAnchors, singleTagMap);
			}
		}

		async function fetchAndUpdate() {
			try {
				const response = await fetch('/api/live_data');
				const data = await response.json();
				cachedAnchors = data.anchors;
				liveTags = data.tags;
				syncTagDropdown(Object.keys(liveTags));

				if (!historyMode) {
					updateTables(cachedAnchors, liveTags);
					if (!isUserDragging) {
						update3DPlot(cachedAnchors, liveTags);
					}
				}
			} catch (err) {
				console.error("Error fetching live UWB data:", err);
			}
		}

		function updateTables(anchors, tags) {
			const anchorBody = document.querySelector('#anchor-table tbody');
			anchorBody.innerHTML = '';
			for (const [id, pos] of Object.entries(anchors)) {
				anchorBody.innerHTML += `<tr>
					<td class="badge-anchor">${id}</td>
					<td>${pos[0].toFixed(2)}</td>
					<td>${pos[1].toFixed(2)}</td>
					<td>${pos[2].toFixed(2)}</td>
				</tr>`;
			}

			const tagBody = document.querySelector('#tag-table tbody');
			tagBody.innerHTML = '';
			for (const [id, info] of Object.entries(tags)) {
				const tp = info.true_pos;
				const cp = info.calc_pos;
				tagBody.innerHTML += `<tr>
					<td><strong>${id}</strong></td>
					<td class="badge-true">[${tp[0].toFixed(2)}, ${tp[1].toFixed(2)}, ${tp[2].toFixed(2)}]</td>
					<td class="badge-calc">[${cp[0].toFixed(2)}, ${cp[1].toFixed(2)}, ${cp[2].toFixed(2)}]</td>
				</tr>`;
			}
		}

		function update3DPlot(anchors, tags) {
			const anchorIds = Object.keys(anchors);
			const anchorTrace = {
				x: anchorIds.map(id => anchors[id][0]),
				y: anchorIds.map(id => anchors[id][1]),
				z: anchorIds.map(id => anchors[id][2]),
				text: anchorIds,
				mode: 'markers+text',
				type: 'scatter3d',
				name: 'Anchors',
				textposition: 'top center',
				marker: { size: 9, color: '#e74c3c', symbol: 'diamond' }
			};

			const tagIds = Object.keys(tags);
			const trueTrace = {
				x: tagIds.map(id => tags[id].true_pos[0]),
				y: tagIds.map(id => tags[id].true_pos[1]),
				z: tagIds.map(id => tags[id].true_pos[2]),
				text: tagIds.map(id => `${id} (True)`),
				mode: 'markers+text',
				type: 'scatter3d',
				name: 'True Pos',
				textposition: 'bottom center',
				marker: { size: 7, color: '#2ecc71', symbol: 'circle' }
			};

			const calcTrace = {
				x: tagIds.map(id => tags[id].calc_pos[0]),
				y: tagIds.map(id => tags[id].calc_pos[1]),
				z: tagIds.map(id => tags[id].calc_pos[2]),
				text: tagIds.map(id => `${id} (Calc)`),
				mode: 'markers+text',
				type: 'scatter3d',
				name: 'Calculated Pos',
				textposition: 'top center',
				marker: { size: 7, color: '#3498db', symbol: 'cross' }
			};

			const layout = {
				paper_bgcolor: '#27293d',
				plot_bgcolor: '#27293d',
				font: { color: '#f4f4f9' },
				margin: { l: 0, r: 0, b: 0, t: 30 },
				scene: {
					xaxis: { title: 'X (m)', range: [-1, 6] },
					yaxis: { title: 'Y (m)', range: [-1, 6] },
					zaxis: { title: 'Z (m)', range: [-1, 5] },
					aspectmode: 'cube'
				},
				uirevision: 'uwb_camera_lock_state'
			};

			if (!isInitialized) {
				Plotly.newPlot(plotDiv, [anchorTrace, trueTrace, calcTrace], layout);
				isInitialized = true;
			} else {
				Plotly.react(plotDiv, [anchorTrace, trueTrace, calcTrace], layout);
			}
		}

		setInterval(fetchAndUpdate, 500);
		fetchAndUpdate();
	</script>
</body>
</html>
"""

@app.route('/')
def index():
	return render_template_string(VIEWER_HTML, history_limit=database.HISTORY_LIMIT_MINUTES)

@app.route('/api/live_data')
def live_data():
	anchors = database.get_anchors()
	tags = database.get_latest_positions()
	return jsonify({"anchors": anchors, "tags": tags})

@app.route('/api/history/<tag_id>')
def tag_history(tag_id):
	return jsonify({
		"tag_id": tag_id,
		"limit_minutes": database.HISTORY_LIMIT_MINUTES,
		"history": database.get_tag_history(tag_id)
	})

if __name__ == '__main__':
	database.init_db()
	app.run(debug=True, port=5001)