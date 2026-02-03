const Action = {
    CLEAR_LOGS: 'clear-logs',
    CLEAR_SESSIONS: 'clear-sessions',
    EXPAND_FOLDERS: 'expand-all-folders',
    COLLAPSE_FOLDERS: 'collapse-all-folders',
    TOGGLE_FOLDER: 'toggle-folder',
    TOGGLE_EXPANDABLE: 'toggle-expandable'
};

class ChatApp {
    static init() {
        this.autoScrollEnabled = true;
        this.ignoreScrollEvents = false;
        this.setupAlpine();
        this.setupMarkdownRenderer();
        this.setupObservers();
        this.setupEventListeners();
        this.setupTreeStatePreservation();
        
        // Initial scan for existing markdown content
        document.addEventListener('DOMContentLoaded', () => {
            this.scanAndRenderMarkdown();
            this.highlightExistingCodeBlocks();
            this.scrollToBottom();
            this.setupScrollHandler();
        });
    }

    static setupAlpine() {
        window.currentPromptTab = localStorage.getItem('currentPromptTab') || 'global';

        document.addEventListener('alpine:init', () => {
            const availableThemes = [
                // Root Themes
                '1c-light', 'a11y-dark', 'a11y-light', 'agate', 'an-old-hope', 'androidstudio', 'arduino-light', 'arta', 'ascetic',
                'atom-one-dark-reasonable', 'atom-one-dark', 'atom-one-light', 'brown-paper', 'codepen-embed', 'color-brewer',
                'cybertopia-cherry', 'cybertopia-dimmer', 'cybertopia-icecap', 'cybertopia-saturated', 'dark', 'default', 'devibeans',
                'docco', 'far', 'felipec', 'foundation', 'github-dark-dimmed', 'github-dark', 'github', 'gml', 'googlecode',
                'gradient-dark', 'gradient-light', 'grayscale', 'hybrid', 'idea', 'intellij-light', 'ir-black', 'isbl-editor-dark',
                'isbl-editor-light', 'kimbie-dark', 'kimbie-light', 'lightfair', 'lioshi', 'magula', 'mono-blue', 'monokai-sublime',
                'monokai', 'night-owl', 'nnfx-dark', 'nnfx-light', 'nord', 'obsidian', 'panda-syntax-dark', 'panda-syntax-light',
                'paraiso-dark', 'paraiso-light', 'pojoaque', 'purebasic', 'qtcreator-dark', 'qtcreator-light', 'rainbow',
                'rose-pine-dawn', 'rose-pine-moon', 'rose-pine', 'routeros', 'school-book', 'shades-of-purple', 'srcery',
                'stackoverflow-dark', 'stackoverflow-light', 'sunburst', 'tokyo-night-dark', 'tokyo-night-light',
                'tomorrow-night-blue', 'tomorrow-night-bright', 'vs', 'vs2015', 'xcode', 'xt256',

                // Base16 Themes
                'base16/3024', 'base16/apathy', 'base16/apprentice', 'base16/ashes', 'base16/atelier-cave-light', 'base16/atelier-cave',
                'base16/atelier-dune-light', 'base16/atelier-dune', 'base16/atelier-estuary-light', 'base16/atelier-estuary',
                'base16/atelier-forest-light', 'base16/atelier-forest', 'base16/atelier-heath-light', 'base16/atelier-heath',
                'base16/atelier-lakeside-light', 'base16/atelier-lakeside', 'base16/atelier-plateau-light', 'base16/atelier-plateau',
                'base16/atelier-savanna-light', 'base16/atelier-savanna', 'base16/atelier-seaside-light', 'base16/atelier-seaside',
                'base16/atelier-sulphurpool-light', 'base16/atelier-sulphurpool', 'base16/atlas', 'base16/bespin',
                'base16/black-metal-bathory', 'base16/black-metal-burzum', 'base16/black-metal-dark-funeral', 'base16/black-metal-gorgoroth',
                'base16/black-metal-immortal', 'base16/black-metal-khold', 'base16/black-metal-marduk', 'base16/black-metal-mayhem',
                'base16/black-metal-nile', 'base16/black-metal-venom', 'base16/black-metal', 'base16/brewer', 'base16/bright',
                'base16/brogrammer', 'base16/brush-trees-dark', 'base16/brush-trees', 'base16/chalk', 'base16/circus',
                'base16/classic-dark', 'base16/classic-light', 'base16/codeschool', 'base16/colors', 'base16/cupcake', 'base16/cupertino',
                'base16/danqing', 'base16/darcula', 'base16/dark-violet', 'base16/darkmoss', 'base16/darktooth', 'base16/decaf',
                'base16/default-dark', 'base16/default-light', 'base16/dirtysea', 'base16/dracula', 'base16/edge-dark', 'base16/edge-light',
                'base16/eighties', 'base16/embers', 'base16/equilibrium-dark', 'base16/equilibrium-gray-dark', 'base16/equilibrium-gray-light',
                'base16/equilibrium-light', 'base16/espresso', 'base16/eva-dim', 'base16/eva', 'base16/flat', 'base16/framer',
                'base16/fruit-soda', 'base16/gigavolt', 'base16/github', 'base16/google-dark', 'base16/google-light',
                'base16/grayscale-dark', 'base16/grayscale-light', 'base16/green-screen', 'base16/gruvbox-dark-hard',
                'base16/gruvbox-dark-medium', 'base16/gruvbox-dark-pale', 'base16/gruvbox-dark-soft', 'base16/gruvbox-light-hard',
                'base16/gruvbox-light-medium', 'base16/gruvbox-light-soft', 'base16/hardcore', 'base16/harmonic16-dark',
                'base16/harmonic16-light', 'base16/heetch-dark', 'base16/heetch-light', 'base16/helios', 'base16/hopscotch',
                'base16/horizon-dark', 'base16/horizon-light', 'base16/humanoid-dark', 'base16/humanoid-light', 'base16/ia-dark',
                'base16/ia-light', 'base16/icy-dark', 'base16/ir-black', 'base16/isotope', 'base16/kimber', 'base16/london-tube',
                'base16/macintosh', 'base16/marrakesh', 'base16/materia', 'base16/material-darker', 'base16/material-lighter',
                'base16/material-palenight', 'base16/material-vivid', 'base16/material', 'base16/mellow-purple', 'base16/mexico-light',
                'base16/mocha', 'base16/monokai', 'base16/nebula', 'base16/nord', 'base16/nova', 'base16/ocean', 'base16/oceanicnext',
                'base16/one-light', 'base16/onedark', 'base16/outrun-dark', 'base16/papercolor-dark', 'base16/papercolor-light',
                'base16/paraiso', 'base16/pasque', 'base16/phd', 'base16/pico', 'base16/pop', 'base16/porple', 'base16/qualia',
                'base16/railscasts', 'base16/rebecca', 'base16/ros-pine-dawn', 'base16/ros-pine-moon', 'base16/ros-pine',
                'base16/sagelight', 'base16/sandcastle', 'base16/seti-ui', 'base16/shapeshifter', 'base16/silk-dark', 'base16/silk-light',
                'base16/snazzy', 'base16/solar-flare-light', 'base16/solar-flare', 'base16/solarized-dark', 'base16/solarized-light',
                'base16/spacemacs', 'base16/summercamp', 'base16/summerfruit-dark', 'base16/summerfruit-light',
                'base16/synth-midnight-terminal-dark', 'base16/synth-midnight-terminal-light', 'base16/tango', 'base16/tender',
                'base16/tomorrow-night', 'base16/tomorrow', 'base16/twilight', 'base16/unikitty-dark', 'base16/unikitty-light',
                'base16/vulcan', 'base16/windows-10-light', 'base16/windows-10', 'base16/windows-95-light', 'base16/windows-95',
                'base16/windows-high-contrast-light', 'base16/windows-high-contrast', 'base16/windows-nt-light', 'base16/windows-nt',
                'base16/woodland', 'base16/xcode-dusk', 'base16/zenburn'
            ];

            const defaults = {
                bgColor: '#121212',
                bgSecondaryColor: '#1E1E1E',
                borderColor: '#2D2D2D',
                scrollColor: '#2D2D2D',
                bgCardColor: '#252525',
                bgDarkerColor: '#000000',
                textColor: '#e0e0e0',
                primaryColor: '#FF8A3D',
                primaryDarkColor: '#B45A2D',
                primaryLightColor: '#FF8A3D',
                uiFontSize: '15',
                editorFontSize: '15',
                codeFontScale: '0.925',
                editorFontFamily: 'sans_serif',
                uiFontFamily: 'sans_serif',
                codeBgColor: '#1E1E1E',
                highlightTheme: 'atom-one-dark',
                themes: availableThemes
            };

            // Font mappings: Key -> CSS Font Stack
            const fontFamilies = {
                'sans_serif': 'ui-sans-serif,system-ui,sans-serif,Apple Color Emoji,Segoe UI Emoji,Segoe UI Symbol,Noto Color Emoji',
                'system_mono': 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'
            };

            Alpine.store('appearance', {
                bgColor: localStorage.getItem('bgColor') || defaults.bgColor,
                bgSecondaryColor: localStorage.getItem('bgSecondaryColor') || defaults.bgSecondaryColor,
                borderColor: localStorage.getItem('borderColor') || defaults.borderColor,
                scrollColor: localStorage.getItem('scrollColor') || defaults.scrollColor,
                bgCardColor: localStorage.getItem('bgCardColor') || defaults.bgCardColor,
                bgDarkerColor: localStorage.getItem('bgDarkerColor') || defaults.bgDarkerColor,
                textColor: localStorage.getItem('textColor') || defaults.textColor,
                primaryColor: localStorage.getItem('primaryColor') || defaults.primaryColor,
                primaryDarkColor: localStorage.getItem('primaryDarkColor') || defaults.primaryDarkColor,
                primaryLightColor: localStorage.getItem('primaryLightColor') || defaults.primaryLightColor,
                uiFontSize: localStorage.getItem('uiFontSize') || defaults.uiFontSize,
                editorFontSize: localStorage.getItem('editorFontSize') || defaults.editorFontSize,
                codeFontScale: localStorage.getItem('codeFontScale') || defaults.codeFontScale,
                editorFontFamily: (() => {
                    const f = localStorage.getItem('editorFontFamily');
                    return fontFamilies[f] ? f : defaults.editorFontFamily;
                })(),
                uiFontFamily: (() => {
                    const f = localStorage.getItem('uiFontFamily');
                    return fontFamilies[f] ? f : defaults.uiFontFamily;
                })(),
                codeBgColor: localStorage.getItem('codeBgColor') || defaults.codeBgColor,
                highlightTheme: (() => {
                    const t = localStorage.getItem('highlightTheme');
                    return availableThemes.includes(t) ? t : defaults.highlightTheme;
                })(),
                themes: availableThemes,
                cssVarMap: {
                    'bgColor': '--color-dark',
                    'bgSecondaryColor': '--color-dark-lighter',
                    'borderColor': '--color-border',
                    'scrollColor': '--color-scroll-thumb',
                    'bgCardColor': '--color-dark-card',
                    'bgDarkerColor': '--color-dark-darker',
                    'textColor': '--color-text',
                    'primaryColor': '--color-primary',
                    'primaryDarkColor': '--color-primary-dark',
                    'primaryLightColor': '--color-primary-light'
                },

                init() {
                    // Initialize all settings to ensure consistency between Store, LocalStorage, and CSS Variables
                    Object.keys(defaults).filter(key => key !== 'themes').forEach(key => {
                        this.updateSetting(key, this[key]);
                    });
                },

                updateSetting(key, val) {
                    this[key] = val;
                    localStorage.setItem(key, val);
                    
                    // Dispatch to specific handlers
                    if (this.cssVarMap[key]) return this.updateCssVar(this.cssVarMap[key], val);
                    if (key === 'uiFontSize') return this.updateFontSize('--fs-ui', val);
                    if (key === 'editorFontSize') return this.updateFontSize('--fs-editor', val);
                    if (key === 'codeFontScale') return this.updateFontSize('--fs-code-scale', val, 'em');
                    if (key === 'editorFontFamily') return this.updateFontFamily('--font-editor', val);
                    if (key === 'uiFontFamily') return this.updateFontFamily('--font-ui', val);
                    if (key === 'codeBgColor') return this.updateCodeBg(val);
                    if (key === 'highlightTheme') return this.updateTheme(val);
                },

                updateCssVar(varName, val) {
                    document.documentElement.style.setProperty(varName, val);
                },

                updateFontSize(varName, val, unit = 'px') {
                    document.documentElement.style.setProperty(varName, val + unit);
                },

                updateFontFamily(varName, val) {
                    const stack = fontFamilies[val] || fontFamilies['system_mono'];
                    document.documentElement.style.setProperty(varName, stack);
                },

                updateCodeBg(val) {
                    if (val && val.trim() !== '') {
                        document.documentElement.style.setProperty('--code-bg-override', val);
                        document.documentElement.classList.add('custom-code-bg');
                    } else {
                        document.documentElement.classList.remove('custom-code-bg');
                        document.documentElement.style.removeProperty('--code-bg-override');
                    }
                },

                updateTheme(val) {
                    const themeLink = document.getElementById('highlight-theme-link');
                    if (themeLink) themeLink.href = this.getThemeUrl(val);
                },

                getThemeUrl(name) {
                    return `/static/css/highlight/${name}.min.css`;
                },

                reset() {
                    const excludedKeys = ['highlightTheme', 'themes', 'cssVarMap'];

                    Object.keys(defaults).forEach(key => {
                        if (excludedKeys.includes(key)) return;
                        this.updateSetting(key, defaults[key]);
                    });
                    
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

            targetEl.querySelectorAll('pre code').forEach((block) => {
                block.classList.add('hljs');
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
                const targetId = mutation.target.id || '';

                // --- 1. Specialized Observers (Tools & Diffs) ---
                
                // Tool Calls: Reveal container when content is added
                if (targetId.startsWith('tool-calls-list-') || targetId.startsWith('tool-calls-container-')) {
                    const container = document.getElementById(targetId.replace('list', 'container'));
                    if (container) container.classList.remove('hidden');
                    
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1 && window.hljs) {
                            node.querySelectorAll('code.language-json').forEach(block => hljs.highlightElement(block));
                        }
                    });
                }

                // Diffs: Apply Syntax Highlighting to new patches
                if (targetId.startsWith('stream-container-') || targetId.startsWith('diff-patch-')) {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1 && window.hljs) {
                            node.querySelectorAll('code.language-diff').forEach(block => hljs.highlightElement(block));
                            if (node.tagName === 'CODE' && node.classList.contains('language-diff')) hljs.highlightElement(node);
                        }
                    });
                }

                // --- 2. Markdown Streaming ---
                
                // Case A: Streaming Text (AI) - Detect changes inside a .markdown-source container
                if (mutation.type === 'characterData' || mutation.type === 'childList') {
                    const target = mutation.target.nodeType === 3 ? mutation.target.parentElement : mutation.target;
                    if (target.classList.contains('markdown-source')) {
                        this.renderMarkdown(target.id); // Re-render on every chunk
                        this.scrollToBottom();
                    }
                }

                // Case B: New Message Insertion (User/History) - Detect new nodes containing .markdown-source
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1) { // Element node
                            // Instant render for static content (User messages or History load)
                            const sources = node.querySelectorAll('.markdown-source');
                            sources.forEach(el => this.renderMarkdown(el.id));
                        }
                    });
                    this.scrollToBottom();
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
                this.setupScrollHandler();
                this.scanAndRenderMarkdown();
            }
        });
    }

    static setupTreeStatePreservation() {
        document.body.addEventListener('htmx:beforeSwap', (evt) => {
            if (evt.target.id === 'file-tree') {
                // 1. Capture State from current DOM
                const expandedIds = new Set();
                evt.target.querySelectorAll('.tree-toggle.rotate-90').forEach(toggle => {
                    const item = toggle.closest('.tree-item');
                    if (item && item.id) expandedIds.add(item.id);
                });
                // 2. Apply State to new HTML (Pre-render) to prevent flicker
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = evt.detail.serverResponse;
                
                tempDiv.querySelectorAll('.tree-item').forEach(item => {
                    if (expandedIds.has(item.id)) {
                        const toggle = item.querySelector('.tree-toggle');
                        const children = item.querySelector('.tree-children');
                        if (toggle) toggle.classList.add('rotate-90');
                        if (children) children.classList.remove('hidden');
                    }
                });

                evt.detail.serverResponse = tempDiv.innerHTML;
            }
        });
    }

    static scanAndRenderMarkdown() {
        document.querySelectorAll('.markdown-source').forEach(el => {
            this.renderMarkdown(el.id);
        });
    }

    static highlightExistingCodeBlocks() {
        document.querySelectorAll('code[class*="language-"]').forEach(block => {
            if (block.classList.contains('hljs')) return;
            if (window.hljs) hljs.highlightElement(block);
        });
    }

    static setupScrollHandler() {
        const messageList = document.getElementById('message-list');
        const scrollBtn = document.getElementById('scroll-to-bottom-btn');
        
        if (!messageList) return;

        const checkPosition = () => {
            if (this.ignoreScrollEvents) return;
 
            const threshold = 10;
            const position = Math.ceil(messageList.scrollTop + messageList.clientHeight);
            const height = messageList.scrollHeight;

            if (height - position <= threshold) {
                this.autoScrollEnabled = true;
                if (scrollBtn) scrollBtn.classList.add('hidden');
            } else {
                this.autoScrollEnabled = false;
                if (scrollBtn) scrollBtn.classList.remove('hidden');
            }
        };

        // Initial check
        checkPosition();

        messageList.onscroll = checkPosition;
    }

    static scrollToBottom() {
        if (!this.autoScrollEnabled) return;
        const messageList = document.getElementById('message-list');
        if (messageList) {
            messageList.scrollTo({ top: messageList.scrollHeight, behavior: 'instant' });
        }
    }

    static forceScrollToBottom() {
        const messageList = document.getElementById('message-list');
        const scrollBtn = document.getElementById('scroll-to-bottom-btn');
        if (!messageList) return;

        this.autoScrollEnabled = true;
        this.ignoreScrollEvents = true;
        if (scrollBtn) scrollBtn.classList.add('hidden');
        
        messageList.scrollTo({ top: messageList.scrollHeight, behavior: 'smooth' });

        // Check arrival to release lock
        const checkArrival = setInterval(() => {
            const threshold = 20;
            const position = Math.ceil(messageList.scrollTop + messageList.clientHeight);
            const height = messageList.scrollHeight;

            if (height - position <= threshold) {
                this.ignoreScrollEvents = false;
                clearInterval(checkArrival);
            }
        }, 100);

        setTimeout(() => {
            clearInterval(checkArrival);
            this.ignoreScrollEvents = false;
        }, 2000);
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
                }
            } else if (closeButton) {
                const modal = closeButton.closest('.modal-overlay');
                if (modal) modal.classList.remove('active');
            }

            // Action Dispatcher
            const actionBtn = event.target.closest('[data-action]');
            if (actionBtn && this.actionHandlers[actionBtn.dataset.action]) {
                event.preventDefault();
                event.stopPropagation();
                this.actionHandlers[actionBtn.dataset.action](actionBtn);
            }

            // File Search Logic
            if (event.target.id === 'file-search') {
                this.handleFileSearch(event.target.value);
            }
        });

        // Search Input Listener (Delegated)
        document.body.addEventListener('input', (event) => {
            if (event.target.id === 'file-search') {
                this.handleFileSearch(event.target.value);
            }
        });

        // Global Keydown Listener
        document.addEventListener('keydown', (e) => {
            // Handle Message Input Submit (Ctrl+Enter)
            if (e.target.id === 'message-input' && e.key === 'Enter' && e.ctrlKey) {
                e.preventDefault();
                const btn = e.target.form?.querySelector('button[type="submit"]');
                if (btn) btn.click();
            }
        });

        // Auto-close modals on successful HTMX requests if attribute is present
        document.body.addEventListener('htmx:afterRequest', (event) => {
            if (event.detail.successful && event.target.hasAttribute('data-close-modal')) {
                const modal = event.target.closest('.modal-overlay');
                if (modal) modal.classList.remove('active');
            }
        });

        // Error Handling
        document.body.addEventListener('htmx:responseError', (event) => {
            let message = 'An unexpected error occurred.';
            try {
                const errorData = JSON.parse(event.detail.xhr.responseText);
                if (Array.isArray(errorData.detail)) {
                    message = errorData.detail.map(err => err.msg).join(', ');
                } else {
                    message = errorData.detail || event.detail.xhr.statusText;
                }
            } catch (e) {
                message = event.detail.xhr.statusText || 'Server error.';
            }
            window.dispatchEvent(new CustomEvent('show-error-toast', { detail: { message: message } }));
        });
    }

    static get actionHandlers() {
        return {
            [Action.CLEAR_LOGS]: () => {
                document.getElementById('logs-container').innerHTML = '<div class="text-xs text-gray-500 text-center py-6">No logs yet</div>';
            },
            [Action.CLEAR_SESSIONS]: () => {
                ChatApp.addLog('Sessions cleared', 'blue');
                document.getElementById('sessions-modal').classList.remove('active');
            },
            [Action.EXPAND_FOLDERS]: () => {
                document.querySelectorAll('.tree-children').forEach(el => el.classList.remove('hidden'));
                document.querySelectorAll('.tree-toggle').forEach(toggle => toggle.classList.add('rotate-90'));
            },
            [Action.COLLAPSE_FOLDERS]: () => {
                document.querySelectorAll('.tree-children').forEach(el => el.classList.add('hidden'));
                document.querySelectorAll('.tree-toggle').forEach(toggle => toggle.classList.remove('rotate-90'));
            },
            [Action.TOGGLE_FOLDER]: (btn) => {
                const container = btn.parentElement.nextElementSibling;
                if (container) {
                    container.classList.toggle('hidden');
                    btn.classList.toggle('rotate-90');
                }
            },
            [Action.TOGGLE_EXPANDABLE]: (btn) => {
                const content = btn.nextElementSibling;
                if (content) {
                    content.classList.toggle('hidden');
                    const icon = btn.querySelector('.fa-chevron-down');
                    if (icon) icon.classList.toggle('rotate-180');
                }
            }
        };
    }

    static handleFileSearch(query) {
        const term = query.toLowerCase();
        const tree = document.getElementById('file-tree');
        if (!tree) return;

        const items = tree.querySelectorAll('li.tree-item');
        
        if (!term) {
            items.forEach(item => item.classList.remove('hidden'));
            return;
        }

        items.forEach(item => {
            // Simple text match on the span inside the item
            const text = item.querySelector('span.select-none, span.text-gray-400')?.textContent?.toLowerCase() || '';
            const isMatch = text.includes(term);
            // If match, show it. If not, hide it (CSS will handle children visibility if parent is hidden)
            item.classList.toggle('hidden', !isMatch);
        });

        // Post-process: If a child is visible, ensure all its parents are visible
        tree.querySelectorAll('li.tree-item:not(.hidden)').forEach(visibleItem => {
            let parent = visibleItem.parentElement.closest('li.tree-item');
            while (parent) {
                parent.classList.remove('hidden');
                // Also expand the folder
                const ul = parent.querySelector('ul.tree-children');
                const toggle = parent.querySelector('.tree-toggle');
                if (ul) ul.classList.remove('hidden');
                if (toggle) toggle.classList.add('rotate-90');
                
                parent = parent.parentElement.closest('li.tree-item');
            }
        });
    }

    static addLog(message, color = 'gray') {
        const container = document.getElementById('logs-container');
        if (!container) return;

        // Remove placeholder if it exists
        const placeholder = document.getElementById('no-logs-placeholder');
        if (placeholder) placeholder.remove();

        const timestamp = new Date().toLocaleTimeString();
        const logHtml = `
            <div class="p-2 rounded-md bg-dark-card hover:bg-dark-light border-l-2 border-${color}-500 my-1 text-xs">
                <div class="text-gray-300 whitespace-pre-wrap">${message}</div>
                <div class="text-gray-500 text-[10px] mt-0.5">${timestamp}</div>
            </div>
        `;
        container.insertAdjacentHTML('afterbegin', logHtml);
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
            if (!openFence || openFence.hasDiffMarker) continue;

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

// Ignite
ChatApp.init();
