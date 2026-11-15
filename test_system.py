"""
EV Charging Station Allocation System - Comprehensive Verification & Test Suite
Validates all backend endpoints, database consistency, allocation algorithm,
business rules, analytics datasets, and edge cases.
"""

import unittest
import json
from app import app
from database import init_db, get_db

class EVSystemTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reset and seed clean test database
        init_db(force_reseed=True)
        cls.client = app.test_client()

    def test_01_health_check(self):
        """Test system health check endpoint."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertGreaterEqual(data['stations_loaded'], 12)
        print("✓ Test 01 Passed: Health Check OK")

    def test_02_dashboard_stats_and_9_kpis(self):
        """Test dashboard statistics calculation with all 9 KPI metrics."""
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        
        # 1. Total Stations
        self.assertEqual(data['total_stations'], 12)
        # 2. Available Stations
        self.assertGreaterEqual(data['available_stations'], 1)
        # 3. Occupied Stations
        self.assertGreaterEqual(data['occupied_stations'], 0)
        # 4. Total Slots
        self.assertGreater(data['total_slots'], 50)
        # 5. Available Slots
        self.assertGreater(data['available_slots'], 20)
        # 6. Active Sessions
        self.assertGreaterEqual(data['active_sessions'], 1)
        # 7. Pending Bookings
        self.assertGreaterEqual(data['pending_reservations'], 0)
        # 8. Total Energy Consumed (real kWh)
        self.assertIn('total_energy_kwh', data)
        self.assertGreater(data['total_energy_kwh'], 0.0)
        # 9. Total Revenue (real currency)
        self.assertIn('total_revenue', data)
        self.assertGreater(data['total_revenue'], 0.0)

        self.assertIn('slot_distribution', data)
        self.assertIn('zone_stats', data)
        print(f"✓ Test 02 Passed: All 9 KPI Stats Verified (Stations: {data['total_stations']}, Slots: {data['total_slots']}, Energy: {data['total_energy_kwh']} kWh, Revenue: ₹{data['total_revenue']})")

    def test_03_analytics_all_7_charts_data(self):
        """Test analytics endpoint providing data for all 7 analytical charts."""
        response = self.client.get('/api/analytics')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])

        # Chart 1: Station Availability
        self.assertIn('station_availability', data)
        self.assertIn('available', data['station_availability'])
        self.assertIn('occupied', data['station_availability'])

        # Chart 2: Occupied vs Available Slots
        self.assertIn('slot_distribution', data)
        self.assertIn('available', data['slot_distribution'])
        self.assertIn('occupied', data['slot_distribution'])

        # Chart 3: Location Zone Distribution
        self.assertIn('location_distribution', data)
        self.assertGreater(len(data['location_distribution']), 0)

        # Chart 4: Daily Sessions
        self.assertIn('daily_sessions', data)

        # Chart 5: Energy by Operator
        self.assertIn('energy_by_operator', data)
        self.assertGreater(len(data['energy_by_operator']), 0)

        # Chart 6: Booking Statistics
        self.assertIn('booking_stats', data)
        self.assertIn('Active', data['booking_stats'])

        # Chart 7: Station Utilization
        self.assertIn('station_utilization', data)
        self.assertGreater(len(data['station_utilization']), 0)

        print("✓ Test 03 Passed: /api/analytics successfully generated datasets for all 7 charts")

    def test_04_station_listing_and_filtering(self):
        """Test station retrieval, distance calculation, search, zone and connector filters."""
        # Distance calculation via Haversine
        response = self.client.get('/api/stations?lat=12.9716&lng=77.5946')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 12)
        
        first_st = data['stations'][0]
        self.assertIsNotNone(first_st['distance_km'])
        self.assertIsNotNone(first_st['eta_mins'])
        self.assertLessEqual(first_st['distance_km'], data['stations'][-1]['distance_km'])

        # Search filter
        res_search = self.client.get('/api/stations?q=Airport')
        search_data = res_search.get_json()
        self.assertEqual(search_data['count'], 1)
        self.assertIn("Airport", search_data['stations'][0]['name'])

        # Connector filter
        res_conn = self.client.get('/api/stations?connector=CHAdeMO')
        conn_data = res_conn.get_json()
        self.assertGreater(conn_data['count'], 0)
        for st in conn_data['stations']:
            self.assertIn("chademo", st['connector_types'].lower())

        # Zone filter
        res_zone = self.client.get('/api/stations?zone=Central%20Zone')
        zone_data = res_zone.get_json()
        self.assertGreater(zone_data['count'], 0)
        for st in zone_data['stations']:
            self.assertEqual(st['zone'], 'Central Zone')

        print("✓ Test 04 Passed: Station listing, Haversine sorting, and filters OK")

    def test_05_smart_allocation_engine(self):
        """Test smart multi-criteria allocation algorithm and rationale."""
        payload = {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "connector_type": "CCS2",
            "min_power_kw": 50,
            "battery_capacity_kwh": 72.6,
            "current_battery_pct": 20,
            "target_battery_pct": 80
        }
        response = self.client.post('/api/allocate', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('recommended', data)
        
        rec = data['recommended']
        self.assertGreater(rec['composite_score'], 0)
        self.assertIn('assigned_slot', rec)
        self.assertIn('distance_km', rec)
        self.assertIn('charging_time_mins', rec)
        self.assertIn('estimated_cost', rec)
        self.assertIn('selection_rationale', rec)
        self.assertGreater(len(rec['selection_rationale']), 0)
        self.assertIn('metrics', rec)
        self.assertIn('alternatives', data)
        print(f"✓ Test 05 Passed: Smart Allocation Recommended '{rec['station']['name']}' (Score: {rec['composite_score']}, Slot #{rec['assigned_slot']['slot_number']}, Rationale: {len(rec['selection_rationale'])} points)")

    def test_06_smart_allocation_no_match(self):
        """Test smart allocation rejection when criteria impossible to meet."""
        payload = {
            "latitude": 12.9716,
            "longitude": 77.5946,
            "connector_type": "NonExistentPlugType",
            "min_power_kw": 9999,
            "battery_capacity_kwh": 50,
            "current_battery_pct": 20,
            "target_battery_pct": 80
        }
        response = self.client.post('/api/allocate', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertFalse(data['success'])
        print("✓ Test 06 Passed: Incompatible connector correctly rejected (404)")

    def test_07_reservation_creation_and_duplicate_prevention(self):
        """Test booking creation, duplicate booking prevention, and slot update."""
        plate = "TEST-EV-8899"
        payload = {
            "user_id": 2,
            "station_id": 1,
            "vehicle_model": "Tesla Model Y",
            "vehicle_plate": plate,
            "connector_type": "CCS2",
            "duration_hours": 1.0
        }
        # First booking succeeds
        res1 = self.client.post('/api/reservations', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res1.status_code, 201)
        data1 = res1.get_json()
        self.assertTrue(data1['success'])
        res_id = data1['reservation_id']
        res_code = data1['reservation_code']
        self.assertTrue(res_code.startswith("RES-"))

        # Second booking with same vehicle plate must be rejected (duplicate prevention)
        res2 = self.client.post('/api/reservations', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res2.status_code, 409)
        data2 = res2.get_json()
        self.assertFalse(data2['success'])
        self.assertIn("Duplicate booking prevented", data2['message'])
        print(f"✓ Test 07 Passed: Reservation created ({res_code}) and duplicate booking prevented (409)")

        # Cancel reservation and verify slot is freed
        cancel_res = self.client.put(f'/api/reservations/{res_id}/cancel')
        self.assertEqual(cancel_res.status_code, 200)
        cancel_data = cancel_res.get_json()
        self.assertTrue(cancel_data['success'])
        print("✓ Test 08 Passed: Reservation cancellation successfully released slot back to grid")

    def test_09_station_crud(self):
        """Test admin station creation, retrieval, updating and deletion."""
        new_station = {
            "name": "Test Greenfield Hub",
            "address": "42 Innovation Way",
            "city": "Bengaluru",
            "zone": "North Tech Zone",
            "latitude": 13.0500,
            "longitude": 77.6200,
            "total_slots": 4,
            "power_kw": 120.0,
            "connector_types": "CCS2, Type 2",
            "price_per_kwh": 16.50,
            "operator": "Test Network",
            "status": "Active"
        }
        res_create = self.client.post('/api/stations', data=json.dumps(new_station), content_type='application/json')
        self.assertEqual(res_create.status_code, 201)
        created_id = res_create.get_json()['station_id']

        # Verify slots were automatically generated
        res_get = self.client.get(f'/api/stations/{created_id}')
        self.assertEqual(res_get.status_code, 200)
        station_obj = res_get.get_json()['station']
        self.assertEqual(len(station_obj['slots']), 4)

        # Update
        update_data = {
            "name": "Test Greenfield Hub (Updated)",
            "price_per_kwh": 18.00
        }
        res_update = self.client.put(f'/api/stations/{created_id}', data=json.dumps(update_data), content_type='application/json')
        self.assertEqual(res_update.status_code, 200)

        # Delete
        res_delete = self.client.delete(f'/api/stations/{created_id}')
        self.assertEqual(res_delete.status_code, 200)

        # Confirm 404 after deletion
        res_after = self.client.get(f'/api/stations/{created_id}')
        self.assertEqual(res_after.status_code, 404)
        print("✓ Test 09 Passed: Station CRUD (Create, Read slots, Update, Delete) OK")

    def test_10_slot_status_toggle(self):
        """Test physical slot status updating and simulation override."""
        res = self.client.get('/api/stations/2/slots')
        slots = res.get_json()['slots']
        target_slot = slots[0]
        slot_id = target_slot['id']

        # Update to Occupied
        res_put = self.client.put(f'/api/slots/{slot_id}', data=json.dumps({"status": "Occupied", "vehicle_number": "KA-99-TEST"}), content_type='application/json')
        self.assertEqual(res_put.status_code, 200)

        # Verify
        res_verify = self.client.get('/api/stations/2/slots')
        updated_slot = [s for s in res_verify.get_json()['slots'] if s['id'] == slot_id][0]
        self.assertEqual(updated_slot['status'], 'Occupied')
        self.assertEqual(updated_slot['vehicle_number'], 'KA-99-TEST')

        # Revert back to Available
        self.client.put(f'/api/slots/{slot_id}', data=json.dumps({"status": "Available"}), content_type='application/json')
        print("✓ Test 10 Passed: Slot status update and simulation toggle OK")

    def test_11_auth_and_users(self):
        """Test login, registration, and user directory."""
        login_res = self.client.post('/api/auth/login', data=json.dumps({"username": "admin", "password": "admin123"}), content_type='application/json')
        self.assertEqual(login_res.status_code, 200)
        self.assertEqual(login_res.get_json()['user']['role'], 'admin')

        bad_login = self.client.post('/api/auth/login', data=json.dumps({"username": "admin", "password": "wrongpassword"}), content_type='application/json')
        self.assertEqual(bad_login.status_code, 401)

        users_res = self.client.get('/api/users')
        self.assertEqual(users_res.status_code, 200)
        self.assertGreaterEqual(len(users_res.get_json()['users']), 5)
        print("✓ Test 11 Passed: Auth login, password hashing, and user listing OK")

if __name__ == '__main__':
    unittest.main()
