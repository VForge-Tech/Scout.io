import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { api } from '../../../lib/api';
import DashboardLayout from '../../../components/DashboardLayout';

interface Chatbot {
  id: string;
  name: string;
  description: string;
  behaviour: string;
  config: Record<string, unknown>;
}

interface KnowledgeSource {
  id: string;
  source_type: string;
  uri: string;
  config: Record<string, unknown>;
  connector_type?: string | null;
  sync_status: string;
  last_sync_at?: string | null;
}

interface Policy {
  id: string;
  name: string;
  policy_type: string;
  rules: Record<string, unknown>;
}

const BEHAVIOUR_OPTIONS = [
  { value: 'fast', label: 'Fast', model: 'GPT-3.5 Turbo', description: 'Quick responses for simple queries. Lowest cost.' },
  { value: 'balanced', label: 'Balanced', model: 'GPT-4o Mini', description: 'General purpose responses. Great price/performance.' },
  { value: 'accurate', label: 'Accurate', model: 'GPT-4o', description: 'High quality responses for complex queries. Highest cost.' },
];

const SOURCE_TYPES = [
  { value: 'web', label: 'Web URL' },
  { value: 'pdf', label: 'PDF Document' },
  { value: 'csv', label: 'CSV File' },
  { value: 'text', label: 'Plain Text' },
];

export default function ChatbotEdit() {
  const router = useRouter();
  const { id } = router.query;
  const chatbotId = typeof id === 'string' ? id : '';

  const [chatbot, setChatbot] = useState<Chatbot | null>(null);
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Basic info form
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [behaviour, setBehaviour] = useState('balanced');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  // New source form
  const [showSourceForm, setShowSourceForm] = useState(false);
  const [sourceType, setSourceType] = useState('web');
  const [sourceUri, setSourceUri] = useState('');
  const [sourceConnector, setSourceConnector] = useState('');
  const [sourceSaving, setSourceSaving] = useState(false);
  const [sourceError, setSourceError] = useState('');

  // Policy forms
  const [showPolicyForm, setShowPolicyForm] = useState(false);
  const [policyType, setPolicyType] = useState('source_filter');
  const [policyName, setPolicyName] = useState('');
  const [allowedSourceIds, setAllowedSourceIds] = useState<string[]>([]);
  const [blockedTerms, setBlockedTerms] = useState('');
  const [policySaving, setPolicySaving] = useState(false);
  const [policyError, setPolicyError] = useState('');
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null);

  // Widget snippet
  const [theme, setTheme] = useState('light');
  const [snippet, setSnippet] = useState('');
  const [copied, setCopied] = useState(false);
  const [showWidget, setShowWidget] = useState(false);
  const [widgetLoading, setWidgetLoading] = useState(false);

  // Delete confirmation
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const fetchAll = async () => {
    if (!chatbotId) return;
    try {
      setLoading(true);
      setError('');
      const [bot, srcs, pols] = await Promise.all([
        api.get<Chatbot>(`/chatbots/${chatbotId}`),
        api.get<KnowledgeSource[]>(`/chatbots/${chatbotId}/knowledge-sources`),
        api.get<Policy[]>(`/chatbots/${chatbotId}/policies`),
      ]);
      setChatbot(bot);
      setSources(srcs);
      setPolicies(pols);
      setName(bot.name);
      setDescription(bot.description || '');
      setBehaviour(bot.behaviour || 'balanced');
    } catch (e: any) {
      setError(e.message || 'Failed to load chatbot');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (chatbotId) fetchAll();
  }, [chatbotId]);

  const generateSnippet = async () => {
    if (!chatbotId) return;
    setWidgetLoading(true);
    try {
      const res = await api.get<any>(`/developer/widget-snippet?chatbot_id=${chatbotId}&theme=${theme}`);
      setSnippet(res.snippet);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setWidgetLoading(false);
    }
  };

  useEffect(() => {
    if (showWidget && chatbotId) generateSnippet();
  }, [showWidget, theme, chatbotId]);

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg('');
    try {
      const updated = await api.put<Chatbot>(`/chatbots/${chatbotId}`, {
        name,
        description,
        behaviour,
      });
      setChatbot(updated);
      setSaveMsg('Chatbot updated');
      setTimeout(() => setSaveMsg(''), 3000);
    } catch (e: any) {
      setSaveMsg(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    setSourceSaving(true);
    setSourceError('');
    try {
      await api.post(`/chatbots/${chatbotId}/knowledge-sources`, {
        source_type: sourceType,
        uri: sourceUri,
        connector_type: sourceConnector || null,
        config: {},
      });
      setSourceUri('');
      setSourceConnector('');
      setShowSourceForm(false);
      const srcs = await api.get<KnowledgeSource[]>(`/chatbots/${chatbotId}/knowledge-sources`);
      setSources(srcs);
    } catch (e: any) {
      setSourceError(e.message);
    } finally {
      setSourceSaving(false);
    }
  };

  const handleDeleteSource = async (sourceId: string) => {
    if (!confirm('Remove this knowledge source?')) return;
    try {
      await api.delete(`/chatbots/${chatbotId}/knowledge-sources/${sourceId}`);
      setSources(sources.filter((s) => s.id !== sourceId));
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleEditPolicy = (policy: Policy) => {
    setEditingPolicy(policy);
    setPolicyType(policy.policy_type);
    setPolicyName(policy.name);
    const rules = policy.rules as Record<string, any>;
    setAllowedSourceIds(rules.allowed_source_ids || []);
    setBlockedTerms((rules.blocked_terms || []).join(', '));
    setShowPolicyForm(true);
  };

  const handleAddPolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    setPolicySaving(true);
    setPolicyError('');
    const rules: Record<string, unknown> =
      policyType === 'source_filter'
        ? { allowed_source_ids: allowedSourceIds }
        : { blocked_terms: blockedTerms.split(',').map((t) => t.trim()).filter(Boolean) };

    try {
      if (editingPolicy) {
        await api.put(`/chatbots/${chatbotId}/policies/${editingPolicy.id}`, {
          name: policyName,
          rules,
        });
      } else {
        await api.post(`/chatbots/${chatbotId}/policies`, {
          name: policyName || policyType,
          policy_type: policyType,
          rules,
        });
      }
      setShowPolicyForm(false);
      setEditingPolicy(null);
      setPolicyName('');
      setAllowedSourceIds([]);
      setBlockedTerms('');
      const pols = await api.get<Policy[]>(`/chatbots/${chatbotId}/policies`);
      setPolicies(pols);
    } catch (e: any) {
      setPolicyError(e.message);
    } finally {
      setPolicySaving(false);
    }
  };

  const handleDeletePolicy = async (policyId: string) => {
    if (!confirm('Delete this policy?')) return;
    try {
      await api.delete(`/chatbots/${chatbotId}/policies/${policyId}`);
      setPolicies(policies.filter((p) => p.id !== policyId));
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDeleteChatbot = async () => {
    setDeleting(true);
    try {
      await api.delete(`/chatbots/${chatbotId}`);
      router.push('/dashboard/chatbots');
    } catch (e: any) {
      setError(e.message);
      setShowDeleteModal(false);
      setDeleting(false);
    }
  };

  const sourceFilterPolicy = policies.find((p) => p.policy_type === 'source_filter');
  const contentFilterPolicy = policies.find((p) => p.policy_type === 'content_filter');

  if (loading) {
    return (
      <DashboardLayout>
        <p className="text-gray-500">Loading chatbot...</p>
      </DashboardLayout>
    );
  }

  if (error && !chatbot) {
    return (
      <DashboardLayout>
        <p className="text-red-500">{error}</p>
        <a href="/dashboard/chatbots" className="text-blue-600 text-sm mt-4 inline-block">← Back to chatbots</a>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-4xl">
        <div className="flex justify-between items-center mb-6">
          <div>
            <a href="/dashboard/chatbots" className="text-sm text-gray-600 hover:text-gray-900">← Back to chatbots</a>
            <h2 className="text-2xl font-bold text-gray-900 mt-1">{chatbot?.name}</h2>
          </div>
          <div className="flex space-x-3">
            <button
              onClick={() => setShowWidget(!showWidget)}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md text-sm hover:bg-gray-300"
            >
              {showWidget ? 'Hide Widget' : 'Widget Snippet'}
            </button>
            <button
              onClick={() => setShowDeleteModal(true)}
              className="px-4 py-2 bg-red-600 text-white rounded-md text-sm hover:bg-red-700"
            >
              Delete
            </button>
          </div>
        </div>

        {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded mb-6">{error}</div>}

        <form onSubmit={(e) => { e.preventDefault(); handleSave(); }} className="bg-white rounded-lg shadow p-6 space-y-6 mb-8">
          <h3 className="text-lg font-medium text-gray-900">Basic Information</h3>
          {saveMsg && (
            <div className={`px-4 py-3 rounded ${saveMsg.includes('updated') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
              {saveMsg}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border rounded-md px-3 py-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full border rounded-md px-3 py-2"
              rows={3}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Model Tier</label>
            <div className="space-y-3">
              {BEHAVIOUR_OPTIONS.map((opt) => (
                <label key={opt.value} className={`flex items-start p-4 border rounded-lg cursor-pointer transition ${behaviour === opt.value ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                  <input
                    type="radio"
                    name="behaviour"
                    value={opt.value}
                    checked={behaviour === opt.value}
                    onChange={() => setBehaviour(opt.value)}
                    className="mt-1 mr-3 h-4 w-4 text-blue-600"
                  />
                  <div>
                    <div className="flex items-center">
                      <span className="font-medium text-gray-900">{opt.label}</span>
                      <span className="ml-2 text-xs text-gray-500">({opt.model})</span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{opt.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
          <div className="flex justify-end pt-4 border-t">
            <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>

        {showWidget && (
          <div className="bg-white rounded-lg shadow p-6 space-y-4 mb-8">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900">Widget Snippet</h3>
              <label className="flex items-center text-sm text-gray-700">
                Theme
                <select
                  value={theme}
                  onChange={(e) => setTheme(e.target.value)}
                  className="ml-2 border rounded-md px-2 py-1"
                >
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                </select>
              </label>
            </div>
            {widgetLoading ? (
              <p className="text-gray-500 text-sm">Generating snippet...</p>
            ) : (
              <div>
                <div className="flex justify-end mb-2">
                  <button
                    onClick={() => { navigator.clipboard.writeText(snippet); setCopied(true); }}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <pre className="bg-gray-50 p-4 rounded text-sm overflow-x-auto border">{snippet}</pre>
              </div>
            )}
          </div>
        )}

        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">Knowledge Sources</h3>
            <button
              onClick={() => setShowSourceForm(!showSourceForm)}
              className="px-3 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
            >
              {showSourceForm ? 'Cancel' : '+ Add Source'}
            </button>
          </div>

          {showSourceForm && (
            <form onSubmit={handleAddSource} className="border rounded-lg p-4 mb-4 space-y-4 bg-gray-50">
              {sourceError && <div className="bg-red-50 text-red-700 px-4 py-2 rounded text-sm">{sourceError}</div>}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                  <select
                    value={sourceType}
                    onChange={(e) => setSourceType(e.target.value)}
                    className="w-full border rounded-md px-3 py-2"
                  >
                    {SOURCE_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Connector</label>
                  <input
                    type="text"
                    value={sourceConnector}
                    onChange={(e) => setSourceConnector(e.target.value)}
                    className="w-full border rounded-md px-3 py-2"
                    placeholder="e.g., website-crawler"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">URI / Location</label>
                <input
                  type="text"
                  value={sourceUri}
                  onChange={(e) => setSourceUri(e.target.value)}
                  className="w-full border rounded-md px-3 py-2"
                  required
                  placeholder="https://example.com/docs or path"
                />
              </div>
              <div className="flex justify-end">
                <button type="submit" disabled={sourceSaving} className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50">
                  {sourceSaving ? 'Adding...' : 'Add Source'}
                </button>
              </div>
            </form>
          )}

          {sources.length === 0 ? (
            <p className="text-gray-500 text-sm">No knowledge sources attached. Add one above to give your chatbot context.</p>
          ) : (
            <div className="divide-y divide-gray-200">
              {sources.map((s) => (
                <div key={s.id} className="py-3 flex justify-between items-center">
                  <div>
                    <div className="font-medium text-gray-900">{s.uri}</div>
                    <div className="text-sm text-gray-500">
                      {s.source_type}
                      {s.connector_type && ` · ${s.connector_type}`} · sync: {s.sync_status}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteSource(s.id)}
                    className="text-red-600 hover:text-red-900 text-sm"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">Policies</h3>
            <button
              onClick={() => { setEditingPolicy(null); setPolicyName(''); setPolicyType('source_filter'); setAllowedSourceIds([]); setBlockedTerms(''); setShowPolicyForm(!showPolicyForm); }}
              className="px-3 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
            >
              {showPolicyForm ? 'Cancel' : '+ Add Policy'}
            </button>
          </div>

          {showPolicyForm && (
            <form onSubmit={handleAddPolicy} className="border rounded-lg p-4 mb-4 space-y-4 bg-gray-50">
              {policyError && <div className="bg-red-50 text-red-700 px-4 py-2 rounded text-sm">{policyError}</div>}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Policy Type</label>
                  <select
                    value={policyType}
                    onChange={(e) => setPolicyType(e.target.value)}
                    className="w-full border rounded-md px-3 py-2"
                  >
                    <option value="source_filter">Source Filter</option>
                    <option value="content_filter">Content Filter</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                  <input
                    type="text"
                    value={policyName}
                    onChange={(e) => setPolicyName(e.target.value)}
                    className="w-full border rounded-md px-3 py-2"
                    placeholder={policyType}
                  />
                </div>
              </div>

              {policyType === 'source_filter' ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Allowed Sources
                  </label>
                  {sources.length === 0 ? (
                    <p className="text-sm text-gray-500">Add knowledge sources first to configure this filter.</p>
                  ) : (
                    <div className="space-y-2 border rounded p-3 max-h-48 overflow-y-auto">
                      {sources.map((s) => (
                        <label key={s.id} className="flex items-center text-sm">
                          <input
                            type="checkbox"
                            checked={allowedSourceIds.includes(s.id)}
                            onChange={(e) => {
                              setAllowedSourceIds((prev) =>
                                e.target.checked
                                  ? [...prev, s.id]
                                  : prev.filter((x) => x !== s.id)
                              );
                            }}
                            className="mr-2 h-4 w-4 text-blue-600"
                          />
                          {s.uri} <span className="ml-2 text-xs text-gray-500">({s.source_type})</span>
                        </label>
                      ))}
                    </div>
                  )}
                  <p className="text-xs text-gray-500 mt-1">
                    Only the selected sources will be used for answering. Leave empty to allow all.
                  </p>
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Blocked Terms</label>
                  <textarea
                    value={blockedTerms}
                    onChange={(e) => setBlockedTerms(e.target.value)}
                    className="w-full border rounded-md px-3 py-2"
                    rows={3}
                    placeholder="e.g., pricing, confidential, internal"
                  />
                  <p className="text-xs text-gray-500 mt-1">Comma-separated. Content matching any term is excluded from answers.</p>
                </div>
              )}

              <div className="flex justify-end">
                <button type="submit" disabled={policySaving} className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50">
                  {policySaving ? 'Saving...' : editingPolicy ? 'Update Policy' : 'Create Policy'}
                </button>
              </div>
            </form>
          )}

          {policies.length === 0 ? (
            <p className="text-gray-500 text-sm">No policies configured.</p>
          ) : (
            <div className="divide-y divide-gray-200">
              {policies.map((p) => {
                const rules = p.rules as Record<string, any>;
                const summary = p.policy_type === 'source_filter'
                  ? `${(rules.allowed_source_ids || []).length} allowed source(s)`
                  : `${(rules.blocked_terms || []).length} blocked term(s)`;
                return (
                  <div key={p.id} className="py-3 flex justify-between items-center">
                    <div>
                      <div className="font-medium text-gray-900">{p.name || p.policy_type}</div>
                      <div className="text-sm text-gray-500">
                        {p.policy_type === 'source_filter' ? 'Source Filter' : 'Content Filter'} · {summary}
                      </div>
                    </div>
                    <div className="flex space-x-3">
                      <button onClick={() => handleEditPolicy(p)} className="text-blue-600 hover:text-blue-900 text-sm">Edit</button>
                      <button onClick={() => handleDeletePolicy(p.id)} className="text-red-600 hover:text-red-900 text-sm">Delete</button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Delete Chatbot</h3>
            <p className="text-gray-600 text-sm mb-6">
              Are you sure you want to delete "{chatbot?.name}"? This will permanently remove the
              chatbot, its knowledge sources, and policies. This action cannot be undone.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                disabled={deleting}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md text-sm hover:bg-gray-300 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteChatbot}
                disabled={deleting}
                className="px-4 py-2 bg-red-600 text-white rounded-md text-sm hover:bg-red-700 disabled:opacity-50"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}