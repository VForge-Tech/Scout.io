import { useEffect, useState } from 'react';
import { fetchArray, api } from '../../lib/api';
import AdminLayout from '../../components/AdminLayout';

export default function SystemHealth() {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    api.get<any>('/admin/health')
      .then((d) => { setHealth(d); setLoading(false); })
      .catch((e: any) => { setError(e.message); setLoading(false); });
  }, [mounted]);

  const statusColor = (status: string) => {
    if (status === 'healthy') return 'bg-green-100 text-green-800';
    if (status === 'degraded') return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  return (
    <AdminLayout>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">System Health</h2>
      {loading && <p className="text-gray-500">Loading...</p>}
      {error && <p className="text-red-500 mb-4">{error}</p>}
      {health && (
        <div className="space-y-4">
          <div className="flex items-center space-x-3 mb-6">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColor(health.status?.toUpperCase() || 'UNKNOWN')}`}>
              {health.status?.toUpperCase() || 'UNKNOWN'}
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(health.services || {}).map(([service, status]: any) => (
              <div key={service} className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900 capitalize">{service}</h3>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    (status === 'healthy' || status === 'ok' || (typeof status === 'object' && status?.status === 'healthy'))
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {(status === 'healthy' || status === 'ok' || (typeof status === 'object' && status?.status === 'healthy')) ? 'OK' : 'ERROR'}
                  </span>
                </div>
                {((status !== 'healthy' && status !== 'ok') || (typeof status === 'object' && status?.status !== 'healthy')) && (
                  <p className="mt-2 text-sm text-red-600">{typeof status === 'object' ? status?.error || JSON.stringify(status) : status}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </AdminLayout>
  );
}
