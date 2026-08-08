import { useEffect, useState } from 'react';
import { fetchArray, api } from '../../lib/api';
import DeveloperLayout from '../../components/DeveloperLayout';

export default function WidgetIntegration() {
  const [chatbots, setChatbots] = useState<any[]>([]);
  const [selectedBot, setSelectedBot] = useState('');
  const [theme, setTheme] = useState('light');
  const [snippet, setSnippet] = useState('');
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchArray<any>('/chatbots')
      .then((data) => { setChatbots(data); setLoading(false); })
      .catch((e: any) => { setError(e.message); setLoading(false); });
  }, []);

  const generateSnippet = async () => {
    if (!selectedBot) return;
    try {
      const res = await api.get<any>(`/developer/widget-snippet?chatbot_id=${selectedBot}&theme=${theme}`);
      setSnippet(res.snippet);
      setCopied(false);
    } catch {}
  };

  useEffect(() => { if (selectedBot) generateSnippet(); }, [selectedBot, theme]);

  return (
    <DeveloperLayout>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Widget Integration</h2>

      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Select Chatbot</label>
          <select
            value={selectedBot}
            onChange={(e) => setSelectedBot(e.target.value)}
            className="border rounded-md px-3 py-2 w-full"
          >
            <option value="">— Select a chatbot —</option>
            {chatbots.map((bot: any) => (
              <option key={bot.id} value={bot.id}>{bot.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Theme</label>
          <select
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            className="border rounded-md px-3 py-2 w-full"
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </div>

        {snippet && (
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-sm font-medium text-gray-700">Embed Code</label>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(snippet);
                  setCopied(true);
                }}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <pre className="bg-gray-50 p-4 rounded text-sm overflow-x-auto border">
              {snippet}
            </pre>
          </div>
        )}

        {loading && <p className="text-gray-500">Loading chatbots...</p>}
        {error && <p className="text-red-500 mb-4">{error}</p>}
        {!selectedBot && !loading && !error && (
          <div className="bg-blue-50 text-blue-700 px-4 py-3 rounded">
            Select a chatbot to generate your widget embed code.
          </div>
        )}
      </div>
    </DeveloperLayout>
  );
}
