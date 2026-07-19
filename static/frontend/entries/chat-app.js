window.__BAA_BOOT_GUARD?.mark?.("entry-chat-app");
// Ordered compatibility entry for the complete chat application.
// Keep side-effect imports aligned with the former template script order.
import "../legacy/i18n.js";
import "../legacy/state.js";
import "./legacy-core.js?v=kb-form-sync-1";
import "../legacy/markdown.js";
import "./legacy-ui.js?v=kb-form-sync-1";
import "../legacy/msg.js?v=copy-label-2";
import "../legacy/command_handlers.js";
import "../legacy/datasource.js";
import "../legacy/preview.js";
import "./legacy-stream.js?v=slash-audit-1";
import "../legacy/app_settings.js?v=boot-fix-1";
import "../legacy/job_history.js";
import "../legacy/sessions.js";
import "../legacy/auth.js?v=preference-memory-1";
import "../legacy/autosave.js";
import "../legacy/update.js";
import "../legacy/checkpoints.js";
import "./legacy-panels.js";
import "../legacy/temp_prompt_panel.js";
import "../legacy/app.js?v=preference-memory-1";
