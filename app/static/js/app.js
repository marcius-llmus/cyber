/**
 * Llama Coding - Main Application Logic
**/
class ChatApp {
    static init() {
        this.filesCount = 0;
        this.setupAlpine();
        this.setupMarkdownRenderer();
        this.setupObservers();
        this.setupEventListeners();
        
        // Initial scan for existing markdown content
        document.addEventListener('DOMContentLoaded', () => {
            this.scanAndRenderMarkdown();
        });
    }

    static setupAlpine() {
        // Fix for Alpine "currentPromptTab is not defined" error
        window.currentPromptTab = localStorage.getItem('currentPromptTab') || 'global';

        document.addEventListener('alpine:init', () => {
            const defaults = {
                bgColor: '#121212',
                bgSecondaryColor: '#1E1E1E',
                bgLightColor: '#2D2D2D',
                bgCardColor: '#252525',
                bgDarkerColor: '#000000',
                textColor: '#e0e0e0',
                primaryColor: '#FF8A3D',
                primaryDarkColor: '#B45A2D',
                primaryLightColor: '#FF8A3D',
                uiFontSize: '14',
                editorFontSize: '14',
                highlightTheme: 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css'
            };

            Alpine.store('appearance', {
                bgColor: localStorage.getItem('bgColor') || defaults.bgColor,
                bgSecondaryColor: localStorage.getItem('bgSecondaryColor') || defaults.bgSecondaryColor,
                bgLightColor: localStorage.getItem('bgLightColor') || defaults.bgLightColor,
                bgCardColor: localStorage.getItem('bgCardColor') || defaults.bgCardColor,
                bgDarkerColor: localStorage.getItem('bgDarkerColor') || defaults.bgDarkerColor,
                textColor: localStorage.getItem('textColor') || defaults.textColor,
                primaryColor: localStorage.getItem('primaryColor') || defaults.primaryColor,
                primaryDarkColor: localStorage.getItem('primaryDarkColor') || defaults.primaryDarkColor,
                primaryLightColor: localStorage.getItem('primaryLightColor') || defaults.primaryLightColor,
                uiFontSize: localStorage.getItem('uiFontSize') || defaults.uiFontSize,
                editorFontSize: localStorage.getItem('editorFontSize') || defaults.editorFontSize,
                highlightTheme: localStorage.getItem('highlightTheme') || defaults.highlightTheme,

                init() {
                    const themeLink = document.getElementById('highlight-theme-link');
                    if (themeLink) themeLink.href = this.highlightTheme;
                },

                updateSetting(key, val) {
                    this[key] = val;
                    localStorage.setItem(key, val);
                },

                reset() {
                    Object.keys(defaults).forEach(key => {
                        this.updateSetting(key, defaults[key]);
                    });
                    
                    // Manually trigger theme link update as updateSetting handles localStorage but init handles link
                    const themeLink = document.getElementById('highlight-theme-link');
                    if (themeLink) themeLink.href = defaults.highlightTheme;
                    
                    ChatApp.addLog('Appearance settings reset to defaults', 'blue');
                    window.dispatchEvent(new CustomEvent('settingsSaved'));
                }
            });
        });
    }

    static setupMarkdownRenderer() {
        // Expose render function globally for HTMX/Observer usage
        window.renderMarkdown = (rawId) => this.renderMarkdown(rawId);
    }

    static renderMarkdown(rawId) {
        const rawEl = document.getElementById(rawId);
        if (!rawEl) return;

        const id = rawId.substring(4); // remove 'raw-'
        const targetEl = document.getElementById(`rendered-${id}`);

        if (targetEl && rawEl) {
            const processedText = MarkdownProcessor.preProcess(rawEl.textContent);
            targetEl.innerHTML = md.render(processedText);
            
            // Highlight code blocks
            targetEl.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });

            // Inject UI components (Copy buttons)
            this.injectCodeControls(targetEl);
        }
    }

    static injectCodeControls(targetEl) {
        targetEl.querySelectorAll('pre').forEach((pre) => {
            const wrapper = document.createElement('div');
            wrapper.className = 'code-block-wrapper group';
            pre.parentNode.insertBefore(wrapper, pre);
            wrapper.appendChild(pre);

            const btn = document.createElement('button');
            btn.className = 'copy-code-btn opacity-0 group-hover:opacity-100 transition-opacity duration-200';
            btn.innerHTML = '<i class="fas fa-copy mr-1"></i>Copy';
            btn.onclick = () => this.copyCodeBlock(btn, pre.innerText);
            wrapper.appendChild(btn);
        });
    }

    static copyCodeBlock(button, text) {
        navigator.clipboard.writeText(text).then(() => {
            const originalHtml = button.innerHTML;
            button.innerHTML = '<i class="fas fa-check mr-1"></i>Copied!';
            setTimeout(() => button.innerHTML = originalHtml, 2000);
        });
    }

    static setupObservers() {
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (mutation.type === 'characterData' || mutation.type === 'childList') {
                    let target = mutation.target;
                    if (target.nodeType === 3) target = target.parentElement;
                    if (target && target.id && target.id.startsWith('raw-')) {
                        this.renderMarkdown(target.id);
                        this.scrollToBottom();
                    }
                }
            }
        });

        const container = document.getElementById('message-list');
        if (container) {
            observer.observe(container, { subtree: true, childList: true, characterData: true });
        }

        // Re-attach on HTMX swaps
        document.body.addEventListener('htmx:afterSettle', (evt) => {
            if (evt.target.id === 'message-list' || evt.target.querySelector('#message-list')) {
                observer.observe(document.getElementById('message-list'), { 
                    subtree: true, childList: true, characterData: true 
                });
                this.scanAndRenderMarkdown();
            }
        });
    }

    static scanAndRenderMarkdown() {
        document.querySelectorAll('[id^="raw-"]').forEach(el => {
            this.renderMarkdown(el.id);
        });
    }

    static scrollToBottom() {
        const messageList = document.getElementById('message-list');
        if (messageList) {
            requestAnimationFrame(() => {
                messageList.scrollTop = messageList.scrollHeight;
            });
        }
    }

    static setupEventListeners() {
        document.body.addEventListener('settingsSaved', () => this.addLog('Settings saved successfully', 'green'));
        
        // Modal Logic
        document.body.addEventListener('click', (event) => {
            const openButton = event.target.closest('[data-modal-open]');
            const closeButton = event.target.closest('[data-modal-close]');

            if (openButton) {
                const modal = document.getElementById(openButton.getAttribute('data-modal-open'));
                if (modal) {
                    modal.classList.add('active');
                    if (modal.id === 'file-selection-modal') this.initializeFileTree();
                }
            } else if (closeButton) {
                const modal = closeButton.closest('.modal-overlay');
                if (modal) modal.classList.remove('active');
            }
        });

        // Error Handling
        document.body.addEventListener('htmx:responseError', (event) => {
            let message = 'An unexpected error occurred.';
            try {
                const errorData = JSON.parse(event.detail.xhr.responseText);
                message = errorData.detail || event.detail.xhr.statusText;
            } catch (e) {
                message = event.detail.xhr.statusText || 'Server error.';
            }
            window.dispatchEvent(new CustomEvent('show-error-toast', { detail: { message: message } }));
        });
    }

    static addLog(message, color) {
        const logsContainer = document.getElementById('logs-container');
        if (!logsContainer) return;
        if (logsContainer.querySelector('.text-center')) logsContainer.innerHTML = '';

        const logEntry = document.createElement('div');
        logEntry.className = `p-2 rounded-md bg-dark-card hover:bg-dark-light border-l-2 border-${color}-500 my-1 text-xs`;
        logEntry.innerHTML = `<div class="text-gray-300">${message}</div><div class="text-gray-500 text-[10px] mt-0.5">${new Date().toLocaleTimeString()}</div>`;
        
        logsContainer.insertBefore(logEntry, logsContainer.firstChild);
        if (logsContainer.children.length > 30) logsContainer.removeChild(logsContainer.lastChild);
    }

    static initializeFileTree() {
        document.querySelectorAll('.tree-toggle').forEach(toggle => {
            toggle.onclick = (e) => {
                e.stopPropagation();
                const item = toggle.closest('.tree-item');
                item.classList.toggle('open');
                toggle.classList.toggle('rotate-90');
            };
        });
    }
}

/**
 * Markdown Processing Logic
 * Handles nested fences and raw text normalization.
 */
class MarkdownProcessor {
    static preProcess(text) {
        if (!text) return text;
        const lines = text.split('\n');
        const newLines = [...lines];

        const getFence = (line) => {
            const match = line.match(/^([\s]*)(`{3,})(.*)$/);
            return match ? { prefix: match[1], ticks: match[2].length, info: match[3].trim(), rawInfo: match[3], hasDiffMarker: /^[\+\-]/.test(line) } : null;
        };

        const isRealFence = (fence, insideDiff) => fence && !(insideDiff && fence.hasDiffMarker);
        const isContainer = (info) => ['markdown', 'md', 'diff'].includes(info.split(/\s+/)[0].toLowerCase());
        
        const hasMoreFences = (lines, start, insideDiff) => {
            for (let k = start + 1; k < lines.length; k++) {
                if (isRealFence(getFence(lines[k]), insideDiff)) return true;
            }
            return false;
        };

        for (let i = 0; i < lines.length; i++) {
            const openFence = getFence(lines[i]);
            if (!openFence || !openFence.info || openFence.hasDiffMarker) continue;

            const isDiffBlock = openFence.info.toLowerCase() === 'diff';
            const isContainerBlock = isContainer(openFence.info);
            let stack = 1, maxInnerTicks = 0, closeIndex = -1;

            for (let j = i + 1; j < lines.length; j++) {
                const current = getFence(lines[j]);
                if (!isRealFence(current, isDiffBlock)) continue;

                if (current.info) stack++;
                else {
                    if (stack > 1) stack--;
                    else if (stack === 1) {
                        if (isContainerBlock) hasMoreFences(lines, j, isDiffBlock) ? stack++ : stack--;
                        else stack--;
                    }
                }

                if (stack > 0 && current.ticks > maxInnerTicks) maxInnerTicks = current.ticks;
                if (stack === 0) { closeIndex = j; break; }
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
}

// Legacy global helpers for HTML event attributes (onclick, etc.)
window.handleKeydown = (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
        e.preventDefault();
        const btn = e.target.form?.querySelector('button[type="submit"]');
        if (btn) btn.click();
    }
};
window.clearLogs = () => document.getElementById('logs-container').innerHTML = '<div class="text-xs text-gray-500 text-center py-6">No logs yet</div>';
window.clearHistory = () => { ChatApp.addLog('History cleared', 'blue'); document.getElementById('history-modal').classList.remove('active'); };
window.removeContextFile = (btn) => {
    btn.closest('div').remove();
    ChatApp.filesCount = Math.max(0, ChatApp.filesCount - 1);
    document.getElementById('files-count').textContent = ChatApp.filesCount;
    if (document.getElementById('context-files-container').children.length === 0) {
        document.getElementById('context-files-container').innerHTML = '<div class="text-xs text-gray-500 text-center py-6">No files loaded</div>';
    }
};
window.clearContextFiles = () => {
    document.getElementById('context-files-container').innerHTML = '<div class="text-xs text-gray-500 text-center py-6">No files loaded</div>';
    ChatApp.filesCount = 0;
    document.getElementById('files-count').textContent = 0;
    ChatApp.addLog('Context files cleared', 'blue');
};
window.expandAllFolders = () => {
    document.querySelectorAll('.tree-item').forEach(item => item.classList.add('open'));
    document.querySelectorAll('.tree-toggle').forEach(toggle => toggle.classList.add('rotate-90'));
};
window.collapseAllFolders = () => {
    document.querySelectorAll('.tree-item').forEach(item => item.classList.remove('open'));
    document.querySelectorAll('.tree-toggle').forEach(toggle => toggle.classList.remove('rotate-90'));
};

// Ignite
ChatApp.init();