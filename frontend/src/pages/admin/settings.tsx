import { useEffect, useState } from 'react';
import AdminLayout from '../../components/AdminLayout';

export default function AdminSettings() {
  const [configs, setConfigs] = useState<any[]>([]);
  const [editing, setEditing] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetch('/api/v1/admin/system-config', {
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
    })
      .then((r) => r.json())
      .then(setConfigs)
      .catch(() => {});
  }, []);

  const saveConfig = async (key: string) => {
    try {
      const parsed = JSON.parse(editValue);
      await fetch(`/api/v1/admin/system-config/${key}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify(parsed),
      });
      setMessage(`Config "${key}" updated`);
      setEditing(null);
    } catch {
      setMessage('Invalid JSON value');
    }
  };

  const defaults = [
    { key: 'default_behaviour', value: { behaviour: 'balanced' }, description: 'Default chatbot behaviour' },
    { key: 'rate_limits', value: { per_ip: '100/minute', per_org: '1000/minute' }, description: 'Rate limit settings' },
    { key: 'max_file_size_mb', value: { max_size: 50 }, description: 'Max upload file size in MB' },
  ];

  return (
    <AdminLayout>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">System Settings</h2>
      {message && (
        <div className="bg-green-50 text-green-700 px-4 py-2 rounded mb-4">{message}</div>
      )}
      <div className="space-y-4">
        {(configs.length > 0 ? configs : defaults).map((cfg: any) => (
          <div key={cfg.key} className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-lg font-medium text-gray-900">{cfg.key}</h3>
                <p className="text-sm text-gray-500">{cfg.description || ''}</p>
              </div>
              <button
                onClick={() => {
                  setEditing(cfg.key);
                  setEditValue(JSON.stringify(cfg.value, null, 2));
                }}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Edit
              </button>
            </div>
            <pre className="mt-2 bg-gray-50 p-3 rounded text-sm">{JSON.stringify(cfg.value, null, 2)}</pre>
            {editing === cfg.key && (
              <div className="mt-4">
                <textarea
                  className="w-full border rounded-md p-2 text-sm font-mono"
                  rows={4}
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                />
                <div className="mt-2 space-x-2">
                  <button
                    onClick={() => saveConfig(cfg.key)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setEditing(null)}
                    className="px-4 py-2 bg-gray-200 rounded-md text-sm"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </AdminLayout>
  );
}
