import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import DashboardLayout from '../../components/DashboardLayout';

interface OrgConfig {
  name: string;
  configuration: Record<string, unknown>;
}

export default function DashboardSettings() {
  const [org, setOrg] = useState<OrgConfig | null>(null);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  useEffect(() => {
    api.get<OrgConfig>('/organizations/me')
      .then((data) => {
        setOrg(data);
        setName(data.name);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!org) return;
    try {
      await api.put(`/organizations/me`, { name });
      setMessage('Organization name updated');
    } catch (e: any) {
      setMessage(e.message);
    }
  };

  if (loading) return <DashboardLayout><p className="text-gray-500">Loading...</p></DashboardLayout>;

  return (
    <DashboardLayout>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Settings</h2>
      <div className="bg-white rounded-lg shadow p-6 max-w-2xl">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Organization Details</h3>
        {message && (
          <div className="bg-green-50 text-green-700 px-4 py-2 rounded mb-4 text-sm">{message}</div>
        )}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Organization Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 block w-full border rounded-md px-3 py-2"
            />
          </div>
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm"
          >
            Save Changes
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
}