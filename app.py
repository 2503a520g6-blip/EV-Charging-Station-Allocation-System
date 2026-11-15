"""
EV Charging Station Allocation System - Backend Server
Modern, responsive, lightweight Python Flask API.
Supports SQLite locally and PostgreSQL on Render.
"""

import os
import math
import random
import string
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from database import get_db, init_db, hash_password, is_postgres

# Create Flask app. Serve static files from workspace root.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
app.config['JSON_SORT_KEYS'] = False

# Ensure DB exists and is seeded on startup
try:
    init_db(force_reseed=False)
except Exception as e:
    print(f"[WARN] Database initialization notice: {e}")

# ----------------- CORS CONFIGURATION ----------------- #

@app.after_request
def add_cors_headers(response):
    """Configures CORS headers to allow GitHub Pages and local development."""
    allowed_origin = os.environ.get('CORS_ALLOWED_ORIGIN', '*')
    response.headers['Access-Control-Allow-Origin'] = allowed_origin
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

@app.route('/api/<path:subpath>', methods=['OPTIONS'])
def handle_options(subpath):
    """Handles CORS preflight requests."""
    return ('', 204)

# ----------------- HAVERSINE UTILITY ----------------- #

def calculate_haversine(lat1, lon1, lat2, lon2):
    """Calculates great-circle distance between two coordinates in kilometers."""
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except (ValueError, TypeError):
        return 0.0

    R = 6371.0  # Earth's radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)

def generate_reservation_code():
    chars = string.ascii_uppercase + string.digits
    rand_str = ''.join(random.choices(chars, k=4))
    year = datetime.now().year
    return f"RES-{year}-{rand_str}"

# ----------------- WEB PAGES & STATIC ASSETS ----------------- #

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    target = os.path.join(BASE_DIR, filename)
    if os.path.exists(target) and os.path.isfile(target):
        return send_from_directory(BASE_DIR, filename)
    return jsonify({"error": "File not found"}), 404

# ----------------- HEALTH CHECK ----------------- #

@app.route('/api/health', methods=['GET'])
def health_check():
    db_type = "postgresql" if is_postgres() else "sqlite"
    station_count = 0
    try:
        with get_db() as db:
            db.execute("SELECT COUNT(*) as cnt FROM stations")
            r = db.fetchone()
            station_count = r['cnt'] if r else 0
    except Exception as e:
        return jsonify({"status": "error", "database": db_type, "message": str(e)}), 500

    return jsonify({
        "status": "healthy",
        "service": "EV Charging Station Allocation System",
        "database": db_type,
        "stations_loaded": station_count,
        "timestamp": datetime.now().isoformat()
    })

# ----------------- DASHBOARD & STATS ----------------- #

@app.route('/api/stats', methods=['GET'])
def get_stats():
    with get_db() as db:
        db.execute("SELECT COUNT(*) as count FROM stations")
        total_stations = db.fetchone()['count']

        db.execute("SELECT COUNT(*) as count FROM slots")
        total_slots = db.fetchone()['count']

        db.execute("SELECT COUNT(*) as count FROM slots WHERE status = 'Available'")
        available_slots = db.fetchone()['count']

        db.execute("SELECT COUNT(*) as count FROM slots WHERE status = 'Occupied'")
        occupied_slots = db.fetchone()['count']

        db.execute("SELECT COUNT(*) as count FROM slots WHERE status = 'Reserved'")
        reserved_slots = db.fetchone()['count']

        db.execute("SELECT COUNT(*) as count FROM slots WHERE status = 'Maintenance'")
        maintenance_slots = db.fetchone()['count']

        db.execute("SELECT COUNT(*) as count FROM reservations WHERE status = 'Active'")
        active_sessions = db.fetchone()['count']

        db.execute("SELECT COUNT(*) as count FROM reservations WHERE status = 'Pending'")
        pending_reservations = db.fetchone()['count']

        # Total Energy Consumed (kWh) from real reservations
        db.execute("""
        SELECT COALESCE(SUM(estimated_energy_kwh), 0) as total_energy,
               COALESCE(SUM(estimated_cost), 0) as total_revenue
        FROM reservations 
        WHERE status IN ('Active', 'Completed')
        """)
        energy_rev = db.fetchone()
        total_energy_kwh = round(float(energy_rev['total_energy'] or 0.0), 1)
        total_revenue = round(float(energy_rev['total_revenue'] or 0.0), 2)

        # Stations with at least 1 available slot
        db.execute("""
        SELECT COUNT(DISTINCT station_id) as count
        FROM slots 
        WHERE status = 'Available'
        """)
        r_avail = db.fetchone()
        available_stations = r_avail['count'] if r_avail else 0

        # Occupied / Full stations: stations with 0 available slots
        db.execute("""
        SELECT s.id, COUNT(sl.id) as tot,
               SUM(CASE WHEN sl.status = 'Available' THEN 1 ELSE 0 END) as free_sl
        FROM stations s
        JOIN slots sl ON s.id = sl.station_id
        GROUP BY s.id
        """)
        station_slot_rows = db.fetchall()
        occupied_stations = sum(1 for row in station_slot_rows if (row['free_sl'] or 0) == 0)

        # Zone stats for bar chart
        db.execute("""
        SELECT s.zone, COUNT(sl.id) as total_zone_slots,
               SUM(CASE WHEN sl.status = 'Available' THEN 1 ELSE 0 END) as free_slots
        FROM stations s
        JOIN slots sl ON s.id = sl.station_id
        GROUP BY s.zone
        ORDER BY total_zone_slots DESC
        LIMIT 6
        """)
        zone_stats = db.fetchall()

    return jsonify({
        "success": True,
        "total_stations": total_stations,
        "available_stations": available_stations,
        "occupied_stations": occupied_stations,
        "total_slots": total_slots,
        "available_slots": available_slots,
        "occupied_slots": occupied_slots,
        "reserved_slots": reserved_slots,
        "maintenance_slots": maintenance_slots,
        "active_sessions": active_sessions,
        "pending_reservations": pending_reservations,
        "total_energy_kwh": total_energy_kwh,
        "total_revenue": total_revenue,
        "slot_distribution": {
            "available": available_slots,
            "occupied": occupied_slots,
            "reserved": reserved_slots,
            "maintenance": maintenance_slots
        },
        "zone_stats": zone_stats
    })

# ----------------- ADVANCED ANALYTICS FOR CHARTS ----------------- #

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Returns aggregated real-data datasets for the 7 dashboard analytical charts."""
    with get_db() as db:
        # 1. Station Availability
        db.execute("""
        SELECT s.id,
               SUM(CASE WHEN sl.status = 'Available' THEN 1 ELSE 0 END) as free_count
        FROM stations s
        LEFT JOIN slots sl ON s.id = sl.station_id
        GROUP BY s.id
        """)
        st_rows = db.fetchall()
        total_st = len(st_rows)
        avail_st = sum(1 for r in st_rows if (r['free_count'] or 0) > 0)
        occ_st = total_st - avail_st

        # 2. Slot Distribution
        db.execute("""
        SELECT 
            SUM(CASE WHEN status = 'Available' THEN 1 ELSE 0 END) as avail_cnt,
            SUM(CASE WHEN status = 'Occupied' THEN 1 ELSE 0 END) as occ_cnt,
            SUM(CASE WHEN status = 'Reserved' THEN 1 ELSE 0 END) as res_cnt,
            SUM(CASE WHEN status = 'Maintenance' THEN 1 ELSE 0 END) as maint_cnt,
            COUNT(*) as total_cnt
        FROM slots
        """)
        slot_row = db.fetchone()

        # 3. Stations & Slots by Location Zone
        db.execute("""
        SELECT s.zone,
               COUNT(DISTINCT s.id) as station_count,
               COUNT(sl.id) as total_slots,
               SUM(CASE WHEN sl.status = 'Available' THEN 1 ELSE 0 END) as free_slots,
               SUM(CASE WHEN sl.status = 'Occupied' THEN 1 ELSE 0 END) as occupied_slots
        FROM stations s
        LEFT JOIN slots sl ON s.id = sl.station_id
        GROUP BY s.zone
        ORDER BY total_slots DESC
        """)
        location_data = db.fetchall()

        # 4. Daily Charging Sessions (grouped by start_time date prefix)
        db.execute("""
        SELECT SUBSTR(start_time, 1, 10) as session_date,
               COUNT(*) as sessions_count,
               ROUND(SUM(estimated_energy_kwh), 1) as total_energy,
               ROUND(SUM(estimated_cost), 2) as total_revenue
        FROM reservations
        GROUP BY session_date
        ORDER BY session_date ASC
        LIMIT 7
        """)
        daily_sessions = db.fetchall()

        # 5. Energy Consumption & Revenue by Operator
        db.execute("""
        SELECT s.operator,
               COUNT(r.id) as booking_count,
               ROUND(SUM(r.estimated_energy_kwh), 1) as energy_kwh,
               ROUND(SUM(r.estimated_cost), 2) as revenue
        FROM reservations r
        JOIN stations s ON r.station_id = s.id
        WHERE r.status IN ('Active', 'Completed')
        GROUP BY s.operator
        ORDER BY energy_kwh DESC
        """)
        energy_by_operator = db.fetchall()

        # 6. Booking Statistics by Status
        db.execute("""
        SELECT status, COUNT(*) as count
        FROM reservations
        GROUP BY status
        """)
        booking_status_rows = db.fetchall()
        booking_stats = {r['status']: r['count'] for r in booking_status_rows}

        # 7. Station Utilization Rate (%) = ((total_slots - free_slots) / total_slots) * 100
        db.execute("""
        SELECT s.id, s.name, s.operator, s.power_kw,
               COUNT(sl.id) as total_slots,
               SUM(CASE WHEN sl.status = 'Occupied' OR sl.status = 'Reserved' THEN 1 ELSE 0 END) as busy_slots
        FROM stations s
        JOIN slots sl ON s.id = sl.station_id
        GROUP BY s.id, s.name, s.operator, s.power_kw
        ORDER BY busy_slots DESC, total_slots DESC
        LIMIT 8
        """)
        util_rows = db.fetchall()
        station_utilization = []
        for u in util_rows:
            tot = u['total_slots'] or 1
            busy = u['busy_slots'] or 0
            rate = round((busy / float(tot)) * 100, 1)
            station_utilization.append({
                "station_id": u['id'],
                "name": u['name'],
                "operator": u['operator'],
                "power_kw": u['power_kw'],
                "total_slots": tot,
                "busy_slots": busy,
                "utilization_pct": rate
            })

    return jsonify({
        "success": True,
        "station_availability": {
            "available": avail_st,
            "occupied": occ_st,
            "total": total_st
        },
        "slot_distribution": {
            "available": int(slot_row['avail_cnt'] or 0),
            "occupied": int(slot_row['occ_cnt'] or 0),
            "reserved": int(slot_row['res_cnt'] or 0),
            "maintenance": int(slot_row['maint_cnt'] or 0),
            "total": int(slot_row['total_cnt'] or 0)
        },
        "location_distribution": location_data,
        "daily_sessions": daily_sessions,
        "energy_by_operator": energy_by_operator,
        "booking_stats": booking_stats,
        "station_utilization": station_utilization
    })

# ----------------- STATIONS API ----------------- #

@app.route('/api/stations', methods=['GET'])
def list_stations():
    search_query = request.args.get('q', '').strip().lower()
    connector_filter = request.args.get('connector', '').strip()
    status_filter = request.args.get('status', '').strip()
    zone_filter = request.args.get('zone', '').strip()
    user_lat = request.args.get('lat', type=float)
    user_lng = request.args.get('lng', type=float)

    with get_db() as db:
        query = """
        SELECT s.id, s.name, s.address, s.city, s.zone, s.latitude, s.longitude,
               s.total_slots, s.power_kw, s.connector_types, s.price_per_kwh, s.operator, s.status,
               COUNT(sl.id) as total_slots_count,
               SUM(CASE WHEN sl.status = 'Available' THEN 1 ELSE 0 END) as available_slots_count,
               SUM(CASE WHEN sl.status = 'Occupied' THEN 1 ELSE 0 END) as occupied_slots_count,
               SUM(CASE WHEN sl.status = 'Reserved' THEN 1 ELSE 0 END) as reserved_slots_count
        FROM stations s
        LEFT JOIN slots sl ON s.id = sl.station_id
        GROUP BY s.id, s.name, s.address, s.city, s.zone, s.latitude, s.longitude,
                 s.total_slots, s.power_kw, s.connector_types, s.price_per_kwh, s.operator, s.status
        ORDER BY s.id ASC
        """
        db.execute(query)
        rows = db.fetchall()

    stations = []
    for row in rows:
        st = dict(row)
        st['available_slots_count'] = int(st['available_slots_count'] or 0)
        st['occupied_slots_count'] = int(st['occupied_slots_count'] or 0)
        st['reserved_slots_count'] = int(st['reserved_slots_count'] or 0)
        st['total_slots_count'] = int(st['total_slots_count'] or st['total_slots'])

        # Calculate distance if user lat/lng provided
        if user_lat is not None and user_lng is not None:
            dist = calculate_haversine(user_lat, user_lng, st['latitude'], st['longitude'])
            st['distance_km'] = dist
            st['eta_mins'] = max(2, int(round((dist / 32.0) * 60)))
        else:
            st['distance_km'] = None
            st['eta_mins'] = None

        # Filter search query
        if search_query:
            combined = f"{st.get('name') or ''} {st.get('address') or ''} {st.get('city') or ''} {st.get('zone') or ''} {st.get('operator') or ''}".lower()
            if search_query not in combined:
                continue

        # Filter connector
        if connector_filter and connector_filter.lower() != 'all':
            if connector_filter.lower() not in (st.get('connector_types') or '').lower():
                continue

        # Filter status
        if status_filter and status_filter.lower() != 'all':
            if (st.get('status') or '').lower() != status_filter.lower():
                continue

        # Filter zone
        if zone_filter and zone_filter.lower() != 'all':
            if (st.get('zone') or '').lower() != zone_filter.lower():
                continue

        stations.append(st)

    # Sort by distance when coordinates are present
    if user_lat is not None and user_lng is not None:
        stations.sort(key=lambda x: x['distance_km'] if x['distance_km'] is not None else 9999)

    return jsonify({"success": True, "count": len(stations), "stations": stations})

@app.route('/api/stations/<int:station_id>', methods=['GET'])
def get_station(station_id):
    with get_db() as db:
        db.execute("SELECT * FROM stations WHERE id = ?", (station_id,))
        station = db.fetchone()
        if not station:
            return jsonify({"success": False, "message": "Station not found"}), 404

        db.execute("SELECT * FROM slots WHERE station_id = ? ORDER BY slot_number ASC", (station_id,))
        slots = db.fetchall()

    station['slots'] = slots
    return jsonify({"success": True, "station": station})

@app.route('/api/stations', methods=['POST'])
def create_station():
    data = request.json or {}
    name = str(data.get('name', '')).strip()
    address = str(data.get('address', '')).strip()
    city = str(data.get('city', 'Bengaluru')).strip()
    zone = str(data.get('zone', 'Metro Zone')).strip()
    
    try:
        latitude = float(data.get('latitude', 12.9716))
        longitude = float(data.get('longitude', 77.5946))
        total_slots = int(data.get('total_slots', 4))
        power_kw = float(data.get('power_kw', 50.0))
        price_per_kwh = float(data.get('price_per_kwh', 15.0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid numeric input values for coordinates, slots, power, or price"}), 400

    connector_types = str(data.get('connector_types', 'CCS2, Type 2')).strip()
    operator = str(data.get('operator', 'Independent EV Network')).strip()
    status = str(data.get('status', 'Active')).strip()

    if not name or not address:
        return jsonify({"success": False, "message": "Station name and address are required"}), 400

    with get_db() as db:
        if db.is_pg:
            db.execute("""
            INSERT INTO stations (name, address, city, zone, latitude, longitude, total_slots, power_kw, connector_types, price_per_kwh, operator, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """, (name, address, city, zone, latitude, longitude, total_slots, power_kw, connector_types, price_per_kwh, operator, status))
            station_id = db.fetchone()['id']
        else:
            db.execute("""
            INSERT INTO stations (name, address, city, zone, latitude, longitude, total_slots, power_kw, connector_types, price_per_kwh, operator, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, address, city, zone, latitude, longitude, total_slots, power_kw, connector_types, price_per_kwh, operator, status))
            station_id = db.lastrowid

        # Auto-create physical slots
        connectors = [c.strip() for c in connector_types.split(',')] if connector_types else ['CCS2']
        slot_type = "Ultra Fast DC" if power_kw >= 150 else ("Fast DC" if power_kw >= 50 else "Standard AC")

        for s_idx in range(1, total_slots + 1):
            conn_type = connectors[(s_idx - 1) % len(connectors)]
            db.execute("""
            INSERT INTO slots (station_id, slot_number, slot_type, power_kw, connector_type, status)
            VALUES (?, ?, ?, ?, ?, 'Available')
            """, (station_id, s_idx, slot_type, power_kw, conn_type))

    return jsonify({"success": True, "message": "Station created successfully", "station_id": station_id}), 201

@app.route('/api/stations/<int:station_id>', methods=['PUT'])
def update_station(station_id):
    data = request.json or {}
    with get_db() as db:
        db.execute("SELECT * FROM stations WHERE id = ?", (station_id,))
        station = db.fetchone()
        if not station:
            return jsonify({"success": False, "message": "Station not found"}), 404

        name = data.get('name', station['name'])
        address = data.get('address', station['address'])
        city = data.get('city', station['city'])
        zone = data.get('zone', station['zone'])
        try:
            latitude = float(data['latitude']) if 'latitude' in data and data['latitude'] != '' else station['latitude']
            longitude = float(data['longitude']) if 'longitude' in data and data['longitude'] != '' else station['longitude']
            power_kw = float(data['power_kw']) if 'power_kw' in data and data['power_kw'] != '' else station['power_kw']
            price_per_kwh = float(data['price_per_kwh']) if 'price_per_kwh' in data and data['price_per_kwh'] != '' else station['price_per_kwh']
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Invalid numeric value in update request"}), 400

        connector_types = data.get('connector_types', station['connector_types'])
        operator = data.get('operator', station['operator'])
        status = data.get('status', station['status'])

        db.execute("""
        UPDATE stations SET
            name = ?, address = ?, city = ?, zone = ?,
            latitude = ?, longitude = ?, power_kw = ?,
            connector_types = ?, price_per_kwh = ?,
            operator = ?, status = ?
        WHERE id = ?
        """, (name, address, city, zone, latitude, longitude, power_kw, connector_types, price_per_kwh, operator, status, station_id))

    return jsonify({"success": True, "message": "Station updated successfully"})

@app.route('/api/stations/<int:station_id>', methods=['DELETE'])
def delete_station(station_id):
    with get_db() as db:
        db.execute("SELECT id FROM stations WHERE id = ?", (station_id,))
        if not db.fetchone():
            return jsonify({"success": False, "message": "Station not found"}), 404

        # Cascading removal
        db.execute("DELETE FROM reservations WHERE station_id = ?", (station_id,))
        db.execute("DELETE FROM slots WHERE station_id = ?", (station_id,))
        db.execute("DELETE FROM stations WHERE id = ?", (station_id,))

    return jsonify({"success": True, "message": "Station and its slots removed successfully"})

# ----------------- SLOTS API ----------------- #

@app.route('/api/stations/<int:station_id>/slots', methods=['GET'])
def get_station_slots(station_id):
    with get_db() as db:
        db.execute("SELECT * FROM slots WHERE station_id = ? ORDER BY slot_number ASC", (station_id,))
        slots = db.fetchall()
    return jsonify({"success": True, "slots": slots})

@app.route('/api/slots/<int:slot_id>', methods=['PUT'])
def update_slot(slot_id):
    data = request.json or {}
    new_status = data.get('status')
    vehicle_number = data.get('vehicle_number', None)

    valid_statuses = ['Available', 'Occupied', 'Reserved', 'Maintenance']
    if new_status and new_status not in valid_statuses:
        return jsonify({"success": False, "message": f"Invalid status. Must be one of {valid_statuses}"}), 400

    with get_db() as db:
        db.execute("SELECT * FROM slots WHERE id = ?", (slot_id,))
        slot = db.fetchone()
        if not slot:
            return jsonify({"success": False, "message": "Slot not found"}), 404

        status_to_set = new_status if new_status else slot['status']
        veh_to_set = None if status_to_set == 'Available' else (vehicle_number or slot['vehicle_number'])

        db.execute("""
        UPDATE slots SET status = ?, vehicle_number = ? WHERE id = ?
        """, (status_to_set, veh_to_set, slot_id))

    return jsonify({"success": True, "message": "Slot updated successfully", "status": status_to_set})

# ----------------- SMART ALLOCATION MODULE ----------------- #

@app.route('/api/allocate', methods=['POST'])
def smart_allocate():
    """
    Intelligent Multi-Criteria EV Charging Station Allocation Algorithm.
    Criteria:
      - Distance calculated via Haversine Formula
      - Connector compatibility verification (checks available slots with that connector!)
      - Minimum power output compliance
      - Slot availability ratio
      - Charging speed and battery capacity (SoC math)
      - Cost economy per kWh
      - Composite ranking with top recommendation + alternative badges + selection rationale
    """
    data = request.json or {}

    try:
        user_lat = float(data.get('latitude', 12.9716))
        user_lng = float(data.get('longitude', 77.5946))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid latitude or longitude coordinates"}), 400

    pref_connector = str(data.get('connector_type', 'Any')).strip()
    try:
        min_power = float(data.get('min_power_kw', 0))
        battery_kwh = float(data.get('battery_capacity_kwh', 50.0))
        current_soc = float(data.get('current_battery_pct', 20.0))
        target_soc = float(data.get('target_battery_pct', 80.0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid numeric inputs for power or battery parameters"}), 400

    current_soc = max(1.0, min(99.0, current_soc))
    if target_soc <= current_soc:
        target_soc = min(100.0, current_soc + 40.0)

    energy_needed_kwh = round(battery_kwh * ((target_soc - current_soc) / 100.0), 2)

    with get_db() as db:
        query = """
        SELECT s.id, s.name, s.address, s.city, s.zone, s.latitude, s.longitude,
               s.total_slots, s.power_kw, s.connector_types, s.price_per_kwh, s.operator, s.status,
               COUNT(sl.id) as total_slots_count,
               SUM(CASE WHEN sl.status = 'Available' THEN 1 ELSE 0 END) as available_slots_count
        FROM stations s
        JOIN slots sl ON s.id = sl.station_id
        WHERE s.status = 'Active'
        GROUP BY s.id, s.name, s.address, s.city, s.zone, s.latitude, s.longitude,
                 s.total_slots, s.power_kw, s.connector_types, s.price_per_kwh, s.operator, s.status
        """
        db.execute(query)
        stations = db.fetchall()

        candidates = []
        for st in stations:
            # Check station has at least 1 free slot
            if (st['available_slots_count'] or 0) <= 0:
                continue

            # Check connector compatibility on station
            if pref_connector != 'Any' and pref_connector.lower() not in (st['connector_types'] or '').lower():
                continue

            # Check min power
            if min_power > 0 and st['power_kw'] < min_power:
                continue

            # Find matching available slot
            if pref_connector != 'Any':
                db.execute("""
                SELECT * FROM slots 
                WHERE station_id = ? AND status = 'Available' AND LOWER(connector_type) LIKE ?
                ORDER BY power_kw DESC, slot_number ASC
                LIMIT 1
                """, (st['id'], f"%{pref_connector.lower()}%"))
            else:
                db.execute("""
                SELECT * FROM slots 
                WHERE station_id = ? AND status = 'Available'
                ORDER BY power_kw DESC, slot_number ASC
                LIMIT 1
                """, (st['id'],))
            
            best_slot = db.fetchone()
            if not best_slot:
                continue

            # Calculate Haversine distance
            dist = calculate_haversine(user_lat, user_lng, st['latitude'], st['longitude'])
            eta_mins = max(3, int(round((dist / 32.0) * 60)))

            slot_power = best_slot['power_kw'] or st['power_kw']
            effective_power = min(slot_power, 150.0)
            charging_time_mins = max(10, int(round((energy_needed_kwh / effective_power) * 60)))
            estimated_cost = round(energy_needed_kwh * st['price_per_kwh'], 2)

            # Multi-factor smart scoring (0 to 100)
            proximity_score = max(5.0, 100.0 - (dist * 4.5))
            avail_ratio = (st['available_slots_count'] or 1) / float(st['total_slots_count'] or 1)
            availability_score = avail_ratio * 100.0
            power_score = min(100.0, (slot_power / 180.0) * 100.0)
            price_score = max(10.0, 100.0 - ((st['price_per_kwh'] - 10.0) * 6.0))

            composite_score = round(
                (0.40 * proximity_score) +
                (0.35 * availability_score) +
                (0.15 * power_score) +
                (0.10 * price_score),
                1
            )

            # Build selection rationale
            rationale_points = [
                f"{dist} km away (approx. {eta_mins} mins travel time)",
                f"{st['available_slots_count']} of {st['total_slots']} slots currently available ({round(avail_ratio*100)}% free capacity)",
                f"Equipped with {slot_power} kW {best_slot['connector_type']} charger (~{charging_time_mins} mins to target charge)",
                f"Economical tariff at ₹{st['price_per_kwh']}/kWh (est. total ₹{estimated_cost})"
            ]

            candidates.append({
                "station": st,
                "assigned_slot": best_slot,
                "distance_km": dist,
                "eta_mins": eta_mins,
                "charging_time_mins": charging_time_mins,
                "energy_needed_kwh": energy_needed_kwh,
                "estimated_cost": estimated_cost,
                "composite_score": composite_score,
                "selection_rationale": rationale_points,
                "metrics": {
                    "proximity_score": round(proximity_score, 1),
                    "availability_score": round(availability_score, 1),
                    "power_score": round(power_score, 1),
                    "price_score": round(price_score, 1)
                }
            })

    if not candidates:
        return jsonify({
            "success": False,
            "message": f"No available stations found matching your connector ({pref_connector}) and minimum power ({min_power} kW). Try choosing 'Any Connector' or lowering power requirements."
        }), 404

    # Rank by composite score descending
    candidates.sort(key=lambda x: x['composite_score'], reverse=True)

    top_recommendation = candidates[0]
    top_recommendation['badge'] = "Best Match - Optimal Balance"

    alternatives = candidates[1:5]
    for alt in alternatives:
        if alt['distance_km'] < top_recommendation['distance_km']:
            alt['badge'] = "Nearest Station"
        elif alt['station']['power_kw'] > top_recommendation['station']['power_kw']:
            alt['badge'] = "Fastest Charger"
        elif alt['station']['price_per_kwh'] < top_recommendation['station']['price_per_kwh']:
            alt['badge'] = "Budget Friendly"
        else:
            alt['badge'] = "High Availability"

    return jsonify({
        "success": True,
        "recommended": top_recommendation,
        "alternatives": alternatives,
        "total_evaluated": len(stations),
        "total_eligible": len(candidates)
    })

# ----------------- RESERVATIONS & BOOKINGS ----------------- #

@app.route('/api/reservations', methods=['GET'])
def list_reservations():
    user_id = request.args.get('user_id', type=int)
    status_filter = request.args.get('status', '').strip()
    search_query = request.args.get('q', '').strip().lower()

    with get_db() as db:
        query = """
        SELECT r.id, r.reservation_code, r.user_id, r.station_id, r.slot_id,
               r.vehicle_model, r.vehicle_plate, r.connector_type, r.charging_speed_kw,
               r.start_time, r.duration_hours, r.status, r.estimated_energy_kwh, r.estimated_cost, r.created_at,
               s.name as station_name, s.address as station_address, s.city as station_city, s.operator as station_operator,
               sl.slot_number, sl.slot_type,
               u.full_name as user_full_name, u.email as user_email
        FROM reservations r
        JOIN stations s ON r.station_id = s.id
        JOIN slots sl ON r.slot_id = sl.id
        JOIN users u ON r.user_id = u.id
        WHERE 1=1
        """
        params = []
        if user_id:
            query += " AND r.user_id = ?"
            params.append(user_id)
        if status_filter and status_filter.lower() != 'all':
            query += " AND r.status = ?"
            params.append(status_filter)

        query += " ORDER BY r.id DESC"
        db.execute(query, params)
        raw_reservations = db.fetchall()

    reservations = []
    for r in raw_reservations:
        if search_query:
            combined = f"{r['reservation_code']} {r['vehicle_plate']} {r['vehicle_model']} {r['station_name']} {r['user_full_name']}".lower()
            if search_query not in combined:
                continue
        reservations.append(r)

    return jsonify({"success": True, "count": len(reservations), "reservations": reservations})

@app.route('/api/reservations', methods=['POST'])
def create_reservation():
    data = request.json or {}
    try:
        user_id = int(data.get('user_id', 2))
        station_id = int(data.get('station_id', 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid user ID or station ID"}), 400

    slot_id = data.get('slot_id')
    vehicle_model = str(data.get('vehicle_model', 'Standard EV')).strip()
    vehicle_plate = str(data.get('vehicle_plate', 'KA-01-EV-2026')).strip().upper()
    connector_type = str(data.get('connector_type', 'CCS2')).strip()
    
    try:
        duration_hours = float(data.get('duration_hours', 1.0))
    except (ValueError, TypeError):
        duration_hours = 1.0

    start_time = data.get('start_time', datetime.now().strftime("%Y-%m-%d %H:%M"))

    if not station_id:
        return jsonify({"success": False, "message": "Station ID is required"}), 400

    if not vehicle_plate:
        return jsonify({"success": False, "message": "Vehicle license plate is required"}), 400

    with get_db() as db:
        # Prevent duplicate active/pending booking for the same vehicle plate
        db.execute("""
        SELECT id, reservation_code FROM reservations 
        WHERE vehicle_plate = ? AND status IN ('Active', 'Pending')
        """, (vehicle_plate,))
        existing_res = db.fetchone()
        if existing_res:
            return jsonify({
                "success": False,
                "message": f"Duplicate booking prevented: Vehicle {vehicle_plate} already has an active session ({existing_res['reservation_code']})."
            }), 409

        # Verify station exists
        db.execute("SELECT * FROM stations WHERE id = ?", (station_id,))
        station = db.fetchone()
        if not station:
            return jsonify({"success": False, "message": "Station not found"}), 404

        # Slot allocation check
        if not slot_id:
            db.execute("""
            SELECT id, power_kw, connector_type FROM slots 
            WHERE station_id = ? AND status = 'Available'
            ORDER BY slot_number ASC
            LIMIT 1
            """, (station_id,))
            free_slot = db.fetchone()
            if not free_slot:
                return jsonify({"success": False, "message": "No slots currently available at this station"}), 409
            slot_id = free_slot['id']
            charging_speed = free_slot['power_kw']
        else:
            try:
                slot_id = int(slot_id)
            except (ValueError, TypeError):
                return jsonify({"success": False, "message": "Invalid slot ID"}), 400

            db.execute("SELECT * FROM slots WHERE id = ? AND station_id = ?", (slot_id, station_id))
            chosen_slot = db.fetchone()
            if not chosen_slot:
                return jsonify({"success": False, "message": "Selected slot does not exist at this station"}), 404
            if chosen_slot['status'] != 'Available':
                return jsonify({
                    "success": False, 
                    "message": f"Slot #{chosen_slot['slot_number']} is currently {chosen_slot['status']}. Please select another slot."
                }), 409
            charging_speed = chosen_slot['power_kw']

        res_code = generate_reservation_code()
        estimated_energy = round(min(charging_speed, 100.0) * duration_hours * 0.7, 1)
        estimated_cost = round(estimated_energy * station['price_per_kwh'], 2)

        if db.is_pg:
            db.execute("""
            INSERT INTO reservations (reservation_code, user_id, station_id, slot_id, vehicle_model, vehicle_plate, connector_type, charging_speed_kw, start_time, duration_hours, status, estimated_energy_kwh, estimated_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?)
            RETURNING id
            """, (res_code, user_id, station_id, slot_id, vehicle_model, vehicle_plate, connector_type, charging_speed, start_time, duration_hours, estimated_energy, estimated_cost))
            res_id = db.fetchone()['id']
        else:
            db.execute("""
            INSERT INTO reservations (reservation_code, user_id, station_id, slot_id, vehicle_model, vehicle_plate, connector_type, charging_speed_kw, start_time, duration_hours, status, estimated_energy_kwh, estimated_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?)
            """, (res_code, user_id, station_id, slot_id, vehicle_model, vehicle_plate, connector_type, charging_speed, start_time, duration_hours, estimated_energy, estimated_cost))
            res_id = db.lastrowid

        # Update slot status
        db.execute("""
        UPDATE slots SET status = 'Occupied', vehicle_number = ?, current_reservation_id = ?
        WHERE id = ?
        """, (vehicle_plate, res_id, slot_id))

    return jsonify({
        "success": True,
        "message": f"Slot allocated successfully! Reservation code: {res_code}",
        "reservation_code": res_code,
        "reservation_id": res_id,
        "slot_id": slot_id,
        "estimated_cost": estimated_cost
    }), 201

@app.route('/api/reservations/<int:res_id>/cancel', methods=['PUT'])
def cancel_reservation(res_id):
    with get_db() as db:
        db.execute("SELECT * FROM reservations WHERE id = ?", (res_id,))
        res = db.fetchone()
        if not res:
            return jsonify({"success": False, "message": "Reservation not found"}), 404

        if res['status'] == 'Cancelled':
            return jsonify({"success": False, "message": "Reservation is already cancelled"}), 400

        if res['status'] == 'Completed':
            return jsonify({"success": False, "message": "Completed sessions cannot be cancelled"}), 400

        # Mark reservation as cancelled
        db.execute("UPDATE reservations SET status = 'Cancelled' WHERE id = ?", (res_id,))

        # Free the slot only if it was tied to this reservation
        db.execute("""
        UPDATE slots SET status = 'Available', vehicle_number = NULL, current_reservation_id = NULL
        WHERE id = ? AND current_reservation_id = ?
        """, (res['slot_id'], res_id))

    return jsonify({"success": True, "message": "Reservation cancelled and charging slot released"})

@app.route('/api/reservations/<int:res_id>/status', methods=['PUT'])
def update_reservation_status(res_id):
    data = request.json or {}
    new_status = data.get('status', 'Completed')

    valid_statuses = ['Active', 'Pending', 'Completed', 'Cancelled']
    if new_status not in valid_statuses:
        return jsonify({"success": False, "message": f"Invalid status. Must be one of {valid_statuses}"}), 400

    with get_db() as db:
        db.execute("SELECT * FROM reservations WHERE id = ?", (res_id,))
        res = db.fetchone()
        if not res:
            return jsonify({"success": False, "message": "Reservation not found"}), 404

        db.execute("UPDATE reservations SET status = ? WHERE id = ?", (new_status, res_id))

        if new_status in ['Completed', 'Cancelled']:
            db.execute("""
            UPDATE slots SET status = 'Available', vehicle_number = NULL, current_reservation_id = NULL
            WHERE id = ? AND current_reservation_id = ?
            """, (res['slot_id'], res_id))

    return jsonify({"success": True, "message": f"Reservation updated to {new_status}"})

# ----------------- AUTH & USERS ----------------- #

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '').strip().lower()
    password = data.get('password', '').strip()

    with get_db() as db:
        db.execute("SELECT * FROM users WHERE LOWER(username) = ?", (username,))
        user = db.fetchone()

    if not user or hash_password(password) != user['password_hash']:
        return jsonify({"success": False, "message": "Invalid username or password"}), 401

    user_dict = dict(user)
    user_dict.pop('password_hash', None)

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user_dict['full_name']}!",
        "user": user_dict
    })

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username', '').strip().lower()
    password = data.get('password', '').strip()
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip()
    vehicle_model = data.get('vehicle_model', 'Electric Vehicle').strip()
    vehicle_plate = data.get('vehicle_plate', 'EV-NEW-2026').strip().upper()
    preferred_connector = data.get('preferred_connector', 'CCS2').strip()

    if not username or not password or not full_name:
        return jsonify({"success": False, "message": "Username, password, and full name are required"}), 400

    with get_db() as db:
        db.execute("SELECT id FROM users WHERE LOWER(username) = ?", (username,))
        if db.fetchone():
            return jsonify({"success": False, "message": "Username already exists"}), 409

        if db.is_pg:
            db.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, vehicle_model, vehicle_plate, preferred_connector)
            VALUES (?, ?, ?, ?, 'user', ?, ?, ?)
            RETURNING id
            """, (username, hash_password(password), full_name, email, vehicle_model, vehicle_plate, preferred_connector))
            user_id = db.fetchone()['id']
        else:
            db.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, vehicle_model, vehicle_plate, preferred_connector)
            VALUES (?, ?, ?, ?, 'user', ?, ?, ?)
            """, (username, hash_password(password), full_name, email, vehicle_model, vehicle_plate, preferred_connector))
            user_id = db.lastrowid

        db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        new_user = db.fetchone()

    new_user.pop('password_hash', None)
    return jsonify({"success": True, "message": "User registered successfully", "user": new_user}), 201

@app.route('/api/users', methods=['GET'])
def list_users():
    with get_db() as db:
        db.execute("SELECT id, username, full_name, email, role, vehicle_model, vehicle_plate, preferred_connector, battery_capacity_kwh, created_at FROM users ORDER BY id ASC")
        users = db.fetchall()
    return jsonify({"success": True, "users": users})

@app.route('/api/reset-data', methods=['POST'])
def reset_database():
    """Resets database with fresh demo stations, slots, and reservations."""
    init_db(force_reseed=True)
    return jsonify({"success": True, "message": "Database successfully reset to initial demo state!"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("  EV CHARGING STATION ALLOCATION SYSTEM")
    print(f"  Server running on http://127.0.0.1:{port}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)
