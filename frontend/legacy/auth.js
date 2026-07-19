import { $ } from "../core/dom.js";
import { closeOverlay, openOverlay, toast } from "../core/overlay.js";

const TOKEN_KEY = "baa_auth_token";
const USER_KEY = "baa_auth_user";
let user = null;
let quota = null;
let mode = "login";

function token() {
  return localStorage.getItem(TOKEN_KEY) || "";
}
function isLoggedIn() {
  return Boolean(user && token());
}
function authHeaders(extra = {}) {
  return token() ? { ...extra, Authorization: `Bearer ${token()}` } : extra;
}
function authFetch(url, options = {}) {
  return fetch(url, {
    ...options,
    headers: authHeaders(options.headers || {}),
  });
}

function renderAuth() {
  $("auth-login-btn")?.classList.toggle("hidden", isLoggedIn());
  $("auth-user-wrap")?.classList.toggle("hidden", !isLoggedIn());
  if (user && $("auth-user-name"))
    $("auth-user-name").textContent = user.nickname || user.email;
}

function renderQuota() {
  const summary = $("quota-summary");
  if (!summary) return;
  const used = Number(quota?.used || 0);
  const remaining = Number(quota?.remaining || 0);
  const limit = Number(quota?.daily_limit || 30);
  const blocked = Boolean(quota?.blocked_until);
  summary.textContent = !quota
    ? "正在获取…"
    : blocked
      ? "暂时受限"
      : `剩余 ${remaining} 次`;
  $("quota-used").textContent = quota ? `${used} 次` : "--";
  $("quota-remaining").textContent = quota ? `${remaining} 次` : "--";
  $("quota-limit").textContent = quota ? `${limit} 次` : "--";
  $("quota-progress").style.width = quota
    ? `${Math.min(100, Math.max(0, (used / limit) * 100))}%`
    : "0%";
  $("quota-note").textContent = !quota
    ? "正在同步你的额度信息。"
    : blocked
      ? "账号因连续异常请求暂时受限，请稍后再试。"
      : "额度按自然日重置；未使用额度不会累计到下一天。";
}

function openAuth(requested = "login") {
  if (requested === "account") {
    openAccount();
    return;
  }
  mode = requested === "register" ? "register" : "login";
  $("auth-modal-title").textContent = mode === "login" ? "登录" : "注册";
  $("auth-submit").textContent = mode === "login" ? "登录" : "注册";
  $("auth-mode-toggle").textContent =
    mode === "login" ? "注册账号" : "已有账号，去登录";
  $("auth-nickname-row").hidden = mode !== "register";
  $("auth-error").textContent = "";
  closeOverlay("ov-auth-gate");
  closeOverlay("ov-knowledge-gate");
  openOverlay("ov-auth");
}

function toggleAuthMode() {
  openAuth(mode === "login" ? "register" : "login");
}
function hasTemporaryConversation() {
  return Boolean(
    document.querySelector("#messages .msg.user, #messages .msg.assistant"),
  );
}

async function submitAuth() {
  const payload = {
    email: $("auth-email").value.trim(),
    password: $("auth-password").value,
    nickname: $("auth-nickname").value.trim(),
  };
  const response = await fetch(
    mode === "login" ? "/api/auth/login" : "/api/auth/register",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  ).catch(() => null);
  const data = response ? await response.json().catch(() => ({})) : {};
  if (!response?.ok || !data.token) {
    $("auth-error").textContent = data.error || "暂时无法完成登录，请稍后重试";
    return;
  }
  localStorage.setItem(TOKEN_KEY, data.token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
  user = data.user;
  quota = data.quota || null;
  renderAuth();
  closeOverlay("ov-auth");
  toast(mode === "login" ? "登录成功" : "注册成功", "ok");
  if (hasTemporaryConversation()) await saveTemporaryAnalysis({ silent: true });
  await window.BAA.sessions?.loadSavedList?.();
}

async function saveTemporaryAnalysis({ silent = false } = {}) {
  const sid = window.BAA.state?.SID;
  const response =
    sid &&
    (await authFetch(`/api/history/import-session/${encodeURIComponent(sid)}`, {
      method: "POST",
    }));
  const data = response ? await response.json().catch(() => ({})) : {};
  if (!response?.ok) {
    if (!silent) toast(data.error || "保存失败", "err");
    return false;
  }
  closeOverlay("ov-save-temporary");
  if (!silent) toast("当前分析已保存到历史分析", "ok");
  return true;
}

function skipTemporarySave() {
  closeOverlay("ov-save-temporary");
}
function showLoginGate() {
  openOverlay("ov-auth-gate");
}
function showKnowledgeGate() {
  openOverlay("ov-knowledge-gate");
}
function toggleAuthMenu() {
  $("auth-user-menu")?.classList.toggle("hidden");
}

function refreshQuota() {
  return authFetch("/api/auth/me")
    .then((response) => response.json())
    .then((data) => {
      if (data?.quota) {
        quota = data.quota;
        renderQuota();
      }
    })
    .catch(() => null);
}

function openQuota() {
  if (!isLoggedIn()) {
    openAuth("login");
    return;
  }
  $("auth-user-menu")?.classList.add("hidden");
  renderQuota();
  openOverlay("ov-quota");
  refreshQuota();
}

function openAccount() {
  if (!isLoggedIn()) {
    openAuth("login");
    return;
  }
  $("auth-user-menu")?.classList.add("hidden");
  $("account-email").value = user.email || "";
  $("account-nickname").value = user.nickname || "";
  $("account-error").textContent = "";
  openOverlay("ov-account");
}

function renderPreferences(items = []) {
  const list = $("preference-list");
  if (!list) return;
  list.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "preference-empty";
    empty.textContent =
      "暂未保存偏好。你也可以在对话中说“记住：默认按 GMV 统计”。";
    list.append(empty);
    return;
  }
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "preference-item";
    const content = document.createElement("span");
    content.textContent = item.content || "";
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "删除";
    remove.addEventListener("click", () => deletePreference(item.id));
    row.append(content, remove);
    list.append(row);
  }
}

async function loadPreferences() {
  const response = await authFetch("/api/preferences").catch(() => null);
  const data = response ? await response.json().catch(() => ({})) : {};
  if (!response?.ok) {
    $("preference-error").textContent = data.error || "暂时无法加载偏好记忆。";
    return;
  }
  renderPreferences(data.preferences || []);
}

function openPreferences() {
  if (!isLoggedIn()) {
    openAuth("login");
    return;
  }
  $("auth-user-menu")?.classList.add("hidden");
  $("preference-input").value = "";
  $("preference-error").textContent = "";
  renderPreferences();
  openOverlay("ov-preferences");
  loadPreferences();
}

async function savePreference() {
  const content = $("preference-input").value.trim();
  if (!content) {
    $("preference-error").textContent = "请输入偏好内容。";
    return;
  }
  const response = await authFetch("/api/preferences", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  }).catch(() => null);
  const data = response ? await response.json().catch(() => ({})) : {};
  if (!response?.ok) {
    $("preference-error").textContent = data.error || "保存偏好失败。";
    return;
  }
  $("preference-input").value = "";
  $("preference-error").textContent = "";
  await loadPreferences();
  toast("偏好已保存，新对话会自动参考。", "ok");
}

async function deletePreference(preferenceId) {
  const response = await authFetch(
    `/api/preferences/${encodeURIComponent(preferenceId)}`,
    { method: "DELETE" },
  ).catch(() => null);
  if (!response?.ok) {
    toast("删除偏好失败，请稍后再试。", "err");
    return;
  }
  await loadPreferences();
}

async function saveAccount() {
  const response = await authFetch("/api/auth/me", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nickname: $("account-nickname").value.trim() }),
  }).catch(() => null);
  const data = response ? await response.json().catch(() => ({})) : {};
  if (!response?.ok || !data.user) {
    $("account-error").textContent = data.error || "保存失败，请稍后重试";
    return;
  }
  user = data.user;
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  renderAuth();
  closeOverlay("ov-account");
  toast("账号设置已保存", "ok");
}

async function logout() {
  await authFetch("/api/auth/logout", { method: "POST" }).catch(() => null);
  closeOverlay("ov-knowledge");
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  user = null;
  quota = null;
  $("auth-user-menu")?.classList.add("hidden");
  renderAuth();
  await window.BAA.chatStream?.newChat?.();
  toast("已退出登录");
  await window.BAA.sessions?.loadSavedList?.();
}

function openMyHistory() {
  $("auth-user-menu")?.classList.add("hidden");
  window.BAA.app?.openSidebarDrawer?.("sessions");
}

async function init() {
  if (token()) {
    const response = await authFetch("/api/auth/me").catch(() => null);
    const data = response ? await response.json().catch(() => ({})) : {};
    if (response?.ok && data.user) {
      user = data.user;
      quota = data.quota || null;
    } else {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
  }
  renderAuth();
}

window.addEventListener("beforeunload", (event) => {
  if (!isLoggedIn() && hasTemporaryConversation()) {
    event.preventDefault();
    event.returnValue =
      "当前分析尚未登录保存，刷新后可能丢失。登录后可保存历史分析。";
  }
});

window.BAA = window.BAA || {};
window.BAA.auth = {
  init,
  isLoggedIn,
  authHeaders,
  authFetch,
  openAuth,
  toggleAuthMode,
  submitAuth,
  saveTemporaryAnalysis,
  skipTemporarySave,
  showLoginGate,
  showKnowledgeGate,
  toggleAuthMenu,
  openAccount,
  openQuota,
  openPreferences,
  savePreference,
  saveAccount,
  logout,
  openMyHistory,
};

export {
  init,
  isLoggedIn,
  authHeaders,
  authFetch,
  openAuth,
  toggleAuthMode,
  submitAuth,
  saveTemporaryAnalysis,
  skipTemporarySave,
  showLoginGate,
  showKnowledgeGate,
  toggleAuthMenu,
  openAccount,
  openQuota,
  openPreferences,
  savePreference,
  saveAccount,
  logout,
  openMyHistory,
};
