/* ============================================================
   CourseLens AI – frontend application
   ============================================================ */

'use strict';

// ── State ─────────────────────────────────────────────────────
const state = {
  quizQuestions: [],   // current quiz question objects
  userAnswers:   {},   // { "1": "B", "2": "D", … }
  quizHistory:   JSON.parse(localStorage.getItem('cl_quiz_history') || '[]'),
};

// ── Utilities ─────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const esc = s => String(s)
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;');

function saveQuizHistory() {
  localStorage.setItem('cl_quiz_history', JSON.stringify(state.quizHistory));
}

// ── Tab / Panel switching ──────────────────────────────────────
function switchPanel(name) {
  document.querySelectorAll('.cl-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.panel === name);
  });
  document.querySelectorAll('.cl-panel').forEach(p => {
    p.classList.toggle('d-none', p.id !== `panel-${name}`);
    if (p.id === `panel-${name}`) p.classList.add('active');
    else p.classList.remove('active');
  });
  if (name === 'analysis') renderAnalysisPage();
}

document.querySelectorAll('.cl-tab').forEach(tab => {
  tab.addEventListener('click', () => switchPanel(tab.dataset.panel));
});

// ── Document management ────────────────────────────────────────
async function loadDocuments() {
  const res  = await fetch('/api/documents');
  const data = await res.json();
  renderDocumentList(data.documents || []);
}

function renderDocumentList(docs) {
  const list = $('documentList');
  if (!docs.length) {
    list.innerHTML = '<p class="text-muted small text-center mt-2">No documents yet.</p>';
    return;
  }
  list.innerHTML = docs.map(name => `
    <div class="doc-item">
      <span class="doc-name" title="${esc(name)}">
        <i class="bi bi-file-earmark-text me-1 text-danger"></i>${esc(name)}
      </span>
      <button class="doc-delete" data-docname="${esc(name)}" title="Remove">
        <i class="bi bi-x-lg"></i>
      </button>
    </div>`).join('');

  list.querySelectorAll('.doc-delete').forEach(btn => {
    btn.addEventListener('click', () => deleteDocument(btn.dataset.docname));
  });
}

async function deleteDocument(filename) {
  if (!confirm(`Remove "${filename}" from your materials?`)) return;
  await fetch(`/api/documents/${encodeURIComponent(filename)}`, { method: 'DELETE' });
  loadDocuments();
}

// ── File upload ────────────────────────────────────────────────
const uploadZone = $('uploadZone');
const fileInput  = $('fileInput');

uploadZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
  if (fileInput.files.length) uploadFile(fileInput.files[0]);
});

uploadZone.addEventListener('dragover', e => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
});

async function uploadFile(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    alert('Only PDF files are supported.');
    return;
  }
  $('uploadProgress').classList.remove('d-none');
  uploadZone.style.pointerEvents = 'none';

  const form = new FormData();
  form.append('file', file);

  try {
    const res  = await fetch('/api/documents/upload', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) {
      alert(`Upload failed: ${data.detail || 'Unknown error'}`);
    } else {
      loadDocuments();
    }
  } catch (e) {
    alert('Upload failed. Is the server running?');
  } finally {
    $('uploadProgress').classList.add('d-none');
    uploadZone.style.pointerEvents = '';
    fileInput.value = '';
  }
}

// ── Q&A ───────────────────────────────────────────────────────
const chatMessages  = $('chatMessages');
const questionInput = $('questionInput');

$('askBtn').addEventListener('click', askQuestion);
questionInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); askQuestion(); }
});

function appendBubble(role, html) {
  const welcome = chatMessages.querySelector('.cl-welcome');
  if (welcome) welcome.remove();

  const wrap = document.createElement('div');
  wrap.className = `cl-bubble-wrap ${role}`;
  wrap.innerHTML = `<div class="cl-bubble">${html}</div>`;
  chatMessages.appendChild(wrap);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return wrap;
}

async function askQuestion() {
  const q = questionInput.value.trim();
  if (!q) return;
  questionInput.value = '';

  appendBubble('user', esc(q));

  const thinking = appendBubble('ai cl-thinking', '<i class="bi bi-three-dots"></i> Thinking…');

  try {
    const res  = await fetch('/api/qa/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q }),
    });
    const data = await res.json();
    thinking.remove();

    if (!res.ok) {
      appendBubble('ai', `<span class="text-danger"><i class="bi bi-exclamation-circle me-1"></i>${esc(data.detail || 'Error')}</span>`);
      return;
    }

    let html = esc(data.answer).replace(/\n/g, '<br>');

    if (data.sources && data.sources.length) {
      const chips = data.sources.map(s =>
        `<div class="cl-source-chip">
           <i class="bi bi-file-earmark-text me-1"></i>
           <strong>${esc(s.document)}</strong>, p.&nbsp;${esc(s.page)}
         </div>`
      ).join('');
      html += `<details class="cl-sources mt-2">
                 <summary><i class="bi bi-bookmarks me-1"></i>Sources (${data.sources.length})</summary>
                 <div class="mt-1">${chips}</div>
               </details>`;
    }

    appendBubble('ai', html);
  } catch (e) {
    thinking.remove();
    appendBubble('ai', '<span class="text-danger">Network error. Please try again.</span>');
  }
}

// ── Quiz ──────────────────────────────────────────────────────
$('generateQuizBtn').addEventListener('click', generateQuiz);

async function generateQuiz() {
  const topic = $('quizTopic').value.trim();
  const num   = parseInt($('numQuestions').value, 10);

  $('quizSetup').classList.add('d-none');
  $('quizLoading').classList.remove('d-none');
  $('quizQuestions').classList.add('d-none');
  $('quizResults').classList.add('d-none');

  try {
    const res  = await fetch('/api/quiz/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, num_questions: num }),
    });
    const data = await res.json();

    $('quizLoading').classList.add('d-none');
    $('quizSetup').classList.remove('d-none');

    if (!res.ok || !data.questions || !data.questions.length) {
      alert(data.detail || data.error || 'No questions generated. Upload course materials first.');
      return;
    }

    state.quizQuestions = data.questions;
    state.userAnswers   = {};
    renderQuizQuestions(data.questions);
  } catch (e) {
    $('quizLoading').classList.add('d-none');
    $('quizSetup').classList.remove('d-none');
    alert('Failed to generate quiz. Is the server running?');
  }
}

function renderQuizQuestions(questions) {
  const container = $('quizQuestions');
  container.innerHTML = questions.map((q, idx) => `
    <div class="quiz-question-card" id="qcard-${q.id}">
      <div class="fw-semibold mb-3">
        <span class="badge bg-primary me-2">${idx + 1}</span>${esc(q.question)}
      </div>
      ${q.options.map((opt, oi) => `
        <div class="quiz-option" id="opt-${q.id}-${oi}"
             onclick="selectOption(${q.id}, '${esc(opt.charAt(0))}', ${oi})">
          ${esc(opt)}
        </div>`).join('')}
    </div>`).join('');

  container.innerHTML += `
    <div class="text-end mt-2 mb-4">
      <button class="btn btn-success px-4" id="submitQuizBtn" onclick="submitQuiz()" disabled>
        <i class="bi bi-check2-circle me-1"></i>Submit Quiz
      </button>
    </div>`;

  container.classList.remove('d-none');
}

function selectOption(qId, letter, optIdx) {
  state.userAnswers[String(qId)] = letter;

  // Highlight selection
  const card = document.getElementById(`qcard-${qId}`);
  card.querySelectorAll('.quiz-option').forEach((el, i) => {
    el.classList.toggle('selected', i === optIdx);
  });

  // Enable submit when all answered
  const allAnswered = state.quizQuestions.every(q => state.userAnswers[String(q.id)]);
  const btn = $('submitQuizBtn');
  if (btn) btn.disabled = !allAnswered;
}

async function submitQuiz() {
  const res  = await fetch('/api/quiz/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      questions: state.quizQuestions,
      answers:   state.userAnswers,
    }),
  });
  const data = await res.json();

  if (!res.ok) { alert(data.detail || 'Submission failed.'); return; }

  // Mark answers in the UI
  state.quizQuestions.forEach(q => {
    const correctLetter = q.correct_answer.toUpperCase();
    const userLetter    = (state.userAnswers[String(q.id)] || '').toUpperCase();
    q.options.forEach((opt, oi) => {
      const el     = document.getElementById(`opt-${q.id}-${oi}`);
      const letter = opt.charAt(0).toUpperCase();
      el.classList.remove('selected');
      if (letter === correctLetter) el.classList.add('correct');
      else if (letter === userLetter) el.classList.add('wrong');
    });
  });

  const submitBtn = $('submitQuizBtn');
  if (submitBtn) submitBtn.disabled = true;

  renderQuizResults(data);

  // Persist to history for analysis
  state.quizHistory.push({
    timestamp: new Date().toISOString(),
    overall_score: data.overall_score,
    topic_breakdown: data.topic_breakdown,
  });
  saveQuizHistory();
}

function renderQuizResults(data) {
  const pct   = data.overall_score;
  const color = pct >= 70 ? '#4caf50' : pct >= 50 ? '#ff9800' : '#f44336';

  const breakdown = (data.topic_breakdown || []).map(t => `
    <div class="mb-2">
      <div class="d-flex justify-content-between small">
        <span>${esc(t.topic)}</span>
        <span>${t.questions_correct}/${t.questions_attempted} (${t.score_percentage}%)</span>
      </div>
      <div class="weak-area-bar">
        <div class="weak-area-fill ${t.score_percentage >= 70 ? 'severity-strong' : t.score_percentage >= 50 ? 'severity-medium' : 'severity-high'}"
             style="width:${t.score_percentage}%"></div>
      </div>
    </div>`).join('');

  $('quizResults').innerHTML = `
    <div class="card shadow-sm mb-4">
      <div class="card-body text-center">
        <div class="score-circle" style="background:${color}">
          ${Math.round(pct)}%<span class="score-label">SCORE</span>
        </div>
        <h5 class="mt-2">${data.total_correct} / ${data.total_questions} correct</h5>
        ${breakdown ? `<hr><h6 class="text-start">By Topic</h6><div class="text-start">${breakdown}</div>` : ''}
        <div class="mt-3">
          <button class="btn btn-outline-primary me-2" onclick="retakeQuiz()">
            <i class="bi bi-arrow-repeat me-1"></i>New Quiz
          </button>
          <button class="btn btn-outline-secondary" onclick="switchPanel('analysis')">
            <i class="bi bi-bar-chart me-1"></i>View Analysis
          </button>
        </div>
      </div>
    </div>`;
  $('quizResults').classList.remove('d-none');
}

function retakeQuiz() {
  $('quizQuestions').classList.add('d-none');
  $('quizResults').classList.add('d-none');
  $('quizQuestions').innerHTML = '';
  $('quizResults').innerHTML = '';
  state.quizQuestions = [];
  state.userAnswers   = {};
}

// ── Analysis ──────────────────────────────────────────────────
async function renderAnalysisPage() {
  if (!state.quizHistory.length) {
    $('analysisEmpty').classList.remove('d-none');
    $('analysisContent').classList.add('d-none');
    return;
  }

  $('analysisEmpty').classList.add('d-none');
  $('analysisContent').innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="mt-2 text-muted">Analysing your performance…</p></div>';
  $('analysisContent').classList.remove('d-none');

  try {
    const res  = await fetch('/api/analysis/weak-areas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quiz_history: state.quizHistory }),
    });
    const data = await res.json();

    if (!res.ok) {
      $('analysisContent').innerHTML = `<div class="alert alert-danger">${esc(data.detail || 'Analysis failed.')}</div>`;
      return;
    }

    renderAnalysis(data);
  } catch (e) {
    $('analysisContent').innerHTML = '<div class="alert alert-danger">Network error.</div>';
  }
}

// Allowed severity values (used as CSS class suffixes – must be whitelisted).
const SEVERITY_CLASSES = new Set(['high', 'medium', 'low', 'strong']);
function safeSeverity(s) {
  return SEVERITY_CLASSES.has(s) ? s : 'medium';
}

function renderAnalysis(data) {
  const overallColor = data.overall_score >= 70 ? '#4caf50' : data.overall_score >= 50 ? '#ff9800' : '#f44336';

  const weakCards = (data.weak_areas || []).map(w => {
    const sev = safeSeverity(w.severity);
    const badgeClass = sev === 'high' ? 'danger' : sev === 'medium' ? 'warning text-dark' : 'info';
    return `
    <div class="card mb-3 border-0 shadow-sm">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start mb-1">
          <h6 class="mb-0">${esc(w.topic)}</h6>
          <span class="badge bg-${badgeClass}">${esc(sev)}</span>
        </div>
        <div class="text-muted small mb-1">${w.questions_correct}/${w.questions_attempted} correct (${w.score_percentage}%)</div>
        <div class="weak-area-bar mb-2">
          <div class="weak-area-fill severity-${sev}" style="width:${w.score_percentage}%"></div>
        </div>
        ${w.recommendation ? `<div class="small text-muted"><i class="bi bi-lightbulb me-1 text-warning"></i>${esc(w.recommendation)}</div>` : ''}
      </div>
    </div>`;
  }).join('') || '<p class="text-muted">No weak areas detected — great job!</p>';

  const strongCards = (data.strong_areas || []).map(s => `
    <div class="d-flex justify-content-between align-items-center mb-2 small">
      <span><i class="bi bi-check-circle-fill text-success me-1"></i>${esc(s.topic)}</span>
      <span class="text-muted">${s.score_percentage}%</span>
    </div>`).join('');

  $('analysisContent').innerHTML = `
    <div class="row g-4">
      <div class="col-12">
        <div class="card border-0 shadow-sm">
          <div class="card-body text-center">
            <div class="score-circle mx-auto mb-2" style="background:${overallColor}">
              ${Math.round(data.overall_score)}%<span class="score-label">OVERALL</span>
            </div>
            ${data.study_plan ? `<p class="text-muted small mt-2 mb-0"><i class="bi bi-journal-bookmark me-1"></i>${esc(data.study_plan)}</p>` : ''}
          </div>
        </div>
      </div>

      <div class="col-md-7">
        <h6 class="fw-semibold mb-3"><i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>Weak Areas</h6>
        ${weakCards}
      </div>

      ${strongCards ? `
      <div class="col-md-5">
        <h6 class="fw-semibold mb-3"><i class="bi bi-trophy-fill text-success me-2"></i>Strong Areas</h6>
        ${strongCards}
      </div>` : ''}

      <div class="col-12 text-end pb-4">
        <button class="btn btn-sm btn-outline-danger" onclick="clearHistory()">
          <i class="bi bi-trash me-1"></i>Clear History
        </button>
      </div>
    </div>`;
}

function clearHistory() {
  if (!confirm('Clear all quiz history?')) return;
  state.quizHistory = [];
  saveQuizHistory();
  $('analysisEmpty').classList.remove('d-none');
  $('analysisContent').classList.add('d-none');
}

// ── Boot ──────────────────────────────────────────────────────
loadDocuments();
