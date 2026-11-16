from flask import Flask, render_template_string, request, redirect, url_for
import database

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>UWB Dropdown Control Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f4f4f9; color: #333; }
        h1, h2 { color: #2c3e50; }
        table { width: 100%; border-collapse: collapse; background: #fff; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        th, td { padding: 10px; border: 1px solid #ddd; text-align: center; }
        th { background-color: #34495e; color: white; }
        select, input[type="text"] { padding: 6px; margin: 2px; }
        button { background: #3498db; color: white; border: none; padding: 6px 12px; cursor: pointer; border-radius: 4px; }
        button:hover { background: #2980b9; }
        button.delete { background: #e74c3c; }
        button.delete:hover { background: #c0392b; }
        .container { display: flex; gap: 20px; flex-wrap: wrap; }
        .pane { flex: 1; min-width: 350px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .section { margin-bottom: 20px; padding: 10px; background: #fafafa; border: 1px solid #eee; border-radius: 6px; }
        .hint { font-size: 11px; color: #666; margin-bottom: 8px; display: block; }
    </style>
</head>
<body>
    <h1>UWB Dropdown Management Dashboard</h1>
    
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
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, anchors=database.get_anchors(), tags=database.get_tags(), logs=database.get_recent_logs(limit=15))

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