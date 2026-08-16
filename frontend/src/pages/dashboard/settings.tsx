import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import DashboardLayout from '../../components/DashboardLayout';

interface OrgConfig {
  name: string;
  configuration: Record<string, unknown>;
}

interface MfaSetupData {
  secret: string;
  provisioning_uri: string;
  qr_data_uri: string;
}

function MfaSection() {
  const [mfaEnabled, setMfaEnabled] = useState<boolean | null>(null);
  const [mode, setMode] = useState<'idle' | 'setup' | 'codes' | 'action'>('idle');
  const [setupData, setSetupData] = useState<MfaSetupData | null>(null);
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [action, setAction] = useState<'disable' | 'regenerate' | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<{ mfa_enabled: boolean }>('/auth/mfa/status')
      .then((d) => setMfaEnabled(d.mfa_enabled))
      .catch(() => setMfaEnabled(false));
  }, []);

  const startSetup = async () => {
    setError('');
    if (!password) {
      setError('Enter your current password.');
      return;
    }
    try {
      const data = await api.post<MfaSetupData>('/auth/mfa/setup', { password });
      setSetupData(data);
      setPassword('');
      setMode('setup');
    } catch (e: any) {
      setError(e.message);
    }
  };

  const confirmEnable = async () => {
    setError('');
    if (!setupData) return;
    try {
      const data = await api.post<{ recovery_codes: string[] }>('/auth/mfa/enable', {
        secret: setupData.secret,
        code,
      });
      setCodes(data.recovery_codes);
      setCode('');
      setMfaEnabled(true);
      setMode('codes');
      setMessage('Two-factor authentication enabled.');
    } catch (e: any) {
      setError(e.message);
    }
  };

  const runAction = async () => {
    setError('');
    try {
      if (action === 'disable') {
        await api.post('/auth/mfa/disable', { password, code });
        setMfaEnabled(false);
        setCodes(null);
        setAction(null);
        setPassword('');
        setCode('');
        setMode('idle');
        setMessage('Two-factor authentication disabled.');
      } else if (action === 'regenerate') {
        const data = await api.post<{ recovery_codes: string[] }>(
          '/auth/mfa/recovery-codes/regenerate',
          { password, code },
        );
        setCodes(data.recovery_codes);
        setAction(null);
        setPassword('');
        setCode('');
        setMode('codes');
        setMessage('New recovery codes generated. Store them safely.');
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  const renderCodes = () => (
    <div>
      <h4 className="text-base font-medium text-gray-900 mb-2">Recovery Codes</h4>
      <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2 mb-4">
        Save these one-time codes somewhere safe. Each code can be used once to sign in if you lose
        your authenticator app.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-4">
        {codes?.map((c, i) => (
          <code key={i} className="bg-gray-50 border rounded px-3 py-2 text-sm font-mono">
            {c}
          </code>
        ))}
      </div>
      <button
        onClick={() => { setMode('idle'); setCodes(null); setMessage(''); }}
        className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm"
      >
        Done
      </button>
    </div>
  );

  const renderActionForm = () => (
    <div>
      <p className="text-sm text-gray-600 mb-4">
        {action === 'disable'
          ? 'Confirm your password and enter a current code to disable two-factor authentication.'
          : 'Confirm your password and enter a current code to generate new recovery codes.'}
      </p>
      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full border rounded-md px-3 py-2"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Authentication Code</label>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="mt-1 block w-full border rounded-md px-3 py-2"
          />
        </div>
        <div className="flex gap-2">
          <button onClick={runAction} className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm">
            Confirm
          </button>
          <button
            onClick={() => { setAction(null); setPassword(''); setCode(''); setError(''); }}
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md text-sm"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );

  const renderSetup = () => (
    <div>
      <h4 className="text-base font-medium text-gray-900 mb-2">Scan with your Authenticator App</h4>
      <div className="flex flex-col sm:flex-row gap-4 mb-4">
        {setupData && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={setupData.qr_data_uri}
            alt="TOTP QR code"
            className="w-40 h-40 border rounded"
          />
        )}
        <div className="flex-1 space-y-3">
          {setupData && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700">Manual Entry Key</label>
                <code className="block bg-gray-50 border rounded px-3 py-2 text-sm font-mono break-all">
                  {setupData.secret}
                </code>
              </div>
              <p className="text-sm text-gray-500">
                If you cannot scan the QR code, enter this key manually in your authenticator app.
              </p>
            </>
          )}
        </div>
      </div>
      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">6-digit Verification Code</label>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="mt-1 block w-full border rounded-md px-3 py-2"
            placeholder="000000"
          />
        </div>
        <div className="flex gap-2">
          <button onClick={confirmEnable} className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm">
            Enable Two-Factor Auth
          </button>
          <button
            onClick={() => { setMode('idle'); setSetupData(null); setCode(''); setError(''); }}
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md text-sm"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );

  if (mfaEnabled === null) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6 max-w-2xl mt-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Two-Factor Authentication</h3>
      {message && (
        <div className="bg-green-50 text-green-700 px-4 py-2 rounded mb-4 text-sm">{message}</div>
      )}
      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-2 rounded mb-4 text-sm">{error}</div>
      )}
      {mode === 'codes' && renderCodes()}
      {mode === 'action' && renderActionForm()}
      {mode === 'setup' && renderSetup()}
      {mode === 'idle' && mfaEnabled && (
        <div>
          <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2 mb-4">
            Two-factor authentication is enabled on your account.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => { setAction('regenerate'); setError(''); }}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm"
            >
              Regenerate Recovery Codes
            </button>
            <button
              onClick={() => { setAction('disable'); setError(''); }}
              className="px-4 py-2 bg-red-600 text-white rounded-md text-sm"
            >
              Disable Two-Factor Auth
            </button>
          </div>
        </div>
      )}
      {mode === 'idle' && !mfaEnabled && (
        <div>
          <p className="text-sm text-gray-600 mb-4">
            Two-factor authentication adds an extra layer of security to your account.
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700">Current Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full border rounded-md px-3 py-2"
              placeholder="Enter your password to continue"
            />
          </div>
          <button
            onClick={startSetup}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md text-sm"
          >
            Enable Two-Factor Auth
          </button>
        </div>
      )}
    </div>
  );
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
      <MfaSection />
    </DashboardLayout>
  );
}
