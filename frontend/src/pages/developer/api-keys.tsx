import { useEffect, useState } from 'react';
import DeveloperLayout from '../../components/DeveloperLayout';

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [newKey, setNewKey] = useState<any>(null);
  const [keyName, setKeyName] = useState('');
  const [message, setMessage] = useState('');

  const fetchKeys = () => {
    fetch('/api/v1/developer/api-keys', {
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
    })
      .then((r) => r.json())
      .then((d) => { setKeys(d); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { fetchKeys(); }, []);

  const createKey = async () => {
    try {
      const res = await fetch('/api/v1/developer/api-keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({ name: keyName, expires_in_days: 365 }),
      });
      const data = await res.json();
      setNewKey(data);
      setShowNew(false);
      setKeyName('');
      fetchKeys();
    } catch (e: any) {
      setMessage(e.message);
    }
  };

  const revokeKey = async (id: string) => {
    await fetch(`/api/v1/developer/api-keys/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
    });
    fetchKeys();
  };

  return (
    <DeveloperLayout>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">API Keys</h2>
        <button
          onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm"
        >
          Create Key
        </button>
      </div>

      {message && (
        <div className="bg-red-50 text-red-700 px-4 py-2 rounded mb-4">{message}</div>
      )}

      {showNew && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-medium mb-4">New API Key</h3>
          <input
            type="text"
            placeholder="Key name"
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
            className="border rounded-md px-3 py-2 w-full mb-4"
          />
          <button onClick={createKey} className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm">
            Generate
          </button>
          <button onClick={() => setShowNew(false)} className="ml-2 px-4 py-2 bg-gray-200 rounded-md text-sm">
            Cancel
          </button>
        </div>
      )}

      {newKey && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
          <h3 className="text-lg font-medium text-yellow-800 mb-2">Key Created - Copy it now!</h3>
          <p className="text-sm text-yellow-700 mb-2">This key will only be shown once.</p>
          <code className="block bg-white p-3 rounded border text-sm font-mono break-all">
            {newKey.full_key}
          </code>
          <button
            onClick={() => { navigator.clipboard.writeText(newKey.full_key); setMessage('Copied!'); }}
            className="mt-2 px-4 py-2 bg-yellow-600 text-white rounded-md text-sm"
          >
            Copy to Clipboard
          </button>
        </div>
      )}

      {loading && <p className="text-gray-500">Loading...</p>}
      {!loading && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Prefix</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Expires</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {keys.map((key: any) => (
                <tr key={key.id}>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{key.name}</td>
                  <td className="px-6 py-4 text-sm text-gray-500 font-mono">{key.key_prefix}...</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      key.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {key.is_active ? 'Active' : 'Revoked'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {key.expires_at ? new Date(key.expires_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {key.is_active && (
                      <button onClick={() => revokeKey(key.id)} className="text-red-600 hover:text-red-900">
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </DeveloperLayout>
  );
}
