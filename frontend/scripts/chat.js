/* ============================
   PromptX Chat Page — JavaScript
   ============================ */

// API URL - dynamically determined for production compatibility
if (typeof window.API_BASE === 'undefined') {
  window.API_BASE = (function() {
    const loc = window.location;
    if (loc.hostname === 'localhost' || loc.hostname === '127.0.0.1') {
      return 'http://127.0.0.1:8000/api/v1';
    }
    return `${loc.protocol}//${loc.host}/api/v1`;
  })();
}
const API_BASE = window.API_BASE;

console.log('=== API Configuration ===');
console.log('API_BASE:', API_BASE);
console.log('Current location:', window.location.href);

let currentMode = 'enhance';
let selectedModel = 'auto';
let currentChatId = null;
let chatSessions = [];

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
  console.log('=== PromptX Chat Initializing ===');
  
  try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(e) {}
  
  loadChatSessions();
  setupSidebar();
  setupModes();
  setupModelSelector();
  setupChatInput();
  
  // Restore API key
  const apiInput = document.getElementById('api-key-input');
  if (apiInput) {
    apiInput.value = localStorage.getItem('promptx_api_key') || '';
    apiInput.addEventListener('input', (e) => localStorage.setItem('promptx_api_key', e.target.value));
  }
  
  // Setup welcome cards immediately
  console.log('Setting up welcome cards on page load...');
  setupWelcomeCards();
  
  // Restore last active chat on refresh
  restoreLastChat();
  
  // Initial render check for diagrams
  renderAllD2();
  
  console.log('=== Initialization Complete ===');
});

// ===== SIDEBAR =====
function setupSidebar() {
  const sidebar = document.getElementById('chat-sidebar');
  const toggle = document.getElementById('sidebar-toggle');
  const closeBtn = document.getElementById('sidebar-close');
  const newChatBtn = document.getElementById('new-chat-btn');
  const clearHistoryBtn = document.getElementById('clear-history-btn');
  
  toggle.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
  });
  
  closeBtn.addEventListener('click', () => {
    sidebar.classList.add('collapsed');
  });
  
  newChatBtn.addEventListener('click', () => {
    startNewChat();
  });
  
  // Clear history button
  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      console.log('Clear button clicked');
      if (confirm('Clear all chat history? This cannot be undone.')) {
        // Clear all data
        chatSessions = [];
        currentChatId = null;
        localStorage.removeItem('promptx_sessions');
        localStorage.removeItem('promptx_current_chat');
        
        // Update UI
        renderHistory();
        startNewChat();
        showToast('History Cleared', 'All chat sessions have been deleted', 'success');
      }
    });
    console.log('Clear history button listener attached');
  } else {
    console.warn('Clear history button not found - ID: clear-history-btn');
  }
  
  // Check localStorage for sidebar state
  const sidebarState = localStorage.getItem('sidebarCollapsed');
  if (sidebarState === 'true') {
    sidebar.classList.add('collapsed');
  }
  
  // Save sidebar state on toggle
  const observer = new MutationObserver(() => {
    localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
  });
  observer.observe(sidebar, { attributes: true, attributeFilter: ['class'] });
}

// ===== MODES =====
function setupModes() {
  const modeItems = document.querySelectorAll('.mode-item');
  modeItems.forEach(item => {
    item.addEventListener('click', () => {
      modeItems.forEach(m => m.classList.remove('active'));
      item.classList.add('active');
      currentMode = item.getAttribute('data-mode');
      updateModeDisplay();
    });
  });
}

function updateModeDisplay() {
  const modeLabels = {
    enhance: 'Enhance Mode',
    analyze: 'Analyze Mode',
    compare: 'Compare Mode'
  };
  const label = modeLabels[currentMode] || 'Enhance Mode';
  
  document.getElementById('topbar-mode').textContent = label;
  document.getElementById('mode-indicator').textContent = label;
}

// ===== MODEL SELECTOR =====
function setupModelSelector() {
  const modelBtns = document.querySelectorAll('.model-option');
  const dropdown = document.getElementById('model-dropdown');
  const badge = document.getElementById('topbar-model-badge');

  const modelLabels = {
    auto: 'Auto',
    gemini_flash: 'Gemini 2.0 Flash',
    gemini_flash_8b: 'Gemini 2.0 Flash Lite',
    gemini_pro: 'Gemini 2.5 Pro',
    nvidia_minimax: 'NVIDIA Minimax',
    groq: 'Groq'
  };
  
  // Handle dropdown change
  if (dropdown) {
    dropdown.addEventListener('change', (e) => {
      selectedModel = e.target.value;
      console.log('=== MODEL CHANGED ===');
      console.log('Selected model:', selectedModel);
      
      if (badge) badge.textContent = modelLabels[selectedModel] || selectedModel;
      
      showToast('Model changed', `Now using ${modelLabels[selectedModel]}`, 'success');
    });
    
    // Set initial value
    selectedModel = dropdown.value || 'auto';
    console.log('=== INITIAL MODEL ===');
    console.log('Initial model:', selectedModel);
  }
  
  // Handle button clicks (if buttons exist)
  modelBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      modelBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedModel = btn.getAttribute('data-model');
      
      if (badge) badge.textContent = modelLabels[selectedModel] || selectedModel;
      
      showToast('Model changed', `Now using ${btn.textContent.trim()}`, 'success');
    });
  });
}

// ===== WELCOME CARDS & EXAMPLES =====
function setupWelcomeCards() {
  console.log('=== setupWelcomeCards called ===');
  
  const cards = document.querySelectorAll('.welcome-card');
  console.log(`Found ${cards.length} welcome cards`);
  
  if (cards.length === 0) {
    console.error('No welcome cards found! Check if welcome-screen exists in DOM');
    const welcomeScreen = document.getElementById('welcome-screen');
    console.log('Welcome screen element:', welcomeScreen);
    return;
  }
  
  cards.forEach((card, index) => {
    console.log(`Setting up card ${index}:`, card);
    
    card.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      console.log(`=== Card ${index} CLICKED ===`);
      
      const action = this.getAttribute('data-action');
      console.log(`Action: ${action}`);
      
      // Switch mode
      document.querySelectorAll('.mode-item').forEach(m => {
        m.classList.remove('active');
        if (m.getAttribute('data-mode') === action) {
          m.classList.add('active');
          console.log(`Activated mode: ${action}`);
        }
      });
      currentMode = action;
      updateModeDisplay();
      
      // Focus input but DON'T hide welcome screen
      const input = document.getElementById('chat-input');
      if (input) {
        console.log('Focusing input...');
        input.focus();
        setTimeout(() => {
          input.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
      } else {
        console.error('Chat input not found!');
      }
    });
  });
  
  // Setup example chips
  const chips = document.querySelectorAll('.example-chip');
  console.log(`Found ${chips.length} example chips`);
  
  chips.forEach((chip, index) => {
    chip.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      console.log(`=== Chip ${index} CLICKED ===`);
      const text = this.textContent.trim();
      console.log(`Text: ${text}`);
      fillPrompt(text);
    });
  });
  
  console.log('=== setupWelcomeCards complete ===');
}

function fillPrompt(text) {
  console.log('=== fillPrompt called ===');
  console.log('Text:', text);
  
  const input = document.getElementById('chat-input');
  if (!input) {
    console.error('Chat input not found!');
    return;
  }
  
  console.log('Setting input value...');
  input.value = text;
  input.dispatchEvent(new Event('input'));
  input.focus();
  
  console.log('Input value set to:', input.value);
  
  // Scroll to input
  setTimeout(() => {
    input.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 100);
}

// Make fillPrompt globally accessible for inline onclick handlers
window.fillPrompt = fillPrompt;
console.log('fillPrompt attached to window');

// ===== CHAT INPUT =====
function setupChatInput() {
  console.log('=== setupChatInput called ===');
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const charCount = document.getElementById('char-count');
  
  console.log('Input:', input);
  console.log('Send button:', sendBtn);
  
  if (!input || !sendBtn) {
    console.error('Chat input or send button not found');
    return;
  }
  
  console.log('Adding input listeners...');
  
  input.addEventListener('input', () => {
    sendBtn.disabled = !input.value.trim();
    
    // Auto-resize textarea
    input.style.height = 'auto';
    const newHeight = Math.min(Math.max(input.scrollHeight, 44), 120);
    input.style.height = newHeight + 'px';
    
    if (charCount) charCount.textContent = `${input.value.length} chars`;
  });
  
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.value.trim()) handleSend();
    }
  });
  
  sendBtn.addEventListener('click', handleSend);
  
  console.log('setupChatInput complete');
}

async function handleSend() {
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;
  
  // Start new session if needed
  if (!currentChatId) {
    currentChatId = Date.now().toString();
    chatSessions.unshift({
      id: currentChatId,
      title: message.substring(0, 50),
      messages: [],
      mode: currentMode,
      timestamp: Date.now()
    });
  }
  
  hideWelcome();
  addUserMessage(message);
  saveMsgToSession('user', message);
  
  input.value = '';
  input.style.height = 'auto';
  document.getElementById('send-btn').disabled = true;
  document.getElementById('char-count').textContent = '0 chars';
  
  if (currentMode === 'enhance') await handleEnhance(message);
  else if (currentMode === 'analyze') await handleAnalyze(message);
  else if (currentMode === 'compare') await handleCompare(message);
  
  saveChatSessions();
  renderHistory();
}

function hideWelcome() {
  const el = document.getElementById('welcome-screen');
  if (el) el.remove();
}

// ===== CHAT SESSIONS =====
function loadChatSessions() {
  try { chatSessions = JSON.parse(localStorage.getItem('promptx_sessions') || '[]'); } catch(e) { chatSessions = []; }
  renderHistory();
}

function saveChatSessions() {
  if (chatSessions.length > 30) chatSessions.length = 30;
  localStorage.setItem('promptx_sessions', JSON.stringify(chatSessions));
  // Save current chat ID for restoration on refresh
  if (currentChatId) {
    localStorage.setItem('promptx_current_chat', currentChatId);
  }
}

function restoreLastChat() {
  console.log('=== restoreLastChat called ===');
  const lastChatId = localStorage.getItem('promptx_current_chat');
  console.log('Last chat ID:', lastChatId);
  console.log('Chat sessions:', chatSessions.length);
  
  // Only restore if there's a valid saved chat with messages
  if (lastChatId && chatSessions.length > 0) {
    const session = chatSessions.find(s => s.id === lastChatId);
    console.log('Found session:', session);
    
    if (session && session.messages && session.messages.length > 0) {
      console.log('Loading session with', session.messages.length, 'messages');
      loadSession(lastChatId);
      return;
    }
  }
  
  // Otherwise, ensure welcome screen is visible and functional
  console.log('No valid session, showing welcome screen');
  const welcomeScreen = document.getElementById('welcome-screen');
  if (welcomeScreen) {
    console.log('Welcome screen found, already set up');
  } else {
    console.error('Welcome screen NOT found in DOM!');
  }
}

function saveMsgToSession(role, content) {
  const session = chatSessions.find(s => s.id === currentChatId);
  if (session) {
    session.messages.push({ role, content, timestamp: Date.now() });
  }
}

function renderHistory() {
  const list = document.getElementById('history-list');
  const empty = document.getElementById('history-empty');
  
  // Clear old items
  list.querySelectorAll('.history-item').forEach(el => el.remove());
  
  if (chatSessions.length === 0) {
    empty.style.display = 'block';
    return;
  }
  
  empty.style.display = 'none';
  
  chatSessions.forEach(session => {
    const btn = document.createElement('button');
    btn.className = `history-item${session.id === currentChatId ? ' active' : ''}`;
    btn.innerHTML = `<span class="history-icon">&gt;</span><span class="history-text">${escapeHtml(session.title)}</span>`;
    btn.addEventListener('click', () => loadSession(session.id));
    list.appendChild(btn);
  });
}

function loadSession(sessionId) {
  const session = chatSessions.find(s => s.id === sessionId);
  if (!session) return;
  
  currentChatId = sessionId;
  currentMode = session.mode || 'enhance';
  
  // Update mode UI
  document.querySelectorAll('.mode-item').forEach(m => {
    m.classList.remove('active');
    if (m.getAttribute('data-mode') === currentMode) m.classList.add('active');
  });
  updateModeDisplay();
  
  // Rebuild messages
  const container = document.getElementById('chat-messages');
  container.innerHTML = '';
  
  session.messages.forEach(msg => {
    if (msg.role === 'user') addUserMessage(msg.content);
    else addAssistantMessage(msg.content);
  });
  
  renderHistory();
}

function startNewChat() {
  currentChatId = null;
  localStorage.removeItem('promptx_current_chat'); // Clear saved chat ID
  const container = document.getElementById('chat-messages');
  container.innerHTML = `
    <div class="welcome-screen" id="welcome-screen">
      <img src="Public/bot-img.png" alt="PromptX" class="welcome-logo">
      <h1>PromptX</h1>
      <p>Pick a mode below, type your prompt, and hit send.</p>
      <div class="welcome-cards">
        <button class="welcome-card" data-action="enhance">
          <div class="wc-icon">✦</div>
          <div class="wc-text"><strong>Enhance Prompt</strong><span>Rewrite it to be clearer and more detailed</span></div>
        </button>
        <button class="welcome-card" data-action="analyze">
          <div class="wc-icon">◈</div>
          <div class="wc-text"><strong>Analyze Quality</strong><span>Get a score and tips to improve it</span></div>
        </button>
        <button class="welcome-card" data-action="compare">
          <div class="wc-icon">⇄</div>
          <div class="wc-text"><strong>Compare Versions</strong><span>See 3 different rewrites side by side</span></div>
        </button>
      </div>
      <div class="welcome-examples">
        <div class="examples-label">Try an example:</div>
        <button class="example-chip" onclick="fillPrompt('Write a blog post about artificial intelligence')">Write a blog about AI</button>
        <button class="example-chip" onclick="fillPrompt('Create a Python function to sort a list of dictionaries by key')">Sort list of dicts in Python</button>
        <button class="example-chip" onclick="fillPrompt('Design a marketing strategy for a SaaS product launch')">SaaS marketing strategy</button>
      </div>
    </div>
  `;
  setupWelcomeCards();
  renderHistory();
}

// ===== MESSAGE RENDERING =====
function addUserMessage(text) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'message user';

  // Render URLs as clickable link previews inside the user bubble
  const urls = extractUrls(text);
  let displayHtml = escapeHtml(text);
  urls.forEach(url => {
    const domain = getDomain(url);
    const favicon = getFaviconUrl(url);
    const chip = `<a href="${escapeHtml(url)}" target="_blank" rel="noopener" class="url-inline-chip">` +
      (favicon ? `<img src="${favicon}" width="14" height="14" style="border-radius:2px;flex-shrink:0;" onerror="this.style.display='none'">` : '🌐') +
      `<span>${escapeHtml(domain)}</span><span style="opacity:0.5;font-size:0.65rem;">↗</span></a>`;
    displayHtml = displayHtml.replace(escapeHtml(url), chip);
  });

  div.innerHTML = `
    <div class="message-content">${displayHtml}</div>
    <div class="message-avatar">U</div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function addAssistantMessage(content) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'message assistant';
  div.innerHTML = `
    <div class="message-avatar"><img src="Public/bot-img.png" alt="AI" style="width:100%;height:100%;object-fit:cover;border-radius:10px;"></div>
    <div class="message-content">${content}</div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(e) {}
  return div;
}

// ===== URL DETECTION =====
const URL_REGEX = /https?:\/\/[^\s<>"']+|www\.[^\s<>"']+/gi;

function addLoadingMessage() {
  return addAssistantMessage(`
    <div class="typing-dots">
      <span></span><span></span><span></span>
    </div>
  `);
}

function extractUrls(text) {
  const matches = text.match(URL_REGEX) || [];
  return matches.map(u => u.startsWith('http') ? u : `https://${u}`);
}

function getDomain(url) {
  try { return new URL(url).hostname.replace('www.', ''); } catch { return url; }
}

function getFaviconUrl(url) {
  try {
    const origin = new URL(url).origin;
    return `https://www.google.com/s2/favicons?domain=${origin}&sz=32`;
  } catch { return null; }
}

// ===== THINKING PROGRESS UI =====
function addThinkingMessage(steps, previewText = '') {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  const uniqueId = `thinking-${Date.now()}`;
  div.className = 'message assistant thinking-msg';
  div.innerHTML = `
    <div class="message-avatar" style="background:var(--bg-card);border:1px solid rgba(255,255,255,0.3);display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(255,255,255,0.15);">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"></path>
        <path d="M8.5 8.5v.01"></path>
        <path d="M15.5 8.5v.01"></path>
        <path d="M12 12v.01"></path>
      </svg>
    </div>
    <div class="message-content thinking-content">
      <details class="thinking-details" open>
        <summary class="thinking-header">
          <div class="thinking-spinner"></div>
          <span class="thinking-title" id="${uniqueId}-title">Analyzing...</span>
          <span class="thinking-toggle-icon">▾</span>
        </summary>
        <div class="thinking-steps" id="${uniqueId}-steps">
          ${steps.map((s, i) => `
            <div class="thinking-step" data-step="${i}">
              <span class="step-icon">○</span>
              <span class="step-text">${s}</span>
            </div>
          `).join('')}
        </div>
        ${previewText ? `
        <div class="thinking-preview" id="${uniqueId}-preview">
          <div class="thinking-preview-label">Real-time View</div>
          <div id="${uniqueId}-preview-text">${previewText}</div>
        </div>` : ''}
      </details>
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;

  div._stepsId = `${uniqueId}-steps`;
  div._previewId = `${uniqueId}-preview-text`;
  div._titleId = `${uniqueId}-title`;
  
  return div;
}

function activateThinkingStep(thinkingDiv, stepIndex, status = 'active', previewText = '') {
  // status: 'active' | 'done' | 'error'
  const steps = thinkingDiv.querySelectorAll('.thinking-step');
  steps.forEach((s, i) => {
    s.classList.remove('active', 'done', 'error');
    if (i < stepIndex) {
      s.querySelector('.step-icon').textContent = '✓';
      s.classList.add('done');
    } else if (i === stepIndex) {
      s.querySelector('.step-icon').textContent = status === 'error' ? '✗' : '◉';
      s.classList.add(status === 'error' ? 'error' : 'active');
    } else {
      s.querySelector('.step-icon').textContent = '○';
    }
  });
  
  // Update title
  const titleEl = thinkingDiv.querySelector('.thinking-title');
  if (titleEl && steps[stepIndex]) {
    const stepText = steps[stepIndex].querySelector('.step-text');
    if (stepText) titleEl.textContent = stepText.textContent;
  }
  
  // Update preview if provided
  if (previewText && thinkingDiv._previewId) {
    const previewEl = document.getElementById(thinkingDiv._previewId);
    if (previewEl) {
      previewEl.textContent = previewText;
    }
  }
  
  // Scroll to bottom
  const container = thinkingDiv.closest('.chat-messages-area, #chat-messages');
  if (container) container.scrollTop = container.scrollHeight;
}

// ===== ENHANCE =====
/**
 * Retry wrapper for fetch with exponential backoff
 * @param {string} url - The URL to fetch
 * @param {object} options - Fetch options
 * @param {number} retries - Number of retries (default 2)
 * @returns {Promise<Response>}
 */
async function fetchWithRetry(url, options, retries = 2) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000); // 60 second timeout
  
  for (let i = 0; i <= retries; i++) {
    try {
      const response = await fetch(url, { ...options, signal: controller.signal });
      clearTimeout(timeout);
      if (response.ok || i === retries) return response;
      // Wait before retry with exponential backoff
      if (i < retries) await new Promise(r => setTimeout(r, 1000 * Math.pow(2, i)));
    } catch (err) {
      clearTimeout(timeout);
      if (err.name === 'AbortError') throw new Error('Request timed out after 60 seconds');
      if (i === retries) throw err;
      if (i < retries) await new Promise(r => setTimeout(r, 1000 * Math.pow(2, i)));
    }
  }
  return fetch(url, options);
}

async function handleEnhance(prompt) {
  const urls = extractUrls(prompt);
  const isUrlRequest = urls.length > 0;

  // For URL requests show a richer thinking UI
  let loadingMsg;
  if (isUrlRequest) {
    const domain = getDomain(urls[0]);
    loadingMsg = addThinkingMessage([
      `Connecting to ${domain}`,
      `Crawling pages (features, pricing, docs, API...)`,
      `Searching web for tech stack & documentation`,
      `Synthesising deep analysis with AI`,
    ]);
    activateThinkingStep(loadingMsg, 0);
  } else {
    loadingMsg = addLoadingMessage();
  }

  try {
    const body = { prompt };
    if (selectedModel !== 'auto') body.model = selectedModel;

    const apiKey = document.getElementById('api-key-input')?.value || '';
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;

    // Simulate step progression for URL requests (backend is synchronous)
    let stepTimer;
    if (isUrlRequest) {
      let step = 0;
      stepTimer = setInterval(() => {
        step = Math.min(step + 1, 3);
        activateThinkingStep(loadingMsg, step);
      }, 4000);
    }

    console.log('=== MAKING API CALL ===');
    console.log('URL:', `${API_BASE}/enhance/`);
    console.log('Body:', body);
    console.log('Headers:', headers);

    const res = await fetchWithRetry(`${API_BASE}/enhance/`, {
      method: 'POST', headers, body: JSON.stringify(body)
    }, 2);
    
    console.log('=== RESPONSE RECEIVED ===');
    console.log('Status:', res.status);
    console.log('OK:', res.ok);
    
    const result = await res.json();
    console.log('=== PARSED RESULT ===');
    console.log('Result:', result);

    if (stepTimer) clearInterval(stepTimer);
    loadingMsg.remove();

    if (result.success) {
      // Map backend response fields to frontend expected format
      const enhanced = result.enhanced || result.enhanced_prompt || result.text || '';
      const originalScore = result.original_score || result.original_quality || result.original_scores || {};
      const enhancedScore = result.enhanced_score || result.enhanced_quality || result.enhanced_scores || {};
      const improvement = result.improvement || 0;
      const modelUsed = result.model || result.model_used || 'pipeline';
      
      // ── Welcome / greeting ──────────────────────────────────────────────
      if (result.type === 'welcome' || result.mode === 'greeting') {
        const html = `<div class="welcome-reply">${renderMarkdown(enhanced)}</div>`;
        addAssistantMessage(html);
        saveMsgToSession('assistant', html);
        return;
      }

      // ── URL / website analysis ──────────────────────────────────────────
      if (result.type === 'url_analysis' || result.mode === 'url_analysis') {
        const url = result.url;
        const domain = getDomain(url);
        const favicon = getFaviconUrl(url);
        const pagesScraped = result.pages_scraped || 0;
        const totalChars = result.total_chars || result.char_count || 0;
        const rawText = enhanced;

        // ── Page chips ──────────────────────────────────────────────────
        const pageChips = (result.pages || []).map(p => {
          const path = (() => { try { return new URL(p.url).pathname || '/'; } catch { return '/'; } })();
          return `<a href="${escapeHtml(p.url)}" target="_blank" rel="noopener" class="page-chip" title="${escapeHtml(p.url)}">
            <img src="https://www.google.com/s2/favicons?domain=${escapeHtml(p.url)}&sz=16" width="12" height="12" style="border-radius:2px;flex-shrink:0;" onerror="this.style.display='none'">
            <span>${escapeHtml(path === '/' ? domain : path)}</span>
          </a>`;
        }).join('');

        // ── Split the AI response into named sections ───────────────────
        // Sections are delimited by ## or # headings
        function splitSections(text) {
          const lines = text.split('\n');
          const sections = [];
          let current = { level: 2, title: 'Overview', body: [] };
          let hasHeaders = false;
          
          for (const line of lines) {
            const h1 = line.match(/^#\s+(.+)/);
            const h2 = line.match(/^##\s+(.+)/);
            const h3 = line.match(/^###\s+(.+)/);
            
            if (h1 || h2 || h3) {
              hasHeaders = true;
              if (current && current.body.join('').trim().length > 0) sections.push(current);
              current = { level: 2, title: (h1 || h2 || h3)[1].trim(), body: [] };
            } else if (current) {
              current.body.push(line);
            }
          }
          
          if (current && current.body.join('').trim().length > 0) sections.push(current);
          return sections;
        }

        // ── Detect if a section is the "How to Build" or "AI Prompts" section
        function isBuildSection(title) {
          const t = title.toLowerCase();
          return t.includes('how to build') || t.includes('build this') || t.includes('step-by-step');
        }
        function isAgentSection(title) {
          const t = title.toLowerCase();
          return t.includes('ai agent') || t.includes('ready prompt') || t.includes('copy & use') || t.includes('copy and use');
        }
        function isFeatureSection(title) {
          const t = title.toLowerCase();
          return t.includes('feature') || t.includes('functionality') || t.includes('capabilities') || t.includes('what it does');
        }
        // ── Automatic Feature Detection (for fallback diagrams) ───────
        function hasFeatures(t) {
          t = t.toLowerCase();
          const keywords = ['feature', 'functionality', 'breakdown', 'architecture', 'process', 'platform', 'how it works', 'steps'];
          return keywords.some(k => t.includes(k));
        }

        // ── Build use-case diagram from feature list (D2 format) ────────
        function buildUseCaseDiagram(text) {
          const features = [];
          const lines = text.split('\n');
          for (const line of lines) {
            const m = line.match(/^[-*•]\s+\*{0,2}([^*\n:]{4,60})\*{0,2}/);
            if (m) features.push(m[1].trim().replace(/[^a-zA-Z0-9 &]/g, '').trim());
          }
          const top = features.slice(0, 8);
          if (top.length < 2) return '';
          
          let d2Code = 'direction: right\n';
          d2Code += 'User: {\n  shape: person\n  label: 👤 User\n}\n';
          top.forEach((f, i) => {
            d2Code += `F${i}: "${f}"\n`;
            d2Code += `User -> F${i}: use\n`;
          });
          return d2Code;
        }

        const sections = splitSections(rawText);

        // ── Render each section as a card ───────────────────────────────
        let sectionsHtml = '';

        for (const sec of sections) {
          const bodyText = sec.body.join('\n');
          const rendered = renderMarkdown(bodyText);

          // Skip AI Agent and Build sections completely
          if (isAgentSection(sec.title) || isBuildSection(sec.title)) {
            continue;
          }

          // Render all other sections
          const emoji = sec.title.match(/^[\u{1F300}-\u{1FFFF}🌐✨🏗️🔌📡🎨📊🔐⚠️💡]/u)?.[0] || '📌';
          sectionsHtml += `
            <details class="analysis-section" open>
              <summary class="section-heading">
                <span class="section-emoji">${emoji}</span>
                <span>${escapeHtml(sec.title.replace(/^[\u{1F300}-\u{1FFFF}🌐✨🏗️🔌📡🎨📊🔐⚠️💡]\s*/u, ''))}</span>
                <span class="section-toggle">▾</span>
              </summary>
              <div class="section-body">${rendered}</div>
            </details>`;
        }

        const html = `
          <div class="analysis-card url-analysis-card">
            <!-- ── Analysis sections ── -->
            <div class="url-analysis-body">
              ${sectionsHtml}
            </div>

            <!-- ── Actions ── -->
            <div class="message-actions" style="padding:0 1.25rem 1rem;">
              <button onclick="copyText(decodeURIComponent('${encodeURIComponent(rawText).replace(/'/g, '%27')}'))">
                <i data-lucide="copy"></i> Copy Full Analysis
              </button>
              <a href="${escapeHtml(url)}" target="_blank" rel="noopener" class="url-visit-btn">
                <i data-lucide="external-link"></i> Open Site
              </a>
            </div>
          </div>
        `;
        addAssistantMessage(html);
        saveMsgToSession('assistant', html);
        try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(e) {}
        renderAllD2();
        return;
      }

      // ── Deep research ───────────────────────────────────────────────────
      if (result.type === 'deep_research' || result.mode === 'deep_research') {
        const category = result.classification?.category || result.domain || 'general';
        const html = `
          <div class="analysis-card">
            <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:1rem;flex-wrap:wrap;">
              <span style="font-size:0.75rem;font-weight:700;color:#f97316;background:rgba(249,115,22,0.1);padding:0.25rem 0.75rem;border-radius:100px;border:1px solid rgba(249,115,22,0.3);">🔬 Deep Research</span>
              <span style="font-size:0.72rem;color:var(--text-secondary);background:var(--primary-light);padding:0.2rem 0.65rem;border-radius:100px;border:1px solid var(--border);font-family:var(--font-mono);">${modelUsed.toUpperCase()}</span>
              <span style="font-size:0.72rem;color:var(--text-secondary);background:var(--primary-light);padding:0.2rem 0.65rem;border-radius:100px;border:1px solid var(--border);font-family:var(--font-mono);">${category.toUpperCase()}</span>
            </div>
            ${result.analysis ? `
            <details style="margin-bottom:1rem;">
              <summary style="cursor:pointer;font-size:0.78rem;color:var(--text-muted);padding:0.5rem;background:rgba(0,0,0,0.2);border-radius:6px;border:1px solid var(--border);">📋 Request Analysis (expand)</summary>
              <div style="padding:0.75rem;background:rgba(0,0,0,0.15);border-radius:0 0 6px 6px;font-size:0.82rem;color:var(--text-secondary);line-height:1.6;border:1px solid var(--border);border-top:none;">${renderMarkdown(result.analysis)}</div>
            </details>` : ''}
            <div style="line-height:1.8;">${renderMarkdown(enhanced)}</div>
            <div class="message-actions" style="margin-top:1rem;">
              <button onclick="copyText(decodeURIComponent('${encodeURIComponent(result.enhanced).replace(/'/g, '%27')}'))">
                <i data-lucide="copy"></i> Copy Full Answer
              </button>
            </div>
          </div>
        `;
        addAssistantMessage(html);
        saveMsgToSession('assistant', html);
        try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(e) {}
        return;
      }

      // ── Standard enhancement ────────────────────────────────────────────
      const category = result.classification?.category || result.domain || 'general';
      const origQuality = originalScore.quality || originalScore.overall || result.original_quality || 0;
      const enhQuality = enhancedScore.quality || enhancedScore.overall || result.enhanced_quality || 0;
      const html = `
        <div class="analysis-card" style="padding:0;">
          <div class="enhanced-content-body" style="line-height:1.75;color:var(--text-primary);margin-bottom:1.5rem;">
            ${renderMarkdown(enhanced)}
          </div>
          <div style="display:flex;gap:0.5rem;align-items:center;margin-bottom:0.85rem;flex-wrap:wrap;border-top:1px solid var(--border);padding-top:1rem;">
            <span style="font-size:0.72rem;color:var(--text-secondary);background:var(--bg-sidebar);padding:0.25rem 0.65rem;border-radius:100px;border:1px solid var(--border);font-family:var(--font-mono);">${modelUsed.toUpperCase()}</span>
            <span style="font-size:0.72rem;color:var(--text-secondary);background:var(--bg-sidebar);padding:0.25rem 0.65rem;border-radius:100px;border:1px solid var(--border);font-family:var(--font-mono);">${category.toUpperCase()}</span>
            <span style="font-size:0.72rem;color:var(--primary);background:var(--primary-ultra-light);padding:0.25rem 0.65rem;border-radius:100px;border:1px solid var(--primary-light);font-family:var(--font-mono);">${typeof origQuality === 'number' ? origQuality.toFixed(2) : origQuality} → ${typeof enhQuality === 'number' ? enhQuality.toFixed(2) : enhQuality} (+${typeof improvement === 'number' ? improvement.toFixed(2) : improvement} pts)</span>
          </div>
          <div class="message-actions">
            <button onclick="copyText(decodeURIComponent('${encodeURIComponent(enhanced).replace(/'/g, '%27')}'))" style="background:transparent;border:1px solid var(--border);color:var(--text-secondary);padding:0.4rem 0.8rem;border-radius:6px;cursor:pointer;display:flex;align-items:center;gap:0.4rem;font-size:0.8rem;transition:all 0.2s;">
              <i data-lucide="copy" style="width:14px;height:14px;"></i> Copy
            </button>
          </div>
        </div>
      `;
      addAssistantMessage(html);
      saveMsgToSession('assistant', html);
    } else {
      const errHtml = `<div class="error-msg">${escapeHtml(result.error || 'Enhancement failed')}</div>`;
      addAssistantMessage(errHtml);
      saveMsgToSession('assistant', errHtml);
    }
  } catch (error) {
    if (loadingMsg) loadingMsg.remove();
    console.error('=== ENHANCE ERROR ===');
    console.error('Error type:', error.name);
    console.error('Error message:', error.message);
    console.error('Full error:', error);
    console.error('API_BASE:', API_BASE);
    const errHtml = `<div class="error-msg">Connection failed — is the server running at ${API_BASE}?<br><small style="opacity:0.7">Error: ${error.message}</small></div>`;
    addAssistantMessage(errHtml);
    saveMsgToSession('assistant', errHtml);
  }
}

// ===== ANALYZE =====
async function handleAnalyze(prompt) {
  const loadingMsg = addLoadingMessage();

  try {
    const body = { prompt };
    if (selectedModel !== 'auto') body.model = selectedModel;

    const apiKey = document.getElementById('api-key-input')?.value || '';
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;

    const res = await fetchWithRetry(`${API_BASE}/quality-heatmap/`, {
      method: 'POST', headers, body: JSON.stringify(body)
    }, 2);
    const result = await res.json();
    loadingMsg.remove();

    if (result.success) {
      // Backend returns quality directly, not nested under data
      const q = result.quality || result.data || {};
      const overall = q.overall || 0;
      const grade = q.grade || 'F';
      const dims = q.dimensions || q.metrics || {};
      const suggestions = q.deductions || q.suggestions || [];
      
      const html = `
        <div class="analysis-card">
          <h3 style="margin-bottom:1.25rem;color:var(--primary);font-family:var(--font-mono);font-size:0.9rem;">[///] Quality Analysis</h3>
          <div style="display:flex;gap:2rem;justify-content:center;margin-bottom:1.5rem;padding:1.25rem;background:rgba(0,0,0,0.3);border-radius:10px;border:1px solid var(--border);">
            <div style="text-align:center;">
              <div style="font-size:2.2rem;font-weight:800;color:var(--primary);font-family:var(--font-display);text-shadow:0 0 20px rgba(0,255,65,0.3);">${overall.toFixed ? overall.toFixed(2) : overall}</div>
              <div style="color:var(--text-muted);font-size:0.72rem;font-family:var(--font-mono);">SCORE</div>
            </div>
            <div style="text-align:center;">
              <div style="font-size:2.2rem;font-weight:800;color:var(--primary);font-family:var(--font-display);text-shadow:0 0 20px rgba(0,255,65,0.3);">${grade}</div>
              <div style="color:var(--text-muted);font-size:0.72rem;font-family:var(--font-mono);">GRADE</div>
            </div>
          </div>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0.6rem;margin-bottom:1.25rem;">
            ${Object.entries(dims).map(([k,v]) => `
              <div style="background:rgba(0,0,0,0.3);padding:0.75rem;border-radius:8px;border:1px solid var(--border);">
                <div style="font-size:0.68rem;color:var(--text-muted);margin-bottom:0.35rem;text-transform:uppercase;font-family:var(--font-mono);">${k.replace('_',' ')}</div>
                <div style="height:5px;background:rgba(255,255,255,0.05);border-radius:3px;overflow:hidden;margin-bottom:0.35rem;">
                  <div style="height:100%;width:${((v.score || v)/10)*100}%;background:linear-gradient(90deg,var(--primary),var(--accent));border-radius:3px;box-shadow:0 0 8px rgba(0,255,65,0.3);"></div>
                </div>
                <div style="font-size:0.9rem;font-weight:700;color:var(--primary);font-family:var(--font-mono);">${(v.score || v).toFixed ? (v.score || v).toFixed(1) : (v.score || v)}/10</div>
              </div>
            `).join('')}
          </div>
          ${suggestions.length > 0 ? `
            <div style="background:var(--primary-light);border:1px solid var(--border);border-radius:10px;padding:1rem;">
              <h4 style="margin-bottom:0.6rem;color:var(--primary);font-size:0.8rem;font-family:var(--font-mono);">[TIP] Issues Detected</h4>
              ${suggestions.map(s => `
                <div style="margin-bottom:0.6rem;padding-bottom:0.6rem;border-bottom:1px solid var(--border);">
                  <div style="color:var(--text-secondary);font-size:0.76rem;">${typeof s === 'string' ? s : s.issue || s.message}</div>
                  ${s.fix ? `<div style="color:var(--success);font-size:0.76rem;font-family:var(--font-mono);">[FIX] ${s.fix}</div>` : ''}
                </div>
              `).join('')}
            </div>
          ` : '<div style="color:var(--success);padding:0.75rem;text-align:center;font-family:var(--font-mono);font-size:0.85rem;">[OK] Your prompt looks great!</div>'}
        </div>
      `;
      addAssistantMessage(html);
      saveMsgToSession('assistant', html);
    } else {
      const errHtml = `<div style="color:var(--error);padding:0.75rem;font-family:var(--font-mono);font-size:0.85rem;">[ERR] ${escapeHtml(result.error || 'Analysis failed')}</div>`;
      addAssistantMessage(errHtml);
      saveMsgToSession('assistant', errHtml);
    }
  } catch (error) {
    loadingMsg.remove();
    const errHtml = `<div style="color:var(--error);padding:0.75rem;font-family:var(--font-mono);font-size:0.85rem;">[ERR] Connection failed</div>`;
    addAssistantMessage(errHtml);
    saveMsgToSession('assistant', errHtml);
  }
}

// ===== COMPARE =====
async function handleCompare(prompt) {
  const loadingMsg = addLoadingMessage();

  try {
    const body = { prompt, include_comparison: true };
    if (selectedModel !== 'auto') body.model = selectedModel;

    const apiKey = document.getElementById('api-key-input')?.value || '';
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;

    const res = await fetch(`${API_BASE}/ab-test/`, {
      method: 'POST', headers, body: JSON.stringify(body)
    });
    const result = await res.json();
    loadingMsg.remove();

    if (result.success) {
      const c = result.data;
      const icons = { concise: '[MIN]', detailed: '[MAX]', structured: '[SYS]' };
      const html = `
        <div class="analysis-card">
          <h3 style="margin-bottom:1.25rem;color:var(--primary);font-family:var(--font-mono);font-size:0.9rem;">[&lt;&gt;] A/B Test Results</h3>
          <div style="background:var(--primary-light);border:1px solid var(--border);border-radius:10px;padding:0.85rem;margin-bottom:1.25rem;font-family:var(--font-mono);font-size:0.8rem;">
            <strong style="color:var(--primary);">[BEST]</strong>
            <span style="color:var(--text-primary);"> ${c.recommendation.best_variation.toUpperCase()} — ${c.recommendation.reason}</span>
          </div>
          <div style="display:grid;gap:0.6rem;">
            ${Object.entries(c.variations).map(([type, v]) => `
              <div style="background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:10px;padding:1rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.6rem;">
                  <h4 style="text-transform:uppercase;font-size:0.85rem;font-family:var(--font-mono);color:var(--primary);">${icons[type]||'[VAR]'} ${type}</h4>
                  <span style="font-size:0.68rem;color:var(--text-muted);font-family:var(--font-mono);">${v.model||''}</span>
                </div>
                <div style="background:rgba(0,0,0,0.3);padding:0.75rem;border-radius:8px;margin-bottom:0.6rem;line-height:1.6;font-size:0.82rem;border:1px solid var(--border);">
                  ${renderMarkdown(v.text)}
                </div>
                <div style="display:flex;gap:1rem;font-size:0.72rem;color:var(--text-muted);font-family:var(--font-mono);">
                  <span>QUALITY: <strong style="color:var(--primary);">${v.quality.overall}/10</strong></span>
                  <span>LENGTH: <strong style="color:var(--text-primary);">${v.length}</strong></span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
      addAssistantMessage(html);
      saveMsgToSession('assistant', html);
    } else {
      const errHtml = `<div style="color:var(--error);padding:0.75rem;font-family:var(--font-mono);font-size:0.85rem;">[ERR] ${escapeHtml(result.error || 'Compare failed')}</div>`;
      addAssistantMessage(errHtml);
      saveMsgToSession('assistant', errHtml);
    }
  } catch (error) {
    loadingMsg.remove();
    const errHtml = `<div style="color:var(--error);padding:0.75rem;font-family:var(--font-mono);font-size:0.85rem;">[ERR] Connection failed</div>`;
    addAssistantMessage(errHtml);
    saveMsgToSession('assistant', errHtml);
  }
}

// ===== UTILITIES =====
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function renderMarkdown(text) {
  if (!text || typeof text !== 'string') return '';
  if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
    // Custom handling for D2 diagram blocks (e.g. ```d2 ... ```)
    if (text.toLowerCase().includes('```d2')) {
      text = text.replace(/```d2\s*([\s\S]*?)```/gi, (match, code) => {
        return `<div class="analysis-section diagram-section" style="margin:1rem 0;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;overflow:hidden;box-shadow:var(--shadow);position:relative;">
          <div class="section-heading" style="padding:0.75rem 1rem;background:var(--bg-darker);border-bottom:1px solid var(--border);font-weight:700;font-size:0.8rem;display:flex;justify-content:space-between;align-items:center;color:var(--text-primary);">
            <div style="display:flex;align-items:center;gap:0.5rem;">
              <span>📐 System Architecture View</span>
            </div>
            <div class="diagram-toolbar" style="display:flex;gap:0.5rem;align-items:center;">
              <button onclick="zoomDiagram(this, 1.1)" title="Zoom In" style="background:none;border:none;cursor:pointer;font-size:1rem;padding:2px;">➕</button>
              <button onclick="zoomDiagram(this, 0.9)" title="Zoom Out" style="background:none;border:none;cursor:pointer;font-size:1rem;padding:2px;">➖</button>
              <button onclick="downloadDiagram(this)" title="Download PNG" style="background:none;border:none;cursor:pointer;font-size:1rem;padding:2px;margin-left:5px;">💾</button>
            </div>
          </div>
          <div class="section-body diagram-wrapper" style="padding:0;display:flex;justify-content:center;background:var(--bg-card);min-height:300px;overflow:auto;position:relative;">
            <div class="d2-diagram-container zoom-target" data-d2="${encodeURIComponent(code.trim())}" style="width:100%;height:auto;display:flex;align-items:center;justify-content:center;transform-origin:top center;transition:transform 0.2s;">
              <div style="padding:2rem;color:var(--text-muted);font-size:0.75rem;">Initializing high-fidelity diagram...</div>
            </div>
          </div>
        </div>`;
      });
    } else if (text.includes('{ shape:') && text.includes(' -> ')) {
      // SAFETY FALLBACK: Capture un-fenced D2 code
      const lines = text.split('\n');
      let d2Buffer = [];
      let nonD2Before = [];
      let nonD2After = [];
      let foundD2 = false;
      for (const line of lines) {
        if (line.includes('{ shape:') || line.includes(' -> ') || (foundD2 && line.trim().length > 0 && !line.match(/^[a-zA-Z0-9]/))) {
          d2Buffer.push(line);
          foundD2 = true;
        } else if (!foundD2) { nonD2Before.push(line); } else { nonD2After.push(line); }
      }
      if (d2Buffer.length > 2) {
        const code = d2Buffer.join('\n');
        const diagramHtml = `<div class="analysis-section diagram-section" style="margin:1rem 0;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;overflow:hidden;box-shadow:var(--shadow);">
          <div class="section-heading" style="padding:0.75rem 1rem;background:var(--bg-darker);border-bottom:1px solid var(--border);font-weight:700;font-size:0.8rem;display:flex;align-items:center;gap:0.5rem;color:var(--text-primary);">
            <span>📐 System Architecture View (Auto-Detected)</span>
          </div>
          <div class="section-body" style="padding:0;display:flex;justify-content:center;background:var(--bg-card);min-height:300px;">
            <div class="d2-diagram-container" data-d2="${encodeURIComponent(code.trim())}" style="width:100%;height:auto;display:flex;align-items:center;justify-content:center;">
              <div style="padding:2rem;color:var(--text-muted);font-size:0.75rem;">Initializing high-fidelity diagram...</div>
            </div>
          </div>
        </div>`;
        text = nonD2Before.join('\n') + '\n' + diagramHtml + '\n' + nonD2After.join('\n');
      }
    }

    // Custom handling for [!TIP] thinking block
    if (text.includes('> [!TIP]') && text.includes('Thinking Process:')) {
      text = text.replace(/> \[!TIP\]\n> \*\*Thinking Process:\*\*\n> ([\s\S]*?)\n\n/g, (match, p1) => {
        return `<div class="ai-thinking-box">
          <div class="thinking-box-header">
            <span class="thinking-pulse"></span>
            <strong>Thinking Process</strong>
          </div>
          <div class="thinking-box-body">${p1.replace(/^> /gm, '').trim()}</div>
        </div>\n\n`;
      });
    }

    return DOMPurify.sanitize(marked.parse(text));
  }
  return escapeHtml(text);
}

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => {
      showToast('[OK] Copied', 'Text copied to clipboard', 'success');
    }).catch(() => fallbackCopy(text));
  } else {
    fallbackCopy(text);
  }
}

function fallbackCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0;';
  document.body.appendChild(ta);
  ta.focus(); ta.select();
  try { document.execCommand('copy'); showToast('[OK] Copied', 'Text copied', 'success'); }
  catch(e) { showToast('[ERR]', 'Copy failed', 'error'); }
  document.body.removeChild(ta);
}

function showToast(title, message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<div class="toast-content"><div class="toast-title">${title}</div><div class="toast-description">${message}</div></div>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

/**
 * Renders all D2 diagram containers in the chat
 */
async function renderAllD2() {
  const containers = document.querySelectorAll('.d2-diagram-container:not([data-rendered])');
  if (containers.length === 0) return;
  
  console.log(`Rendering ${containers.length} D2 diagrams via optimized Cloud Engine...`);
  
  for (const el of containers) {
    try {
      const codeAttr = el.getAttribute('data-d2');
      if (!codeAttr) continue;
      
      const code = decodeURIComponent(codeAttr);
      el.setAttribute('data-rendered', 'true');

      // Kroki API expects base64 + zlib, but we can also use the simple /d2/svg/ path
      // Actually, Kroki has a very simple GET API for D2.
      // We will use the POST API for reliability with large diagrams
      const response = await fetch('https://kroki.io/d2/svg', {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: code
      });

      if (response.ok) {
        const svg = await response.text();
        el.innerHTML = svg;
        console.log('D2 render successful via Kroki');
        
        const svgEl = el.querySelector('svg');
        if (svgEl) {
          svgEl.style.width = '100%';
          svgEl.style.height = 'auto';
          svgEl.style.maxWidth = '100%';
        }
      } else {
        throw new Error(`Cloud engine response: ${response.status}`);
      }
    } catch (e) {
      console.warn('Cloud D2 failed, using Technical Fallback:', e);
      const codeAttr = el.getAttribute('data-d2');
      const rawCode = codeAttr ? decodeURIComponent(codeAttr) : '';
      
      el.innerHTML = `
        <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;overflow:hidden;box-shadow:var(--shadow-sm);">
          <div style="background:#f8fafc;padding:0.75rem 1.25rem;border-bottom:1px solid var(--border);display:flex;justify-content:between;align-items:center;">
             <span style="font-size:0.7rem;font-weight:800;color:var(--primary);text-transform:uppercase;letter-spacing:1px;">📐 System Logic Specification</span>
          </div>
          <div style="padding:1.5rem;background:var(--bg-card);font-family:var(--font-mono);font-size:0.88rem;color:var(--text-primary);line-height:1.7;white-space:pre-wrap;">${escapeHtml(rawCode)}</div>
        </div>
      `;
    }
  }
}
/**
 * INTERACTIVE DIAGRAM FUNCTIONS
 */
window.zoomDiagram = function(btn, factor) {
  const wrapper = btn.closest('.diagram-section').querySelector('.zoom-target');
  if (!wrapper) return;
  const currentScale = parseFloat(wrapper.dataset.scale || 1);
  const newScale = Math.min(Math.max(currentScale * factor, 0.5), 3);
  wrapper.style.transform = `scale(${newScale})`;
  wrapper.dataset.scale = newScale;
  // Adjust wrapper height to prevent overlap if zooming in
  if (newScale > 1) {
    wrapper.style.marginBottom = `${(newScale - 1) * 300}px`;
  } else {
    wrapper.style.marginBottom = '0';
  }
};

window.downloadDiagram = function(btn) {
  const svg = btn.closest('.diagram-section').querySelector('svg');
  if (!svg) return showToast('[ERR]', 'Diagram not rendered yet', 'error');
  
  const svgData = new XMLSerializer().serializeToString(svg);
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const img = new Image();
  
  // High res download
  const svgSize = svg.getBoundingClientRect();
  const scale = 2; // 2x resolution
  canvas.width = svgSize.width * scale;
  canvas.height = svgSize.height * scale;
  
  img.onload = function() {
    ctx.fillStyle = "white";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    const pngUrl = canvas.toDataURL("image/png");
    const downloadLink = document.createElement("a");
    downloadLink.href = pngUrl;
    downloadLink.download = "promptx_diagram.png";
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
    showToast('[OK]', 'Diagram downloaded as PNG', 'success');
  };
  
  img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svgData)));
};
