// Only declare API_BASE if it doesn't exist
if (typeof window.API_BASE === 'undefined') {
  window.API_BASE = (function() {
    const loc = window.location;
    if (loc.hostname === 'localhost' || loc.hostname === '127.0.0.1' || loc.protocol === 'file:') {
      return 'http://127.0.0.1:8000/api/v1';
    }
    return 'https://promptx-hkfx.onrender.com/api/v1';
  })();
}
const API_BASE = window.API_BASE;
let currentMode = 'enhance';
let selectedModel = 'auto';

window.addEventListener('load', () => {
  // Reveal the canvas tee box after data load
  document.body.classList.add('data-loaded');
});

document.addEventListener('DOMContentLoaded', () => {
  document.body.classList.add('js-enhanced');

  try {
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  } catch (e) {
    console.error('Failed to initialize icons:', e);
  }
  
  // Shared setup
  setupModelSelector();
  setupChatInput();
  setupQuickActions();
  
  // Landing page specific
  if (document.getElementById('navbar')) {
    setupNavbar();
    setupMobileNav();
  }
  setupScrollAnimations();
  setupCanvasParticles();
  
  // Chat page or landing page mode tabs
  setupModeTabs();
  
  const apiInput = document.getElementById('api-key-input');
  if (apiInput) {
    apiInput.value = localStorage.getItem('promptx_api_key') || '';
    apiInput.addEventListener('input', (e) => localStorage.setItem('promptx_api_key', e.target.value));
  }
});

// ===== NAVBAR =====
function setupNavbar() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;
  
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  });
  
  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
      const targetId = link.getAttribute('href');
      if (targetId === '#') return;
      const target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
}

// ===== MOBILE NAV =====
function setupMobileNav() {
  const toggle = document.getElementById('nav-mobile-toggle');
  const navLinks = document.getElementById('nav-links');
  
  if (toggle && navLinks) {
    toggle.addEventListener('click', () => {
      navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
      navLinks.style.position = 'absolute';
      navLinks.style.top = '72px';
      navLinks.style.left = '0';
      navLinks.style.right = '0';
      navLinks.style.flexDirection = 'column';
      navLinks.style.background = 'rgba(3, 8, 5, 0.98)';
      navLinks.style.padding = '1rem';
      navLinks.style.borderBottom = '1px solid var(--border)';
      navLinks.style.backdropFilter = 'blur(20px)';
    });
  }
}

// ===== MODE TABS =====
function setupModeTabs() {
  const tabs = document.querySelectorAll('.app-mode-tab, .chat-mode-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentMode = tab.getAttribute('data-mode');
      updateModeIndicator();
    });
  });
}

// ===== SCROLL ANIMATIONS =====
function setupScrollAnimations() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  });
  
  document.querySelectorAll('.fade-in').forEach(el => {
    observer.observe(el);
  });
}

// ===== MODEL SELECTOR =====
function setupModelSelector() {
  const customSelect = document.getElementById('custom-model-select');
  if (!customSelect) return;
  const selected = customSelect.querySelector('.select-selected');
  const itemsContainer = customSelect.querySelector('.select-items');
  const items = itemsContainer.querySelectorAll('div');

  selected.addEventListener('click', (e) => {
    e.stopPropagation();
    itemsContainer.classList.toggle('select-hide');
    selected.classList.toggle('open');
  });

  items.forEach(item => {
    item.addEventListener('click', (e) => {
      e.stopPropagation();
      selectedModel = item.getAttribute('data-value');
      
      const iconClass = item.getAttribute('data-icon');
      const text = item.querySelector('span').textContent;
      
      selected.innerHTML = `<i data-lucide="${iconClass}"></i> <span>${text}</span> <i data-lucide="chevron-down" class="chevron"></i>`;
      try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(err){}
      
      items.forEach(i => i.classList.remove('same-as-selected'));
      item.classList.add('same-as-selected');
      
      itemsContainer.classList.add('select-hide');
      selected.classList.remove('open');
      
      showToast('[SYS] Model Changed', `Switched to ${text}`, 'success');
    });
  });

  document.addEventListener('click', () => {
    itemsContainer.classList.add('select-hide');
    selected.classList.remove('open');
  });
}

function updateModeIndicator() {
  const modeNames = {
    enhance: 'Enhance Mode',
    analyze: 'Analyze Mode',
    compare: 'Compare Mode'
  };
  const indicator = document.getElementById('mode-indicator');
  if (indicator) indicator.textContent = modeNames[currentMode] || 'Enhance Mode';
}

// ===== CHAT INPUT =====
function setupChatInput() {
  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  
  if (!chatInput || !sendBtn) return;
  
  chatInput.addEventListener('input', () => {
    sendBtn.disabled = !chatInput.value.trim();
    chatInput.style.height = 'auto';
    chatInput.style.height = chatInput.scrollHeight + 'px';
  });
  
  chatInput.addEventListener('keydown', (e) => {
    if ((e.key === 'Enter' || e.keyCode === 13) && !e.shiftKey) {
      e.preventDefault();
      if (chatInput.value.trim()) {
        handleSend();
      }
    }
  });
  
  sendBtn.addEventListener('click', handleSend);
}

async function handleSend() {
  const chatInput = document.getElementById('chat-input');
  const message = chatInput.value.trim();
  if (!message) return;
  
  hideWelcome();
  addUserMessage(message);
  autoSaveToHistory(message);
  
  chatInput.value = '';
  chatInput.style.height = 'auto';
  document.getElementById('send-btn').disabled = true;
  
  if (currentMode === 'enhance') {
    await handleEnhance(message);
  } else if (currentMode === 'analyze') {
    await handleAnalyze(message);
  } else if (currentMode === 'compare') {
    await handleCompare(message);
  }
}

function hideWelcome() {
  const welcome = document.getElementById('welcome-screen');
  if (welcome) welcome.remove();
}

function addUserMessage(text) {
  const messagesContainer = document.getElementById('chat-messages');
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message user';
  messageDiv.innerHTML = `
    <div class="message-content">${escapeHtml(text)}</div>
    <div class="message-avatar">U</div>
  `;
  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addAssistantMessage(content) {
  const messagesContainer = document.getElementById('chat-messages');
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message assistant';
  messageDiv.innerHTML = `
    <div class="message-avatar"><img src="Public/PROMPTX.png" alt="Promptrix" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;"></div>
    <div class="message-content">${content}</div>
  `;
  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(e){}
  return messageDiv;
}

function addLoadingMessage() {
  const msg = addAssistantMessage('<div style="padding: 0.75rem; display: flex; align-items: center; gap: 0.75rem;"><div class="typing-cursor" style="width: 3px; height: 16px;"></div> <span style="color: var(--text-secondary); font-size: 0.9rem; font-family: var(--font-mono);">[SYS] Processing...</span></div>');
  return msg;
}

// ===== ENHANCE MODE =====
async function handleEnhance(prompt) {
  const loadingMsg = addLoadingMessage();
  
  try {
    const requestBody = { prompt };
    if (selectedModel !== 'auto') requestBody.model = selectedModel;
    
    const apiKey = document.getElementById('api-key-input')?.value || '';
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;
    
    const response = await fetch(`${API_BASE}/enhance/`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(requestBody)
    });
    
    const result = await response.json();
    loadingMsg.remove();
    
    if (result.success) {
      const content = `
        <div class="analysis-card">
          <h3 style="margin-bottom: 1rem; color: var(--primary); font-family: var(--font-mono); font-size: 0.95rem;">[&gt;_] Enhanced Prompt</h3>
          <div style="background: rgba(0,0,0,0.3); padding: 1.25rem; border-radius: 12px; margin-bottom: 1rem; line-height: 1.8; border: 1px solid var(--border);">
            ${renderMarkdown(result.enhanced)}
          </div>
          <div style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap;">
            <span style="font-size: 0.78rem; color: var(--text-secondary); background: var(--primary-light); padding: 0.25rem 0.75rem; border-radius: 100px; border: 1px solid var(--border); font-family: var(--font-mono);">
              MODEL: ${(result.model || result.model_used || "?").toUpperCase()}
            </span>
            <span style="font-size: 0.78rem; color: var(--primary); background: var(--primary-light); padding: 0.25rem 0.75rem; border-radius: 100px; border: 1px solid var(--border); font-family: var(--font-mono);">
              +${result.improvement} quality pts
            </span>
          </div>
          <div class="message-actions">
            <button onclick="copyText(decodeURIComponent('${encodeURIComponent(result.enhanced).replace(/'/g, '%27')}'))">
              <i data-lucide="copy"></i> Copy
            </button>
            <button onclick="saveToHistory(decodeURIComponent('${encodeURIComponent(prompt).replace(/'/g, '%27')}'), decodeURIComponent('${encodeURIComponent(result.enhanced).replace(/'/g, '%27')}'))">
              <i data-lucide="bookmark"></i> Save
            </button>
          </div>
        </div>
      `;
      addAssistantMessage(content);
    } else {
      addAssistantMessage(`<div style="color: var(--error); padding: 1rem; font-family: var(--font-mono);">[ERR] ${escapeHtml(result.error || 'Failed to enhance prompt')}</div>`);
    }
  } catch (error) {
    loadingMsg.remove();
    addAssistantMessage('<div style="color: var(--error); padding: 1rem; font-family: var(--font-mono);">[ERR] Connection failed. Check your server.</div>');
  }
}

// ===== ANALYZE MODE =====
async function handleAnalyze(prompt) {
  const loadingMsg = addLoadingMessage();
  
  try {
    const requestBody = { prompt };
    if (selectedModel !== 'auto') requestBody.model = selectedModel;
    
    const apiKey = document.getElementById('api-key-input')?.value || '';
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;
    
    const response = await fetch(`${API_BASE}/quality-heatmap/`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(requestBody)
    });
    
    const result = await response.json();
    loadingMsg.remove();
    
    if (result.success) {
      const analysis = result.data;
      const metrics = analysis.metrics;
      
      const content = `
        <div class="analysis-card">
          <h3 style="margin-bottom: 1.5rem; color: var(--primary); font-family: var(--font-mono); font-size: 0.95rem;">[///] Quality Analysis</h3>
          
          <div style="display: flex; gap: 2rem; justify-content: center; margin-bottom: 2rem; padding: 1.5rem; background: rgba(0,0,0,0.3); border-radius: 12px; border: 1px solid var(--border);">
            <div style="text-align: center;">
              <div style="font-size: 2.5rem; font-weight: 800; color: var(--primary); font-family: var(--font-display); text-shadow: 0 0 20px rgba(255,255,255,0.3);">${analysis.overall}</div>
              <div style="color: var(--text-secondary); font-size: 0.8rem; font-family: var(--font-mono);">SCORE</div>
            </div>
            <div style="text-align: center;">
              <div style="font-size: 2.5rem; font-weight: 800; color: var(--primary); font-family: var(--font-display); text-shadow: 0 0 20px rgba(255,255,255,0.3);">${analysis.grade}</div>
              <div style="color: var(--text-secondary); font-size: 0.8rem; font-family: var(--font-mono);">GRADE</div>
            </div>
          </div>
          
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; margin-bottom: 1.5rem;">
            ${Object.entries(metrics).map(([key, value]) => `
              <div style="background: rgba(0,0,0,0.3); padding: 0.85rem; border-radius: 8px; border: 1px solid var(--border);">
                <div style="font-size: 0.72rem; color: var(--text-secondary); margin-bottom: 0.4rem; text-transform: uppercase; font-family: var(--font-mono);">
                  ${key.replace('_', ' ')}
                </div>
                <div style="height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; margin-bottom: 0.4rem;">
                  <div style="height: 100%; width: ${(value.score * 100)}%; background: linear-gradient(90deg, var(--primary), var(--accent)); border-radius: 3px; box-shadow: 0 0 8px rgba(255,255,255,0.3);"></div>
                </div>
                <div style="font-size: 1rem; font-weight: 700; color: var(--primary); font-family: var(--font-mono);">${(value.score * 10).toFixed(1)}/10</div>
              </div>
            `).join('')}
          </div>
          
          ${analysis.suggestions.length > 0 ? `
            <div style="background: var(--primary-light); border: 1px solid var(--border); border-radius: 12px; padding: 1.15rem;">
              <h4 style="margin-bottom: 0.75rem; color: var(--primary); font-size: 0.85rem; font-family: var(--font-mono);">[TIP] Suggestions</h4>
              ${analysis.suggestions.map(sug => `
                <div style="margin-bottom: 0.75rem; padding-bottom: 0.75rem; border-bottom: 1px solid var(--border);">
                  <div style="font-weight: 600; color: var(--primary); margin-bottom: 0.3rem; font-size: 0.82rem;">${sug.category}</div>
                  <div style="color: var(--text-secondary); font-size: 0.8rem; margin-bottom: 0.3rem;">${sug.issue}</div>
                  <div style="color: var(--success); font-size: 0.8rem; font-family: var(--font-mono);">[FIX] ${sug.fix}</div>
                </div>
              `).join('')}
            </div>
          ` : '<div style="color: var(--success); padding: 1rem; text-align: center; font-family: var(--font-mono);">[OK] Your prompt looks great!</div>'}
        </div>
      `;
      addAssistantMessage(content);
    } else {
      addAssistantMessage(`<div style="color: var(--error); padding: 1rem; font-family: var(--font-mono);">[ERR] ${escapeHtml(result.error || 'Failed to analyze prompt')}</div>`);
    }
  } catch (error) {
    loadingMsg.remove();
    addAssistantMessage('<div style="color: var(--error); padding: 1rem; font-family: var(--font-mono);">[ERR] Analysis failed</div>');
  }
}

// ===== COMPARE MODE =====
async function handleCompare(prompt) {
  const loadingMsg = addLoadingMessage();
  
  try {
    const requestBody = { prompt, include_comparison: true };
    if (selectedModel !== 'auto') requestBody.model = selectedModel;
    
    const apiKey = document.getElementById('api-key-input')?.value || '';
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;
    
    const response = await fetch(`${API_BASE}/ab-test/`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(requestBody)
    });
    
    const result = await response.json();
    loadingMsg.remove();
    
    if (result.success) {
      const comparison = result.data;
      
      const typeIcons = { concise: '[MIN]', detailed: '[MAX]', structured: '[SYS]' };
      
      const content = `
        <div class="analysis-card">
          <h3 style="margin-bottom: 1.5rem; color: var(--primary); font-family: var(--font-mono); font-size: 0.95rem;">[&lt;&gt;] A/B Test Variations</h3>
          
          <div style="background: var(--primary-light); border: 1px solid var(--border); border-radius: 12px; padding: 1rem; margin-bottom: 1.5rem; font-family: var(--font-mono); font-size: 0.85rem;">
            <strong style="color: var(--primary);">[BEST]</strong>
            <span style="color: var(--text-primary);"> ${comparison.recommendation.best_variation.toUpperCase()} — ${comparison.recommendation.reason}</span>
          </div>
          
          <div style="display: grid; gap: 0.75rem;">
            ${Object.entries(comparison.variations).map(([type, variation]) => `
              <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 12px; padding: 1.15rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                  <h4 style="text-transform: uppercase; font-size: 0.9rem; font-family: var(--font-mono); color: var(--primary);">${typeIcons[type] || '[VAR]'} ${type}</h4>
                  <span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">${variation.model || ''}</span>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 0.85rem; border-radius: 8px; margin-bottom: 0.75rem; line-height: 1.6; font-size: 0.88rem; border: 1px solid var(--border);">
                  ${renderMarkdown(variation.text)}
                </div>
                <div style="display: flex; gap: 1.25rem; font-size: 0.78rem; color: var(--text-secondary); font-family: var(--font-mono);">
                  <span>QUALITY: <strong style="color: var(--primary);">${variation.quality.overall}/10</strong></span>
                  <span>LENGTH: <strong style="color: var(--text-primary);">${variation.length}</strong></span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
      addAssistantMessage(content);
    } else {
      addAssistantMessage(`<div style="color: var(--error); padding: 1rem; font-family: var(--font-mono);">[ERR] ${escapeHtml(result.error || 'Failed to generate variations')}</div>`);
    }
  } catch (error) {
    loadingMsg.remove();
    addAssistantMessage('<div style="color: var(--error); padding: 1rem; font-family: var(--font-mono);">[ERR] Compare failed</div>');
  }
}

// ===== QUICK ACTIONS =====
function setupQuickActions() {
  document.querySelectorAll('.quick-action').forEach(btn => {
    btn.addEventListener('click', () => {
      const action = btn.getAttribute('data-action');
      const tabs = document.querySelectorAll('.app-mode-tab, .chat-mode-tab');
      tabs.forEach(t => {
        t.classList.remove('active');
        if (t.getAttribute('data-mode') === action) {
          t.classList.add('active');
        }
      });
      currentMode = action;
      updateModeIndicator();
      const input = document.getElementById('chat-input');
      if (input) input.focus();
    });
  });
}

// ===== UTILITY FUNCTIONS =====
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => {
      showToast('[OK] Copied', 'Text copied to clipboard', 'success');
    }).catch(() => fallbackCopyTextToClipboard(text));
  } else {
    fallbackCopyTextToClipboard(text);
  }
}

function copyCodeSnippet() {
  const code = `# pip install promptx-py
from promptx import PromptX

app = PromptX(api_key="px-YOUR_API_KEY")

# Enhance a prompt:
result = app.enhance('Write a blog post about AI')

# Analyze prompt quality:
score = app.analyze(result.enhanced)
print(score.overall)  # → 9.2/10`;
  copyText(code);
}

function fallbackCopyTextToClipboard(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.style.cssText = "position:fixed;top:0;left:0;opacity:0;";
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  try {
    document.execCommand('copy');
    showToast('[OK] Copied', 'Text copied to clipboard', 'success');
  } catch (err) {
    showToast('[ERR]', 'Failed to copy text', 'error');
  }
  document.body.removeChild(textArea);
}

function saveToHistory(original, enhanced) {
  const history = getSafeHistory();
  if (!history.find(h => h.original === original && h.enhanced === enhanced)) {
    history.unshift({ id: Date.now().toString(), original, enhanced, timestamp: Date.now() });
    localStorage.setItem('promptHistory', JSON.stringify(history));
  }
  showToast('[OK] Saved', 'Prompt saved to history', 'success');
}

function autoSaveToHistory(original) {
  const history = getSafeHistory();
  if (history.length > 0 && history[0].original === original) return;
  history.unshift({ id: Date.now().toString(), original, enhanced: '', timestamp: Date.now() });
  if (history.length > 50) history.length = 50;
  localStorage.setItem('promptHistory', JSON.stringify(history));
}

function showToast(title, message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      <div class="toast-description">${message}</div>
    </div>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function getSafeHistory() {
  try { return JSON.parse(localStorage.getItem('promptHistory') || '[]'); } 
  catch(e) { return []; }
}

// renderMarkdown moved to chat.js for unified logic

function exportHistory() {
  const history = getSafeHistory();
  if (history.length === 0) return showToast('[ERR]', 'No history to export', 'error');
  const blob = new Blob([JSON.stringify(history, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `promptx_history_${new Date().toISOString().split('T')[0]}.json`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('[OK] Exported', 'History downloaded', 'success');
}

// ===== INTERACTIVE CANVAS PARTICLE SYSTEM =====
function setupCanvasParticles() {
  const canvas = document.getElementById('fc-canvas-particles');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let w, h;
  let mouse = { x: -9999, y: -9999 };
  const PARTICLE_COUNT = 70;
  const CONNECTION_DIST = 120;
  const MOUSE_RADIUS = 150;
  const particles = [];

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  document.addEventListener('mousemove', (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
  });
  document.addEventListener('mouseleave', () => {
    mouse.x = -9999;
    mouse.y = -9999;
  });

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push({
      x: Math.random() * (w || window.innerWidth),
      y: Math.random() * (h || window.innerHeight),
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      r: Math.random() * 1.8 + 0.8,
      alpha: Math.random() * 0.4 + 0.15
    });
  }

  function draw() {
    ctx.clearRect(0, 0, w, h);
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0) p.x = w;
      if (p.x > w) p.x = 0;
      if (p.y < 0) p.y = h;
      if (p.y > h) p.y = 0;

      const dx = p.x - mouse.x;
      const dy = p.y - mouse.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < MOUSE_RADIUS && dist > 0) {
        const force = (MOUSE_RADIUS - dist) / MOUSE_RADIUS;
        p.vx += (dx / dist) * force * 0.3;
        p.vy += (dy / dist) * force * 0.3;
      }
      p.vx *= 0.995;
      p.vy *= 0.995;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(139, 0, 0, ' + p.alpha + ')';
      ctx.fill();

      for (let j = i + 1; j < particles.length; j++) {
        const p2 = particles[j];
        const cdx = p.x - p2.x;
        const cdy = p.y - p2.y;
        const cdist = Math.sqrt(cdx * cdx + cdy * cdy);
        if (cdist < CONNECTION_DIST) {
          const lineAlpha = (1 - cdist / CONNECTION_DIST) * 0.12;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.strokeStyle = 'rgba(139, 0, 0, ' + lineAlpha + ')';
          ctx.lineWidth = 0.6;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }
  draw();
}
