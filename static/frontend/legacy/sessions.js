// Compatibility saved-session operations: save / list / load / delete.
import { appendMsg, clearMessages, sysMsg, updateTokenBar } from "./msg.js";
import { renderMd } from "./markdown.js";
import { $, esc, hideWelcome } from "../core/dom.js";
import { closeOverlay, openOverlay, toast } from "../core/overlay.js";
import {
  renderSourceList,
  setSrc,
} from "./datasource.js";
import { setLoadedName } from "./autosave.js";

  const state = window.BAA.state;
  let activeLoad = null;
  let renameTarget = null;
  let deleteTarget = null;

  function escAttr(s) {
    return esc(s).replace(/"/g, "&quot;");
  }

  function formatFileNameAsTitle(fileName = "") {
    const stem = String(fileName || "").replace(/\.[^.]+$/, "");
    const lower = stem.toLowerCase();
    if (lower.includes("ecommerce") && lower.includes("sales") && lower.includes("sample")) {
      return "电商销售样本分析";
    }
    if (lower.includes("refund")) return "退款异常数据排查";
    if (lower.includes("sku")) return "SKU销售表现分析";
    if (lower.includes("category") || stem.includes("品类")) return "品类销售表现分析";
    if (lower.includes("channel") || stem.includes("渠道")) return "渠道销售表现分析";
    if (lower.includes("traffic") || stem.includes("流量")) return "店铺流量表现分析";
    if (lower.includes("advert") || lower.includes("ad_") || stem.includes("推广")) return "推广投放效果分析";
    if (lower.includes("sales") || stem.includes("销售")) return "销售数据分析";
    if (lower.includes("order") || stem.includes("订单")) return "订单数据分析";
    return "数据分析";
  }

  function summarizeUserQuestionAsTitle(question = "") {
    const q = String(question || "").replace(/\s+/g, " ").trim().replace(/[。.!！?？；;，,、]+$/, "");
    if (!q || q.toLowerCase() === "data" || q === "你好" || q === "您好" || /^\d+$/.test(q)) return "";
    if (q.includes("退款")) return "退款异常数据排查";
    if (q.includes("SKU") || q.toLowerCase().includes("sku")) return "SKU销售表现分析";
    if (q.includes("品类") && q.includes("毛利")) return "品类毛利结构诊断";
    if (q.includes("品类")) return "品类销售表现分析";
    if (q.includes("渠道")) return "渠道销售表现分析";
    if (q.includes("店铺") && q.includes("经营")) return "店铺经营情况分析";
    if (q.includes("经营")) return "店铺经营概览";
    if (q.includes("缺失") || q.includes("数据质量")) return "销售数据质量检查";
    if (q.includes("异常")) return "异常数据排查";
    if (q.includes("画图") || q.includes("图表") || q.includes("可视化")) return "数据可视化分析";
    if (q.includes("销售")) return "销售表现分析";
    return q.length > 16 ? `${q.slice(0, 14)}分析` : `${q}分析`;
  }

  function generateConversationTitle(conversation) {
    const direct = conversation?.display_title || conversation?.title || conversation?.summaryTitle || conversation?.summary_title;
    if (direct) return String(direct).slice(0, 20);

    const rawName = String(conversation?.name || "");
    const savedAt = conversation?.saved_at ? conversation.saved_at.slice(0, 16).replace("T", " ") : "";
    const generatedName = !rawName ||
      rawName.startsWith("自动保存_") ||
      rawName.startsWith("自动保存 ") ||
      rawName === savedAt ||
      /^对话_\d{8}_\d{6}$/.test(rawName);
    if (!generatedName) return rawName.slice(0, 20);

    const firstUserMessage = conversation?.messages?.find(m => m.role === "user")?.content ||
      conversation?.history?.find(m => m.role === "user")?.content;
    const fromQuestion = summarizeUserQuestionAsTitle(firstUserMessage);
    if (fromQuestion) return fromQuestion.slice(0, 20);

    const fileName = conversation?.fileName || conversation?.datasetName || conversation?.ds_name || conversation?.filename;
    if (fileName) return formatFileNameAsTitle(fileName);

    return "未命名分析";
  }

  function openSaveDialog() {
    $("save-name").value = "";
    $("save-err").textContent = "";
    openOverlay("ov-save");
    setTimeout(() => $("save-name").focus(), 80);
  }

  async function saveSession() {
    const name  = $("save-name").value.trim();
    const errEl = $("save-err");
    errEl.textContent = "";
    if (!window.BAA.auth?.isLoggedIn?.()) {
      closeOverlay("ov-save");
      window.BAA.auth?.showLoginGate?.();
      return;
    }
    const r = await window.BAA.auth.authFetch(`/api/history/import-session/${encodeURIComponent(state.SID)}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: name }),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok || d.error) { errEl.textContent = d.error || "保存失败，请稍后重试"; return; }
    closeOverlay("ov-save");
    toast("已保存到历史分析", "ok");
    window.BAA.sidebar?.setSessionName?.(name || d.session?.title || "当前分析", "");
    await loadSavedList();
  }

  function openRenameDialog(filename, name) {
    renameTarget = { filename, name };
    const input = $("rename-name");
    const errEl = $("rename-err");
    if (input) input.value = name || "";
    if (errEl) errEl.textContent = "";
    openOverlay("ov-rename");
    setTimeout(() => {
      if (!input) return;
      input.focus();
      input.select();
    }, 80);
  }

  async function loadSavedList() {
    const box = $("saved-list");
    if (!window.BAA.auth?.isLoggedIn?.()) {
      box.innerHTML = '<div class="saved-empty">登录后可保存并查看你的历史分析记录。</div>';
      return;
    }
    const r = await window.BAA.auth.authFetch("/api/history/sessions");
    const payload = await r.json().catch(() => ({}));
    const list = payload.sessions || [];
    if (!list.length) {
      box.innerHTML = '<div class="saved-empty">暂无历史分析，上传数据后开始你的第一次分析。</div>';
      return;
    }
    box.innerHTML = list.map(s => {
      const displayName = s.title || "未命名分析";
      const subtitle = s.last_question || s.data_source_name || "数据分析";
      return `
        <div class="saved-item saved-session-item">
          <div class="saved-info" data-action="loadHistorySession:${escAttr(s.id)}">
            <div class="saved-name">${esc(displayName)}</div>
            <div class="saved-sub">${esc(String(subtitle).slice(0, 42))}</div>
          </div>
        </div>`;
    }).join("");
  }

  async function loadHistorySession(historyId) {
    if (!window.BAA.auth?.isLoggedIn?.()) { window.BAA.auth?.showLoginGate?.(); return; }
    const r = await window.BAA.auth.authFetch(`/api/history/sessions/${encodeURIComponent(historyId)}`);
    const data = await r.json().catch(() => ({}));
    if (!r.ok || !data.session) { toast(data.error || "历史分析加载失败", "err"); return; }
    const restore = await window.BAA.auth.authFetch(`/api/history/sessions/${encodeURIComponent(historyId)}/restore/${encodeURIComponent(state.SID)}`, { method: "POST" });
    if (!restore.ok) { toast("恢复历史分析失败", "err"); return; }
    clearMessages(); hideWelcome();
    for (const msg of data.messages || []) {
      if (msg.role === "user") appendMsg("user", msg.content);
      else if (msg.role === "assistant") {
        const el = appendMsg("assistant", null);
        const bubble = el.querySelector(".msg-bubble");
        bubble.innerHTML = renderMd(msg.content || "");
        for (const cid of (msg.chart_ids || [])) bubble.before(window.BAA.chatStream.buildChartFrame(cid));
      }
    }
    window.BAA.sidebar?.setSessionName?.(data.session.title || "历史分析", "");
    sysMsg(`已恢复「${data.session.title || "历史分析"}」`);
  }

  function _elapsedLabel(startedAt) {
    const seconds = Math.floor((Date.now() - startedAt) / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ${String(seconds % 60).padStart(2, "0")}s`;
  }

  function showLoadMask(name, controller) {
    const ui = window.BAA.ui;
    if (ui && ui.isVue && typeof ui.showLoading === "function") {
      const loadingId = ui.showLoading({
        id: "session-load",
        title: t('session_load.title'),
        name: name || "",
        message: t('session_load.sub'),
        elapsedLabel: t('session_load.elapsed_label'),
        cancelText: t('session_load.cancel'),
        cancellable: true,
        onCancel: cancelLoadSession,
        startedAt: Date.now(),
      });
      activeLoad = { controller, timer: null, loadingId };
      return null;
    }

    const mask = $("session-load-mask");
    const nameEl = $("session-load-name");
    const elapsedEl = $("session-load-elapsed");
    if (!mask || !elapsedEl) return null;
    if (nameEl) nameEl.textContent = name || "";
    const startedAt = Date.now();
    elapsedEl.textContent = _elapsedLabel(startedAt);
    mask.hidden = false;
    mask.classList.add("open");
    const timer = setInterval(() => {
      elapsedEl.textContent = _elapsedLabel(startedAt);
    }, 500);
    activeLoad = { controller, timer };
    return timer;
  }

  function hideLoadMask(timer) {
    if (activeLoad && activeLoad.loadingId && window.BAA.ui && window.BAA.ui.isVue && typeof window.BAA.ui.hideLoading === "function") {
      window.BAA.ui.hideLoading(activeLoad.loadingId);
      return;
    }
    if (timer) clearInterval(timer);
    const mask = $("session-load-mask");
    if (!mask) return;
    mask.classList.remove("open");
    mask.hidden = true;
  }

  function cancelLoadSession() {
    if (!activeLoad) return;
    activeLoad.cancelled = true;
    activeLoad.controller.abort();
    hideLoadMask(activeLoad.timer);
    activeLoad = null;
    toast(t('toast.load_cancelled'));
  }

  async function loadSavedSession(filename, name) {
    if (!await window.BAA.ui?.confirm?.({
      title: t('confirm.title'), message: t('confirm.load', { name }),
    })) return;
    if (activeLoad) {
      toast(t('toast.load_busy'), "err");
      return;
    }

    // 告诉后端保留当前 session 已设的模型（keep_provider），
    // 历史文件中的 model_provider 不会覆盖 session。
    const controller = new AbortController();
    const timer = showLoadMask(name, controller);
    let d;
    try {
      const r = await fetch(`/api/session/${state.SID}/load`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, keep_provider: true }),
        signal: controller.signal,
      });
      d = await r.json();
      if (d.error) { toast(d.error, "err"); return; }

      clearMessages();
      hideWelcome();

      // Update sidebar datasource status + source list
      if (d.ds_connected) {
        setSrc(d.ds_name, 'src.restored', true);
        toast(t('src.restored_toast', { name: d.ds_name }), "ok");
      } else if (d.ds_lost) {
        setSrc(d.ds_name + t('src.lost_suffix'), 'src.lost_hint', false);
        toast(t('src.lost_hint'), "err");
      } else {
        setSrc(null, 'sidebar.hint.noconn', false);
      }

      // Re-fetch the source list from the server and render it.
      // load_session rebuilds sess.data_source on the backend, so the /sources
      // endpoint reflects the restored state. Without this, the sidebar source
      // list stays stale (showing the previous session's sources or nothing).
      try {
        const sr = await fetch(`/api/session/${state.SID}/sources`, { signal: controller.signal });
        const sd = await sr.json();
        const sources = sd.sources || [];
        renderSourceList(sources);
        // If backend restored a source, sync the status bar to match the list.
        // If the list is empty (e.g. SQL/GSheets can't be auto-restored),
        // the status bar text set above (setSrc) already reflects ds_lost/none,
        // so we only override when there actually are sources to show.
        if (sources.length > 0) {
          const active = sources.find(s => s.active);
          if (active) {
            setSrc(active.name, 'src.restored', true);
          }
        }
      } catch (err) {
        if (err && err.name === "AbortError") throw err;
        /* non-critical — status bar already updated above */
      }

      // A restored session may mount a different Workspace, so refresh both
      // independent extension catalogs and discard stale composer selections.
      window.BAA.slash?.clearCmd?.();
      window.BAA.skills?.clearSkill?.();
      await Promise.all([
        window.BAA.slash?.loadCommands?.(),
        window.BAA.skills?.loadSkills?.(),
      ]);

      // 不再从历史文件恢复模型 — 前端选择与后端 session 均保持不变。

      state.tokenState = {
        promptTokens:  0,
        totalInput:    d.total_input  || 0,
        totalOutput:   d.total_output || 0,
        contextWindow: state.tokenState.contextWindow,
      };
      updateTokenBar();

      for (const msg of d.history) {
        if (msg.role === "user") {
          appendMsg("user", msg.content);
        } else if (msg.role === "assistant" && msg.content) {
          const el = appendMsg("assistant", null);
          const bubble = el.querySelector(".msg-bubble");
          bubble.innerHTML = renderMd(msg.content);
          if (msg.reasoning) {
            bubble.before(window.BAA.chatStream.buildReasoningBlock(msg.reasoning));
          }
          for (const cid of (msg.chart_ids || [])) {
            const wrap = window.BAA.chatStream.buildChartFrame(cid);
            bubble.before(wrap);
          }
        }
      }

      const loadedName = d.display_title || name || d.name;
      sysMsg(t('sys.loaded', { name: loadedName }));
      toast(t('toast.loaded', { name: loadedName }), "ok");
      window.BAA.sidebar?.setSessionName?.(loadedName, filename);

      // Tell autosave to overwrite this exact file (not create a new one)
      setLoadedName(loadedName, filename);
    } catch (err) {
      if (err && err.name === "AbortError") {
        if (activeLoad && activeLoad.controller === controller) toast(t('toast.load_cancelled'));
      } else {
        toast(t('toast.load_failed', { error: String(err) }), "err");
      }
    } finally {
      if (activeLoad && activeLoad.controller === controller) {
        hideLoadMask(timer);
        activeLoad = null;
      }
    }
  }

  async function renameSavedSession(filename, name) {
    openRenameDialog(filename, name);
  }

  async function submitRenameSession() {
    if (!renameTarget) return;
    const input = $("rename-name");
    const errEl = $("rename-err");
    const newName = (input ? input.value : "").trim();
    if (errEl) errEl.textContent = "";
    if (!newName) {
      if (errEl) errEl.textContent = t('toast.rename_empty');
      return;
    }
    const r = await fetch(`/api/saved-sessions/${encodeURIComponent(renameTarget.filename)}/rename`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName }),
    });
    const d = await r.json().catch(() => ({ error: t('toast.rename_failed') }));
    if (d.error) {
      if (errEl) errEl.textContent = d.error;
      else toast(d.error, "err");
      return;
    }
    closeOverlay("ov-rename");
    toast(t('toast.renamed', { name: d.name }), "ok");
    if (state.loadedSessionFilename === renameTarget.filename) {
      window.BAA.sidebar?.setSessionName?.(d.name, renameTarget.filename);
    }
    setLoadedName(d.name, renameTarget.filename);
    renameTarget = null;
    await loadSavedList();
  }

  async function deleteSavedSession(filename, name) {
    deleteTarget = { filename, name };
    $("delete-session-name").textContent = name || filename;
    $("delete-session-err").textContent = "";
    $("delete-session-confirm").disabled = false;
    openOverlay("ov-delete-session");
  }

  async function confirmDeleteSavedSession() {
    if (!deleteTarget) return;
    const { filename, name } = deleteTarget;
    const btn = $("delete-session-confirm");
    const errEl = $("delete-session-err");
    btn.disabled = true;
    errEl.textContent = "";
    try {
      const r = await fetch(`/api/saved-sessions/${encodeURIComponent(filename)}`, { method: "DELETE" });
      const d = await r.json();
      if (d.error) { errEl.textContent = d.error; return; }
      closeOverlay("ov-delete-session");
      toast(t('toast.deleted', { name }));
      deleteTarget = null;
      await loadSavedList();
    } catch (err) {
      errEl.textContent = String(err);
    } finally {
      btn.disabled = false;
    }
  }

  export {
    openSaveDialog,
    openRenameDialog,
    saveSession,
    loadSavedList,
    loadHistorySession,
    loadSavedSession,
    cancelLoadSession,
    renameSavedSession,
    submitRenameSession,
    deleteSavedSession,
    confirmDeleteSavedSession,
  };

  document.addEventListener("DOMContentLoaded", () => {
    const input = $("rename-name");
    if (!input) return;
    input.addEventListener("keydown", e => {
      if (e.key === "Enter") submitRenameSession();
      if (e.key === "Escape") closeOverlay("ov-rename");
    });
  });
