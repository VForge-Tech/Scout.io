import { useCallback, useEffect, useRef, useState } from 'react';
import { api, streamRequest, SSEEvent } from '../../lib/api';
import DashboardLayout from '../../components/DashboardLayout';

interface PlaygroundChatbot {
  id: string;
  name: string;
  behaviour: string;
}

interface PlayMessage {
  role: 'user' | 'assistant';
  content: string;
}

export default function Playground() {
  const [chatbots, setChatbots] = useState<PlaygroundChatbot[]>([]);
  const [chatbotId, setChatbotId] = useState('');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<PlayMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [latency, setLatency] = useState<{ ttft: number; total: number } | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.get<PlaygroundChatbot[]>('/chatbots');
        if (cancelled) return;
        setChatbots(data);
        if (data.length > 0) setChatbotId((prev) => prev || data[0].id);
      } catch (e: any) {
        if (!cancelled) setError(e.message || 'Failed to load chatbots');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const send = useCallback(async () => {
    const content = input.trim();
    if (!content || !chatbotId || streaming) return;
    setInput('');
    setError('');
    setLatency(null);
    setMessages((prev) => [...prev, { role: 'user', content }, { role: 'assistant', content: '' }]);
    setStreaming(true);

    let acc = '';
    try {
      await streamRequest(`/chatbots/${chatbotId}/messages/stream`, { content }, (evt: SSEEvent) => {
        if (evt.type === 'token') {
          acc += String(evt.content ?? '');
          setMessages((prev) => [...prev.slice(0, -1), { role: 'assistant', content: acc }]);
        } else if (evt.type === 'done') {
          if (typeof evt.reply === 'string') acc = evt.reply;
          setMessages((prev) => [...prev.slice(0, -1), { role: 'assistant', content: acc }]);
          setLatency({
            ttft: Number(evt.time_to_first_token_ms) || 0,
            total: Number(evt.total_latency_ms) || 0,
          });
        } else if (evt.type === 'error') {
          setError(String(evt.message ?? 'Stream error'));
        }
      });
    } catch (e: any) {
      setError(e.message || 'Failed to send message');
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: acc || 'Sorry, I encountered an error. Please try again.' },
      ]);
    } finally {
      setStreaming(false);
    }
  }, [chatbotId, input, streaming]);

  const messagesEndRef = useAutoScroll(messages);

  return (
    <DashboardLayout>
      <div className="max-w-4xl">
        <h2 className="text-2xl font-bold text-gray-900">Streaming Playground</h2>
        <p className="text-sm text-gray-600 mt-1 mb-6">
          Send a test message and watch the exact token-by-token behavior your end users
          see in the widget — including time-to-first-token and total latency.
        </p>

        {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded mb-6">{error}</div>}

        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">Chatbot</label>
          <select
            value={chatbotId}
            onChange={(e) => setChatbotId(e.target.value)}
            disabled={streaming}
            className="w-full border rounded-md px-3 py-2"
          >
            {chatbots.length === 0 && <option value="">No chatbots yet</option>}
            {chatbots.map((b) => (
              <option key={b.id} value={b.id}>{b.name} ({b.behaviour})</option>
            ))}
          </select>
        </div>

        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">Conversation</h3>
            {streaming && (
              <span className="inline-flex items-center px-2 py-1 text-xs text-blue-700 bg-blue-50 rounded-full">
                <span className="w-2 h-2 bg-blue-600 rounded-full mr-2 animate-pulse" />
                Typing…
              </span>
            )}
          </div>

          <div className="border rounded-lg p-4 space-y-3 max-h-96 overflow-y-auto bg-gray-50">
            {messages.length === 0 ? (
              <p className="text-gray-400 text-sm text-center py-8">
                Select a chatbot and send a message to begin
              </p>
            ) : (
              messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[80%] px-4 py-2 rounded-lg text-sm whitespace-pre-wrap ${
                      m.role === 'user'
                        ? 'bg-blue-600 text-white rounded-br-none'
                        : 'bg-white border rounded-bl-none'
                    }`}
                  >
                    {m.content || '…'}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {latency && !streaming && (
            <div className="flex space-x-4 mt-4 text-sm">
              <div className="px-3 py-2 bg-gray-100 rounded-md">
                <span className="text-gray-500">Time to first token: </span>
                <span className="font-semibold text-gray-900">{latency.ttft.toFixed(0)} ms</span>
              </div>
              <div className="px-3 py-2 bg-gray-100 rounded-md">
                <span className="text-gray-500">Total latency: </span>
                <span className="font-semibold text-gray-900">{latency.total.toFixed(0)} ms</span>
              </div>
            </div>
          )}

          <div className="mt-4 flex space-x-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              disabled={streaming || !chatbotId}
              placeholder="Type a test message… (Enter to send)"
              rows={2}
              className="flex-1 border rounded-md px-3 py-2 disabled:opacity-50"
            />
            <button
              onClick={send}
              disabled={streaming || !chatbotId || !input.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {streaming ? 'Streaming…' : 'Send'}
            </button>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}

function useAutoScroll(deps: unknown[]) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: 'smooth' });
  }, deps);
  return ref;
}