import { useCallback, useEffect, useState } from 'react';
import { api } from '../../lib/api';
import DashboardLayout from '../../components/DashboardLayout';

interface PlanInfo {
  key: string;
  name: string;
  price_inr: number;
  description: string;
  features: string[];
  limits: {
    chatbots: number;
    monthly_messages: number;
    knowledge_sources: number;
    included_monthly_tokens?: number;
  };
}

interface UsageBilling {
  period: string;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  estimated_cost: number;
  overage_tokens: number;
  overage_cost: number;
  reported_to_razorpay: boolean;
}

interface BillingInfo {
  billing_enabled: boolean;
  plan: string;
  plan_name: string;
  plan_status: string;
  limits: {
    chatbots: number;
    monthly_messages: number;
    knowledge_sources: number;
    included_monthly_tokens: number;
  };
  usage: {
    chatbots: number;
    monthly_messages: number;
    knowledge_sources: number;
  };
  usage_billing: UsageBilling | null;
  warning: { type: string; message: string } | null;
  available_plans: PlanInfo[];
}

const PLAN_ORDER = ['free', 'starter', 'growth', 'scale'];

function formatINR(n: number) {
  if (n === 0) return 'Free';
  return `₹${n.toLocaleString('en-IN')}/mo`;
}

function formatNum(n: number) {
  return n >= 1_000_000 ? `${(n / 1_000_000).toFixed(0)}M` : n >= 1_000 ? `${(n / 1_000).toFixed(0)}k` : String(n);
}

export default function DashboardBilling() {
  const [billing, setBilling] = useState<BillingInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkingOut, setCheckingOut] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const fetchBilling = useCallback(async () => {
    if (!mounted) return;
    try {
      const data = await api.get<BillingInfo>('/organizations/me/billing');
      setBilling(data);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load billing info');
    } finally {
      setLoading(false);
    }
  }, [mounted]);

  useEffect(() => {
    if (!mounted) return;
    fetchBilling();
  }, [mounted, fetchBilling]);

  const handleUpgrade = async (planKey: string) => {
    setCheckingOut(planKey);
    setActionError(null);
    try {
      const res = await api.post<{ checkout_url: string | null; plan: string }>(
        '/organizations/me/billing/checkout-session',
        { plan: planKey },
      );
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      } else {
        await fetchBilling();
      }
    } catch (e: any) {
      setActionError(e.message || 'Failed to start checkout');
    } finally {
      setCheckingOut(null);
    }
  };

  const sortedPlans = billing
    ? [...billing.available_plans].sort(
        (a, b) => PLAN_ORDER.indexOf(a.key) - PLAN_ORDER.indexOf(b.key),
      )
    : [];

  return (
    <DashboardLayout>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Billing</h2>
        <p className="text-sm text-gray-500 mt-1">
          Current plan:{' '}
          <span className="font-medium text-gray-700">{billing?.plan_name || 'Free'}</span>
          {billing && billing.plan_status !== 'active' && (
            <span className="ml-2 px-2 py-0.5 rounded-full text-xs bg-yellow-100 text-yellow-800">
              {billing.plan_status}
            </span>
          )}
        </p>
      </div>

      {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded mb-6">{error}</div>}
      {loading && <p className="text-gray-500">Loading billing info...</p>}

      {!loading && billing && !billing.billing_enabled && (
        <div className="bg-yellow-50 text-yellow-800 px-4 py-4 rounded mb-6">
          <p className="font-medium">Billing is disabled in this environment</p>
          <p className="text-sm mt-1">
            Payment processing and plan limit enforcement are turned off for this
            testing build. Billing will be enabled in production.
          </p>
        </div>
      )}

      {!loading && billing && billing.warning && (
        <div className="bg-orange-50 text-orange-800 border border-orange-200 px-4 py-4 rounded mb-6">
          <p className="font-medium">Usage warning</p>
          <p className="text-sm mt-1">{billing.warning.message}</p>
        </div>
      )}

      {!loading && billing && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-5">
              <p className="text-sm text-gray-500">Chatbots</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {billing.usage.chatbots}
                <span className="text-gray-400 text-base font-normal"> / {billing.limits.chatbots}</span>
              </p>
            </div>
            <div className="bg-white rounded-lg shadow p-5">
              <p className="text-sm text-gray-500">Messages / month</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {formatNum(billing.usage.monthly_messages)}
                <span className="text-gray-400 text-base font-normal"> / {formatNum(billing.limits.monthly_messages)}</span>
              </p>
            </div>
            <div className="bg-white rounded-lg shadow p-5">
              <p className="text-sm text-gray-500">Knowledge sources</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {billing.usage.knowledge_sources}
                <span className="text-gray-400 text-base font-normal"> / {billing.limits.knowledge_sources}</span>
              </p>
            </div>
            {billing.usage_billing && (
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-sm text-gray-500">Tokens used (month)</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {formatNum(billing.usage_billing.total_tokens)}
                  <span className="text-gray-400 text-base font-normal"> / {formatNum(billing.limits.included_monthly_tokens)}</span>
                </p>
                {billing.usage_billing.overage_tokens > 0 && (
                  <p className="text-xs text-red-600 mt-1">
                    {formatNum(billing.usage_billing.overage_tokens)} over included limit
                    {billing.usage_billing.reported_to_razorpay
                      ? ' — billed as add-on'
                      : ' — will be invoiced'}
                  </p>
                )}
              </div>
            )}
          </div>

          {actionError && <div className="bg-red-50 text-red-700 px-4 py-3 rounded mb-6">{actionError}</div>}

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {sortedPlans.map((plan) => {
              const isCurrent = plan.key === billing.plan;
              const disabled = !billing.billing_enabled;
              return (
                <div
                  key={plan.key}
                  className={`bg-white rounded-lg shadow p-6 flex flex-col ${
                    isCurrent ? 'ring-2 ring-blue-500' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-bold text-gray-900">{plan.name}</h3>
                    {isCurrent && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-800">Current</span>
                    )}
                  </div>
                  <p className="text-2xl font-bold text-gray-900 mt-2">{formatINR(plan.price_inr)}</p>
                  <p className="text-sm text-gray-500 mt-1">{plan.description}</p>
                  <ul className="mt-4 space-y-2 flex-1">
                    {plan.features.map((f) => (
                      <li key={f} className="text-sm text-gray-600 flex items-start gap-2">
                        <span className="text-green-500 mt-0.5">✓</span>
                        {f}
                      </li>
                    ))}
                  </ul>
                  <button
                    onClick={() => handleUpgrade(plan.key)}
                    disabled={disabled || isCurrent || checkingOut !== null}
                    className={`mt-6 px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50 ${
                      disabled
                        ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                        : isCurrent
                          ? 'bg-gray-100 text-gray-500 cursor-default'
                          : 'bg-blue-600 text-white hover:bg-blue-700'
                    }`}
                  >
                    {disabled
                      ? 'Unavailable'
                      : checkingOut === plan.key
                        ? 'Redirecting...'
                        : isCurrent || plan.price_inr === 0
                          ? 'Current Plan'
                          : 'Upgrade'}
                  </button>
                </div>
              );
            })}
          </div>

          <p className="text-xs text-gray-400 mt-6">
            Payments are processed by Razorpay. You will be redirected to a secure
            Razorpay-hosted checkout page to complete your subscription.
          </p>
        </>
      )}
    </DashboardLayout>
  );
}