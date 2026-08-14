import React from 'react';
import Sidebar from './Sidebar';

const dashboardItems = [
  { label: 'Overview', href: '/dashboard', icon: '📊' },
  { label: 'Chatbots', href: '/dashboard/chatbots', icon: '🤖' },
  { label: 'Knowledge Sources', href: '/dashboard/knowledge-sources', icon: '📚' },
  { label: 'Policies', href: '/dashboard/policies', icon: '🛡️' },
  { label: 'Analytics', href: '/dashboard/analytics', icon: '📈' },
  { label: 'Team', href: '/dashboard/team', icon: '👥' },
  { label: 'Billing', href: '/dashboard/billing', icon: '💳' },
  { label: 'Settings', href: '/dashboard/settings', icon: '⚙️' },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">Scout.io Dashboard</h1>
            </div>
            <div className="flex items-center space-x-4">
              <a href="/auth/login" className="text-sm text-gray-600 hover:text-gray-900">Login</a>
              <button
                onClick={() => { localStorage.clear(); window.location.href = '/auth/login'; }}
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>
      <div className="flex">
        <Sidebar items={dashboardItems} title="Organization" />
        <main className="flex-1 p-8">{children}</main>
      </div>
    </div>
  );
}