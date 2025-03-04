/**
 * UI Preferences System for TQ GenAI Chat
 * Allows users to customize their experience
 */

class UIPreferences {
    constructor() {
        this.preferences = {
            theme: 'light',         // light, dark, system
            fontSize: 'medium',     // small, medium, large
            density: 'comfortable', // compact, comfortable, spacious
            codeTheme: 'github',    // github, monokai, dracula
            animations: true,       // enable/disable animations
            sounds: false,          // enable/disable interaction sounds
            markdownDefault: true   // enable markdown by default
        };

        // Load saved preferences
        this.loadPreferences();

        // Initialize UI
        this.initUI();

        // Apply preferences
        this.applyAllPreferences();
    }

    loadPreferences() {
        try {
            const savedPrefs = localStorage.getItem('ui_preferences');
            if (savedPrefs) {
                this.preferences = { ...this.preferences, ...JSON.parse(savedPrefs) };
            }

            // Check if system prefers dark mode
            if (this.preferences.theme === 'system') {
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                this.systemTheme = prefersDark ? 'dark' : 'light';
            }
        } catch (error) {
            console.error('Error loading preferences:', error);
        }
    }

    savePreferences() {
        try {
            localStorage.setItem('ui_preferences', JSON.stringify(this.preferences));
        } catch (error) {
            console.error('Error saving preferences:', error);
        }
    }

    initUI() {
        // Create preferences panel if it doesn't exist
        if (!document.getElementById('preferences-panel')) {
            this.createPreferencesPanel();
        }

        // Set up listeners for preferences changes
        this.setupListeners();
    }

    createPreferencesPanel() {
        const panel = document.createElement('div');
        panel.id = 'preferences-panel';
        panel.className = 'preferences-panel hidden';

        panel.innerHTML = `
      <div class="preferences-header">
        <h3>UI Preferences</h3>
        <button class="close-preferences" aria-label="Close preferences panel">&times;</button>
      </div>
      <div class="preferences-body">
        <div class="preference-group">
          <h4>Appearance</h4>
          <div class="preference-item">
            <label for="pref-theme">Theme</label>
            <select id="pref-theme" class="preference-control">
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </select>
          </div>

          <div class="preference-item">
            <label for="pref-font-size">Font Size</label>
            <select id="pref-font-size" class="preference-control">
              <option value="small">Small</option>
              <option value="medium">Medium</option>
              <option value="large">Large</option>
            </select>
          </div>

          <div class="preference-item">
            <label for="pref-density">Interface Density</label>
            <select id="pref-density" class="preference-control">
              <option value="compact">Compact</option>
              <option value="comfortable">Comfortable</option>
              <option value="spacious">Spacious</option>
            </select>
          </div>
        </div>

        <div class="preference-group">
          <h4>Code Display</h4>
          <div class="preference-item">
            <label for="pref-code-theme">Code Block Theme</label>
            <select id="pref-code-theme" class="preference-control">
              <option value="github">GitHub</option>
              <option value="monokai">Monokai</option>
              <option value="dracula">Dracula</option>
            </select>
          </div>
        </div>

        <div class="preference-group">
          <h4>Behavior</h4>
          <div class="preference-item">
            <label for="pref-animations">Enable Animations</label>
            <label class="switch">
              <input type="checkbox" id="pref-animations">
              <span class="slider round"></span>
            </label>
          </div>

          <div class="preference-item">
            <label for="pref-sounds">Enable Sounds</label>
            <label class="switch">
              <input type="checkbox" id="pref-sounds">
              <span class="slider round"></span>
            </label>
          </div>

          <div class="preference-item">
            <label for="pref-markdown">Use Markdown by default</label>
            <label class="switch">
              <input type="checkbox" id="pref-markdown">
              <span class="slider round"></span>
            </label>
          </div>
        </div>
      </div>
      <div class="preferences-footer">
        <button class="btn btn-outline" id="reset-preferences">Reset to Defaults</button>
      </div>
    `;

        document.body.appendChild(panel);

        // Add preference button to header if not exists
        const appNav = document.querySelector('.app-nav');
        if (appNav && !document.getElementById('preferences-btn')) {
            const preferencesBtn = document.createElement('button');
            preferencesBtn.id = 'preferences-btn';
            preferencesBtn.className = 'btn btn-icon';
            preferencesBtn.setAttribute('aria-label', 'Open preferences');
            preferencesBtn.innerHTML = '<i class="fas fa-cog"></i>';
            appNav.appendChild(preferencesBtn);
        }
    }

    setupListeners() {
        // Preference panel toggle
        const preferencesBtn = document.getElementById('preferences-btn');
        const panel = document.getElementById('preferences-panel');
        const closeBtn = panel.querySelector('.close-preferences');

        if (preferencesBtn) {
            preferencesBtn.addEventListener('click', () => {
                panel.classList.toggle('hidden');
                this.updatePanelUI();
            });
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                panel.classList.add('hidden');
            });
        }

        // Reset button
        const resetBtn = document.getElementById('reset-preferences');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetToDefaults();
            });
        }

        // Theme preference
        const themeSelect = document.getElementById('pref-theme');
        if (themeSelect) {
            themeSelect.addEventListener('change', () => {
                this.preferences.theme = themeSelect.value;
                this.applyTheme();
                this.savePreferences();
            });
        }

        // Font size preference
        const fontSizeSelect = document.getElementById('pref-font-size');
        if (fontSizeSelect) {
            fontSizeSelect.addEventListener('change', () => {
                this.preferences.fontSize = fontSizeSelect.value;
                this.applyFontSize();
                this.savePreferences();
            });
        }

        // Density preference
        const densitySelect = document.getElementById('pref-density');
        if (densitySelect) {
            densitySelect.addEventListener('change', () => {
                this.preferences.density = densitySelect.value;
                this.applyDensity();
                this.savePreferences();
            });
        }

        // Code theme preference
        const codeThemeSelect = document.getElementById('pref-code-theme');
        if (codeThemeSelect) {
            codeThemeSelect.addEventListener('change', () => {
                this.preferences.codeTheme = codeThemeSelect.value;
                this.applyCodeTheme();
                this.savePreferences();
            });
        }

        // Toggle switches
        const animationsToggle = document.getElementById('pref-animations');
        if (animationsToggle) {
            animationsToggle.addEventListener('change', () => {
                this.preferences.animations = animationsToggle.checked;
                this.applyAnimations();
                this.savePreferences();
            });
        }

        const soundsToggle = document.getElementById('pref-sounds');
        if (soundsToggle) {
            soundsToggle.addEventListener('change', () => {
                this.preferences.sounds = soundsToggle.checked;
                this.savePreferences();
            });
        }

        const markdownToggle = document.getElementById('pref-markdown');
        if (markdownToggle) {
            markdownToggle.addEventListener('change', () => {
                this.preferences.markdownDefault = markdownToggle.checked;
                this.savePreferences();
            });
        }

        // Listen for system theme changes
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)')
                .addEventListener('change', (e) => {
                    if (this.preferences.theme === 'system') {
                        this.systemTheme = e.matches ? 'dark' : 'light';
                        this.applyTheme();
                    }
                });
        }
    }

    updatePanelUI() {
        // Set form controls to match current preferences
        document.getElementById('pref-theme').value = this.preferences.theme;
        document.getElementById('pref-font-size').value = this.preferences.fontSize;
        document.getElementById('pref-density').value = this.preferences.density;
        document.getElementById('pref-code-theme').value = this.preferences.codeTheme;
        document.getElementById('pref-animations').checked = this.preferences.animations;
        document.getElementById('pref-sounds').checked = this.preferences.sounds;
        document.getElementById('pref-markdown').checked = this.preferences.markdownDefault;
    }

    resetToDefaults() {
        this.preferences = {
            theme: 'light',
            fontSize: 'medium',
            density: 'comfortable',
            codeTheme: 'github',
            animations: true,
            sounds: false,
            markdownDefault: true
        };

        this.savePreferences();
        this.updatePanelUI();
        this.applyAllPreferences();
    }

    applyAllPreferences() {
        this.applyTheme();
        this.applyFontSize();
        this.applyDensity();
        this.applyCodeTheme();
        this.applyAnimations();
    }

    applyTheme() {
        const theme = this.preferences.theme === 'system'
            ? this.systemTheme
            : this.preferences.theme;

        document.body.classList.remove('light-theme', 'dark-theme');
        document.body.classList.add(`${theme}-theme`);

        // Update theme-color meta tag for mobile browsers
        const themeColor = theme === 'dark' ? '#121212' : '#ffffff';
        let metaThemeColor = document.querySelector('meta[name="theme-color"]');
        if (!metaThemeColor) {
            metaThemeColor = document.createElement('meta');
            metaThemeColor.name = 'theme-color';
            document.head.appendChild(metaThemeColor);
        }
        metaThemeColor.content = themeColor;

        // Update toggle checkbox if it exists
        const themeToggle = document.getElementById('theme-toggle-input');
        if (themeToggle) {
            themeToggle.checked = (theme === 'dark');
        }
    }

    applyFontSize() {
        document.documentElement.setAttribute('data-font-size', this.preferences.fontSize);

        const sizeValues = {
            'small': '0.875rem',
            'medium': '1rem',
            'large': '1.125rem'
        };

        document.documentElement.style.setProperty('--font-size-base',
            sizeValues[this.preferences.fontSize] || '1rem');
    }

    applyDensity() {
        document.documentElement.setAttribute('data-density', this.preferences.density);

        const spacingValues = {
            'compact': {
                xs: '0.15rem',
                sm: '0.35rem',
                md: '0.75rem',
                lg: '1.25rem',
                xl: '1.75rem'
            },
            'comfortable': {
                xs: '0.25rem',
                sm: '0.5rem',
                md: '1rem',
                lg: '1.5rem',
                xl: '2rem'
            },
            'spacious': {
                xs: '0.35rem',
                sm: '0.65rem',
                md: '1.25rem',
                lg: '1.75rem',
                xl: '2.5rem'
            }
        };

        const spacing = spacingValues[this.preferences.density] || spacingValues.comfortable;

        document.documentElement.style.setProperty('--spacing-xs', spacing.xs);
        document.documentElement.style.setProperty('--spacing-sm', spacing.sm);
        document.documentElement.style.setProperty('--spacing-md', spacing.md);
        document.documentElement.style.setProperty('--spacing-lg', spacing.lg);
        document.documentElement.style.setProperty('--spacing-xl', spacing.xl);
    }

    applyCodeTheme() {
        document.documentElement.setAttribute('data-code-theme', this.preferences.codeTheme);

        const codeThemes = {
            'github': {
                bg: 'var(--card-bg)',
                color: '#24292e',
                keyword: '#d73a49',
                string: '#032f62',
                comment: '#6a737d',
                variable: '#005cc5'
            },
            'monokai': {
                bg: '#272822',
                color: '#f8f8f2',
                keyword: '#f92672',
                string: '#a6e22e',
                comment: '#75715e',
                variable: '#66d9ef'
            },
            'dracula': {
                bg: '#282a36',
                color: '#f8f8f2',
                keyword: '#ff79c6',
                string: '#f1fa8c',
                comment: '#6272a4',
                variable: '#bd93f9'
            }
        };

        const theme = codeThemes[this.preferences.codeTheme] || codeThemes.github;

        document.documentElement.style.setProperty('--code-bg', theme.bg);
        document.documentElement.style.setProperty('--code-color', theme.color);
        document.documentElement.style.setProperty('--code-keyword', theme.keyword);
        document.documentElement.style.setProperty('--code-string', theme.string);
        document.documentElement.style.setProperty('--code-comment', theme.comment);
        document.documentElement.style.setProperty('--code-variable', theme.variable);
    }

    applyAnimations() {
        document.documentElement.setAttribute('data-animations',
            this.preferences.animations ? 'enabled' : 'disabled');

        if (!this.preferences.animations) {
            // Add a class that disables animations site-wide
            document.body.classList.add('no-animations');
        } else {
            document.body.classList.remove('no-animations');
        }
    }

    playSound(soundType) {
        if (!this.preferences.sounds) return;

        const sounds = {
            'message-sent': '/static/sounds/message-sent.mp3',
            'message-received': '/static/sounds/message-received.mp3',
            'notification': '/static/sounds/notification.mp3',
            'error': '/static/sounds/error.mp3',
            'success': '/static/sounds/success.mp3'
        };

        const soundFile = sounds[soundType];
        if (soundFile) {
            const audio = new Audio(soundFile);
            audio.volume = 0.5;
            audio.play().catch(e => console.error('Error playing sound:', e));
        }
    }
}

// Initialize preferences system
document.addEventListener('DOMContentLoaded', () => {
    window.uiPreferences = new UIPreferences();
});
