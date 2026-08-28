import React from 'react';
import { useRouter } from 'next/router';
import Sidebar from './Sidebar';

const dashboardItems = [
  { label: 'Overview', href: '/dashboard', icon: '📊' },
  { label: 'Chatbots', href: '/dashboard/chatbots', icon: '🤖' },
  { label: 'Knowledge Sources', href: '/dashboard/knowledge-sources', icon: '📚' },
  { label: 'Policies', href: '/dashboard/policies', icon: '🛡️' },
  { label: 'Playground', href: '/dashboard/playground', icon: '🧪' },
  { label: 'Analytics', href: '/dashboard/analytics', icon: '📈' },
  { label: 'Team', href: '/dashboard/team', icon: '👥' },
  { label: 'Billing', href: '/dashboard/billing', icon: '💳' },
  { label: 'Settings', href: '/dashboard/settings', icon: '⚙️' },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const isDashboard = router.pathname.startsWith('/dashboard');
  const isAdmin = router.pathname.startsWith('/admin');
  const isDeveloper = router.pathname.startsWith('/developer');
  const isAuth = router.pathname.startsWith('/auth');

  // Don't show layout for auth pages
  if (isAuth) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-amber-50">
      {/* Top navigation */}
      <nav className="bg-white/80 backdrop-blur-lg border-b border-gray-100 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center gap-4">
              <a href="/dashboard" className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center shadow-lg shadow-amber-500/25">
                  <span className="text-lg">🔍</span>
                </div>
                <span className="text-xl font-bold text-gray-900 hidden sm:block">Scout.io</span>
              </a>
              <div className="hidden md:block w-px h-6 bg-gray-200" />
              <nav className="hidden md:flex items-center gap-6">
                <a
                  href="/dashboard"
                  className={`text-sm font-medium transition-colors ${
                    isDashboard ? 'text-amber-600' : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Dashboard
                </a>
                <a
                  href="/developer"
                  className={`text-sm font-medium transition-colors ${
                    isDeveloper ? 'text-amber-600' : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Developer
                </a>
                {isDashboard && (
                  <a
                    href="/admin"
                    className={`text-sm font-medium transition-colors ${
                      isAdmin ? 'text-amber-600' : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Admin
                  </a>
                )}
              </nav>
            </div>
            <div className="flex items-center gap-4">
              <div className="hidden sm:block px-3 py-1.5 bg-amber-50 text-amber-700 text-xs font-medium rounded-full">
                Free Plan
              </div>
              <button
                onClick={() => { localStorage.clear(); window.location.href = '/auth/login'; }}
                className="text-sm text-gray-600 hover:text-gray-900 font-medium transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="flex">
        {isDashboard && <Sidebar items={dashboardItems} title="Dashboard" />}
        <main className="flex-1 min-w-0 lg:ml-0 p-4 sm:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}