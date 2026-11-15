The database is created automatically by backend/main.py.

Main tables:

1. tags
   Editable tag/device information.

2. anchors
   Fixed UWB anchor positions.

3. positions
   Every received UWB position with timestamp, x/y/z, accuracy and source.

4. zones
   Geofence rectangles.

5. geofence_events
   ENTER/EXIT events generated when a tag crosses a zone boundary.

Useful PostgreSQL commands:

    \dt

    SELECT * FROM tags;

    SELECT * FROM anchors;

    SELECT * FROM positions ORDER BY timestamp DESC LIMIT 20;

    SELECT * FROM zones;

    SELECT * FROM geofence_events ORDER BY timestamp DESC LIMIT 20;
