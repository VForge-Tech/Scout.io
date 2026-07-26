export interface ScoutClientOptions {
  apiKey: string;
  baseUrl?: string;
}

export interface MessageResponse {
  reply: string;
  session_id: string;
}

export class ScoutClient {
  constructor(options: ScoutClientOptions);
  sendMessage(chatbotId: string, content: string, sessionId?: string): Promise<MessageResponse>;
  getHistory(sessionId: string): Promise<Record<string, unknown>[]>;
  searchKnowledge(organizationId: string, query: string, topK?: number): Promise<Record<string, unknown>[]>;
}
