// Chat logic for TQ GenAI Chat
import { sendChatMessage } from './api.js';

export async function handleSendMessage(message, provider, model) {
  const data = { message, provider, model };
  return await sendChatMessage(data);
}
