'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  Loader2,
  Lock,
  AlertCircle,
  CheckCircle,
  AlertTriangle,
  BarChart3,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Metric {
  name: string;
  value: number;
  format: 'percent' | 'number';
  label: string;
}

interface Recommendation {
  priority: string;
  category: string;
  title: string;
  description: string;
  actions: string[];
}

interface PublicReport {
  title: string;
  report_type: string;
  content_html: string;
  content_json: {
    summary: {
      health_score: number;
      status: string;
      status_text: string;
      status_color: string;
    };
    metrics: Record<string, Metric>;
    recommendations: Recommendation[];
    generated_at: string;
  };
  generated_at: string;
}

export default function SharePage() {
  const params = useParams();
  const token = params.token as string;

  const [report, setReport] = useState<PublicReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [needsPassword, setNeedsPassword] = useState(false);
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchReport = async (pwd?: string) => {
    setIsLoading(true);
    setError('');

    try {
      const res = await api.get(`/reports/share/${token}`, {
        params: pwd ? { password: pwd } : undefined,
      });
      setReport(res.data);
      setNeedsPassword(false);
    } catch (err: any) {
      if (err.response?.status === 401) {
        setNeedsPassword(true);
      } else if (err.response?.status === 403) {
        setError('访问被拒绝，请检查密码是否正确');
      } else if (err.response?.status === 404) {
        setError('报告不存在或链接已失效');
      } else {
        setError('加载报告失败');
      }
    } finally {
      setIsLoading(false);
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, [token]);

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) return;
    setIsSubmitting(true);
    fetchReport(password);
  };

  const getHealthScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getHealthScoreBg = (score: number) => {
    if (score >= 80) return 'from-green-500/20 to-green-500/5';
    if (score >= 60) return 'from-yellow-500/20 to-yellow-500/5';
    return 'from-red-500/20 to-red-500/5';
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'border-red-500/50 bg-red-500/5';
      case 'medium':
        return 'border-yellow-500/50 bg-yellow-500/5';
      default:
        return 'border-green-500/50 bg-green-500/5';
    }
  };

  const getPriorityLabel = (priority: string) => {
    switch (priority) {
      case 'high':
        return { text: '高优先级', color: 'text-red-400' };
      case 'medium':
        return { text: '中优先级', color: 'text-yellow-400' };
      default:
        return { text: '低优先级', color: 'text-green-400' };
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  // Password required
  if (needsPassword) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 px-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-primary-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Lock className="w-8 h-8 text-primary-400" />
            </div>
            <h1 className="font-display text-2xl font-bold text-white mb-2">
              输入密码
            </h1>
            <p className="text-slate-400">此报告需要密码才能查看</p>
          </div>

          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            )}

            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="输入访问密码"
              className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              autoFocus
            />

            <button
              type="submit"
              disabled={isSubmitting || !password.trim()}
              className="w-full bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/50 text-white py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  验证中...
                </>
              ) : (
                '查看报告'
              )}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 px-4">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-red-400" />
          </div>
          <h1 className="font-display text-2xl font-bold text-white mb-2">
            无法加载报告
          </h1>
          <p className="text-slate-400 mb-6">{error}</p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-6 py-2.5 rounded-lg font-medium transition-all"
          >
            返回首页
          </Link>
        </div>
      </div>
    );
  }

  // Report view
  if (!report) return null;

  const { summary, metrics, recommendations } = report.content_json;

  return (
    <div className="min-h-screen bg-slate-900 relative">
      {/* Watermark */}
      <div className="fixed inset-0 pointer-events-none z-50 overflow-hidden opacity-[0.03]">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="transform -rotate-45 text-white text-[200px] font-bold whitespace-nowrap select-none">
            FindableX 只读分享
          </div>
        </div>
      </div>
      
      {/* Read-only banner */}
      <div className="bg-amber-500/10 border-b border-amber-500/20">
        <div className="max-w-5xl mx-auto px-4 py-2 flex items-center justify-center gap-2 text-sm text-amber-400">
          <Lock className="w-4 h-4" />
          <span>只读分享 · 此报告由 FindableX 用户分享</span>
        </div>
      </div>
      
      {/* Header */}
      <header className="border-b border-slate-800">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-primary-400 to-accent-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">F</span>
              </div>
              <span className="font-display text-xl font-bold text-white">
                FindableX
              </span>
            </Link>
            <span className="text-slate-400 text-sm">共享报告</span>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Title */}
        <div>
          <h1 className="font-display text-2xl lg:text-3xl font-bold text-white">
            {report.title}
          </h1>
          <p className="mt-2 text-slate-400">
            生成于 {formatDate(report.generated_at)}
          </p>
        </div>

        {/* Health Score Card */}
        <div
          className={cn(
            'bg-gradient-to-br rounded-2xl p-8 border border-slate-700/50',
            getHealthScoreBg(summary.health_score)
          )}
        >
          <div className="flex flex-col md:flex-row md:items-center gap-6">
            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className={cn('text-6xl font-bold', getHealthScoreColor(summary.health_score))}>
                  {summary.health_score}
                </div>
                <div className="text-slate-400 text-sm mt-1">健康度评分</div>
              </div>
              <div className="w-px h-16 bg-slate-700/50 hidden md:block" />
              <div>
                <div className="flex items-center gap-2 mb-2">
                  {summary.health_score >= 60 ? (
                    <CheckCircle className="w-5 h-5 text-green-400" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-yellow-400" />
                  )}
                  <span className={cn('font-medium', getHealthScoreColor(summary.health_score))}>
                    {summary.status_text}
                  </span>
                </div>
                <p className="text-slate-400 text-sm max-w-md">
                  {summary.health_score >= 80
                    ? 'GEO 表现出色，继续保持！'
                    : summary.health_score >= 60
                    ? 'GEO 表现良好，仍有提升空间。'
                    : 'GEO 表现需要改进，请查看下方建议。'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.values(metrics).map((metric) => (
            <div
              key={metric.name}
              className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-5"
            >
              <div className="text-slate-400 text-sm mb-2">{metric.label}</div>
              <div className="text-2xl font-bold text-white">
                {metric.format === 'percent'
                  ? `${(metric.value * 100).toFixed(0)}%`
                  : metric.value.toFixed(1)}
              </div>
            </div>
          ))}
        </div>

        {/* Recommendations */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50">
          <div className="p-6 border-b border-slate-700/50">
            <h2 className="font-display text-lg font-semibold text-white">优化建议</h2>
          </div>
          <div className="divide-y divide-slate-700/50">
            {recommendations.map((rec, index) => {
              const priority = getPriorityLabel(rec.priority);
              return (
                <div key={index} className={cn('p-6', getPriorityColor(rec.priority))}>
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <h3 className="font-medium text-white">{rec.title}</h3>
                    <span className={cn('text-xs font-medium', priority.color)}>
                      {priority.text}
                    </span>
                  </div>
                  <p className="text-slate-400 text-sm mb-4">{rec.description}</p>
                  <div className="space-y-2">
                    {rec.actions.map((action, actionIndex) => (
                      <div key={actionIndex} className="flex items-center gap-2 text-sm text-slate-300">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary-500" />
                        {action}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* CTA */}
        <div className="text-center py-8 border-t border-slate-800">
          <p className="text-slate-400 mb-4">想要监测您的品牌 GEO 可见性？</p>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-6 py-3 rounded-lg font-medium transition-all"
          >
            免费开始使用 FindableX
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-6">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-slate-500 text-sm">
          Powered by FindableX · GEO 体检平台
        </div>
      </footer>
    </div>
  );
}
