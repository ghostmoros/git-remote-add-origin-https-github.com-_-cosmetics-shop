/* AI Trading Dashboard — frontend logic */

let ws = null;
let alertCount = 0;

// ── DOM refs ────────────────────────────────────────────────────────────────
const wsDot       = document.getElementById('ws-dot');
const wsLabel     = document.getElementById('ws-label');
const scanInfo    = document.getElementById('scan-info');
const lastScan    = document.getElementById('last-scan');
const btnStart    = document.getElementById('btn-start');
const btnStop     = document.getElementById('btn-stop');
const statusDot   = document.getElementById('status-dot');
const statusText  = document.getElementById('status-text');
const screenImg   = document.getElementById('screen-img');
const screenPlh   = document.getElementById('screen-placeholder');
const alertsList  = document.getElementById('alerts-list');
const alertCountEl= document.getElementById('alert-count');
const quickBar    = document.getElementById('quick-bar');
const qbInst      = document.getElementById('qb-instrument');
const qbDir       = document.getElementById('qb-direction');
const qbCf        = document.getElementById('qb-cf');
const qbSummary   = document.getElementById('qb-summary');
const chatMessages= document.getElementById('chat-messages');
const chatInput   = document.getElementById('chat-input');
const btnSend     = document.getElementById('btn-send');
const useScreen   = document.getElementById('use-screen');
const modalOverlay= document.getElementById('modal-overlay');
const modalTitle  = document.getElementById('modal-title');
const modalBody   = document.getElementById('modal-body');
const modalClose  = document.getElementById('modal-close');

// ── WebSocket ────────────────────────────────────────────────────────────────
function connect() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws`);

  ws.onopen = () => {
    wsDot.className = 'dot connected';
    wsLabel.textContent = 'Подключено';
  };

  ws.onclose = () => {
    wsDot.className = 'dot error';
    wsLabel.textContent = 'Отключено — переподключение...';
    setTimeout(connect, 3000);
  };

  ws.onerror = () => {
    wsDot.className = 'dot error';
  };

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    handleMessage(msg);
  };
}

function send(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(obj));
  }
}

// ── Message handler ──────────────────────────────────────────────────────────
function handleMessage(msg) {
  switch (msg.type) {

    case 'init':
      setMonitorState(msg.monitor_running);
      scanInfo.textContent = `Сканов: ${msg.scan_count}`;
      lastScan.textContent  = `Последний: ${msg.last_scan}`;
      if (msg.screenshot) setScreenshot(msg.screenshot);
      if (msg.alerts && msg.alerts.length) {
        alertsList.innerHTML = '';
        msg.alerts.forEach(addAlertCard);
      }
      break;

    case 'monitor_status':
      setMonitorState(msg.running);
      break;

    case 'scan':
      scanInfo.textContent = `Сканов: ${msg.count}`;
      lastScan.textContent  = `Последний: ${msg.time}`;
      break;

    case 'screenshot':
      setScreenshot(msg.data);
      break;

    case 'quick_scan':
      updateQuickBar(msg);
      break;

    case 'alert':
      addAlertCard(msg.alert);
      playAlert();
      break;

    case 'alerts_cleared':
      alertsList.innerHTML = '<div class="empty-state">Алертов пока нет.</div>';
      alertCount = 0;
      alertCountEl.textContent = '0';
      break;

    case 'chat_thinking':
      addChatMsg('Анализирую...', 'bot thinking', '_thinking');
      break;

    case 'chat_reply':
      const thinking = document.getElementById('_thinking');
      if (thinking) thinking.remove();
      addChatMsg(msg.text, 'bot');
      break;

    case 'error':
      const thinking2 = document.getElementById('_thinking');
      if (thinking2) thinking2.remove();
      addChatMsg(`Ошибка: ${msg.message}`, 'bot');
      break;
  }
}

// ── Screenshot ───────────────────────────────────────────────────────────────
function setScreenshot(b64) {
  screenImg.src = 'data:image/png;base64,' + b64;
  screenImg.style.display = 'block';
  screenPlh.style.display = 'none';
}

// ── Monitor state ─────────────────────────────────────────────────────────────
function setMonitorState(running) {
  btnStart.disabled = running;
  btnStop.disabled  = !running;
  statusDot.className = 'status-dot ' + (running ? 'running' : 'stopped');
  statusText.textContent = running ? 'Работает' : 'Остановлен';
}

// ── Quick scan bar ────────────────────────────────────────────────────────────
function updateQuickBar(msg) {
  quickBar.style.display = 'flex';
  qbInst.textContent = msg.instrument || '—';
  qbDir.textContent  = msg.direction  || '—';
  qbDir.className    = 'qb-dir ' + (msg.direction || '').toLowerCase();
  qbCf.textContent   = (msg.confluences || 0) + ' cf';
  qbSummary.textContent = msg.summary || '';
}

// ── Alerts ────────────────────────────────────────────────────────────────────
function addAlertCard(alert) {
  // Remove empty state
  const empty = alertsList.querySelector('.empty-state');
  if (empty) empty.remove();

  alertCount++;
  alertCountEl.textContent = alertCount;

  const dir = (alert.direction || '').toLowerCase();
  const card = document.createElement('div');
  card.className = `alert-card ${dir}`;
  card.innerHTML = `
    <div class="alert-header">
      <span class="alert-time">${alert.timestamp}</span>
      <span class="alert-inst">${alert.instrument}</span>
      <span class="alert-dir ${dir}">${alert.direction}</span>
      <span class="alert-cf">⬡ ${alert.confluences}</span>
    </div>
    <div class="alert-summary">${alert.summary}</div>
  `;
  card.addEventListener('click', () => openModal(alert));
  alertsList.prepend(card);
}

function openModal(alert) {
  const dir = (alert.direction || '').toLowerCase();
  modalTitle.textContent = `${alert.direction} ${alert.instrument} — ${alert.timestamp}`;
  modalTitle.style.color = dir === 'buy' ? 'var(--green)' : 'var(--red)';
  modalBody.textContent = alert.analysis;
  modalOverlay.style.display = 'flex';
}

modalClose.addEventListener('click', () => modalOverlay.style.display = 'none');
modalOverlay.addEventListener('click', (e) => {
  if (e.target === modalOverlay) modalOverlay.style.display = 'none';
});

function playAlert() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.4);
  } catch (_) {}
}

// ── Chat ─────────────────────────────────────────────────────────────────────
function addChatMsg(text, cls, id) {
  const div = document.createElement('div');
  div.className = 'msg ' + cls;
  if (id) div.id = id;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function sendChat() {
  const text = chatInput.value.trim();
  if (!text) return;
  addChatMsg(text, 'user');
  chatInput.value = '';
  send({ action: 'chat', text, use_screen: useScreen.checked });
}

btnSend.addEventListener('click', sendChat);
chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
});

// ── Controls ──────────────────────────────────────────────────────────────────
btnStart.addEventListener('click', () => {
  send({
    action:   'start_monitor',
    interval: parseInt(document.getElementById('interval').value) || 60,
    min_cf:   parseInt(document.getElementById('min-cf').value)   || 3,
    context:  document.getElementById('context').value,
  });
});

btnStop.addEventListener('click', () => {
  send({ action: 'stop_monitor' });
});

document.getElementById('btn-screenshot').addEventListener('click', () => {
  send({ action: 'screenshot' });
});

document.getElementById('btn-clear-alerts').addEventListener('click', () => {
  send({ action: 'clear_alerts' });
});

// ── Init ─────────────────────────────────────────────────────────────────────
connect();
