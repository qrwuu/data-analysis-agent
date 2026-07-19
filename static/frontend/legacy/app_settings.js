// Compatibility application settings rendered as a Vue island.
import { state as appState } from "../core/runtime.js";
import { uiRegistry } from "../core/ui-registry.js";

const Vue = window.Vue;
const root = document.getElementById("app-settings-root");
const PROMPT_SUGGESTION_KEY = "baa_prompt_suggestion_enabled";
const TEAMS_KEY = "baa_teams_enabled";

const DEFAULT_HOOKS_TEXT = JSON.stringify({
  enabled: true,
  allow_command_hooks: false,
  hooks: [],
}, null, 2);
const HOOK_EVENTS = [
  "startup",
  "session_start",
  "user_prompt_submit",
  "turn_start",
  "turn_end",
  "tool_call",
  "pre_tool_use",
  "post_tool_use",
  "permission_request",
  "subagent_start",
  "subagent_stop",
  "pre_compact",
  "post_compact",
  "stop",
  "error",
];

function t(key) {
  return window.t ? window.t(key) : key;
}

function getLang() {
  return window.BAA?.i18n?.getLang?.() || "zh";
}

function setLang(lang) {
  window.BAA?.i18n?.setLang?.(lang);
  if (uiState) {
    uiState.language = getLang();
    draw();
  }
}

function getTheme() {
  return window.BAA?.theme?.getTheme?.() || "light";
}

function setTheme(theme) {
  window.BAA?.theme?.setTheme?.(theme);
  if (uiState) {
    uiState.theme = getTheme();
    draw();
  }
}

function _enabledFromStorage() {
  return localStorage.getItem(PROMPT_SUGGESTION_KEY) !== "0";
}

function _teamsEnabledFromStorage() {
  return localStorage.getItem(TEAMS_KEY) === "1";
}

function setPromptSuggestionEnabled(enabled) {
  appState.promptSuggestionEnabled = !!enabled;
  localStorage.setItem(PROMPT_SUGGESTION_KEY, appState.promptSuggestionEnabled ? "1" : "0");
  if (!appState.promptSuggestionEnabled) {
    window.BAA?.chatStream?.clearPromptSuggestion?.();
  }
  if (uiState) {
    uiState.promptSuggestionEnabled = appState.promptSuggestionEnabled;
    draw();
  }
}

function setTeamsEnabled(enabled) {
  appState.teamsEnabled = !!enabled;
  localStorage.setItem(TEAMS_KEY, appState.teamsEnabled ? "1" : "0");
  if (uiState) {
    uiState.teamsEnabled = appState.teamsEnabled;
    draw();
  }
}

let uiState = null;
let draw = () => {};

function toast(message, type = "") {
  uiRegistry.toast?.(message, type);
}

async function parseHooksJson() {
  try {
    return JSON.parse(uiState.hooksText || "{}");
  } catch (error) {
    uiState.hooksStatus = `JSON 格式错误：${error.message || error}`;
    uiState.hooksStatusType = "error";
    draw();
    return null;
  }
}

async function loadHooks() {
  if (!uiState) return;
  uiState.hooksLoading = true;
  uiState.hooksStatus = "";
  draw();
  try {
    const resp = await fetch("/api/hooks");
    const data = await resp.json();
    uiState.hooksText = JSON.stringify(data.settings || JSON.parse(DEFAULT_HOOKS_TEXT), null, 2);
    uiState.hooksStatus = data.ok ? "Hooks 配置已加载。" : (data.error || "Hooks 配置存在错误。");
    uiState.hooksStatusType = data.ok ? "ok" : "error";
  } catch (error) {
    uiState.hooksStatus = `加载失败：${error.message || error}`;
    uiState.hooksStatusType = "error";
  } finally {
    uiState.hooksLoading = false;
    draw();
  }
}

async function validateHooks() {
  const raw = await parseHooksJson();
  if (!raw) return false;
  uiState.hooksLoading = true;
  draw();
  try {
    const resp = await fetch("/api/hooks/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(raw),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !data.ok) throw new Error(data.error || "校验失败");
    uiState.hooksText = JSON.stringify(data.settings || raw, null, 2);
    uiState.hooksStatus = "校验通过。";
    uiState.hooksStatusType = "ok";
    toast("Hooks 校验通过");
    return true;
  } catch (error) {
    uiState.hooksStatus = `校验失败：${error.message || error}`;
    uiState.hooksStatusType = "error";
    return false;
  } finally {
    uiState.hooksLoading = false;
    draw();
  }
}

async function saveHooks() {
  const raw = await parseHooksJson();
  if (!raw) return;
  uiState.hooksLoading = true;
  draw();
  try {
    const resp = await fetch("/api/hooks", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(raw),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !data.ok) throw new Error(data.error || "保存失败");
    uiState.hooksText = JSON.stringify(data.settings || raw, null, 2);
    uiState.hooksStatus = "已保存，下一轮对话生效。";
    uiState.hooksStatusType = "ok";
    toast("Hooks 已保存");
  } catch (error) {
    uiState.hooksStatus = `保存失败：${error.message || error}`;
    uiState.hooksStatusType = "error";
  } finally {
    uiState.hooksLoading = false;
    draw();
  }
}

async function testHooks() {
  const raw = await parseHooksJson();
  if (!raw) return;
  uiState.hooksLoading = true;
  draw();
  try {
    const resp = await fetch("/api/hooks/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event: uiState.testEvent || "turn_start",
        settings: raw,
        context: {
          session_id: "preview",
          turn_id: "preview-turn",
          tool_name: "query_data",
          tool_args: { sql: "SELECT 1" },
          message: "测试 Hooks",
        },
      }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !data.ok) throw new Error(data.error || "测试失败");
    uiState.hooksStatus = JSON.stringify(data, null, 2);
    uiState.hooksStatusType = "ok";
  } catch (error) {
    uiState.hooksStatus = `测试失败：${error.message || error}`;
    uiState.hooksStatusType = "error";
  } finally {
    uiState.hooksLoading = false;
    draw();
  }
}

function renderSwitch(checked, onChange) {
  return Vue.h("span", { class: "app-setting-switch" }, [
    Vue.h("input", {
      type: "checkbox",
      checked,
      onChange: event => onChange(event.target.checked),
    }),
    Vue.h("span", { "aria-hidden": "true" }),
  ]);
}

function renderChoiceOptions(currentValue, options, onSelect) {
  return Vue.h("div", { class: "app-setting-options" }, options.map(option =>
    Vue.h("button", {
      class: `app-setting-chip${currentValue === option.value ? " active" : ""}`,
      type: "button",
      onClick: () => onSelect(option.value),
    }, option.label)
  ));
}

function renderGeneral() {
  return Vue.h("section", { class: "app-settings-panel" }, [
    Vue.h("div", { class: "app-settings-section-title" }, t("app_settings.assistant")),
    Vue.h("label", { class: "app-setting-row" }, [
      Vue.h("span", { class: "app-setting-copy" }, [
        Vue.h("strong", null, t("app_settings.prompt_suggestion.title")),
        Vue.h("span", null, t("app_settings.prompt_suggestion.desc")),
      ]),
      renderSwitch(uiState.promptSuggestionEnabled, setPromptSuggestionEnabled),
    ]),
    Vue.h("label", { class: "app-setting-row" }, [
      Vue.h("span", { class: "app-setting-copy" }, [
        Vue.h("strong", null, t("app_settings.teams.title")),
        Vue.h("span", null, t("app_settings.teams.desc")),
      ]),
      renderSwitch(uiState.teamsEnabled, setTeamsEnabled),
    ]),
    Vue.h("div", { class: "app-settings-section-title" }, t("app_settings.appearance")),
    Vue.h("div", { class: "app-setting-row app-setting-row--stack" }, [
      Vue.h("span", { class: "app-setting-copy" }, [
        Vue.h("strong", null, t("app_settings.language.title")),
        Vue.h("span", null, t("app_settings.language.desc")),
      ]),
      renderChoiceOptions(uiState.language, [
        { value: "zh", label: t("app_settings.lang.zh") },
        { value: "en", label: t("app_settings.lang.en") },
      ], setLang),
    ]),
    Vue.h("div", { class: "app-setting-row app-setting-row--stack" }, [
      Vue.h("span", { class: "app-setting-copy" }, [
        Vue.h("strong", null, t("app_settings.theme.title")),
        Vue.h("span", null, t("app_settings.theme.desc")),
      ]),
      renderChoiceOptions(uiState.theme, [
        { value: "light", label: t("app_settings.theme.light") },
        { value: "dark", label: t("app_settings.theme.dark") },
      ], setTheme),
    ]),
  ]);
}

function renderHooks() {
  const hint = "示例条件：tool == 'query_data' && args.sql contains 'DROP'";
  return Vue.h("section", { class: "app-settings-panel app-hooks-panel" }, [
    Vue.h("div", { class: "app-settings-section-title" }, "Hooks"),
    Vue.h("div", { class: "app-hooks-toolbar" }, [
      Vue.h("button", { class: "btn-sm btn-sm-ghost", type: "button", disabled: uiState.hooksLoading, onClick: loadHooks }, "重新加载"),
      Vue.h("button", { class: "btn-sm btn-sm-ghost", type: "button", disabled: uiState.hooksLoading, onClick: validateHooks }, "校验"),
      Vue.h("button", { class: "btn-sm btn-sm-primary", type: "button", disabled: uiState.hooksLoading, onClick: saveHooks }, "保存"),
    ]),
    Vue.h("p", { class: "app-hooks-hint" }, "支持标准事件别名：SessionStart / UserPromptSubmit / PreToolUse / PostToolUse / PermissionRequest / SubagentStart / SubagentStop / PreCompact / PostCompact / Stop。保存后会规范化为 snake_case。"),
    Vue.h("textarea", {
      class: "app-hooks-editor",
      spellcheck: "false",
      value: uiState.hooksText,
      onInput: event => { uiState.hooksText = event.target.value; },
    }),
    Vue.h("div", { class: "app-hooks-test-row" }, [
      Vue.h("select", {
        class: "app-hooks-select",
        value: uiState.testEvent,
        onChange: event => { uiState.testEvent = event.target.value; draw(); },
      }, HOOK_EVENTS.map(event =>
        Vue.h("option", { value: event }, event)
      )),
      Vue.h("button", { class: "btn-sm btn-sm-ghost", type: "button", disabled: uiState.hooksLoading, onClick: testHooks }, "测试运行"),
      Vue.h("span", { class: "app-hooks-hint-inline" }, hint),
    ]),
    uiState.hooksStatus
      ? Vue.h("pre", { class: `app-hooks-status app-hooks-status-${uiState.hooksStatusType}` }, uiState.hooksStatus)
      : null,
  ]);
}

function renderApp() {
  if (!root) return;
  const tabs = [
    ["general", t("app_settings.general")],
    ["hooks", t("app_settings.hooks")],
  ];
  Vue.render(Vue.h("div", { class: "app-settings-layout" }, [
    Vue.h("aside", { class: "app-settings-nav", "aria-label": "Settings sections" }, tabs.map(([id, label]) =>
      Vue.h("button", {
        class: `app-settings-nav-item${uiState.tab === id ? " active" : ""}`,
        type: "button",
        onClick: () => { uiState.tab = id; draw(); },
      }, label)
    )),
    uiState.tab === "hooks" ? renderHooks() : renderGeneral(),
  ]), root);
}

function syncLocaleState() {
  if (!uiState) return;
  uiState.language = getLang();
  draw();
}

function init() {
  appState.promptSuggestionEnabled = _enabledFromStorage();
  appState.teamsEnabled = _teamsEnabledFromStorage();
  if (!root || !Vue?.h || !Vue?.render || !Vue?.reactive) return;
  uiState = Vue.reactive({
    tab: "general",
    promptSuggestionEnabled: appState.promptSuggestionEnabled,
    teamsEnabled: appState.teamsEnabled,
    language: getLang(),
    theme: getTheme(),
    hooksText: DEFAULT_HOOKS_TEXT,
    hooksStatus: "",
    hooksStatusType: "ok",
    hooksLoading: false,
    testEvent: "turn_start",
  });
  draw = renderApp;
  draw();
  loadHooks();
}

document.addEventListener("DOMContentLoaded", init);
document.addEventListener("langchange", syncLocaleState);

export {
  init,
  setPromptSuggestionEnabled,
  setTeamsEnabled,
  loadHooks,
  validateHooks,
  saveHooks,
  testHooks,
};
