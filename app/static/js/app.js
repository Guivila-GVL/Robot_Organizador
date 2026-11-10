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
  loadProjects().then(() => {
    // Select first project by default
    if (state.projects.length > 0) {
      selectProject(state.projects[0].id);
    }
  });

  // Service & Watchdog polling every 10s + live progress refresh if in_progress tasks exist
  setInterval(() => {
    loadServices();
    loadWatchdogStatus();

    const activeTag = document.activeElement ? document.activeElement.tagName : '';
    const isTyping = ['INPUT', 'TEXTAREA', 'SELECT'].includes(activeTag);
    const hasModalOpen = document.querySelector('.modal-overlay.open') !== null;
    if (!isTyping && !hasModalOpen && state.activeProjectId && state.tasks.some(t => t.status === 'in_progress')) {
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
    const stateEl = document.getElementById('watchdogState');
    const cardEl = document.getElementById('agentStatusCard') || document.querySelector('.agent-status-card');
    const modelEl = document.getElementById('watchdogModel');
    const pctEl = document.getElementById('watchdogQuotaPct');
    const barEl = document.getElementById('watchdogQuotaBar');
    const resetEl = document.getElementById('watchdogResetTime');

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
  } catch (err) {
    console.error('Error al consultar Watchdog:', err);
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
  try {
    const res = await fetch(`/api/projects/${state.activeProjectId}/open-resource/${resourceKey}`, {
      method: 'POST'
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message || 'Recurso abierto', 'success');
    } else {
      showToast(data.error || 'No se pudo abrir el recurso', 'error');
    }
  } catch (err) {
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

function renderTasksList() {
  tasksContainerEl.innerHTML = '';

  let filtered = state.tasks;
  if (state.currentFilter !== 'all') {
    filtered = state.tasks.filter(t => t.status === state.currentFilter);
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
      showToast('¡Tarea completada y enviada a Telegram con éxito!', 'success');
      await loadTasks(state.activeProjectId);
      renderProjectsList(projectSearchEl.value.toLowerCase());
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
      showToast('🚀 Tarea lanzada a «En Progreso» y añadida a la Cola de Ejecución', 'success');
      await loadTasks(state.activeProjectId);
      renderProjectsList(projectSearchEl.value.toLowerCase());
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
      showToast(`Progreso actualizado (${pct}%)`, 'success');
      await loadTasks(state.activeProjectId);
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

// --------------------------------------------------------------------------
// UTILS & GLOBAL HANDLERS
// --------------------------------------------------------------------------
window.closeModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('open');
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
