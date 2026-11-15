import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_CONFIG = {
    "host": os.getenv("UWB_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("UWB_DB_PORT", "5432")),
    "dbname": os.getenv("UWB_DB_NAME", "uwb_rtls"),
    "user": os.getenv("UWB_DB_USER", "uwb"),
    "password": os.getenv("UWB_DB_PASSWORD", "uwb_demo_password"),
}


# ============================================================
# DATABASE SCHEMA
# ============================================================

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tags (
    tag_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    tag_type VARCHAR(50) NOT NULL DEFAULT 'person',
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS anchors (
    anchor_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,
    z DOUBLE PRECISION NOT NULL DEFAULT 2.5
);

CREATE TABLE IF NOT EXISTS positions (
    id BIGSERIAL PRIMARY KEY,
    tag_id VARCHAR(50) NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,
    z DOUBLE PRECISION NOT NULL DEFAULT 0,
    accuracy DOUBLE PRECISION,
    source VARCHAR(50) NOT NULL DEFAULT 'simulator'
);

CREATE INDEX IF NOT EXISTS idx_positions_tag_time
ON positions(tag_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS zones (
    zone_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    min_x DOUBLE PRECISION NOT NULL,
    min_y DOUBLE PRECISION NOT NULL,
    max_x DOUBLE PRECISION NOT NULL,
    max_y DOUBLE PRECISION NOT NULL,
    alert_enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS geofence_events (
    id BIGSERIAL PRIMARY KEY,
    tag_id VARCHAR(50) NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
    zone_id VARCHAR(50) NOT NULL REFERENCES zones(zone_id) ON DELETE CASCADE,
    event VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


# ============================================================
# PYDANTIC MODELS
# ============================================================

class PositionIn(BaseModel):
    tag_id: str = Field(min_length=1, max_length=50)
    x: float
    y: float
    z: float = 0
    accuracy: float | None = None
    source: str = Field(default="simulator", max_length=50)
    timestamp: datetime | None = None


class TagIn(BaseModel):
    tag_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    tag_type: str = Field(default="person", max_length=50)
    status: str = Field(default="active", max_length=30)


class ZoneIn(BaseModel):
    zone_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    alert_enabled: bool = True


# ============================================================
# WEBSOCKET CONNECTION MANAGER
# ============================================================

class ConnectionManager:

    def __init__(self):
        self.clients: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.clients.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.clients.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]):

        dead = []

        message = json.dumps(
            payload,
            default=str
        )

        for client in list(self.clients):

            try:
                await client.send_text(message)

            except Exception:
                dead.append(client)

        for client in dead:
            self.disconnect(client)


manager = ConnectionManager()


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_conn():

    return psycopg.connect(
        **DB_CONFIG,
        row_factory=dict_row
    )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():

    with get_conn() as conn:

        conn.execute(SCHEMA_SQL)

        # ----------------------------------------------------
        # SAMPLE TAGS
        # ----------------------------------------------------

        conn.execute("""
            INSERT INTO tags(
                tag_id,
                name,
                tag_type,
                status
            )
            VALUES
                ('TAG001', 'Worker 01', 'person', 'active'),
                ('TAG002', 'Worker 02', 'person', 'active'),
                ('TAG003', 'Forklift 01', 'vehicle', 'active')
            ON CONFLICT (tag_id) DO NOTHING;
        """)

        # ----------------------------------------------------
        # ANCHORS
        # ----------------------------------------------------

        conn.execute("""
            INSERT INTO anchors(
                anchor_id,
                name,
                x,
                y,
                z
            )
            VALUES
                ('A01', 'Anchor 01', 1, 1, 2.5),
                ('A02', 'Anchor 02', 9, 1, 2.5),
                ('A03', 'Anchor 03', 9, 9, 2.5),
                ('A04', 'Anchor 04', 1, 9, 2.5)
            ON CONFLICT (anchor_id) DO NOTHING;
        """)

        # ----------------------------------------------------
        # ZONES
        # ----------------------------------------------------

        conn.execute("""
            INSERT INTO zones(
                zone_id,
                name,
                min_x,
                min_y,
                max_x,
                max_y,
                alert_enabled
            )
            VALUES
                ('ZONE01', 'Restricted Area', 6, 6, 9, 9, TRUE),
                ('ZONE02', 'Production Area', 1, 1, 5, 5, TRUE)
            ON CONFLICT (zone_id) DO NOTHING;
        """)


# ============================================================
# FASTAPI LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # PostgreSQL may need a moment to start
    # when Docker is used.

    last_error = None

    for _ in range(20):

        try:

            init_db()

            last_error = None

            break

        except Exception as exc:

            last_error = exc

            await asyncio.sleep(1)

    if last_error:
        raise last_error

    yield


# ============================================================
# CREATE FASTAPI APP
# ============================================================

app = FastAPI(
    title="UWB Indoor Localization Backend",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# CORS
# ============================================================
#
# This allows the frontend running on port 5500
# to communicate with the backend running on port 8000.
#

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():

    with get_conn() as conn:

        conn.execute("SELECT 1")

    return {
        "status": "ok",
        "database": "connected"
    }


# ============================================================
# TAGS
# ============================================================

@app.get("/api/tags")
def get_tags():

    with get_conn() as conn:

        return conn.execute("""
            SELECT
                tag_id,
                name,
                tag_type,
                status,
                created_at
            FROM tags
            ORDER BY tag_id
        """).fetchall()


@app.post("/api/tags")
def create_tag(tag: TagIn):

    with get_conn() as conn:

        exists = conn.execute(
            "SELECT tag_id FROM tags WHERE tag_id = %s",
            (tag.tag_id,)
        ).fetchone()

        if exists:

            raise HTTPException(
                status_code=409,
                detail="Tag already exists"
            )

        row = conn.execute("""
            INSERT INTO tags(
                tag_id,
                name,
                tag_type,
                status
            )
            VALUES(
                %s,
                %s,
                %s,
                %s
            )
            RETURNING
                tag_id,
                name,
                tag_type,
                status,
                created_at
        """, (
            tag.tag_id,
            tag.name,
            tag.tag_type,
            tag.status
        )).fetchone()

    return row


@app.put("/api/tags/{tag_id}")
def update_tag(
    tag_id: str,
    tag: TagIn
):

    if tag.tag_id != tag_id:

        raise HTTPException(
            status_code=400,
            detail="tag_id cannot be changed"
        )

    with get_conn() as conn:

        row = conn.execute("""
            UPDATE tags

            SET
                name = %s,
                tag_type = %s,
                status = %s

            WHERE tag_id = %s

            RETURNING
                tag_id,
                name,
                tag_type,
                status,
                created_at
        """, (
            tag.name,
            tag.tag_type,
            tag.status,
            tag_id
        )).fetchone()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Tag not found"
        )

    return row


@app.delete("/api/tags/{tag_id}")
def delete_tag(tag_id: str):

    with get_conn() as conn:

        row = conn.execute(
            """
            DELETE FROM tags
            WHERE tag_id = %s
            RETURNING tag_id
            """,
            (tag_id,)
        ).fetchone()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Tag not found"
        )

    return {
        "deleted": row["tag_id"]
    }


# ============================================================
# ANCHORS
# ============================================================

@app.get("/api/anchors")
def get_anchors():

    with get_conn() as conn:

        return conn.execute("""
            SELECT
                anchor_id,
                name,
                x,
                y,
                z
            FROM anchors
            ORDER BY anchor_id
        """).fetchall()


# ============================================================
# ZONES
# ============================================================

@app.get("/api/zones")
def get_zones():

    with get_conn() as conn:

        return conn.execute("""
            SELECT
                zone_id,
                name,
                min_x,
                min_y,
                max_x,
                max_y,
                alert_enabled
            FROM zones
            ORDER BY zone_id
        """).fetchall()


@app.post("/api/zones")
def create_zone(zone: ZoneIn):

    if (
        zone.min_x >= zone.max_x
        or
        zone.min_y >= zone.max_y
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid zone coordinates"
        )

    with get_conn() as conn:

        exists = conn.execute(
            "SELECT zone_id FROM zones WHERE zone_id=%s",
            (zone.zone_id,)
        ).fetchone()

        if exists:

            raise HTTPException(
                status_code=409,
                detail="Zone already exists"
            )

        row = conn.execute("""
            INSERT INTO zones(
                zone_id,
                name,
                min_x,
                min_y,
                max_x,
                max_y,
                alert_enabled
            )
            VALUES(
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            RETURNING
                zone_id,
                name,
                min_x,
                min_y,
                max_x,
                max_y,
                alert_enabled
        """, (
            zone.zone_id,
            zone.name,
            zone.min_x,
            zone.min_y,
            zone.max_x,
            zone.max_y,
            zone.alert_enabled
        )).fetchone()

    return row


# ============================================================
# GEOFENCE CALCULATION
# ============================================================

def inside_zone(
    x: float,
    y: float,
    zone: dict
) -> bool:

    return (
        zone["min_x"] <= x <= zone["max_x"]
        and
        zone["min_y"] <= y <= zone["max_y"]
    )


# ============================================================
# RECEIVE UWB POSITION
# ============================================================

@app.post("/api/positions")
async def receive_position(
    position: PositionIn
):

    with get_conn() as conn:

        # ----------------------------------------------------
        # Check tag
        # ----------------------------------------------------

        tag = conn.execute(
            """
            SELECT tag_id
            FROM tags
            WHERE tag_id = %s
            """,
            (position.tag_id,)
        ).fetchone()

        if not tag:

            raise HTTPException(
                status_code=404,
                detail="Unknown tag_id"
            )

        # ----------------------------------------------------
        # Timestamp
        # ----------------------------------------------------

        ts = (
            position.timestamp
            or datetime.now(timezone.utc)
        )

        # ----------------------------------------------------
        # Store position
        # ----------------------------------------------------

        row = conn.execute("""
            INSERT INTO positions(
                tag_id,
                timestamp,
                x,
                y,
                z,
                accuracy,
                source
            )
            VALUES(
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            RETURNING
                id,
                tag_id,
                timestamp,
                x,
                y,
                z,
                accuracy,
                source
        """, (
            position.tag_id,
            ts,
            position.x,
            position.y,
            position.z,
            position.accuracy,
            position.source
        )).fetchone()

        # ----------------------------------------------------
        # Get active zones
        # ----------------------------------------------------

        zones = conn.execute("""
            SELECT
                zone_id,
                name,
                min_x,
                min_y,
                max_x,
                max_y,
                alert_enabled
            FROM zones
            WHERE alert_enabled = TRUE
        """).fetchall()

        # ----------------------------------------------------
        # Detect ENTER / EXIT
        # ----------------------------------------------------

        events = []

        for zone in zones:

            key = (
                position.tag_id,
                zone["zone_id"]
            )

            previous = app.state.zone_state.get(
                key,
                False
            )

            current = inside_zone(
                position.x,
                position.y,
                zone
            )

            if current != previous:

                event = (
                    "ENTER"
                    if current
                    else "EXIT"
                )

                event_row = conn.execute("""
                    INSERT INTO geofence_events(
                        tag_id,
                        zone_id,
                        event,
                        timestamp
                    )
                    VALUES(
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    RETURNING
                        id,
                        tag_id,
                        zone_id,
                        event,
                        timestamp
                """, (
                    position.tag_id,
                    zone["zone_id"],
                    event,
                    ts
                )).fetchone()

                events.append({
                    **event_row,
                    "zone_name": zone["name"]
                })

            app.state.zone_state[key] = current

    # --------------------------------------------------------
    # Send real-time WebSocket message
    # --------------------------------------------------------

    payload = {
        "type": "position",
        "position": row,
        "events": events
    }

    await manager.broadcast(payload)

    return payload


# ============================================================
# LATEST POSITIONS
# ============================================================

@app.get("/api/positions/latest")
def latest_positions():

    with get_conn() as conn:

        rows = conn.execute("""
            SELECT DISTINCT ON (p.tag_id)

                p.id,
                p.tag_id,

                t.name,
                t.tag_type,
                t.status,

                p.timestamp,

                p.x,
                p.y,
                p.z,

                p.accuracy,
                p.source

            FROM positions p

            JOIN tags t
            ON t.tag_id = p.tag_id

            ORDER BY
                p.tag_id,
                p.timestamp DESC,
                p.id DESC
        """).fetchall()

    return rows


# ============================================================
# POSITION HISTORY
# ============================================================

@app.get("/api/positions/history/{tag_id}")
def position_history(
    tag_id: str,
    limit: int = 200
):

    limit = max(
        1,
        min(limit, 1000)
    )

    with get_conn() as conn:

        rows = conn.execute("""
            SELECT
                id,
                tag_id,
                timestamp,
                x,
                y,
                z,
                accuracy,
                source

            FROM positions

            WHERE tag_id = %s

            ORDER BY
                timestamp DESC,
                id DESC

            LIMIT %s
        """, (
            tag_id,
            limit
        )).fetchall()

    # Oldest → newest
    return list(reversed(rows))


# ============================================================
# GEOFENCE EVENTS
# ============================================================

@app.get("/api/geofence-events")
def geofence_events(
    limit: int = 50
):

    limit = max(
        1,
        min(limit, 500)
    )

    with get_conn() as conn:

        return conn.execute("""
            SELECT

                e.id,
                e.tag_id,
                t.name AS tag_name,

                e.zone_id,
                z.name AS zone_name,

                e.event,
                e.timestamp

            FROM geofence_events e

            JOIN tags t
            ON t.tag_id = e.tag_id

            JOIN zones z
            ON z.zone_id = e.zone_id

            ORDER BY
                e.timestamp DESC,
                e.id DESC

            LIMIT %s
        """, (limit,)).fetchall()


# ============================================================
# WEBSOCKET
# ============================================================

@app.websocket("/ws/live")
async def websocket_live(
    websocket: WebSocket
):

    await manager.connect(websocket)

    try:

        while True:

            # Browser does not need to send data.
            # This keeps the connection alive.

            await websocket.receive_text()

    except WebSocketDisconnect:

        manager.disconnect(websocket)

    except Exception:

        manager.disconnect(websocket)


# ============================================================
# APPLICATION STATE
# ============================================================

app.state.zone_state = {}


# ============================================================
# SERVE FRONTEND
# ============================================================

# This allows FastAPI to serve the frontend directly.
#
# Later you can simply open:
#
# http://127.0.0.1:8000
#
# instead of running a separate frontend server.

app.mount(
    "/",
    StaticFiles(
        directory=FRONTEND_DIR,
        html=True
    ),
    name="frontend"
)