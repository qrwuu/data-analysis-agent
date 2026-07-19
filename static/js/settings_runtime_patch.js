const LABELS = {
  zh: {
    composerSkills: "分析工具",
    skillHeader: "选择分析工具",
    appSettingsTitle: "⚙ 应用设置",
    appearance: "界面偏好",
    languageTitle: "界面语言",
    languageDesc: "在中文和英文之间切换界面文案。",
    themeTitle: "界面主题",
    themeDesc: "切换浅色或深色界面风格。",
    zh: "中文",
    en: "English",
    light: "浅色",
    dark: "深色",
    settings: "设置",
  },
  en: {
    composerSkills: "Analysis Tools",
    skillHeader: "Choose Analysis Tool",
    appSettingsTitle: "⚙ App Settings",
    appearance: "Appearance",
    languageTitle: "Language",
    languageDesc: "Switch the interface copy between Chinese and English.",
    themeTitle: "Theme",
    themeDesc: "Switch between light and dark interface styles.",
    zh: "Chinese",
    en: "English",
    light: "Light",
    dark: "Dark",
    settings: "Settings",
  },
};

function getLang() {
  return window.BAA?.i18n?.getLang?.() || localStorage.getItem("baa_lang") || "zh";
}

function getTheme() {
  return window.BAA?.theme?.getTheme?.() || localStorage.getItem("baa_theme") || "light";
}

function applyLabelPatches() {
  const lang = getLang() === "en" ? "en" : "zh";
  const labels = LABELS[lang];

  document.querySelectorAll('[data-action="openSkillPicker"] [data-i18n="composer.skills"]').forEach((el) => {
    el.textContent = labels.composerSkills;
  });

  const skillHead = document.querySelector('#skill-picker [data-i18n="skills.header"]');
  if (skillHead) skillHead.textContent = labels.skillHeader;

  const footerSettings = document.querySelector('.sb-footer-settings span');
  if (footerSettings) footerSettings.textContent = labels.settings;

  const modalTitle = document.querySelector('#ov-app-settings .modal-title');
  if (modalTitle) modalTitle.textContent = labels.appSettingsTitle;
}

function renderQuickControls() {
  const host = document.getElementById('app-settings-quick-controls');
  if (!host) return;
  const lang = getLang() === 'en' ? 'en' : 'zh';
  const labels = LABELS[lang];
  const currentLang = getLang() === 'en' ? 'en' : 'zh';
  const currentTheme = getTheme() === 'dark' ? 'dark' : 'light';

  host.innerHTML = `
    <section class="app-settings-panel">
      <div class="app-settings-section-title">${labels.appearance}</div>
      <div class="app-setting-row app-setting-row--stack">
        <span class="app-setting-copy">
          <strong>${labels.languageTitle}</strong>
          <span>${labels.languageDesc}</span>
        </span>
        <div class="app-setting-options">
          <button type="button" class="app-setting-chip${currentLang === 'zh' ? ' active' : ''}" data-lang-choice="zh">${labels.zh}</button>
          <button type="button" class="app-setting-chip${currentLang === 'en' ? ' active' : ''}" data-lang-choice="en">${labels.en}</button>
        </div>
      </div>
      <div class="app-setting-row app-setting-row--stack">
        <span class="app-setting-copy">
          <strong>${labels.themeTitle}</strong>
          <span>${labels.themeDesc}</span>
        </span>
        <div class="app-setting-options">
          <button type="button" class="app-setting-chip${currentTheme === 'light' ? ' active' : ''}" data-theme-choice="light">${labels.light}</button>
          <button type="button" class="app-setting-chip${currentTheme === 'dark' ? ' active' : ''}" data-theme-choice="dark">${labels.dark}</button>
        </div>
      </div>
    </section>
  `;

  host.querySelectorAll('[data-lang-choice]').forEach((button) => {
    button.addEventListener('click', () => {
      window.BAA?.i18n?.setLang?.(button.dataset.langChoice);
      renderQuickControls();
      applyLabelPatches();
    });
  });

  host.querySelectorAll('[data-theme-choice]').forEach((button) => {
    button.addEventListener('click', () => {
      window.BAA?.theme?.setTheme?.(button.dataset.themeChoice);
      renderQuickControls();
    });
  });
}

function initRuntimePatch() {
  applyLabelPatches();
  renderQuickControls();
  document.addEventListener('langchange', () => {
    applyLabelPatches();
    renderQuickControls();
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initRuntimePatch, { once: true });
} else {
  initRuntimePatch();
}
