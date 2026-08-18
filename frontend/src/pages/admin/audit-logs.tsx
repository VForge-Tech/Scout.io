import { useCallback, useEffect, useState } from 'react';
import { fetchArray } from '../../lib/api';
import { usePolling } from '../../lib/usePolling';
import AdminLayout from '../../components/AdminLayout';

export default function AuditLogs() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const fetchLogs = useCallback(async () => {
    if (!mounted) return;
    try {
      setError(null);
      const d = await fetchArray<any>(`/admin/audit-logs?limit=50&offset=${page * 50}`);
      setLogs(d);
    } catch (e: any) {
      setError(e.message);
    }
  }, [page, mounted]);

  useEffect(() => {
    if (!mounted) return;
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        await fetchLogs();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [mounted, fetchLogs]);

  usePolling(fetchLogs);

  return (
    <AdminLayout>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Audit Logs</h2>
      {loading && <p className="text-gray-500">Loading...</p>}
      {error && <p className="text-red-500 mb-4">{error}</p>}
      {!loading && !error && (
        <>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Details</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">IP</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {logs.map((log: any) => (
                  <tr key={log.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{log.action}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{log.user_id?.slice(0, 8) || '—'}</td>
                    <td className="px-6 py-4 text-sm text-gray-500 max-w-xs truncate">{JSON.stringify(log.details)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{log.ip_address || '—'}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex justify-between">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="px-4 py-2 text-sm bg-white border rounded-md disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500">Page {page + 1}</span>
            <button
              onClick={() => setPage(page + 1)}
              disabled={logs.length < 50}
              className="px-4 py-2 text-sm bg-white border rounded-md disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </>
      )}
    </AdminLayout>
  );
}
