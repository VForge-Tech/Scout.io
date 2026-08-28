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
    <aside className="w-64 bg-white border-r border-gray-100 min-h-screen hidden lg:block">
      <div className="p-4 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <span className="text-amber-600">●</span>
          {title}
        </h2>
      </div>
      <nav className="p-2 space-y-1">
        {items.map((item) => {
          const isActive =
            router.pathname === item.href ||
            router.pathname.startsWith(`${item.href}/`);
          return (
            <a
              key={item.href}
              href={item.href}
              className={`sidebar-link ${isActive ? 'sidebar-link-active' : 'sidebar-link-inactive'}`}
            >
              {item.icon && <span className="text-lg">{item.icon}</span>}
              <span className="flex-1 truncate">{item.label}</span>
              {isActive && <span className="w-1.5 h-1.5 bg-amber-500 rounded-full" />}
            </a>
          );
        })}
      </nav>
    </aside>
  );
}
