import { useEffect, useState } from 'react';
import DeveloperLayout from '../../components/DeveloperLayout';

export default function DeveloperDashboard() {
  const [keys, setKeys] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/v1/developer/api-keys', {
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
    })
      .then((r) => r.json())
      .then((d) => { setKeys(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return (
    <DeveloperLayout>
      <h2 className="text-2xl font-bold text-gray-900">Developer Portal</h2>
      <p className="mt-2 text-gray-600">Manage your API keys and integrations.</p>

      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <a href="/developer/api-keys" className="bg-white rounded-lg shadow p-6 hover:shadow-md transition">
          <h3 className="text-lg font-medium text-gray-900">🔑 API Keys</h3>
          <p className="mt-2 text-sm text-gray-600">Manage API keys ({keys.length} active)</p>
        </a>
        <a href="/developer/docs" className="bg-white rounded-lg shadow p-6 hover:shadow-md transition">
          <h3 className="text-lg font-medium text-gray-900">📖 API Documentation</h3>
          <p className="mt-2 text-sm text-gray-600">Explore the Scout API</p>
        </a>
        <a href="/developer/widget" className="bg-white rounded-lg shadow p-6 hover:shadow-md transition">
          <h3 className="text-lg font-medium text-gray-900">💬 Widget Integration</h3>
          <p className="mt-2 text-sm text-gray-600">Embed the chat widget</p>
        </a>
      </div>
    </DeveloperLayout>
  );
}
