import { chatStream } from "../features/chat-stream.js?v=slash-audit-1";

const baa = globalThis.BAA || {};
baa.chatStream = chatStream;
globalThis.BAA = baa;
