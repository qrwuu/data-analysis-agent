(function () {
  const endpoint = "/api/system/frontend-error";

  function post(payload) {
    const body = JSON.stringify({
      userAgent: navigator.userAgent,
      url: location.href,
      ...payload,
    });
    try {
      if (navigator.sendBeacon) {
        const blob = new Blob([body], { type: "application/json" });
        navigator.sendBeacon(endpoint, blob);
        return;
      }
    } catch (_) {}
    try {
      fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true,
      }).catch(() => {});
    } catch (_) {}
  }

  const seen = new Set();
  function report(level, message, details) {
    const key = `${level}:${message}:${details?.source || ""}:${details?.lineno || ""}:${details?.colno || ""}`;
    if (seen.has(key)) return;
    seen.add(key);
    post({ level, message, ...details });
  }

  function mark(stage, extra) {
    post({ level: "info", message: `boot:${stage}`, stage, extra: extra || null });
  }

  window.__BAA_BOOT_GUARD = { report, mark };
  mark("bootstrap-script-loaded");

  window.addEventListener("error", function (event) {
    const target = event.target;
    if (target && target !== window) {
      report("resource", `resource-load-failed: ${target.tagName || "unknown"}`, {
        source: target.src || target.href || "",
        stage: document.body?.dataset?.appBoot || "resource",
      });
      return;
    }
    report("error", event.message || "window-error", {
      source: event.filename || "",
      lineno: event.lineno || 0,
      colno: event.colno || 0,
      stack: event.error?.stack || "",
      stage: document.body?.dataset?.appBoot || "window-error",
    });
  }, true);

  window.addEventListener("unhandledrejection", function (event) {
    const reason = event.reason;
    report("promise", String(reason?.message || reason || "unhandledrejection"), {
      stack: reason?.stack || "",
      stage: document.body?.dataset?.appBoot || "promise",
    });
  });

  document.addEventListener("DOMContentLoaded", function () {
    mark("dom-content-loaded");
    setTimeout(function () {
      if (document.body?.dataset?.appBoot !== "ready") {
        report("timeout", "appBoot-not-ready", {
          stage: document.body?.dataset?.appBoot || "unknown",
          extra: {
            title: document.title,
            readyState: document.readyState,
            uiRefine: document.body?.dataset?.uiRefine || "",
          },
        });
      }
    }, 7000);
  }, { once: true });

  window.addEventListener("load", function () {
    mark("window-load", { appBoot: document.body?.dataset?.appBoot || "" });
  }, { once: true });
})();
