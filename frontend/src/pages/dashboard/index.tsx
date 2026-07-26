import { useEffect, useState } from 'react';
import Layout from '../../components/Layout';

export default function Dashboard() {
  const [analytics, setAnalytics] = useState<any>(null);

  useEffect(() => {
    fetch('/api/v1/organizations/me/analytics/summary', {
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
    })
      .then((r) => r.json())
      .then(setAnalytics)
      .catch(() => {});
  }, []);

  return (
    <Layout title="Dashboard">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-600">Active Sessions</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{analytics?.active_sessions ?? '—'}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-600">Total Sessions</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{analytics?.total_sessions ?? '—'}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-600">Total Messages</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{analytics?.total_messages ?? '—'}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <a href="/admin" className="bg-white rounded-lg shadow p-6 hover:shadow-md transition">
          <h3 className="text-lg font-medium text-gray-900">⚙️ Admin</h3>
          <p className="mt-2 text-sm text-gray-600">Platform management</p>
        </a>
        <a href="/developer" className="bg-white rounded-lg shadow p-6 hover:shadow-md transition">
          <h3 className="text-lg font-medium text-gray-900">🔧 Developer</h3>
          <p className="mt-2 text-sm text-gray-600">API keys & integration</p>
        </a>
      </div>
    </Layout>
  );
}
