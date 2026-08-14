import { useEffect, useState } from 'react';
import { fetchArray, api } from '../../lib/api';
import DashboardLayout from '../../components/DashboardLayout';

interface Chatbot {
  id: string;
  name: string;
  description: string;
  behaviour: string;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export default function ChatbotsList() {
  const [chatbots, setChatbots] = useState<Chatbot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Chatbot | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const fetchChatbots = async () => {
    if (!mounted) return;
    try {
      setLoading(true);
      setError(null);
      const data = await fetchArray<Chatbot>('/chatbots');
      setChatbots(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (mounted) fetchChatbots();
  }, [mounted]);

  const deleteChatbot = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    setError(null);
    try {
      await api.delete(`/chatbots/${pendingDelete.id}`);
      setPendingDelete(null);
      fetchChatbots();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Chatbots</h2>
        <a href="/dashboard/chatbots/new" className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700">
          Create Chatbot
        </a>
      </div>

      {loading && <p className="text-gray-500">Loading...</p>}
      {error && <p className="text-red-500 mb-4">{error}</p>}

      {!loading && !error && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {chatbots.length === 0 ? (
            <div className="p-12 text-center">
              <p className="text-gray-500 mb-4">No chatbots yet</p>
              <a href="/dashboard/chatbots/new" className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 inline-block">
                Create your first chatbot
              </a>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Behaviour</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {chatbots.map((bot: Chatbot) => (
                  <tr key={bot.id}>
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">{bot.name}</div>
                      {bot.description && <div className="text-sm text-gray-500 truncate max-w-xs">{bot.description}</div>}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        bot.behaviour === 'fast' ? 'bg-green-100 text-green-800' :
                        bot.behaviour === 'balanced' ? 'bg-blue-100 text-blue-800' :
                        'bg-purple-100 text-purple-800'
                      }`}>
                        {bot.behaviour}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {bot.created_at ? new Date(bot.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <a href={`/dashboard/chatbots/${bot.id}`} className="text-blue-600 hover:text-blue-900 mr-3">Edit</a>
                      <button
                        onClick={() => setPendingDelete(bot)}
                        className="text-red-600 hover:text-red-900"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {pendingDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Delete Chatbot</h3>
            <p className="text-gray-600 text-sm mb-6">
              Are you sure you want to delete "{pendingDelete.name}"? This will permanently remove
              the chatbot and all of its data. This action cannot be undone.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setPendingDelete(null)}
                disabled={deleting}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md text-sm hover:bg-gray-300 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={deleteChatbot}
                disabled={deleting}
                className="px-4 py-2 bg-red-600 text-white rounded-md text-sm hover:bg-red-700 disabled:opacity-50"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}