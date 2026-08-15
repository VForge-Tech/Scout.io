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

interface Invoice {
  id: string;
  status: string | null;
  amount_paise: number | null;
  currency: string | null;
  issued_at: string | null;
  paid_at: string | null;
}

interface SubscriptionDetail {
  has_subscription: boolean;
  subscription_id: string | null;
  plan_id: string | null;
  plan_key: string | null;
  status: string | null;
  current_start: string | null;
  current_end: string | null;
  next_charge_on: string | null;
  payment_method: string | null;
  cancel_at_cycle_end: boolean | null;
  invoices: Invoice[];
}

interface ChangePlanResult {
  subscription_id: string;
  plan: string;
  schedule_change_at: string;
  status: string | null;
  next_charge_on: string | null;
}

interface CancelResult {
  subscription_id: string;
  status: string | null;
  cancel_at_cycle_end: boolean;
  current_end: string | null;
}

const PLAN_ORDER = ['free', 'starter', 'growth', 'scale'];

function formatINR(n: number) {
  if (n === 0) return 'Free';
  return `₹${n.toLocaleString('en-IN')}/mo`;
}

function formatNum(n: number) {
  return n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1_000 ? `${(n / 1_000).toFixed(0)}k` : String(n);
}

function formatDate(iso: string | null) {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? '—' : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function ProgressBar({ used, limit, color = 'bg-blue-600' }: { used: number; limit: number; color?: string }) {
  const pct = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
  const over = limit > 0 && used > limit;
  return (
    <div className="mt-2">
      <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
        <span>
          <span className="font-medium text-gray-900">{formatNum(used)}</span>
          <span className="text-gray-400"> / {formatNum(limit)}</span>
        </span>
        <span className={over ? 'text-red-600 font-medium' : pct >= 80 ? 'text-orange-600 font-medium' : ''}>
          {over ? 'Over limit' : `${Math.round(pct)}%`}
        </span>
      </div>
      <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
        <div
          className={`h-full rounded-full ${over ? 'bg-red-600' : pct >= 80 ? 'bg-orange-500' : color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function DashboardBilling() {
  const [billing, setBilling] = useState<BillingInfo | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkingOut, setCheckingOut] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [busy, setBusy] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const fetchBilling = useCallback(async () => {
    if (!mounted) return;
    try {
      const [b, sub] = await Promise.all([
        api.get<BillingInfo>('/organizations/me/billing'),
        api.get<SubscriptionDetail>('/organizations/me/billing/subscription').catch(() => null),
      ]);
      setBilling(b);
      setSubscription(sub);
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
    setActionNotice(null);
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

  const handleChangePlan = async (planKey: string, schedule: 'now' | 'cycle_end') => {
    setBusy(true);
    setActionError(null);
    setActionNotice(null);
    try {
      const res = await api.post<ChangePlanResult>(
        '/organizations/me/billing/subscription/change-plan',
        { plan: planKey, schedule_change_at: schedule },
      );
      setActionNotice(
        schedule === 'now'
          ? `Plan changed to ${res.plan}. Your new limits are now active.`
          : `Plan change to ${res.plan} scheduled for the end of your current billing cycle.`,
      );
      await fetchBilling();
    } catch (e: any) {
      setActionError(e.message || 'Failed to change plan');
    } finally {
      setBusy(false);
    }
  };

  const handleCancel = async () => {
    setBusy(true);
    setActionError(null);
    setActionNotice(null);
    try {
      const res = await api.post<CancelResult>('/organizations/me/billing/subscription/cancel', {
        cancel_at_cycle_end: true,
      });
      setConfirmCancel(false);
      setActionNotice(
        res.cancel_at_cycle_end
          ? `Your subscription will cancel at the end of the current cycle${res.current_end ? ` (${formatDate(res.current_end)})` : ''}. You'll keep access until then.`
          : 'Your subscription has been cancelled.',
      );
      await fetchBilling();
    } catch (e: any) {
      setActionError(e.message || 'Failed to cancel subscription');
    } finally {
      setBusy(false);
    }
  };

  const sortedPlans = billing
    ? [...billing.available_plans].sort((a, b) => PLAN_ORDER.indexOf(a.key) - PLAN_ORDER.indexOf(b.key))
    : [];

  const hasSubscription = subscription?.has_subscription === true;
  const isFree = billing ? billing.plan === 'free' : true;
  const subStatus = subscription?.status || billing?.plan_status;

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

      {actionError && <div className="bg-red-50 text-red-700 px-4 py-3 rounded mb-6">{actionError}</div>}
      {actionNotice && (
        <div className="bg-green-50 text-green-800 border border-green-200 px-4 py-3 rounded mb-6">{actionNotice}</div>
      )}

      {!loading && billing && (
        <>
          {/* Current plan / subscription status */}
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Current plan</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {billing.plan_name}
                  {isFree && (
                    <span className="ml-2 align-middle px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      Trial / Free
                    </span>
                  )}
                </p>
                <p className="text-sm text-gray-500 mt-1">{formatINR(billing.available_plans.find((p) => p.key === billing.plan)?.price_inr || 0)}</p>
              </div>
              {hasSubscription ? (
                <div className="text-sm text-gray-600 space-y-1 text-right">
                  <p>
                    Renews on:{' '}
                    <span className="font-medium text-gray-900">{formatDate(subscription?.current_end)}</span>
                  </p>
                  <p>
                    Status:{' '}
                    <span className={`font-medium ${subStatus === 'active' ? 'text-green-700' : 'text-yellow-700'}`}>
                      {subStatus || billing.plan_status}
                    </span>
                    {subscription?.cancel_at_cycle_end && (
                      <span className="ml-1 text-xs text-orange-600">(cancelling at cycle end)</span>
                    )}
                  </p>
                  {subscription?.payment_method && (
                    <p>
                      Payment method:{' '}
                      <span className="font-medium text-gray-900">{subscription.payment_method}</span>
                    </p>
                  )}
                </div>
              ) : (
                <div className="text-sm text-gray-500 max-w-xs text-right">
                  {billing.plan_status === 'cancelled' ? (
                    <p>Your subscription is cancelled. You can resubscribe anytime.</p>
                  ) : (
                    <p>
                      You're on the free tier. Upgrade to unlock higher limits and usage-based billing.
                    </p>
                  )}
                </div>
              )}
            </div>

            {hasSubscription && (
              <div className="flex flex-wrap gap-3 mt-6 pt-5 border-t border-gray-100">
                {subscription?.cancel_at_cycle_end ? (
                  <button
                    onClick={() => handleChangePlan(billing.plan, 'now')}
                    disabled={busy}
                    className="px-4 py-2 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    Resume subscription
                  </button>
                ) : (
                  <>
                    {!confirmCancel ? (
                      <button
                        onClick={() => setConfirmCancel(true)}
                        disabled={busy}
                        className="px-4 py-2 rounded-md text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                      >
                        Cancel subscription
                      </button>
                    ) : (
                      <>
                        <button
                          onClick={handleCancel}
                          disabled={busy}
                          className="px-4 py-2 rounded-md text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
                        >
                          {busy ? 'Cancelling...' : 'Confirm cancel at cycle end'}
                        </button>
                        <button
                          onClick={() => setConfirmCancel(false)}
                          disabled={busy}
                          className="px-4 py-2 rounded-md text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                        >
                          Keep subscription
                        </button>
                      </>
                    )}
                  </>
                )}
              </div>
            )}
          </div>

          {/* Current-period usage vs plan limits */}
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h3 className="text-sm font-semibold text-gray-700">Usage this month</h3>
            <p className="text-xs text-gray-400 mt-1 mb-4">Current period usage against your plan's limits.</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <p className="text-sm font-medium text-gray-800">Tokens</p>
                <ProgressBar
                  used={billing.usage_billing?.total_tokens || 0}
                  limit={billing.limits.included_monthly_tokens}
                />
                {billing.usage_billing && billing.usage_billing.overage_tokens > 0 && (
                  <p className="text-xs text-red-600 mt-2">
                    {formatNum(billing.usage_billing.overage_tokens)} tokens over included limit
                    {billing.usage_billing.reported_to_razorpay ? ' — billed as a Razorpay add-on' : ' — will be invoiced at period end'}
                  </p>
                )}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-800">Chatbots</p>
                <ProgressBar used={billing.usage.chatbots} limit={billing.limits.chatbots} color="bg-emerald-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-800">Messages / month</p>
                <ProgressBar used={billing.usage.monthly_messages} limit={billing.limits.monthly_messages} color="bg-violet-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-800">Knowledge sources</p>
                <ProgressBar used={billing.usage.knowledge_sources} limit={billing.limits.knowledge_sources} color="bg-teal-600" />
              </div>
            </div>
          </div>

          {/* Invoice history */}
          {hasSubscription && subscription?.invoices.length ? (
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Invoice history</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Invoice</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Issued</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {subscription.invoices.map((inv) => (
                      <tr key={inv.id}>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{inv.id}</td>
                        <td className="px-4 py-3 text-sm text-gray-600">{formatDate(inv.issued_at)}</td>
                        <td className="px-4 py-3 text-sm text-gray-900">
                          {inv.amount_paise != null ? `₹${(inv.amount_paise / 100).toLocaleString('en-IN')}` : '—'}
                        </td>
                        <td className="px-4 py-3 text-sm text-right">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${inv.status === 'paid' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                            {inv.status || 'unknown'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          {/* Plan comparison / upgrade */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {sortedPlans.map((plan) => {
              const isCurrent = plan.key === billing.plan;
              const disabled = !billing.billing_enabled || busy;
              return (
                <div
                  key={plan.key}
                  className={`bg-white rounded-lg shadow p-6 flex flex-col ${isCurrent ? 'ring-2 ring-blue-500' : ''}`}
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
                    {plan.limits.included_monthly_tokens ? (
                      <li className="text-sm text-gray-600 flex items-start gap-2">
                        <span className="text-green-500 mt-0.5">✓</span>
                        {formatNum(plan.limits.included_monthly_tokens)} included tokens / month
                      </li>
                    ) : null}
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
                  {hasSubscription && !isCurrent && plan.price_inr > 0 && (
                    <button
                      onClick={() => handleChangePlan(plan.key, plan.price_inr > billing.available_plans.find((p) => p.key === billing.plan)?.price_inr! ? 'now' : 'cycle_end')}
                      disabled={disabled}
                      className="mt-2 px-4 py-2 rounded-md text-sm font-medium border border-blue-200 text-blue-700 hover:bg-blue-50 disabled:opacity-50"
                    >
                      {busy ? 'Switching...' : 'Switch (existing sub)'}
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          <p className="text-xs text-gray-400 mt-6">
            Payments are processed by Razorpay. Subscriptions, plan changes, and cancellation are
            managed in-house through Razorpay's subscription APIs (Razorpay has no self-serve
            customer portal). Plan changes take effect immediately on upgrade and at the end of the
            billing cycle on downgrade.
          </p>
        </>
      )}
    </DashboardLayout>
  );
}