import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../../lib/api';
import DashboardLayout from '../../components/DashboardLayout';

interface Chatbot {
  id: string;
  name: string;
}

interface KnowledgeSource {
  id: string;
  organization_id: string;
  chatbot_id: string | null;
  source_type: string;
  uri: string;
  config: Record<string, unknown>;
  connector_type?: string | null;
  sync_status: string;
  last_sync_at: string | null;
  created_at: string;
}

type SourceRow = KnowledgeSource & { chatbot_name: string };

const SOURCE_TYPES = [
  { value: 'url', label: 'Website URL' },
  { value: 'pdf', label: 'PDF Document' },
  { value: 'markdown', label: 'Markdown File' },
  { value: 'docx', label: 'Word (DOCX) File' },
  { value: 'text', label: 'Text File' },
  { value: 'sql', label: 'SQL Database' },
  { value: 'api', label: 'External API' },
  { value: 'git', label: 'Git Repository' },
];

const CONNECTOR_TYPES: Record<string, string> = {
  sql: 'sql',
  api: 'api',
  git: 'git',
};

function statusBadge(status: string) {
  switch (status) {
    case 'completed':
      return <span className="px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">Synced</span>;
    case 'failed':
      return <span className="px-2 py-1 rounded-full text-xs bg-red-100 text-red-800">Failed</span>;
    case 'processing':
      return (
        <span className="px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800 flex items-center gap-1">
          <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
          </svg>
          Syncing
        </span>
      );
    default:
      return <span className="px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-700">Pending</span>;
  }
}

function formatTime(value: string | null) {
  if (!value) return '—';
  const d = new Date(value);
  return d.toLocaleString();
}

export default function KnowledgeSourcesPage() {
  const [chatbots, setChatbots] = useState<Chatbot[]>([]);
  const [sources, setSources] = useState<SourceRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  // Add-source modal state
  const [showAdd, setShowAdd] = useState(false);
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState('');
  const [selectedChatbot, setSelectedChatbot] = useState('');
  const [sourceType, setSourceType] = useState('url');
  const [uri, setUri] = useState('');
  const [file, setFile] = useState<File | null>(null);

  // Connector-specific fields
  const [sqlQuery, setSqlQuery] = useState('');
  const [sqlLimit, setSqlLimit] = useState('1000');
  const [apiMethod, setApiMethod] = useState('GET');
  const [apiHeaders, setApiHeaders] = useState('');
  const [apiBody, setApiBody] = useState('');
  const [gitBranch, setGitBranch] = useState('main');
  const [gitExtensions, setGitExtensions] = useState('.md, .py, .js, .ts, .txt, .rst');
  const [gitMaxSize, setGitMaxSize] = useState('100');

  // Delete confirmation modal
  const [pendingDelete, setPendingDelete] = useState<SourceRow | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Retry
  const [retrying, setRetrying] = useState<Record<string, boolean>>({});

  const fetchAll = useCallback(async () => {
    if (!mounted) return;
    try {
      const bots = await api.get<Chatbot[]>('/chatbots');
      setChatbots(bots);
      const rows: SourceRow[] = [];
      for (const bot of bots) {
        try {
          const botSources = await api.get<KnowledgeSource[]>(`/chatbots/${bot.id}/knowledge-sources`);
          for (const s of botSources) {
            rows.push({ ...s, chatbot_name: bot.name });
          }
        } catch {
          // skip chatbot whose sources failed to load
        }
      }
      setSources(rows);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load knowledge sources');
    } finally {
      setLoading(false);
    }
  }, [mounted]);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    fetchAll();
    const interval = setInterval(fetchAll, 5000);
    return () => clearInterval(interval);
  }, [mounted, fetchAll]);

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedChatbot) {
      setAddError('Select a chatbot to attach this source to.');
      return;
    }
    setAdding(true);
    setAddError('');
    try {
      let sourceTypeValue = sourceType;
      let uriValue = uri;

      // File upload flow: upload the file first, then use the returned url as the uri
      if (sourceType === 'pdf' || sourceType === 'markdown' || sourceType === 'docx' || sourceType === 'text') {
        if (!file) {
          setAddError('Choose a file to upload.');
          setAdding(false);
          return;
        }
        const uploadRes = await api.upload<{ url: string; filename: string }>(`/uploads/${selectedChatbot}`, file);
        uriValue = uploadRes.url;
      }

      const connectorType = CONNECTOR_TYPES[sourceType] || null;
      let config: Record<string, unknown> = {};
      if (sourceType === 'sql') {
        config = { query: sqlQuery, limit: Number(sqlLimit) || 1000 };
      } else if (sourceType === 'api') {
        config = { method: apiMethod };
        if (apiHeaders.trim()) {
          try {
            config.headers = JSON.parse(apiHeaders);
          } catch {
            setAddError('API headers must be valid JSON, e.g. {"Authorization": "Bearer ..."}');
            setAdding(false);
            return;
          }
        }
        if (apiMethod === 'POST' && apiBody.trim()) {
          try {
            config.body = JSON.parse(apiBody);
          } catch {
            setAddError('API body must be valid JSON.');
            setAdding(false);
            return;
          }
        }
      } else if (sourceType === 'git') {
        config = {
          branch: gitBranch,
          include_extensions: gitExtensions.split(',').map((e) => e.trim()).filter(Boolean),
          max_file_size_kb: Number(gitMaxSize) || 100,
        };
      }

      await api.post(`/chatbots/${selectedChatbot}/knowledge-sources`, {
        source_type: sourceTypeValue,
        uri: uriValue,
        connector_type: connectorType,
        config,
      });

      setShowAdd(false);
      setUri('');
      setFile(null);
      setSqlQuery('');
      setApiHeaders('');
      setApiBody('');
      setGitBranch('main');
      fetchAll();
    } catch (e: any) {
      setAddError(e.message);
    } finally {
      setAdding(false);
    }
  };

  const handleRetry = async (row: SourceRow) => {
    setRetrying((prev) => ({ ...prev, [row.id]: true }));
    try {
      await api.post(`/chatbots/${row.chatbot_id}/knowledge-sources/${row.id}/sync`);
      fetchAll();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRetrying((prev) => ({ ...prev, [row.id]: false }));
    }
  };

  const handleDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await api.delete(`/chatbots/${pendingDelete.chatbot_id}/knowledge-sources/${pendingDelete.id}`);
      setPendingDelete(null);
      fetchAll();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Knowledge Sources</h2>
        <button
          onClick={() => setShowAdd(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
        >
          + Add Source
        </button>
      </div>

      {error && <div className="bg-red-50 text-red-700 px-4 py-3 rounded mb-6">{error}</div>}
      {loading && <p className="text-gray-500">Loading knowledge sources...</p>}

      {!loading && !error && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {sources.length === 0 ? (
            <div className="p-12 text-center text-gray-500">
              No knowledge sources yet. Add one to give your chatbots context.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Chatbot</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sync Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Synced</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {sources.map((row) => (
                    <tr key={row.id}>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">{row.chatbot_name}</td>
                      <td className="px-6 py-4 text-sm text-gray-700 truncate max-w-xs" title={row.uri}>{row.uri}</td>
                      <td className="px-6 py-4 text-sm">
                        <span className="text-gray-600">{row.source_type}</span>
                        {row.connector_type && (
                          <span className="ml-2 px-2 py-0.5 rounded bg-purple-100 text-purple-800 text-xs">{row.connector_type}</span>
                        )}
                      </td>
                      <td className="px-6 py-4">{statusBadge(row.sync_status)}</td>
                      <td className="px-6 py-4 text-sm text-gray-500">{formatTime(row.last_sync_at)}</td>
                      <td className="px-6 py-4 text-sm text-right whitespace-nowrap">
                        {row.sync_status === 'failed' && (
                          <button
                            onClick={() => handleRetry(row)}
                            disabled={retrying[row.id]}
                            className="text-blue-600 hover:text-blue-900 mr-3 disabled:opacity-50"
                          >
                            {retrying[row.id] ? 'Retrying...' : 'Retry'}
                          </button>
                        )}
                        <button
                          onClick={() => setPendingDelete(row)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {showAdd && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-gray-900">Add Knowledge Source</h3>
              <button onClick={() => setShowAdd(false)} className="text-gray-500 hover:text-gray-800">✕</button>
            </div>

            <form onSubmit={handleAddSource} className="space-y-4">
              {addError && <div className="bg-red-50 text-red-700 px-4 py-2 rounded text-sm">{addError}</div>}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Chatbot</label>
                <select
                  value={selectedChatbot}
                  onChange={(e) => setSelectedChatbot(e.target.value)}
                  className="w-full border rounded-md px-3 py-2"
                  required
                >
                  <option value="">— Select a chatbot —</option>
                  {chatbots.map((bot) => (
                    <option key={bot.id} value={bot.id}>{bot.name}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">This source will be attached to the selected chatbot.</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Source Type</label>
                <select
                  value={sourceType}
                  onChange={(e) => { setSourceType(e.target.value); setUri(''); setFile(null); }}
                  className="w-full border rounded-md px-3 py-2"
                >
                  {SOURCE_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>

              {(sourceType === 'pdf' || sourceType === 'markdown' || sourceType === 'docx' || sourceType === 'text') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    File ({sourceType === 'pdf' ? 'PDF' : sourceType === 'markdown' ? 'Markdown' : sourceType === 'docx' ? 'DOCX' : 'TXT'})
                  </label>
                  <input
                    type="file"
                    accept={
                      sourceType === 'pdf' ? '.pdf,application/pdf'
                      : sourceType === 'markdown' ? '.md,.markdown,text/markdown'
                      : sourceType === 'docx' ? '.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                      : '.txt,text/plain'
                    }
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    className="w-full border rounded-md px-3 py-2"
                    required
                  />
                </div>
              )}

              {sourceType !== 'pdf' && sourceType !== 'markdown' && sourceType !== 'docx' && sourceType !== 'text' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {sourceType === 'url' ? 'Website URL' :
                     sourceType === 'sql' ? 'Database Connection URI' :
                     sourceType === 'api' ? 'API Endpoint URL' :
                     'Git Repository URL'}
                  </label>
                  <input
                    type="text"
                    value={uri}
                    onChange={(e) => setUri(e.target.value)}
                    className="w-full border rounded-md px-3 py-2"
                    required
                    placeholder={
                      sourceType === 'url' ? 'https://example.com/docs' :
                      sourceType === 'sql' ? 'postgresql://user:pass@host:5432/db' :
                      sourceType === 'api' ? 'https://api.example.com/data' :
                      'https://github.com/org/repo.git'
                    }
                  />
                </div>
              )}

              {sourceType === 'sql' && (
                <div className="space-y-3 border rounded-lg p-4 bg-gray-50">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">SQL Query</label>
                    <textarea
                      value={sqlQuery}
                      onChange={(e) => setSqlQuery(e.target.value)}
                      className="w-full border rounded-md px-3 py-2"
                      rows={3}
                      required
                      placeholder="SELECT * FROM documents WHERE active = true"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Row Limit</label>
                    <input
                      type="number"
                      value={sqlLimit}
                      onChange={(e) => setSqlLimit(e.target.value)}
                      className="w-full border rounded-md px-3 py-2"
                      min={1}
                    />
                  </div>
                </div>
              )}

              {sourceType === 'api' && (
                <div className="space-y-3 border rounded-lg p-4 bg-gray-50">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">HTTP Method</label>
                    <select
                      value={apiMethod}
                      onChange={(e) => setApiMethod(e.target.value)}
                      className="w-full border rounded-md px-3 py-2"
                    >
                      <option value="GET">GET</option>
                      <option value="POST">POST</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Headers (JSON, optional)</label>
                    <textarea
                      value={apiHeaders}
                      onChange={(e) => setApiHeaders(e.target.value)}
                      className="w-full border rounded-md px-3 py-2"
                      rows={2}
                      placeholder='{"Authorization": "Bearer ..."}'
                    />
                  </div>
                  {apiMethod === 'POST' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Request Body (JSON, optional)</label>
                      <textarea
                        value={apiBody}
                        onChange={(e) => setApiBody(e.target.value)}
                        className="w-full border rounded-md px-3 py-2"
                        rows={2}
                        placeholder='{"key": "value"}'
                      />
                    </div>
                  )}
                </div>
              )}

              {sourceType === 'git' && (
                <div className="space-y-3 border rounded-lg p-4 bg-gray-50">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Branch</label>
                    <input
                      type="text"
                      value={gitBranch}
                      onChange={(e) => setGitBranch(e.target.value)}
                      className="w-full border rounded-md px-3 py-2"
                      placeholder="main"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Include Extensions</label>
                    <input
                      type="text"
                      value={gitExtensions}
                      onChange={(e) => setGitExtensions(e.target.value)}
                      className="w-full border rounded-md px-3 py-2"
                      placeholder=".md, .py, .js, .ts, .txt, .rst"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Max File Size (KB)</label>
                    <input
                      type="number"
                      value={gitMaxSize}
                      onChange={(e) => setGitMaxSize(e.target.value)}
                      className="w-full border rounded-md px-3 py-2"
                      min={1}
                    />
                  </div>
                </div>
              )}

              <div className="flex justify-end space-x-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setShowAdd(false)}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md text-sm hover:bg-gray-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={adding}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {adding ? 'Adding...' : 'Add Source'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {pendingDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Remove Knowledge Source</h3>
            <p className="text-gray-600 text-sm mb-6">
              Are you sure you want to remove this source (<span className="font-medium">{pendingDelete.uri}</span>)?
              This will permanently remove it from <span className="font-medium">{pendingDelete.chatbot_name}</span>
              {sources.filter((s) => s.uri === pendingDelete.uri).length > 1
                ? ' and every other chatbot using it'
                : ''} and delete its indexed data. This action cannot be undone.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setPendingDelete(null)}
                disabled={deleting}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md text-sm hover:bg-gray-300 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-4 py-2 bg-red-600 text-white rounded-md text-sm hover:bg-red-700 disabled:opacity-50"
              >
                {deleting ? 'Removing...' : 'Remove Source'}
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}