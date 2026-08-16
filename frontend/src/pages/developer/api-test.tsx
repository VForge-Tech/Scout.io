import { useEffect, useState } from 'react';
import { fetchArray, api } from '../../lib/api';
import DeveloperLayout from '../../components/DeveloperLayout';
import FeedbackWidget from '../../components/FeedbackWidget';

export default function ApiTestPage() {
  const [chatbots, setChatbots] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'internal' | 'connectivity' | 'chatbot'>('internal');
  const [internalResults, setInternalResults] = useState<any[]>([]);
  const [connectivityResults, setConnectivityResults] = useState<any[]>([]);
  const [chatbotTestResult, setChatbotTestResult] = useState<any>(null);
  const [selectedChatbot, setSelectedChatbot] = useState('');
  const [testMessage, setTestMessage] = useState('Hello, what can you do?');
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    fetchArray<any>('/chatbots')
      .then(setChatbots)
      .catch(() => {});
  }, [mounted]);

  const getToken = () => {
    if (!mounted) return '';
    return localStorage.getItem('access_token') || '';
  };

  const runConnectivityTest = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<any[]>('/developer/connectivity-test');
      setConnectivityResults(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const testInternalEndpoint = async (endpoint: string, method: string = 'GET') => {
    setLoading(true);
    setError(null);
    try {
      const token = getToken();
      const res = await api.post<any>('/developer/api-test', {
        endpoint,
        method,
        headers: { Authorization: `Bearer ${token}` }
      });
      setInternalResults([res, ...internalResults.slice(0, 9)]);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const testChatbot = async () => {
    if (!selectedChatbot) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.post<any>(`/developer/test-chatbot/${selectedChatbot}`, {
        message: testMessage
      });
      setChatbotTestResult(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-100 text-green-800';
      case 'degraded': return 'bg-yellow-100 text-yellow-800';
      case 'unhealthy': return 'bg-red-100 text-red-800';
      case 'disabled': return 'bg-gray-100 text-gray-800';
      case 'not_configured': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const internalEndpoints = [
    { method: 'GET', path: '/health', desc: 'Basic health check' },
    { method: 'GET', path: '/health/ready', desc: 'Readiness with dependencies' },
    { method: 'GET', path: '/auth/me', desc: 'Get current user' },
    { method: 'GET', path: '/organizations/me', desc: 'Get current organization' },
    { method: 'GET', path: '/chatbots', desc: 'List chatbots' },
    { method: 'GET', path: '/knowledge-sources', desc: 'List knowledge sources' },
    { method: 'GET', path: '/developer/api-keys', desc: 'List API keys' },
    { method: 'GET', path: '/developer/widget-snippet', desc: 'Get widget embed code' },
    { method: 'GET', path: '/debug/retrieve?q=test', desc: 'Debug retrieval' },
  ];

  return (
    <DeveloperLayout>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">API Testing</h2>

      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-2 rounded mb-4">{error}</div>
      )}

      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-4" aria-label="Tabs">
          <button
            onClick={() => setActiveTab('internal')}
            className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'internal'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Internal APIs
          </button>
          <button
            onClick={() => setActiveTab('connectivity')}
            className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'connectivity'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            External Connectivity
          </button>
          <button
            onClick={() => setActiveTab('chatbot')}
            className={`py-2 px-4 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'chatbot'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Chatbot Test
          </button>
        </nav>
      </div>

      {activeTab === 'internal' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium mb-4">Test Internal Endpoints</h3>
            <p className="text-sm text-gray-500 mb-4">Click any endpoint to test it with your current authentication.</p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {internalEndpoints.map((ep) => (
                <button
                  key={ep.path}
                  onClick={() => testInternalEndpoint(ep.path, ep.method)}
                  disabled={loading}
                  className="p-4 border rounded-lg text-left hover:bg-gray-50 transition-colors disabled:opacity-50"
                >
                  <div className="flex items-center space-x-2 mb-1">
                    <span className={`px-2 py-0.5 text-xs font-mono rounded ${
                      ep.method === 'GET' ? 'bg-green-100 text-green-800' :
                      ep.method === 'POST' ? 'bg-blue-100 text-blue-800' :
                      ep.method === 'PATCH' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>{ep.method}</span>
                    <span className="text-xs text-gray-500 font-mono">{ep.path}</span>
                  </div>
                  <p className="text-sm text-gray-600">{ep.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {internalResults.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium mb-4">Recent Test Results</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Endpoint</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Status</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Time</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Response</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {internalResults.map((r, i) => (
                      <tr key={i}>
                        <td className="px-4 py-2 text-sm font-mono text-gray-900">{r.endpoint || 'N/A'}</td>
                        <td className="px-4 py-2">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            r.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                            {r.success ? 'Success' : `Error ${r.status_code}`}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-500">{r.response_time_ms}ms</td>
                        <td className="px-4 py-2 text-sm text-gray-500 max-w-xs truncate">
                          {r.error || (r.response_data ? JSON.stringify(r.response_data).slice(0, 100) : '—')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'connectivity' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium">External Service Connectivity</h3>
            <button
              onClick={runConnectivityTest}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm disabled:opacity-50"
            >
              {loading ? 'Testing...' : 'Run Connectivity Test'}
            </button>
          </div>

          {connectivityResults.length > 0 && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {connectivityResults.map((r) => (
                <div key={r.service} className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-gray-900 capitalize">{r.service}</h4>
                    <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(r.status)}`}>
                      {r.status}
                    </span>
                  </div>
                  {r.response_time_ms && (
                    <p className="text-sm text-gray-500 mb-2">Response: {r.response_time_ms}ms</p>
                  )}
                  {r.details && (
                    <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-32">
                      {JSON.stringify(r.details, null, 2)}
                    </pre>
                  )}
                  {r.error && (
                    <p className="text-sm text-red-600 mt-2">{r.error}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'chatbot' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium mb-4">Test Chatbot Interaction</h3>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Select Chatbot</label>
              <select
                value={selectedChatbot}
                onChange={(e) => setSelectedChatbot(e.target.value)}
                className="border rounded-md px-3 py-2 w-full"
              >
                <option value="">— Select a chatbot —</option>
                {chatbots.map((bot: any) => (
                  <option key={bot.id} value={bot.id}>{bot.name} ({bot.behaviour})</option>
                ))}
              </select>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Test Message</label>
              <textarea
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                rows={3}
                className="border rounded-md px-3 py-2 w-full"
              />
            </div>

            <button
              onClick={testChatbot}
              disabled={loading || !selectedChatbot}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm disabled:opacity-50"
            >
              {loading ? 'Testing...' : 'Test Chatbot'}
            </button>
          </div>

          {chatbotTestResult && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium mb-4">Test Result</h3>
              <div className="space-y-3">
                <div>
                  <span className="font-medium text-gray-700">Chatbot:</span>
                  <span className="ml-2 text-gray-900">{chatbotTestResult.chatbot_name}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Behaviour:</span>
                  <span className="ml-2 text-gray-900">{chatbotTestResult.behaviour}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Response Time:</span>
                  <span className="ml-2 text-gray-900">{chatbotTestResult.response_time_ms}ms</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Cached:</span>
                  <span className="ml-2 text-gray-900">{chatbotTestResult.cached ? 'Yes' : 'No'}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Query:</span>
                  <p className="mt-1 text-gray-900 bg-gray-50 p-3 rounded">{chatbotTestResult.query}</p>
                </div>
                <div>
                  <span className="font-medium text-gray-700">Response:</span>
                  <p className="mt-1 text-gray-900 bg-gray-50 p-3 rounded whitespace-pre-wrap">{chatbotTestResult.response}</p>
                </div>
              </div>
              <div className="mt-4">
                <FeedbackWidget
                  context="chatbot_test"
                  chatbotId={selectedChatbot}
                  prompt="Did the test chatbot give you a useful answer?"
                />
              </div>
            </div>
          )}
        </div>
      )}
    </DeveloperLayout>
  );
}