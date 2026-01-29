'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { RefreshCw, Home, AlertTriangle } from 'lucide-react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Application error:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        {/* Logo */}
        <Link href="/" className="inline-flex items-center gap-2 mb-8">
          <div className="w-10 h-10 bg-gradient-to-br from-primary-400 to-accent-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-xl">F</span>
          </div>
          <span className="font-display text-2xl font-bold text-white">
            FindableX
          </span>
        </Link>

        {/* Error Icon */}
        <div className="w-20 h-20 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
          <AlertTriangle className="w-10 h-10 text-red-400" />
        </div>

        {/* Message */}
        <h1 className="font-display text-2xl font-bold text-white mb-4">
          出了点问题
        </h1>
        <p className="text-slate-400 mb-8">
          抱歉，应用程序遇到了一个错误。我们的团队已收到通知，正在努力修复。
        </p>

        {/* Error Details (dev only) */}
        {process.env.NODE_ENV === 'development' && error.message && (
          <div className="mb-8 p-4 bg-slate-800/50 border border-slate-700 rounded-lg text-left">
            <p className="text-xs text-slate-500 mb-1">错误详情:</p>
            <p className="text-sm text-red-400 font-mono break-all">
              {error.message}
            </p>
            {error.digest && (
              <p className="text-xs text-slate-500 mt-2">
                Digest: {error.digest}
              </p>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={reset}
            className="w-full sm:w-auto bg-primary-500 hover:bg-primary-600 text-white px-6 py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2"
          >
            <RefreshCw className="w-5 h-5" />
            重试
          </button>
          <Link
            href="/"
            className="w-full sm:w-auto text-slate-300 hover:text-white px-6 py-3 rounded-lg font-medium border border-slate-600 hover:border-slate-500 transition-all flex items-center justify-center gap-2"
          >
            <Home className="w-5 h-5" />
            返回首页
          </Link>
        </div>

        {/* Help Text */}
        <p className="mt-8 text-slate-500 text-sm">
          如果问题持续存在，请{' '}
          <Link
            href="/contact"
            className="text-primary-400 hover:text-primary-300 transition-colors"
          >
            联系我们的支持团队
          </Link>
        </p>
      </div>
    </div>
  );
}
