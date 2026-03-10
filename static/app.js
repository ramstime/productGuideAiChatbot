// ---- State ----
const state = {
    sources: [],
    sending: false,
};

// ---- DOM Elements ----
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ---- Toast Notifications ----
function showToast(message, type = 'info') {
    const container = $('.toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

// ---- Sidebar Tabs ----
function initTabs() {
    $$('.sidebar-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            $$('.sidebar-tab').forEach(t => t.classList.remove('active'));
            $$('.sidebar-panel').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            $(`#panel-${tab.dataset.tab}`).classList.add('active');
        });
    });
}

// ---- File Upload ----
function initUpload() {
    const zone = $('.upload-zone');
    const fileInput = $('#file-input');

    zone.addEventListener('click', () => fileInput.click());

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('dragover');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            uploadFiles(e.dataTransfer.files);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            uploadFiles(fileInput.files);
            fileInput.value = '';
        }
    });
}

async function uploadFiles(files) {
    // Show progress items for each file
    const progressIds = [];
    for (const file of files) {
        const id = 'upload-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6);
        progressIds.push({ id, name: file.name });
        addProgressItem(id, file.name, 'file');
    }

    const formData = new FormData();
    for (const file of files) {
        formData.append('files', file);
    }

    try {
        const resp = await fetch('/api/upload', { method: 'POST', body: formData });
        const data = await resp.json();

        if (!resp.ok) throw new Error(data.detail || 'Upload failed');

        for (let i = 0; i < data.results.length; i++) {
            const result = data.results[i];
            const pid = progressIds[i]?.id;
            if (result.status === 'success') {
                state.sources.push({ name: result.filename, type: 'file', chunks: result.chunks, added_at: new Date().toISOString() });
                if (pid) completeProgressItem(pid, 'success', `${result.chunks} chunks`);
                showToast(`✓ ${result.filename} uploaded`, 'success');
            } else {
                if (pid) completeProgressItem(pid, 'error', result.error);
                showToast(`✗ ${result.filename}: ${result.error}`, 'error');
            }
        }
        renderSources();
        updateStats();
    } catch (err) {
        progressIds.forEach(p => completeProgressItem(p.id, 'error', err.message));
        showToast(`Upload error: ${err.message}`, 'error');
    }
}

// ---- URL Addition ----
function initURLInput() {
    const input = $('#url-input');
    const btn = $('#add-url-btn');

    btn.addEventListener('click', () => addURL(input.value));
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addURL(input.value);
    });
}

async function addURL(url) {
    url = url.trim();
    if (!url) return;

    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = 'https://' + url;
    }

    $('#url-input').value = '';
    const pid = 'url-' + Date.now();
    addProgressItem(pid, url, 'url');

    try {
        const resp = await fetch('/api/add-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });
        const data = await resp.json();

        if (!resp.ok) throw new Error(data.detail || 'Failed to fetch URL');

        state.sources.push({ name: data.title || url, type: 'url', chunks: data.chunks, url, added_at: new Date().toISOString() });
        completeProgressItem(pid, 'success', `${data.chunks} chunks`);
        showToast(`✓ URL added (${data.chunks} chunks)`, 'success');
        renderSources();
        updateStats();
    } catch (err) {
        completeProgressItem(pid, 'error', err.message);
        showToast(`URL error: ${err.message}`, 'error');
    }
}

// ---- Progress Items ----
function addProgressItem(id, name, type) {
    const container = $('#progress-list');
    container.style.display = 'block';
    const div = document.createElement('div');
    div.id = id;
    div.className = 'progress-item';
    div.innerHTML = `
        <div class="progress-item-header">
            <span class="progress-name">${type === 'file' ? '📄' : '🔗'} ${name}</span>
            <span class="progress-status processing"><span class="spinner"></span> Processing</span>
        </div>
        <div class="progress-bar-track"><div class="progress-bar-fill animating"></div></div>
    `;
    container.appendChild(div);
}

function completeProgressItem(id, status, detail) {
    const el = document.getElementById(id);
    if (!el) return;
    const statusEl = el.querySelector('.progress-status');
    const barFill = el.querySelector('.progress-bar-fill');
    barFill.classList.remove('animating');
    if (status === 'success') {
        statusEl.className = 'progress-status done';
        statusEl.innerHTML = `✓ ${detail}`;
        barFill.style.width = '100%';
        barFill.classList.add('success');
    } else {
        statusEl.className = 'progress-status failed';
        statusEl.innerHTML = `✗ ${detail}`;
        barFill.style.width = '100%';
        barFill.classList.add('failed');
    }
    setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 400); }, 3000);
}

// ---- Source List ----
function renderSources() {
    const list = $('#source-list');
    if (state.sources.length === 0) {
        list.innerHTML = '<div class="empty-state">No sources added yet.<br>Upload files or add URLs above.</div>';
        return;
    }

    // Sort newest first
    const sorted = [...state.sources].reverse();
    list.innerHTML = sorted.map((s) => {
        const timeStr = s.added_at ? formatTime(s.added_at) : '';
        const escapedName = s.name.replace(/'/g, "\\'").replace(/"/g, '&quot;');
        return `
        <div class="source-item">
            <div class="icon ${s.type}">${s.type === 'file' ? '📄' : '🔗'}</div>
            <div class="info">
                <div class="name" title="${s.name}">${s.name}</div>
                <div class="meta">${s.chunks} chunks · ${s.type}${timeStr ? ' · ' + timeStr : ''}</div>
            </div>
            <button class="btn-delete-source" onclick="deleteSource('${escapedName}')" title="Delete">&times;</button>
        </div>`;
    }).join('');
}

function formatTime(isoStr) {
    try {
        const d = new Date(isoStr);
        const now = new Date();
        const diffMs = now - d;
        const diffMin = Math.floor(diffMs / 60000);
        if (diffMin < 1) return 'just now';
        if (diffMin < 60) return `${diffMin}m ago`;
        const diffHr = Math.floor(diffMin / 60);
        if (diffHr < 24) return `${diffHr}h ago`;
        const diffDay = Math.floor(diffHr / 24);
        return `${diffDay}d ago`;
    } catch { return ''; }
}

// ---- Chat ----
function initChat() {
    const textarea = $('#chat-input');
    const sendBtn = $('#send-btn');

    sendBtn.addEventListener('click', sendMessage);
    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    });
}

async function sendMessage() {
    const textarea = $('#chat-input');
    const message = textarea.value.trim();
    if (!message || state.sending) return;

    state.sending = true;
    textarea.value = '';
    textarea.style.height = 'auto';
    $('#send-btn').disabled = true;

    // Hide welcome message
    const welcome = $('.welcome-message');
    if (welcome) welcome.style.display = 'none';

    // Add user message
    appendMessage('user', message);

    // Show typing indicator
    $('.typing-indicator').classList.add('active');
    scrollToBottom();

    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
        });
        const data = await resp.json();

        if (!resp.ok) throw new Error(data.detail || 'Chat request failed');

        $('.typing-indicator').classList.remove('active');
        appendMessage('assistant', data.response);
    } catch (err) {
        $('.typing-indicator').classList.remove('active');
        appendMessage('assistant', `Error: ${err.message}`);
        showToast(`Chat error: ${err.message}`, 'error');
    } finally {
        state.sending = false;
        $('#send-btn').disabled = false;
        textarea.focus();
    }
}

function appendMessage(role, content) {
    const container = $('#chat-messages');
    const avatar = role === 'user' ? 'User' : 'AI Agent';
    const formattedContent = formatMarkdown(content);

    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">${formattedContent}</div>
    `;
    container.appendChild(div);
    scrollToBottom();
}

function formatMarkdown(text) {
    // Protect code blocks from other transformations
    const codeBlocks = [];
    text = text.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        const idx = codeBlocks.length;
        codeBlocks.push(`<pre><code class="language-${lang}">${code}</code></pre>`);
        return `\x00CODEBLOCK${idx}\x00`;
    });

    // Markdown tables — extract and protect from paragraph wrapping
    const tables = [];
    text = text.replace(/((?:^\|.+\|$\n?)+)/gm, (tableBlock) => {
        const rows = tableBlock.trim().split('\n').filter(r => r.trim());
        if (rows.length < 2) return tableBlock;
        const parseRow = (row) => row.replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
        const isSeparator = (row) => /^\|?[\s\-:|]+\|?$/.test(row);
        let sepIdx = -1;
        for (let i = 0; i < rows.length; i++) {
            if (isSeparator(rows[i])) { sepIdx = i; break; }
        }
        let html = '<div class="table-wrapper"><table>';
        if (sepIdx === 1) {
            const cells = parseRow(rows[0]);
            html += '<thead><tr>' + cells.map(c => `<th>${c}</th>`).join('') + '</tr></thead>';
            html += '<tbody>';
            for (let i = 2; i < rows.length; i++) {
                if (isSeparator(rows[i])) continue;
                const cells = parseRow(rows[i]);
                html += '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
            }
            html += '</tbody>';
        } else {
            html += '<tbody>';
            for (const row of rows) {
                if (isSeparator(row)) continue;
                const cells = parseRow(row);
                html += '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
            }
            html += '</tbody>';
        }
        html += '</table></div>';
        const idx = tables.length;
        tables.push(html);
        return `\x00TABLE${idx}\x00`;
    });

    // Inline code
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Markdown links [text](url)
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    // Bare URLs → clickable "Source" links (only those not already inside an href or tag)
    let srcCounter = 0;
    text = text.replace(/(^|[^"'>])(https?:\/\/[^\s<,)]+)/g, (_, pre, url) => {
        srcCounter++;
        const label = srcCounter > 1 ? `Source ${srcCounter}` : 'Source';
        return `${pre}<a href="${url}" target="_blank" rel="noopener">${label}</a>`;
    });
    // Bold
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic
    text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Line breaks into paragraphs
    text = text.split('\n\n').map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');

    // Restore protected blocks
    tables.forEach((html, i) => { text = text.replace(`\x00TABLE${i}\x00`, html); });
    codeBlocks.forEach((html, i) => { text = text.replace(`\x00CODEBLOCK${i}\x00`, html); });
    return text;
}

function scrollToBottom() {
    const container = $('#chat-messages');
    container.scrollTop = container.scrollHeight;
}

// ---- MCP Server Management ----
function initMCP() {
    const addBtn = $('#mcp-add-btn');
    addBtn.addEventListener('click', addMCPServer);

    const transportSelect = $('#mcp-transport');
    transportSelect.addEventListener('change', () => {
        const isSSE = transportSelect.value === 'sse';
        $('#mcp-command-group').style.display = isSSE ? 'none' : 'block';
        $('#mcp-args-group').style.display = isSSE ? 'none' : 'block';
        $('#mcp-url-group').style.display = isSSE ? 'block' : 'none';
    });
}

async function addMCPServer() {
    const name = $('#mcp-name').value.trim();
    const transport = $('#mcp-transport').value;

    if (!name) {
        showToast('Server name is required', 'error');
        return;
    }

    const payload = { name, transport };

    if (transport === 'stdio') {
        payload.command = $('#mcp-command').value.trim();
        payload.args = $('#mcp-args').value.trim().split(/\s+/).filter(Boolean);
        if (!payload.command) {
            showToast('Command is required for stdio transport', 'error');
            return;
        }
    } else {
        payload.url = $('#mcp-url').value.trim();
        if (!payload.url) {
            showToast('URL is required for SSE transport', 'error');
            return;
        }
    }

    showToast(`Connecting to ${name}...`, 'info');

    try {
        const resp = await fetch('/api/mcp/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || 'Failed to add server');

        showToast(`✓ MCP server "${name}" connected`, 'success');

        // Clear form
        $('#mcp-name').value = '';
        $('#mcp-command').value = '';
        $('#mcp-args').value = '';
        $('#mcp-url').value = '';

        refreshMCPServers();
        updateStats();
    } catch (err) {
        showToast(`MCP error: ${err.message}`, 'error');
    }
}

async function removeMCPServer(name) {
    try {
        await fetch(`/api/mcp/${encodeURIComponent(name)}`, { method: 'DELETE' });
        showToast(`Removed server "${name}"`, 'info');
        refreshMCPServers();
        updateStats();
    } catch (err) {
        showToast(`Error: ${err.message}`, 'error');
    }
}

async function callMCPTool(serverName, toolName) {
    const argsStr = prompt(`Arguments for ${toolName} (JSON object, e.g. {}):`, '{}');
    if (argsStr === null) return;

    let args;
    try {
        args = JSON.parse(argsStr);
    } catch {
        showToast('Invalid JSON arguments', 'error');
        return;
    }

    showToast(`Calling ${toolName}...`, 'info');

    try {
        const resp = await fetch(`/api/mcp/${encodeURIComponent(serverName)}/call-tool`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tool: toolName, arguments: args }),
        });
        const data = await resp.json();

        // Show result as an assistant message
        const welcome = $('.welcome-message');
        if (welcome) welcome.style.display = 'none';

        appendMessage('assistant', `**MCP Tool Result (${toolName}):**\n\n${data.result}`);
        showToast(`✓ Tool "${toolName}" executed`, 'success');
    } catch (err) {
        showToast(`Tool error: ${err.message}`, 'error');
    }
}

async function refreshMCPServers() {
    try {
        const resp = await fetch('/api/mcp/servers');
        const data = await resp.json();
        renderMCPServers(data.servers);
    } catch (err) {
        console.error('Failed to refresh MCP servers', err);
    }
}

function renderMCPServers(servers) {
    const list = $('#mcp-server-list');
    if (!servers || servers.length === 0) {
        list.innerHTML = '<div class="empty-state">No MCP servers connected.</div>';
        return;
    }

    list.innerHTML = servers.map(s => `
        <div class="mcp-server-item">
            <div class="server-header">
                <span class="server-name">${s.name}</span>
                <div>
                    <span class="server-transport">${s.transport}</span>
                    <button class="btn btn-danger btn-sm" onclick="removeMCPServer('${s.name}')" style="margin-left:6px">✕</button>
                </div>
            </div>
            <div class="server-tools">
                ${s.tools && s.tools.length > 0
                    ? '<strong>Tools:</strong> ' + s.tools.map(t =>
                        `<span class="tool-tag" style="cursor:pointer" onclick="callMCPTool('${s.name}', '${t.name}')" title="${t.description || ''}">${t.name}</span>`
                    ).join('')
                    : '<span style="color:var(--text-muted)">No tools discovered</span>'
                }
            </div>
        </div>
    `).join('');
}

// ---- LLM Provider Switcher ----
function initProvider() {
    $$('.provider-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const provider = btn.dataset.provider;
            try {
                const resp = await fetch('/api/provider', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider }),
                });
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.detail || 'Failed to switch provider');
                updateProviderUI(data.provider);
                showToast(`Switched to ${data.provider === 'openai' ? 'OpenAI' : 'Groq'}`, 'success');
            } catch (err) {
                showToast(`Provider error: ${err.message}`, 'error');
            }
        });
    });
    loadProvider();
}

async function loadProvider() {
    try {
        const resp = await fetch('/api/provider');
        const data = await resp.json();
        updateProviderUI(data.provider);
    } catch (err) {
        console.error('Failed to load provider', err);
    }
}

function updateProviderUI(provider) {
    $$('.provider-btn').forEach(b => b.classList.remove('active'));
    const btn = $(`#provider-${provider}`);
    if (btn) btn.classList.add('active');
    const stat = $('#stat-provider');
    if (stat) stat.textContent = provider;
}

// ---- Stats ----
async function updateStats() {
    try {
        const resp = await fetch('/api/stats');
        const data = await resp.json();
        $('#stat-chunks').textContent = data.document_chunks;
        $('#stat-messages').textContent = data.conversation_length;
        $('#stat-mcp').textContent = data.mcp_servers;
        if (data.llm_provider) updateProviderUI(data.llm_provider);
    } catch (err) {
        console.error('Failed to update stats', err);
    }
}

// ---- Clear Actions ----
function initActions() {
    $('#clear-chat-btn').addEventListener('click', async () => {
        if (!confirm('Clear the conversation history?')) return;
        try {
            await fetch('/api/clear-chat', { method: 'POST' });
            $('#chat-messages').innerHTML = '';
            const welcome = $('.welcome-message');
            if (welcome) welcome.style.display = '';
            // Re-add welcome
            location.reload();
        } catch (err) {
            showToast(`Error: ${err.message}`, 'error');
        }
    });

    $('#clear-all-btn').addEventListener('click', async () => {
        if (!confirm('This will clear ALL documents, URLs, chat history, and MCP connections. Continue?')) return;
        try {
            await fetch('/api/clear', { method: 'POST' });
            state.sources = [];
            renderSources();
            updateStats();
            location.reload();
        } catch (err) {
            showToast(`Error: ${err.message}`, 'error');
        }
    });
}

// ---- View All Sources Modal ----
function initSourcesModal() {
    const btn = $('#view-all-sources-btn');
    const modal = $('#sources-modal');
    const closeBtn = $('#close-sources-modal');

    btn.addEventListener('click', () => {
        renderSourcesModal();
        modal.style.display = 'flex';
    });

    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.style.display = 'none';
    });
}

function renderSourcesModal() {
    const body = $('#sources-modal-body');
    if (state.sources.length === 0) {
        body.innerHTML = '<div class="empty-state">No documents or URLs have been added yet.</div>';
        return;
    }

    const sorted = [...state.sources].reverse();
    body.innerHTML = sorted.map((s) => {
        const timeStr = s.added_at ? formatTime(s.added_at) : '';
        const urlLine = s.url ? `<div class="meta" style="margin-top:1px"><a href="${s.url}" target="_blank" rel="noopener" style="color:var(--accent);text-decoration:none;font-size:0.72rem">${s.url}</a></div>` : '';
        const escapedName = s.name.replace(/'/g, "\\'").replace(/"/g, '&quot;');
        return `
        <div class="modal-source-item">
            <div class="icon ${s.type}">${s.type === 'file' ? '📄' : '🔗'}</div>
            <div class="info">
                <div class="name" title="${s.name}">${s.name}</div>
                <div class="meta">${s.chunks} chunks · ${s.type}${timeStr ? ' · ' + timeStr : ''}</div>
                ${urlLine}
            </div>
            <button class="btn-delete-source" onclick="deleteSource('${escapedName}')" title="Delete">&times;</button>
        </div>`;
    }).join('');
}

// ---- Delete Source ----
async function deleteSource(name) {
    if (!confirm(`Delete "${name}" and its chunks?`)) return;
    try {
        const resp = await fetch(`/api/source/${encodeURIComponent(name)}`, { method: 'DELETE' });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || 'Delete failed');
        state.sources = state.sources.filter(s => s.name !== name);
        renderSources();
        renderSourcesModal();
        updateStats();
        showToast(`Deleted "${name}"`, 'success');
    } catch (err) {
        showToast(`Delete error: ${err.message}`, 'error');
    }
}

// ---- Welcome Card Clicks ----
function initWelcomeCards() {
    $$('.welcome-card').forEach(card => {
        card.addEventListener('click', () => {
            const action = card.dataset.action;
            if (action === 'upload') {
                // Switch to documents tab
                $$('.sidebar-tab')[0].click();
                $('#file-input').click();
            } else if (action === 'url') {
                $$('.sidebar-tab')[0].click();
                $('#url-input').focus();
            } else if (action === 'mcp') {
                $$('.sidebar-tab')[1].click();
            } else if (action === 'ask') {
                $('#chat-input').focus();
            }
        });
    });
}

// ---- Load Persisted Chat History ----
async function loadChatHistory() {
    try {
        const resp = await fetch('/api/chat-history');
        const data = await resp.json();
        if (data.history && data.history.length > 0) {
            const welcome = $('.welcome-message');
            if (welcome) welcome.style.display = 'none';
            for (const msg of data.history) {
                appendMessage(msg.role, msg.content);
            }
        }
    } catch (err) {
        console.error('Failed to load chat history', err);
    }
}

// ---- Load Persisted Sources ----
async function loadSources() {
    try {
        const resp = await fetch('/api/sources');
        const data = await resp.json();
        if (data.sources && data.sources.length > 0) {
            state.sources = data.sources;
            renderSources();
        }
    } catch (err) {
        console.error('Failed to load sources', err);
    }
}

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initUpload();
    initURLInput();
    initChat();
    initMCP();
    initActions();
    initProvider();
    initWelcomeCards();
    initSourcesModal();
    loadSources();
    loadChatHistory();
    refreshMCPServers();
    updateStats();
});
