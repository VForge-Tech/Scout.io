import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import AdminLayout from '../../components/AdminLayout';

interface FunnelOrgRow {
  organization_id: string;
  name: string;
  created_at: string | null;
  steps_completed: string[];
  has_chatbot: boolean;
  has_knowledge_source: boolean;
  has_widget_session: boolean;
  has_teammate: boolean;
}

interface FeedbackItem {
  id: string;
  organization_id: string;
  org_name: string | null;
  rating: string | null;
  message: string | null;
  context: string | null;
  timestamp: string | null;
}

interface FunnelResponse {
  summary: Record<string, number>;
  funnel: FunnelOrgRow[];
  feedback: FeedbackItem[];
}

const STEP_LABELS: Record<string, string> = {
  create_chatbot: 'Chatbot',
  add_knowledge_source: 'Knowledge source',
  test_widget: 'Widget test',
  invite_teammate: 'Teammate',
};

export default function AdminOnboarding() {
  const [data, setData] = useState<FunnelResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<FunnelResponse>('/admin/onboarding/funnel')
      .then((d) => { setData(d); setLoading(false); })
      .catch((e: any) => { setError(e.message); setLoading(false); });
  }, []);

  const boolBadge = (val: boolean) =>
    val
      ? <span className="px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">Yes</span>
      : <span className="px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-500">No</span>;

  const summaryCards = data ? [
    { label: 'Organizations', value: data.summary.total_organizations ?? 0 },
    { label: 'Created a Chatbot', value: data.summary.with_chatbot ?? 0 },
    { label: 'Added a Source', value: data.summary.with_knowledge_source ?? 0 },
    { label: 'Tested the Widget', value: data.summary.with_widget_session ?? 0 },
    { label: 'Invited a Teammate', value: data.summary.with_teammate ?? 0 },
    { label: 'Feedback Up', value: data.summary.feedback_up ?? 0 },
    { label: 'Feedback Down', value: data.summary.feedback_down ?? 0 },
  ] : [];

  return (
    <AdminLayout>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Onboarding & Feedback</h2>
      {loading && <p className="text-gray-500">Loading...</p>}
      {error && <p className="text-red-500 mb-4">{error}</p>}
      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
            {summaryCards.map((c) => (
              <div key={c.label} className="bg-white rounded-lg shadow p-6">
                <p className="text-sm text-gray-600">{c.label}</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{c.value}</p>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden mb-8">
            <h3 className="text-lg font-medium text-gray-900 px-6 pt-6 pb-4">Onboarding Funnel</h3>
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Organization</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Chatbot</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Widget</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Teammate</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Recorded Steps</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.funnel.map((row) => (
                  <tr key={row.organization_id}>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{row.name}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {row.created_at ? new Date(row.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-6 py-4">{boolBadge(row.has_chatbot)}</td>
                    <td className="px-6 py-4">{boolBadge(row.has_knowledge_source)}</td>
                    <td className="px-6 py-4">{boolBadge(row.has_widget_session)}</td>
                    <td className="px-6 py-4">{boolBadge(row.has_teammate)}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {row.steps_completed.length === 0
                        ? '—'
                        : row.steps_completed.map((s) => STEP_LABELS[s] || s).join(', ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden">
            <h3 className="text-lg font-medium text-gray-900 px-6 pt-6 pb-4">Feedback Submissions</h3>
            {data.feedback.length === 0 ? (
              <p className="px-6 pb-6 text-sm text-gray-500">No feedback submitted yet.</p>
            ) : (
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Organization</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rating</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Context</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Message</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {data.feedback.map((f) => (
                    <tr key={f.id}>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">{f.org_name || '—'}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          f.rating === 'up' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {f.rating === 'up' ? '👍 Up' : '👎 Down'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{f.context || '—'}</td>
                      <td className="px-6 py-4 text-sm text-gray-600 max-w-xs truncate">{f.message || '—'}</td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {f.timestamp ? new Date(f.timestamp).toLocaleString() : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </AdminLayout>
  );
}