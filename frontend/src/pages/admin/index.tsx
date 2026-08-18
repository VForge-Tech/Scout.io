import { useCallback, useEffect, useState } from 'react';
import AdminLayout from '../../components/AdminLayout';
import { usePolling } from '../../lib/usePolling';

export default function AdminDashboard() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchStats = useCallback(async () => {
    const res = await fetch('/api/v1/admin/stats', {
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
    });
    if (!res.ok) throw new Error('Failed');
    const d = await res.json();
    setStats(d);
    setError('');
    return d;
  }, []);

  useEffect(() => {
    fetchStats().catch(() => setError('Failed to load stats')).finally(() => setLoading(false));
  }, [fetchStats]);

  usePolling(fetchStats);

  return (
    <AdminLayout>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Platform Statistics</h2>
      {loading && <p className="text-gray-500">Loading...</p>}
      {error && <p className="text-red-500">{error}</p>}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StatCard title="Organizations" value={stats.total_organizations} />
          <StatCard title="Chatbots" value={stats.total_chatbots} />
          <StatCard title="Sessions" value={stats.total_sessions} />
          <StatCard title="Messages" value={stats.total_messages} />
          <StatCard title="Tokens Used" value={stats.total_tokens_used?.toLocaleString()} />
          <StatCard title="API Keys" value={stats.total_api_keys} />
          <StatCard title="Policies" value={stats.total_policies} />
          <StatCard title="Knowledge Sources" value={stats.total_knowledge_sources} />
          <StatCard title="LLM Calls" value={stats.total_llm_calls} />
        </div>
      )}
    </AdminLayout>
  );
}

function StatCard({ title, value }: { title: string; value: string | number }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <p className="text-sm text-gray-600">{title}</p>
      <p className="text-3xl font-bold text-gray-900 mt-2">{value ?? '—'}</p>
    </div>
  );
}
