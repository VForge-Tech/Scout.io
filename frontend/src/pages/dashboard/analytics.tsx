import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '../../lib/api';
import DashboardLayout from '../../components/DashboardLayout';

interface DailyAnalyticsRow {
  id: string;
  date: string;
  organization_id: string;
  chatbot_id: string | null;
  source_id: string | null;
  entity_type: string;
  sessions_count: number;
  messages_count: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  avg_latency_ms: number;
  feedback_positive: number;
  feedback_negative: number;
  retrieval_count: number;
  sync_success_count: number;
  sync_failure_count: number;
}

interface Chatbot {
  id: string;
  name: string;
}

interface KnowledgeSource {
  id: string;
  chatbot_id: string | null;
  source_type: string;
  uri: string;
}

interface SourceAnalytics {
  source_id: string;
  retrieval_count: number;
  sync_success_count: number;
  sync_failure_count: number;
}

interface CurrentUser {
  role: string;
  organization_id: string;
}

type RangeKey = '7d' | '30d' | '90d';

const RANGE_DAYS: Record<RangeKey, number> = { '7d': 7, '30d': 30, '90d': 90 };

const RANGE_LABELS: { value: RangeKey; label: string }[] = [
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
];

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function shortLabel(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-lg shadow p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-64 text-gray-400 text-sm">{message}</div>
  );
}

export default function DashboardAnalytics() {
  const [range, setRange] = useState<RangeKey>('30d');
  const [rows, setRows] = useState<DailyAnalyticsRow[]>([]);
  const [chatbots, setChatbots] = useState<Chatbot[]>([]);
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [sourceStats, setSourceStats] = useState<Record<string, SourceAnalytics>>({});
  const [userRole, setUserRole] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  const isAdmin = userRole === 'admin' || userRole === 'platform_admin';

  useEffect(() => {
    setMounted(true);
  }, []);

  const fetchData = useCallback(async () => {
    if (!mounted) return;
    try {
      const [me, botList] = await Promise.all([
        api.get<CurrentUser>('/auth/me'),
        api.get<Chatbot[]>('/chatbots'),
      ]);
      setUserRole(me.role);
      setChatbots(botList);

      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - RANGE_DAYS[range]);
      const qs = `?start_date=${isoDate(start)}&end_date=${isoDate(end)}`;

      const daily = await api.get<DailyAnalyticsRow[]>(`/analytics/organization/daily${qs}`);
      setRows(daily);

      const sourceRows: KnowledgeSource[] = [];
      const statPromises: Promise<void>[] = [];
      const statsAcc: Record<string, SourceAnalytics> = {};

      for (const bot of botList) {
        try {
          const botSources = await api.get<KnowledgeSource[]>(
            `/chatbots/${bot.id}/knowledge-sources`,
          );
          for (const s of botSources) {
            sourceRows.push({ ...s, chatbot_id: s.chatbot_id });
            statPromises.push(
              api
                .get<SourceAnalytics>(`/analytics/source/${s.id}`)
                .then((st) => {
                  statsAcc[s.id] = st;
                })
                .catch(() => {
                  // source without analytics data
                }),
            );
          }
        } catch {
          // skip chatbot whose sources failed to load
        }
      }
      setSources(sourceRows);
      await Promise.all(statPromises);
      setSourceStats(statsAcc);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  }, [mounted, range]);

  useEffect(() => {
    if (!mounted) return;
    setLoading(true);
    fetchData();
  }, [mounted, range, fetchData]);

  const byDate = useMemo(() => {
    const map: Record<string, DailyAnalyticsRow> = {};
    for (const r of rows) {
      const key = r.date;
      if (!map[key]) {
        map[key] = {
          ...r,
          sessions_count: 0,
          messages_count: 0,
          prompt_tokens: 0,
          completion_tokens: 0,
          total_tokens: 0,
          avg_latency_ms: 0,
          feedback_positive: 0,
          feedback_negative: 0,
        };
      }
      const agg = map[key];
      agg.sessions_count += r.sessions_count;
      agg.messages_count += r.messages_count;
      agg.prompt_tokens += r.prompt_tokens;
      agg.completion_tokens += r.completion_tokens;
      agg.total_tokens += r.total_tokens;
      agg.feedback_positive += r.feedback_positive;
      agg.feedback_negative += r.feedback_negative;
    }
    return Object.keys(map)
      .sort()
      .map((dateStr) => ({
        date: dateStr,
        label: shortLabel(dateStr),
        sessions_count: map[dateStr].sessions_count,
        messages_count: map[dateStr].messages_count,
        total_tokens: map[dateStr].total_tokens,
        feedback_positive: map[dateStr].feedback_positive,
        feedback_negative: map[dateStr].feedback_negative,
      }));
  }, [rows]);

  const perChatbotTokens = useMemo(() => {
    const names: Record<string, string> = {};
    for (const bot of chatbots) names[bot.id] = bot.name;

    const map: Record<string, Record<string, number>> = {};
    for (const r of rows) {
      if (!r.chatbot_id) continue;
      if (!map[r.date]) map[r.date] = {};
      map[r.date][r.chatbot_id] = (map[r.date][r.chatbot_id] || 0) + r.total_tokens;
    }

    const days = Object.keys(map).sort();
    return days.map((dateStr) => {
      const point: Record<string, string | number> = { date: shortLabel(dateStr) };
      for (const [chatbotId, tokens] of Object.entries(map[dateStr])) {
        point[names[chatbotId] || chatbotId] = tokens;
      }
      return point;
    });
  }, [rows, chatbots]);

  const totals = useMemo(() => {
    return rows.reduce(
      (acc, r) => {
        acc.messages += r.messages_count;
        acc.sessions += r.sessions_count;
        acc.tokens += r.total_tokens;
        acc.feedbackPositive += r.feedback_positive;
        acc.feedbackNegative += r.feedback_negative;
        return acc;
      },
      { messages: 0, sessions: 0, tokens: 0, feedbackPositive: 0, feedbackNegative: 0 },
    );
  }, [rows]);

  const chatbotIds = useMemo(() => new Set(chatbots.map((c) => c.id)), [chatbots]);
  const showPerChatbot = chatbotIds.size > 1;

  return (
    <DashboardLayout>
      <div className="flex flex-wrap justify-between items-center mb-6 gap-3">
        <h2 className="text-2xl font-bold text-gray-900">Analytics</h2>
        <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
          {RANGE_LABELS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setRange(opt.value)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium ${
                range === opt.value ? 'bg-white text-blue-700 shadow' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded mb-6">{error}</div>}
      {loading && <p className="text-gray-500">Loading analytics...</p>}

      {!loading && !error && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <StatCard label="Messages" value={formatNumber(totals.messages)} sub="in selected range" />
            <StatCard label="Sessions" value={formatNumber(totals.sessions)} sub="in selected range" />
            <StatCard label="Total Tokens" value={formatNumber(totals.tokens)} sub="in selected range" />
            <StatCard
              label="Feedback"
              value={`${totals.feedbackPositive} 👍 / ${totals.feedbackNegative} 👎`}
              sub="positive vs negative"
            />
          </div>

          <div className="bg-white rounded-lg shadow p-5 mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-1">Messages & Sessions Over Time</h3>
            <p className="text-xs text-gray-400 mb-4">Volume of messages and unique sessions per day across your organization.</p>
            {byDate.length === 0 ? (
              <EmptyChart message="No daily activity recorded in this range yet." />
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart data={byDate} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#6b7280' }} />
                  <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} />
                  <Tooltip />
                  <Bar dataKey="messages_count" name="Messages" fill="#3b82f6" radius={[3, 3, 0, 0]} />
                  <Line type="monotone" dataKey="sessions_count" name="Sessions" stroke="#10b981" strokeWidth={2} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>

          {showPerChatbot && (
            <div className="bg-white rounded-lg shadow p-5 mb-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-1">Token Usage by Chatbot</h3>
              <p className="text-xs text-gray-400 mb-4">Total tokens consumed per day, broken out per chatbot.</p>
              {perChatbotTokens.length === 0 ? (
                <EmptyChart message="No token usage recorded in this range yet." />
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <ComposedChart data={perChatbotTokens} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#6b7280' }} />
                    <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} />
                    <Tooltip />
                    {chatbots.map((bot, i) => (
                      <Line
                        key={bot.id}
                        type="monotone"
                        dataKey={bot.name}
                        name={bot.name}
                        stroke={['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4'][i % 6]}
                        strokeWidth={2}
                        dot={false}
                      />
                    ))}
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </div>
          )}

          {isAdmin && (
            <div className="bg-white rounded-lg shadow p-5 mb-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-1">Knowledge Source Usage</h3>
              <p className="text-xs text-gray-400 mb-4">
                How often each knowledge source is retrieved during answers, plus sync health. (Admin view)
              </p>
              {sources.length === 0 ? (
                <EmptyChart message="No knowledge sources configured." />
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Retrievals</th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Sync OK</th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Sync Failed</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {sources.map((s) => {
                        const st = sourceStats[s.id];
                        return (
                          <tr key={s.id}>
                            <td className="px-4 py-3 text-sm text-gray-900 truncate max-w-xs" title={s.uri}>{s.uri}</td>
                            <td className="px-4 py-3 text-sm text-gray-600">{s.source_type}</td>
                            <td className="px-4 py-3 text-sm text-right text-gray-700">
                              {st ? formatNumber(st.retrieval_count) : '—'}
                            </td>
                            <td className="px-4 py-3 text-sm text-right text-green-600">
                              {st ? formatNumber(st.sync_success_count) : '—'}
                            </td>
                            <td className="px-4 py-3 text-sm text-right text-red-600">
                              {st ? formatNumber(st.sync_failure_count) : '—'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </DashboardLayout>
  );
}