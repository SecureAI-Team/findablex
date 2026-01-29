'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  Bot,
  FileText,
  FolderKanban,
  Home,
  LogOut,
  Menu,
  Settings,
  User,
  Users,
  X,
  CreditCard,
  Shield,
} from 'lucide-react';
import { api, logout } from '@/lib/api';
import { clsx } from 'clsx';

const navigation = [
  { name: '概览', href: '/dashboard', icon: Home },
  { name: '项目', href: '/projects', icon: FolderKanban },
  { name: '报告', href: '/reports', icon: FileText },
  { name: 'AI 研究', href: '/research', icon: Bot },
  { name: '团队', href: '/team', icon: Users },
  { name: '订阅', href: '/subscription', icon: CreditCard },
  { name: '设置', href: '/settings', icon: Settings },
];

const adminNavigation = [
  { name: '审计日志', href: '/admin/audit', icon: Shield },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    // Check both localStorage and sessionStorage (sessionStorage used when "remember me" is unchecked)
    const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    api.get('/auth/me')
      .then((res) => setUser(res.data))
      .catch(() => {
        // Clear tokens and redirect to login
        logout();
      });
  }, [router]);

  const handleLogout = () => {
    logout();
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="spinner w-8 h-8 text-primary-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Mobile sidebar */}
      <div
        className={clsx(
          'fixed inset-0 z-50 lg:hidden',
          sidebarOpen ? 'block' : 'hidden'
        )}
      >
        <div className="fixed inset-0 bg-black/50" onClick={() => setSidebarOpen(false)} />
        <div className="fixed inset-y-0 left-0 w-64 bg-slate-800 border-r border-slate-700">
          <div className="flex items-center justify-between h-16 px-4 border-b border-slate-700">
            <span className="font-display text-xl font-bold text-white">FindableX</span>
            <button onClick={() => setSidebarOpen(false)}>
              <X className="w-6 h-6 text-slate-400" />
            </button>
          </div>
          <nav className="p-4 space-y-1">
            {navigation.map((item) => {
              const isActive = item.href === '/dashboard' 
                ? pathname === '/dashboard'
                : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={clsx(
                    'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary-500/10 text-primary-400'
                      : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                  )}
                >
                  <item.icon className="w-5 h-5" />
                  {item.name}
                </Link>
              );
            })}
            
            {/* Admin navigation */}
            {user?.is_superuser && (
              <>
                <div className="pt-4 pb-2">
                  <span className="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    管理
                  </span>
                </div>
                {adminNavigation.map((item) => {
                  const isActive = pathname.startsWith(item.href);
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={clsx(
                        'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-primary-500/10 text-primary-400'
                          : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                      )}
                    >
                      <item.icon className="w-5 h-5" />
                      {item.name}
                    </Link>
                  );
                })}
              </>
            )}
          </nav>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-50 lg:block lg:w-64 lg:bg-slate-800 lg:border-r lg:border-slate-700">
        <div className="flex items-center h-16 px-6 border-b border-slate-700">
          <span className="font-display text-xl font-bold text-white">FindableX</span>
        </div>
        <nav className="p-4 space-y-1">
          {navigation.map((item) => {
            const isActive = item.href === '/dashboard' 
              ? pathname === '/dashboard'
              : pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-500/10 text-primary-400'
                    : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                )}
              >
                <item.icon className="w-5 h-5" />
                {item.name}
              </Link>
            );
          })}
          
          {/* Admin navigation */}
          {user?.is_superuser && (
            <>
              <div className="pt-4 pb-2">
                <span className="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  管理
                </span>
              </div>
              {adminNavigation.map((item) => {
                const isActive = pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={clsx(
                      'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary-500/10 text-primary-400'
                        : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                    )}
                  >
                    <item.icon className="w-5 h-5" />
                    {item.name}
                  </Link>
                );
              })}
            </>
          )}
        </nav>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <div className="sticky top-0 z-40 h-16 bg-slate-800/80 backdrop-blur-sm border-b border-slate-700">
          <div className="flex items-center justify-between h-full px-4 sm:px-6">
            <button
              className="lg:hidden text-slate-400 hover:text-white"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="w-6 h-6" />
            </button>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-primary-500/20 rounded-full flex items-center justify-center">
                  <User className="w-4 h-4 text-primary-400" />
                </div>
                <span className="text-sm text-slate-300 hidden sm:block">
                  {user.full_name || user.email}
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="p-4 sm:p-6 lg:p-8 min-h-[calc(100vh-4rem-3rem)]">
          {children}
        </main>

        {/* Footer with ICP */}
        <footer className="py-4 text-center border-t border-slate-800">
          <a
            href="https://beian.miit.gov.cn/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-500 hover:text-slate-400 text-xs transition-colors"
          >
            苏ICP备2026005817号
          </a>
        </footer>
      </div>
    </div>
  );
}
