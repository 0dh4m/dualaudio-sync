/**
 * Copyright (C) 2026 Adham Cherkaoui Eddeqaqi (0dh4m). All rights reserved.
 * Proprietary and confidential. Unauthorized copying or distribution is strictly prohibited.
 * Author: Adham Cherkaoui Eddeqaqi (0dh4m) <adamcherkaoui99@gmail.com>
 * GitHub: https://github.com/0dh4m
 */

// DualAudio Sync Frontend Controller (English)
let isCalibrating = false;
let pollInterval = null;

// DOM Elements
const autopilotPill = document.getElementById('autopilot-pill');
const autopilotText = document.getElementById('autopilot-text');
const btnRestartStream = document.getElementById('btn-restart-stream');
const btnToggleNotifs = document.getElementById('btn-toggle-notifs');
const shieldStatusText = document.getElementById('shield-status-text');
const heroShieldTag = document.getElementById('hero-shield-tag');
const heroShieldText = document.getElementById('hero-shield-text');

// Sonos Elements
const sonosStatusBadge = document.getElementById('sonos-status-badge');
const sonosStatusText = document.getElementById('sonos-status-text');
const sonosDeviceName = document.getElementById('sonos-device-name');
const sonosIpDisplay = document.getElementById('sonos-ip-display');
const btnEditSonosIp = document.getElementById('btn-edit-sonos-ip');
const sonosVolSlider = document.getElementById('sonos-vol-slider');
const sonosVolVal = document.getElementById('sonos-vol-val');
const btnSonosMute = document.getElementById('btn-sonos-mute');

// Citytek Elements
const citytekStatusBadge = document.getElementById('citytek-status-badge');
const citytekStatusText = document.getElementById('citytek-status-text');
const citytekDeviceDropdown = document.getElementById('citytek-device-dropdown');
const citytekVolSlider = document.getElementById('citytek-vol-slider');
const citytekVolVal = document.getElementById('citytek-vol-val');
const btnCitytekMute = document.getElementById('btn-citytek-mute');

// Sync Elements
const syncDelaySlider = document.getElementById('sync-delay-slider');
const delayNumDisplay = document.getElementById('delay-num-display');
const btnCalibrateBeat = document.getElementById('btn-calibrate-beat');
const calibrateBtnText = document.getElementById('calibrate-btn-text');

// Master Controls
const masterVolSlider = document.getElementById('master-vol-slider');
const masterVolVal = document.getElementById('master-vol-val');
const btnMasterMute = document.getElementById('btn-master-mute');
const vuLeft = document.getElementById('vu-left');
const vuRight = document.getElementById('vu-right');
const audioActivityStatus = document.getElementById('audio-activity-status');
const footerStreamUrl = document.getElementById('footer-stream-url');

// Modal
const modalSonosIp = document.getElementById('modal-sonos-ip');
const inputManualIp = document.getElementById('input-manual-ip');
const btnCloseModal = document.getElementById('btn-close-modal');
const btnSaveManualIp = document.getElementById('btn-save-manual-ip');


document.addEventListener('DOMContentLoaded', () => {
    restoreCachedSettings();
    initListeners();
    loadAudioDevices();
    startPolling();
});

// Restore settings from localStorage immediately on page load / hard refresh
function restoreCachedSettings() {
    try {
        const master = localStorage.getItem('master_volume');
        if (master !== null) {
            masterVolSlider.value = master;
            masterVolVal.textContent = master + '%';
        }
        const citytek = localStorage.getItem('citytek_volume');
        if (citytek !== null) {
            citytekVolSlider.value = citytek;
            citytekVolVal.textContent = citytek + '%';
        }
        const sonos = localStorage.getItem('sonos_volume');
        if (sonos !== null) {
            sonosVolSlider.value = sonos;
            sonosVolVal.textContent = sonos + '%';
        }
        const delay = localStorage.getItem('delay_ms');
        if (delay !== null) {
            syncDelaySlider.value = delay;
            delayNumDisplay.textContent = delay;
        }
        const boost = localStorage.getItem('preamp_gain');
        if (boost !== null) {
            document.querySelectorAll('.btn-boost').forEach(btn => {
                if (Math.abs(parseFloat(btn.getAttribute('data-boost')) - parseFloat(boost)) < 0.15) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
        }
        const notifs = localStorage.getItem('mute_system_notifications');
        if (notifs !== null) {
            updateShieldUI(notifs === 'true');
        }
    } catch (e) {
        console.warn('localStorage read error:', e);
    }
}

function initListeners() {
    // Notification & click shield toggle
    if (btnToggleNotifs) {
        btnToggleNotifs.addEventListener('click', toggleSystemSounds);
    }

    // Manual Sonos IP modal
    btnEditSonosIp.addEventListener('click', () => modalSonosIp.classList.remove('hide'));
    btnCloseModal.addEventListener('click', () => modalSonosIp.classList.add('hide'));
    btnSaveManualIp.addEventListener('click', connectManualSonosIp);

    // Refresh stream
    btnRestartStream.addEventListener('click', async () => {
        btnRestartStream.disabled = true;
        btnRestartStream.querySelector('span').textContent = 'Refreshing...';
        await fetch('/api/sync/restart', { method: 'POST' });
        setTimeout(() => {
            btnRestartStream.disabled = false;
            btnRestartStream.querySelector('span').textContent = 'Refresh Stream';
        }, 1500);
    });

    // Volume Sliders (saves to localStorage & server)
    sonosVolSlider.addEventListener('input', (e) => {
        sonosVolVal.textContent = e.target.value + '%';
        localStorage.setItem('sonos_volume', e.target.value);
        setVolume('sonos', e.target.value);
    });

    citytekVolSlider.addEventListener('input', (e) => {
        citytekVolVal.textContent = e.target.value + '%';
        localStorage.setItem('citytek_volume', e.target.value);
        setVolume('citytek', e.target.value);
    });

    masterVolSlider.addEventListener('input', (e) => {
        masterVolVal.textContent = e.target.value + '%';
        localStorage.setItem('master_volume', e.target.value);
        setVolume('master', e.target.value);
    });

    // Mutes
    btnSonosMute.addEventListener('click', () => {
        const isMuted = sonosVolSlider.value == 0;
        const newVol = isMuted ? 50 : 0;
        sonosVolSlider.value = newVol;
        sonosVolVal.textContent = newVol + '%';
        localStorage.setItem('sonos_volume', newVol);
        setVolume('sonos', newVol);
    });
    btnCitytekMute.addEventListener('click', () => {
        const isMuted = citytekVolSlider.value == 0;
        const newVol = isMuted ? 80 : 0;
        citytekVolSlider.value = newVol;
        citytekVolVal.textContent = newVol + '%';
        localStorage.setItem('citytek_volume', newVol);
        setVolume('citytek', newVol);
    });
    btnMasterMute.addEventListener('click', toggleMute);

    // Citytek dropdown
    citytekDeviceDropdown.addEventListener('change', (e) => {
        if (e.target.value) {
            setCitytekDevice(e.target.value);
        }
    });

    // Sync Delay Slider
    syncDelaySlider.addEventListener('input', (e) => {
        delayNumDisplay.textContent = e.target.value;
        localStorage.setItem('delay_ms', e.target.value);
        setDelay(e.target.value);
    });

    // Nudge buttons
    document.querySelectorAll('.btn-nudge').forEach(btn => {
        btn.addEventListener('click', () => {
            const nudge = btn.getAttribute('data-nudge');
            let current = parseInt(syncDelaySlider.value);
            if (nudge === 'preset-1150') {
                current = 1150;
            } else {
                current += parseInt(nudge);
            }
            current = Math.max(0, Math.min(3000, current));
            syncDelaySlider.value = current;
            delayNumDisplay.textContent = current;
            setDelay(current);
        });
    });

    // Calibration Metronome
    btnCalibrateBeat.addEventListener('click', toggleCalibration);

    // Pre-Amp Boost Buttons
    document.querySelectorAll('.btn-boost').forEach(btn => {
        btn.addEventListener('click', async () => {
            document.querySelectorAll('.btn-boost').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const boost = parseFloat(btn.getAttribute('data-boost'));
            await fetch('/api/volume/boost', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ boost })
            });
        });
    });
}


// ==================== POLLING & STATUS ====================

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(fetchStatus, 350);
}

async function fetchStatus() {
    try {
        const res = await fetch('/api/status');
        if (!res.ok) return;
        const data = await res.json();
        updateUI(data);
    } catch (err) {
        // Server busy or restarting
    }
}

function updateUI(data) {
    const sonos = data.sonos;
    const engine = data.engine;
    const server = data.server;

    if (server && server.stream_url) {
        footerStreamUrl.textContent = server.stream_url;
    }

    // Sonos Card
    if (sonos.connected) {
        sonosStatusBadge.innerHTML = `<span class="dot pulse-amber"></span><span>Connected (Wi-Fi)</span>`;
        sonosDeviceName.textContent = sonos.name || 'Sonos Play:1';
        sonosIpDisplay.textContent = sonos.ip || '192.168.1.X';
    } else {
        sonosStatusBadge.innerHTML = `<span class="dot pulse-amber" style="background:#f59e0b;"></span><span>Auto-Scanning...</span>`;
        sonosIpDisplay.textContent = 'Scanning subnet...';
    }

    // Citytek Card
    if (engine.citytek_device && engine.citytek_device.index !== null) {
        citytekStatusBadge.innerHTML = `<span class="dot pulse-cyan"></span><span>Connected to Windows</span>`;
    }

    // Two-way synchronization for Master Volume (only when user is not dragging)
    if (engine.master_volume !== undefined && document.activeElement !== masterVolSlider) {
        masterVolSlider.value = engine.master_volume;
        masterVolVal.textContent = engine.master_volume + '%';
        localStorage.setItem('master_volume', engine.master_volume);
    }

    // Two-way synchronization for Citytek Volume
    if (engine.citytek_volume !== undefined && document.activeElement !== citytekVolSlider) {
        citytekVolSlider.value = engine.citytek_volume;
        citytekVolVal.textContent = engine.citytek_volume + '%';
        localStorage.setItem('citytek_volume', engine.citytek_volume);
    }

    // Two-way synchronization for Sonos Volume
    const sonosVol = (sonos && sonos.volume !== undefined) ? sonos.volume : engine.sonos_volume;
    if (sonosVol !== undefined && document.activeElement !== sonosVolSlider) {
        sonosVolSlider.value = sonosVol;
        sonosVolVal.textContent = sonosVol + '%';
        localStorage.setItem('sonos_volume', sonosVol);
    }

    // Delay Display
    if (engine.delay_ms !== undefined && document.activeElement !== syncDelaySlider) {
        syncDelaySlider.value = engine.delay_ms;
        delayNumDisplay.textContent = engine.delay_ms;
        localStorage.setItem('delay_ms', engine.delay_ms);
    }

    // Live VU Meters
    if (engine.levels) {
        const l = engine.levels.left * 100;
        const r = engine.levels.right * 100;
        vuLeft.style.width = l + '%';
        vuRight.style.width = r + '%';

        if (l > 3 || r > 3) {
            audioActivityStatus.textContent = 'Audio Playing';
            audioActivityStatus.style.color = '#10b981';
        } else {
            audioActivityStatus.textContent = 'Waiting for PC Audio';
            audioActivityStatus.style.color = '#94a3b8';
        }
    }

    // Pre-Amp Boost UI state
    if (engine.preamp_gain !== undefined) {
        localStorage.setItem('preamp_gain', engine.preamp_gain);
        document.querySelectorAll('.btn-boost').forEach(btn => {
            const b = parseFloat(btn.getAttribute('data-boost'));
            if (Math.abs(b - engine.preamp_gain) < 0.15) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    // Notification & click shield UI state
    if (engine.mute_system_notifications !== undefined) {
        localStorage.setItem('mute_system_notifications', engine.mute_system_notifications);
        updateShieldUI(engine.mute_system_notifications);
    }
}


// ==================== ACTIONS ====================

async function setVolume(target, volume) {
    if (target === 'sonos') {
        await fetch('/api/sonos/volume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ volume: parseInt(volume) })
        });
    } else if (target === 'citytek') {
        await fetch('/api/citytek/volume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ volume: parseInt(volume) })
        });
    } else if (target === 'master') {
        await fetch('/api/volume/master', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ volume: parseInt(volume) })
        });
    }
}

async function toggleMute() {
    const res = await fetch('/api/volume/mute', { method: 'POST' });
    const data = await res.json();
    btnMasterMute.classList.toggle('muted', data.is_muted);
}

async function setDelay(delay_ms) {
    await fetch('/api/sync/delay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ delay_ms: parseInt(delay_ms) })
    });
}

async function toggleCalibration() {
    const res = await fetch('/api/sync/calibrate', { method: 'POST' });
    const data = await res.json();
    if (data.calibrating) {
        btnCalibrateBeat.classList.add('active');
        calibrateBtnText.textContent = 'Stop Metronome Beat';
    } else {
        btnCalibrateBeat.classList.remove('active');
        calibrateBtnText.textContent = 'Test Sync (Metronome Click)';
    }
}

async function connectManualSonosIp() {
    const ip = inputManualIp.value.trim();
    if (!ip) return;

    btnSaveManualIp.disabled = true;
    btnSaveManualIp.textContent = 'Connecting...';

    try {
        const res = await fetch('/api/sonos/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip })
        });
        const data = await res.json();

        if (data.success) {
            modalSonosIp.classList.add('hide');
        } else {
            alert(`Could not connect to ${ip}: ${data.message}`);
        }
    } catch (e) {
        alert('Connection error. Check your IP and network.');
    } finally {
        btnSaveManualIp.disabled = false;
        btnSaveManualIp.textContent = 'Connect';
    }
}

async function loadAudioDevices() {
    try {
        const res = await fetch('/api/devices');
        const data = await res.json();

        citytekDeviceDropdown.innerHTML = '';
        if (data.devices) {
            data.devices.forEach(dev => {
                const opt = document.createElement('option');
                opt.value = dev.index;
                const star = dev.is_citytek ? '🎧 [Citytek MF109099] ' : '';
                opt.textContent = `${star}${dev.name} (${dev.sample_rate}Hz)`;
                if (dev.is_selected) opt.selected = true;
                citytekDeviceDropdown.appendChild(opt);
            });
        }
    } catch (e) {
        console.error('Error loading devices:', e);
    }
}

async function setCitytekDevice(index) {
    await fetch('/api/citytek/device', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ index: parseInt(index) })
    });
}

function updateShieldUI(isMuted) {
    if (!btnToggleNotifs) return;
    if (isMuted) {
        btnToggleNotifs.className = 'btn btn-glass btn-shield active';
        if (shieldStatusText) shieldStatusText.textContent = 'Clicks & Alerts: Muted';
        if (heroShieldTag) {
            heroShieldTag.className = 'feature-tag active';
            if (heroShieldText) heroShieldText.textContent = 'Notification & Click Sounds Blocked';
        }
    } else {
        btnToggleNotifs.className = 'btn btn-glass btn-shield inactive';
        if (shieldStatusText) shieldStatusText.textContent = 'Alerts: Unmuted';
        if (heroShieldTag) {
            heroShieldTag.className = 'feature-tag inactive';
            if (heroShieldText) heroShieldText.textContent = 'Notification Sounds Allowed';
        }
    }
}

async function toggleSystemSounds() {
    try {
        const res = await fetch('/api/system_sounds/toggle', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            updateShieldUI(data.mute_system_notifications);
            localStorage.setItem('mute_system_notifications', data.mute_system_notifications);
        }
    } catch (e) {
        console.error('Failed to toggle system sounds shield:', e);
    }
}
