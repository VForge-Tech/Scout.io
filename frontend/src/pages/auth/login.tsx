import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { extractApiError } from '../../lib/api';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        throw new Error(await extractApiError(res));
      }
      const data = await res.json();
      if (data.mfa_required) {
        setMfaToken(data.mfa_token);
        return;
      }
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      router.push('/dashboard');
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!mfaToken) return;
    try {
      const res = await fetch('/api/v1/auth/mfa/verify-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mfa_token: mfaToken, code: mfaCode }),
      });
      if (!res.ok) {
        throw new Error(await extractApiError(res));
      }
      const data = await res.json();
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      router.push('/dashboard');
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-amber-50 via-white to-amber-50 px-4 py-12">
      {/* Background decorative elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-amber-200/30 rounded-full blur-3xl animate-pulse-soft" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-amber-300/20 rounded-full blur-3xl animate-pulse-soft delay-2" />
      </div>

      <div className="relative max-w-md w-full animate-fade-in">
        {/* Logo/brand */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-500 to-amber-700 shadow-lg shadow-amber-500/25 mb-6">
            <span className="text-2xl">🔍</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Scout.io</h1>
          <p className="text-gray-600 mt-2">Sign in to your dashboard</p>
        </div>

        {/* Login card */}
        <div className="card gradient-border p-8">
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 animate-fade-in">
              <svg className="w-5 h-5 text-red-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span className="text-red-700 text-sm">{error}</span>
            </div>
          )}

          {mfaToken ? (
            <form onSubmit={handleVerifyCode} className="space-y-6 animate-fade-in delay-1">
              <div className="text-center mb-4">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-amber-100 text-amber-600 mb-4">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2H8" />
                  </svg>
                </div>
                <h2 className="text-xl font-bold text-gray-900">Two-Factor Authentication</h2>
                <p className="text-gray-600 mt-2">Enter the 6-digit code from your authenticator app</p>
              </div>

              <div>
                <label className="label">Verification Code</label>
                <input
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  autoFocus
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  className="input text-center text-2xl tracking-widest font-mono"
                  maxLength={6}
                  required
                />
              </div>

              <button
                type="submit"
                className="btn-primary w-full py-3 text-lg"
              >
                Verify & Sign In
              </button>
            </form>
          ) : (
            <form onSubmit={handleLogin} className="space-y-6 animate-fade-in delay-1">
              <div>
                <label className="label" htmlFor="email">Email</label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  placeholder="you@company.com"
                  required
                />
              </div>

              <div>
                <label className="label" htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input"
                  placeholder="••••••••"
                  required
                />
              </div>

              <button
                type="submit"
                className="btn-primary w-full py-3 text-lg"
              >
                Sign In
              </button>
            </form>
          )}

          <div className="mt-8 pt-6 border-t border-gray-100">
            <p className="text-center text-sm text-gray-600">
              Don&apos;t have an account?{' '}
              <Link href="/auth/signup" className="text-amber-600 font-medium hover:text-amber-700 transition-colors">
                Create an account
              </Link>
            </p>
          </div>
        </div>

        {/* Demo credentials hint */}
        <div className="mt-6 text-center animate-fade-in delay-2">
          <details className="group cursor-pointer">
            <summary className="text-sm text-gray-500 hover:text-amber-600 transition-colors">
              Demo credentials
            </summary>
            <div className="mt-3 p-3 bg-gray-50 rounded-lg text-left text-xs text-gray-600 animate-fade-in">
              <p><strong>Email:</strong> demo@scout.io</p>
              <p><strong>Password:</strong> DemoPass123!</p>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
}
