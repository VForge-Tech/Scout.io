import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import DashboardLayout from '../../components/DashboardLayout';

interface OrgInfo {
  id: string;
  name: string;
  configuration: Record<string, unknown>;
}

interface Analytics {
  total_sessions: number;
  active_sessions: number;
  total_messages: number;
  total_tokens: number;
  total_chatbots: number;
  active_chatbots: number;
}

interface OnboardingStep {
  step: string;
  label: string;
  completed: boolean;
}

interface Checklist {
  steps: OnboardingStep[];
  completed_count: number;
}

const STEP_LINKS: Record<string, string> = {
  create_chatbot: '/dashboard/chatbots',
  add_knowledge_source: '/dashboard/knowledge-sources',
  test_widget: '/developer/api-test',
  invite_teammate: '/dashboard/team',
};

function OnboardingChecklist() {
  const [checklist, setChecklist] = useState<Checklist | null>(null);

  useEffect(() => {
    api.get<Checklist>('/analytics/onboarding')
      .then(setChecklist)
      .catch(() => {});
  }, []);

  if (!checklist || checklist.completed_count >= checklist.steps.length) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-8">
      <h3 className="text-lg font-medium text-gray-900 mb-1">Get started</h3>
      <p className="text-sm text-gray-500 mb-4">
        Complete these steps to launch your first chatbot.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {checklist.steps.map((s) => (
          <a
            key={s.step}
            href={STEP_LINKS[s.step] || '#'}
            className={`flex items-center gap-3 p-3 rounded-lg border transition-colors ${
              s.completed
                ? 'bg-green-50 border-green-200'
                : 'border-gray-200 hover:bg-gray-50'
            }`}
          >
            <span
              className={`w-5 h-5 rounded-full flex items-center justify-center text-xs shrink-0 ${
                s.completed ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'
              }`}
            >
              {s.completed ? '✓' : ''}
            </span>
            <span className={`text-sm ${s.completed ? 'text-green-700' : 'text-gray-800'}`}>
              {s.label}
            </span>
          </a>
        ))}
      </div>
      <p className="text-xs text-gray-400 mt-3">
        {checklist.completed_count} of {checklist.steps.length} completed
      </p>
    </div>
  );
}

export default function DashboardOverview() {
  const [org, setOrg] = useState<OrgInfo | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [orgData, analyticsData] = await Promise.all([
          api.get<OrgInfo>('/organizations/me'),
          api.get<Analytics>('/analytics/organization'),
        ]);
        setOrg(orgData);
        setAnalytics(analyticsData);
      } catch (e: any) {
        setError(e.message || 'Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const plan = (org?.configuration as Record<string, unknown> | undefined)?.plan as string ?? 'free';
  const planLabel = plan.charAt(0).toUpperCase() + plan.slice(1);

  return (
    <DashboardLayout>
      {loading && <p className="text-gray-500">Loading dashboard...</p>}
      {error && <p className="text-red-500 mb-6">{error}</p>}
      {!loading && !error && org && (
        <>
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">{org.name}</h2>
              <p className="text-sm text-gray-500 mt-1">Organization ID: {org.id.slice(0, 8)}...</p>
            </div>
            <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">
              {planLabel} Plan
            </span>
          </div>

          <OnboardingChecklist />

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatCard title="Chatbots" value={analytics?.total_chatbots ?? 0} subtitle={`${analytics?.active_chatbots ?? 0} active`} />
            <StatCard title="This Month's Messages" value={analytics?.total_messages ?? 0} subtitle="Total across all chatbots" />
            <StatCard title="Total Sessions" value={analytics?.total_sessions ?? 0} subtitle={`${analytics?.active_sessions ?? 0} active now`} />
            <StatCard title="Tokens Used" value={analytics?.total_tokens?.toLocaleString() ?? '0'} subtitle="This month" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <QuickActionCard
              title="Chatbots"
              description="Create and manage your chatbots"
              href="/dashboard/chatbots"
              icon="🤖"
            />
            <QuickActionCard
              title="Knowledge Sources"
              description="Connect data sources to your chatbots"
              href="/dashboard/knowledge-sources"
              icon="📚"
            />
            <QuickActionCard
              title="Analytics"
              description="View detailed usage analytics"
              href="/dashboard/analytics"
              icon="📈"
            />
          </div>

          <div className="mt-10 border-t pt-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Links</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[
                { label: 'Chatbots', href: '/dashboard/chatbots', icon: '🤖' },
                { label: 'Knowledge Sources', href: '/dashboard/knowledge-sources', icon: '📚' },
                { label: 'Policies', href: '/dashboard/policies', icon: '🛡️' },
                { label: 'Team', href: '/dashboard/team', icon: '👥' },
                { label: 'Billing', href: '/dashboard/billing', icon: '💳' },
                { label: 'Settings', href: '/dashboard/settings', icon: '⚙️' },
              ].map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="bg-white rounded-lg shadow p-4 hover:shadow-md transition"
                >
                  <span className="text-2xl">{item.icon}</span>
                  <span className="ml-3 font-medium text-gray-900">{item.label}</span>
                </a>
              ))}
            </div>
          </div>
        </>
      )}
    </DashboardLayout>
  );
}

function StatCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: number | string;
  subtitle?: string;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <p className="text-sm text-gray-600">{title}</p>
      <p className="text-3xl font-bold text-gray-900 mt-2">{value.toLocaleString?.() ?? value}</p>
      {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
    </div>
  );
}

function QuickActionCard({
  title,
  description,
  href,
  icon,
}: {
  title: string;
  description: string;
  href: string;
  icon: string;
}) {
  return (
    <a href={href} className="bg-white rounded-lg shadow p-6 hover:shadow-md transition">
      <div className="flex items-start">
        <span className="text-3xl mr-4">{icon}</span>
        <div>
          <h3 className="text-lg font-medium text-gray-900">{title}</h3>
          <p className="mt-1 text-sm text-gray-600">{description}</p>
        </div>
      </div>
    </a>
  );
}