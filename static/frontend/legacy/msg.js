// Compatibility message helpers + token bar + /status renderer.
import { state } from "../core/app-store.js";
import { $, scrollBottom } from "../core/dom.js";
import { getUiIsland } from "../core/ui-registry.js";
import { renderMd } from "./markdown.js";

  // ── 气泡内图片：no-referrer 策略绕过 OSS 防盗链 ─────────────────
  // OSS referer 白名单通常允许「空 Referer」，浏览器加 referrerpolicy="no-referrer"
  // 后发出的图片请求不带 Referer 头，多数情况下可以通过防盗链。
  // 同时准备 blob 兜底：若直连仍失败，用 fetch(no-cors) 拿 blob 本地显示。

  export function bindBubbleImages(bubbleEl) {
    bindCopyableBlocks(bubbleEl);
    if (!bubbleEl) return;
    bubbleEl.querySelectorAll("img").forEach(img => {
      if (img.dataset.bound) return;
      img.dataset.bound = "1";

      const originalSrc = img.getAttribute("src") || "";
      if (!originalSrc.startsWith("http")) return;

      // Step 1: 加 no-referrer，浏览器不发 Referer 头
      img.referrerPolicy = "no-referrer";
      img.crossOrigin    = "anonymous";

      // 点击新标签打开
      img.style.cursor = "pointer";
      img.addEventListener("click", () => window.open(originalSrc, "_blank", "noopener"));

      // Step 2: 若 no-referrer 仍失败，尝试 fetch blob 兜底
      img.addEventListener("error", () => {
        if (img.dataset.blobTried) {
          _replaceWithLink(img, originalSrc);
          return;
        }
        img.dataset.blobTried = "1";
        // fetch with no-cors — 拿到 opaque response，转 blob 作为本地 objectURL
        fetch(originalSrc, { mode: "no-cors", referrerPolicy: "no-referrer" })
          .then(r => r.blob())
          .then(blob => {
            if (!blob.size) throw new Error("empty blob");
            const blobUrl = URL.createObjectURL(blob);
            img.src = blobUrl;
            // blob URL 用完后在页面卸载时释放
            window.addEventListener("beforeunload", () => URL.revokeObjectURL(blobUrl), { once: true });
          })
          .catch(() => _replaceWithLink(img, originalSrc));
      });
    });
  }

  export function bindCopyableBlocks(rootEl) {
    if (!rootEl) return;
    rootEl.querySelectorAll("pre").forEach(pre => {
      if (pre.closest(".copyable-block")) return;
      const code = pre.querySelector("code");
      const text = (code || pre).textContent || "";
      if (!text.trim()) return;
      _wrapCopyable(pre, () => text, _detectBlockLabel(text, code?.className || ""));
    });

    rootEl.querySelectorAll("table").forEach(table => {
      if (table.closest(".copyable-block")) return;
      const text = _tableToCopyText(table);
      if (!text.trim()) return;
      _wrapCopyable(
        table,
        () => _tableToCopyText(table),
        table.classList.contains("preview-table") ? "CSV" : "TABLE",
        table.classList.contains("preview-table") ? "copyable-table-block copyable-preview-table-block" : "copyable-table-block",
      );
    });

    rootEl.querySelectorAll("p").forEach(paragraph => {
      if (paragraph.closest(".copyable-block, pre, table")) return;
      const text = _textWithBreaks(paragraph);
      const label = _detectBlockLabel(text, "");
      if (!label || !_looksStructuredText(text, label)) return;
      _wrapCopyable(paragraph, () => _textWithBreaks(paragraph), label, "copyable-text-block");
    });
  }

  function _wrapCopyable(node, getText, label = "", extraClass = "") {
    if (!node?.parentNode || node.closest(".copyable-block")) return;
    const visibleLabel = String(label || "").trim().toUpperCase() === "TEXT" ? "" : label;
    const wrap = document.createElement("div");
    wrap.className = `copyable-block ${extraClass}`.trim();
    if (visibleLabel) wrap.dataset.copyLabel = visibleLabel;
    node.parentNode.insertBefore(wrap, node);
    wrap.appendChild(node);

    const tools = document.createElement("div");
    tools.className = "copyable-tools";
    const isTableCopyOnly = /\bcopyable-table-block\b/.test(extraClass);
    if (isTableCopyOnly) tools.style.opacity = "1";
    if (visibleLabel && !isTableCopyOnly) {
      const badge = document.createElement("span");
      badge.className = "copyable-label";
      badge.textContent = visibleLabel;
      tools.appendChild(badge);
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = "copyable-copy-btn";
    button.innerHTML = `<span class="copyable-copy-icon" aria-hidden="true">⧉</span><span class="copyable-copy-text">复制</span>`;
    button.addEventListener("click", async event => {
      event.preventDefault();
      event.stopPropagation();
      const ok = await _copyPlainText(getText());
      _setCopyButtonState(button, ok ? "已复制" : "复制失败", ok);
    });
    tools.appendChild(button);
    wrap.appendChild(tools);
  }

  async function _copyPlainText(text) {
    const value = String(text || "");
    if (!value) return false;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
        return true;
      }
    } catch (_) {}
    try {
      const area = document.createElement("textarea");
      area.value = value;
      area.setAttribute("readonly", "");
      area.style.cssText = "position:fixed;left:-9999px;top:0;opacity:0;";
      document.body.appendChild(area);
      area.select();
      const ok = document.execCommand("copy");
      area.remove();
      return ok;
    } catch (_) {
      return false;
    }
  }

  function _setCopyButtonState(button, text, ok) {
    const label = button.querySelector(".copyable-copy-text");
    const icon = button.querySelector(".copyable-copy-icon");
    if (label) label.textContent = text;
    if (icon) icon.textContent = ok ? "✓" : "!";
    button.classList.toggle("copied", ok);
    button.classList.toggle("copy-failed", !ok);
    clearTimeout(button._copyResetTimer);
    button._copyResetTimer = setTimeout(() => {
      if (label) label.textContent = "复制";
      if (icon) icon.textContent = "⧉";
      button.classList.remove("copied", "copy-failed");
    }, ok ? 1500 : 2000);
  }

  function _detectBlockLabel(text, className = "") {
    const lang = String(className || "").match(/language-([a-z0-9_+-]+)/i)?.[1]?.toUpperCase();
    if (lang) {
      if (lang === "JS") return "JS";
      if (lang === "TS") return "TS";
      if (lang === "PY") return "PYTHON";
      return lang;
    }
    const value = String(text || "").trim();
    if (!value) return "";
    if (_looksJson(value)) return "JSON";
    if (_looksSql(value)) return "SQL";
    if (_looksMarkdownTable(value)) return "TABLE";
    if (_looksCsv(value)) return "CSV";
    return "";
  }

  function _looksStructuredText(text, label) {
    const lines = String(text || "").split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    if (label === "JSON") return lines.length >= 2 || /^(?:\{|\[)/.test(String(text || "").trim());
    if (label === "SQL") return lines.length >= 1;
    return lines.length >= 2;
  }

  function _looksJson(text) {
    const value = String(text || "").trim();
    if (!/^(?:\{|\[)/.test(value) || !/(?:\}|\])$/.test(value)) return false;
    try { JSON.parse(value); return true; } catch (_) { return false; }
  }

  function _looksSql(text) {
    return /^\s*(SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|EXPLAIN)\b/i.test(String(text || ""));
  }

  function _looksMarkdownTable(text) {
    const lines = String(text || "").split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    return lines.length >= 2 && lines[0].includes("|") && /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(lines[1]);
  }

  function _looksCsv(text) {
    const lines = String(text || "").split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    if (lines.length < 2 || !lines[0].includes(",")) return false;
    const counts = lines.slice(0, Math.min(lines.length, 5)).map(line => _splitCsvLine(line).length);
    return counts[0] >= 2 && counts.filter(count => count === counts[0]).length >= Math.min(counts.length, 2);
  }

  function _splitCsvLine(line) {
    const cells = [];
    let cell = "";
    let quoted = false;
    const value = String(line || "");
    for (let i = 0; i < value.length; i += 1) {
      const ch = value[i];
      if (ch === '"' && value[i + 1] === '"') {
        cell += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = !quoted;
      } else if (ch === "," && !quoted) {
        cells.push(cell);
        cell = "";
      } else {
        cell += ch;
      }
    }
    cells.push(cell);
    return cells;
  }

  function _textWithBreaks(node) {
    const parts = [];
    const walk = current => {
      current.childNodes.forEach(child => {
        if (child.nodeType === Node.TEXT_NODE) {
          parts.push(child.nodeValue || "");
        } else if (child.nodeName === "BR") {
          parts.push("\n");
        } else {
          walk(child);
        }
      });
    };
    walk(node);
    return parts.join("").replace(/\u00a0/g, " ").trim();
  }

  function _tableToCopyText(table) {
    const rows = [...table.querySelectorAll("tr")].map(row => [...row.children]);
    if (!rows.length) return "";
    const skipFirst = table.classList.contains("preview-table")
      && rows.some(row => row[0]?.classList?.contains("preview-rn"));
    const data = rows.map(row => row
      .slice(skipFirst ? 1 : 0)
      .map(cell => (cell.textContent || "").trim()));
    if (table.classList.contains("preview-table")) {
      return data.map(row => row.map(_csvCell).join(",")).join("\n");
    }
    const header = data[0] || [];
    const body = data.slice(1);
    const separator = header.map(() => "---");
    return [header, separator, ...body]
      .filter(row => row.length)
      .map(row => `| ${row.map(cell => cell.replace(/\|/g, "\\|")).join(" | ")} |`)
      .join("\n");
  }

  function _csvCell(value) {
    const text = String(value ?? "");
    return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  }

  function _replaceWithLink(img, src) {
    const link = document.createElement("a");
    link.href   = src;
    link.target = "_blank";
    link.rel    = "noopener";
    link.textContent = "🖼️ " + (img.alt || "查看图片（点击打开原链接）");
    link.style.cssText = "display:inline-block;padding:6px 10px;background:#f1f5f9;" +
      "border-radius:6px;font-size:13px;color:#3b82f6;text-decoration:none;";
    img.replaceWith(link);
  }

  export function appendMsg(role, text, options = {}) {
    const chatUi = getUiIsland("chat");
    if (chatUi?.appendMsg) {
      const vueEl = chatUi.appendMsg(role, text, options);
      if (vueEl) {
        bindBubbleImages(vueEl.querySelector(".msg-bubble"));
        scrollBottom();
        return vueEl;
      }
    }

    const msgs = $("messages");
    const div  = document.createElement("div");
    div.className = `msg ${role}`;
    if (options.variant) div.classList.add(`msg-${options.variant}`);
    const avatar = role === "user"
      ? "👤"
      : `<img class="assistant-avatar-img" src="/static/Images/icon.png?v=brand-8" alt="AI">`;
    div.innerHTML = `
      <div class="msg-avatar">${avatar}</div>
      <div class="msg-body">
        <div class="tool-steps"></div>
        <div class="msg-bubble">${text !== null ? renderMd(text) : ""}</div>
      </div>`;
    msgs.appendChild(div);
    // 绑定气泡内图片交互
    bindBubbleImages(div.querySelector(".msg-bubble"));
    scrollBottom();
    return div;
  }

  export function sysMsg(text) {
    const chatUi = getUiIsland("chat");
    if (chatUi?.sysMsg) {
      const vueEl = chatUi.sysMsg(text);
      scrollBottom();
      return vueEl;
    }

    const msgs = $("messages");
    const d = document.createElement("div");
    d.className = "sys-msg";
    d.style.cssText = "text-align:center;font-size:12px;color:#94a3b8;padding:3px 0;";
    d.textContent = text;
    msgs.appendChild(d);
  }

  export function clearMessages() {
    const chatUi = getUiIsland("chat");
    if (chatUi?.clear) {
      chatUi.clear();
    }
    document.querySelectorAll(".msg, .sys-msg").forEach(el => el.remove());
  }

  function fmtK(n) { return n >= 1000 ? (n / 1000).toFixed(1) + "K" : String(n); }

  export function updateTokenBar() {
    const wrap  = $("token-bar-wrap");
    const fill  = $("token-bar-fill");
    const label = $("token-bar-label");
    const { promptTokens, totalInput, totalOutput, contextWindow } = state.tokenState;

    if (!wrap || !fill || !label) return;
    if (!promptTokens && !totalInput) { wrap.classList.remove("visible"); return; }
    wrap.classList.add("visible");

    // Toggle warn/crit modifiers without touching the base class, so the same
    // function works for both the legacy .token-bar-fill and the new
    // .token-pill-fill (only the modifier classes need to flip).
    fill.classList.remove("warn", "crit");

    if (contextWindow) {
      const pct = Math.min(promptTokens / contextWindow * 100, 100);
      fill.style.width = pct + "%";
      if      (pct >= 85) fill.classList.add("crit");
      else if (pct >= 60) fill.classList.add("warn");
      label.textContent = t('ctx.bar', {
        used:  fmtK(promptTokens),
        total: fmtK(contextWindow),
        pct:   pct.toFixed(1),
      });
    } else {
      fill.style.width = "0%";
      label.textContent = t('token.bar', { input: fmtK(totalInput), output: fmtK(totalOutput) });
    }
  }

  export function showStatus() {
    const provKey   = $("model-sel").value;
    const cfg       = state.modelConfigs[provKey] || {};
    const modelName = cfg.model || provKey || t('status.no_model');
    const ctx       = state.tokenState.contextWindow;
    const pct       = (ctx && state.tokenState.promptTokens)
      ? ` (${(state.tokenState.promptTokens / ctx * 100).toFixed(1)}%)`
      : "";

    const lines = [
      t('status.line.model', { v: modelName }),
      t('status.line.src',   { v: state.srcConnected ? state.srcName : t('sidebar.disconnected') }),
      ``,
      t('status.line.usage'),
      t('status.line.input',  { v: state.tokenState.totalInput.toLocaleString() }),
      t('status.line.output', { v: state.tokenState.totalOutput.toLocaleString() }),
      ctx
        ? t('status.line.ctx',      { used: state.tokenState.promptTokens.toLocaleString(), total: ctx.toLocaleString(), pct })
        : t('status.line.ctx_none', { used: state.tokenState.promptTokens.toLocaleString() }),
    ];

    const aEl = appendMsg("assistant", null);
    const bubble = aEl.querySelector(".msg-bubble");
    bubble.innerHTML = renderMd(lines.join("\n"));
    bindBubbleImages(bubble);
    scrollBottom();
  }
