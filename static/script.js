/* EmoStudyAI — script.js  (corrected) */

let currentEmotion    = 'neutral';
let currentConf       = 0;
let detectionCount    = 0;
let sessionSeconds    = 0;
let historyData       = [];
let emotionCounts     = { happy:0, sad:0, neutral:0, angry:0, surprise:0, disgust:0, fear:0 };
let confHistory       = [];
let lastEnrichEmotion = '';
let trendChart, pieChart, barChart, confChart;

const IS_CLOUD = window.IS_CLOUD || false;
let browserStream = null, browserVideo = null, browserCanvas = null;

const EMOTIONS = {
  happy:    { emoji: '😊', color: '#ffd166', label: 'Happy'    },
  sad:      { emoji: '😢', color: '#6c9fff', label: 'Sad'      },
  neutral:  { emoji: '😐', color: '#a0a8c0', label: 'Neutral'  },
  angry:    { emoji: '😠', color: '#ff6b6b', label: 'Angry'    },
  surprise: { emoji: '😲', color: '#c77dff', label: 'Surprise' },
  disgust:  { emoji: '🤢', color: '#52e3a0', label: 'Disgust'  },
  fear:     { emoji: '😨', color: '#ff9f43', label: 'Fear'     }
};

const RECOMMENDATIONS = {
  happy:    [
    'Attempt difficult problems — you\'re in peak state.',
    'Start a challenging new topic.',
    'Use this energy for deep focused work.',
    'Set ambitious goals for this session.'
  ],
  sad:      [
    'Revise an easy familiar topic first.',
    'Watch a short concept explanation video.',
    'Take a 5-minute mindful break.',
    'Light revision is perfectly fine right now.'
  ],
  neutral:  [
    'Continue your planned study session.',
    'Revise class notes steadily.',
    'Solve moderate-level practice questions.',
    'Try Pomodoro: 25 min study, 5 min break.'
  ],
  angry:    [
    'Pause for 3–5 minutes before continuing.',
    'Do a short box-breathing exercise.',
    'Switch to an easier topic temporarily.',
    'Avoid hard problems right now — reset first.'
  ],
  surprise: [
    'Do a quick concept recall quiz.',
    'Review key points from the last topic.',
    'Test yourself with 2–3 short questions.',
    'Channel this alertness into active recall.'
  ],
  disgust:  [
    'Switch subjects or study method now.',
    'Try interactive or visual learning instead.',
    'Change your environment — fresh start.',
    'Short varied tasks work best here.'
  ],
  fear:     [
    'Break the task into very small steps.',
    'Start with something you already know well.',
    'Progress over perfection — every bit counts.',
    'Breathe slowly then resume gently.'
  ]
};

const PAGE_TITLES = {
  dashboard: 'Dashboard',
  camera:    'Live Camera',
  history:   'Mood History',
  analytics: 'Analytics',
  tips:      'Study Tips'
};

/* ══════════════════════════════════════
   NAVIGATION
══════════════════════════════════════ */
function navigate(page) {
  document.querySelectorAll('.page-content').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const pageEl = document.getElementById('page-' + page);
  const navEl  = document.querySelector(`[data-page="${page}"]`);

  if (pageEl) pageEl.classList.add('active');
  if (navEl)  navEl.classList.add('active');

  const titleEl = document.getElementById('topbar-title');
  if (titleEl) titleEl.textContent = PAGE_TITLES[page] || page;

  if (page === 'history')   renderHistory();
  if (page === 'analytics') renderAnalytics();
  if (page === 'tips')      renderTips();
}

document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => navigate(btn.dataset.page));
});

const gotoCameraBtn = document.getElementById('goto-camera');
if (gotoCameraBtn) gotoCameraBtn.addEventListener('click', () => navigate('camera'));

/* ══════════════════════════════════════
   SESSION TIMER
══════════════════════════════════════ */
setInterval(() => {
  sessionSeconds++;
  const m = String(Math.floor(sessionSeconds / 60)).padStart(2, '0');
  const s = String(sessionSeconds % 60).padStart(2, '0');
  const el = document.getElementById('stat-time');
  if (el) el.textContent = `${m}:${s}`;
}, 1000);

/* ══════════════════════════════════════
   BROWSER WEBCAM
══════════════════════════════════════ */
async function startBrowserWebcam() {
  try {
    browserStream = await navigator.mediaDevices.getUserMedia({ video: true });

    // Hidden video + canvas for frame capture
    browserVideo = document.createElement('video');
    browserVideo.srcObject   = browserStream;
    browserVideo.autoplay    = true;
    browserVideo.playsInline = true;
    browserVideo.style.display = 'none';
    document.body.appendChild(browserVideo);

    browserCanvas = document.createElement('canvas');
    browserCanvas.width  = 640;
    browserCanvas.height = 480;
    browserCanvas.style.display = 'none';
    document.body.appendChild(browserCanvas);

    // Replace all <img id="camera-feed"> and .camera-feed-img placeholders
    // with live <video> elements showing the stream
    function replaceFeedEl(el) {
      if (!el) return;
      const v = document.createElement('video');
      v.srcObject   = browserStream;
      v.autoplay    = true;
      v.playsInline = true;
      v.muted       = true;
      v.className   = el.className;
      el.parentNode.insertBefore(v, el);
      el.style.display = 'none';
    }

    replaceFeedEl(document.getElementById('camera-feed'));
    document.querySelectorAll('#page-camera .camera-feed-img').forEach(replaceFeedEl);

    await new Promise(r => setTimeout(r, 500));
    setInterval(predictFromBrowser, 3000);

  } catch (err) {
    console.error('[Camera] Error:', err);
  }
}

async function predictFromBrowser() {
  if (!browserVideo || !browserCanvas) return;
  try {
    const ctx = browserCanvas.getContext('2d');
    ctx.drawImage(browserVideo, 0, 0, 224, 224);
    const base64 = browserCanvas.toDataURL('image/jpeg', 0.4);
    const res    = await fetch('/predict_frame', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: base64 })
    });
    const data = await res.json();
    if (data.emotion) updateEmotion(data.emotion.toLowerCase(), data.confidence || 0);
  } catch (e) {
    // silent fail — network may be unavailable
  }
}

/* ══════════════════════════════════════
   SERVER WEBCAM (local mode)
══════════════════════════════════════ */
async function pollEmotion() {
  try {
    const res  = await fetch('/get_emotion');
    const data = await res.json();
    if (data && data.emotion) updateEmotion(data.emotion.toLowerCase(), data.confidence || 0);
  } catch (e) {
    // silent fail
  }
}

/* ══════════════════════════════════════
   UPDATE EMOTION  ← main bug fix here
══════════════════════════════════════ */
function updateEmotion(emotion, conf) {
  const cfg = EMOTIONS[emotion] || EMOTIONS.neutral;
  currentEmotion = emotion;
  currentConf    = conf;

  // Stat bar
  setText('stat-emotion', cfg.label);
  setText('stat-conf',    (conf * 100).toFixed(1) + '%');

  // Topbar chip
  setText('chip-emoji', cfg.emoji);
  setText('chip-label', cfg.label);

  // Dashboard overlay
  setText('overlay-emoji',   cfg.emoji);
  setText('overlay-emotion', cfg.label);
  setText('overlay-conf',    `Confidence: ${(conf * 100).toFixed(0)}%`);

  // Camera page overlay
  setText('cam-page-emoji',   cfg.emoji);
  setText('cam-page-emotion', cfg.label);
  setText('cam-page-conf',    `Confidence: ${(conf * 100).toFixed(0)}%`);

  // Confidence bars
  const pct = Math.min(conf * 100, 100).toFixed(1) + '%';
  setWidth('conf-bar-fill', pct);
  setText('conf-bar-pct',  pct);
  setWidth('cam-conf-fill', pct);
  setText('cam-conf-pct',  pct);

  // Meters
  updateMeter('meter-list',     emotion, conf);
  updateMeter('cam-meter-list', emotion, conf);

  // Counters
  detectionCount++;
  setText('stat-detects', detectionCount);
  emotionCounts[emotion] = (emotionCounts[emotion] || 0) + 1;
  confHistory.push(+(conf * 100).toFixed(1));

  // History
  const recs = RECOMMENDATIONS[emotion] || RECOMMENDATIONS.neutral;
  historyData.unshift({
    emotion,
    conf,
    recommendation: recs[0],
    time: new Date().toLocaleTimeString()
  });
  if (historyData.length > 50) historyData.pop();

  renderRecs(emotion);
  updateAnalyticsSummary();

  // Enrichment call (only when emotion changes)
  if (emotion !== lastEnrichEmotion) {
    lastEnrichEmotion = emotion;
    fetchEnrichment(emotion, conf);
  }
}

/* helpers */
function setText(id, val)  { const el = document.getElementById(id); if (el) el.textContent = val; }
function setWidth(id, val) { const el = document.getElementById(id); if (el) el.style.width  = val; }

/* ══════════════════════════════════════
   EMOTION METER
══════════════════════════════════════ */
function updateMeter(containerId, activeEmotion, conf) {
  const list = document.getElementById(containerId);
  if (!list) return;
  list.innerHTML = Object.entries(EMOTIONS).map(([key, cfg]) => {
    const pct = key === activeEmotion ? Math.min(conf * 100, 100).toFixed(0) : 0;
    return `
      <div class="meter-row">
        <div class="meter-label">${cfg.emoji} ${cfg.label}</div>
        <div class="meter-track">
          <div class="meter-fill" style="width:${pct}%;background:${cfg.color}"></div>
        </div>
        <div class="meter-val">${pct}%</div>
      </div>`;
  }).join('');
}
updateMeter('meter-list',     'neutral', 0);
updateMeter('cam-meter-list', 'neutral', 0);

/* ══════════════════════════════════════
   RECOMMENDATIONS
══════════════════════════════════════ */
function renderRecs(emotion) {
  const recs = RECOMMENDATIONS[emotion] || RECOMMENDATIONS.neutral;
  ['rec-list', 'cam-rec-list'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.innerHTML = recs
        .map(r => `<div class="rec-item"><div class="rec-dot"></div>${r}</div>`)
        .join('');
    }
  });
}
renderRecs('neutral');

const refreshRecsBtn = document.getElementById('refresh-recs-btn');
if (refreshRecsBtn) refreshRecsBtn.addEventListener('click', () => renderRecs(currentEmotion));

/* ══════════════════════════════════════
   ENRICHMENT API  ← fixed undefined vars
══════════════════════════════════════ */
async function fetchEnrichment(emotion, conf) {
  const adviceEl = document.getElementById('ai-advice');   // fixed: was using wrong var name
  if (adviceEl) {
    adviceEl.textContent = '🤖 Thinking…';
    adviceEl.classList.add('ai-loading');
  }

  try {
    const res  = await fetch('/api/enrich', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ emotion, confidence: conf })
    });
    const data = await res.json();

    // AI advice
    if (adviceEl) {
      adviceEl.textContent = data.ai_advice || 'No advice available.';
      adviceEl.classList.remove('ai-loading');
    }

    // Quote
    if (data.quote) {
      setText('quote-text',   `"${data.quote.quote}"`);
      setText('quote-author', `— ${data.quote.author}`);
    }

    // Videos
    if (data.videos && data.videos.length) renderVideos(data.videos);

  } catch (e) {
    if (adviceEl) {
      adviceEl.textContent = 'AI advice unavailable.';
      adviceEl.classList.remove('ai-loading');
    }
  }
}

/* Quote refresh */
const refreshQuoteBtn = document.getElementById('refresh-quote-btn');
if (refreshQuoteBtn) {
  refreshQuoteBtn.addEventListener('click', async () => {
    try {
      const res  = await fetch('/api/enrich', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ emotion: currentEmotion, confidence: currentConf })
      });
      const data = await res.json();
      if (data.quote) {
        setText('quote-text',   `"${data.quote.quote}"`);
        setText('quote-author', `— ${data.quote.author}`);
      }
    } catch (e) {}
  });
}

/* Videos refresh */
const refreshVideosBtn = document.getElementById('refresh-videos-btn');
if (refreshVideosBtn) {
  refreshVideosBtn.addEventListener('click', async () => {
    try {
      const res  = await fetch('/api/enrich', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ emotion: currentEmotion, confidence: currentConf })
      });
      const data = await res.json();
      if (data.videos && data.videos.length) renderVideos(data.videos);
    } catch (e) {}
  });
}

/* ══════════════════════════════════════
   RENDER VIDEOS
══════════════════════════════════════ */
function renderVideos(videos) {
  const grid = document.getElementById('video-grid');
  if (!grid) return;
  grid.innerHTML = videos.map(v => `
    <a class="video-thumb" href="${v.url}" target="_blank" rel="noopener noreferrer">
      <div class="video-thumb-wrap">
        <img src="${v.thumbnail}" alt="${v.title}" loading="lazy"
             onerror="this.src='https://img.youtube.com/vi/default/mqdefault.jpg'"/>
        <div class="video-play-btn">▶</div>
      </div>
      <div class="video-thumb-title">${v.title}</div>
    </a>`).join('');
}

/* ══════════════════════════════════════
   AI CHAT
══════════════════════════════════════ */
async function sendMessage() {
  const input   = document.getElementById('chat-input');
  const chatBox = document.getElementById('chat-box');
  const message = input.value.trim();
  if (!message) return;

  chatBox.innerHTML += `<div class="message user">${message}</div>`;
  input.value = '';

  const typingId = 'typing-' + Date.now();
  chatBox.innerHTML += `<div id="${typingId}" class="message bot typing">🤖 Typing…</div>`;
  chatBox.scrollTop = chatBox.scrollHeight;

  try {
    const res  = await fetch('/api/chat', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ message })
    });
    const data = await res.json();
    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();
    chatBox.innerHTML += `<div class="message bot">${data.response}</div>`;
    chatBox.scrollTop = chatBox.scrollHeight;
  } catch (err) {
    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();
    chatBox.innerHTML += `<div class="message bot">⚠️ Error connecting to server.</div>`;
  }
}

function quickMsg(text) {
  const input = document.getElementById('chat-input');
  if (input) input.value = text;
  sendMessage();
}

const chatInput = document.getElementById('chat-input');
if (chatInput) chatInput.addEventListener('keypress', e => { if (e.key === 'Enter') sendMessage(); });

/* ══════════════════════════════════════
   SAVE SESSION
══════════════════════════════════════ */
const saveBtn = document.getElementById('save-btn');
if (saveBtn) {
  saveBtn.addEventListener('click', async () => {
    try {
      const res = await fetch('/save_session', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          emotion:      currentEmotion,
          confidence:   currentConf,
          session_time: sessionSeconds,
          detections:   detectionCount
        })
      });
      alert(res.ok ? '✅ Session saved!' : '⚠️ Save failed.');
    } catch (e) {
      alert('⚠️ Cannot connect to server.');
    }
  });
}

/* ══════════════════════════════════════
   HISTORY PAGE
══════════════════════════════════════ */
function renderHistory() {
  const recent = historyData.slice(0, 20).reverse();
  const tbody  = document.getElementById('history-body');

  // Trend chart
  if (trendChart) trendChart.destroy();
  const trendCanvas = document.getElementById('trend-chart');
  if (trendCanvas) {
    trendChart = new Chart(trendCanvas, {
      type: 'line',
      data: {
        labels:   recent.map((_, i) => i + 1),
        datasets: [{
          label:              'Confidence %',
          data:               recent.map(d => (d.conf * 100).toFixed(1)),
          borderColor:        '#6c63ff',
          backgroundColor:    'rgba(108,99,255,.1)',
          pointBackgroundColor: recent.map(d => EMOTIONS[d.emotion]?.color || '#6c63ff'),
          pointRadius:        5,
          tension:            0.4,
          fill:               true
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: '#1f2330' }, ticks: { color: '#5a607a' } },
          y: { grid: { color: '#1f2330' }, ticks: { color: '#5a607a' }, min: 0, max: 100 }
        }
      }
    });
  }

  // Table
  if (!tbody) return;
  if (!historyData.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="no-data-cell">No history yet.</td></tr>';
    return;
  }
  tbody.innerHTML = historyData.slice(0, 20).map((d, i) => {
    const cfg = EMOTIONS[d.emotion] || EMOTIONS.neutral;
    return `<tr>
      <td style="color:var(--muted)">${i + 1}</td>
      <td><span class="emotion-tag" style="background:${cfg.color}22;color:${cfg.color}">${cfg.emoji} ${cfg.label}</span></td>
      <td>${(d.conf * 100).toFixed(1)}%</td>
      <td style="color:var(--muted);font-size:12px">${d.recommendation}</td>
      <td style="color:var(--muted)">${d.time}</td>
    </tr>`;
  }).join('');
}

/* ══════════════════════════════════════
   ANALYTICS SUMMARY (live update)
══════════════════════════════════════ */
function updateAnalyticsSummary() {
  let maxEmotion = 'neutral', maxValue = 0;
  for (const [key, val] of Object.entries(emotionCounts)) {
    if (val > maxValue) { maxValue = val; maxEmotion = key; }
  }
  const cfg = EMOTIONS[maxEmotion] || EMOTIONS.neutral;
  setText('dominantEmotion', `${cfg.emoji} ${cfg.label}`);

  const total = Object.values(emotionCounts).reduce((a, b) => a + b, 0);
  if (total > 0) {
    const focusScore = Math.round(
      ((emotionCounts.neutral + emotionCounts.happy) / total) * 100
    );
    setText('focusScore', focusScore + '%');
  }
}

/* ══════════════════════════════════════
   ANALYTICS PAGE
══════════════════════════════════════ */
function renderAnalytics() {
  updateAnalyticsSummary();

  const labels = Object.keys(emotionCounts).map(k => EMOTIONS[k]?.label || k);
  const vals   = Object.values(emotionCounts);
  const colors = Object.keys(emotionCounts).map(k => EMOTIONS[k]?.color || '#6c63ff');

  if (pieChart) pieChart.destroy();
  const pieCanvas = document.getElementById('pie-chart');
  if (pieCanvas) {
    pieChart = new Chart(pieCanvas, {
      type: 'doughnut',
      data: { labels, datasets: [{ data: vals, backgroundColor: colors, borderWidth: 2, borderColor: '#111318' }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'right', labels: { color: '#a0a8c0', font: { size: 12 } } } }
      }
    });
  }

  if (barChart) barChart.destroy();
  const barCanvas = document.getElementById('bar-chart');
  if (barCanvas) {
    barChart = new Chart(barCanvas, {
      type: 'bar',
      data: { labels, datasets: [{ label: 'Count', data: vals, backgroundColor: colors, borderRadius: 6, borderWidth: 0 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false },      ticks: { color: '#5a607a' } },
          y: { grid: { color: '#1f2330' },    ticks: { color: '#5a607a' }, beginAtZero: true }
        }
      }
    });
  }

  if (confChart) confChart.destroy();
  const confCanvas = document.getElementById('conf-chart');
  if (confCanvas) {
    confChart = new Chart(confCanvas, {
      type: 'line',
      data: {
        labels:   confHistory.map((_, i) => i + 1),
        datasets: [{
          label:           'Confidence %',
          data:            confHistory,
          borderColor:     '#ff6584',
          backgroundColor: 'rgba(255,101,132,.08)',
          tension:         0.4,
          fill:            true,
          pointRadius:     3,
          pointBackgroundColor: '#ff6584'
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: '#1f2330' }, ticks: { color: '#5a607a', maxTicksLimit: 10 } },
          y: { grid: { color: '#1f2330' }, ticks: { color: '#5a607a' }, min: 0, max: 100 }
        }
      }
    });
  }
}

/* ══════════════════════════════════════
   STUDY TIPS PAGE
══════════════════════════════════════ */
function renderTips() {
  const grid = document.getElementById('tips-grid');
  if (!grid) return;
  grid.innerHTML = Object.entries(EMOTIONS).map(([key, cfg]) => {
    const tips = RECOMMENDATIONS[key] || [];
    return `
      <div class="tip-card">
        <div class="tip-emotion-icon">${cfg.emoji}</div>
        <div class="tip-emotion-name" style="color:${cfg.color}">${cfg.label}</div>
        <ul class="tip-list">${tips.map(t => `<li>${t}</li>`).join('')}</ul>
      </div>`;
  }).join('');
}

/* ══════════════════════════════════════
   INIT
══════════════════════════════════════ */
(async function init() {
  // Load initial quote + videos for neutral state
  try {
    const res  = await fetch('/api/enrich', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ emotion: 'neutral', confidence: 0 })
    });
    const data = await res.json();
    if (data.quote) {
      setText('quote-text',   `"${data.quote.quote}"`);
      setText('quote-author', `— ${data.quote.author}`);
    }
    if (data.videos && data.videos.length) renderVideos(data.videos);
  } catch (e) {}

  // Start webcam / polling
  if (IS_CLOUD) {
    console.log('[Mode] Cloud — browser webcam');
    await startBrowserWebcam();
  } else {
    console.log('[Mode] Local — server webcam');
    pollEmotion();
    setInterval(pollEmotion, 2000);
  }
})();