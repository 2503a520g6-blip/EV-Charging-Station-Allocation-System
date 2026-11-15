/**
 * EV Charging Station Allocation System - Master Frontend Controller
 * Robust, lightweight, zero-external-dependency SPA client.
 * Supports local Flask backend AND production Render backend on GitHub Pages.
 */

// Global App Namespace
const App = {
  // Determine API base URL
  apiBase: window.API_BASE_URL ||
           localStorage.getItem('ev_api_base_url') ||
           (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:'
             ? 'http://127.0.0.1:5000'
             : 'https://ev-charging-station-allocation.onrender.com'),

  // Current logged in profile (default: Driver Alex Rivera)
  currentUser: {
    id: 2,
    username: 'alex_ev',
    name: 'Alex Rivera',
    initials: 'AR',
    role: 'user', // 'user' or 'admin'
    vehicleModel: 'Hyundai Ioniq 5',
    vehiclePlate: 'KA-01-EV-4421',
    connector: 'CCS2',
    batteryKwh: 72.6
  },

  // Simulated vehicle position
  currentLocation: {
    name: 'Downtown Central',
    lat: 12.9716,
    lng: 77.5946
  },

  // Location Presets across Bengaluru metropolitan region
  presets: [
    { name: 'Downtown Central', lat: 12.9716, lng: 77.5946 },
    { name: 'Cyber City Tech', lat: 12.8452, lng: 77.6602 },
    { name: 'Kempegowda Airport', lat: 13.2008, lng: 77.7088 },
    { name: 'Green Valley HSR', lat: 12.9121, lng: 77.6446 },
    { name: 'Whitefield Tech Park', lat: 12.9698, lng: 77.7499 },
    { name: 'Malleshwaram West', lat: 13.0031, lng: 77.5685 }
  ],

  // Cache
  stations: [],
  stats: null,
  analytics: null,
  activeTab: 'dashboard',
  cachedRecommendation: null,

  // ----------------- INITIALIZATION ----------------- //
  init() {
    this.setupNavigation();
    this.renderLocationPresets();
    this.setupModals();
    this.updateUserUI();

    // Initialize 2D Offline Vector Map
    try {
      EVMap.init('map-viewport', {
        onLocationChange: (coords) => {
          this.setLocation(coords.lat, coords.lng, "Map Clicked Position");
        }
      });
    } catch (e) {
      console.warn("[EV Map] Initialization notice:", e);
    }

    // Initial Data Fetch
    this.checkHealth();
    this.loadStats();
    this.loadStations();
    this.loadReservations();
    this.loadUsers();
    this.loadAnalytics();

    // Auto-run smart allocation once for immediate visual preview
    setTimeout(() => {
      this.runSmartAllocation(false);
    }, 400);
  },

  // ----------------- API HELPER ----------------- //
  async api(endpoint, options = {}) {
    let base = this.apiBase;
    if (base.endsWith('/')) base = base.slice(0, -1);
    const url = endpoint.startsWith('http') ? endpoint : `${base}${endpoint}`;

    const defaultHeaders = {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    };

    options.headers = { ...defaultHeaders, ...(options.headers || {}) };

    try {
      const res = await fetch(url, options);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.message || `API error ${res.status}: ${res.statusText}`);
      }
      return data;
    } catch (err) {
      console.error(`[API Fetch Failed] ${endpoint}:`, err);
      throw err;
    }
  },

  // ----------------- HEALTH CHECK ----------------- //
  async checkHealth() {
    const statusDot = document.querySelector('.system-status-indicator');
    try {
      const data = await this.api('/api/health');
      if (statusDot) {
        statusDot.title = `Connected to ${data.database.toUpperCase()} backend (${data.stations_loaded} stations active)`;
        statusDot.innerHTML = `<span class="status-dot"></span><span>${data.database === 'postgresql' ? 'PostgreSQL Active' : 'SQLite Connected'}</span>`;
      }
    } catch (e) {
      if (statusDot) {
        statusDot.title = "Backend connection pending or offline";
        statusDot.innerHTML = `<span class="status-dot" style="background:#f59e0b;box-shadow:0 0 0 2px #fde68a;"></span><span>API Ready</span>`;
      }
    }
  },

  // ----------------- NAVIGATION & TABS ----------------- //
  setupNavigation() {
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const tab = item.getAttribute('data-tab');
        if (tab) this.switchTab(tab);
      });
    });

    const mobileBtn = document.getElementById('mobile-toggle');
    const sidebar = document.querySelector('.sidebar');
    if (mobileBtn && sidebar) {
      mobileBtn.addEventListener('click', () => {
        sidebar.classList.toggle('mobile-open');
      });
    }
  },

  switchTab(tabName) {
    this.activeTab = tabName;

    // Update nav links
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(el => {
      if (el.getAttribute('data-tab') === tabName) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    });

    // Update views
    document.querySelectorAll('.view-section').forEach(sec => {
      sec.classList.remove('active');
    });

    const target = document.getElementById(`view-${tabName}`);
    if (target) {
      target.classList.add('active');
    }

    // Close mobile menu if open
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) sidebar.classList.remove('mobile-open');

    // Tab-specific refreshes
    if (tabName === 'dashboard') {
      this.loadStats();
      this.loadStations();
      setTimeout(() => EVMap.render('map-viewport'), 100);
    } else if (tabName === 'analytics') {
      this.loadAnalytics();
    } else if (tabName === 'diagnostics') {
      setTimeout(() => EVMap.render('map-viewport-alt'), 100);
    } else if (tabName === 'reservations') {
      this.loadReservations();
    } else if (tabName === 'admin') {
      this.loadStations();
      this.loadReservations();
      this.loadUsers();
    }
  },

  // ----------------- USER & ROLE MANAGEMENT ----------------- //
  toggleCurrentRole() {
    if (this.currentUser.role === 'user') {
      this.currentUser = {
        id: 1,
        username: 'admin',
        name: 'System Administrator',
        initials: 'AD',
        role: 'admin',
        vehicleModel: 'Tesla Model 3',
        vehiclePlate: 'EV-ADM-001',
        connector: 'CCS2',
        batteryKwh: 75.0
      };
      this.showToast("Switched to System Administrator Mode");
    } else {
      this.currentUser = {
        id: 2,
        username: 'alex_ev',
        name: 'Alex Rivera',
        initials: 'AR',
        role: 'user',
        vehicleModel: 'Hyundai Ioniq 5',
        vehiclePlate: 'KA-01-EV-4421',
        connector: 'CCS2',
        batteryKwh: 72.6
      };
      this.showToast("Switched to EV Driver Profile (Alex Rivera)");
    }
    this.updateUserUI();
    this.loadStations();
    this.loadReservations();
  },

  updateUserUI() {
    const avatarEl = document.getElementById('user-avatar-initials');
    const nameEl = document.getElementById('user-profile-name');
    const roleEl = document.getElementById('user-profile-role');
    const toggleBtn = document.getElementById('role-toggle-btn');
    const navAdmin = document.getElementById('nav-admin-item');

    if (avatarEl) avatarEl.textContent = this.currentUser.initials;
    if (nameEl) nameEl.textContent = this.currentUser.name;
    if (roleEl) {
      roleEl.textContent = this.currentUser.role === 'admin' ? 'Administrator' : 'EV Driver';
      roleEl.style.color = this.currentUser.role === 'admin' ? '#3b82f6' : '#38bdf8';
    }
    if (toggleBtn) {
      toggleBtn.textContent = this.currentUser.role === 'admin' ? 'Switch to EV Driver' : 'Switch to Admin';
    }
    if (navAdmin) {
      navAdmin.style.display = 'flex';
    }
  },

  // ----------------- LOCATION PRESETS ----------------- //
  renderLocationPresets() {
    const container = document.getElementById('preset-locations-box');
    if (!container) return;

    let html = '';
    this.presets.forEach((p, idx) => {
      const isActive = (p.name === this.currentLocation.name);
      html += `
        <button type="button" class="pill-btn ${isActive ? 'active' : ''}" onclick="App.selectLocationPreset(${idx})">
          📍 ${p.name}
        </button>
      `;
    });
    container.innerHTML = html;
  },

  selectLocationPreset(index) {
    const preset = this.presets[index];
    if (!preset) return;

    this.setLocation(preset.lat, preset.lng, preset.name);
    this.renderLocationPresets();
    this.showToast(`Simulated location set to: ${preset.name}`);
  },

  setLocation(lat, lng, name = "Custom Position") {
    this.currentLocation = { lat: Number(lat), lng: Number(lng), name };

    const latInput = document.getElementById('alloc-lat');
    const lngInput = document.getElementById('alloc-lng');
    const labelEl = document.getElementById('alloc-location-name');

    if (latInput) latInput.value = lat;
    if (lngInput) lngInput.value = lng;
    if (labelEl) labelEl.textContent = name;

    EVMap.setUserLocation(lat, lng, name);
    this.loadStations();
  },

  // ----------------- DASHBOARD & STATS ----------------- //
  async loadStats() {
    try {
      const data = await this.api('/api/stats');
      if (!data.success) return;

      this.stats = data;

      const updateEl = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val !== undefined ? val : '0';
      };

      // 9 KPI cards
      updateEl('stat-total-stations', data.total_stations);
      updateEl('stat-available-stations', data.available_stations);
      updateEl('stat-occupied-stations', data.occupied_stations);
      updateEl('stat-total-slots', data.total_slots);
      updateEl('stat-available-slots', data.available_slots);
      updateEl('stat-active-sessions', data.active_sessions);
      updateEl('stat-pending-bookings', data.pending_reservations);
      updateEl('stat-total-energy', `${Number(data.total_energy_kwh || 0).toFixed(1)} kWh`);
      updateEl('stat-total-revenue', `₹${Number(data.total_revenue || 0).toFixed(2)}`);

      // Render Dashboard Charts
      Charts.renderStationAvailabilityChart('chart-dashboard-station-avail', {
        available: data.available_stations,
        occupied: data.occupied_stations
      });

      Charts.renderSlotAvailabilityChart('chart-donut-slots', data.slot_distribution);
    } catch (err) {
      console.warn("[Stats Load Warning]:", err);
    }
  },

  // ----------------- ANALYTICS & 7 CHARTS ----------------- //
  async loadAnalytics() {
    try {
      const data = await this.api('/api/analytics');
      if (!data.success) return;

      this.analytics = data;

      // Render 7 Visualizations
      Charts.renderStationAvailabilityChart('chart-analytics-station-avail', data.station_availability);
      Charts.renderSlotAvailabilityChart('chart-analytics-slots-avail', data.slot_distribution);
      Charts.renderLocationDistributionChart('chart-analytics-location', data.location_distribution);
      Charts.renderDailySessionsChart('chart-analytics-daily', data.daily_sessions);
      Charts.renderEnergyByOperatorChart('chart-analytics-energy', data.energy_by_operator);
      Charts.renderBookingStatsChart('chart-analytics-booking-stats', data.booking_stats);
      Charts.renderUtilizationChart('chart-analytics-utilization', data.station_utilization);
    } catch (err) {
      console.warn("[Analytics Load Warning]:", err);
    }
  },

  // ----------------- STATIONS & SLOTS ----------------- //
  async loadStations() {
    const searchVal = document.getElementById('station-search-box')?.value || '';
    const connFilter = document.getElementById('station-conn-filter')?.value || 'all';
    const zoneFilter = document.getElementById('station-zone-filter')?.value || 'all';

    const params = new URLSearchParams({
      lat: this.currentLocation.lat,
      lng: this.currentLocation.lng,
      q: searchVal,
      connector: connFilter,
      zone: zoneFilter
    });

    try {
      const data = await this.api(`/api/stations?${params.toString()}`);
      if (!data.success) return;

      this.stations = data.stations || [];

      // Update Map pins
      EVMap.setStations(this.stations);

      // Render Tables
      this.renderDashboardStationsTable();
      this.renderFullStationsTable();
      this.renderAdminStationsTable();
    } catch (err) {
      console.error("[Stations Load Error]:", err);
    }
  },

  renderDashboardStationsTable() {
    const tbody = document.getElementById('dashboard-stations-tbody');
    if (!tbody) return;

    if (this.stations.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:#94a3b8;">No matching charging stations found</td></tr>`;
      return;
    }

    const displayList = this.stations.slice(0, 6);
    let html = '';

    displayList.forEach(st => {
      const isAvail = st.available_slots_count > 0;
      const statusBadge = isAvail
        ? `<span class="badge badge-available">✓ Open (${st.available_slots_count} free)</span>`
        : `<span class="badge badge-occupied">✕ 100% Full</span>`;

      const distText = st.distance_km !== null ? `${st.distance_km} km` : '—';
      const etaText = st.eta_mins !== null ? `~${st.eta_mins} mins` : '';

      html += `
        <tr>
          <td>
            <div class="station-cell">
              <span class="station-name-link" onclick="App.inspectStationSlots(${st.id})">${st.name}</span>
              <span class="station-location-sub">${st.address}, ${st.zone}</span>
            </div>
          </td>
          <td>
            <strong style="color:#0f172a;">${distText}</strong>
            <div style="font-size:11px;color:#64748b;">${etaText}</div>
          </td>
          <td>
            <span style="font-weight:700;color:${isAvail ? '#059669' : '#dc2626'};">${st.available_slots_count} / ${st.total_slots}</span>
            <div class="slot-bar-wrap">
              <div class="slot-bar-fill" style="width:${Math.round((st.available_slots_count / st.total_slots) * 100)}%;"></div>
            </div>
          </td>
          <td><span class="badge badge-power">${st.power_kw} kW</span></td>
          <td style="font-size:12px;color:#475569;">${st.connector_types}</td>
          <td>${statusBadge}</td>
          <td>
            <button class="btn btn-sm btn-secondary" onclick="App.inspectStationSlots(${st.id})">
              Slots
            </button>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  },

  renderFullStationsTable() {
    const tbody = document.getElementById('full-stations-tbody');
    if (!tbody) return;

    if (this.stations.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:30px;color:#94a3b8;">No charging stations match your filter criteria</td></tr>`;
      return;
    }

    let html = '';
    this.stations.forEach(st => {
      const isAvail = st.available_slots_count > 0;
      const distText = st.distance_km !== null ? `${st.distance_km} km (~${st.eta_mins} mins)` : '—';

      html += `
        <tr>
          <td>
            <div class="station-cell">
              <strong style="color:#1e3a8a;font-size:14px;cursor:pointer;" onclick="App.inspectStationSlots(${st.id})">${st.name}</strong>
              <span class="station-location-sub">${st.address}, ${st.city} • <em style="color:#2563eb;">${st.operator}</em></span>
            </div>
          </td>
          <td><strong>${distText}</strong></td>
          <td>
            <span style="font-weight:700;color:${isAvail ? '#059669' : '#dc2626'};">${st.available_slots_count} / ${st.total_slots} Free</span>
            <div class="slot-bar-wrap">
              <div class="slot-bar-fill" style="width:${Math.round((st.available_slots_count / st.total_slots) * 100)}%;"></div>
            </div>
          </td>
          <td><span class="badge badge-power">${st.power_kw} kW</span></td>
          <td style="font-size:12px;">${st.connector_types}</td>
          <td>
            ${isAvail 
              ? `<span class="badge badge-available">Available</span>` 
              : `<span class="badge badge-occupied">Occupied</span>`}
          </td>
          <td>
            <div style="display:flex;gap:6px;">
              <button class="btn btn-sm btn-secondary" onclick="App.inspectStationSlots(${st.id})">
                Inspect
              </button>
              ${isAvail ? `
                <button class="btn btn-sm btn-primary" onclick="App.openBookingModal(${st.id}, null, '${st.name.replace(/'/g, "\\'")}')">
                  Book
                </button>
              ` : `
                <button class="btn btn-sm btn-secondary" disabled style="opacity:0.5;cursor:not-allowed;">
                  Full
                </button>
              `}
            </div>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  },

  renderAdminStationsTable() {
    const tbody = document.getElementById('admin-stations-tbody');
    if (!tbody) return;

    if (this.stations.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:24px;color:#94a3b8;">No stations registered</td></tr>`;
      return;
    }

    let html = '';
    this.stations.forEach(st => {
      html += `
        <tr>
          <td><strong>#${st.id}</strong></td>
          <td>
            <div class="station-cell">
              <strong>${st.name}</strong>
              <span class="station-location-sub">${st.address} • ${st.operator}</span>
            </div>
          </td>
          <td>${st.zone}</td>
          <td>${st.available_slots_count} / ${st.total_slots} Free</td>
          <td>${st.power_kw} kW</td>
          <td>₹${st.price_per_kwh.toFixed(2)}/kWh</td>
          <td><span class="badge ${st.status === 'Active' ? 'badge-available' : 'badge-occupied'}">${st.status}</span></td>
          <td>
            <div style="display:flex;gap:6px;">
              <button class="btn btn-sm btn-secondary" onclick="App.openEditStationModal(${st.id})">Edit</button>
              <button class="btn btn-sm btn-secondary" onclick="App.inspectStationSlots(${st.id})">Slots</button>
              <button class="btn btn-sm btn-danger" onclick="App.deleteStation(${st.id}, '${st.name.replace(/'/g, "\\'")}')">Delete</button>
            </div>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  },

  // ----------------- SMART ALLOCATION ENGINE ----------------- //
  async runSmartAllocation(scrollIntoView = true) {
    const container = document.getElementById('allocation-result-container');
    if (!container) return;

    const lat = parseFloat(document.getElementById('alloc-lat')?.value || this.currentLocation.lat);
    const lng = parseFloat(document.getElementById('alloc-lng')?.value || this.currentLocation.lng);
    const connector = document.getElementById('alloc-connector')?.value || 'Any';
    const minPower = parseFloat(document.getElementById('alloc-min-power')?.value || 0);
    const currentSoc = parseFloat(document.getElementById('alloc-current-soc')?.value || 20);
    const targetSoc = parseFloat(document.getElementById('alloc-target-soc')?.value || 80);

    if (targetSoc <= currentSoc) {
      this.showToast("Target Battery SoC must be greater than current battery level!", "warn");
      return;
    }

    container.innerHTML = `
      <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:40px;text-align:center;">
        <div style="font-size:28px;margin-bottom:12px;">⚡</div>
        <div style="font-weight:700;color:#1e3a8a;font-size:16px;">Running Multi-Criteria Smart Allocation Algorithm...</div>
        <p style="font-size:12px;color:#64748b;margin-top:6px;">
          Calculating Haversine distances, verifying physical slot compatibility, evaluating power delivery and price models...
        </p>
      </div>
    `;

    try {
      const data = await this.api('/api/allocate', {
        method: 'POST',
        body: JSON.stringify({
          latitude: lat,
          longitude: lng,
          connector_type: connector,
          min_power_kw: minPower,
          battery_capacity_kwh: this.currentUser.batteryKwh || 50.0,
          current_battery_pct: currentSoc,
          target_battery_pct: targetSoc
        })
      });

      if (!data.success) {
        throw new Error(data.message || "Failed to find suitable station");
      }

      this.cachedRecommendation = data.recommended;
      this.renderAllocationResult(data);

      if (data.recommended && data.recommended.station) {
        EVMap.setHighlight(data.recommended.station.id);
      }

      if (scrollIntoView) {
        container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    } catch (err) {
      container.innerHTML = `
        <div style="background:#fff1f2;border:1px solid #fecdd3;border-radius:10px;padding:30px;text-align:center;">
          <div style="font-size:32px;color:#e11d48;margin-bottom:8px;">⚠️</div>
          <div style="font-weight:700;color:#9f1239;font-size:15px;">No Compatible Stations Available</div>
          <p style="font-size:13px;color:#be123c;max-width:440px;margin:8px auto;">
            ${err.message || "No active stations currently match your connector and power requirements."}
          </p>
          <div style="margin-top:14px;">
            <button class="btn btn-secondary btn-sm" onclick="document.getElementById('alloc-connector').value='Any';document.getElementById('alloc-min-power').value='0';App.runSmartAllocation(true);">
              Reset Filters & Retry
            </button>
          </div>
        </div>
      `;
    }
  },

  renderAllocationResult(data) {
    const container = document.getElementById('allocation-result-container');
    if (!container || !data.recommended) return;

    const rec = data.recommended;
    const st = rec.station;
    const slot = rec.assigned_slot;

    let rationaleHtml = '';
    if (rec.selection_rationale && rec.selection_rationale.length > 0) {
      rationaleHtml = `
        <div class="rationale-box">
          <h5>Why this station was selected:</h5>
          <ul>
            ${rec.selection_rationale.map(r => `<li>${r}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    let alternativesHtml = '';
    if (data.alternatives && data.alternatives.length > 0) {
      alternativesHtml += `
        <div class="alternatives-container">
          <h4 style="font-size:13px;font-weight:700;color:#1e293b;margin-bottom:10px;text-transform:uppercase;letter-spacing:0.5px;">
            Alternative Evaluated Candidates (${data.alternatives.length})
          </h4>
      `;

      data.alternatives.forEach(alt => {
        const altSt = alt.station;
        alternativesHtml += `
          <div class="alt-card">
            <div>
              <div style="display:flex;align-items:center;gap:8px;">
                <strong style="color:#0f172a;font-size:13.5px;">${altSt.name}</strong>
                <span class="badge badge-power" style="font-size:10.5px;">${alt.badge || 'Alternative'}</span>
              </div>
              <div style="font-size:11.5px;color:#64748b;margin-top:2px;">
                ${alt.distance_km} km away (~${alt.eta_mins} mins) • ${altSt.power_kw} kW • ₹${altSt.price_per_kwh}/kWh
              </div>
            </div>
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="font-weight:700;font-size:13px;color:#059669;">Score: ${alt.composite_score}</span>
              <button class="btn btn-sm btn-secondary" onclick="App.openBookingModal(${altSt.id}, ${alt.assigned_slot ? alt.assigned_slot.id : 'null'}, '${altSt.name.replace(/'/g, "\\'")}')">
                Select
              </button>
            </div>
          </div>
        `;
      });

      alternativesHtml += `</div>`;
    }

    container.innerHTML = `
      <div class="recommendation-banner">
        <div class="rec-tag-ribbon">
          ⚡ ${rec.badge || "Best Match - Optimal Balance"}
        </div>

        <div class="rec-header-row">
          <div>
            <div class="rec-title">${st.name}</div>
            <div class="rec-address">${st.address}, ${st.zone} • Operator: <strong>${st.operator}</strong></div>
          </div>
          <div class="score-badge-circle" title="Multi-factor algorithm composite score out of 100">
            <span class="score-num">${rec.composite_score}</span>
            <span class="score-sub">Score</span>
          </div>
        </div>

        <!-- 4 Key Decision Metrics -->
        <div class="rec-metrics-grid">
          <div class="metric-col">
            <span class="m-label">Distance & ETA</span>
            <span class="m-val">${rec.distance_km} km <small style="font-size:11px;font-weight:500;color:#64748b;">(~${rec.eta_mins} min)</small></span>
          </div>
          <div class="metric-col">
            <span class="m-label">Charging Time</span>
            <span class="m-val">~${rec.charging_time_mins} mins</span>
          </div>
          <div class="metric-col">
            <span class="m-label">Energy Required</span>
            <span class="m-val">${rec.energy_needed_kwh} kWh</span>
          </div>
          <div class="metric-col">
            <span class="m-label">Estimated Tariff</span>
            <span class="m-val" style="color:#059669;">₹${rec.estimated_cost}</span>
          </div>
        </div>

        <!-- Physical Slot Assignment -->
        <div class="slot-allocated-box">
          <div>
            <div style="font-size:11px;color:#1e40af;font-weight:700;text-transform:uppercase;">Optimal Slot Pre-Allocated</div>
            <div style="font-size:14px;font-weight:700;color:#0f172a;margin-top:2px;">
              Slot #${slot.slot_number} — ${slot.slot_type} (${slot.power_kw} kW, ${slot.connector_type})
            </div>
          </div>
          <button class="btn btn-primary" onclick="App.openBookingModal(${st.id}, ${slot.id}, '${st.name.replace(/'/g, "\\'")}')">
            ⚡ Confirm & Reserve Slot
          </button>
        </div>

        ${rationaleHtml}

        <!-- Factor breakdown -->
        <div style="display:flex;gap:8px;flex-wrap:wrap;font-size:11px;color:#64748b;margin-top:10px;">
          <span style="background:#f1f5f9;padding:3px 8px;border-radius:4px;">Proximity: <strong>${rec.metrics.proximity_score}</strong>/100</span>
          <span style="background:#f1f5f9;padding:3px 8px;border-radius:4px;">Availability: <strong>${rec.metrics.availability_score}</strong>/100</span>
          <span style="background:#f1f5f9;padding:3px 8px;border-radius:4px;">Power Rating: <strong>${rec.metrics.power_score}</strong>/100</span>
          <span style="background:#f1f5f9;padding:3px 8px;border-radius:4px;">Pricing: <strong>${rec.metrics.price_score}</strong>/100</span>
        </div>

        ${alternativesHtml}
      </div>
    `;
  },

  // ----------------- SLOT INSPECTION MODAL ----------------- //
  async inspectStationSlots(stationId) {
    try {
      const data = await this.api(`/api/stations/${stationId}`);
      if (!data.success || !data.station) return;

      const st = data.station;
      const titleEl = document.getElementById('inspector-station-title');
      const container = document.getElementById('inspector-slots-container');

      if (titleEl) {
        titleEl.textContent = `${st.name} — Physical Slots (${st.available_slots_count || 0}/${st.total_slots} Free)`;
      }

      if (container) {
        let html = '';
        const slots = st.slots || [];
        slots.forEach(slot => {
          let cardClass = 'avail';
          let statusLabel = 'Available';
          if (slot.status === 'Occupied') {
            cardClass = 'occ';
            statusLabel = 'Occupied';
          } else if (slot.status === 'Reserved') {
            cardClass = 'rsv';
            statusLabel = 'Reserved';
          } else if (slot.status === 'Maintenance') {
            cardClass = 'maint';
            statusLabel = 'Maintenance';
          }

          const vehText = slot.vehicle_number ? `Plate: ${slot.vehicle_number}` : 'No vehicle';

          const adminToggleBtn = (this.currentUser.role === 'admin') ? `
            <button class="btn btn-sm btn-secondary" style="margin-top:8px;font-size:10px;padding:3px 6px;" onclick="App.toggleSlotStatus(${slot.id}, '${slot.status}', ${st.id})">
              Toggle Status
            </button>
          ` : '';

          const userBookBtn = (slot.status === 'Available' && this.currentUser.role === 'user') ? `
            <button class="btn btn-sm btn-primary" style="margin-top:8px;font-size:10px;padding:3px 6px;" onclick="App.closeModal('modal-slot-inspector');App.openBookingModal(${st.id}, ${slot.id}, '${st.name.replace(/'/g, "\\'")}')">
              Book This
            </button>
          ` : '';

          html += `
            <div class="slot-card-item ${cardClass}">
              <div class="slot-num">Slot #${slot.slot_number}</div>
              <div class="slot-type-text">${slot.slot_type}</div>
              <div style="font-size:11px;font-weight:600;margin-top:2px;">${slot.power_kw} kW • ${slot.connector_type}</div>
              <div style="margin-top:4px;"><span class="badge badge-${cardClass === 'avail' ? 'available' : (cardClass === 'occ' ? 'occupied' : 'reserved')}">${statusLabel}</span></div>
              <div class="slot-vehicle">${vehText}</div>
              ${adminToggleBtn}
              ${userBookBtn}
            </div>
          `;
        });

        container.innerHTML = html;
      }

      this.openModal('modal-slot-inspector');
    } catch (err) {
      this.showToast(`Error loading station slots: ${err.message}`, 'error');
    }
  },

  async toggleSlotStatus(slotId, currentStatus, stationId) {
    const nextStatus = (currentStatus === 'Available') ? 'Occupied' : 'Available';
    const fakePlate = (nextStatus === 'Occupied') ? `EV-${Math.floor(100 + Math.random() * 899)}-SIM` : null;

    try {
      await this.api(`/api/slots/${slotId}`, {
        method: 'PUT',
        body: JSON.stringify({ status: nextStatus, vehicle_number: fakePlate })
      });

      this.showToast(`Slot status updated to: ${nextStatus}`);
      this.loadStats();
      this.loadStations();
      this.loadAnalytics();
      if (stationId) this.inspectStationSlots(stationId);
    } catch (err) {
      this.showToast(`Failed to toggle slot: ${err.message}`, 'error');
    }
  },

  // ----------------- RESERVATION & BOOKING ----------------- //
  openBookingModal(stationId, slotId, stationName) {
    document.getElementById('booking-station-id').value = stationId;
    document.getElementById('booking-slot-id').value = slotId || '';
    document.getElementById('booking-station-name').value = stationName || 'Selected Station';
    document.getElementById('booking-vehicle-model').value = this.currentUser.vehicleModel;
    document.getElementById('booking-vehicle-plate').value = this.currentUser.vehiclePlate;
    document.getElementById('booking-connector').value = this.currentUser.connector || 'CCS2';

    this.openModal('modal-booking');
  },

  async submitBooking(event) {
    event.preventDefault();

    const stationId = parseInt(document.getElementById('booking-station-id').value, 10);
    const slotIdVal = document.getElementById('booking-slot-id').value;
    const slotId = slotIdVal ? parseInt(slotIdVal, 10) : null;
    const vehicleModel = document.getElementById('booking-vehicle-model').value.trim();
    const vehiclePlate = document.getElementById('booking-vehicle-plate').value.trim();
    const connector = document.getElementById('booking-connector').value;
    const duration = parseFloat(document.getElementById('booking-duration').value);

    try {
      const res = await this.api('/api/reservations', {
        method: 'POST',
        body: JSON.stringify({
          user_id: this.currentUser.id,
          station_id: stationId,
          slot_id: slotId,
          vehicle_model: vehicleModel,
          vehicle_plate: vehiclePlate,
          connector_type: connector,
          duration_hours: duration
        })
      });

      if (!res.success) throw new Error(res.message);

      this.closeModal('modal-booking');
      this.showToast(`🎉 Reservation confirmed! Code: ${res.reservation_code}`);

      this.loadStats();
      this.loadStations();
      this.loadReservations();
      this.loadAnalytics();

      this.switchTab('reservations');
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  async loadReservations() {
    const searchVal = document.getElementById('booking-search-box')?.value || '';
    const params = new URLSearchParams({ q: searchVal });

    try {
      const data = await this.api(`/api/reservations?${params.toString()}`);
      if (!data.success) return;

      const list = data.reservations || [];
      this.renderUserReservationsTable(list);
      this.renderAdminReservationsTable(list);
    } catch (err) {
      console.warn("[Reservations Load Error]:", err);
    }
  },

  renderUserReservationsTable(list) {
    const tbody = document.getElementById('reservations-tbody');
    if (!tbody) return;

    const userList = list.filter(r => r.user_id === this.currentUser.id || this.currentUser.role === 'admin');

    if (userList.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:30px;color:#94a3b8;">No charging sessions on record. Reserve a slot through Smart Allocation!</td></tr>`;
      return;
    }

    let html = '';
    userList.forEach(r => {
      const isEligibleForCancel = (r.status === 'Active' || r.status === 'Pending');
      const statusBadge = r.status === 'Active'
        ? `<span class="badge badge-available">● Active Session</span>`
        : (r.status === 'Pending' ? `<span class="badge badge-reserved">⏱ Pending</span>` : `<span class="badge" style="background:#f1f5f9;color:#64748b;">${r.status}</span>`);

      html += `
        <tr>
          <td><strong style="color:#1e3a8a;font-family:monospace;">${r.reservation_code}</strong></td>
          <td>
            <strong>${r.station_name}</strong>
            <div style="font-size:11.5px;color:#64748b;">${r.station_address}</div>
          </td>
          <td>Slot #${r.slot_number} <small>(${r.connector_type})</small></td>
          <td>${r.vehicle_model} <div style="font-size:11px;font-family:monospace;color:#475569;">${r.vehicle_plate}</div></td>
          <td>${r.start_time} <div style="font-size:11px;color:#64748b;">${r.duration_hours} hr (${r.estimated_energy_kwh} kWh)</div></td>
          <td><strong style="color:#059669;">₹${r.estimated_cost.toFixed(2)}</strong></td>
          <td>${statusBadge}</td>
          <td>
            ${isEligibleForCancel ? `
              <button class="btn btn-sm btn-danger" onclick="App.cancelReservation(${r.id})">
                Cancel
              </button>
            ` : `
              <span style="font-size:11px;color:#94a3b8;">Completed</span>
            `}
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  },

  renderAdminReservationsTable(list) {
    const tbody = document.getElementById('admin-reservations-tbody');
    if (!tbody) return;

    if (list.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:#94a3b8;">No reservations found</td></tr>`;
      return;
    }

    let html = '';
    list.forEach(r => {
      html += `
        <tr>
          <td><strong style="font-family:monospace;">${r.reservation_code}</strong></td>
          <td>${r.user_full_name} <div style="font-size:11px;color:#64748b;">${r.user_email}</div></td>
          <td>${r.station_name}</td>
          <td>Slot #${r.slot_number}</td>
          <td><code style="font-weight:700;">${r.vehicle_plate}</code></td>
          <td><span class="badge ${r.status === 'Active' ? 'badge-available' : (r.status === 'Cancelled' ? 'badge-occupied' : 'badge-reserved')}">${r.status}</span></td>
          <td>
            ${r.status === 'Active' ? `
              <div style="display:flex;gap:4px;">
                <button class="btn btn-sm btn-secondary" onclick="App.updateReservationStatus(${r.id}, 'Completed')">Complete</button>
                <button class="btn btn-sm btn-danger" onclick="App.cancelReservation(${r.id})">Cancel</button>
              </div>
            ` : `<span style="font-size:11.5px;color:#94a3b8;">—</span>`}
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  },

  async cancelReservation(resId) {
    if (!confirm("Are you sure you want to cancel this reservation and release the charging slot?")) {
      return;
    }

    try {
      const res = await this.api(`/api/reservations/${resId}/cancel`, { method: 'PUT' });
      if (!res.success) throw new Error(res.message);

      this.showToast("Reservation cancelled and charging slot released back to grid.");
      this.loadStats();
      this.loadStations();
      this.loadReservations();
      this.loadAnalytics();
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  async updateReservationStatus(resId, status) {
    try {
      const res = await this.api(`/api/reservations/${resId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status })
      });
      if (!res.success) throw new Error(res.message);

      this.showToast(`Reservation marked as ${status}`);
      this.loadStats();
      this.loadStations();
      this.loadReservations();
      this.loadAnalytics();
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  // ----------------- ADMIN STATION MANAGEMENT ----------------- //
  openAddStationModal() {
    document.getElementById('station-form-id').value = '';
    document.getElementById('station-form-title').textContent = 'Add New Charging Station';
    document.getElementById('st-name').value = '';
    document.getElementById('st-address').value = '';
    document.getElementById('st-city').value = 'Bengaluru';
    document.getElementById('st-zone').value = 'Metro Zone';
    document.getElementById('st-lat').value = this.currentLocation.lat;
    document.getElementById('st-lng').value = this.currentLocation.lng;
    document.getElementById('st-slots').value = '4';
    document.getElementById('st-power').value = '60';
    document.getElementById('st-connectors').value = 'CCS2, Type 2';
    document.getElementById('st-price').value = '15.00';
    document.getElementById('st-operator').value = 'Tata Power EZ';

    this.openModal('modal-station-form');
  },

  async openEditStationModal(stationId) {
    try {
      const data = await this.api(`/api/stations/${stationId}`);
      if (!data.success || !data.station) return;

      const st = data.station;
      document.getElementById('station-form-id').value = st.id;
      document.getElementById('station-form-title').textContent = `Edit Station: ${st.name}`;
      document.getElementById('st-name').value = st.name;
      document.getElementById('st-address').value = st.address;
      document.getElementById('st-city').value = st.city;
      document.getElementById('st-zone').value = st.zone;
      document.getElementById('st-lat').value = st.latitude;
      document.getElementById('st-lng').value = st.longitude;
      document.getElementById('st-slots').value = st.total_slots;
      document.getElementById('st-power').value = st.power_kw;
      document.getElementById('st-connectors').value = st.connector_types;
      document.getElementById('st-price').value = st.price_per_kwh;
      document.getElementById('st-operator').value = st.operator;

      this.openModal('modal-station-form');
    } catch (err) {
      this.showToast(`Error fetching station: ${err.message}`, 'error');
    }
  },

  async submitStationForm(event) {
    event.preventDefault();

    const id = document.getElementById('station-form-id').value;
    const payload = {
      name: document.getElementById('st-name').value.trim(),
      address: document.getElementById('st-address').value.trim(),
      city: document.getElementById('st-city').value.trim(),
      zone: document.getElementById('st-zone').value.trim(),
      latitude: parseFloat(document.getElementById('st-lat').value),
      longitude: parseFloat(document.getElementById('st-lng').value),
      total_slots: parseInt(document.getElementById('st-slots').value, 10),
      power_kw: parseFloat(document.getElementById('st-power').value),
      connector_types: document.getElementById('st-connectors').value.trim(),
      price_per_kwh: parseFloat(document.getElementById('st-price').value),
      operator: document.getElementById('st-operator').value.trim(),
      status: 'Active'
    };

    try {
      if (id) {
        await this.api(`/api/stations/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
        this.showToast("Station updated successfully!");
      } else {
        await this.api('/api/stations', { method: 'POST', body: JSON.stringify(payload) });
        this.showToast("New charging station registered successfully!");
      }

      this.closeModal('modal-station-form');
      this.loadStats();
      this.loadStations();
      this.loadAnalytics();
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  async deleteStation(stationId, stationName) {
    if (!confirm(`Are you sure you want to permanently delete station "${stationName}" and its slots?`)) {
      return;
    }

    try {
      await this.api(`/api/stations/${stationId}`, { method: 'DELETE' });
      this.showToast(`Station "${stationName}" removed from network.`);
      this.loadStats();
      this.loadStations();
      this.loadAnalytics();
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  },

  async loadUsers() {
    const tbody = document.getElementById('admin-users-tbody');
    if (!tbody) return;

    try {
      const data = await this.api('/api/users');
      if (!data.success) return;

      let html = '';
      (data.users || []).forEach(u => {
        html += `
          <tr>
            <td><strong>#${u.id}</strong></td>
            <td>
              <strong>${u.full_name}</strong>
              <div style="font-size:11px;color:#64748b;">${u.email}</div>
            </td>
            <td><code>${u.username}</code></td>
            <td><span class="badge ${u.role === 'admin' ? 'badge-power' : 'badge-available'}">${u.role}</span></td>
            <td>${u.vehicle_model || '—'} <span style="font-size:11px;color:#64748b;">(${u.vehicle_plate || '—'})</span></td>
            <td>${u.preferred_connector || 'CCS2'}</td>
          </tr>
        `;
      });
      tbody.innerHTML = html;
    } catch (err) {
      console.warn("[Users Load Error]:", err);
    }
  },

  // ----------------- DEMO RESET ----------------- //
  async resetDemoData() {
    if (!confirm("Reset database to clean initial state with 12 demo stations and sample bookings?")) {
      return;
    }

    try {
      const res = await this.api('/api/reset-data', { method: 'POST' });
      this.showToast(res.message || "Database reset to pristine state!");
      this.loadStats();
      this.loadStations();
      this.loadReservations();
      this.loadUsers();
      this.loadAnalytics();
      this.runSmartAllocation(false);
    } catch (err) {
      this.showToast(`Failed to reset data: ${err.message}`, 'error');
    }
  },

  // ----------------- MODALS & TOASTS ----------------- //
  setupModals() {
    document.querySelectorAll('.modal-backdrop').forEach(modal => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          modal.classList.remove('open');
        }
      });
    });
  },

  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('open');
  },

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('open');
  },

  showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'error' ? '✕' : (type === 'warn' ? '⚠️' : '✓');
    toast.innerHTML = `<span style="font-weight:700;">${icon}</span><span>${message}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }
};

// Auto-boot on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
