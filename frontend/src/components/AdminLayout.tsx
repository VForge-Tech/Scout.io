import React from 'react';
import Sidebar from './Sidebar';

const adminItems = [
  { label: 'Organizations', href: '/admin/organizations', icon: '🏢' },
  { label: 'Platform Stats', href: '/admin', icon: '📊' },
  { label: 'Onboarding & Feedback', href: '/admin/onboarding', icon: '🧭' },
  { label: 'Audit Logs', href: '/admin/audit-logs', icon: '📋' },
  { label: 'System Health', href: '/admin/system-health', icon: '🔍' },
  { label: 'Settings', href: '/admin/settings', icon: '⚙️' },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">Scout.io Admin</h1>
            </div>
            <div className="flex items-center space-x-4">
              <a href="/dashboard" className="text-sm text-gray-600 hover:text-gray-900">Dashboard</a>
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
        <Sidebar items={adminItems} title="Admin Panel" />
        <main className="flex-1 p-8">{children}</main>
      </div>
    </div>
  );
}
