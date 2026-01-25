/**
 * NanoRTK Admin - Main Application Logic
 * 
 * Handles configuration loading, websocket communication, map interaction,
 * and system status monitoring.
 */

// Global State
const state = {
    socket: null,
    isConnected: false,
    map: null,
    marker: null,
    currentConfig: null,
    statusInterval: null
};

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', init);

async function init() {
    // Set current year in footer
    const yearElem = document.getElementById('currentYear');
    if (yearElem) yearElem.textContent = new Date().getFullYear();

    try {
        showLoading(true);

        await Promise.all([
            loadConfig(),
            loadServiceStatus(),
            loadSerialPorts()
        ]);

        initSocket();
        initMap();

        // Start system monitor
        updateSystemStatus();
        state.statusInterval = setInterval(updateSystemStatus, 5000);

        bindEvents();

        addLogEntry({
            level: 'INFO',
            message: 'System initialized. Waiting for logs...'
        });

    } catch (error) {
        console.error('Initialization failed:', error);
        addLogEntry({
            level: 'ERROR',
            message: 'Init failed: ' + error.message
        });
    } finally {
        showLoading(false);
    }
}

function showLoading(show) {
    const el = document.getElementById('loadingOverlay');
    if (el) el.style.display = show ? 'flex' : 'none';
}

// ============================================================================
// Data Loading & API
// ============================================================================

async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) throw new Error('Failed to fetch config');

        state.currentConfig = await response.json();

        // Populate inputs
        setInputValue('serialBaudrate', state.currentConfig.serial?.baudrate || 115200);
        setInputValue('ntripHost', state.currentConfig.ntrip?.host || '');
        setInputValue('ntripPort', state.currentConfig.ntrip?.port || 2101);
        setInputValue('ntripMountpoint', state.currentConfig.ntrip?.mountpoint || '');
        setInputValue('ntripUsername', state.currentConfig.ntrip?.username || '');
        setInputValue('ntripPassword', state.currentConfig.ntrip?.password || '');
        setInputValue('reconnectMaxRetries', state.currentConfig.reconnect?.max_retries || 5);
        setInputValue('reconnectRetryDelay', state.currentConfig.reconnect?.retry_delay || 5.0);
        setInputValue('baseStationLatitude', state.currentConfig.base_station?.latitude || 0);
        setInputValue('baseStationLongitude', state.currentConfig.base_station?.longitude || 0);
        setInputValue('baseStationAltitude', state.currentConfig.base_station?.altitude || 0);
        setInputValue('baseStationArpAverage', state.currentConfig.base_station?.enable_arp_average || 0);

        // Update port selection if available
        const portSelect = document.getElementById('serialPortSelect');
        if (portSelect && state.currentConfig.serial?.port) {
            portSelect.value = state.currentConfig.serial.port;
        }

    } catch (error) {
        console.error('Config load error:', error);
        throw error;
    }
}

function setInputValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value;
}

async function loadServiceStatus() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) throw new Error('Status fetch failed');
        const data = await response.json();
        updateServiceStatusBadge(data.running);
    } catch (error) {
        console.warn('Service status load failed:', error);
        updateServiceStatusBadge(false);
    }
}

function updateServiceStatusBadge(running) {
    const badge = document.getElementById('serviceStatusBadge');
    if (!badge) return;

    if (running) {
        badge.className = 'badge bg-success';
        badge.textContent = 'RUNNING';
    } else {
        badge.className = 'badge bg-secondary';
        badge.textContent = 'STOPPED';
    }
}

async function loadSerialPorts() {
    const select = document.getElementById('serialPortSelect');
    if (!select) return;

    const currentPort = state.currentConfig?.serial?.port || '';

    try {
        const response = await fetch('/api/serial-ports');
        if (!response.ok) throw new Error('Ports fetch failed');

        const data = await response.json();
        const ports = data.ports;

        select.innerHTML = '';
        let found = false;

        ports.forEach(port => {
            const option = document.createElement('option');
            option.value = port;
            option.textContent = port;
            if (port === currentPort) {
                option.selected = true;
                found = true;
            }
            select.appendChild(option);
        });

        if (!found && currentPort) {
            const option = document.createElement('option');
            option.value = currentPort;
            option.textContent = `${currentPort} (Offline)`;
            option.selected = true;
            select.appendChild(option);
        }

        if (ports.length === 0 && !currentPort) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No ports detected';
            select.appendChild(option);
        }
    } catch (error) {
        console.error('Serial ports error:', error);
    }
}

async function updateSystemStatus() {
    try {
        const response = await fetch('/api/system');
        if (!response.ok) return; // Silent fail
        const data = await response.json();

        // CPU Temp
        updateProgressBar('cpuTempProgress', data.cpu_temp, 100, ' °C');
        const cpuText = document.getElementById('cpuTempText');
        if (cpuText) cpuText.textContent = data.cpu_temp ? `Temp: ${data.cpu_temp.toFixed(1)} °C` : 'N/A';

        // Memory
        updateProgressBar('memoryProgress', data.memory_percent, 100, ' %');
        const memText = document.getElementById('memoryText');
        if (memText && data.memory_total) {
            const totalGB = (data.memory_total / (1024 ** 3)).toFixed(1);
            const availGB = (data.memory_available / (1024 ** 3)).toFixed(1);
            memText.textContent = `Avail: ${availGB} GB / Total: ${totalGB} GB`;
        }

        // Info
        setText('uptimeText', data.uptime_str);
        setText('hardwareText', data.hardware);
        setText('systemText', data.system);

    } catch (error) {
        console.warn('System status update error:', error);
    }
}

function updateProgressBar(id, value, max, unit) {
    const bar = document.getElementById(id);
    if (!bar) return;

    if (value === null || value === undefined) {
        bar.style.width = '0%';
        bar.textContent = 'N/A';
        return;
    }

    const percent = Math.min((value / max) * 100, 100);
    bar.style.width = `${percent}%`;
    bar.textContent = `${value.toFixed(1)}${unit}`;

    // Color logic
    if (percent >= 90) bar.className = 'progress-bar bg-danger';
    else if (percent >= 70) bar.className = 'progress-bar bg-warning';
    else bar.className = 'progress-bar bg-success';
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text || '--';
}

// ============================================================================
// Socket.IO
// ============================================================================

function initSocket() {
    state.socket = io(window.location.origin, {
        transports: ['websocket', 'polling']
    });

    state.socket.on('connect', () => {
        state.isConnected = true;
        updateSocketStatus(true);
        addLogEntry({ level: 'DEBUG', message: 'Socket connected' });
    });

    state.socket.on('disconnect', () => {
        state.isConnected = false;
        updateSocketStatus(false);
        addLogEntry({ level: 'DEBUG', message: 'Socket disconnected' });
    });

    state.socket.on('log', (data) => {
        addLogEntry(data);
    });
}

function updateSocketStatus(connected) {
    const textStatus = document.getElementById('socketStatusText');
    const dotStatus = document.querySelector('#socketStatus .socket-status');

    if (connected) {
        if (textStatus) textStatus.textContent = 'Connected';
        if (dotStatus) dotStatus.className = 'socket-status socket-connected';
    } else {
        if (textStatus) textStatus.textContent = 'Disconnected';
        if (dotStatus) dotStatus.className = 'socket-status socket-disconnected';
    }
}

function addLogEntry(log) {
    const container = document.getElementById('logTerminal');
    if (!container) return;

    const entry = document.createElement('div');
    entry.className = `log-entry ${log.level.toLowerCase()}`;

    // Format timestamp
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });

    entry.innerHTML = `<strong>[${time}] [${log.level}]</strong> ${log.message}`;
    container.appendChild(entry);

    // Auto scroll if near bottom
    if (container.scrollHeight - container.scrollTop <= container.clientHeight + 100) {
        container.scrollTop = container.scrollHeight;
    }
}

// ============================================================================
// Map
// ============================================================================

function initMap() {
    const latIn = document.getElementById('baseStationLatitude');
    const lngIn = document.getElementById('baseStationLongitude');

    if (!latIn || !lngIn) return;

    let lat = parseFloat(latIn.value) || 39.9042;
    let lng = parseFloat(lngIn.value) || 116.4074;

    state.map = L.map('map').setView([lat, lng], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(state.map);

    state.marker = L.marker([lat, lng], { draggable: true }).addTo(state.map);

    // Map events
    state.marker.on('dragend', (e) => {
        const pos = state.marker.getLatLng();
        latIn.value = pos.lat.toFixed(9);
        lngIn.value = pos.lng.toFixed(9);
    });

    state.map.on('click', (e) => {
        state.marker.setLatLng(e.latlng);
        latIn.value = e.latlng.lat.toFixed(9);
        lngIn.value = e.latlng.lng.toFixed(9);
    });

    // Input events
    const updateMarker = () => {
        const newLat = parseFloat(latIn.value);
        const newLng = parseFloat(lngIn.value);
        if (!isNaN(newLat) && !isNaN(newLng)) {
            state.marker.setLatLng([newLat, newLng]);
            state.map.setView([newLat, newLng]);
        }
    };

    latIn.addEventListener('change', updateMarker);
    lngIn.addEventListener('change', updateMarker);
}

// ============================================================================
// Events
// ============================================================================

function bindEvents() {
    // Clear Logs
    bindClick('btnClearLogs', () => {
        const term = document.getElementById('logTerminal');
        if (term) term.innerHTML = '';
    });

    // Refresh Ports
    bindClick('btnRefreshPorts', loadSerialPorts);

    // Start Service
    bindClick('btnStart', () => controlService('start'));

    // Stop Service
    bindClick('btnStop', () => controlService('stop'));

    // Config Form
    const form = document.getElementById('configForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const config = Object.fromEntries(formData.entries());

            try {
                const res = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                const data = await res.json();
                alert(data.message || 'Config saved');
                await loadConfig();
            } catch (err) {
                console.error(err);
                alert('Failed to save config');
            }
        });
    }
}

function bindClick(id, handler) {
    const el = document.getElementById(id);
    if (el) el.addEventListener('click', handler);
}

async function controlService(action) {
    try {
        const res = await fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
        const data = await res.json();
        // alert(data.message); // Optional: silent success is better for tech UI
        await loadServiceStatus();
    } catch (err) {
        console.error(err);
        alert(`Failed to ${action} service`);
    }
}
