import { useState } from 'react';
import { useRouter } from 'next/router';
import { api } from '../../../lib/api';
import DashboardLayout from '../../../components/DashboardLayout';

const BEHAVIOUR_OPTIONS = [
  { value: 'fast', label: 'Fast', description: 'Low cost, good for simple queries', model: 'GPT-3.5 Turbo' },
  { value: 'balanced', label: 'Balanced', description: 'Best price/performance for most use cases', model: 'GPT-4o Mini' },
  { value: 'accurate', label: 'Accurate', description: 'Highest quality, higher cost', model: 'GPT-4o' },
];

export default function ChatbotCreate() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [behaviour, setBehaviour] = useState('balanced');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.post<any>('/chatbots', { name, description, behaviour });
      setSuccess(true);
      setTimeout(() => router.push(`/dashboard/chatbots/${res.id}`), 1000);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-2xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-900">Create Chatbot</h2>
          <a href="/dashboard/chatbots" className="text-sm text-gray-600 hover:text-gray-900">← Back to list</a>
        </div>

        {success && (
          <div className="bg-green-50 text-green-700 px-4 py-3 rounded mb-4">
            Chatbot created successfully! Redirecting...
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-6">
          {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded">{error}</div>}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border rounded-md px-3 py-2"
              required
              placeholder="e.g., Customer Support Bot"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full border rounded-md px-3 py-2"
              rows={3}
              placeholder="What does this chatbot do?"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Model Tier *</label>
            <div className="space-y-3">
              {BEHAVIOUR_OPTIONS.map((opt) => (
                <label key={opt.value} className={`flex items-start p-4 border rounded-lg cursor-pointer transition ${behaviour === opt.value ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                  <input
                    type="radio"
                    name="behaviour"
                    value={opt.value}
                    checked={behaviour === opt.value}
                    onChange={() => setBehaviour(opt.value)}
                    className="mt-1 mr-3 h-4 w-4 text-blue-600"
                  />
                  <div>
                    <div className="flex items-center">
                      <span className="font-medium text-gray-900">{opt.label}</span>
                      <span className="ml-2 text-xs text-gray-500">({opt.model})</span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{opt.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <button type="button" onClick={() => router.push('/dashboard/chatbots')} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md text-sm hover:bg-gray-300">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50">
              {loading ? 'Creating...' : 'Create Chatbot'}
            </button>
          </div>
        </form>
      </div>
    </DashboardLayout>
  );
}