
let currentEmotion    = 'neutral';
let currentConf       = 0;
let detectionCount    = 0;
let sessionSeconds    = 0;
let historyData       = [];
let emotionCounts     = { happy:0, sad:0, neutral:0, angry:0, surprise:0, disgust:0, fear:0 };
let confHistory       = [];
let lastEnrichEmotion = '';
let trendChart, pieChart, barChart, confChart;

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
  happy: [
    'Attempt difficult problems now — you\'re in peak state.',
    'Start a challenging new topic.',
    'Use this energy for deep focused work.',
    'Set ambitious goals for this session.'
  ],
  sad: [
    'Revise an easy, familiar topic first.',
    'Watch a short concept explanation video.',
    'Take a 5-minute mindful break.',
    'Be gentle — light revision is perfectly fine.'
  ],
  neutral: [
    'Continue your planned study session.',
    'Revise class notes steadily.',
    'Solve moderate-level practice questions.',
    'Try Pomodoro: 25 min study, 5 min break.'
  ],
  angry: [
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
  disgust: [
    'Switch subjects or study method now.',
    'Try interactive or visual learning instead.',
    'Change your environment — fresh start.',
    'Short, varied tasks work best here.'
  ],
  fear: [
    'Break the task into very small steps.',
    'Start with something you already know well.',
    'Progress over perfection — every bit counts.',
    'Breathe slowly, then resume gently.'
  ]
};

const PAGE_TITLES = {
  dashboard: 'Dashboard',
  camera:    'Live Camera',
  history:   'Mood History',
  analytics: 'Analytics',
  tips:      'Study Tips'
};


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

document.getElementById('goto-camera').addEventListener('click', () => navigate('camera'));


setInterval(() => {
  sessionSeconds++;
  const m = String(Math.floor(sessionSeconds / 60)).padStart(2, '0');
  const s = String(sessionSeconds % 60).padStart(2, '0');
  document.getElementById('stat-time').textContent = `${m}:${s}`;
}, 1000);


async function pollEmotion() {
  try {
    const res  = await fetch('/get_emotion');
    const data = await res.json();
    if (data && data.emotion) {
      updateEmotion(data.emotion.toLowerCase(), data.confidence || 0);
    }
  } catch (e) {
    /* silent fail — server may not be ready */
  }
}

function updateEmotion(emotion, conf) {
  const cfg = EMOTIONS[emotion] || EMOTIONS.neutral;
  currentEmotion = emotion;
  currentConf    = conf;

  /* Stat cards */
  document.getElementById('stat-emotion').textContent = cfg.label;
  document.getElementById('stat-conf').textContent    = (conf * 100).toFixed(1) + '%';

  /* Topbar chip */
  document.getElementById('chip-emoji').textContent = cfg.emoji;
  document.getElementById('chip-label').textContent = cfg.label;

  /* Dashboard overlay */
  document.getElementById('overlay-emoji').textContent   = cfg.emoji;
  document.getElementById('overlay-emotion').textContent = cfg.label;
  document.getElementById('overlay-conf').textContent    = `Confidence: ${(conf * 100).toFixed(0)}%`;

  /* Camera page overlay */
  document.getElementById('cam-page-emoji').textContent   = cfg.emoji;
  document.getElementById('cam-page-emotion').textContent = cfg.label;
  document.getElementById('cam-page-conf').textContent    = `Confidence: ${(conf * 100).toFixed(0)}%`;

  /* Confidence bars */
  const pct = (conf * 100).toFixed(1) + '%';
  document.getElementById('conf-bar-fill').style.width = pct;
  document.getElementById('conf-bar-pct').textContent  = pct;
  document.getElementById('cam-conf-fill').style.width = pct;
  document.getElementById('cam-conf-pct').textContent  = pct;

  /* Emotion meter */
  updateMeter(emotion, conf);

  /* History tracking */
  detectionCount++;
  document.getElementById('stat-detects').textContent = detectionCount;
  emotionCounts[emotion] = (emotionCounts[emotion] || 0) + 1;
  confHistory.push(+(conf * 100).toFixed(1));

  const recs = RECOMMENDATIONS[emotion] || RECOMMENDATIONS.neutral;
  historyData.unshift({
    emotion,
    conf,
    recommendation: recs[0],
    time: new Date().toLocaleTimeString()
  });
  if (historyData.length > 50) historyData.pop();

  
  renderRecs(emotion);

  if (emotion !== lastEnrichEmotion) {
    lastEnrichEmotion = emotion;
    fetchEnrichment(emotion, conf);
  }
}


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


function renderRecs(emotion) {
  const recs = RECOMMENDATIONS[emotion] || RECOMMENDATIONS.neutral;
  document.getElementById('rec-list').innerHTML = recs.map(r =>
    `<div class="rec-item"><div class="rec-dot"></div>${r}</div>`
  ).join('');
}

renderRecs('neutral');

document.getElementById('refresh-recs-btn').addEventListener('click', () => {
  renderRecs(currentEmotion);
});


async function fetchEnrichment(emotion, conf) {
  /* Show loading states */
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

    /* AI Advice */
    if (data.ai_advice) {
      adviceEl.textContent = data.ai_advice;
      adviceEl.classList.remove('ai-loading');
    }

    /* Quote */
    if (data.quote) {
      document.getElementById('quote-text').textContent   = `"${data.quote.quote}"`;
      document.getElementById('quote-author').textContent = `— ${data.quote.author}`;
    }

    /* Videos */
    if (data.videos && data.videos.length) {
      renderVideos(data.videos);
    }

  } catch (e) {
    adviceEl.textContent = 'AI advice unavailable — check your API key.';
    adviceEl.classList.remove('ai-loading');
  }
}


document.getElementById('refresh-quote-btn').addEventListener('click', async () => {
  try {
    const res  = await fetch('/api/enrich', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ emotion: currentEmotion, confidence: currentConf })
    });
    const data = await res.json();
    if (data.quote) {
      document.getElementById('quote-text').textContent   = `"${data.quote.quote}"`;
      document.getElementById('quote-author').textContent = `— ${data.quote.author}`;
    }
  } catch (e) { /* silent */ }
});

document.getElementById('refresh-videos-btn').addEventListener('click', async () => {
  try {
    const res  = await fetch('/api/enrich', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ emotion: currentEmotion, confidence: currentConf })
    });
    const data = await res.json();
    if (data.videos && data.videos.length) renderVideos(data.videos);
  } catch (e) { /* silent */ }
});


function renderVideos(videos) {
  const grid = document.getElementById('video-grid');
  grid.innerHTML = videos.map(v => `
    <a class="video-thumb" href="${v.url}" target="_blank" rel="noopener noreferrer">
      <img src="${v.thumbnail}" alt="${v.title}" loading="lazy"
           onerror="this.style.display='none'"/>
      <div class="video-thumb-title">${v.title}</div>
    </a>`).join('');
}


document.getElementById('save-btn').addEventListener('click', async () => {
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
    if (res.ok) {
      alert('✅ Session saved successfully!');
    } else {
      alert('⚠️ Save failed. Check Flask server.');
    }
  } catch (e) {
    alert('⚠️ Could not connect to server.');
  }
});


function renderHistory() {
  /* Trend line chart */
  const recent = historyData.slice(0, 20).reverse();
  const labels = recent.map((_, i) => i + 1);
  const vals   = recent.map(d => (d.conf * 100).toFixed(1));
  const colors = recent.map(d => EMOTIONS[d.emotion]?.color || '#6c63ff');

  if (trendChart) trendChart.destroy();
  trendChart = new Chart(document.getElementById('trend-chart'), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label:            'Confidence %',
        data:             vals,
        borderColor:      '#6c63ff',
        backgroundColor:  'rgba(108,99,255,.1)',
        pointBackgroundColor: colors,
        pointRadius:      5,
        tension:          0.4,
        fill:             true
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

 
  const tbody = document.getElementById('history-body');
  if (!historyData.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="no-data-cell">No history yet.</td></tr>';
    return;
  }
  tbody.innerHTML = historyData.slice(0, 20).map((d, i) => {
    const cfg = EMOTIONS[d.emotion] || EMOTIONS.neutral;
    return `<tr>
      <td style="color:var(--muted)">${i + 1}</td>
      <td>
        <span class="emotion-tag"
              style="background:${cfg.color}22;color:${cfg.color}">
          ${cfg.emoji} ${cfg.label}
        </span>
      </td>
      <td>${(d.conf * 100).toFixed(1)}%</td>
      <td style="color:var(--muted);font-size:12px">${d.recommendation}</td>
      <td style="color:var(--muted)">${d.time}</td>
    </tr>`;
  }).join('');
}


function renderAnalytics() {
  const labels = Object.keys(emotionCounts).map(k => EMOTIONS[k]?.label || k);
  const vals   = Object.values(emotionCounts);
  const colors = Object.keys(emotionCounts).map(k => EMOTIONS[k]?.color || '#6c63ff');

  /* Doughnut */
  if (pieChart) pieChart.destroy();
  pieChart = new Chart(document.getElementById('pie-chart'), {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data: vals, backgroundColor: colors, borderWidth: 2, borderColor: '#111318' }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'right', labels: { color: '#a0a8c0', font: { size: 12 } } } }
    }
  });

  if (barChart) barChart.destroy();
  barChart = new Chart(document.getElementById('bar-chart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Count', data: vals,
        backgroundColor: colors, borderRadius: 6, borderWidth: 0
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#5a607a' } },
        y: { grid: { color: '#1f2330' }, ticks: { color: '#5a607a' }, beginAtZero: true }
      }
    }
  });

  
  if (confChart) confChart.destroy();
  confChart = new Chart(document.getElementById('conf-chart'), {
    type: 'line',
    data: {
      labels: confHistory.map((_, i) => i + 1),
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


function renderTips() {
  document.getElementById('tips-grid').innerHTML = Object.entries(EMOTIONS).map(([key, cfg]) => {
    const tips = RECOMMENDATIONS[key] || [];
    return `
      <div class="tip-card">
        <div class="tip-emotion-icon">${cfg.emoji}</div>
        <div class="tip-emotion-name" style="color:${cfg.color}">${cfg.label}</div>
        <ul class="tip-list">
          ${tips.map(t => `<li>${t}</li>`).join('')}
        </ul>
      </div>`;
  }).join('');
}


(async function init() {
  /* Load initial quote */
  try {
    const res  = await fetch('/api/enrich', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ emotion: 'neutral', confidence: 0 })
    });
    const data = await res.json();
    if (data.quote) {
      document.getElementById('quote-text').textContent   = `"${data.quote.quote}"`;
      document.getElementById('quote-author').textContent = `— ${data.quote.author}`;
    }
  } catch (e) { /* silent */ }

 
  pollEmotion();
  setInterval(pollEmotion, 2000);
})();