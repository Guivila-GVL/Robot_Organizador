// ==========================================================================
// ROBOT ORGANIZADOR 2026 - APPLICATION CONTROLLER (ES6+ Vanilla JS)
// ==========================================================================

const state = {
  projects: [],
  activeProjectId: null,
  tasks: [],
  currentFilter: 'in_progress',
  services: [],
  settings: {}
};

// DOM Elements
const projectsListEl = document.getElementById('projectsList');
const projectCountEl = document.getElementById('projectCount');
const projectSearchEl = document.getElementById('projectSearch');
const dockItemsEl = document.getElementById('dockItems');
const tasksContainerEl = document.getElementById('tasksContainer');

// Banner Elements
const bannerIconEl = document.getElementById('bannerIcon');
const bannerNameEl = document.getElementById('bannerName');
const bannerCategoryEl = document.getElementById('bannerCategory');
const bannerDescEl = document.getElementById('bannerDesc');
const bannerFolderEl = document.getElementById('bannerFolder');
const bannerUrlLinkEl = document.getElementById('bannerUrlLink');
const bannerProgressCircleEl = document.getElementById('bannerProgressCircle');
const bannerProgressTextEl = document.getElementById('bannerProgressText');
const statCompletedEl = document.getElementById('statCompleted');
const statTotalEl = document.getElementById('statTotal');

// Filter count elements
const countAllEl = document.getElementById('countAll');
const countPendingEl = document.getElementById('countPending');
const countInProgressEl = document.getElementById('countInProgress');
const countCompletedEl = document.getElementById('countCompleted');

// Modals
const taskModal = document.getElementById('taskModal');
const checkModal = document.getElementById('checkModal');
const settingsModal = document.getElementById('settingsModal');

// Init
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  loadServices();
  loadWatchdogStatus();
  refreshGlobalQueueBadge();
  loadProjects().then(() => {
    // Select first project by default
    if (state.projects.length > 0) {
      selectProject(state.projects[0].id);
    }
  });

  // Service & Watchdog polling every 8s + live activity console polling
  updateActivityConsole();
  setInterval(updateActivityConsole, 1800);

  setInterval(() => {
    loadServices();
    loadWatchdogStatus();
    refreshGlobalQueueBadge();

    const gqModal = document.getElementById('globalQueueModal');
    if (gqModal && gqModal.classList.contains('open')) {
      loadGlobalQueueModal();
    }

    const activeTag = document.activeElement ? document.activeElement.tagName : '';
    const isTyping = ['INPUT', 'TEXTAREA', 'SELECT'].includes(activeTag);
    const hasModalOpen = document.querySelector('.modal-overlay.open') !== null;
    if (!isTyping && !hasModalOpen && state.activeProjectId) {
      loadTasks(state.activeProjectId, true);
    }
  }, 8000);
});

function initEventListeners() {
  // Search
  projectSearchEl.addEventListener('input', (e) => {
    renderProjectsList(e.target.value.toLowerCase());
  });

  // Filter tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.currentFilter = btn.dataset.filter;
      renderTasksList();
      if (state.activeProjectId) {
        loadTasks(state.activeProjectId, true);
      }
    });
  });

  // Copy All Queue button
  const btnCopyQueue = document.getElementById('btnCopyAllQueue');
  if (btnCopyQueue) {
    btnCopyQueue.addEventListener('click', copyAllLaunchedQueue);
  }

  // Progress Modal listeners
  const progressRange = document.getElementById('progressRange');
  if (progressRange) {
    progressRange.addEventListener('input', (e) => {
      document.getElementById('progressPctLabel').textContent = `${e.target.value}%`;
    });
  }
  const btnSaveProgress = document.getElementById('btnSaveProgress');
  if (btnSaveProgress) {
    btnSaveProgress.addEventListener('click', saveTaskProgress);
  }

  // Top buttons
  const btnCmdMon = document.getElementById('btnOpenCmdMonitor');
  if (btnCmdMon) btnCmdMon.addEventListener('click', openCmdMonitorModal);
  const btnGlobalQ = document.getElementById('btnOpenGlobalQueue');
  if (btnGlobalQ) btnGlobalQ.addEventListener('click', openGlobalQueueModal);
  const btnCopyGlobalSeq = document.getElementById('btnCopyGlobalSequence');
  if (btnCopyGlobalSeq) btnCopyGlobalSeq.addEventListener('click', copyGlobalQueueSequence);
  const btnRunGQ = document.getElementById('btnRunGlobalQueue');
  if (btnRunGQ) btnRunGQ.addEventListener('click', runGlobalQueueNow);
  const btnStopGQ = document.getElementById('btnStopGlobalQueue');
  if (btnStopGQ) btnStopGQ.addEventListener('click', stopGlobalQueueNow);

  document.getElementById('btnOpenAllServices').addEventListener('click', openAllServices);
  document.getElementById('btnTestTelegram').addEventListener('click', testTelegram);
  document.getElementById('btnRescan').addEventListener('click', rescanProjects);
  document.getElementById('btnOpenSettings').addEventListener('click', openSettingsModal);

  // New task
  document.getElementById('btnNewTask').addEventListener('click', () => openTaskModal());
  document.getElementById('btnSaveTask').addEventListener('click', saveTask);

  // Smart Quick Task
  const smartInput = document.getElementById('smartTaskInput');
  const btnSmart = document.getElementById('btnSmartCreateTask');
  if (smartInput && btnSmart) {
    btnSmart.addEventListener('click', createSmartTask);
    smartInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        createSmartTask();
      }
    });
  }

  // Voice Dictation
  const btnVoice = document.getElementById('btnVoiceInput');
  if (btnVoice) {
    btnVoice.addEventListener('click', startVoiceDictation);
  }

  // Check completion submit
  document.getElementById('btnSubmitCheck').addEventListener('click', submitTaskCompletion);

  // Settings save
  document.getElementById('btnSaveSettings').addEventListener('click', saveSettings);

  // Image preview in check modal
  const imgInput = document.getElementById('checkImageFile');
  imgInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        document.getElementById('checkPreviewImg').src = ev.target.result;
        document.getElementById('checkImagePreview').style.display = 'block';
      };
      reader.readAsDataURL(file);
    }
  });
}

// --------------------------------------------------------------------------
// SERVICES / DOCK
// --------------------------------------------------------------------------
async function loadServices() {
  try {
    const res = await fetch('/api/services');
    const services = await res.json();
    state.services = services;
    renderServiceDock();
  } catch (err) {
    console.error('Error al cargar servicios:', err);
  }
}

async function loadWatchdogStatus() {
  try {
    const res = await fetch('/api/watchdog/status');
    const data = await res.json();
    state.watchdogData = data;

    const stateEl = document.getElementById('watchdogState');
    const cardEl = document.getElementById('agentStatusCard') || document.querySelector('.agent-status-card');
    const modelEl = document.getElementById('watchdogModel');
    const pctEl = document.getElementById('watchdogQuotaPct');
    const barEl = document.getElementById('watchdogQuotaBar');
    const resetEl = document.getElementById('watchdogResetTime');
    const othersEl = document.getElementById('watchdogOtherModels');

    if (stateEl && data.label) {
      stateEl.textContent = data.label;
    }
    if (cardEl && data.detail) {
      cardEl.title = data.detail;
      cardEl.classList.toggle('quota-warning', Boolean(data.quota_alert));
    }

    if (modelEl && data.active_model) {
      modelEl.textContent = data.active_model;
    }

    if (typeof data.quota_remaining_pct === 'number') {
      const pct = data.quota_remaining_pct;
      const colorClass = `quota-${data.quota_color || (pct < 20 ? 'red' : pct <= 50 ? 'orange' : 'green')}`;

      if (pctEl) {
        pctEl.textContent = `${pct}%`;
        pctEl.className = `quota-pct-badge ${colorClass}`;
      }
      if (barEl) {
        barEl.style.width = `${pct}%`;
        barEl.className = `quota-bar-fill ${colorClass}`;
      }
    }

    if (resetEl && data.reset_text) {
      resetEl.textContent = data.reset_text;
    }

    if (othersEl && Array.isArray(data.models)) {
      const others = data.models.filter(m => !m.is_active);
      othersEl.innerHTML = others.map(m => {
        const shortName = m.name.replace('Gemini ', '').replace(' (Medium)', '').replace(' (High)', '');
        return `<span class="quota-mini-chip" title="${m.name}: ${m.reset_text}">${shortName}: <b>${m.quota_remaining_pct}%</b></span>`;
      }).join('');
    }

    const modelsModal = document.getElementById('modelsModal');
    if (modelsModal && modelsModal.classList.contains('open')) {
      renderModelsModal();
    }
  } catch (err) {
    console.error('Error al consultar Watchdog:', err);
  }
}

function openModelsModal() {
  document.getElementById('modelsModal').classList.add('open');
  renderModelsModal();
  loadWatchdogStatus();
}

function renderModelsModal() {
  const container = document.getElementById('modelsListContainer');
  const data = state.watchdogData;
  if (!container || !data || !Array.isArray(data.models)) return;

  container.innerHTML = '';
  data.models.forEach((m, idx) => {
    const isFirst = idx === 0;
    const isLast = idx === data.models.length - 1;
    const colorClass = `quota-${m.quota_color}`;
    const statusBadge = m.is_active
      ? '<span class="model-active-pill">⚡ EN USO AHORA</span>'
      : (m.is_exhausted
          ? '<span class="priority-tag priority-urgente">⚠️ AGOTADO 429</span>'
          : '<span class="gq-project-pill">✅ DISPONIBLE</span>');

    const row = document.createElement('div');
    row.className = 'global-queue-item';
    row.innerHTML = `
      <div class="gq-item-main">
        <div class="gq-order-badge">#${idx + 1}</div>
        <div class="gq-item-info">
          <div class="gq-item-meta">
            <strong style="color:var(--text-white);font-size:0.9rem;">${m.name}</strong>
            ${statusBadge}
          </div>
          <div style="font-size:0.74rem;color:var(--text-muted);margin-bottom:0.35rem;">
            ${m.tier} · Uso ciclo 5h: <b>${m.steps_used}/${m.steps_budget}</b> pasos · ⏳ ${m.reset_text}
          </div>
          <div class="gq-item-progress-row">
            <div class="gq-mini-bar-bg" style="width:140px;">
              <div class="quota-bar-fill ${colorClass}" style="width:${m.quota_remaining_pct}%;"></div>
            </div>
            <span class="quota-pct-badge ${colorClass}">${m.quota_remaining_pct}%</span>
          </div>
        </div>
      </div>
      <div class="gq-actions">
        <button class="btn btn-secondary btn-small" onclick="moveModelSequence('${m.name.replace(/'/g, "\\'")}', 'up')" ${isFirst ? 'disabled style="opacity:0.35;cursor:not-allowed;"' : ''} title="Subir prioridad en la secuencia de fallback">⬆️</button>
        <button class="btn btn-secondary btn-small" onclick="moveModelSequence('${m.name.replace(/'/g, "\\'")}', 'down')" ${isLast ? 'disabled style="opacity:0.35;cursor:not-allowed;"' : ''} title="Bajar prioridad en la secuencia de fallback">⬇️</button>
      </div>
    `;
    container.appendChild(row);
  });
}

async function moveModelSequence(modelName, direction) {
  try {
    const res = await fetch('/api/watchdog/models/move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_name: modelName, direction })
    });
    const data = await res.json();
    if (data.success && data.status) {
      state.watchdogData = data.status;
      renderModelsModal();
      showToast('Secuencia de motores actualizada', 'success');
    }
  } catch (err) {
    showToast('Error al reordenar motores', 'error');
  }
}

function renderServiceDock() {
  dockItemsEl.innerHTML = '';
  state.services.forEach(s => {
    const pill = document.createElement('a');
    pill.className = `dock-pill ${s.is_online ? 'online' : ''}`;
    pill.href = s.url;
    pill.target = '_blank';
    pill.title = `${s.name}: ${s.description} (${s.status_text})`;
    pill.innerHTML = `
      <span class="dock-dot"></span>
      <span>${s.icon} ${s.name}</span>
      <span style="font-family: var(--font-mono); font-size: 0.65rem; opacity: 0.7;">:${s.port}</span>
    `;

    pill.addEventListener('click', async (e) => {
      if (!s.is_online && s.can_autostart) {
        e.preventDefault();
        showToast(`Arrancando servidor de ${s.name} (:${s.port})...`, 'info');
        try {
          const res = await fetch(`/api/services/${s.id}/start?open_browser=true`, { method: 'POST' });
          const data = await res.json();
          if (data.success) {
            showToast(`${s.name} iniciado y abierto en el navegador`, 'success');
            loadServices();
          } else {
            showToast(`Error al iniciar ${s.name}: ${data.error || ''}`, 'error');
          }
        } catch (err) {
          showToast(`No se pudo iniciar ${s.name}`, 'error');
        }
      }
    });

    dockItemsEl.appendChild(pill);
  });
}

async function openAllServices() {
  try {
    showToast('Arrancando servidores locales y abriendo todas las pestañas...', 'info');
    const res = await fetch('/api/services/open-all', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      await loadServices();
      showToast(`Servicios abiertos: ${data.opened_services.join(', ')}`, 'success');
    }
  } catch (err) {
    showToast('Error al abrir servicios', 'error');
  }
}

// --------------------------------------------------------------------------
// PROJECTS
// --------------------------------------------------------------------------
async function loadProjects() {
  try {
    const res = await fetch('/api/projects');
    const projects = await res.json();
    state.projects = projects;
    projectCountEl.textContent = projects.length;
    renderProjectsList();
  } catch (err) {
    showToast('Error al cargar proyectos', 'error');
  }
}

function renderProjectsList(searchQuery = '') {
  projectsListEl.innerHTML = '';

  const filtered = state.projects.filter(p => 
    p.name.toLowerCase().includes(searchQuery) || 
    p.category.toLowerCase().includes(searchQuery) ||
    p.description.toLowerCase().includes(searchQuery)
  );

  if (filtered.length === 0) {
    projectsListEl.innerHTML = '<div class="empty-state">No se encontraron proyectos</div>';
    return;
  }

  filtered.forEach(p => {
    const card = document.createElement('div');
    card.className = `project-card ${p.id === state.activeProjectId ? 'active' : ''}`;
    card.onclick = () => selectProject(p.id);

    card.innerHTML = `
      <div class="project-card-header">
        <div class="card-title-group">
          <span class="card-icon">${p.icon}</span>
          <span class="card-name">${p.name}</span>
        </div>
        <span class="card-percent">${p.progress_percent}%</span>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" style="width: ${p.progress_percent}%;"></div>
      </div>
      <div class="project-card-footer">
        <span>${p.category}</span>
        <span>${p.completed_tasks}/${p.total_tasks} tareas</span>
      </div>
    `;
    projectsListEl.appendChild(card);
  });
}

function selectProject(projectId) {
  state.activeProjectId = projectId;
  const project = state.projects.find(p => p.id === projectId);
  if (!project) return;

  // Update UI active card
  document.querySelectorAll('.project-card').forEach(c => c.classList.remove('active'));
  renderProjectsList(projectSearchEl.value.toLowerCase());

  // Update Banner
  bannerIconEl.textContent = project.icon;
  bannerNameEl.textContent = project.name;
  bannerCategoryEl.textContent = project.category;
  bannerDescEl.textContent = project.description;
  bannerFolderEl.textContent = `📁 ${project.folder_name}`;

  if (project.url) {
    bannerUrlLinkEl.href = project.url;
    bannerUrlLinkEl.style.display = 'inline-flex';
    bannerUrlLinkEl.textContent = `🔗 Abrir ${project.port ? `(:${project.port})` : ''}`;
    bannerUrlLinkEl.onclick = async (e) => {
      const matchingService = state.services.find(s => s.port && s.port === project.port);
      if (matchingService && !matchingService.is_online && matchingService.can_autostart) {
        e.preventDefault();
        showToast(`Arrancando servidor de ${matchingService.name} (:${matchingService.port})...`, 'info');
        try {
          const res = await fetch(`/api/services/${matchingService.id}/start?open_browser=true`, { method: 'POST' });
          const data = await res.json();
          if (data.success) {
            showToast(`${matchingService.name} iniciado y abierto en el navegador`, 'success');
            loadServices();
          }
        } catch (err) {
          showToast(`No se pudo iniciar ${matchingService.name}`, 'error');
        }
      }
    };
  } else {
    bannerUrlLinkEl.style.display = 'none';
  }

  // Pestaña inicial por defecto: tareas 'En Progreso'
  state.currentFilter = 'in_progress';
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === 'in_progress');
  });

  loadTasks(projectId);
  updateActivityConsole();
}

async function rescanProjects() {
  try {
    showToast('Escaneando proyectos y tareas en disco...', 'info');
    const res = await fetch('/api/projects/rescan', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      await loadProjects();
      if (state.activeProjectId) {
        selectProject(state.activeProjectId);
      }
      showToast('Proyectos y tareas sincronizados correctamente', 'success');
    }
  } catch (err) {
    showToast('Error al sincronizar proyectos', 'error');
  }
}

async function openProjectResource(resourceKey) {
  if (!state.activeProjectId) {
    showToast('Selecciona primero un proyecto', 'error');
    return;
  }

  const isWebResource = (resourceKey === 'onenote' || resourceKey === 'git');
  let popupWin = null;
  if (isWebResource) {
    popupWin = window.open('about:blank', '_blank');
  }

  try {
    const query = (isWebResource && popupWin) ? '?open_browser=false' : '';
    const res = await fetch(`/api/projects/${state.activeProjectId}/open-resource/${resourceKey}${query}`, {
      method: 'POST'
    });
    const data = await res.json();
    if (data.success) {
      if (isWebResource && data.target && data.target.startsWith('http')) {
        if (popupWin) {
          popupWin.location.href = data.target;
        } else {
          window.open(data.target, '_blank', 'noopener');
        }
        const proj = state.projects.find(p => p.id === state.activeProjectId);
        if (proj && resourceKey === 'onenote') proj.onenote_url = data.target;
        if (proj && resourceKey === 'git') proj.git_url = data.target;
      } else if (popupWin) {
        popupWin.close();
      }
      showToast(data.message || 'Recurso abierto', 'success');
    } else {
      if (popupWin) popupWin.close();
      showToast(data.error || 'No se pudo abrir el recurso', 'error');
    }
  } catch (err) {
    if (popupWin) popupWin.close();
    showToast('Error al abrir recurso del proyecto', 'error');
  }
}

// --------------------------------------------------------------------------
// TASKS
// --------------------------------------------------------------------------
async function loadTasks(projectId, silent = false) {
  try {
    const res = await fetch(`/api/projects/${projectId}/tasks`);
    const tasks = await res.json();
    state.tasks = tasks;
    updateTaskCounters();
    updateBannerProgress();
    renderTasksList();
    updateActivityConsole();
  } catch (err) {
    if (!silent) showToast('Error al cargar tareas', 'error');
  }
}

function updateTaskCounters() {
  const total = state.tasks.length;
  const pending = state.tasks.filter(t => t.status === 'pending').length;
  const inProgress = state.tasks.filter(t => t.status === 'in_progress').length;
  const completed = state.tasks.filter(t => t.status === 'completed').length;

  countAllEl.textContent = total;
  countPendingEl.textContent = pending;
  countInProgressEl.textContent = inProgress;
  countCompletedEl.textContent = completed;

  statCompletedEl.textContent = completed;
  statTotalEl.textContent = total;

  // Actualizar banner de Cola Activa
  const queueBanner = document.getElementById('queueBanner');
  const queueCountText = document.getElementById('queueCountText');
  if (queueBanner && queueCountText) {
    if (inProgress > 0) {
      queueCountText.textContent = `${inProgress} ${inProgress === 1 ? 'tarea activa' : 'tareas activas'}`;
      queueBanner.style.display = 'flex';
    } else {
      queueBanner.style.display = 'none';
    }
  }
}

function updateBannerProgress() {
  const total = state.tasks.length;
  const completed = state.tasks.filter(t => t.status === 'completed').length;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  bannerProgressTextEl.textContent = `${pct}%`;
  bannerProgressCircleEl.style.background = `conic-gradient(var(--accent-purple) ${pct * 3.6}deg, rgba(255, 255, 255, 0.08) 0deg)`;

  // Update local project in state
  const proj = state.projects.find(p => p.id === state.activeProjectId);
  if (proj) {
    proj.total_tasks = total;
    proj.completed_tasks = completed;
    proj.progress_percent = pct;
  }
}

function sortTasksForDisplay(tasksArray) {
  const copy = [...tasksArray];
  copy.sort((a, b) => {
    const statusOrder = { in_progress: 0, pending: 1, completed: 2 };
    const sa = statusOrder[a.status] ?? 2;
    const sb = statusOrder[b.status] ?? 2;
    if (sa !== sb) return sa - sb;

    if (a.status === 'completed') {
      const ca = a.completed_at || '1970-01-01';
      const cb = b.completed_at || '1970-01-01';
      if (ca !== cb) return cb.localeCompare(ca);
      const oa = a.order_index ?? 0;
      const ob = b.order_index ?? 0;
      if (oa !== ob) return ob - oa;
      return (b.id || 0) - (a.id || 0);
    }

    if (a.status === 'in_progress') {
      const qa = a.queue_order ?? 9999;
      const qb = b.queue_order ?? 9999;
      if (qa !== qb) return qa - qb;
    }

    const oa = a.order_index ?? 0;
    const ob = b.order_index ?? 0;
    if (oa !== ob) return ob - oa;
    return (b.id || 0) - (a.id || 0);
  });
  return copy;
}

function renderTasksList() {
  tasksContainerEl.innerHTML = '';

  const sortedAll = sortTasksForDisplay(state.tasks);
  const completedSorted = sortedAll.filter(t => t.status === 'completed');
  const totalCompletedCount = completedSorted.length;
  const completedRankMap = {};
  completedSorted.forEach((t, idx) => {
    completedRankMap[t.id] = {
      histNum: totalCompletedCount - idx,
      isLatest: idx === 0
    };
  });

  let filtered = sortedAll;
  if (state.currentFilter !== 'all') {
    filtered = sortedAll.filter(t => t.status === state.currentFilter);
  }

  if (filtered.length === 0) {
    if (state.currentFilter === 'in_progress') {
      const pendCount = state.tasks.filter(t => t.status === 'pending').length;
      tasksContainerEl.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🚀</div>
          <h3>No hay tareas en progreso en este proyecto</h3>
          <p>${pendCount > 0 ? `Tienes ${pendCount} tarea(s) en Pendientes listas para lanzar.` : 'Añade una nueva tarea arriba para empezar.'}</p>
          ${pendCount > 0 ? `<button class="btn btn-launch" style="margin-top:0.8rem;" onclick="switchFilterTab('pending')">Ir a Pendientes (${pendCount}) →</button>` : ''}
        </div>
      `;
    } else {
      tasksContainerEl.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📋</div>
          <h3>No hay tareas en esta categoría</h3>
          <p>Añade una nueva tarea para comenzar a organizar este proyecto.</p>
        </div>
      `;
    }
    return;
  }

  filtered.forEach(task => {
    const item = document.createElement('div');
    item.className = `task-item ${task.status}`;
    item.id = `task-${task.id}`;

    const isChecked = task.status === 'completed';
    const isPending = task.status === 'pending';
    const isInProgress = task.status === 'in_progress';

    let completedOrderBadge = '';
    if (isChecked && completedRankMap[task.id]) {
      const { histNum, isLatest } = completedRankMap[task.id];
      const dateStr = task.completed_at ? ` · 🕒 ${formatDate(task.completed_at)}` : '';
      completedOrderBadge = `<span class="priority-tag" style="background: rgba(16, 185, 129, 0.18); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.38);">✅ Hito #${histNum}${isLatest ? ' (Última completada)' : ''}${dateStr}</span>`;
    }

    // Live Progress Tracker HTML for in_progress tasks
    let trackerHtml = '';
    if (isInProgress) {
      const pct = task.progress_pct || 10;
      const stepLabel = task.current_step || '🚀 En cola de lanzamiento (lista para ejecutar)';
      trackerHtml = `
        <div class="task-progress-tracker">
          <div class="tracker-header">
            <span class="tracker-step">${stepLabel}</span>
            <span class="tracker-pct">${pct}%</span>
          </div>
          <div class="tracker-bar-bg">
            <div class="tracker-bar-fill" style="width: ${pct}%;"></div>
          </div>
        </div>
      `;
    }

    // Image preview HTML
    let imagePreviewHtml = '';
    if (task.result_image_url) {
      imagePreviewHtml = `
        <div class="result-image-preview">
          <a href="${task.result_image_url}" target="_blank">
            <img src="${task.result_image_url}" alt="Captura del resultado">
          </a>
        </div>
      `;
    }

    // Milestone details HTML
    let milestoneHtml = '';
    if (task.milestone_description || task.milestone_result) {
      milestoneHtml = `
        <div class="milestone-box">
          <div class="milestone-header">
            <span style="font-weight: 600; color: var(--text-white);">🎯 Hito Esperado:</span>
            <span class="milestone-type-pill">${task.milestone_type.toUpperCase()}</span>
          </div>
          <div>${task.milestone_description || task.milestone_target || 'Validación manual'}</div>
          ${task.milestone_result ? `<div class="milestone-result-text"><b>Resultado:</b> ${task.milestone_result}</div>` : ''}
          ${imagePreviewHtml}
        </div>
      `;
    }

    // Comments list HTML
    let commentsListHtml = '';
    if (task.comments && task.comments.length > 0) {
      commentsListHtml = task.comments.map(c => `
        <div class="comment-bubble">
          <span class="comment-author">${c.author}:</span>
          <span>${c.text}</span>
          <span class="comment-date">(${formatDate(c.created_at)})</span>
        </div>
      `).join('');
    }

    item.innerHTML = `
      <div class="task-main-row">
        <div class="custom-checkbox ${isChecked ? 'checked' : ''}" onclick="toggleTaskCheck(${task.id}, ${isChecked})"></div>
        <div class="task-content">
          <div class="task-title-group">
            ${completedOrderBadge}
            <span class="task-title">${task.title}</span>
            <span class="priority-tag priority-${task.priority}">${task.priority}</span>
          </div>
          ${task.description ? `<p class="task-desc">${task.description}</p>` : ''}
        </div>
      </div>

      ${trackerHtml}
      ${milestoneHtml}

      <div class="task-footer">
        <div class="task-buttons-left">
          ${isPending ? `
            <button class="btn btn-launch btn-small" onclick="launchTask(${task.id})" title="Pasar a En Progreso y añadir a la Cola de Ejecución">
              🚀 Lanzar Tarea
            </button>
            <button class="btn btn-secondary btn-small" onclick="copyTaskPrompt(${task.id})" title="Copiar orden lista para pegar en Antigravity IDE">
              📋 Copiar Prompt
            </button>
            <button class="btn btn-secondary btn-small" onclick="openCheckModal(${task.id})">
              ✅ Completar & Telegram
            </button>
          ` : isInProgress ? `
            <button class="btn btn-primary btn-small" onclick="openProgressModal(${task.id})" title="Actualizar porcentaje y fase actual">
              📝 Avance
            </button>
            <button class="btn btn-secondary btn-small" onclick="openCheckModal(${task.id})">
              ✅ Completar & Telegram
            </button>
            <button class="btn btn-secondary btn-small" onclick="copyTaskPrompt(${task.id})" title="Copiar orden lista para pegar en Antigravity IDE">
              📋 Copiar Prompt
            </button>
            <button class="btn btn-secondary btn-small" onclick="pauseTask(${task.id})" title="Devolver a Pendientes">
              ⏸️ Pausar
            </button>
          ` : `
            <span style="font-size: 0.74rem; color: var(--accent-emerald); font-weight: 600;">
              ✓ Completado ${task.completed_at ? formatDate(task.completed_at) : ''}
            </span>
          `}
          <button class="comments-toggle-btn" onclick="toggleCommentsDrawer(${task.id})">
            💬 Comentarios (${task.comments ? task.comments.length : 0})
          </button>
        </div>
        <div class="task-buttons-right">
          <button class="btn btn-secondary btn-small" onclick="editTask(${task.id})">✏️</button>
          <button class="btn btn-secondary btn-small" onclick="deleteTask(${task.id})">🗑️</button>
        </div>
      </div>

      <!-- Comments Drawer -->
      <div class="comments-drawer" id="comments-${task.id}">
        <div class="comments-list">${commentsListHtml}</div>
        <div class="comment-input-row">
          <input type="text" id="comment-input-${task.id}" placeholder="Escribe un comentario o nota de progreso..." onkeypress="handleCommentKey(event, ${task.id})">
          <button class="btn btn-secondary btn-small" onclick="addComment(${task.id})">Enviar</button>
        </div>
      </div>
    `;

    tasksContainerEl.appendChild(item);
  });
}

function formatDate(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  return d.toLocaleDateString('es-ES', { hour: '2-digit', minute: '2-digit' });
}

// Checkbox toggle
function toggleTaskCheck(taskId, isCurrentlyChecked) {
  if (isCurrentlyChecked) {
    // Uncheck directly
    updateTaskStatus(taskId, 'pending');
  } else {
    // Open check completion modal to allow comment + photo
    openCheckModal(taskId);
  }
}

async function updateTaskStatus(taskId, newStatus) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force_status: newStatus })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Estado de la tarea actualizado: ${newStatus}`, 'info');
      await loadTasks(state.activeProjectId);
      renderProjectsList(projectSearchEl.value.toLowerCase());
    }
  } catch (err) {
    showToast('Error al actualizar estado', 'error');
  }
}

// Automated check button
async function runAutomatedCheck(taskId) {
  try {
    showToast('Validando hito automáticamente...', 'info');
    const res = await fetch(`/api/tasks/${taskId}/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (data.success) {
      if (data.is_success) {
        showToast('¡Hito verificado con éxito! Notificación enviada a Telegram.', 'success');
      } else {
        showToast(`Hito no superado: ${data.message}`, 'error');
      }
      await loadTasks(state.activeProjectId);
      renderProjectsList(projectSearchEl.value.toLowerCase());
    }
  } catch (err) {
    showToast('Error en la verificación del hito', 'error');
  }
}

async function copyTaskPrompt(taskId) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/prompt`);
    const data = await res.json();
    if (data.success && data.prompt) {
      await navigator.clipboard.writeText(data.prompt);
      showToast('📋 Prompt copiado al portapapeles. Pégalo en Antigravity IDE.', 'success');
    } else {
      showToast('No se pudo generar el prompt', 'error');
    }
  } catch (err) {
    showToast('Error al copiar prompt de la tarea', 'error');
  }
}

// --------------------------------------------------------------------------
// MODAL: COMPLETAR HITO & TELEGRAM
// --------------------------------------------------------------------------
function openCheckModal(taskId) {
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;

  document.getElementById('checkTaskId').value = taskId;
  document.getElementById('checkTaskTitle').textContent = `Tarea: "${task.title}"`;
  document.getElementById('checkComment').value = task.milestone_description ? `Hito cumplido: ${task.milestone_description}` : '';
  document.getElementById('checkImageFile').value = '';
  document.getElementById('checkPreviewImg').src = '';
  document.getElementById('checkImagePreview').style.display = 'none';

  checkModal.classList.add('open');
}

async function submitTaskCompletion() {
  const taskId = document.getElementById('checkTaskId').value;
  const comment = document.getElementById('checkComment').value;
  const fileInput = document.getElementById('checkImageFile');

  let imageUrl = null;

  // Upload image if selected
  if (fileInput.files.length > 0) {
    showToast('Subiendo imagen de resultado...', 'info');
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
      const uploadRes = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      const uploadData = await uploadRes.json();
      if (uploadData.success) {
        imageUrl = uploadData.file_path; // Use absolute path on disk for Telegram
      }
    } catch (err) {
      console.error('Error al subir imagen:', err);
    }
  }

  // Collect verified protocols
  const protocolsVerified = [];
  if (document.getElementById('protoDocs')?.checked) protocolsVerified.push('Documentado en /docs');
  if (document.getElementById('protoOneNote')?.checked) protocolsVerified.push('OneNote actualizado');
  if (document.getElementById('protoGit')?.checked) protocolsVerified.push('Git actualizado y subido');
  if (document.getElementById('protoSkills')?.checked) protocolsVerified.push('Skills y forma de trabajo revisadas');
  if (document.getElementById('protoTelegram')?.checked) protocolsVerified.push('Check enviado a Telegram');

  try {
    showToast('Completando hito y enviando notificación a Telegram...', 'info');
    const res = await fetch(`/api/tasks/${taskId}/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        comment: comment,
        image_url: imageUrl,
        force_status: 'completed',
        protocols_verified: protocolsVerified
      })
    });
    const data = await res.json();
    if (data.success) {
      closeModal('checkModal');
      showToast('¡Tarea completada y enviada a Telegram! (Sincronizando OneNote y Git en 2º plano)', 'success');
      await loadProjects();
      await loadTasks(state.activeProjectId);
      refreshGlobalQueueBadge();
    }
  } catch (err) {
    showToast('Error al completar tarea', 'error');
  }
}

// --------------------------------------------------------------------------
// SMART QUICK TASK CREATOR
// --------------------------------------------------------------------------
async function createSmartTask() {
  const input = document.getElementById('smartTaskInput');
  const prompt = input.value.trim();
  if (!prompt) {
    showToast('Introduce una idea o frase para la tarea', 'error');
    return;
  }
  if (!state.activeProjectId) {
    showToast('Selecciona primero un proyecto', 'error');
    return;
  }

  try {
    showToast('Desglosando y estructurando tarea con IA...', 'info');
    const res = await fetch('/api/tasks/smart-create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: state.activeProjectId,
        prompt: prompt
      })
    });
    const data = await res.json();
    if (data.success) {
      input.value = '';
      showToast('¡Tarea creada en Pendientes! Pulsa 🚀 Lanzar cuando quieras arrancarla.', 'success');
      switchFilterTab('pending');
      await loadTasks(state.activeProjectId);
      renderProjectsList(projectSearchEl.value.toLowerCase());
    } else {
      showToast(`Error al crear tarea: ${data.detail || 'desconocido'}`, 'error');
    }
  } catch (err) {
    showToast('Error en la llamada inteligente', 'error');
  }
}

function startVoiceDictation() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    showToast('Tu navegador no soporta dictado directo por voz. Puedes escribir tu idea en el campo.', 'error');
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = 'es-ES';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  const btnMic = document.getElementById('btnVoiceInput');
  btnMic.classList.add('recording');
  showToast('🎙️ Escuchando... Describe tu tarea.', 'info');

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    document.getElementById('smartTaskInput').value = transcript;
    showToast(`Detectado: "${transcript}"`, 'success');
    btnMic.classList.remove('recording');
  };

  recognition.onerror = (event) => {
    console.error('Error de voz:', event.error);
    btnMic.classList.remove('recording');
    showToast('Error al capturar voz. Inténtalo de nuevo o escríbelo.', 'error');
  };

  recognition.onend = () => {
    btnMic.classList.remove('recording');
  };

  recognition.start();
}

// --------------------------------------------------------------------------
// COMMENTS
// --------------------------------------------------------------------------
function toggleCommentsDrawer(taskId) {
  const drawer = document.getElementById(`comments-${taskId}`);
  if (drawer) {
    drawer.classList.toggle('open');
  }
}

function handleCommentKey(e, taskId) {
  if (e.key === 'Enter') {
    addComment(taskId);
  }
}

async function addComment(taskId) {
  const input = document.getElementById(`comment-input-${taskId}`);
  const text = input.value.trim();
  if (!text) return;

  try {
    const res = await fetch(`/api/tasks/${taskId}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, author: 'Guillermo' })
    });
    const data = await res.json();
    if (data.success) {
      input.value = '';
      await loadTasks(state.activeProjectId);
      // Keep drawer open
      setTimeout(() => {
        const drawer = document.getElementById(`comments-${taskId}`);
        if (drawer) drawer.classList.add('open');
      }, 50);
    }
  } catch (err) {
    showToast('Error al guardar comentario', 'error');
  }
}

// --------------------------------------------------------------------------
// MODAL: NUEVA / EDITAR TAREA
// --------------------------------------------------------------------------
function openTaskModal(task = null) {
  document.getElementById('formTaskId').value = task ? task.id : '';
  document.getElementById('modalTaskTitle').textContent = task ? 'Editar Tarea' : 'Nueva Tarea';
  document.getElementById('formTitle').value = task ? task.title : '';
  document.getElementById('formDescription').value = task ? task.description : '';
  document.getElementById('formPriority').value = task ? task.priority : 'media';
  document.getElementById('formMilestoneType').value = task ? task.milestone_type : 'manual';
  document.getElementById('formMilestoneTarget').value = task ? task.milestone_target : '';
  document.getElementById('formMilestoneDesc').value = task ? task.milestone_description : '';

  taskModal.classList.add('open');
}

function editTask(taskId) {
  const task = state.tasks.find(t => t.id === taskId);
  if (task) {
    openTaskModal(task);
  }
}

async function saveTask() {
  const taskId = document.getElementById('formTaskId').value;
  const title = document.getElementById('formTitle').value.trim();
  const description = document.getElementById('formDescription').value.trim();
  const priority = document.getElementById('formPriority').value;
  const milestone_type = document.getElementById('formMilestoneType').value;
  const milestone_target = document.getElementById('formMilestoneTarget').value.trim();
  const milestone_description = document.getElementById('formMilestoneDesc').value.trim();

  if (!title) {
    showToast('Por favor introduce un título para la tarea', 'error');
    return;
  }

  const payload = {
    project_id: state.activeProjectId,
    title,
    description,
    priority,
    milestone_type,
    milestone_target,
    milestone_description
  };

  try {
    let res;
    if (taskId) {
      res = await fetch(`/api/tasks/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } else {
      res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    }
    const data = await res.json();
    if (data.success) {
      closeModal('taskModal');
      showToast(taskId ? 'Tarea actualizada' : 'Tarea creada en Pendientes. Pulsa 🚀 Lanzar para arrancarla.', 'success');
      if (!taskId) {
        switchFilterTab('pending');
      }
      await loadTasks(state.activeProjectId);
      renderProjectsList(projectSearchEl.value.toLowerCase());
    }
  } catch (err) {
    showToast('Error al guardar tarea', 'error');
  }
}

async function deleteTask(taskId) {
  if (!confirm('¿Estás seguro de eliminar esta tarea?')) return;

  try {
    const res = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      showToast('Tarea eliminada', 'info');
      await loadTasks(state.activeProjectId);
      renderProjectsList(projectSearchEl.value.toLowerCase());
    }
  } catch (err) {
    showToast('Error al eliminar tarea', 'error');
  }
}

// --------------------------------------------------------------------------
// TELEGRAM & SETTINGS
// --------------------------------------------------------------------------
async function testTelegram() {
  try {
    showToast('Enviando mensaje de prueba a Telegram...', 'info');
    const res = await fetch('/api/telegram/test', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('¡Mensaje recibido en Telegram con éxito! Revisa tu móvil.', 'success');
    } else {
      showToast(`Fallo al enviar a Telegram: ${data.error}`, 'error');
    }
  } catch (err) {
    showToast('Error en la llamada a Telegram', 'error');
  }
}

async function openSettingsModal() {
  try {
    loadServices();
    const res = await fetch('/api/settings');
    const settings = await res.json();
    state.settings = settings;

    document.getElementById('settingBotToken').value = settings.telegram_bot_token || '';
    document.getElementById('settingChatId').value = settings.telegram_chat_id || '';
    document.getElementById('settingN8nWebhook').value = settings.n8n_webhook_url || '';
    document.getElementById('settingNotifyTelegram').checked = settings.notify_telegram_enabled !== 'false';
    document.getElementById('settingNotifyViaN8n').checked = settings.notify_via_n8n === 'true';

    settingsModal.classList.add('open');
  } catch (err) {
    showToast('Error al cargar ajustes', 'error');
  }
}

async function saveSettings() {
  const payload = {
    telegram_bot_token: document.getElementById('settingBotToken').value.trim(),
    telegram_chat_id: document.getElementById('settingChatId').value.trim(),
    n8n_webhook_url: document.getElementById('settingN8nWebhook').value.trim(),
    notify_telegram_enabled: document.getElementById('settingNotifyTelegram').checked ? 'true' : 'false',
    notify_via_n8n: document.getElementById('settingNotifyViaN8n').checked ? 'true' : 'false'
  };

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      closeModal('settingsModal');
      showToast('Ajustes guardados correctamente', 'success');
    }
  } catch (err) {
    showToast('Error al guardar ajustes', 'error');
  }
}

// --------------------------------------------------------------------------
// EXECUTION QUEUE & LIVE PROGRESS TRACKING
// --------------------------------------------------------------------------
function switchFilterTab(filterKey) {
  state.currentFilter = filterKey;
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === filterKey);
  });
  renderTasksList();
}

async function launchTask(taskId) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/launch`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('🚀 Tarea lanzada a «En Progreso» y añadida a la Cola Global', 'success');
      await loadTasks(state.activeProjectId);
      renderProjectsList(projectSearchEl.value.toLowerCase());
      refreshGlobalQueueBadge();
    } else {
      showToast(data.error || 'No se pudo lanzar la tarea', 'error');
    }
  } catch (err) {
    showToast('Error al lanzar la tarea', 'error');
  }
}

async function pauseTask(taskId) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/pause`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('⏸️ Tarea devuelta a Pendientes', 'info');
      await loadTasks(state.activeProjectId);
      refreshGlobalQueueBadge();
    }
  } catch (err) {
    showToast('Error al pausar tarea', 'error');
  }
}

let activeProgressTaskId = null;

function openProgressModal(taskId) {
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;
  activeProgressTaskId = taskId;

  const pct = task.progress_pct || 10;
  document.getElementById('progressTaskTitle').textContent = `Tarea: "${task.title}"`;
  document.getElementById('progressRange').value = pct;
  document.getElementById('progressPctLabel').textContent = `${pct}%`;
  document.getElementById('progressStepInput').value = task.current_step || '';
  document.getElementById('progressNoteInput').value = '';

  document.getElementById('progressModal').classList.add('open');
}

function setProgressPreset(pct, stepText) {
  document.getElementById('progressRange').value = pct;
  document.getElementById('progressPctLabel').textContent = `${pct}%`;
  document.getElementById('progressStepInput').value = stepText;
}

async function saveTaskProgress() {
  if (!activeProgressTaskId) return;
  const pct = parseInt(document.getElementById('progressRange').value, 10);
  const step = document.getElementById('progressStepInput').value.trim();
  const note = document.getElementById('progressNoteInput').value.trim();

  try {
    const res = await fetch(`/api/tasks/${activeProgressTaskId}/progress`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        progress_pct: pct,
        current_step: step,
        note: note,
        author: 'Guillermo'
      })
    });
    const data = await res.json();
    if (data.success) {
      closeModal('progressModal');
      if (data.auto_completed || pct >= 100) {
        showToast('¡Tarea al 100% completada automáticamente y enviada a Telegram!', 'success');
      } else {
        showToast(`Progreso actualizado (${pct}%)`, 'success');
      }
      await loadProjects();
      await loadTasks(state.activeProjectId);
      refreshGlobalQueueBadge();
    }
  } catch (err) {
    showToast('Error al guardar el avance', 'error');
  }
}

async function copyAllLaunchedQueue() {
  try {
    const url = state.activeProjectId ? `/api/queue?project_id=${state.activeProjectId}` : '/api/queue';
    const res = await fetch(url);
    const data = await res.json();
    if (data.success && data.master_prompt) {
      await navigator.clipboard.writeText(data.master_prompt);
      showToast(`📋 Orden de ${data.count} tarea(s) copiada al portapapeles. Pégala en Antigravity o di: "Ponte con las tareas lanzadas"`, 'success');
    } else {
      showToast('No hay tareas en progreso en este proyecto para copiar.', 'info');
    }
  } catch (err) {
    showToast('Error al copiar la cola de tareas', 'error');
  }
}

async function refreshGlobalQueueBadge() {
  try {
    const res = await fetch('/api/queue');
    const data = await res.json();
    const btn = document.getElementById('btnOpenGlobalQueue');
    const runner = data.runner || {};
    const total = data.total_global ?? data.count ?? 0;

    if (btn && data.success) {
      if (runner.running) {
        btn.innerHTML = `<span class="btn-icon">⚙️</span> Ejecutando Cola (<span id="globalQueueTopCount">${total}</span>)`;
      } else {
        btn.innerHTML = `<span class="btn-icon">🚀</span> Cola Global (<span id="globalQueueTopCount">${total}</span>)`;
      }
    }
  } catch (err) {
    // silent fail on background poll
  }
}

async function openGlobalQueueModal() {
  document.getElementById('globalQueueModal').classList.add('open');
  await loadGlobalQueueModal();
}

async function loadGlobalQueueModal() {
  try {
    const res = await fetch('/api/queue');
    const data = await res.json();
    if (!data.success) return;

    const badge = document.getElementById('globalQueueTopCount');
    if (badge) badge.textContent = data.total_global ?? 0;

    // Estado en vivo del Worker Autónomo + Watchdog
    const wd = data.watchdog || {};
    const runner = data.runner || {};
    const dot = document.getElementById('gqLiveDot');
    const agentLabel = document.getElementById('gqAgentLabel');
    const summaryText = document.getElementById('gqSummaryText');
    const runnerLogEl = document.getElementById('gqRunnerLog');
    const btnRun = document.getElementById('btnRunGlobalQueue');
    const btnStop = document.getElementById('btnStopGlobalQueue');

    if (btnRun && btnStop) {
      btnRun.style.display = runner.running ? 'none' : 'inline-flex';
      btnStop.style.display = runner.running ? 'inline-flex' : 'none';
    }

    if (dot && agentLabel && summaryText) {
      dot.className = 'gq-live-dot';
      if (runner.running) {
        dot.classList.add('working');
        agentLabel.textContent = `⚙️ Worker Autónomo Activo: "${runner.current_task_title || 'Iniciando...'}" · ${runner.current_model || ''}`;
      } else if (wd.state === 'working') {
        dot.classList.add('working');
        agentLabel.textContent = `${wd.label || '⚡ Trabajando ahora mismo'} · ${wd.active_model || 'Gemini'}`;
      } else if (wd.state === 'quota_error') {
        dot.classList.add('error');
        agentLabel.textContent = wd.label || '⚠️ Cuota agotada';
      } else {
        agentLabel.textContent = `${wd.label || '🟢 Parado / Esperando órdenes'} · ${wd.active_model || 'Gemini'}`;
      }
      summaryText.textContent = `${data.total_global || 0} en progreso (cola activa) · ${data.total_pending || 0} pendientes entre todos los proyectos`;
    }

    if (runnerLogEl) {
      runnerLogEl.textContent = runner.last_log || '';
    }

    const listEl = document.getElementById('globalQueueList');
    if (!listEl) return;
    listEl.innerHTML = '';

    if (!data.tasks || data.tasks.length === 0) {
      listEl.innerHTML = `
        <div class="empty-state" style="padding: 2rem;">
          <div class="empty-icon">🚀</div>
          <h3>La Cola Global está vacía</h3>
          <p>Ve a la pestaña <b>Pendientes</b> de cualquier proyecto y pulsa <b>🚀 Lanzar Tarea</b> para añadir tareas aquí.</p>
        </div>
      `;
      return;
    }

    data.tasks.forEach((t, idx) => {
      const pct = t.progress_pct || 10;
      const stepText = t.current_step || '🚀 En cola de lanzamiento (lista para ejecutar)';
      const isFirst = idx === 0;
      const isLast = idx === data.tasks.length - 1;

      const row = document.createElement('div');
      row.className = 'global-queue-item';
      row.innerHTML = `
        <div class="gq-item-main">
          <div class="gq-order-badge">#${idx + 1}</div>
          <div class="gq-item-info">
            <div class="gq-item-meta">
              <span class="gq-project-pill">${t.project_icon || '📁'} ${t.project_name}</span>
              <span class="priority-tag priority-${t.priority}">${t.priority}</span>
            </div>
            <div class="gq-item-title">${t.title}</div>
            <div class="gq-item-progress-row">
              <div class="gq-mini-bar-bg">
                <div class="gq-mini-bar-fill" style="width: ${pct}%;"></div>
              </div>
              <strong>${pct}%</strong>
              <span>— ${stepText}</span>
            </div>
          </div>
        </div>
        <div class="gq-actions">
          <button class="btn btn-secondary btn-small" onclick="moveGlobalQueueTask(${t.id}, 'up')" ${isFirst ? 'disabled style="opacity:0.35;cursor:not-allowed;"' : ''} title="Subir prioridad en la secuencia">⬆️</button>
          <button class="btn btn-secondary btn-small" onclick="moveGlobalQueueTask(${t.id}, 'down')" ${isLast ? 'disabled style="opacity:0.35;cursor:not-allowed;"' : ''} title="Bajar prioridad en la secuencia">⬇️</button>
          <button class="btn btn-secondary btn-small" onclick="goToProjectFromQueue('${t.project_id}')" title="Ir a este proyecto">🔗 Ir</button>
          <button class="btn btn-secondary btn-small" onclick="pauseFromGlobalQueue(${t.id})" title="Pausar y sacar de la cola activa">⏸️</button>
        </div>
      `;
      listEl.appendChild(row);
    });
  } catch (err) {
    showToast('Error al cargar la Cola Global', 'error');
  }
}

async function moveGlobalQueueTask(taskId, direction) {
  try {
    const res = await fetch(`/api/queue/${taskId}/move/${direction}`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      await loadGlobalQueueModal();
    }
  } catch (err) {
    showToast('Error al reordenar la secuencia', 'error');
  }
}

function goToProjectFromQueue(projectId) {
  closeModal('globalQueueModal');
  selectProject(projectId);
}

async function pauseFromGlobalQueue(taskId) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/pause`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('⏸️ Tarea pausada y devuelta a Pendientes', 'info');
      await loadGlobalQueueModal();
      if (state.activeProjectId) {
        await loadTasks(state.activeProjectId);
      }
    }
  } catch (err) {
    showToast('Error al pausar tarea', 'error');
  }
}

async function copyGlobalQueueSequence() {
  try {
    const res = await fetch('/api/queue');
    const data = await res.json();
    if (data.success && data.master_prompt) {
      await navigator.clipboard.writeText(data.master_prompt);
      showToast(`📋 Secuencia completa (${data.count} tareas) copiada. Pégala en Antigravity o di: "Ejecuta la cola global"`, 'success');
    } else {
      showToast('No hay tareas en la Cola Global para copiar.', 'info');
    }
  } catch (err) {
    showToast('Error al copiar la secuencia global', 'error');
  }
}

async function runGlobalQueueNow() {
  try {
    showToast('▶️ Arrancando Worker Autónomo para ejecutar la secuencia...', 'info');
    const res = await fetch('/api/queue/run', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('🚀 ¡Ejecución autónoma iniciada! Verás el avance en directo.', 'success');
      await loadGlobalQueueModal();
      refreshGlobalQueueBadge();
    } else {
      showToast(data.error || 'No se pudo iniciar la ejecución', 'error');
    }
  } catch (err) {
    showToast('Error al arrancar la Cola Global', 'error');
  }
}

async function stopGlobalQueueNow() {
  try {
    const res = await fetch('/api/queue/stop', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('⏹️ Deteniendo el worker autónomo...', 'info');
      await loadGlobalQueueModal();
      refreshGlobalQueueBadge();
    }
  } catch (err) {
    showToast('Error al detener la ejecución', 'error');
  }
}

// --------------------------------------------------------------------------
// CONSOLA LATERAL DE ACTIVIDAD & SEGUIMIENTO EN VIVO EN LA PÁGINA PRINCIPAL
// --------------------------------------------------------------------------
state.consoleFilter = 'all';
state.telemetry = null;
let activityConsoleTicks = 0;

function setConsoleFilter(filter) {
  state.consoleFilter = filter;
  document.querySelectorAll('.console-filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-filter') === filter);
  });
  renderConsoleTerminal();
}

function clearActivityTerminal() {
  const terminal = document.getElementById('liveActivityTerminal');
  if (terminal) {
    terminal.innerHTML = '<div class="terminal-line placeholder">Consola limpiada por el usuario.</div>';
  }
}

function clearConsoleView(terminalId) {
  const terminal = document.getElementById(terminalId) || document.getElementById('liveActivityTerminal');
  if (terminal) {
    terminal.innerHTML = '<div class="terminal-line placeholder">Consola limpiada por el usuario.</div>';
  }
}

function openServiceUrl(url) {
  window.open(url, '_blank');
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

async function startService(serviceId) {
  showToast(`Arrancando servicio (${serviceId})...`, 'info');
  try {
    const res = await fetch(`/api/services/${encodeURIComponent(serviceId)}/start?open_browser=false`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast(`${data.name || serviceId} iniciado en segundo plano`, 'success');
      loadServices();
      updateActivityConsole();
    } else {
      showToast(data.error || `No se pudo iniciar ${serviceId}`, 'error');
    }
  } catch (err) {
    showToast(`Error arrancando ${serviceId}`, 'error');
  }
}

async function triggerEsiosSync() {
  const btn = document.getElementById('btnEsiosQuickSync');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="btn-icon">⏳</span> Iniciando...';
  }
  try {
    const res = await fetch('/api/services/esios/start', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast(data.message || 'Sincronización de energía iniciada', 'success');
      updateActivityConsole();
      setTimeout(updateActivityConsole, 600);
      setTimeout(updateActivityConsole, 1800);
    } else {
      showToast(data.error || 'No se pudo iniciar la sincronización', 'error');
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '▶️ Iniciar Sincronización';
      }
    }
  } catch (err) {
    showToast('Error conectando con el servicio ESIOS', 'error');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '▶️ Iniciar Sincronización';
    }
  }
}

function formatElapsedSeconds(sec) {
  const m = Math.floor(sec / 60).toString().padStart(2, '0');
  const s = (sec % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

async function updateActivityConsole() {
  activityConsoleTicks++;
  try {
    const res = await fetch('/api/services/monitor');
    if (!res.ok) return;
    const data = await res.json();
    if (!data.success) return;

    state.telemetry = data;
    const esios = data.esios || {};
    const robot = data.robot || {};
    const runner = robot.runner || {};

    // 1. Badge en vivo de la cabecera
    const liveBadge = document.getElementById('activityLiveBadge');
    if (liveBadge) {
      if (runner.running || esios.status === 'running') {
        liveBadge.className = 'activity-live-badge running';
        liveBadge.innerHTML = '⚡ Ejecutando';
      } else {
        liveBadge.className = 'activity-live-badge online';
        liveBadge.innerHTML = '🟢 En Vivo';
      }
    }

    // 2. Actualizar tarjeta de seguimiento del proyecto / tarea seleccionada
    renderSelectedTrackingCard(data);

    // 3. Renderizar consola de logs con filtros
    renderConsoleTerminal();

    // 4. Si hay una tarea en progreso en el proyecto activo, refrescar tareas periódicamente
    if (activityConsoleTicks % 2 === 0 && state.activeProjectId) {
      const hasActive = (state.tasks || []).some(t => t.status === 'in_progress');
      if (hasActive || runner.running) {
        const activeTag = document.activeElement ? document.activeElement.tagName : '';
        const isTyping = ['INPUT', 'TEXTAREA', 'SELECT'].includes(activeTag);
        if (!isTyping) {
          loadTasks(state.activeProjectId, true);
        }
      }
    }
  } catch (err) {
    console.warn('Error actualizando consola de actividad lateral:', err);
  }
}

function renderSelectedTrackingCard(data) {
  const projIconEl = document.getElementById('sidebarProjIcon');
  const projNameEl = document.getElementById('sidebarProjName');
  const projCatEl = document.getElementById('sidebarProjCategory');
  const projBadgeEl = document.getElementById('sidebarProjBadge');
  const progressAreaEl = document.getElementById('sidebarProgressArea');
  const globalWorkerNoticeEl = document.getElementById('globalWorkerNotice');
  const globalWorkerTaskInfoEl = document.getElementById('globalWorkerTaskInfo');

  if (!progressAreaEl) return;

  const currentProject = state.projects.find(p => p.id === state.activeProjectId);
  if (!currentProject) {
    if (projIconEl) projIconEl.textContent = '📁';
    if (projNameEl) projNameEl.textContent = 'Selecciona un Proyecto';
    if (projCatEl) projCatEl.textContent = 'General';
    if (projBadgeEl) projBadgeEl.textContent = '0 tareas';
    progressAreaEl.innerHTML = '<div class="selected-idle-state">Elige un proyecto del menú izquierdo para ver cómo avanza su actividad en tiempo real.</div>';
    if (globalWorkerNoticeEl) globalWorkerNoticeEl.style.display = 'none';
    return;
  }

  // Identidad del proyecto
  if (projIconEl) projIconEl.textContent = currentProject.icon || '📁';
  if (projNameEl) projNameEl.textContent = currentProject.name || 'Proyecto';
  if (projCatEl) projCatEl.textContent = currentProject.category || 'General';

  const esios = data.esios || {};
  const robot = data.robot || {};
  const runner = robot.runner || {};

  const isEsiosProject = currentProject.id === 'actualizador_esios' ||
                         currentProject.folder_name === '2026_Proyecto_Energia_Graficos' ||
                         (currentProject.port && currentProject.port === 8050) ||
                         (currentProject.name && currentProject.name.toLowerCase().includes('energía'));

  // A. Si el proyecto seleccionado es ESIOS (Ingesta de Energía)
  if (isEsiosProject) {
    const isRunning = esios.status === 'running';
    let statusClass = 'online';
    let statusLabel = '✅ Listo / Al día';
    if (isRunning) {
      statusClass = 'running';
      statusLabel = '⚡ Sincronizando';
    } else if (esios.status === 'failed') {
      statusClass = 'stopped';
      statusLabel = '❌ Error';
    } else if (!esios.online) {
      statusClass = 'stopped';
      statusLabel = '🔴 Servicio Apagado';
    }

    if (projBadgeEl) {
      projBadgeEl.textContent = isRunning ? '⚡ Ingesta Activa' : '86 Tareas ESIOS';
      projBadgeEl.className = isRunning ? 'badge badge-accent' : 'badge';
    }

    const pct = esios.progress || (isRunning ? 20 : (esios.status === 'completed' ? 100 : 0));
    const elapsedStr = formatElapsedSeconds(esios.elapsed_time || 0);

    progressAreaEl.innerHTML = `
      <div class="esios-live-card">
        <div class="esios-live-header">
          <span class="cmd-status-badge ${statusClass}">${statusLabel}</span>
          <button type="button" class="btn btn-xs btn-primary" id="btnEsiosQuickSync" onclick="triggerEsiosSync()" ${isRunning ? 'disabled' : ''}>
            ${isRunning ? '⏳ Sincronizando...' : '▶️ Iniciar Sincronización'}
          </button>
        </div>
        <div class="active-task-step-row">
          <span class="active-task-step">${escapeHtml(esios.current_step || 'En espera de órdenes')}</span>
          <span class="active-task-pct">${pct}%</span>
        </div>
        <div class="active-task-bar-bg">
          <div class="active-task-bar-fill" style="width: ${pct}%;"></div>
        </div>
        <div class="esios-metrics-mini-grid">
          <div><label>Transcurrido</label> <strong>${elapsedStr}</strong></div>
          <div><label>ETA</label> <strong>${esios.eta_text || '--'}</strong></div>
          <div><label>Tareas</label> <strong>${esios.completed_tasks || 0}/${esios.total_tasks || 86}</strong></div>
          <div><label>Añadidos</label> <strong style="color:#10b981;">+${esios.total_added || 0}</strong></div>
        </div>
      </div>
    `;
  }
  // B. Proyecto estándar con tareas
  else {
    const tasks = state.tasks || [];
    const inProgressTasks = tasks.filter(t => t.status === 'in_progress');
    const runnerMatchesProject = runner.running && (
      runner.current_project_name === currentProject.name ||
      tasks.some(t => t.id === runner.current_task_id)
    );

    // Si hay una tarea en curso en este proyecto
    if (runnerMatchesProject || inProgressTasks.length > 0) {
      const activeTask = inProgressTasks.find(t => runner.current_task_id && t.id === runner.current_task_id) ||
                         inProgressTasks[0] ||
                         { id: runner.current_task_id, title: runner.current_task_title, progress_pct: 35, current_step: runner.last_log };

      const pct = activeTask.progress_pct || 15;
      const stepText = activeTask.current_step || (runnerMatchesProject && runner.last_log ? runner.last_log : 'Ejecutando tarea en segundo plano...');
      const modelName = runnerMatchesProject ? (runner.current_model || 'Motor Autónomo') : 'Agente Antigravity';

      let elapsedStr = '';
      if (runnerMatchesProject && runner.started_at) {
        try {
          const startMs = new Date(runner.started_at).getTime();
          const diffSec = Math.max(0, Math.floor((Date.now() - startMs) / 1000));
          elapsedStr = formatElapsedSeconds(diffSec);
        } catch (_) {}
      }

      if (projBadgeEl) {
        projBadgeEl.textContent = inProgressTasks.length > 1 ? `${inProgressTasks.length} en curso` : '⚡ En progreso';
        projBadgeEl.className = 'badge badge-accent';
      }

      progressAreaEl.innerHTML = `
        <div class="active-task-live-card">
          <div class="active-task-header-row">
            <span class="badge badge-accent">#${activeTask.id}</span>
            <strong class="active-task-title" title="${escapeHtml(activeTask.title)}">${escapeHtml(activeTask.title)}</strong>
          </div>
          <div class="active-task-step-row">
            <span class="active-task-step">${escapeHtml(stepText)}</span>
            <span class="active-task-pct">${pct}%</span>
          </div>
          <div class="active-task-bar-bg">
            <div class="active-task-bar-fill" style="width: ${pct}%;"></div>
          </div>
          <div class="active-task-meta-row">
            <span>🤖 ${escapeHtml(modelName)}</span>
            ${elapsedStr ? `<span>⏱️ ${elapsedStr}</span>` : `<span>⚡ Activo</span>`}
          </div>
        </div>
      `;
    }
    // Si no hay tarea en curso
    else {
      const pendingTasks = tasks.filter(t => t.status === 'pending');
      const completedTasks = tasks.filter(t => t.status === 'completed');
      const nextPending = pendingTasks[0];

      if (projBadgeEl) {
        projBadgeEl.textContent = `${tasks.length} tareas`;
        projBadgeEl.className = 'badge';
      }

      progressAreaEl.innerHTML = `
        <div class="project-idle-card">
          <div class="idle-status-row">
            <span class="idle-badge">⚪ En espera de ejecución</span>
            <span class="idle-task-stats">${pendingTasks.length} pendientes · ${completedTasks.length} listas</span>
          </div>
          ${nextPending ? `
            <div class="next-task-box">
              <span class="next-task-label">Siguiente tarea pendiente:</span>
              <div class="next-task-content" title="${escapeHtml(nextPending.title)}">
                <strong>#${nextPending.id}</strong> — ${escapeHtml(nextPending.title)}
              </div>
            </div>
          ` : `
            <div class="all-completed-note">🎉 ¡Todas las tareas de este proyecto han sido completadas!</div>
          `}
        </div>
      `;
    }
  }

  // Aviso si el worker de la cola global está ejecutando OTRA tarea de OTRO proyecto
  if (runner.running && !isEsiosProject && runner.current_project_name && runner.current_project_name !== currentProject.name) {
    if (globalWorkerNoticeEl) {
      globalWorkerNoticeEl.style.display = 'flex';
      if (globalWorkerTaskInfoEl) {
        globalWorkerTaskInfoEl.textContent = `#${runner.current_task_id || 0} (${runner.current_project_name})`;
        globalWorkerTaskInfoEl.title = runner.current_task_title || '';
      }
    }
  } else {
    if (globalWorkerNoticeEl) {
      globalWorkerNoticeEl.style.display = 'none';
    }
  }
}

function renderConsoleTerminal() {
  const terminal = document.getElementById('liveActivityTerminal');
  const logCountEl = document.getElementById('activityLogCount');
  const autoScroll = document.getElementById('activityAutoScroll')?.checked ?? true;
  if (!terminal) return;

  const data = state.telemetry || {};
  const robot = data.robot || {};
  const runner = robot.runner || {};
  const esios = data.esios || {};

  const srvLogs = robot.server_logs || [];
  const runLogs = runner.history || [];
  const esiosLogs = esios.logs || [];

  // Combinación y orden cronológico
  const combined = [];
  const seen = new Set();

  [...srvLogs, ...runLogs].forEach(l => {
    const trimmed = l.trim();
    if (trimmed && !seen.has(trimmed)) {
      seen.add(trimmed);
      combined.push(trimmed);
    }
  });

  const currentProject = state.projects.find(p => p.id === state.activeProjectId);
  const activeTaskIds = (state.tasks || []).map(t => `#${t.id}`);
  const filter = state.consoleFilter || 'all';

  let filtered = combined;
  if (filter === 'project') {
    if (currentProject) {
      const projName = currentProject.name.toLowerCase();
      const projFolder = (currentProject.folder_name || '').toLowerCase();
      filtered = combined.filter(l => {
        const lower = l.toLowerCase();
        return lower.includes(projName) ||
               (projFolder && lower.includes(projFolder)) ||
               activeTaskIds.some(tid => l.includes(tid)) ||
               l.includes('[PROGRESO]') ||
               l.includes('[TAREA]') ||
               l.includes('[HITO]');
      });
      if (projFolder.includes('energia') || projName.includes('energía') || currentProject.id === 'actualizador_esios') {
        filtered = [...filtered, ...esiosLogs].slice(-70);
      }
    }
  } else if (filter === 'runner') {
    filtered = combined.filter(l => (
      l.includes('[RUNNER]') ||
      l.includes('[PROGRESO]') ||
      l.includes('[TAREA]') ||
      l.includes('[HITO]') ||
      l.includes('🚀') ||
      l.includes('📊') ||
      l.includes('Gemini') ||
      l.includes('Claude') ||
      l.includes('Worker')
    ));
  }

  const finalLogs = filtered.slice(-80);
  if (logCountEl) {
    logCountEl.textContent = `${finalLogs.length} líneas`;
  }

  if (finalLogs.length === 0) {
    terminal.innerHTML = '<div class="terminal-line placeholder">No hay eventos para el filtro seleccionado. Esperando actividad...</div>';
    return;
  }

  terminal.innerHTML = finalLogs.map(line => {
    let cls = 'terminal-line';
    if (line.includes('ERROR') || line.includes('❌') || line.includes('Falló') || line.includes('⚠️')) {
      cls += ' error';
    } else if (line.includes('[HITO]') || line.includes('✅') || line.includes('200 OK') || line.includes('completada') || line.includes('🟢')) {
      cls += ' success';
    } else if (line.includes('[RUNNER]') || line.includes('[PROGRESO]') || line.includes('⚡') || line.includes('▶️')) {
      cls += ' info';
    } else if (line.includes('[TAREA]') || line.includes('🚀')) {
      cls += ' purple';
    } else if (line.includes('[ESIOS]') || line.includes('🔋')) {
      cls += ' orange';
    }
    return `<div class="${cls}">${escapeHtml(line)}</div>`;
  }).join('');

  if (autoScroll) {
    terminal.scrollTop = terminal.scrollHeight;
  }
}

// --------------------------------------------------------------------------
// UTILS & GLOBAL HANDLERS
// --------------------------------------------------------------------------
window.closeModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('open');
  if (modalId === 'cmdMonitorModal' && cmdMonitorInterval) {
    clearInterval(cmdMonitorInterval);
    cmdMonitorInterval = null;
  }
};

window.openTaskModal = openTaskModal;
window.editTask = editTask;
window.deleteTask = deleteTask;
window.toggleTaskCheck = toggleTaskCheck;
window.openCheckModal = openCheckModal;
window.runAutomatedCheck = runAutomatedCheck;
window.copyTaskPrompt = copyTaskPrompt;
window.openProjectResource = openProjectResource;
window.toggleCommentsDrawer = toggleCommentsDrawer;
window.handleCommentKey = handleCommentKey;
window.addComment = addComment;
window.switchFilterTab = switchFilterTab;
window.launchTask = launchTask;
window.pauseTask = pauseTask;
window.openProgressModal = openProgressModal;
window.setProgressPreset = setProgressPreset;
window.saveTaskProgress = saveTaskProgress;
window.copyAllLaunchedQueue = copyAllLaunchedQueue;
window.openGlobalQueueModal = openGlobalQueueModal;
window.loadGlobalQueueModal = loadGlobalQueueModal;
window.moveGlobalQueueTask = moveGlobalQueueTask;
window.goToProjectFromQueue = goToProjectFromQueue;
window.pauseFromGlobalQueue = pauseFromGlobalQueue;
window.copyGlobalQueueSequence = copyGlobalQueueSequence;
window.runGlobalQueueNow = runGlobalQueueNow;
window.stopGlobalQueueNow = stopGlobalQueueNow;
window.openModelsModal = openModelsModal;
window.renderModelsModal = renderModelsModal;
window.moveModelSequence = moveModelSequence;
window.clearActivityTerminal = clearActivityTerminal;
window.clearConsoleView = clearConsoleView;
window.setConsoleFilter = setConsoleFilter;
window.updateActivityConsole = updateActivityConsole;
window.loadCmdTelemetry = updateActivityConsole;
window.openServiceUrl = openServiceUrl;
window.triggerEsiosSync = triggerEsiosSync;
window.startService = startService;
window.openAllServicesInBrowser = openAllServices;

// Close modals when clicking outside modal-dialog or on Escape key
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.classList.remove('open');
    }
  });
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
  }
});

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icon = type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️');
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
