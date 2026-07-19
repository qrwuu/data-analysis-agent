const COPY = {
  zh: {
    placeholder: "上传数据或连接数据库后，直接输入你的分析问题",
    sampleSoon: "正在加载示例数据…",
    featureSoon: "功能加载失败，请刷新页面后重试",
    newAnalysis: "＋ 新建分析",
    newAnalysisTitle: "新建分析",
    newAnalysisMessage: "新建分析会清空当前对话内容，但不会删除已上传的数据源。是否继续？",
    newAnalysisConfirm: "确认新建",
    headerSubtitle: "连接数据源开始分析",
    headerSource: "当前数据源：{name}",
    historyNav: "历史分析",
    historyTitle: "历史分析",
    historySubtitle: "查看并恢复历史分析记录。",
    historyNewChat: "+ 新对话",
    savedSessions: "已保存对话",
    cloneFailed: "当前数据源保留失败，请重新连接后继续分析",
    clonePartial: "部分数据源恢复失败：{count} 个",
  },
  en: {
    placeholder: "Upload data or connect a database, then ask your analysis question",
    sampleSoon: "Loading sample data…",
    featureSoon: "The feature failed to load. Refresh the page and try again.",
    newAnalysis: "+ New Analysis",
    newAnalysisTitle: "New Analysis",
    newAnalysisMessage: "Starting a new analysis clears the current conversation, but keeps uploaded data sources. Continue?",
    newAnalysisConfirm: "Start New",
    headerSubtitle: "Connect a data source to begin analysis",
    headerSource: "Current data source: {name}",
    historyNav: "History",
    historyTitle: "Analysis History",
    historySubtitle: "Review and restore previous analyses.",
    historyNewChat: "+ New Chat",
    savedSessions: "Saved Chats",
    cloneFailed: "Could not keep the current data source. Please reconnect it before continuing.",
    clonePartial: "Some data sources could not be restored: {count}",
  },
};

function currentLang() {
  const lang = window.BAA?.i18n?.getLang?.() || localStorage.getItem("baa_lang") || "zh";
  return lang === "en" ? "en" : "zh";
}

function interpolate(template, vars = {}) {
  return String(template || "").replace(/\{(\w+)\}/g, (_match, key) => {
    return vars[key] == null ? "" : String(vars[key]);
  });
}

function copyFor(key, vars) {
  const value = COPY[currentLang()][key] || COPY.zh[key] || "";
  return vars ? interpolate(value, vars) : value;
}

function inferHintKey(type) {
  switch (String(type || "").toLowerCase()) {
    case "sql":
      return "src.hint.db";
    case "gsheets":
      return "src.hint.gsheets";
    case "http":
      return "src.hint.api";
    default:
      return "src.hint.file";
  }
}

function hiddenSourceName() {
  return document.getElementById("src-name")?.textContent?.trim() || "";
}

function syncHistoryCopy() {
  const historyLabel = document.querySelector('[data-sidebar-nav="history"] .sb-nav-label');
  if (historyLabel && historyLabel.textContent !== copyFor("historyNav")) historyLabel.textContent = copyFor("historyNav");

  const drawerTitle = document.getElementById("sb-drawer-title");
  if (drawerTitle && drawerTitle.textContent !== copyFor("historyTitle")) drawerTitle.textContent = copyFor("historyTitle");

  const drawerSubtitle = document.querySelector(".sb-drawer-title span");
  if (drawerSubtitle && drawerSubtitle.textContent !== copyFor("historySubtitle")) drawerSubtitle.textContent = copyFor("historySubtitle");

  const newChatButton = document.getElementById("history-new-chat-btn");
  if (newChatButton && newChatButton.textContent !== copyFor("historyNewChat")) newChatButton.textContent = copyFor("historyNewChat");

  const savedTitle = document.getElementById("history-saved-title");
  if (savedTitle && savedTitle.textContent !== copyFor("savedSessions")) savedTitle.textContent = copyFor("savedSessions");
}

function syncHeaderDataSourceLabel() {
  const sub = document.getElementById("hdr-sub");
  if (!sub) return;

  const state = window.BAA?.state;
  const name = state?.srcName || hiddenSourceName();
  const connected = Boolean(state?.srcConnected || name);
  const nextText = connected ? copyFor("headerSource", { name }) : copyFor("headerSubtitle");
  if (sub.textContent !== nextText) sub.textContent = nextText;
}

function syncNewAnalysisButton() {
  const button = document.getElementById("btn-new-analysis");
  if (!button) return;
  if (button.textContent !== copyFor("newAnalysis")) button.textContent = copyFor("newAnalysis");
  if (button.title !== copyFor("newAnalysisTitle")) button.title = copyFor("newAnalysisTitle");
}

const SKILL_NAME_MAP = {
  zh: {
    data: "数据分析能力",
    sql: "SQL 查询",
    chart: "图表生成",
    report: "报告生成",
    file: "文件解析",
  },
  en: {
    data: "Data Analysis",
    sql: "SQL Query",
    chart: "Chart Generation",
    report: "Report Generation",
    file: "File Parsing",
  },
};

function mapSkillName(skillName) {
  const normalized = String(skillName || "").trim();
  if (!normalized) return "";
  const lang = currentLang();
  return SKILL_NAME_MAP[lang]?.[normalized] || SKILL_NAME_MAP.zh[normalized] || normalized;
}

function skillStatusText(skillName) {
  const mapped = mapSkillName(skillName);
  if (!mapped) return "";
  return currentLang() === "en"
    ? `Using: ${mapped}`
    : `正在使用：${mapped}`;
}

function rewriteSkillDisplayText(text) {
  const raw = String(text || "");
  const match = raw.match(/^\s*\[Skill:\s*([^\]]+)\]\s*(.*)$/s);
  if (!match) return raw;

  const internalName = match[1].trim();
  const trailing = match[2].trim();
  const label = skillStatusText(internalName);
  if (!label) return raw;
  if (!trailing || trailing.toLowerCase() === internalName.toLowerCase()) return label;
  return `${label} · ${trailing}`;
}

function syncSkillBadge() {
  const badge = document.getElementById("skill-badge");
  const badgeText = document.getElementById("skill-badge-text");
  const activeSkill = window.BAA?.state?.activeSkill || "";
  if (!badge || !badgeText || !activeSkill) return;
  const nextText = skillStatusText(activeSkill);
  if (nextText && badgeText.textContent !== nextText) badgeText.textContent = nextText;
}

function rewriteSkillTextNodes(root) {
  if (!root) return;
  const walker = document.createTreeWalker(
    root,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        return node.nodeValue && node.nodeValue.includes("[Skill:")
          ? NodeFilter.FILTER_ACCEPT
          : NodeFilter.FILTER_REJECT;
      },
    },
  );

  const textNodes = [];
  while (walker.nextNode()) textNodes.push(walker.currentNode);

  textNodes.forEach((node) => {
    const nextValue = rewriteSkillDisplayText(node.nodeValue);
    if (nextValue !== node.nodeValue) node.nodeValue = nextValue;
  });
}

function applySkillPresentation(root = document) {
  syncSkillBadge();
  if (root === document) {
    rewriteSkillTextNodes(document.getElementById("messages"));
    rewriteSkillTextNodes(document.getElementById("composer-queue-root"));
    return;
  }
  rewriteSkillTextNodes(root);
}

function patchTranslator() {
  if (typeof window.t !== "function" || window.t.__uiRefinePatched) return;
  const original = window.t;
  const patched = function patchedT(key, vars) {
    if (key === "input.placeholder") return copyFor("placeholder");
    return original(key, vars);
  };
  patched.__uiRefinePatched = true;
  patched.__original = original;
  window.t = patched;
}

function applyStaticCopy() {
  const input = document.getElementById("msg-input");
  if (input && !input.dataset.promptSuggestion) input.placeholder = copyFor("placeholder");
  syncHistoryCopy();
  syncHeaderDataSourceLabel();
  syncNewAnalysisButton();
  applySkillPresentation();
}

async function silentlySetProvider(provider) {
  const state = window.BAA?.state;
  if (!provider || !state?.SID) return;
  const selectors = [
    document.getElementById("model-sel"),
    document.getElementById("model-sel-sidebar"),
  ].filter(Boolean);
  selectors.forEach((select) => {
    select.value = provider;
  });
  try {
    await fetch(`/api/session/${state.SID}/model`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider }),
    });
  } catch (error) {
    console.warn("[ui-refine] failed to set default provider:", error);
  }
}

function patchModelsApi() {
  const api = window.BAA?.models;
  const state = window.BAA?.state;
  if (!api || !state) return false;
  if (window.BAA.models?.__uiRefinePatched) return true;

  const originalLoadBuiltinProviders = api.loadBuiltinProviders?.bind(api);
  const patched = { ...api };

  patched.loadModels = async function loadModelsSilently() {
    const response = await fetch("/api/models");
    const models = await response.json();
    state.modelConfigs = models || {};

    const selectors = [
      document.getElementById("model-sel"),
      document.getElementById("model-sel-sidebar"),
    ].filter(Boolean);

    for (const select of selectors) {
      const previous = select.value || "";
      select.innerHTML = '<option value="">internal-model</option>';
      for (const [key, cfg] of Object.entries(models || {})) {
        if (!cfg?.has_api_key) continue;
        const option = document.createElement("option");
        option.value = key;
        option.textContent = key;
        select.appendChild(option);
      }
      if (previous && [...select.options].some((option) => option.value === previous)) {
        select.value = previous;
      }
    }

    const availableProviders = Object.entries(models || {})
      .filter(([, cfg]) => cfg?.has_api_key)
      .map(([key]) => key);
    const fallbackProvider = selectors.map((select) => select.value).find(Boolean) || availableProviders[0] || "";
    if (fallbackProvider) await silentlySetProvider(fallbackProvider);
    return models;
  };

  patched.onModelChange = async (provider) => {
    await silentlySetProvider(provider || document.getElementById("model-sel")?.value || "");
  };
  patched.openModelPicker = () => {};
  patched.closeModelPicker = () => {};
  patched.renderModelPicker = () => {};
  patched.refreshModelPickerLabels = () => {};
  patched.testModel = async () => true;
  patched.loadBuiltinProviders = async function quietLoadBuiltinProviders() {
    try {
      return await originalLoadBuiltinProviders?.();
    } catch (error) {
      console.warn("[ui-refine] skipped provider settings bootstrap:", error);
      return null;
    }
  };
  patched.__uiRefinePatched = true;
  window.BAA.models = patched;
  return true;
}

function positionDataMenu(trigger, menu) {
  if (!trigger || !menu || menu.hidden) return;
  menu.style.visibility = "hidden";
  const triggerRect = trigger.getBoundingClientRect();
  const width = menu.offsetWidth || Math.min(360, window.innerWidth - 32);
  const height = menu.offsetHeight || 300;
  const left = Math.max(16, Math.min(triggerRect.left - 4, window.innerWidth - width - 16));
  let top = triggerRect.top - height - 12;
  if (top < 16) {
    top = Math.min(window.innerHeight - height - 16, triggerRect.bottom + 12);
  }
  menu.style.left = `${left}px`;
  menu.style.top = `${Math.max(16, top)}px`;
  menu.style.visibility = "visible";
}

function openOverlayOrToast(id) {
  if (document.getElementById(id) && typeof window.openOverlay === "function") {
    window.openOverlay(id);
    return;
  }
  window.toast?.(copyFor("featureSoon"), "ok");
}

function initComposerDataMenu() {
  if (window.__uiRefineDataMenuBound) return true;

  const trigger = document.getElementById("composer-data-trigger");
  const menu = document.getElementById("composer-data-menu");
  if (!trigger || !menu) return false;

  if (menu.parentElement !== document.body) document.body.appendChild(menu);

  const closeMenu = () => {
    menu.hidden = true;
    menu.classList.remove("open");
    trigger.setAttribute("aria-expanded", "false");
  };

  const openMenu = () => {
    menu.hidden = false;
    menu.classList.add("open");
    trigger.setAttribute("aria-expanded", "true");
    positionDataMenu(trigger, menu);
  };

  const toggleMenu = () => {
    if (menu.hidden) openMenu();
    else closeMenu();
  };

  trigger.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    toggleMenu();
  });

  menu.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    const item = event.target.closest("[data-data-menu-action]");
    if (!item) return;
    const action = item.dataset.dataMenuAction;
    closeMenu();

    if (action === "upload") {
      if (typeof window.openOverlay === "function") window.openOverlay("ov-excel");
      return;
    }
    if (action === "sql") {
      openOverlayOrToast("ov-db");
      return;
    }
    if (action === "gsheets") {
      openOverlayOrToast("ov-gsheets");
      return;
    }
    if (action === "api") {
      openOverlayOrToast("ov-api");
      return;
    }
    if (action === "sample") {
      window.toast?.(copyFor("sampleSoon"), "ok");
      if (typeof window.BAA?.datasource?.loadSampleData === "function") {
        window.BAA.datasource.loadSampleData();
      } else {
        window.toast?.(copyFor("featureSoon"), "err");
      }
    }
  });

  document.addEventListener("click", (event) => {
    if (menu.hidden) return;
    if (event.target.closest("#composer-data-menu, #composer-data-trigger")) return;
    closeMenu();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });

  window.addEventListener("resize", () => positionDataMenu(trigger, menu));
  window.addEventListener("scroll", () => positionDataMenu(trigger, menu), true);

  window.__uiRefineDataMenuBound = true;
  return true;
}

function restoreClonedSources(sources) {
  const list = Array.isArray(sources) ? sources : [];
  const state = window.BAA?.state;
  if (!state) return;

  const primary = list.find((item) => item?.active) || list[0] || null;
  const hintKey = inferHintKey(primary?.type || "");

  state.sources = list;
  state.srcConnected = Boolean(primary);
  state.srcName = primary?.name || "";
  state.srcHintKey = primary ? hintKey : "sidebar.hint.noconn";
  state.analysisContext = null;

  const srcDot = document.getElementById("src-dot");
  if (srcDot) srcDot.classList.toggle("on", Boolean(primary));

  const srcName = document.getElementById("src-name");
  if (srcName) srcName.textContent = primary?.name || (currentLang() === "en" ? "Not connected" : "未连接");

  const srcHint = document.getElementById("src-hint");
  if (srcHint) {
    srcHint.textContent = primary && typeof window.t === "function"
      ? window.t(hintKey)
      : (typeof window.t === "function" ? window.t("sidebar.hint.noconn") : "请上传文件或连接数据库");
  }

  const schemaBtn = document.getElementById("btn-schema");
  if (schemaBtn) {
    schemaBtn.classList.toggle("is-empty", !primary);
    schemaBtn.title = primary
      ? (typeof window.t === "function" ? window.t("header.schema") : "数据预览")
      : copyFor("headerSubtitle");
  }

  document.querySelector(".sidebar")?.classList.toggle("has-source", Boolean(primary));
  syncHeaderDataSourceLabel();
  window.BAA?.dom?.showWelcome?.();
}

function hasAnalysisContent() {
  const turns = Number(window.BAA?.ui?.chat?.countMessages?.() || 0);
  if (turns > 0) return true;
  if ((window.BAA?.state?.pendingMessages || []).length > 0) return true;
  return Boolean(document.querySelector(".reasoning-block, .tool-step, .chart-list iframe, .card-list > *"));
}

async function runNewAnalysis() {
  if (window.__uiRefineNewAnalysisBusy) return;
  window.__uiRefineNewAnalysisBusy = true;

  try {
    if (hasAnalysisContent()) {
      const accepted = await window.BAA?.ui?.confirm?.({
        title: copyFor("newAnalysisTitle"),
        message: copyFor("newAnalysisMessage"),
        confirmText: copyFor("newAnalysisConfirm"),
        cancelText: typeof window.t === "function" ? window.t("common.cancel") : "取消",
      });
      if (!accepted) return;
    }

    const state = window.BAA?.state;
    const oldSid = state?.SID || "";
    const hadSources = Array.isArray(state?.sources) && state.sources.length > 0;

    await window.BAA?.chatStream?.newChat?.();

    const newSid = window.BAA?.state?.SID || "";
    if (hadSources && oldSid && newSid && oldSid !== newSid) {
      try {
        const response = await fetch(`/api/session/${encodeURIComponent(oldSid)}/sources/clone`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ target_session_id: newSid }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.error) {
          window.toast?.(data.error || copyFor("cloneFailed"), "err");
        } else {
          restoreClonedSources(data.sources || []);
          if ((data.errors || []).length > 0) {
            window.toast?.(copyFor("clonePartial", { count: data.errors.length }), "err");
          }
        }
      } catch (error) {
        console.warn("[ui-refine] failed to clone sources into new analysis:", error);
        window.toast?.(copyFor("cloneFailed"), "err");
      }
    }

    const messages = document.getElementById("messages");
    if (messages) messages.scrollTop = 0;
    window.BAA?.dom?.showWelcome?.();
    syncHeaderDataSourceLabel();
    syncHistoryCopy();
  } finally {
    window.__uiRefineNewAnalysisBusy = false;
  }
}

function bindNewAnalysisButton() {
  if (window.__uiRefineNewAnalysisBound) return true;
  const button = document.getElementById("btn-new-analysis");
  if (!button) return false;
  button.addEventListener("click", (event) => {
    event.preventDefault();
    runNewAnalysis();
  });
  window.__uiRefineNewAnalysisBound = true;
  return true;
}

function observeRuntimeNodes() {
  if (window.__uiRefineObserved) return;
  const observer = new MutationObserver((mutations) => {
    syncHistoryCopy();
    syncHeaderDataSourceLabel();
    syncNewAnalysisButton();

    const roots = new Set();
    mutations.forEach((mutation) => {
      const target = mutation.target?.nodeType === Node.TEXT_NODE
        ? mutation.target.parentNode
        : mutation.target;
      if (target) roots.add(target);
    });

    if (!roots.size) {
      applySkillPresentation();
      return;
    }
    roots.forEach((root) => applySkillPresentation(root));
  });
  const srcName = document.getElementById("src-name");
  const drawerTitle = document.getElementById("sb-drawer-title");
  const skillBadgeText = document.getElementById("skill-badge-text");
  const messages = document.getElementById("messages");
  const queueRoot = document.getElementById("composer-queue-root");
  if (srcName) observer.observe(srcName, { childList: true, characterData: true, subtree: true });
  if (drawerTitle) observer.observe(drawerTitle, { childList: true, characterData: true, subtree: true });
  if (skillBadgeText) observer.observe(skillBadgeText, { childList: true, characterData: true, subtree: true });
  if (messages) observer.observe(messages, { childList: true, characterData: true, subtree: true });
  if (queueRoot) observer.observe(queueRoot, { childList: true, characterData: true, subtree: true });

  document.addEventListener("click", (event) => {
    if (event.target.closest('[data-sidebar-nav="history"]')) {
      setTimeout(syncHistoryCopy, 0);
    }
  }, true);

  document.addEventListener("langchange", () => {
    applyStaticCopy();
    setTimeout(syncHistoryCopy, 0);
    setTimeout(() => applySkillPresentation(), 0);
  });

  window.__uiRefineObserved = true;
}

function bootstrap() {
  patchTranslator();
  applyStaticCopy();
  observeRuntimeNodes();
  const menuReady = initComposerDataMenu();
  const newAnalysisReady = bindNewAnalysisButton();
  const modelsReady = patchModelsApi();
  return menuReady && newAnalysisReady && modelsReady;
}

function initBootWatchdog() {
  if (window.__uiRefineBootWatchdogBound) return;
  window.__uiRefineBootWatchdogBound = true;

  window.setTimeout(() => {
    if (document.body?.dataset?.appBoot === "ready") {
      sessionStorage.removeItem("baa_boot_retry");
      return;
    }

    const hasRetried = sessionStorage.getItem("baa_boot_retry") === "1";
    if (!hasRetried) {
      sessionStorage.setItem("baa_boot_retry", "1");
      localStorage.removeItem("baa_session_id");
      sessionStorage.removeItem("baa_session_id");
      window.location.reload();
      return;
    }

    window.__BAA_BOOT_GUARD?.report?.("timeout", "ui-refine-appBoot-failed", { stage: document.body?.dataset?.appBoot || "" });
    document.body.dataset.appBoot = "failed";
    const savedEmpty = document.querySelector("#saved-list .saved-empty");
    if (savedEmpty && /加载/.test(savedEmpty.textContent || "")) {
      savedEmpty.textContent = currentLang() === "en"
        ? "Initialization timed out. Refresh to try again."
        : "初始化超时，请刷新页面重试";
    }
    window.toast?.(currentLang() === "en"
      ? "Initialization timed out. Please refresh and try again."
      : "页面初始化超时，请刷新后重试", "err");
  }, 8000);
}

function init() {
  initBootWatchdog();
  let attempts = 0;
  const run = () => {
    const ready = bootstrap();
    attempts += 1;
    if (ready) {
      document.body.dataset.uiRefine = "ready";
      return;
    }
    if (attempts < 40) setTimeout(run, attempts < 8 ? 150 : 400);
  };
  run();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init, { once: true });
} else {
  init();
}
