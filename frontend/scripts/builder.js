/* ═══════════════════════════════════════════════════════════════════════
   PROMPTX BUILDER ENGINE — AI Agent + VFS + WebContainers + Live Preview
   Dual-mode: HTML (iframe srcdoc) + React (WebContainer with Vite)
   ═══════════════════════════════════════════════════════════════════════ */

// API URL
if (typeof window.API_BASE === 'undefined') {
  window.API_BASE = (() => {
    const loc = window.location;
    if (loc.hostname === 'localhost' || loc.hostname === '127.0.0.1' || loc.protocol === 'file:') {
      return 'http://127.0.0.1:8000/api/v1';
    }
    return 'https://promptx-hkfx.onrender.com/api/v1';
  })();
}
const API_BASE = window.API_BASE;

// ── WebContainer Import (ESM) ────────────────────────────────────────────
let WebContainer;
let webcontainerInstance = null;
let wcBooted = false;

// Try to load WebContainer API — graceful fallback if unavailable
try {
    const wcModule = await import('@webcontainer/api');
    WebContainer = wcModule.WebContainer;
    console.log('[BUILDER] WebContainer API loaded successfully');
} catch (e) {
    console.warn('[BUILDER] WebContainer API not available — React mode disabled.', e.message);
    WebContainer = null;
}

// ── Virtual File System (for HTML mode) ──────────────────────────────────
const VFS = {
    files: new Map(),
    set(path, content) { this.files.set(path, content); this.onUpdate(); },
    get(path) { return this.files.get(path) || null; },
    delete(path) { this.files.delete(path); this.onUpdate(); },
    clear() { this.files.clear(); this.onUpdate(); },
    list() { return Array.from(this.files.keys()).sort(); },
    getAll() {
        const all = {};
        this.files.forEach((c, p) => { all[p] = c; });
        return all;
    },
    onUpdate() { renderFileTree(); renderCodeDropdown(); updateFileCountBadge(); }
};

// ── State ────────────────────────────────────────────────────────────────
let isGenerating = false;
let chatHistory = [];
let currentMode = 'html'; // 'html' or 'react'

// ── DOM References ───────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const $agentInput   = $('agent-input');
const $btnSend      = $('btn-send');
const $chatMessages = $('chat-messages');
const $chatWelcome  = $('chat-welcome');
const $agentStatus  = $('agent-status');
const $charCount    = $('agent-char-count');
const $previewIframe = $('preview-iframe');
const $previewEmpty = $('preview-empty');
const $fileTree     = $('file-tree');
const $codeDisplay  = $('code-display-content');
const $codeSelect   = $('code-file-select');
const $consoleOut   = $('console-output');
const $projectName  = $('project-name');
const $modelSelect  = $('builder-model-select');
const $fileCountBadge = $('file-count-badge');

// ── Initialize ───────────────────────────────────────────────────────────
setupInputHandlers();
setupTabSwitching();
setupResizer();
setupButtons();
setupModeToggle();
consoleLog('info', 'PromptX Agent initialized. Mode: HTML (iframe preview)');

if (WebContainer) {
    consoleLog('success', 'WebContainer API available — React mode enabled!');
} else {
    consoleLog('warn', 'WebContainer API unavailable — React mode disabled. Only HTML mode available.');
    // Disable React mode button
    const reactBtn = document.querySelector('[data-mode="react"]');
    if (reactBtn) {
        reactBtn.disabled = true;
        reactBtn.title = 'WebContainers require HTTPS or localhost with proper headers';
        reactBtn.style.opacity = '0.3';
    }
}

// ── Mode Toggle ──────────────────────────────────────────────────────────
function setupModeToggle() {
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;
            if (mode === 'react' && !WebContainer) {
                consoleLog('error', 'WebContainer API not available. Cannot switch to React mode.');
                return;
            }
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentMode = mode;
            consoleLog('info', `Switched to ${mode.toUpperCase()} mode.`);

            if (mode === 'react' && !wcBooted) {
                bootWebContainer();
            }
        });
    });
}

// ══════════════════════════════════════════════════════════════════════════
// WEBCONTAINER ENGINE (React/Node.js Mode)
// ══════════════════════════════════════════════════════════════════════════

async function bootWebContainer() {
    if (wcBooted || !WebContainer) return;
    consoleLog('agent', '[WC] Booting WebContainer...');
    $agentStatus.textContent = 'Booting WebContainer...';

    try {
        webcontainerInstance = await WebContainer.boot();
        wcBooted = true;
        consoleLog('success', '[WC] WebContainer booted successfully!');
        $agentStatus.textContent = 'Ready (WebContainer)';

        // Listen for server-ready events
        webcontainerInstance.on('server-ready', (port, url) => {
            consoleLog('success', `[WC] Dev server ready on port ${port}`);
            $previewEmpty.style.display = 'none';
            $previewIframe.classList.remove('hidden');
            $previewIframe.src = url;
            // Switch to preview tab
            document.querySelector('[data-tab="preview"]').click();
        });
    } catch (err) {
        consoleLog('error', `[WC] Boot failed: ${err.message}`);
        $agentStatus.textContent = 'WebContainer boot failed';

        // Fallback to HTML mode
        currentMode = 'html';
        document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
        document.querySelector('[data-mode="html"]').classList.add('active');
    }
}

async function mountAndRunProject(files) {
    if (!webcontainerInstance) return;

    consoleLog('agent', '[WC] Mounting project files...');
    $agentStatus.textContent = 'Mounting files...';

    // Convert flat files to WebContainer mount format
    const mountTree = {};
    for (const file of files) {
        const parts = file.path.split('/');
        let current = mountTree;
        for (let i = 0; i < parts.length - 1; i++) {
            if (!current[parts[i]]) {
                current[parts[i]] = { directory: {} };
            }
            current = current[parts[i]].directory;
        }
        current[parts[parts.length - 1]] = {
            file: { contents: file.content }
        };
    }

    try {
        await webcontainerInstance.mount(mountTree);
        consoleLog('success', `[WC] ${files.length} files mounted.`);

        // Check if package.json exists → run npm install
        const hasPackageJson = files.some(f => f.path === 'package.json');
        if (hasPackageJson) {
            await runNpmInstall();
            await runDevServer();
        } else {
            consoleLog('warn', '[WC] No package.json found. Skipping npm install.');
        }
    } catch (err) {
        consoleLog('error', `[WC] Mount error: ${err.message}`);
    }
}

async function runNpmInstall() {
    consoleLog('agent', '[WC] Running npm install...');
    $agentStatus.textContent = 'npm install...';

    const installProcess = await webcontainerInstance.spawn('npm', ['install']);

    // Stream output to console
    installProcess.output.pipeTo(new WritableStream({
        write(data) {
            consoleLog('info', data.trim());
        }
    }));

    const exitCode = await installProcess.exit;
    if (exitCode !== 0) {
        consoleLog('error', `[WC] npm install failed with code ${exitCode}`);
        throw new Error('npm install failed');
    }
    consoleLog('success', '[WC] npm install completed successfully!');
}

async function runDevServer() {
    consoleLog('agent', '[WC] Starting dev server (npm run dev)...');
    $agentStatus.textContent = 'Starting dev server...';

    const devProcess = await webcontainerInstance.spawn('npm', ['run', 'dev']);
    devProcess.output.pipeTo(new WritableStream({
        write(data) {
            consoleLog('info', data.trim());
        }
    }));

    // Don't await exit — dev server runs indefinitely
    consoleLog('success', '[WC] Dev server starting... Waiting for server-ready event.');
}

async function writeFileToWC(path, content) {
    if (!webcontainerInstance) return;
    try {
        // Ensure parent directories exist
        const parts = path.split('/');
        if (parts.length > 1) {
            const dir = parts.slice(0, -1).join('/');
            await webcontainerInstance.fs.mkdir(dir, { recursive: true });
        }
        await webcontainerInstance.fs.writeFile(path, content);
        consoleLog('success', `[WC] Written: ${path}`);
    } catch (err) {
        consoleLog('error', `[WC] Write error for ${path}: ${err.message}`);
    }
}

async function deleteFileFromWC(path) {
    if (!webcontainerInstance) return;
    try {
        await webcontainerInstance.fs.rm(path);
        consoleLog('warn', `[WC] Deleted: ${path}`);
    } catch (err) {
        consoleLog('error', `[WC] Delete error for ${path}: ${err.message}`);
    }
}

// ══════════════════════════════════════════════════════════════════════════
// INPUT HANDLING
// ══════════════════════════════════════════════════════════════════════════

function setupInputHandlers() {
    $agentInput.addEventListener('input', () => {
        $agentInput.style.height = 'auto';
        $agentInput.style.height = Math.min($agentInput.scrollHeight, 150) + 'px';
        $charCount.textContent = $agentInput.value.length + ' chars';
        $btnSend.disabled = !$agentInput.value.trim() || isGenerating;
    });

    $agentInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendPrompt();
        }
    });

    $btnSend.addEventListener('click', sendPrompt);
}

// ══════════════════════════════════════════════════════════════════════════
// TAB SWITCHING
// ══════════════════════════════════════════════════════════════════════════

function setupTabSwitching() {
    document.querySelectorAll('.preview-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.preview-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.preview-pane').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('pane-' + tab.dataset.tab).classList.add('active');
        });
    });
}

// ══════════════════════════════════════════════════════════════════════════
// PANEL RESIZER
// ══════════════════════════════════════════════════════════════════════════

function setupResizer() {
    const resizer = $('panel-resizer');
    const chatPanel = $('panel-chat');
    let isResizing = false;

    resizer.addEventListener('mousedown', () => {
        isResizing = true;
        resizer.classList.add('dragging');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        chatPanel.style.width = Math.max(320, Math.min(600, e.clientX)) + 'px';
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            resizer.classList.remove('dragging');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
    });
}

// ══════════════════════════════════════════════════════════════════════════
// BUTTONS
// ══════════════════════════════════════════════════════════════════════════

function setupButtons() {
    $('btn-clear-chat').addEventListener('click', () => {
        chatHistory = [];
        $chatMessages.innerHTML = '';
        $chatWelcome.style.display = '';
        $chatMessages.appendChild($chatWelcome);
        VFS.clear();
        hidePreview();
        $consoleOut.innerHTML = '<div class="console-line console-info">[SYSTEM] Chat cleared.</div>';
    });

    $('btn-download').addEventListener('click', downloadAsZip);

    $('btn-copy-code').addEventListener('click', () => {
        navigator.clipboard.writeText($codeDisplay.textContent).then(() => {
            consoleLog('success', 'Code copied!');
        });
    });

    $codeSelect.addEventListener('change', () => showCodeForFile($codeSelect.value));
}

// ══════════════════════════════════════════════════════════════════════════
// CORE: SEND PROMPT TO AI AGENT
// ══════════════════════════════════════════════════════════════════════════

async function sendPrompt() {
    const prompt = $agentInput.value.trim();
    if (!prompt || isGenerating) return;

    $chatWelcome.style.display = 'none';
    addChatMessage('user', prompt);
    chatHistory.push({ role: 'user', content: prompt });

    $agentInput.value = '';
    $agentInput.style.height = 'auto';
    $charCount.textContent = '0 chars';
    $btnSend.disabled = true;

    isGenerating = true;
    $agentStatus.innerHTML = '<span class="thinking-dots"><span></span><span></span><span></span></span> Generating...';
    const thinkingId = addThinkingBubble();

    consoleLog('agent', `[AGENT] Processing: "${prompt.substring(0, 60)}..."`);
    consoleLog('info', `[MODE] ${currentMode.toUpperCase()} | [MODEL] ${$modelSelect.value}`);

    try {
        const model = $modelSelect.value;
        const existingFiles = VFS.getAll();

        const response = await fetch(`${API_BASE}/generate-app`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: currentMode === 'react'
                    ? `[REACT/VITE PROJECT] ${prompt}. Use React with Vite. Generate package.json, vite.config.js, index.html, src/App.jsx, src/main.jsx, src/App.css. Use modern React patterns.`
                    : prompt,
                model,
                existing_files: Object.keys(existingFiles).length > 0 ? existingFiles : null,
                history: chatHistory.slice(-6),
                mode: currentMode
            })
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || `Server error: ${response.status}`);
        }

        const data = await response.json();
        removeElement(thinkingId);

        if (data.files && data.files.length > 0) {
            const actions = [];
            const isFirstBuild = VFS.files.size === 0;

            for (const file of data.files) {
                const action = file.action || 'create';
                if (action === 'delete') {
                    VFS.delete(file.path);
                    if (currentMode === 'react') await deleteFileFromWC(file.path);
                    actions.push({ path: file.path, action: 'deleted' });
                    consoleLog('warn', `[DELETE] ${file.path}`);
                } else {
                    const existed = VFS.get(file.path) !== null;
                    VFS.set(file.path, file.content);
                    if (currentMode === 'react' && wcBooted) {
                        await writeFileToWC(file.path, file.content);
                    }
                    const a = existed ? 'modified' : 'created';
                    actions.push({ path: file.path, action: a });
                    consoleLog('success', `[${a.toUpperCase()}] ${file.path} (${file.content.length} bytes)`);
                }
            }

            // Build agent response
            let agentReply = data.explanation ? data.explanation + '\n\n' : '';
            agentReply += actions.map(a =>
                `<span class="agent-file-action ${a.action}">` +
                (a.action === 'created' ? '+ ' : a.action === 'deleted' ? '- ' : '~ ') +
                `${a.path}</span>`
            ).join('\n');

            addChatMessage('agent', agentReply, true);
            chatHistory.push({ role: 'assistant', content: data.explanation || 'Files updated.' });

            if (chatHistory.length <= 3) {
                const name = prompt.split(' ').slice(0, 4).join(' ');
                $projectName.textContent = name.length > 30 ? name.substring(0, 30) + '...' : name;
            }

            // Render based on mode
            if (currentMode === 'html') {
                renderPreview();
            } else if (currentMode === 'react' && wcBooted) {
                if (isFirstBuild) {
                    await mountAndRunProject(data.files);
                } else {
                    // Files already written individually above
                    consoleLog('info', '[WC] Files updated. Vite hot-reload will handle the rest.');
                }
            }

            consoleLog('success', `[AGENT] Build complete. ${actions.length} files. Model: ${data.model || model}`);
        } else {
            addChatMessage('agent', data.explanation || data.enhanced || 'Done.', true);
            chatHistory.push({ role: 'assistant', content: data.explanation || '' });
        }

    } catch (error) {
        removeElement(thinkingId);
        addChatMessage('agent', `❌ **Error:** ${error.message}`, true);
        consoleLog('error', `[ERROR] ${error.message}`);
    }

    isGenerating = false;
    $agentStatus.textContent = currentMode === 'react' && wcBooted ? 'Ready (WebContainer)' : 'Ready';
    $btnSend.disabled = !$agentInput.value.trim();
}

// ══════════════════════════════════════════════════════════════════════════
// CHAT MESSAGE RENDERING
// ══════════════════════════════════════════════════════════════════════════

function addChatMessage(role, content, isMarkdown = false) {
    const msg = document.createElement('div');
    msg.className = `chat-msg ${role}`;

    const avatarLabel = role === 'user' ? 'U' : 'AI';
    let bodyContent;

    if (isMarkdown && role === 'agent') {
        try {
            bodyContent = DOMPurify.sanitize(marked.parse(content, { breaks: true }));
        } catch (e) { bodyContent = content; }
    } else {
        bodyContent = escapeHtml(content);
    }

    msg.innerHTML = `
        <div class="chat-msg-avatar">${avatarLabel}</div>
        <div class="chat-msg-body">${bodyContent}</div>
    `;

    $chatMessages.appendChild(msg);
    $chatMessages.scrollTop = $chatMessages.scrollHeight;

    msg.querySelectorAll('pre code').forEach(block => {
        try { hljs.highlightElement(block); } catch(e) {}
    });

    return msg;
}

function addThinkingBubble() {
    const id = 'thinking-' + Date.now();
    const el = document.createElement('div');
    el.className = 'chat-msg agent';
    el.id = id;
    el.innerHTML = `
        <div class="chat-msg-avatar">AI</div>
        <div class="chat-msg-body">
            <div class="agent-thinking">
                <div class="thinking-dots"><span></span><span></span><span></span></div>
                <span class="thinking-label">Agent is building your app...</span>
            </div>
        </div>
    `;
    $chatMessages.appendChild(el);
    $chatMessages.scrollTop = $chatMessages.scrollHeight;
    return id;
}

// ══════════════════════════════════════════════════════════════════════════
// PREVIEW RENDERING (HTML Mode)
// ══════════════════════════════════════════════════════════════════════════

function renderPreview() {
    const files = VFS.getAll();
    const htmlFile = files['index.html'];
    if (!htmlFile) {
        consoleLog('warn', '[PREVIEW] No index.html found.');
        return;
    }

    let fullHtml = htmlFile;

    // Inject CSS
    Object.entries(files).forEach(([path, content]) => {
        if (path.endsWith('.css')) {
            const tag = `<style>/* ${path} */\n${content}\n</style>`;
            fullHtml = fullHtml.includes('</head>') ? fullHtml.replace('</head>', tag + '\n</head>') : tag + '\n' + fullHtml;
        }
    });

    // Inject JS
    Object.entries(files).forEach(([path, content]) => {
        if (path.endsWith('.js')) {
            const tag = `<script>/* ${path} */\n${content}\n<\/script>`;
            fullHtml = fullHtml.includes('</body>') ? fullHtml.replace('</body>', tag + '\n</body>') : fullHtml + '\n' + tag;
        }
    });

    $previewEmpty.style.display = 'none';
    $previewIframe.classList.remove('hidden');
    $previewIframe.srcdoc = fullHtml;
    document.querySelector('[data-tab="preview"]').click();
}

function hidePreview() {
    $previewEmpty.style.display = '';
    $previewIframe.classList.add('hidden');
    $previewIframe.srcdoc = '';
    $previewIframe.src = 'about:blank';
}

// ══════════════════════════════════════════════════════════════════════════
// FILE TREE & CODE VIEWER
// ══════════════════════════════════════════════════════════════════════════

function renderFileTree() {
    const files = VFS.list();
    if (!files.length) { $fileTree.innerHTML = '<div class="file-tree-empty">No files generated yet</div>'; return; }

    const icons = { html: '📄', css: '🎨', js: '⚡', jsx: '⚛️', tsx: '⚛️', json: '📋', md: '📝', svg: '🖼️' };

    $fileTree.innerHTML = files.map(path => {
        const ext = path.split('.').pop();
        const icon = icons[ext] || '📄';
        const content = VFS.get(path);
        const size = content ? (content.length > 1024 ? (content.length / 1024).toFixed(1) + ' KB' : content.length + ' B') : '0 B';
        return `<div class="file-tree-item" onclick="window._selectFile('${path}')">
            <span class="file-icon">${icon}</span><span>${path}</span><span class="file-size">${size}</span>
        </div>`;
    }).join('');
}

// Expose to onclick handlers (since we're in a module)
window._selectFile = function(path) {
    document.querySelectorAll('.file-tree-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.file-tree-item').forEach(el => {
        if (el.textContent.includes(path)) el.classList.add('active');
    });
    showCodeForFile(path);
    document.querySelector('[data-tab="code"]').click();
};

function renderCodeDropdown() {
    const files = VFS.list();
    $codeSelect.innerHTML = files.length === 0
        ? '<option>No files</option>'
        : files.map(f => `<option value="${f}">${f}</option>`).join('');
    if (files.length > 0) showCodeForFile(files[0]);
}

function showCodeForFile(path) {
    const content = VFS.get(path);
    if (!content) { $codeDisplay.textContent = 'File not found'; return; }
    $codeDisplay.textContent = content;
    $codeSelect.value = path;
    const ext = path.split('.').pop();
    const langMap = { html: 'html', css: 'css', js: 'javascript', jsx: 'javascript', tsx: 'typescript', json: 'json', py: 'python', md: 'markdown' };
    $codeDisplay.className = 'hljs language-' + (langMap[ext] || 'plaintext');
    try { hljs.highlightElement($codeDisplay); } catch(e) {}
}

function updateFileCountBadge() { $fileCountBadge.textContent = VFS.files.size; }

// ══════════════════════════════════════════════════════════════════════════
// CONSOLE LOGGER
// ══════════════════════════════════════════════════════════════════════════

function consoleLog(type, message) {
    const line = document.createElement('div');
    line.className = `console-line console-${type}`;
    line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    $consoleOut.appendChild(line);
    $consoleOut.scrollTop = $consoleOut.scrollHeight;
}

// ══════════════════════════════════════════════════════════════════════════
// DOWNLOAD / EXPORT
// ══════════════════════════════════════════════════════════════════════════

function downloadAsZip() {
    const files = VFS.getAll();
    if (!Object.keys(files).length) { consoleLog('warn', 'No files to download.'); return; }
    let combined = '';
    Object.entries(files).forEach(([path, content]) => {
        combined += `\n${'='.repeat(60)}\n// FILE: ${path}\n${'='.repeat(60)}\n${content}\n`;
    });
    const blob = new Blob([combined], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = ($projectName.textContent || 'promptx-project') + '.txt';
    a.click();
    URL.revokeObjectURL(url);
    consoleLog('success', `Exported ${Object.keys(files).length} files.`);
}

// ══════════════════════════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════════════════════════

// Expose fillPrompt globally for the welcome chips
window.fillPrompt = function(text) {
    $agentInput.value = text;
    $agentInput.dispatchEvent(new Event('input'));
    $agentInput.focus();
};

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function removeElement(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}
