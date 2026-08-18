import React from 'react';
import { useRouter } from 'next/router';

interface SidebarItem {
  label: string;
  href: string;
  icon?: string;
}

interface SidebarProps {
  items: SidebarItem[];
  title: string;
}

export default function Sidebar({ items, title }: SidebarProps) {
  const router = useRouter();
  return (
    <aside className="w-64 bg-white shadow-sm border-r min-h-screen">
      <div className="p-4">
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      </div>
      <nav className="space-y-1 px-2">
        {items.map((item) => {
          const isActive =
            router.pathname === item.href ||
            router.pathname.startsWith(`${item.href}/`);
          return (
            <a
              key={item.href}
              href={item.href}
              className={`block px-3 py-2 rounded-md text-sm font-medium ${
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              {item.icon && <span className="mr-2">{item.icon}</span>}
              {item.label}
            </a>
          );
        })}
      </nav>
    </aside>
  );
}
