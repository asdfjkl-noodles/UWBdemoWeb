import sqlite3
import json
import time
from datetime import datetime

DB_NAME = "uwb_system.db"

# ==========================================
# EDITABLE HISTORY CONFIGURATION
# ==========================================
HISTORY_LIMIT_MINUTES = 30          # Maximum history retention & playback window (minutes)
DISPLAY_TIME_FORMAT = "%H:%M:%S"    # Editable display format (e.g., "%H:%M:%S" or "%I:%M:%S %p")

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
			timestamp REAL,
			step INTEGER,
			tag_id TEXT,
			true_x REAL, true_y REAL, true_z REAL,
			calc_x REAL, calc_y REAL, calc_z REAL,
			distances TEXT
		)
	''')

	# Migrate older movement_logs table if 'timestamp' column does not exist yet
	cursor.execute("PRAGMA table_info(movement_logs)")
	log_cols = [row[1] for row in cursor.fetchall()]
	if 'timestamp' not in log_cols:
		cursor.execute('ALTER TABLE movement_logs ADD COLUMN timestamp REAL')
		cursor.execute('UPDATE movement_logs SET timestamp = ? WHERE timestamp IS NULL', (time.time(),))

	cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_tag_time ON movement_logs (tag_id, timestamp)')

	cursor.execute('''
		CREATE TABLE IF NOT EXISTS floorplans (
			floor_num INTEGER PRIMARY KEY,
			height REAL DEFAULT 2.0,
			svg_data TEXT,
			min_x REAL,
			max_x REAL,
			min_y REAL,
			max_y REAL
		)
	''')

	# Migrate older floorplans table if 'height' column does not exist yet
	cursor.execute("PRAGMA table_info(floorplans)")
	cols = [row[1] for row in cursor.fetchall()]
	if 'height' not in cols:
		cursor.execute('ALTER TABLE floorplans ADD COLUMN height REAL DEFAULT 2.0')

	# Seed default Floor 1 (3m) and Floor 2 (2m) if no floors exist
	cursor.execute('SELECT COUNT(*) FROM floorplans')
	if cursor.fetchone()[0] == 0:
		cursor.execute('INSERT INTO floorplans (floor_num, height, svg_data, min_x, max_x, min_y, max_y) VALUES (?, ?, ?, ?, ?, ?, ?)',
					   (1, 3.0, None, 0.0, 5.0, 0.0, 5.0))
		cursor.execute('INSERT INTO floorplans (floor_num, height, svg_data, min_x, max_x, min_y, max_y) VALUES (?, ?, ?, ?, ?, ?, ?)',
					   (2, 2.0, None, 0.0, 5.0, 0.0, 5.0))
	
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

# --- Logging & History ---
def log_step(step, tag_id, true_pos, calc_pos, distances):
	now = time.time()
	cutoff = now - (HISTORY_LIMIT_MINUTES * 60)
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	cursor.execute('''
		INSERT INTO movement_logs (timestamp, step, tag_id, true_x, true_y, true_z, calc_x, calc_y, calc_z, distances)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	''', (now, step, tag_id, true_pos[0], true_pos[1], true_pos[2], 
		  calc_pos[0], calc_pos[1], calc_pos[2], json.dumps(distances)))
	# Keep database trimmed to HISTORY_LIMIT_MINUTES
	cursor.execute('DELETE FROM movement_logs WHERE timestamp < ?', (cutoff,))
	conn.commit()
	conn.close()

def get_recent_logs(limit=25):
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	cursor.execute('SELECT step, tag_id, true_x, true_y, true_z, calc_x, calc_y, calc_z, distances FROM movement_logs ORDER BY id DESC LIMIT ?', (limit,))
	rows = cursor.fetchall()
	conn.close()
	return rows

def get_tag_history(tag_id, limit_minutes=None):
	mins = float(limit_minutes) if limit_minutes is not None else HISTORY_LIMIT_MINUTES
	cutoff = time.time() - (mins * 60)
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	cursor.execute('''
		SELECT timestamp, step, true_x, true_y, true_z, calc_x, calc_y, calc_z
		FROM movement_logs
		WHERE tag_id = ? AND timestamp >= ?
		ORDER BY id ASC
	''', (tag_id, cutoff))
	rows = cursor.fetchall()
	conn.close()

	history = []
	for r in rows:
		ts = r[0] if r[0] is not None else time.time()
		history.append({
			"timestamp": ts,
			"display_time": datetime.fromtimestamp(ts).strftime(DISPLAY_TIME_FORMAT),
			"step": r[1],
			"true_pos": [r[2], r[3], r[4]],
			"calc_pos": [r[5], r[6], r[7]]
		})
	return history

def get_latest_positions():
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
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

# --- Dynamic Floor & Floorplan Management ---
def get_all_floors():
	"""Returns floors ordered by floor_num with calculated z_min and z_max."""
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	cursor.execute('SELECT floor_num, height, svg_data, min_x, max_x, min_y, max_y FROM floorplans ORDER BY floor_num ASC')
	rows = cursor.fetchall()
	conn.close()

	floors = []
	current_z = 0.0
	for r in rows:
		h = float(r[1]) if r[1] is not None else 2.0
		z_min = round(current_z, 3)
		z_max = round(current_z + h, 3)
		floors.append({
			"floor_num": r[0],
			"height": h,
			"z_min": z_min,
			"z_max": z_max,
			"svg_data": r[2],
			"min_x": r[3] if r[3] is not None else 0.0,
			"max_x": r[4] if r[4] is not None else 5.0,
			"min_y": r[5] if r[5] is not None else 0.0,
			"max_y": r[6] if r[6] is not None else 5.0
		})
		current_z += h
	return floors

def add_floor(height=2.0):
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	cursor.execute('SELECT COALESCE(MAX(floor_num), 0) FROM floorplans')
	next_num = cursor.fetchone()[0] + 1
	cursor.execute('''
		INSERT INTO floorplans (floor_num, height, svg_data, min_x, max_x, min_y, max_y)
		VALUES (?, ?, NULL, 0.0, 5.0, 0.0, 5.0)
	''', (next_num, float(height)))
	conn.commit()
	conn.close()
	return next_num

def update_floor_height(floor_num, height):
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	cursor.execute('UPDATE floorplans SET height = ? WHERE floor_num = ?', (float(height), floor_num))
	conn.commit()
	conn.close()

def save_floorplan(floor_num, svg_data, min_x, max_x, min_y, max_y, height=None):
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	if height is not None:
		cursor.execute('''
			INSERT INTO floorplans (floor_num, height, svg_data, min_x, max_x, min_y, max_y)
			VALUES (?, ?, ?, ?, ?, ?, ?)
			ON CONFLICT(floor_num) DO UPDATE SET
				height = excluded.height,
				svg_data = COALESCE(excluded.svg_data, floorplans.svg_data),
				min_x = excluded.min_x,
				max_x = excluded.max_x,
				min_y = excluded.min_y,
				max_y = excluded.max_y
		''', (floor_num, float(height), svg_data, min_x, max_x, min_y, max_y))
	else:
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

def clear_floorplan_svg(floor_num):
	"""Clears only the SVG image while keeping the floor and its height."""
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	cursor.execute('UPDATE floorplans SET svg_data = NULL WHERE floor_num = ?', (floor_num,))
	conn.commit()
	conn.close()

def delete_floor(floor_num):
	"""Removes the floor completely and re-numbers subsequent floors cleanly."""
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	cursor.execute('DELETE FROM floorplans WHERE floor_num = ?', (floor_num,))
	cursor.execute('SELECT floor_num FROM floorplans ORDER BY floor_num ASC')
	remaining = [r[0] for r in cursor.fetchall()]
	for idx, old_num in enumerate(remaining, start=1):
		if old_num != idx:
			cursor.execute('UPDATE floorplans SET floor_num = ? WHERE floor_num = ?', (idx, old_num))
	conn.commit()
	conn.close()