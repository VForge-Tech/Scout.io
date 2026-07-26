import React from 'react';
import Sidebar from './Sidebar';

const devItems = [
  { label: 'API Keys', href: '/developer/api-keys', icon: '🔑' },
  { label: 'API Docs', href: '/developer/docs', icon: '📖' },
  { label: 'Widget Integration', href: '/developer/widget', icon: '💬' },
];

export default function DeveloperLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">Scout.io Developer</h1>
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
        <Sidebar items={devItems} title="Developer Portal" />
        <main className="flex-1 p-8">{children}</main>
      </div>
    </div>
  );
}
