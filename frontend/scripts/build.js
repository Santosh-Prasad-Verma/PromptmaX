// Build Page JavaScript

// State
let currentTool = 'enhance';
let currentModel = 'auto';
let messages = [];
let isLoading = false;

// DOM Elements
const promptInput = document.getElementById('prompt-input');
const sendBtn = document.getElementById('send-btn');
const messagesContainer = document.getElementById('messages-container');
const welcomeMessage = document.getElementById('welcome-message');
const charCount = document.getElementById('char-count');
const modelBadge = document.getElementById('model-badge');
const resultsPanel = document.getElementById('results-panel');
const panelContent = document.getElementById('panel-content');
const panelClose = document.getElementById('panel-close');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  initializeLucide();
  setupEventListeners();
});

function initializeLucide() {
  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }
}

function setupEventListeners() {
  // Tool selection
  document.querySelectorAll('.tool-btn').forEach(btn => {
    btn.addEventListener('click', () => selectTool(btn.dataset.tool));
  });

  // Model selection
  document.querySelectorAll('.model-btn').forEach(btn => {
    btn.addEventListener('click', () => selectModel(btn.dataset.model));
  });

  // Input handling
  promptInput.addEventListener('input', handleInputChange);
  promptInput.addEventListener('keydown', handleKeyDown);
  
  // Send button
  sendBtn.addEventListener('click', sendMessage);

  // Panel close
  panelClose.addEventListener('click', () => resultsPanel.classList.add('hidden'));
}

function selectTool(tool) {
  currentTool = tool;
  document.querySelectorAll('.tool-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tool === tool);
  });
  updatePlaceholder();
}

function selectModel(model) {
  currentModel = model;
  document.querySelectorAll('.model-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.model === model);
  });
  const modelNames = {
    'gemini': 'Gemini 2.0',
    'groq':   'Groq'
  };
  modelBadge.textContent = modelNames[model] || 'Auto';
}

function updatePlaceholder() {
  const placeholders = {
    'enhance': 'Describe what you want to create...',
    'analyze': 'Paste a prompt to analyze...',
    'abtest': 'Enter a prompt to create variations...',
    'templates': 'Search for templates...'
  };
  promptInput.placeholder = placeholders[currentTool] || 'Describe what you want to create...';
}

function handleInputChange() {
  const length = promptInput.value.length;
  charCount.textContent = `${length} character${length !== 1 ? 's' : ''}`;
  
  // Auto-resize
  promptInput.style.height = 'auto';
  promptInput.style.height = Math.min(promptInput.scrollHeight, 200) + 'px';
  
  // Enable/disable send button
  sendBtn.disabled = !promptInput.value.trim();
}

function handleKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function quickStart(type) {
  const prompts = {
    blog: 'Write a professional blog post about artificial intelligence in healthcare',
    code: 'Create a Python function to fetch data from an API and cache it',
    email: 'Write a follow-up email to a potential client after a demo call',
    strategy: 'Design a marketing strategy for a SaaS product launch'
  };
  promptInput.value = prompts[type] || '';
  handleInputChange();
  promptInput.focus();
}

async function sendMessage() {
  const prompt = promptInput.value.trim();
  if (!prompt || isLoading) return;

  // Hide welcome message
  welcomeMessage.style.display = 'none';
  
  // Add user message
  addMessage('user', prompt);
  promptInput.value = '';
  handleInputChange();
  
  // Show loading
  isLoading = true;
  sendBtn.disabled = true;
  
  const loadingId = addLoadingMessage();

  try {
    const result = await callAPI(prompt);
    
    // Remove loading
    removeMessage(loadingId);
    
    // Add assistant response
    addMessage('assistant', result.text);
    
    // Show results panel
    showResults(result);
    
  } catch (error) {
    removeMessage(loadingId);
    addMessage('assistant', `Error: ${error.message}`);
    showToast('Failed to process prompt', 'error');
  }

  isLoading = false;
  sendBtn.disabled = false;
}

async function callAPI(prompt) {
  let endpoint = '/api/v1/enhance/';
  let payload = { prompt, model: currentModel };

  if (currentTool === 'analyze') {
    endpoint = '/api/v1/analyze/';
  } else if (currentTool === 'abtest') {
    endpoint = '/api/v1/ab-test/';
  }

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

function addMessage(role, content) {
  const messageId = Date.now().toString();
  messages.push({ id: messageId, role, content });
  
  const messageEl = document.createElement('div');
  messageEl.className = `message ${role}`;
  messageEl.id = messageId;
  
  const avatarIcon = role === 'assistant' ? 'bot' : 'user';
  
  messageEl.innerHTML = `
    <div class="message-avatar">
      <i data-lucide="${avatarIcon}" width="18" height="18"></i>
    </div>
    <div class="message-content">
      <p>${escapeHtml(content)}</p>
    </div>
  `;
  
  messagesContainer.appendChild(messageEl);
  initializeLucide();
  
  // Scroll to bottom
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  return messageId;
}

function addLoadingMessage() {
  const messageId = 'loading-' + Date.now();
  
  const messageEl = document.createElement('div');
  messageEl.className = 'message assistant';
  messageEl.id = messageId;
  
  messageEl.innerHTML = `
    <div class="message-avatar">
      <i data-lucide="bot" width="18" height="18"></i>
    </div>
    <div class="message-content">
      <div class="loading">
        <div class="loading-dots">
          <span></span><span></span><span></span>
        </div>
        <span>Processing...</span>
      </div>
    </div>
  `;
  
  messagesContainer.appendChild(messageEl);
  initializeLucide();
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  return messageId;
}

function removeMessage(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function showResults(result) {
  resultsPanel.classList.remove('hidden');
  
  let html = '';
  
  if (currentTool === 'enhance') {
    const score = result.enhanced_score?.total || 0;
    const percentage = result.enhanced_score?.percentage || 0;
    
    html = `
      <div class="result-card">
        <h4>Enhanced Prompt</h4>
        <p>${escapeHtml(result.enhanced)}</p>
      </div>
      
      <div class="result-card">
        <h4>Quality Score</h4>
        <div class="quality-score">
          <div class="score-bar">
            <div class="score-fill" style="width: ${percentage}%"></div>
          </div>
          <span class="score-value">${score}/10</span>
        </div>
      </div>
      
      <div class="result-card">
        <h4>Improvement</h4>
        <p>+${result.improvement} points</p>
      </div>
      
      <div class="result-card">
        <h4>Model Used</h4>
        <p>${result.model || currentModel}</p>
      </div>
    `;
  } else if (currentTool === 'analyze') {
    const data = result.data || result;
    html = `
      <div class="result-card">
        <h4>Overall Score</h4>
        <div class="quality-score">
          <div class="score-bar">
            <div class="score-fill" style="width: ${data.overall * 10}%"></div>
          </div>
          <span class="score-value">${data.overall}/10</span>
        </div>
      </div>
      
      <div class="result-card">
        <h4>Grade</h4>
        <p style="font-size: 1.5rem; font-weight: 600; color: var(--accent);">${data.grade}</p>
      </div>
      
      <div class="result-card">
        <h4>Metrics</h4>
        ${Object.entries(data.metrics || {}).map(([key, val]) => `
          <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span style="text-transform: capitalize; color: var(--text-secondary);">${key.replace('_', ' ')}</span>
            <span style="font-weight: 500;">${val.score}/10</span>
          </div>
        `).join('')}
      </div>
    `;
  } else if (currentTool === 'abtest') {
    const variations = result.data?.variations || result;
    html = Object.entries(variations).map(([key, val]) => `
      <div class="result-card">
        <h4 style="text-transform: capitalize;">${key}</h4>
        <p>${escapeHtml(val.text?.substring(0, 200))}</p>
        <div class="quality-score">
          <span style="color: var(--text-muted); font-size: 0.8rem;">${val.length} chars</span>
          <span style="color: var(--accent);">${val.model}</span>
        </div>
      </div>
    `).join('');
  }
  
  panelContent.innerHTML = html;
}

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.remove();
  }, 3000);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
