import { useEffect, useState } from 'react';
import AdminLayout from '../../components/AdminLayout';

export default function AdminOrganizations() {
  const [orgs, setOrgs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchOrgs = () => {
    fetch('/api/v1/admin/organizations', {
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
    })
      .then((r) => r.json())
      .then((d) => { setOrgs(d); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { fetchOrgs(); }, []);

  const suspendOrg = async (id: string) => {
    await fetch(`/api/v1/admin/organizations/${id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('access_token')}`,
      },
      body: JSON.stringify({ suspended: true }),
    });
    fetchOrgs();
  };

  return (
    <AdminLayout>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Organizations</h2>
      {loading && <p className="text-gray-500">Loading...</p>}
      {!loading && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {orgs.map((org: any) => (
                <tr key={org.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{org.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {org.created_at ? new Date(org.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      onClick={() => suspendOrg(org.id)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Suspend
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AdminLayout>
  );
}
