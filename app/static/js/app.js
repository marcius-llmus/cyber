let filesCount = 0;

// Fix for Alpine "currentPromptTab is not defined" error
window.currentPromptTab = localStorage.getItem('currentPromptTab') || 'global';

document.addEventListener('alpine:init', () => {
    Alpine.store('appearance', {
        bgColor: localStorage.getItem('bgColor') || '#121212',
        bgSecondaryColor: localStorage.getItem('bgSecondaryColor') || '#1E1E1E',
        bgLightColor: localStorage.getItem('bgLightColor') || '#2D2D2D',
        bgCardColor: localStorage.getItem('bgCardColor') || '#252525',
        textColor: localStorage.getItem('textColor') || '#e0e0e0',
        primaryColor: localStorage.getItem('primaryColor') || '#FF8A3D',
        primaryDarkColor: localStorage.getItem('primaryDarkColor') || 'rgba(180, 90, 45, 0.7)',
        primaryLightColor: localStorage.getItem('primaryLightColor') || '#FF8A3D',
        uiFontSize: localStorage.getItem('uiFontSize') || '14',
        editorFontSize: localStorage.getItem('editorFontSize') || '14',
        highlightTheme: localStorage.getItem('highlightTheme') || 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css',

        init() {
            // Apply initial highlight theme
            const themeLink = document.getElementById('highlight-theme-link');
            if (themeLink) themeLink.href = this.highlightTheme;
        },

        updateSetting(key, val) {
            this[key] = val;
            localStorage.setItem(key, val);
        },

        setHighlightTheme(val) {
            this.highlightTheme = val;
            localStorage.setItem('highlightTheme', val);
            const themeLink = document.getElementById('highlight-theme-link');
            if (themeLink) themeLink.href = val;
        }
    });
});

function preProcessMarkdown(text) {
    if (!text) return text;

    const lines = text.split('\n');
    const newLines = [...lines];

    function getFence(line) {
        const match = line.match(/^([\s]*)(`{3,})(.*)$/);
        if (!match) return null;
        return {
            prefix: match[1],
            ticks: match[2].length,
            info: match[3].trim(),
            rawInfo: match[3],
            hasDiffMarker: /^[\+\-]/.test(line)
        };
    }

    function isRealFence(fence, insideDiff) {
        if (!fence) return false;
        if (insideDiff && fence.hasDiffMarker) return false;
        return true;
    }

    function isContainer(info) {
        const mode = info.split(/\s+/)[0].toLowerCase();
        return ['markdown', 'md', 'diff'].includes(mode);
    }

    function hasMoreFences(lines, startIndex, insideDiff) {
        for (let k = startIndex + 1; k < lines.length; k++) {
            const f = getFence(lines[k]);
            if (isRealFence(f, insideDiff)) return true;
        }
        return false;
    }

    for (let i = 0; i < lines.length; i++) {
        const openFence = getFence(lines[i]);
        if (!openFence || !openFence.info || openFence.hasDiffMarker) continue;

        const isDiffBlock = openFence.info.toLowerCase() === 'diff';
        const isContainerBlock = isContainer(openFence.info);

        let stack = 1;
        let maxInnerTicks = 0;
        let closeIndex = -1;

        for (let j = i + 1; j < lines.length; j++) {
            const current = getFence(lines[j]);
            if (!isRealFence(current, isDiffBlock)) continue;

            if (current.info) {
                stack++;
            } else {
                if (stack > 1) {
                    stack--;
                } else if (stack === 1) {
                    if (isContainerBlock) {
                        if (hasMoreFences(lines, j, isDiffBlock)) {
                            stack++;
                        } else {
                            stack--;
                        }
                    } else {
                        stack--;
                    }
                }
            }

            if (stack > 0 && current.ticks > maxInnerTicks) {
                maxInnerTicks = current.ticks;
            }

            if (stack === 0) {
                closeIndex = j;
                break;
            }
        }

        if (closeIndex !== -1) {
            const newFenceLength = Math.max(3, maxInnerTicks + 1);
            const newFence = '`'.repeat(newFenceLength);

            newLines[i] = `${openFence.prefix}${newFence}${openFence.rawInfo}`;

            const closeFence = getFence(lines[closeIndex]);
            newLines[closeIndex] = `${closeFence.prefix}${newFence}`;

            i = closeIndex;
        }
    }

    return newLines.join('\n');
}

// Global Markdown Renderer
window.renderMarkdown = function (rawId) {
    const rawEl = document.getElementById(rawId);
    if (!rawEl) return;

    // Extract ID suffix (remove 'raw-')
    const id = rawId.substring(4);
    const targetEl = document.getElementById(`rendered-${id}`);

    if (targetEl && rawEl) {
        const processedText = preProcessMarkdown(rawEl.textContent);
        targetEl.innerHTML = md.render(processedText);
        // Re-highlight code blocks after render
        targetEl.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });

        // Inject Copy Buttons
        targetEl.querySelectorAll('pre').forEach((pre) => {
            // Wrap pre in a relative container
            const wrapper = document.createElement('div');
            wrapper.className = 'code-block-wrapper group';
            pre.parentNode.insertBefore(wrapper, pre);
            wrapper.appendChild(pre);

            // Add Copy Button
            const btn = document.createElement('button');
            btn.className = 'copy-code-btn opacity-0 group-hover:opacity-100 transition-opacity duration-200';
            btn.innerHTML = '<i class="fas fa-copy mr-1"></i>Copy';
            btn.onclick = () => copyCodeBlock(btn, pre.innerText);
            wrapper.appendChild(btn);
        });
    }
};

function scrollToBottom() {
    const messageList = document.getElementById('message-list');
    if (messageList) {
        requestAnimationFrame(() => {
            messageList.scrollTop = messageList.scrollHeight;
        });
    }
}

// Observer for Streaming & Dynamic Content
const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
        // Handle text updates (Streaming)
        if (mutation.type === 'characterData' || mutation.type === 'childList') {
            let target = mutation.target;
            if (target.nodeType === 3) target = target.parentElement; // Text node -> Element

            if (target && target.id && target.id.startsWith('raw-')) {
                window.renderMarkdown(target.id);
                scrollToBottom();
            }
        }
    }
});

function copyCodeBlock(button, text) {
    navigator.clipboard.writeText(text).then(() => {
        const originalHtml = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check mr-1"></i>Copied!';
        setTimeout(() => {
            button.innerHTML = originalHtml;
        }, 2000);
    });
}

function clearHistory() {
    addLog('History cleared', 'blue');
    document.getElementById('history-modal').classList.remove('active');
}

function saveSettings() {
    addLog('Settings saved successfully', 'green');
}

function initializeFileTree() {
    document.querySelectorAll('.tree-toggle').forEach(toggle => {
        toggle.addEventListener('click', function (e) {
            e.stopPropagation();
            const item = this.closest('.tree-item');
            item.classList.toggle('open');
            this.classList.toggle('rotate-90');
        });
    });

    document.querySelectorAll('.folder-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function (e) {
            e.stopPropagation();
            const item = this.closest('.tree-item');
            const childCheckboxes = item.querySelectorAll('input[type="checkbox"]');
            childCheckboxes.forEach(child => {
                child.checked = this.checked;
            });
        });
    });
}

function expandAllFolders() {
    document.querySelectorAll('.tree-item').forEach(item => item.classList.add('open'));
    document.querySelectorAll('.tree-toggle').forEach(toggle => toggle.classList.add('rotate-90'));
}

function collapseAllFolders() {
    document.querySelectorAll('.tree-item').forEach(item => item.classList.remove('open'));
    document.querySelectorAll('.tree-toggle').forEach(toggle => toggle.classList.remove('rotate-90'));
}

function removeContextFile(button) {
    button.closest('div').remove();
    filesCount--;
    document.getElementById('files-count').textContent = filesCount;
    const contextContainer = document.getElementById('context-files-container');
    if (contextContainer.children.length === 0) {
        contextContainer.innerHTML = '<div class="text-xs text-gray-500 text-center py-6">No files loaded</div>';
    }
}

function clearContextFiles() {
    document.getElementById('context-files-container').innerHTML = '<div class="text-xs text-gray-500 text-center py-6">No files loaded</div>';
    filesCount = 0;
    document.getElementById('files-count').textContent = filesCount;
    addLog('Context files cleared', 'blue');
}

function handleKeydown(event) {
    if (event.key === 'Enter' && event.ctrlKey) {
        event.preventDefault();
        const form = event.target.form;
        if (form) {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) submitButton.click();
        }
    }
}

function addLog(message, color) {
    const logsContainer = document.getElementById('logs-container');
    if (logsContainer.querySelector('.text-center')) {
        logsContainer.innerHTML = '';
    }

    const logEntry = document.createElement('div');
    logEntry.className = `p-2 rounded-md bg-dark-card hover:bg-dark-light border-l-2 border-${color}-500 my-1 text-xs`;
    const messageDiv = document.createElement('div');
    messageDiv.className = 'text-gray-300';
    messageDiv.textContent = message;
    const timestampDiv = document.createElement('div');
    timestampDiv.className = 'text-gray-500 text-[10px] mt-0.5';
    timestampDiv.textContent = new Date().toLocaleTimeString();
    logEntry.append(messageDiv, timestampDiv);
    logsContainer.insertBefore(logEntry, logsContainer.firstChild);

    if (logsContainer.children.length > 30) {
        logsContainer.removeChild(logsContainer.lastChild);
    }
}

function clearLogs() {
    document.getElementById('logs-container').innerHTML = '<div class="text-xs text-gray-500 text-center py-6">No logs yet</div>';
}

// Initialize Observer on the Message List
function initMarkdownObserver() {
    const container = document.getElementById('message-list');
    if (container) {
        observer.observe(container, {
            subtree: true, childList: true, characterData: true
        });
    }
}

// Initial Scan & Setup
document.addEventListener('DOMContentLoaded', () => {
    // Scan existing history
    document.querySelectorAll('[id^="raw-"]').forEach(el => {
        window.renderMarkdown(el.id);
    });

    // Start observing
    initMarkdownObserver();
});

document.body.addEventListener('settingsSaved', saveSettings);

// Re-init observer if message list is swapped (e.g. clear chat)
document.body.addEventListener('htmx:afterSettle', (evt) => {
    if (evt.target.id === 'message-list' || evt.target.querySelector('#message-list')) {
        initMarkdownObserver();
        // Re-scan for new content
        document.querySelectorAll('[id^="raw-"]').forEach(el => {
            window.renderMarkdown(el.id);
        });
    }
});

document.body.addEventListener('htmx:responseError', function (event) {
    let message = 'An unexpected error occurred.';
    try {
        // FastAPI exceptions often have a 'detail' key.
        const errorData = JSON.parse(event.detail.xhr.responseText);
        message = errorData.detail || event.detail.xhr.statusText;
    } catch (e) {
        // Fallback for non-JSON or malformed responses.
        message = event.detail.xhr.statusText || 'Server error.';
    }

    window.dispatchEvent(new CustomEvent('show-error-toast', {
        detail: {
            message: message
        }
    }));
});

document.body.addEventListener('click', function (event) {
    const openButton = event.target.closest('[data-modal-open]');
    const closeButton = event.target.closest('[data-modal-close]');

    if (openButton) {
        const modalId = openButton.getAttribute('data-modal-open');
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            if (modalId === 'file-selection-modal') {
                initializeFileTree();
            }
        }
    } else if (closeButton) {
        const modal = closeButton.closest('.modal-overlay');
        if (modal) {
            modal.classList.remove('active');
        }
    }
});