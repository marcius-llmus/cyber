/**
 * Critical Rendering Path Logic
 * This script must run in the <head> before the body is rendered
 * to prevent Flash of Unstyled Content (FOUC).
 */
(function() {
    // Restore Color Palette
    const map = {
        'bgColor': '--color-dark', 'bgSecondaryColor': '--color-dark-lighter',
        'borderColor': '--color-border', 'scrollColor': '--color-scroll-thumb',
        'bgCardColor': '--color-dark-card', 'bgDarkerColor': '--color-dark-darker', 
        'textColor': '--color-text',
        'primaryColor': '--color-primary', 'primaryDarkColor': '--color-primary-dark',
        'primaryLightColor': '--color-primary-light'
    };
    const root = document.documentElement;

    Object.entries(map).forEach(([key, varName]) => {
        const val = localStorage.getItem(key);
        if (val) root.style.setProperty(varName, val);
    });
    
    // Font Sizes
    const uiSz = localStorage.getItem('uiFontSize');
    if (uiSz) root.style.setProperty('--fs-ui', uiSz + 'px');
    
    const edSz = localStorage.getItem('editorFontSize');
    if (edSz) root.style.setProperty('--fs-editor', edSz + 'px');
    
    const codeScale = localStorage.getItem('codeFontScale');
    if (codeScale) root.style.setProperty('--fs-code-scale', codeScale + 'em');
    
    // Font Family
    const fontMap = {
        'system_default': 'ui-sans-serif,system-ui,sans-serif,Apple Color Emoji,Segoe UI Emoji,Segoe UI Symbol,Noto Color Emoji',
        'system_mono': 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
        'fira_code': '"Fira Code", monospace',
        'jetbrains_mono': '"JetBrains Mono", monospace',
        'consolas': '"Consolas", monospace',
        'courier_new': '"Courier New", monospace'
    };
    const edFont = localStorage.getItem('editorFontFamily');
    if (edFont && fontMap[edFont]) root.style.setProperty('--font-editor', fontMap[edFont]);

    // Code Background Override
    const codeBg = localStorage.getItem('codeBgColor');
    if (codeBg && codeBg.trim() !== '') {
        root.style.setProperty('--code-bg-override', codeBg);
        root.classList.add('custom-code-bg');
    }
})();