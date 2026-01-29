import Link from 'next/link';
import { Home, ArrowLeft, Search } from 'lucide-react';

export default function NotFound() {
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

        {/* 404 Illustration */}
        <div className="mb-8">
          <div className="text-8xl font-display font-bold bg-gradient-to-r from-primary-400 to-accent-400 bg-clip-text text-transparent">
            404
          </div>
          <div className="mt-2 text-slate-400 text-lg">页面未找到</div>
        </div>

        {/* Message */}
        <h1 className="font-display text-2xl font-bold text-white mb-4">
          抱歉，我们找不到这个页面
        </h1>
        <p className="text-slate-400 mb-8">
          您访问的页面可能已被移动、删除或从未存在。请检查 URL 是否正确，或返回首页。
        </p>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/"
            className="w-full sm:w-auto bg-primary-500 hover:bg-primary-600 text-white px-6 py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2"
          >
            <Home className="w-5 h-5" />
            返回首页
          </Link>
          <Link
            href="/dashboard"
            className="w-full sm:w-auto text-slate-300 hover:text-white px-6 py-3 rounded-lg font-medium border border-slate-600 hover:border-slate-500 transition-all flex items-center justify-center gap-2"
          >
            <ArrowLeft className="w-5 h-5" />
            前往控制台
          </Link>
        </div>

        {/* Help Text */}
        <p className="mt-8 text-slate-500 text-sm">
          需要帮助？{' '}
          <Link
            href="/contact"
            className="text-primary-400 hover:text-primary-300 transition-colors"
          >
            联系我们
          </Link>
        </p>
      </div>
    </div>
  );
}
