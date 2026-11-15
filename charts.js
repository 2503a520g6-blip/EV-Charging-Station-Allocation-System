/**
 * EV Charging Station Allocation System - Master Visualization Engine
 * 100% offline-ready, responsive Canvas & SVG chart engine.
 * Renders all 7 analytical charts using real database values with zero CDN dependencies.
 */

const Charts = {
  // Cache of active chart canvas contexts to prevent duplicate rendering
  activeCharts: {},

  /**
   * Helper to clean up existing chart container before redrawing
   */
  prepareContainer(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return null;
    container.innerHTML = '';
    return container;
  },

  /**
   * Shows a graceful empty state message when no data exists
   */
  renderEmptyState(container, message = "No data available in database") {
    container.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;min-height:160px;color:#94a3b8;font-size:12.5px;text-align:center;padding:20px;">
        <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="#cbd5e1" stroke-width="1.8" style="margin-bottom:8px;">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <span>${message}</span>
      </div>
    `;
  },

  /**
   * 1. Charging Station Availability Chart (Donut)
   */
  renderStationAvailabilityChart(containerId, data) {
    const container = this.prepareContainer(containerId);
    if (!container) return;

    const available = Number(data?.available) || 0;
    const occupied = Number(data?.occupied) || 0;
    const total = available + occupied;

    if (total === 0) {
      this.renderEmptyState(container, "No stations registered");
      return;
    }

    const availPct = Math.round((available / total) * 100);
    const size = 180;
    const strokeWidth = 24;
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const center = size / 2;

    const availDash = (available / total) * circumference;
    const occDash = (occupied / total) * circumference;

    const svg = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%;">
        <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
          <circle cx="${center}" cy="${center}" r="${radius}" fill="none" stroke="#e2e8f0" stroke-width="${strokeWidth}" />
          <circle cx="${center}" cy="${center}" r="${radius}" fill="none" stroke="#059669" stroke-width="${strokeWidth}"
                  stroke-dasharray="${availDash} ${circumference}" stroke-dashoffset="0"
                  transform="rotate(-90 ${center} ${center})">
            <title>Available: ${available} (${availPct}%)</title>
          </circle>
          <circle cx="${center}" cy="${center}" r="${radius}" fill="none" stroke="#ef4444" stroke-width="${strokeWidth}"
                  stroke-dasharray="${occDash} ${circumference}" stroke-dashoffset="-${availDash}"
                  transform="rotate(-90 ${center} ${center})">
            <title>100% Full / Occupied: ${occupied} (${100 - availPct}%)</title>
          </circle>
          <text x="${center}" y="${center - 3}" text-anchor="middle" font-size="22" font-weight="800" fill="#0f172a">${availPct}%</text>
          <text x="${center}" y="${center + 15}" text-anchor="middle" font-size="10.5" font-weight="600" fill="#64748b" text-transform="uppercase">Available</text>
        </svg>
        <div style="display:flex;gap:14px;justify-content:center;margin-top:12px;font-size:11.5px;color:#475569;">
          <span style="display:flex;align-items:center;gap:6px;">
            <span style="width:10px;height:10px;background:#059669;border-radius:2px;"></span>
            Available (${available})
          </span>
          <span style="display:flex;align-items:center;gap:6px;">
            <span style="width:10px;height:10px;background:#ef4444;border-radius:2px;"></span>
            Full (${occupied})
          </span>
        </div>
      </div>
    `;
    container.innerHTML = svg;
  },

  /**
   * 2. Occupied vs Available Slots Chart (Multi-color Donut)
   */
  renderSlotAvailabilityChart(containerId, data) {
    const container = this.prepareContainer(containerId);
    if (!container) return;

    if (!data) {
      this.renderEmptyState(container, "No slot data available");
      return;
    }

    const available = Number(data.available) || 0;
    const occupied = Number(data.occupied) || 0;
    const reserved = Number(data.reserved) || 0;
    const maintenance = Number(data.maintenance) || 0;
    const total = available + occupied + reserved + maintenance;

    if (total === 0) {
      this.renderEmptyState(container, "No active slots found");
      return;
    }

    const size = 180;
    const strokeWidth = 24;
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const center = size / 2;

    const slices = [
      { key: 'Available', val: available, color: '#10b981' },
      { key: 'Occupied', val: occupied, color: '#ef4444' },
      { key: 'Reserved', val: reserved, color: '#f59e0b' },
      { key: 'Maintenance', val: maintenance, color: '#64748b' }
    ];

    let accumulatedOffset = 0;
    let paths = '';

    slices.forEach(s => {
      if (s.val <= 0) return;
      const dash = (s.val / total) * circumference;
      paths += `
        <circle cx="${center}" cy="${center}" r="${radius}" fill="none" stroke="${s.color}" stroke-width="${strokeWidth}"
                stroke-dasharray="${dash} ${circumference}" stroke-dashoffset="-${accumulatedOffset}"
                transform="rotate(-90 ${center} ${center})">
          <title>${s.key}: ${s.val} slots (${Math.round((s.val / total) * 100)}%)</title>
        </circle>
      `;
      accumulatedOffset += dash;
    });

    const freePct = Math.round((available / total) * 100);

    const svg = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%;">
        <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
          <circle cx="${center}" cy="${center}" r="${radius}" fill="none" stroke="#e2e8f0" stroke-width="${strokeWidth}" />
          ${paths}
          <text x="${center}" y="${center - 3}" text-anchor="middle" font-size="22" font-weight="800" fill="#0f172a">${freePct}%</text>
          <text x="${center}" y="${center + 15}" text-anchor="middle" font-size="10.5" font-weight="600" fill="#64748b" text-transform="uppercase">Free Slots</text>
        </svg>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 14px;margin-top:12px;font-size:11.5px;color:#475569;">
          <span style="display:flex;align-items:center;gap:6px;">
            <span style="width:10px;height:10px;background:#10b981;border-radius:2px;"></span>
            Available (${available})
          </span>
          <span style="display:flex;align-items:center;gap:6px;">
            <span style="width:10px;height:10px;background:#ef4444;border-radius:2px;"></span>
            Occupied (${occupied})
          </span>
          <span style="display:flex;align-items:center;gap:6px;">
            <span style="width:10px;height:10px;background:#f59e0b;border-radius:2px;"></span>
            Reserved (${reserved})
          </span>
          <span style="display:flex;align-items:center;gap:6px;">
            <span style="width:10px;height:10px;background:#64748b;border-radius:2px;"></span>
            Maint (${maintenance})
          </span>
        </div>
      </div>
    `;
    container.innerHTML = svg;
  },

  /**
   * 3. Charging Stations by Location Chart (Bar Chart)
   */
  renderLocationDistributionChart(containerId, locationData) {
    const container = this.prepareContainer(containerId);
    if (!container) return;

    if (!locationData || locationData.length === 0) {
      this.renderEmptyState(container, "No zone capacity data");
      return;
    }

    let barsHtml = '';
    const maxVal = Math.max(...locationData.map(z => Number(z.total_slots || z.total_zone_slots) || 1), 8);

    locationData.forEach(z => {
      const zoneName = z.zone || 'Unknown Zone';
      const total = Number(z.total_slots || z.total_zone_slots) || 0;
      const free = Number(z.free_slots) || 0;
      const freePct = total > 0 ? (free / total) * 100 : 0;
      const stCount = z.station_count ? ` (${z.station_count} hubs)` : '';

      barsHtml += `
        <div style="margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;">
            <span style="font-weight:600;color:#1e3a8a;">${zoneName}${stCount}</span>
            <span style="color:#64748b;font-weight:600;">${free} free / ${total} total</span>
          </div>
          <div style="background-color:#e2e8f0;height:10px;border-radius:999px;overflow:hidden;display:flex;width:100%;" title="${zoneName}: ${free} free out of ${total} total slots">
            <div style="background-color:#059669;height:100%;width:${freePct}%;transition:width 0.4s ease;"></div>
            <div style="background-color:#ef4444;height:100%;width:${100 - freePct}%;"></div>
          </div>
        </div>
      `;
    });

    container.innerHTML = barsHtml;
  },

  /**
   * 4. Daily Charging Sessions Chart (Histogram / Bar Graph)
   */
  renderDailySessionsChart(containerId, sessionData) {
    const container = this.prepareContainer(containerId);
    if (!container) return;

    if (!sessionData || sessionData.length === 0) {
      this.renderEmptyState(container, "No charging session records logged yet");
      return;
    }

    const maxSessions = Math.max(...sessionData.map(d => Number(d.sessions_count) || 1), 4);
    let barsSvg = '';
    const chartHeight = 150;
    const barWidth = 32;
    const gap = 20;
    const totalWidth = sessionData.length * (barWidth + gap);

    sessionData.forEach((d, idx) => {
      const cnt = Number(d.sessions_count) || 0;
      const height = Math.round((cnt / maxSessions) * (chartHeight - 40));
      const x = idx * (barWidth + gap) + 10;
      const y = chartHeight - height - 25;
      const dateLabel = (d.session_date || '').slice(5); // e.g. "11-15"

      barsSvg += `
        <g>
          <rect x="${x}" y="${y}" width="${barWidth}" height="${height}" rx="4" fill="#2563eb" opacity="0.9">
            <title>${d.session_date}: ${cnt} sessions (${d.total_energy || 0} kWh)</title>
          </rect>
          <text x="${x + barWidth / 2}" y="${y - 6}" text-anchor="middle" font-size="11" font-weight="700" fill="#1e3a8a">${cnt}</text>
          <text x="${x + barWidth / 2}" y="${chartHeight - 8}" text-anchor="middle" font-size="10" font-weight="600" fill="#64748b">${dateLabel}</text>
        </g>
      `;
    });

    const svg = `
      <div style="width:100%;overflow-x:auto;">
        <svg width="${Math.max(totalWidth + 20, 280)}" height="${chartHeight}" style="display:block;margin:0 auto;">
          <line x1="0" y1="${chartHeight - 24}" x2="100%" y2="${chartHeight - 24}" stroke="#e2e8f0" stroke-width="1.5" />
          ${barsSvg}
        </svg>
      </div>
      <div style="text-align:center;font-size:11px;color:#64748b;margin-top:6px;">Sessions logged by date</div>
    `;

    container.innerHTML = svg;
  },

  /**
   * 5. Energy Consumption Chart by Operator (Horizontal Bar Chart)
   */
  renderEnergyByOperatorChart(containerId, operatorData) {
    const container = this.prepareContainer(containerId);
    if (!container) return;

    if (!operatorData || operatorData.length === 0) {
      this.renderEmptyState(container, "No energy consumption data");
      return;
    }

    const maxEnergy = Math.max(...operatorData.map(o => Number(o.energy_kwh) || 1), 10);
    let html = '';

    operatorData.forEach(o => {
      const kwh = Number(o.energy_kwh) || 0;
      const pct = Math.min(100, Math.round((kwh / maxEnergy) * 100));
      const revText = o.revenue ? ` • ₹${Number(o.revenue).toFixed(2)}` : '';

      html += `
        <div style="margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;">
            <span style="font-weight:600;color:#0f172a;">${o.operator}</span>
            <span style="color:#2563eb;font-weight:700;">${kwh.toFixed(1)} kWh<small style="color:#64748b;font-weight:500;">${revText}</small></span>
          </div>
          <div style="background-color:#eff6ff;height:12px;border-radius:999px;overflow:hidden;border:1px solid #bfdbfe;">
            <div style="background:linear-gradient(90deg, #3b82f6 0%, #1d4ed8 100%);height:100%;width:${pct}%;border-radius:999px;transition:width 0.4s ease;"></div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  },

  /**
   * 6. Booking Statistics by Status (Segmented Breakdown)
   */
  renderBookingStatsChart(containerId, bookingStats) {
    const container = this.prepareContainer(containerId);
    if (!container) return;

    if (!bookingStats || Object.keys(bookingStats).length === 0) {
      this.renderEmptyState(container, "No bookings recorded yet");
      return;
    }

    const total = Object.values(bookingStats).reduce((a, b) => a + Number(b), 0);
    if (total === 0) {
      this.renderEmptyState(container, "No bookings recorded yet");
      return;
    }

    const statusColors = {
      'Active': '#10b981',
      'Completed': '#3b82f6',
      'Pending': '#f59e0b',
      'Cancelled': '#ef4444'
    };

    let segmentsHtml = '';
    let legendHtml = '';

    for (const [status, count] of Object.entries(bookingStats)) {
      const cnt = Number(count) || 0;
      if (cnt <= 0) continue;
      const pct = (cnt / total) * 100;
      const color = statusColors[status] || '#64748b';

      segmentsHtml += `
        <div style="background-color:${color};width:${pct}%;height:100%;transition:width 0.3s ease;" title="${status}: ${cnt} (${Math.round(pct)}%)"></div>
      `;

      legendHtml += `
        <div style="display:flex;align-items:center;gap:6px;font-size:12px;">
          <span style="width:10px;height:10px;background-color:${color};border-radius:2px;"></span>
          <span style="color:#1e293b;font-weight:600;">${status}:</span>
          <span style="color:#64748b;font-weight:500;">${cnt} (${Math.round(pct)}%)</span>
        </div>
      `;
    }

    const html = `
      <div style="display:flex;flex-direction:column;gap:14px;padding:8px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:13px;font-weight:700;color:#0f172a;">Total Bookings: ${total}</span>
          <span style="font-size:11px;color:#64748b;font-weight:500;">Across All Stations</span>
        </div>
        <div style="background-color:#e2e8f0;height:16px;border-radius:999px;overflow:hidden;display:flex;width:100%;">
          ${segmentsHtml}
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 12px;margin-top:4px;">
          ${legendHtml}
        </div>
      </div>
    `;

    container.innerHTML = html;
  },

  /**
   * 7. Charging Station Utilization Chart (Horizontal Progress List)
   */
  renderUtilizationChart(containerId, utilizationData) {
    const container = this.prepareContainer(containerId);
    if (!container) return;

    if (!utilizationData || utilizationData.length === 0) {
      this.renderEmptyState(container, "No station utilization data");
      return;
    }

    let html = '';
    utilizationData.forEach(st => {
      const rate = Number(st.utilization_pct) || 0;
      const barColor = rate >= 75 ? '#ef4444' : (rate >= 40 ? '#f59e0b' : '#10b981');

      html += `
        <div style="margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;">
            <span style="font-weight:600;color:#0f172a;">${st.name}</span>
            <span style="font-weight:700;color:${barColor};">${rate}% <small style="color:#64748b;font-weight:500;">(${st.busy_slots}/${st.total_slots} busy)</small></span>
          </div>
          <div style="background-color:#f1f5f9;height:9px;border-radius:999px;overflow:hidden;border:1px solid #e2e8f0;">
            <div style="background-color:${barColor};height:100%;width:${rate}%;border-radius:999px;transition:width 0.4s ease;"></div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  }
};
