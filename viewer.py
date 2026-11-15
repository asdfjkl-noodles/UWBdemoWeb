from flask import Flask, render_template_string, jsonify
import database

app = Flask(__name__)

VIEWER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Live 3D UWB Workspace Visualizer</title>
    <!-- Load Plotly.js for smooth interactive 3D rendering -->
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1e1e2f; color: #f4f4f9; }
        h1 { color: #00d8ff; margin-bottom: 5px; }
        p { color: #aaa; margin-top: 0; }
        .layout { display: flex; gap: 20px; flex-wrap: wrap; }
        #plot-container { flex: 2; min-width: 600px; height: 650px; background: #27293d; border-radius: 8px; padding: 10px; }
        #data-panel { flex: 1; min-width: 320px; background: #27293d; border-radius: 8px; padding: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; font-size: 13px; }
        th, td { padding: 8px; border: 1px solid #3c3f58; text-align: center; }
        th { background-color: #34495e; color: #00d8ff; }
        .badge-true { color: #2ecc71; font-weight: bold; }
        .badge-calc { color: #3498db; font-weight: bold; }
        .badge-anchor { color: #e74c3c; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Live 3D UWB Position Visualizer</h1>
    <p>Real-time rendering from local SQLite database. Edit anchors/tags on port 5000 to see live updates here.</p>
    
    <div class="layout">
        <!-- 3D Interactive Graph -->
        <div id="plot-container"></div>

        <!-- Live Coordinates Readout -->
        <div id="data-panel">
            <h3>Active Anchors (Database)</h3>
            <table id="anchor-table">
                <thead><tr><th>ID</th><th>X (m)</th><th>Y (m)</th><th>Z (m)</th></tr></thead>
                <tbody></tbody>
            </table>

            <h3>Live Tag Coordinates</h3>
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

    <script>
        let isInitialized = false;

        async function fetchAndUpdate() {
            try {
                const response = await fetch('/api/live_data');
                const data = await response.json();

                updateTables(data.anchors, data.tags);
                update3DPlot(data.anchors, data.tags);
            } catch (err) {
                console.error("Error fetching live UWB data:", err);
            }
        }

        function updateTables(anchors, tags) {
            // Update Anchors Table
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

            // Update Tags Table
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
            // 1. Anchor Trace
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

            // 2. True Position Trace
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

            // 3. Calculated Position Trace
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
                uirevision: 'true' // Preserves your camera rotation angle during live updates!
            };

            if (!isInitialized) {
                Plotly.newPlot('plot-container', [anchorTrace, trueTrace, calcTrace], layout);
                isInitialized = true;
            } else {
                Plotly.react('plot-container', [anchorTrace, trueTrace, calcTrace], layout);
            }
        }

        // Refresh every 500ms
        setInterval(fetchAndUpdate, 500);
        fetchAndUpdate();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(VIEWER_HTML)

@app.route('/api/live_data')
def live_data():
    anchors = database.get_anchors()
    tags = database.get_latest_positions()
    return jsonify({"anchors": anchors, "tags": tags})

if __name__ == '__main__':
    database.init_db()
    app.run(debug=True, port=5001)