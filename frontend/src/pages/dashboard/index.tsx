import { useCallback, useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { usePolling } from '../../lib/usePolling';
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

  const fetchChecklist = useCallback(() => {
    api.get<Checklist>('/analytics/onboarding')
      .then(setChecklist)
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchChecklist();
  }, [fetchChecklist]);

  usePolling(fetchChecklist);

  if (!checklist || checklist.completed_count >= checklist.steps.length) return null;

  return (
    <div className="card p-6 mb-8 animate-fade-in">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-2xl">🚀</span>
        <h3 className="text-lg font-medium text-gray-900">Get started</h3>
      </div>
      <p className="text-sm text-gray-500 mb-4">
        Complete these steps to launch your first chatbot.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {checklist.steps.map((s) => (
          <a
            key={s.step}
            href={STEP_LINKS[s.step] || '#'}
            className={`onboarding-step ${s.completed ? 'onboarding-step-completed' : 'onboarding-step-pending'}`}
          >
            <span className={`onboarding-step-icon ${s.completed ? 'onboarding-step-icon-completed' : 'onboarding-step-icon-pending'}`}>
              {s.completed ? '✓' : s.completed ? '' : String(checklist.steps.indexOf(s) + 1)}
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

  const fetchData = useCallback(async () => {
    try {
      const [orgData, analyticsData] = await Promise.all([
        api.get<OrgInfo>('/organizations/me'),
        api.get<Analytics>('/analytics/organization'),
      ]);
      setOrg(orgData);
      setAnalytics(analyticsData);
      setError('');
    } catch (e: any) {
      setError(e.message || 'Failed to load dashboard data');
    }
  }, []);

  useEffect(() => {
    const initial = async () => {
      try {
        setLoading(true);
        await fetchData();
      } finally {
        setLoading(false);
      }
    };
    initial();
  }, [fetchData]);

  usePolling(fetchData);

  const plan = (org?.configuration as Record<string, unknown> | undefined)?.plan as string ?? 'free';
  const planLabel = plan.charAt(0).toUpperCase() + plan.slice(1);

  return (
    <DashboardLayout>
      {loading && (
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center animate-pulse-soft">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-500 to-amber-700 mb-4">
              <span className="text-2xl">🔍</span>
            </div>
            <p className="text-gray-500">Loading dashboard...</p>
          </div>
        </div>
      )}
      {error && (
        <div className="card p-6 mb-8 border-red-200 bg-red-50 animate-fade-in">
          <div className="flex items-center gap-3 text-red-700">
            <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 001.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span>{error}</span>
          </div>
        </div>
      )}
      {!loading && !error && org && (
        <>
          {/* Header */}
          <div className="flex items-center justify-between mb-8 animate-fade-in">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">{org.name}</h2>
              <p className="text-sm text-gray-500 mt-1">Organization ID: {org.id.slice(0, 8)}...</p>
            </div>
            <span className="px-3 py-1 bg-amber-100 text-amber-800 text-sm font-medium rounded-full">
              {planLabel} Plan
            </span>
          </div>

          <OnboardingChecklist />

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatCard 
              title="Chatbots" 
              value={analytics?.total_chatbots ?? 0} 
              subtitle={`${analytics?.active_chatbots ?? 0} active`}
              icon="🤖"
              trend="+12%"
            />
            <StatCard 
              title="Messages" 
              value={analytics?.total_messages ?? 0} 
              subtitle="Total across all chatbots"
              icon="💬"
              trend="+23%"
            />
            <StatCard 
              title="Sessions" 
              value={analytics?.total_sessions ?? 0} 
              subtitle={`${analytics?.active_sessions ?? 0} active now`}
              icon="👥"
              trend="+8%"
            />
            <StatCard 
              title="Tokens Used" 
              value={analytics?.total_tokens?.toLocaleString() ?? '0'} 
              subtitle="This month"
              icon="⚡"
              trend="+5%"
            />
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
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
              title="Playground"
              description="Test your chatbot with streaming responses"
              href="/dashboard/playground"
              icon="🧪"
            />
          </div>

          <div className="card gradient-border p-6 animate-fade-in delay-2">
            <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
              <span className="text-xl">⚡</span>
              Quick Links
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                { label: 'Chatbots', href: '/dashboard/chatbots', icon: '🤖', desc: 'Create & manage bots' },
                { label: 'Knowledge', href: '/dashboard/knowledge-sources', icon: '📚', desc: 'Connect data sources' },
                { label: 'Policies', href: '/dashboard/policies', icon: '🛡️', desc: 'Content policies' },
                { label: 'Team', href: '/dashboard/team', icon: '👥', desc: 'Manage members' },
                { label: 'Analytics', href: '/dashboard/analytics', icon: '📈', desc: 'Detailed metrics' },
                { label: 'Playground', href: '/dashboard/playground', icon: '🧪', desc: 'Test streaming' },
                { label: 'Billing', href: '/dashboard/billing', icon: '💳', desc: 'Plan & usage' },
                { label: 'Settings', href: '/dashboard/settings', icon: '⚙️', desc: 'Configuration' },
              ].map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="action-card flex flex-col"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-2xl">{item.icon}</span>
                    <span className="action-card-title">{item.label}</span>
                  </div>
                  <p className="text-xs text-gray-500">{item.desc}</p>
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
  icon,
  trend,
}: {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: string;
  trend?: string;
}) {
  return (
    <div className="stat-card gradient-border animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="stat-label">{title}</p>
          <p className="stat-value">{value.toLocaleString?.() ?? value}</p>
          {subtitle && <p className="stat-subtitle">{subtitle}</p>}
        </div>
        <div className="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center text-2xl shrink-0">
          {icon}
        </div>
      </div>
      {trend && (
        <div className="mt-4 flex items-center gap-1 text-xs text-green-600 font-medium">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7 7v18" />
          </svg>
          <span>{trend}</span>
        </div>
      )}
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
    <a href={href} className="action-card flex flex-col">
      <div className="flex items-center gap-3 mb-2">
        <span className="action-card-icon">{icon}</span>
        <span className="action-card-title">{title}</span>
      </div>
      <p className="action-card-desc">{description}</p>
      <div className="mt-auto pt-4 border-t border-gray-100">
        <span className="text-sm text-amber-600 font-medium flex items-center gap-1">
          Open
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
          </svg>
        </span>
      </div>
    </a>
  );
}