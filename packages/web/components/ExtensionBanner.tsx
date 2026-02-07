'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { X, Puzzle, Download, ArrowRight } from 'lucide-react';

const DISMISS_KEY = 'findablex_ext_banner_dismissed';
const DISMISS_DURATION_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

/**
 * Dismissible banner prompting users to install the browser extension.
 * Shows in the dashboard for logged-in users.
 * Re-appears after 7 days if dismissed.
 */
export default function ExtensionBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Check if banner was recently dismissed
    const dismissedAt = localStorage.getItem(DISMISS_KEY);
    if (dismissedAt) {
      const elapsed = Date.now() - parseInt(dismissedAt, 10);
      if (elapsed < DISMISS_DURATION_MS) {
        return; // Still dismissed
      }
    }
    // Small delay so it doesn't flash on page load
    const timer = setTimeout(() => setVisible(true), 1000);
    return () => clearTimeout(timer);
  }, []);

  const dismiss = () => {
    setVisible(false);
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
  };

  if (!visible) return null;

  return (
    <div className="mb-6 animate-in fade-in slide-in-from-top-2 duration-500">
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-primary-600/20 via-slate-800 to-accent-600/20 border border-primary-500/20 p-4 sm:p-5">
        {/* Background glow */}
        <div className="absolute top-0 right-0 w-40 h-40 bg-primary-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />

        <div className="relative flex flex-col sm:flex-row items-start sm:items-center gap-4">
          {/* Icon */}
          <div className="flex-shrink-0 w-10 h-10 bg-primary-500/20 rounded-xl flex items-center justify-center">
            <Puzzle className="w-5 h-5 text-primary-400" />
          </div>

          {/* Text */}
          <div className="flex-1 min-w-0">
            <p className="text-white font-medium text-sm sm:text-base">
              安装浏览器插件，自动采集 AI 搜索数据
            </p>
            <p className="text-slate-400 text-xs sm:text-sm mt-0.5">
              插件在后台自动从 9 大 AI 引擎采集数据，无需手动操作
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <Link
              href="/extension"
              className="inline-flex items-center gap-1.5 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-all shadow-sm"
            >
              <Download className="w-4 h-4" />
              <span className="hidden sm:inline">下载插件</span>
              <span className="sm:hidden">下载</span>
            </Link>
            <button
              onClick={dismiss}
              className="text-slate-500 hover:text-slate-300 p-1.5 rounded-lg hover:bg-slate-700/50 transition-colors"
              aria-label="关闭"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
