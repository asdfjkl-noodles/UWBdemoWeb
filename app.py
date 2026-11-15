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
        .container { display: flex; gap: 20px; }
        .pane { flex: 1; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .section { margin-bottom: 20px; padding: 10px; background: #fafafa; border: 1px solid #eee; }
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
                <form action="/modify_anchor" method="POST">
                    <label>Select Anchor:</label><br>
                    <select name="old_id" required>
                        {% for aid in anchors.keys() %}
                        <option value="{{ aid }}">{{ aid }}</option>
                        {% endfor %}
                    </select><br><br>
                    <label>New Name ID:</label><br>
                    <input type="text" name="new_id" placeholder="e.g. A0" required><br>
                    <label>X, Y, Z Coordinates:</label><br>
                    <input type="text" name="x" placeholder="X" size="5" required>
                    <input type="text" name="y" placeholder="Y" size="5" required>
                    <input type="text" name="z" placeholder="Z" size="5" required><br><br>
                    <button type="submit">Save Changes</button>
                    <button type="submit" name="action" value="delete" class="delete">Delete Anchor</button>
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
                <form action="/modify_tag" method="POST">
                    <label>Select Tag:</label><br>
                    <select name="old_id" required>
                        {% for tid in tags.keys() %}
                        <option value="{{ tid }}">{{ tid }}</option>
                        {% endfor %}
                    </select><br><br>
                    <label>New Name ID:</label><br>
                    <input type="text" name="new_id" placeholder="e.g. T0" required><br>
                    <label>Tilt (°), Radius:</label><br>
                    <input type="text" name="tilt" placeholder="Tilt" size="5" required>
                    <input type="text" name="radius" placeholder="Radius" size="5" required><br>
                    <label>Center (X, Y, Z):</label><br>
                    <input type="text" name="cx" placeholder="X" size="4" required>
                    <input type="text" name="cy" placeholder="Y" size="4" required>
                    <input type="text" name="cz" placeholder="Z" size="4" required><br><br>
                    <button type="submit">Save Changes</button>
                    <button type="submit" name="action" value="delete" class="delete">Delete Tag</button>
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
    <div class="pane" style="margin-top: 20px;">
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
        new_id = request.form.get('new_id')
        try:
            x, y, z = float(request.form.get('x')), float(request.form.get('y')), float(request.form.get('z'))
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
        new_id = request.form.get('new_id')
        try:
            tilt = float(request.form.get('tilt'))
            radius = float(request.form.get('radius'))
            cx, cy, cz = float(request.form.get('cx')), float(request.form.get('cy')), float(request.form.get('cz'))
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