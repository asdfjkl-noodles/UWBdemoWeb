import sqlite3
import json

DB_NAME = "uwb_system.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS anchors (
            id TEXT PRIMARY KEY,
            x REAL,
            y REAL,
            z REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id TEXT PRIMARY KEY,
            tilt_deg REAL,
            radius REAL,
            center_x REAL,
            center_y REAL,
            center_z REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movement_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            step INTEGER,
            tag_id TEXT,
            true_x REAL, true_y REAL, true_z REAL,
            calc_x REAL, calc_y REAL, calc_z REAL,
            distances TEXT
        )
    ''')

    cursor.execute('''
            CREATE TABLE IF NOT EXISTS floorplans (
                floor_num INTEGER PRIMARY KEY,
                svg_data TEXT,
                min_x REAL,
                max_x REAL,
                min_y REAL,
                max_y REAL
            )
        ''')
    
    conn.commit()
    conn.close()

def seed_default_data(default_anchors, default_tags):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM anchors')
    if cursor.fetchone()[0] == 0:
        for aid, pos in default_anchors.items():
            cursor.execute('INSERT INTO anchors (id, x, y, z) VALUES (?, ?, ?, ?)', (aid, pos[0], pos[1], pos[2]))
            
    cursor.execute('SELECT COUNT(*) FROM tags')
    if cursor.fetchone()[0] == 0:
        for tag_id, cfg in default_tags.items():
            cursor.execute('INSERT INTO tags (id, tilt_deg, radius, center_x, center_y, center_z) VALUES (?, ?, ?, ?, ?, ?)',
                           (tag_id, cfg['tilt_deg'], cfg['radius'], cfg['center'][0], cfg['center'][1], cfg['center'][2]))
            
    conn.commit()
    conn.close()

def get_anchors():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, x, y, z FROM anchors')
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: [row[1], row[2], row[3]] for row in rows}

def get_tags():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, tilt_deg, radius, center_x, center_y, center_z FROM tags')
    rows = cursor.fetchall()
    conn.close()
    tags = {}
    for r in rows:
        tags[r[0]] = {"tilt_deg": r[1], "radius": r[2], "center": [r[3], r[4], r[5]]}
    return tags

# --- Anchor Management ---
def add_anchor(aid, x, y, z):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO anchors (id, x, y, z) VALUES (?, ?, ?, ?)', (aid, x, y, z))
    conn.commit()
    conn.close()

def update_anchor(old_id, new_id, x, y, z):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if old_id != new_id:
        cursor.execute('UPDATE anchors SET id = ?, x = ?, y = ?, z = ? WHERE id = ?', (new_id, x, y, z, old_id))
    else:
        cursor.execute('UPDATE anchors SET x = ?, y = ?, z = ? WHERE id = ?', (x, y, z, old_id))
    conn.commit()
    conn.close()

def delete_anchor(aid):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM anchors WHERE id = ?', (aid,))
    conn.commit()
    conn.close()

# --- Tag Management ---
def add_tag(tid, tilt, radius, cx, cy, cz):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO tags (id, tilt_deg, radius, center_x, center_y, center_z) VALUES (?, ?, ?, ?, ?, ?)', 
                   (tid, tilt, radius, cx, cy, cz))
    conn.commit()
    conn.close()

def update_tag(old_id, new_id, tilt, radius, cx, cy, cz):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if old_id != new_id:
        cursor.execute('UPDATE tags SET id = ?, tilt_deg = ?, radius = ?, center_x = ?, center_y = ?, center_z = ? WHERE id = ?', 
                       (new_id, tilt, radius, cx, cy, cz, old_id))
    else:
        cursor.execute('UPDATE tags SET tilt_deg = ?, radius = ?, center_x = ?, center_y = ?, center_z = ? WHERE id = ?', 
                       (tilt, radius, cx, cy, cz, old_id))
    conn.commit()
    conn.close()

def delete_tag(tid):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tags WHERE id = ?', (tid,))
    conn.commit()
    conn.close()

# --- Logging ---
def log_step(step, tag_id, true_pos, calc_pos, distances):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO movement_logs (step, tag_id, true_x, true_y, true_z, calc_x, calc_y, calc_z, distances)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (step, tag_id, true_pos[0], true_pos[1], true_pos[2], 
          calc_pos[0], calc_pos[1], calc_pos[2], json.dumps(distances)))
    conn.commit()
    conn.close()

def get_recent_logs(limit=25):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT step, tag_id, true_x, true_y, true_z, calc_x, calc_y, calc_z, distances FROM movement_logs ORDER BY id DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_latest_positions():
    """Fetches the most recent True and Calculated XYZ positions for each active tag."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get all currently active tag IDs from the tags table
    cursor.execute('SELECT id FROM tags')
    active_tags = [row[0] for row in cursor.fetchall()]
    
    latest_data = {}
    for tid in active_tags:
        cursor.execute('''
            SELECT step, true_x, true_y, true_z, calc_x, calc_y, calc_z 
            FROM movement_logs 
            WHERE tag_id = ? 
            ORDER BY id DESC LIMIT 1
        ''', (tid,))
        row = cursor.fetchone()
        if row:
            latest_data[tid] = {
                "step": row[0],
                "true_pos": [row[1], row[2], row[3]],
                "calc_pos": [row[4], row[5], row[6]]
            }
            
    conn.close()
    return latest_data



# Add these functions to the bottom of database.py:
def save_floorplan(floor_num, svg_data, min_x, max_x, min_y, max_y):
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	cursor.execute('''
		INSERT INTO floorplans (floor_num, svg_data, min_x, max_x, min_y, max_y)
		VALUES (?, ?, ?, ?, ?, ?)
		ON CONFLICT(floor_num) DO UPDATE SET
			svg_data = COALESCE(excluded.svg_data, floorplans.svg_data),
			min_x = excluded.min_x,
			max_x = excluded.max_x,
			min_y = excluded.min_y,
			max_y = excluded.max_y
	''', (floor_num, svg_data, min_x, max_x, min_y, max_y))
	conn.commit()
	conn.close()

def get_floorplan(floor_num):
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	cursor.execute('SELECT svg_data, min_x, max_x, min_y, max_y FROM floorplans WHERE floor_num = ?', (floor_num,))
	row = cursor.fetchone()
	conn.close()
	if row:
		return {
			"svg_data": row[0],
			"min_x": row[1],
			"max_x": row[2],
			"min_y": row[3],
			"max_y": row[4]
		}
	return None

def get_all_floorplans():
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	cursor.execute('SELECT floor_num, svg_data, min_x, max_x, min_y, max_y FROM floorplans')
	rows = cursor.fetchall()
	conn.close()
	return {
		r[0]: {"svg_data": r[1], "min_x": r[2], "max_x": r[3], "min_y": r[4], "max_y": r[5]}
		for r in rows
	}

def delete_floorplan(floor_num):
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	cursor.execute('DELETE FROM floorplans WHERE floor_num = ?', (floor_num,))
	conn.commit()
	conn.close()