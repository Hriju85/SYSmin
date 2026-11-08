// Base URL for API requests (supports same-origin and separate deployments)
const API_BASE = (typeof window !== 'undefined' && window.API_BASE_URL) ? window.API_BASE_URL.replace(/\/+$/, '') : '';

// State
let allTasks = [];
let searchQuery = "";
let currentFilter = "all"; // 'all' | 'external' | 'heavy' | 'suspended'
let sortField = "memory_mb";
let sortAsc = false; // Descending by memory by default (like Task Manager)

// Real-Time Graph History (60 data points for 60 seconds)
const HISTORY_LENGTH = 60;
const cpuHistory = new Array(HISTORY_LENGTH).fill(0);
const memHistory = new Array(HISTORY_LENGTH).fill(0);

// ==========================================================================
// Real-Time Canvas Graphs (Task Manager Style)
// ==========================================================================
function drawTaskManagerGrid(ctx, width, height) {
    ctx.clearRect(0, 0, width, height);

    // Subtle background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, width, height);

    // Draw horizontal grid lines (0%, 25%, 50%, 75%, 100%)
    ctx.lineWidth = 1;
    ctx.strokeStyle = '#e2e8f0';
    ctx.setLineDash([2, 4]);

    for (let i = 0; i <= 4; i++) {
        const y = Math.round((height - 2) * (i / 4)) + 1;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }

    // Draw vertical grid lines (every 10 seconds / 6 slices)
    for (let i = 1; i < 6; i++) {
        const x = Math.round(width * (i / 6));
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
    }

    ctx.setLineDash([]); // Reset line dash
}

function renderTaskManagerGraph(canvasId, dataPoints, strokeColor, fillColor) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Handle high-DPI displays
    const rect = canvas.getBoundingClientRect();
    const width = rect.width || canvas.width;
    const height = rect.height || canvas.height;

    if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
    }

    drawTaskManagerGrid(ctx, width, height);

    if (!dataPoints || dataPoints.length === 0) return;

    const step = width / (HISTORY_LENGTH - 1);
    const points = [];

    for (let i = 0; i < HISTORY_LENGTH; i++) {
        const val = Math.max(0, Math.min(100, dataPoints[i] || 0));
        const x = i * step;
        const y = height - (val / 100) * (height - 4) - 2;
        points.push({ x, y });
    }

    // Fill area under curve
    ctx.beginPath();
    ctx.moveTo(points[0].x, height);
    for (let i = 0; i < points.length; i++) {
        ctx.lineTo(points[i].x, points[i].y);
    }
    ctx.lineTo(points[points.length - 1].x, height);
    ctx.closePath();

    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, fillColor);
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0.0)');
    ctx.fillStyle = gradient;
    ctx.fill();

    // Draw graph stroke line
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
        ctx.lineTo(points[i].x, points[i].y);
    }
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 1.8;
    ctx.lineJoin = 'round';
    ctx.stroke();

    // Pulse dot at the latest value (right edge)
    const last = points[points.length - 1];
    ctx.beginPath();
    ctx.arc(last.x - 2, last.y, 3, 0, Math.PI * 2);
    ctx.fillStyle = strokeColor;
    ctx.fill();
}

function updatePerformanceGraphs(systemData) {
    if (!systemData) return;

    const cpuPct = systemData.cpu_percent || 0;
    const ramPct = systemData.ram_percent || 0;

    // Shift in new telemetry values
    cpuHistory.shift();
    cpuHistory.push(cpuPct);

    memHistory.shift();
    memHistory.push(ramPct);

    // Update Text Labels
    const cpuValEl = document.getElementById('cpuPercentVal');
    if (cpuValEl) cpuValEl.textContent = `${cpuPct.toFixed(1)}%`;

    const cpuSubEl = document.getElementById('cpuSubVal');
    if (cpuSubEl) cpuSubEl.textContent = `${systemData.cpu_cores || 8} Logical Cores`;

    const memValEl = document.getElementById('memPercentVal');
    if (memValEl) memValEl.textContent = `${ramPct.toFixed(1)}%`;

    const memSubEl = document.getElementById('memSubVal');
    if (memSubEl) memSubEl.textContent = `${systemData.ram_used_gb || 0} / ${systemData.ram_total_gb || 0} GB`;

    // Render Canvas Graphs
    renderTaskManagerGraph('cpuGraphCanvas', cpuHistory, '#16a34a', 'rgba(22, 163, 74, 0.22)');
    renderTaskManagerGraph('memGraphCanvas', memHistory, '#ea580c', 'rgba(234, 88, 12, 0.22)');

    // Update Summary Stats Box
    const totalEl = document.getElementById('statTotalProc');
    if (totalEl) totalEl.textContent = String(systemData.total_processes || allTasks.length);

    const extEl = document.getElementById('statExternalProc');
    if (extEl) extEl.textContent = String(systemData.external_count || 0);

    const sysEl = document.getElementById('statSystemProc');
    if (sysEl) sysEl.textContent = String(systemData.system_count || 0);

    const heavyCount = allTasks.filter(t => t.is_big).length;
    const heavyEl = document.getElementById('statHeavyProc');
    if (heavyEl) heavyEl.textContent = String(heavyCount);
}

// ==========================================================================
// Filtering & Sorting
// ==========================================================================
function handleSearch(event) {
    const input = document.getElementById('searchInput');
    searchQuery = (input ? input.value : (event?.target?.value || '')).trim().toLowerCase();
    
    const clearBtn = document.getElementById('clearSearchBtn');
    if (clearBtn) {
        clearBtn.style.display = searchQuery ? 'block' : 'none';
    }
    renderTables();
}

function clearSearch() {
    const input = document.getElementById('searchInput');
    if (input) input.value = '';
    searchQuery = '';
    const clearBtn = document.getElementById('clearSearchBtn');
    if (clearBtn) clearBtn.style.display = 'none';
    renderTables();
}

function setQuickFilter(filter) {
    currentFilter = filter;
    document.querySelectorAll('.pill-btn').forEach(btn => {
        if (btn.getAttribute('data-filter') === filter) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    renderTables();
}

function sortTable(field) {
    if (sortField === field) {
        sortAsc = !sortAsc;
    } else {
        sortField = field;
        sortAsc = (field === 'name' || field === 'pid'); // Ascending for text/pid, descending for memory
    }
    updateSortIcons();
    renderTables();
}

function updateSortIcons() {
    const arrow = sortAsc ? '▲' : '▼';
    const fields = ['pid', 'name', 'mem'];
    fields.forEach(f => {
        const icon = document.getElementById(`sort-${f}`);
        const sysIcon = document.getElementById(`sort-sys-${f}`);
        const isActive = (f === 'mem' && sortField === 'memory_mb') || (sortField === f);
        if (icon) icon.textContent = isActive ? arrow : '';
        if (sysIcon) sysIcon.textContent = isActive ? arrow : '';
    });
}

function getProcessedTasks(tasks) {
    let result = tasks.filter(task => {
        if (searchQuery) {
            const name = (task.name || '').toLowerCase();
            const pid = String(task.pid);
            if (!name.includes(searchQuery) && !pid.includes(searchQuery)) {
                return false;
            }
        }

        if (currentFilter === 'heavy') return task.is_big;
        if (currentFilter === 'suspended') return task.status === 'SUSPENDED';
        if (currentFilter === 'external') return task.category === 'EXTERNAL_APP';

        return true;
    });

    result.sort((a, b) => {
        let valA = a[sortField];
        let valB = b[sortField];

        if (typeof valA === 'string') {
            valA = valA.toLowerCase();
            valB = (valB || '').toLowerCase();
            return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }

        valA = Number(valA) || 0;
        valB = Number(valB) || 0;
        return sortAsc ? valA - valB : valB - valA;
    });

    return result;
}

// ==========================================================================
// Table Rendering (Compact Task Manager Density)
// ==========================================================================
function renderTables() {
    const filteredAll = getProcessedTasks(allTasks);

    const externalTasks = filteredAll.filter(t => t.category === 'EXTERNAL_APP');
    const systemTasks = filteredAll.filter(t => t.category === 'SYSTEM_APP');

    // Update Counter Badges
    const matchedEl = document.getElementById('matchedCount');
    if (matchedEl) matchedEl.textContent = String(filteredAll.length);

    const extEl = document.getElementById('externalCount');
    if (extEl) extEl.textContent = String(externalTasks.length);

    const extSecEl = document.getElementById('externalSectionCount');
    if (extSecEl) extSecEl.textContent = String(externalTasks.length);

    const sysSecEl = document.getElementById('systemSectionCount');
    if (sysSecEl) sysSecEl.textContent = String(systemTasks.length);

    renderTableSection('externalAppsBody', externalTasks);
    renderTableSection('systemAppsBody', systemTasks);
}

function renderTableSection(tbodyId, tasks) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;

    if (tasks.length === 0) {
        tbody.innerHTML = `<tr class="empty-row"><td colspan="6">No active processes match your filter.</td></tr>`;
        return;
    }

    const emptyRow = tbody.querySelector('.empty-row');
    if (emptyRow) emptyRow.remove();

    const existingRows = new Map();
    tbody.querySelectorAll('tr[data-pid]').forEach(row => {
        existingRows.set(row.getAttribute('data-pid'), row);
    });

    const currentPids = new Set(tasks.map(t => String(t.pid)));

    // Remove rows that no longer exist
    existingRows.forEach((row, pid) => {
        if (!currentPids.has(pid)) {
            row.remove();
            existingRows.delete(pid);
        }
    });

    // Max memory baseline for mini-meter (500MB baseline)
    const maxMemBaseline = 600;

    // Update or insert rows
    tasks.forEach((task, index) => {
        const pidStr = String(task.pid);
        let row = existingRows.get(pidStr);

        const badgeClass = task.is_big ? 'badge-heavy' : 'badge-short';
        const badgeText = task.is_big ? 'HEAVY' : 'SHORT';
        const statusClass = task.status === 'SUSPENDED' ? 'state-suspended' : 'state-running';
        const statusText = `● ${task.status}`;
        const memMb = Number(task.memory_mb) || 0;
        const memPct = Math.min(100, Math.round((memMb / maxMemBaseline) * 100));
        const isProtected = Boolean(task.is_protected);

        const focusButton = `<button class="btn-row btn-focus" onclick="focusTask(${task.pid})">Focus</button>`;
        const killButton = isProtected
            ? `<button class="btn-row btn-kill" disabled title="Protected system process cannot be terminated">End</button>`
            : `<button class="btn-row btn-kill" onclick="killTask(${task.pid}, '${escapeJs(task.name)}')">End</button>`;

        if (!row) {
            row = document.createElement('tr');
            row.setAttribute('data-pid', pidStr);
            row.innerHTML = `
                <td class="col-pid">${task.pid}</td>
                <td class="col-name" title="${escapeHtml(task.name)}">${escapeHtml(task.name)}</td>
                <td class="col-mem">
                    <div class="mem-cell-wrap">
                        <span class="mem-text">${memMb.toFixed(1)} MB</span>
                        <div class="mem-mini-bar">
                            <div class="mem-mini-fill ${task.is_big ? 'heavy' : ''}" style="width: ${memPct}%"></div>
                        </div>
                    </div>
                </td>
                <td class="col-class"><span class="${badgeClass}">${badgeText}</span></td>
                <td class="col-status ${statusClass}">${statusText}</td>
                <td class="col-action">
                    <div class="row-actions">
                        ${focusButton}
                        ${killButton}
                    </div>
                </td>
            `;
            tbody.appendChild(row);
            existingRows.set(pidStr, row);
        } else {
            // Update in-place to avoid layout reflow & preserve smooth scrolling
            const nameCell = row.querySelector('.col-name');
            if (nameCell && nameCell.textContent !== task.name) {
                nameCell.textContent = task.name;
                nameCell.setAttribute('title', task.name);
            }

            const memTextEl = row.querySelector('.mem-text');
            if (memTextEl) memTextEl.textContent = `${memMb.toFixed(1)} MB`;

            const memFillEl = row.querySelector('.mem-mini-fill');
            if (memFillEl) {
                memFillEl.style.width = `${memPct}%`;
                memFillEl.className = `mem-mini-fill ${task.is_big ? 'heavy' : ''}`;
            }

            const badgeSpan = row.querySelector('.col-class span');
            if (badgeSpan) {
                if (badgeSpan.className !== badgeClass) badgeSpan.className = badgeClass;
                if (badgeSpan.textContent !== badgeText) badgeSpan.textContent = badgeText;
            }

            const statusCell = row.querySelector('.col-status');
            if (statusCell) {
                const targetClass = `col-status ${statusClass}`;
                if (statusCell.className !== targetClass) statusCell.className = targetClass;
                if (statusCell.textContent !== statusText) statusCell.textContent = statusText;
            }
        }

        // Row position ordering
        if (tbody.children[index] !== row) {
            tbody.insertBefore(row, tbody.children[index] || null);
        }
    });
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function escapeJs(str) {
    if (!str) return '';
    return String(str)
        .replace(/\\/g, '\\\\')
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"');
}

// ==========================================================================
// Task Actions
// ==========================================================================
async function killTask(pid, name) {
    const label = name ? `"${name}" (PID: ${pid})` : `PID ${pid}`;
    if (!confirm(`End process ${label}?`)) return;

    allTasks = allTasks.filter(t => t.pid !== pid);
    renderTables();

    try {
        const response = await fetch(`${API_BASE}/api/kill/${pid}`, { method: 'POST' });
        const data = await response.json();
        if (!response.ok || data.status === 'error') {
            alert(`Failed to terminate task: ${data.message || response.statusText}`);
        }
    } catch (err) {
        console.error('Failed to kill process:', err);
    } finally {
        await refreshTasks();
    }
}

async function focusTask(pid) {
    try {
        await fetch(`${API_BASE}/api/focus/${pid}`, { method: 'POST' });
        await refreshTasks();
    } catch (err) {
        console.error('Failed to focus task:', err);
    }
}

async function resumeAll() {
    try {
        await fetch(`${API_BASE}/api/resume-all`, { method: 'POST' });
        await refreshTasks();
    } catch (err) {
        console.error('Failed to resume all:', err);
    }
}

async function toggleAuto() {
    try {
        await fetch(`${API_BASE}/api/toggle-auto`, { method: 'POST' });
        await refreshTasks();
    } catch (err) {
        console.error('Failed to toggle auto mode:', err);
    }
}

// ==========================================================================
// Polling Loop & State Synchronizer
// ==========================================================================
async function refreshTasks() {
    try {
        const response = await fetch(`${API_BASE}/api/tasks`);
        if (!response.ok) return;
        const data = await response.json();

        allTasks = data.tasks || [];

        // Real-Time System Telemetry & Canvas Graphs
        if (data.system) {
            updatePerformanceGraphs(data.system);
        }

        // Auto Button State
        const autoBtn = document.getElementById('autoBtn');
        const autoBtnText = document.getElementById('autoBtnText');
        if (autoBtn) {
            if (data.auto_mode) {
                autoBtn.classList.add('active');
                if (autoBtnText) autoBtnText.textContent = 'Auto-Schedule: ACTIVE';
            } else {
                autoBtn.classList.remove('active');
                if (autoBtnText) autoBtnText.textContent = 'Auto-Schedule: OFF';
            }
        }

        // Mode Pill & Description
        const bannerPill = document.getElementById('statusBannerPill');
        const bannerDesc = document.getElementById('statusBanner');

        if (data.focused_pid) {
            if (bannerPill) {
                bannerPill.textContent = `ISOLATED PID: ${data.focused_pid}`;
                bannerPill.className = 'status-pill status-pill-focus';
            }
            if (bannerDesc) {
                bannerDesc.textContent = `Process PID ${data.focused_pid} has dedicated CPU execution. Other heavy tasks are suspended.`;
            }
            // Highlight row in tables
            document.querySelectorAll('tr[data-pid]').forEach(r => {
                if (r.getAttribute('data-pid') === String(data.focused_pid)) {
                    r.classList.add('row-focused');
                } else {
                    r.classList.remove('row-focused');
                }
            });
        } else if (data.auto_mode) {
            if (bannerPill) {
                bannerPill.textContent = 'AUTO SJF ACTIVE';
                bannerPill.className = 'status-pill status-pill-auto';
            }
            if (bannerDesc) {
                bannerDesc.textContent = 'Sequential Shortest-Job-First throttler is optimizing background CPU allocation.';
            }
            document.querySelectorAll('tr.row-focused').forEach(r => r.classList.remove('row-focused'));
        } else {
            if (bannerPill) {
                bannerPill.textContent = 'Manual Mode';
                bannerPill.className = 'status-pill status-pill-manual';
            }
            if (bannerDesc) {
                bannerDesc.textContent = 'Standard Windows scheduling active. Select a process to Focus or toggle Auto-Schedule.';
            }
            document.querySelectorAll('tr.row-focused').forEach(r => r.classList.remove('row-focused'));
        }

        renderTables();
    } catch (err) {
        console.error('Error fetching process updates:', err);
    }
}

// Window resize handler for canvas crispness
window.addEventListener('resize', () => {
    renderTaskManagerGraph('cpuGraphCanvas', cpuHistory, '#16a34a', 'rgba(22, 163, 74, 0.22)');
    renderTaskManagerGraph('memGraphCanvas', memHistory, '#ea580c', 'rgba(234, 88, 12, 0.22)');
});

// Poll every 1.5 seconds for snappy real-time responsiveness
setInterval(refreshTasks, 1500);
refreshTasks();
