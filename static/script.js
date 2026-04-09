/* ═══════════════════════════════════════════════════════════
   EmoStudyAI — script.js
   Supports both LOCAL (server webcam) and CLOUD (browser webcam)
═══════════════════════════════════════════════════════════ */

/* ─── STATE ──────────────────────────────────────────────── */
let currentEmotion    = 'neutral';
let currentConf       = 0;
let detectionCount    = 0;
let sessionSeconds    = 0;
let historyData       = [];
let emotionCounts     = { happy:0, sad:0, neutral:0, angry:0, surprise:0, disgust:0, fear:0 };
let confHistory       = [];
let lastEnrichEmotion = '';
let trendChart, pieChart, barChart, confChart;

// Cloud mode — set by dashboard.html via window.IS_CLOUD
const IS_CLOUD = window.IS_CLOUD || false;

// Browser webcam variables (cloud mode)
let browserStream     = null;
let browserVideo      = null;
let browserCanvas     = null;
let predictInterval   = null;

/* ─── EMOTION CONFIG ─────────────────────────────────────── */
const EMOTIONS = {
  happy:    { emoji: '😊', color: '#ffd166', label: 'Happy' },
  sad:      { emoji: '😢', color: '#6c9fff', label: 'Sad' },
  neutral:  { emoji: '😐', color: '#a0a8c0', label: 'Neutral' },
  angry:    { emoji: '😠', color: '#ff6b6b', label: 'Angry' },
  surprise: { emoji: '😲', color: '#c77dff', label: 'Surprise' },
  disgust:  { emoji: '🤢', color: '#52e3a0', label: 'Disgust' },
  fear:     { emoji: '😨', color: '#ff9f43', label: 'Fear' }
};

const RECOMMENDATIONS = {
  happy:    ['Attempt difficult problems — you\'re in peak state.','Start a challenging new topic.','Use this energy for deep focused work.','Set ambitious goals for this session.'],
  sad:      ['Revise an easy familiar topic first.','Watch a short concept explanation video.','Take a 5-minute mindful break.','Light revision is perfectly fine right now.'],
  neutral:  ['Continue your planned study session.','Revise class notes steadily.','Solve moderate-level practice questions.','Try Pomodoro: 25 min study, 5 min break.'],
  angry:    ['Pause for 3–5 minutes before continuing.','Do a short box-breathing exercise.','Switch to an easier topic temporarily.','Avoid hard problems right now — reset first.'],
  surprise: ['Do a quick concept recall quiz.','Review key points from the last topic.','Test yourself with 2–3 short questions.','Channel this alertness into active recall.'],
  disgust:  ['Switch subjects or study method now.','Try interactive or visual learning instead.','Change your environment — fresh start.','Short varied tasks work best here.'],
  fear:     ['Break the task into very small steps.','Start with something you already know well.','Progress over perfection — every bit counts.','Breathe slowly then resume gently.']
};

const PAGE_TITLES = {
  dashboard: 'Dashboard', camera: 'Live Camera',
  history: 'Mood History', analytics: 'Analytics', tips: 'Study Tips'
};

/* ═══════════════════════════════════════════════════════════
   NAVIGATION
═══════════════════════════════════════════════════════════ */
function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.querySelector(`[data-page="${page}"]`).classList.add('active');
  document.getElementById('topbar-title').textContent = PAGE_TITLES[page];
  if (page === 'history')   renderHistory();
  if (page === 'analytics') renderAnalytics();
  if (page === 'tips')      renderTips();
}

document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => navigate(btn.dataset.page));
});

const gotoCameraBtn = document.getElementById('goto-camera');
if (gotoCameraBtn) gotoCameraBtn.addEventListener('click', () => navigate('camera'));

/* ═══════════════════════════════════════════════════════════
   SESSION TIMER
═══════════════════════════════════════════════════════════ */
setInterval(() => {
  sessionSeconds++;
  const m = String(Math.floor(sessionSeconds / 60)).padStart(2, '0');
  const s = String(sessionSeconds % 60).padStart(2, '0');
  document.getElementById('stat-time').textContent = `${m}:${s}`;
}, 1000);

/* ═══════════════════════════════════════════════════════════
   BROWSER WEBCAM (Cloud mode)
   Captures frame from browser, sends to /predict_frame
═══════════════════════════════════════════════════════════ */
async function startBrowserWebcam() {
  try {
    browserStream = await navigator.mediaDevices.getUserMedia({ video: true });

    // Create hidden video element
    browserVideo          = document.createElement('video');
    browserVideo.srcObject = browserStream;
    browserVideo.autoplay  = true;
    browserVideo.playsInline = true;
    browserVideo.style.display = 'none';
    document.body.appendChild(browserVideo);

    // Create hidden canvas for frame capture
    browserCanvas = document.createElement('canvas');
    browserCanvas.width  = 640;
    browserCanvas.height = 480;
    browserCanvas.style.display = 'none';
    document.body.appendChild(browserCanvas);

    // Show browser video in camera feed area
    const feedImg = document.getElementById('camera-feed');
    if (feedImg) {
      // Replace img with video element in same position
      feedImg.style.display = 'none';
      const videoEl = document.createElement('video');
      videoEl.srcObject   = browserStream;
      videoEl.autoplay    = true;
      videoEl.playsInline = true;
      videoEl.muted       = true;
      videoEl.className   = 'camera-feed-img';
      feedImg.parentNode.insertBefore(videoEl, feedImg);
    }

    // Also show in camera page
    const camPageFeed = document.querySelector('#page-camera .camera-feed-img');
    if (camPageFeed) {
      camPageFeed.style.display = 'none';
      const videoEl2 = document.createElement('video');
      videoEl2.srcObject   = browserStream;
      videoEl2.autoplay    = true;
      videoEl2.playsInline = true;
      videoEl2.muted       = true;
      videoEl2.className   = 'camera-feed-img';
      camPageFeed.parentNode.insertBefore(videoEl2, camPageFeed);
    }

    console.log('[Camera] Browser webcam started');

    // Start predicting every 2 seconds
    await new Promise(r => setTimeout(r, 500)); // wait for video to load
    predictInterval = setInterval(predictFromBrowser, 2000);

  } catch (err) {
    console.error('[Camera] Browser webcam error:', err);
    const placeholder = document.getElementById('cam-placeholder');
    if (placeholder) {
      placeholder.style.display = 'flex';
      placeholder.innerHTML = '<span style="font-size:36px">📷</span>Camera permission denied';
    }
  }
}

async function sendMessage() {
    const input   = document.getElementById("chat-input");
    const chatBox = document.getElementById("chat-box");
    const message = input.value.trim();
    if (!message) return;

    chatBox.innerHTML += `<div class="message user">${message}</div>`;
    input.value = "";
    chatBox.scrollTop = chatBox.scrollHeight;

    // Show typing indicator
    chatBox.innerHTML += `<div class="message bot" id="typing">Thinking…</div>`;

    try {
        const res = await fetch("/api/chat", {
            method:  "POST",
            headers: {"Content-Type": "application/json"},
            body:    JSON.stringify({
                message,
                emotion:    currentEmotion,
                confidence: currentConf * 100
            })
        });
        const data = await res.json();
        document.getElementById("typing").remove();
        chatBox.innerHTML += `<div class="message bot">${data.response}</div>`;
        chatBox.scrollTop = chatBox.scrollHeight;
    } catch (err) {
        document.getElementById("typing").remove();
        chatBox.innerHTML += `<div class="message bot">Error connecting to AI</div>`;
    }
}

async function predictFromBrowser() {
  if (!browserVideo || !browserCanvas) return;
  try {
    const ctx = browserCanvas.getContext('2d');
    ctx.drawImage(browserVideo, 0, 0, 640, 480);
    const base64 = browserCanvas.toDataURL('image/jpeg', 0.8);

    const res  = await fetch('/predict_frame', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ image: base64 })
    });
    const data = await res.json();

    if (data.emotion) {
      updateEmotion(data.emotion.toLowerCase(), data.confidence || 0);
    }
  } catch (e) {
    console.error('[predict_frame error]', e);
  }
}

/* ═══════════════════════════════════════════════════════════
   SERVER WEBCAM (Local mode)
   Polls /get_emotion every 2 seconds
═══════════════════════════════════════════════════════════ */
async function pollEmotion() {
  try {
    const res  = await fetch('/get_emotion');
    const data = await res.json();
    if (data && data.emotion) {
      updateEmotion(data.emotion.toLowerCase(), data.confidence || 0);
    }
  } catch (e) { /* silent */ }
}

/* ═══════════════════════════════════════════════════════════
   UPDATE UI WITH NEW EMOTION
═══════════════════════════════════════════════════════════ */
function updateEmotion(emotion, conf) {
  const cfg = EMOTIONS[emotion] || EMOTIONS.neutral;
  currentEmotion = emotion;
  currentConf    = conf;

  // Stat cards
  document.getElementById('stat-emotion').textContent = cfg.label;
  document.getElementById('stat-conf').textContent    = (conf * 100).toFixed(1) + '%';

  // Topbar chip
  document.getElementById('chip-emoji').textContent = cfg.emoji;
  document.getElementById('chip-label').textContent = cfg.label;

  // Overlays
  document.getElementById('overlay-emoji').textContent   = cfg.emoji;
  document.getElementById('overlay-emotion').textContent = cfg.label;
  document.getElementById('overlay-conf').textContent    = `Confidence: ${(conf * 100).toFixed(0)}%`;
  document.getElementById('cam-page-emoji').textContent   = cfg.emoji;
  document.getElementById('cam-page-emotion').textContent = cfg.label;
  document.getElementById('cam-page-conf').textContent    = `Confidence: ${(conf * 100).toFixed(0)}%`;

  // Confidence bars
  const pct = (conf * 100).toFixed(1) + '%';
  document.getElementById('conf-bar-fill').style.width = pct;
  document.getElementById('conf-bar-pct').textContent  = pct;
  document.getElementById('cam-conf-fill').style.width = pct;
  document.getElementById('cam-conf-pct').textContent  = pct;

  // Meter
  updateMeter(emotion, conf);

  // History tracking
  detectionCount++;
  document.getElementById('stat-detects').textContent = detectionCount;
  emotionCounts[emotion] = (emotionCounts[emotion] || 0) + 1;
  confHistory.push(+(conf * 100).toFixed(1));

  const recs = RECOMMENDATIONS[emotion] || RECOMMENDATIONS.neutral;
  historyData.unshift({
    emotion, conf,
    recommendation: recs[0],
    time: new Date().toLocaleTimeString()
  });
  if (historyData.length > 50) historyData.pop();

  renderRecs(emotion);

  // Fetch enrichment only when emotion changes
  if (emotion !== lastEnrichEmotion) {
    lastEnrichEmotion = emotion;
    fetchEnrichment(emotion, conf);
  }
}

/* ═══════════════════════════════════════════════════════════
   EMOTION METER
═══════════════════════════════════════════════════════════ */
function updateMeter(activeEmotion, conf) {
  const list = document.getElementById('meter-list');
  list.innerHTML = Object.entries(EMOTIONS).map(([key, cfg]) => {
    const pct = key === activeEmotion ? (conf * 100).toFixed(0) : 0;
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
updateMeter('neutral', 0);

/* ═══════════════════════════════════════════════════════════
   RECOMMENDATIONS
═══════════════════════════════════════════════════════════ */
function renderRecs(emotion) {
  const recs = RECOMMENDATIONS[emotion] || RECOMMENDATIONS.neutral;
  document.getElementById('rec-list').innerHTML = recs.map(r =>
    `<div class="rec-item"><div class="rec-dot"></div>${r}</div>`
  ).join('');
}
renderRecs('neutral');

const refreshRecsBtn = document.getElementById('refresh-recs-btn');
if (refreshRecsBtn) refreshRecsBtn.addEventListener('click', () => renderRecs(currentEmotion));

/* ═══════════════════════════════════════════════════════════
   ENRICHMENT API
═══════════════════════════════════════════════════════════ */
async function fetchEnrichment(emotion, conf) {
  const adviceEl = document.getElementById('ai-advice');
  adviceEl.textContent = 'Generating personalised advice…';
  adviceEl.classList.add('ai-loading');
  try {
    const res  = await fetch('/api/enrich', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ emotion, confidence: conf })
    });
    const data = await res.json();
    if (data.ai_advice) {
      adviceEl.textContent = data.ai_advice;
      adviceEl.classList.remove('ai-loading');
    }
    if (data.quote) {
      document.getElementById('quote-text').textContent   = `"${data.quote.quote}"`;
      document.getElementById('quote-author').textContent = `— ${data.quote.author}`;
    }
    if (data.videos && data.videos.length) renderVideos(data.videos);
  } catch (e) {
    adviceEl.textContent = 'AI advice unavailable.';
    adviceEl.classList.remove('ai-loading');
  }
}

const refreshQuoteBtn = document.getElementById('refresh-quote-btn');
if (refreshQuoteBtn) refreshQuoteBtn.addEventListener('click', async () => {
  try {
    const res  = await fetch('/api/enrich', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ emotion: currentEmotion, confidence: currentConf }) });
    const data = await res.json();
    if (data.quote) {
      document.getElementById('quote-text').textContent   = `"${data.quote.quote}"`;
      document.getElementById('quote-author').textContent = `— ${data.quote.author}`;
    }
  } catch (e) {}
});

const refreshVideosBtn = document.getElementById('refresh-videos-btn');
if (refreshVideosBtn) refreshVideosBtn.addEventListener('click', async () => {
  try {
    const res  = await fetch('/api/enrich', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ emotion: currentEmotion, confidence: currentConf }) });
    const data = await res.json();
    if (data.videos && data.videos.length) renderVideos(data.videos);
  } catch (e) {}
});

function renderVideos(videos) {
    const container = document.getElementById("video-container");

    container.innerHTML = "";

    videos.forEach(video => {
        container.innerHTML += `
            <iframe src="https://www.youtube.com/embed/${video.id}"
                frameborder="0"
                allowfullscreen>
            </iframe>
        `;
    });
}
/* ═══════════════════════════════════════════════════════════
   SAVE SESSION
═══════════════════════════════════════════════════════════ */
const saveBtn = document.getElementById('save-btn');
if (saveBtn) saveBtn.addEventListener('click', async () => {
  try {
    const res = await fetch('/save_session', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ emotion: currentEmotion, confidence: currentConf, session_time: sessionSeconds, detections: detectionCount })
    });
    if (res.ok) alert('✅ Session saved!');
    else        alert('⚠️ Save failed.');
  } catch (e) { alert('⚠️ Cannot connect to server.'); }
});

/* ═══════════════════════════════════════════════════════════
   HISTORY PAGE
═══════════════════════════════════════════════════════════ */
function renderHistory() {
  const recent = historyData.slice(0, 20).reverse();
  const labels = recent.map((_, i) => i + 1);
  const vals   = recent.map(d => (d.conf * 100).toFixed(1));
  const colors = recent.map(d => EMOTIONS[d.emotion]?.color || '#6c63ff');

  if (trendChart) trendChart.destroy();
  trendChart = new Chart(document.getElementById('trend-chart'), {
    type: 'line',
    data: { labels, datasets: [{ label: 'Confidence %', data: vals, borderColor: '#6c63ff', backgroundColor: 'rgba(108,99,255,.1)', pointBackgroundColor: colors, pointRadius: 5, tension: 0.4, fill: true }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { color: '#1f2330' }, ticks: { color: '#5a607a' } }, y: { grid: { color: '#1f2330' }, ticks: { color: '#5a607a' }, min: 0, max: 100 } } }
  });

  const tbody = document.getElementById('history-body');
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

/* ═══════════════════════════════════════════════════════════
   ANALYTICS PAGE
═══════════════════════════════════════════════════════════ */
function renderAnalytics() {
  const labels = Object.keys(emotionCounts).map(k => EMOTIONS[k]?.label || k);
  const vals   = Object.values(emotionCounts);
  const colors = Object.keys(emotionCounts).map(k => EMOTIONS[k]?.color || '#6c63ff');

  if (pieChart) pieChart.destroy();
  pieChart = new Chart(document.getElementById('pie-chart'), {
    type: 'doughnut',
    data: { labels, datasets: [{ data: vals, backgroundColor: colors, borderWidth: 2, borderColor: '#111318' }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { color: '#a0a8c0', font: { size: 12 } } } } }
  });

  if (barChart) barChart.destroy();
  barChart = new Chart(document.getElementById('bar-chart'), {
    type: 'bar',
    data: { labels, datasets: [{ label: 'Count', data: vals, backgroundColor: colors, borderRadius: 6, borderWidth: 0 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { color: '#5a607a' } }, y: { grid: { color: '#1f2330' }, ticks: { color: '#5a607a' }, beginAtZero: true } } }
  });

  if (confChart) confChart.destroy();
  confChart = new Chart(document.getElementById('conf-chart'), {
    type: 'line',
    data: { labels: confHistory.map((_, i) => i + 1), datasets: [{ label: 'Confidence %', data: confHistory, borderColor: '#ff6584', backgroundColor: 'rgba(255,101,132,.08)', tension: 0.4, fill: true, pointRadius: 3, pointBackgroundColor: '#ff6584' }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { color: '#1f2330' }, ticks: { color: '#5a607a', maxTicksLimit: 10 } }, y: { grid: { color: '#1f2330' }, ticks: { color: '#5a607a' }, min: 0, max: 100 } } }
  });
}

/* ═══════════════════════════════════════════════════════════
   STUDY TIPS PAGE
═══════════════════════════════════════════════════════════ */
function renderTips() {
  document.getElementById('tips-grid').innerHTML = Object.entries(EMOTIONS).map(([key, cfg]) => {
    const tips = RECOMMENDATIONS[key] || [];
    return `
      <div class="tip-card">
        <div class="tip-emotion-icon">${cfg.emoji}</div>
        <div class="tip-emotion-name" style="color:${cfg.color}">${cfg.label}</div>
        <ul class="tip-list">${tips.map(t => `<li>${t}</li>`).join('')}</ul>
      </div>`;
  }).join('');
}

/* ═══════════════════════════════════════════════════════════
   INIT
═══════════════════════════════════════════════════════════ */
(async function init() {
  // Load initial quote
  try {
    const res  = await fetch('/api/enrich', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ emotion: 'neutral', confidence: 0 }) });
    const data = await res.json();
    if (data.quote) {
      document.getElementById('quote-text').textContent   = `"${data.quote.quote}"`;
      document.getElementById('quote-author').textContent = `— ${data.quote.author}`;
    }
    if (data.videos && data.videos.length) renderVideos(data.videos);
  } catch (e) {}

  // Start camera based on mode
  if (IS_CLOUD) {
    console.log('[Mode] Cloud — using browser webcam');
    await startBrowserWebcam();
  } else {
    console.log('[Mode] Local — using server webcam');
    pollEmotion();
    setInterval(pollEmotion, 2000);
  }
})();