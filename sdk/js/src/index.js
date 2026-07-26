class ScoutClient {
  constructor({ apiKey, baseUrl = "https://api.scout.io" }) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }

  async _request(method, path, body) {
    const url = `${this.baseUrl}${path}`;
    const res = await fetch(url, {
      method,
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`Scout API error: ${res.status}`);
    return res.json();
  }

  async sendMessage(chatbotId, content, sessionId) {
    return this._request("POST", `/api/v1/widget/chatbots/${chatbotId}/messages`, {
      content,
      session_id: sessionId,
    });
  }

  async getHistory(sessionId) {
    return this._request("GET", `/api/v1/widget/sessions/${sessionId}/messages`);
  }

  async searchKnowledge(organizationId, query, topK = 5) {
    return this._request("POST", "/api/v1/retrieval/search", {
      organization_id: organizationId,
      query,
      top_k: topK,
    });
  }
}

module.exports = { ScoutClient };
