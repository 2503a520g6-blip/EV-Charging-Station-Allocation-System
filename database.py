"""
EV Charging Station Allocation System - Database Management & Seeder
Supports SQLite locally (ev_charging.db) and PostgreSQL in production (Render).
"""

import os
import sqlite3
import hashlib
from datetime import datetime, timedelta

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ev_charging.db')
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# Normalize Render postgres:// to postgresql:// if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def is_postgres():
    return bool(DATABASE_URL and DATABASE_URL.startswith("postgresql://"))

def hash_password(password: str) -> str:
    """Secure SHA-256 password hashing."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

class DBWrapper:
    """Unified wrapper supporting both SQLite and PostgreSQL connections & queries."""
    
    def __init__(self):
        self.is_pg = is_postgres()
        self._conn = None
        self._cursor = None

    def __enter__(self):
        if self.is_pg:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            self._conn = psycopg2.connect(DATABASE_URL)
            self._cursor = self._conn.cursor(cursor_factory=RealDictCursor)
        else:
            self._conn = sqlite3.connect(DB_FILE)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._cursor = self._conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if self._conn:
                self._conn.rollback()
        else:
            if self._conn:
                self._conn.commit()
        if self._cursor:
            self._cursor.close()
        if self._conn:
            self._conn.close()

    def execute(self, query: str, params=None):
        if params is None:
            params = ()
        if self.is_pg:
            # Convert SQLite '?' placeholders to PostgreSQL '%s'
            pg_query = query.replace('?', '%s')
            # Handle SQLite INSERT OR IGNORE -> PostgreSQL ON CONFLICT DO NOTHING
            if "INSERT OR IGNORE" in pg_query:
                pg_query = pg_query.replace("INSERT OR IGNORE INTO users", "INSERT INTO users")
                if "ON CONFLICT" not in pg_query:
                    pg_query = pg_query + " ON CONFLICT (username) DO NOTHING"
            self._cursor.execute(pg_query, params)
        else:
            self._cursor.execute(query, params)
        return self._cursor

    def executemany(self, query: str, param_list):
        if self.is_pg:
            pg_query = query.replace('?', '%s')
            if "INSERT OR IGNORE" in pg_query:
                pg_query = pg_query.replace("INSERT OR IGNORE INTO users", "INSERT INTO users")
                if "ON CONFLICT" not in pg_query:
                    pg_query = pg_query + " ON CONFLICT (username) DO NOTHING"
            self._cursor.executemany(pg_query, param_list)
        else:
            self._cursor.executemany(query, param_list)
        return self._cursor

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [dict(r) for r in rows]

    @property
    def lastrowid(self):
        if self.is_pg:
            return None
        return self._cursor.lastrowid

def get_db():
    return DBWrapper()

def init_db(force_reseed=False):
    """Initializes tables and seeds initial data if empty."""
    with get_db() as db:
        if db.is_pg:
            if force_reseed:
                db.execute("DROP TABLE IF EXISTS reservations CASCADE")
                db.execute("DROP TABLE IF EXISTS slots CASCADE")
                db.execute("DROP TABLE IF EXISTS stations CASCADE")
                db.execute("DROP TABLE IF EXISTS users CASCADE")

            db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(150) NOT NULL,
                email VARCHAR(150) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'user',
                vehicle_model VARCHAR(100),
                vehicle_plate VARCHAR(50),
                preferred_connector VARCHAR(50) DEFAULT 'CCS2',
                battery_capacity_kwh REAL DEFAULT 50.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            db.execute("""
            CREATE TABLE IF NOT EXISTS stations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                address VARCHAR(255) NOT NULL,
                city VARCHAR(100) NOT NULL,
                zone VARCHAR(100) NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                total_slots INTEGER NOT NULL,
                power_kw REAL NOT NULL,
                connector_types VARCHAR(150) NOT NULL,
                price_per_kwh REAL NOT NULL,
                operator VARCHAR(100) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            db.execute("""
            CREATE TABLE IF NOT EXISTS slots (
                id SERIAL PRIMARY KEY,
                station_id INTEGER NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
                slot_number INTEGER NOT NULL,
                slot_type VARCHAR(100) NOT NULL,
                power_kw REAL NOT NULL,
                connector_type VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'Available',
                vehicle_number VARCHAR(50),
                current_reservation_id INTEGER
            )
            """)

            db.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id SERIAL PRIMARY KEY,
                reservation_code VARCHAR(100) UNIQUE NOT NULL,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                station_id INTEGER NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
                slot_id INTEGER NOT NULL REFERENCES slots(id) ON DELETE CASCADE,
                vehicle_model VARCHAR(100) NOT NULL,
                vehicle_plate VARCHAR(50) NOT NULL,
                connector_type VARCHAR(50) NOT NULL,
                charging_speed_kw REAL NOT NULL,
                start_time VARCHAR(50) NOT NULL,
                duration_hours REAL NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'Active',
                estimated_energy_kwh REAL NOT NULL,
                estimated_cost REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        else:
            if force_reseed:
                db.execute("DROP TABLE IF EXISTS reservations")
                db.execute("DROP TABLE IF EXISTS slots")
                db.execute("DROP TABLE IF EXISTS stations")
                db.execute("DROP TABLE IF EXISTS users")

            db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                vehicle_model TEXT,
                vehicle_plate TEXT,
                preferred_connector TEXT DEFAULT 'CCS2',
                battery_capacity_kwh REAL DEFAULT 50.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            db.execute("""
            CREATE TABLE IF NOT EXISTS stations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                city TEXT NOT NULL,
                zone TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                total_slots INTEGER NOT NULL,
                power_kw REAL NOT NULL,
                connector_types TEXT NOT NULL,
                price_per_kwh REAL NOT NULL,
                operator TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            db.execute("""
            CREATE TABLE IF NOT EXISTS slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id INTEGER NOT NULL,
                slot_number INTEGER NOT NULL,
                slot_type TEXT NOT NULL,
                power_kw REAL NOT NULL,
                connector_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Available',
                vehicle_number TEXT,
                current_reservation_id INTEGER,
                FOREIGN KEY (station_id) REFERENCES stations(id) ON DELETE CASCADE
            )
            """)

            db.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reservation_code TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                station_id INTEGER NOT NULL,
                slot_id INTEGER NOT NULL,
                vehicle_model TEXT NOT NULL,
                vehicle_plate TEXT NOT NULL,
                connector_type TEXT NOT NULL,
                charging_speed_kw REAL NOT NULL,
                start_time TEXT NOT NULL,
                duration_hours REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active',
                estimated_energy_kwh REAL NOT NULL,
                estimated_cost REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (station_id) REFERENCES stations(id) ON DELETE CASCADE,
                FOREIGN KEY (slot_id) REFERENCES slots(id) ON DELETE CASCADE
            )
            """)

    # Check station count and seed if needed
    with get_db() as db:
        db.execute("SELECT COUNT(*) as count FROM stations")
        row = db.fetchone()
        count = row['count'] if row else 0

        if count == 0 or force_reseed:
            seed_sample_data()

def seed_sample_data():
    """Seeds rich sample stations, slots, users, and reservations."""
    with get_db() as db:
        # 1. Users
        users_data = [
            ('admin', hash_password('admin123'), 'System Administrator', 'admin@evcharge.org', 'admin', 'Tesla Model 3', 'EV-ADM-001', 'CCS2', 75.0),
            ('alex_ev', hash_password('user123'), 'Alex Rivera', 'alex.rivera@example.com', 'user', 'Hyundai Ioniq 5', 'KA-01-EV-4421', 'CCS2', 72.6),
            ('sarah_k', hash_password('user123'), 'Sarah Koenig', 'sarah.k@example.com', 'user', 'Tata Nexon EV Max', 'DL-04-EV-8890', 'CCS2', 40.5),
            ('david_lee', hash_password('user123'), 'David Lee', 'david.lee@example.com', 'user', 'MG ZS EV', 'MH-02-EV-1902', 'CCS2', 50.3),
            ('priya_sharma', hash_password('user123'), 'Priya Sharma', 'priya.s@example.com', 'user', 'Nissan Leaf', 'TN-07-EV-3114', 'CHAdeMO', 40.0),
        ]

        for user in users_data:
            db.execute("""
            INSERT OR IGNORE INTO users (username, password_hash, full_name, email, role, vehicle_model, vehicle_plate, preferred_connector, battery_capacity_kwh)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, user)

        # 2. 12 Sample Stations
        stations_data = [
            ("Cyber City Tech Hub", "Plot 14, Electronics City Phase 1", "Bengaluru", "South Sector", 12.8452, 77.6602, 6, 120.0, "CCS2, Type 2, CHAdeMO", 15.50, "Tata Power EZ", "Active"),
            ("Downtown Central Metro", "Station Road, Near MG Road Metro", "Bengaluru", "Central Zone", 12.9752, 77.6062, 8, 150.0, "CCS2, Type 2", 18.00, "ChargeZone Super", "Active"),
            ("Airport Terminal 2 Express", "T2 Forecourt, Kempegowda Airport", "Bengaluru", "North Sector", 13.2008, 77.7088, 6, 240.0, "CCS2, CHAdeMO", 21.00, "Jio-bp pulse", "Active"),
            ("Green Valley Eco Park", "Eco Boulevard, HSR Layout Sector 2", "Bengaluru", "South-East", 12.9121, 77.6446, 4, 50.0, "CCS2, Type 2", 13.50, "Statiq Green", "Active"),
            ("Horizon Galleria Mall", "Level B2, Bannerghatta Main Road", "Bengaluru", "South Sector", 12.8985, 77.5998, 6, 60.0, "CCS2, Type 2", 16.00, "Zeon Charging", "Active"),
            ("Highway Rest Stop KM 42", "Bengaluru-Mysuru Expressway Toll Plaza", "Ramanagara", "Highway Zone", 12.7214, 77.2831, 6, 180.0, "CCS2, CHAdeMO", 19.50, "Shell Recharge", "Active"),
            ("North Suburb Community Hub", "Hebbal Outer Ring Road, Near Flyover", "Bengaluru", "North Sector", 13.0358, 77.5970, 4, 30.0, "Type 2, CCS2", 12.00, "Tata Power EZ", "Active"),
            ("South University Campus", "Kengeri Satellite Town, Tech Block", "Bengaluru", "West Sector", 12.9150, 77.4820, 4, 50.0, "CCS2, Type 2", 14.00, "Statiq Clean", "Active"),
            ("Harbor View Financial Park", "Financial District, Whitefield Main Rd", "Bengaluru", "East Sector", 12.9698, 77.7499, 6, 120.0, "CCS2, Type 2", 17.50, "ChargeZone", "Active"),
            ("West Hills Residential Grid", "8th Main, Malleshwaram West", "Bengaluru", "North-West", 13.0031, 77.5685, 4, 22.0, "Type 2", 11.50, "BESCOM EV Hub", "Active"),
            ("East Gateway Logistics Center", "Hosakote Industrial Area", "Bengaluru", "East Outer", 13.0715, 77.7981, 6, 150.0, "CCS2, CHAdeMO", 16.50, "Jio-bp pulse", "Active"),
            ("Grand Central Railway Hub", "Krantivira Sangolli Rayanna Station", "Bengaluru", "Central Zone", 12.9781, 77.5694, 6, 100.0, "CCS2, Type 2", 15.00, "Zeon Fast", "Active")
        ]

        station_ids = []
        for station in stations_data:
            if db.is_pg:
                db.execute("""
                INSERT INTO stations (name, address, city, zone, latitude, longitude, total_slots, power_kw, connector_types, price_per_kwh, operator, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """, station)
                station_id = db.fetchone()['id']
            else:
                db.execute("""
                INSERT INTO stations (name, address, city, zone, latitude, longitude, total_slots, power_kw, connector_types, price_per_kwh, operator, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, station)
                station_id = db.lastrowid
            station_ids.append(station_id)

            total_slots = station[6]
            power_kw = station[7]
            connectors = [c.strip() for c in station[8].split(',')]

            for s_idx in range(1, total_slots + 1):
                conn_type = connectors[(s_idx - 1) % len(connectors)]
                slot_type = "Ultra Fast DC" if power_kw >= 150 else ("Fast DC" if power_kw >= 50 else "Standard AC")

                status = 'Available'
                vehicle_plate = None
                if s_idx == 1 and station_id in [1, 2, 5, 6, 9]:
                    status = 'Occupied'
                    vehicle_plate = f"EV-{100 + station_id * 7}-ACT"
                elif s_idx == 2 and station_id in [2, 3, 6, 10]:
                    status = 'Occupied'
                    vehicle_plate = f"EV-{200 + station_id * 5}-PWR"
                elif s_idx == 3 and station_id in [1, 3]:
                    status = 'Reserved'
                    vehicle_plate = f"EV-{300 + station_id * 3}-RSV"
                elif s_idx == total_slots and station_id == 6:
                    status = 'Maintenance'

                db.execute("""
                INSERT INTO slots (station_id, slot_number, slot_type, power_kw, connector_type, status, vehicle_number)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (station_id, s_idx, slot_type, power_kw, conn_type, status, vehicle_plate))

        # 3. Reservations - Enriched sample with diverse states and realistic energy / tariffs
        now = datetime.now()
        sample_reservations = [
            ("RES-2026-9041", 2, 1, 3, "Hyundai Ioniq 5", "KA-01-EV-4421", "CCS2", 120.0, (now - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M"), 1.0, "Active", 35.0, 542.50),
            ("RES-2026-9042", 3, 2, 1, "Tata Nexon EV Max", "DL-04-EV-8890", "CCS2", 150.0, (now - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M"), 0.75, "Active", 28.5, 513.00),
            ("RES-2026-9043", 4, 3, 3, "MG ZS EV", "MH-02-EV-1902", "CCS2", 240.0, (now + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M"), 1.0, "Pending", 38.0, 798.00),
            ("RES-2026-9044", 5, 6, 1, "Nissan Leaf", "TN-07-EV-3114", "CHAdeMO", 180.0, (now - timedelta(minutes=35)).strftime("%Y-%m-%d %H:%M"), 0.5, "Active", 22.0, 429.00),
            ("RES-2026-9039", 2, 5, 2, "Hyundai Ioniq 5", "KA-01-EV-4421", "CCS2", 60.0, (now - timedelta(days=1, hours=3)).strftime("%Y-%m-%d %H:%M"), 1.5, "Completed", 45.0, 720.00),
            ("RES-2026-9035", 3, 4, 1, "Tata Nexon EV Max", "DL-04-EV-8890", "Type 2", 50.0, (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M"), 1.0, "Completed", 30.0, 405.00),
            ("RES-2026-9031", 4, 9, 1, "MG ZS EV", "MH-02-EV-1902", "CCS2", 120.0, (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M"), 1.25, "Completed", 42.0, 735.00),
            ("RES-2026-9028", 5, 12, 2, "Nissan Leaf", "TN-07-EV-3114", "CCS2", 100.0, (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M"), 0.75, "Completed", 26.0, 390.00),
            ("RES-2026-9020", 2, 2, 2, "Hyundai Ioniq 5", "KA-01-EV-4421", "CCS2", 150.0, (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M"), 1.0, "Cancelled", 0.0, 0.00),
        ]

        for res in sample_reservations:
            db.execute("""
            INSERT INTO reservations (reservation_code, user_id, station_id, slot_id, vehicle_model, vehicle_plate, connector_type, charging_speed_kw, start_time, duration_hours, status, estimated_energy_kwh, estimated_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, res)

if __name__ == '__main__':
    print("Initializing EV Charging Station Database...")
    init_db(force_reseed=True)
    print("Database successfully initialized!")
