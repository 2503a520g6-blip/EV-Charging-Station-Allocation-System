# EV Charging Station Allocation System

A high-performance, responsive web application for Electric Vehicle (EV) drivers and charging network operators. It features real-time charging station discovery, intelligent multi-criteria slot allocation using the Haversine distance formula, live physical slot state tracking, an offline 2D regional radar simulation, 7 analytical charts, and complete User and Admin modules.

![System Status](https://img.shields.io/badge/System-Production_Ready-10b981?style=for-the-badge)
![Backend](https://img.shields.io/badge/Backend-Python_Flask-1e3a8a?style=for-the-badge&logo=flask&logoColor=white)
![Frontend](https://img.shields.io/badge/Frontend-Vanilla_JS_|_CSS3_|_HTML5-0284c7?style=for-the-badge)
![Database](https://img.shields.io/badge/Database-SQLite_|_PostgreSQL-2563eb?style=for-the-badge&logo=postgresql&logoColor=white)

---

## 🌟 Architecture & Highlights

1. **Separation of Concerns for Cloud Deployment**:
   - **Frontend**: Hosted on **GitHub Pages**. Pure static HTML, CSS, and Vanilla JavaScript with zero external CDN dependencies.
   - **Backend API**: Hosted on **Render** (Python Flask + Gunicorn).
   - **Database**: Dual-mode data layer supporting **SQLite** for instant local execution, and persistent **PostgreSQL** on Render via environment variable `DATABASE_URL`.
   - **Cross-Origin Resource Sharing (CORS)**: Configured to allow communication between GitHub Pages and Render.

2. **Redesigned Executive Single-Page Dashboard**:
   - **9 Real-Time KPI Metric Cards**:
     1. Total Charging Stations (12)
     2. Available Stations (11)
     3. Occupied Stations (1)
     4. Total Charging Slots (66)
     5. Available Charging Slots (51)
     6. Active Charging Sessions (3)
     7. Pending Bookings (1)
     8. Total Energy Consumed (228.5 kWh from database records)
     9. Total Revenue (₹3,734.50 from database records)
   - **Live Station Availability Table**: Slot occupancy progress bars, distance (km), ETA (mins), max power (kW), and supported connectors.
   - **2D Regional Vector Radar**: Offline GPS coordinate projection with animated range rings (5 km, 10 km, 15 km) and dynamic routing lines to allocated stations. Click anywhere on the radar to reposition the simulated vehicle.

3. **7 Analytical Charts & Visualizations**:
   - **Charging Station Availability Ratio** (SVG Donut Chart)
   - **Occupied vs Available Slots** (Multi-slice Status Donut Chart)
   - **Charging Stations by Location Zone** (Capacity & Free Slots by Sector)
   - **Daily Charging Sessions** (Date-grouped histogram of charging volume)
   - **Energy Consumption by Operator** (Total kWh delivered by network)
   - **Booking Statistics** (Breakdown across Active, Completed, Pending, and Cancelled states)
   - **Charging Station Utilization Rate (%)** (Top hub occupancy percentages)

4. **Smart Multi-Criteria Allocation Engine**:
   - **Haversine Geodesic Distance Formula**:
     $$\Delta\sigma = 2 \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)$$
     $$d = R \cdot \Delta\sigma \quad (R = 6371.0\text{ km})$$
   - **Multi-Factor Scoring Matrix (0–100 score)**:
     - **Proximity (40% weight)**: Normalized distance decay.
     - **Slot Availability Ratio (35% weight)**: Real-time ratio of free slots.
     - **Power Delivery Speed (15% weight)**: High-speed DC (150–240 kW) vs Fast DC (50–120 kW) vs AC (22 kW).
     - **Tariff Economy (10% weight)**: Cost optimization per kWh.
   - **Slot-Level Verification**: Strictly verifies connector compatibility at the physical slot level before recommending a station.
   - **Decision Support Badges**: Best Match, Nearest Station, Fastest Charger, and Budget Friendly.
   - **Selection Rationale**: Transparent explanation of why the station was selected.

5. **User & Admin Capabilities**:
   - **EV Driver**: Reposition location via presets or map, run smart allocation, book slots, view receipts, and cancel active reservations.
   - **Network Administrator**: Add new charging hubs with custom slots and power ratings, edit metadata, delete stations, toggle physical slot states, monitor all bookings, and reset demo data.

---

## 📁 Repository File Structure

```
ev-charging-station-allocation/
├── app.py                  # Flask REST API, Smart Allocation Algorithm, CORS & Analytics
├── database.py             # Dual SQLite & PostgreSQL Database Engine with 12 Sample Stations
├── requirements.txt        # Production Dependencies (Flask, Gunicorn, psycopg2-binary, flask-cors)
├── Procfile                # Render Web Process Start Command
├── render.yaml             # Render Blueprint for Web Service & PostgreSQL Database
├── run.bat                 # One-click Windows Local Launch Script
├── .gitignore              # Ignores local databases, virtual environments, cache files
├── README.md               # Complete System Documentation & Deployment Guide
├── index.html              # Responsive Dashboard & Single-Page Application UI
├── style.css               # Modern Blue, White & Light-Grey Theme Stylesheet
├── charts.js               # Master Visualization Engine (All 7 Analytical Charts)
├── map.js                  # Pure SVG 2D Regional Grid Radar & Position Simulator
├── app.js                  # Master Frontend Application Controller & REST API Client
├── test_system.py          # Backend Unit & Integration Test Suite (11 test cases)
└── test_static.py          # Frontend Static Assets & DOM Verification Suite (5 test cases)
```

---

## 🚀 Local Installation & Execution

### Prerequisites
- Python 3.8 or higher installed on your machine.
- Pip (Python Package Manager).

### Steps
1. Open your terminal in this project folder.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the automated test suite:
   ```bash
   python -m unittest test_system.py test_static.py -v
   ```
4. Start the server:
   ```bash
   python app.py
   ```
   *(Or on Windows, simply double-click `run.bat`)*
5. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```

---

## 🌐 Online Deployment Instructions

### Step 1: Upload Project to GitHub

```bash
git init
git add .
git commit -m "EV Charging Station Allocation System - Complete Redesign and Verified Suite"
git branch -M main
git remote add origin https://github.com/2503a520g6-blip/ev-charging-station-allocation.git
git push -u origin main --force
```

### Step 2: Deploy Backend & Database on Render

1. Log in to [Render](https://dashboard.render.com/).
2. Click **New +** > **Blueprint**.
3. Select your repository: `2503a520g6-blip/ev-charging-station-allocation`.
4. Render will read `render.yaml` and configure:
   - **Web Service**: `ev-charging-station-allocation` (Python 3.11, `gunicorn app:app`)
   - **PostgreSQL Database**: `ev-charging-db`
5. Click **Apply**.
6. Once deployed, copy your Render Web Service URL (e.g., `https://ev-charging-station-allocation.onrender.com`).

### Step 3: Enable GitHub Pages for Frontend

1. Go to your GitHub repository: `https://github.com/2503a520g6-blip/ev-charging-station-allocation`.
2. Click **Settings** > **Pages**.
3. Under **Build and deployment**:
   - **Source**: `Deploy from a branch`
   - **Branch**: `main`
   - **Folder**: `/ (root)`
4. Click **Save**.
5. Your website will be live at:
   ```
   https://2503a520g6-blip.github.io/ev-charging-station-allocation/
   ```

### Step 4: Configure CORS on Render

In your Render dashboard for `ev-charging-station-allocation`:
- Go to **Environment** > **Environment Variables**.
- Set `CORS_ALLOWED_ORIGIN` to:
  `https://2503a520g6-blip.github.io`
- Click **Save Changes**.
