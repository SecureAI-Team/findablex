'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Loader2,
  Download,
  Share2,
  AlertTriangle,
  CheckCircle,
  ChevronRight,
  Copy,
  Check,
  Clock,
  XCircle,
  RefreshCw,
  Crown,
  RotateCcw,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { analytics } from '@/lib/analytics';

interface Metric {
  score: number;
  label: string;
  description: string;
}

interface Recommendation {
  priority: string;
  category: string;
  title: string;
  description: string;
  actions: string[];
}

interface HealthReport {
  report_type: string;
  title: string;
  project_id: string;
  project_name: string;
  run_id: string;
  generated_at: string;
  summary: {
    health_score: number;
    status: string;
    status_text: string;
  };
  metrics: Record<string, Metric>;
  recommendations: Recommendation[];
  comparison: {
    industry_avg: number;
    vs_industry: number;
    percentile: number;
  };
}

interface Run {
  id: string;
  project_id: string;
  health_score: number | null;
  status: string;
  run_type: string;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export default function ReportDetailPage() {
  const params = useParams();
  const router = useRouter();
  const reportId = params.id as string;

  const [run, setRun] = useState<Run | null>(null);
  const [report, setReport] = useState<HealthReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareUrl, setShareUrl] = useState('');
  const [copied, setCopied] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  const fetchData = async () => {
    try {
      setIsLoading(true);
      // Get run data first
      const runRes = await api.get(`/runs/${reportId}`);
      setRun(runRes.data);

      // Only fetch report if run is completed
      if (runRes.data.status === 'completed') {
        try {
          const reportRes = await api.get(`/reports/health/${reportId}`);
          setReport(reportRes.data);
          
          // Track report view
          analytics.trackReportViewed(reportId, 'health');
        } catch (e) {
          console.error('Failed to fetch health report:', e);
        }
      }
    } catch (error) {
      console.error('Failed to fetch report:', error);
      router.push('/reports');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [reportId]);

  // Auto-refresh for pending/processing runs
  useEffect(() => {
    if (run && (run.status === 'pending' || run.status === 'processing')) {
      const interval = setInterval(fetchData, 5000);
      return () => clearInterval(interval);
    }
  }, [run?.status]);

  const handleShare = async () => {
    try {
      const res = await api.post(`/reports/${reportId}/share`, {
        expires_in_days: 7,
      });
      setShareUrl(res.data.share_url);
      setShowShareModal(true);
    } catch (error) {
      console.error('Failed to create share link:', error);
      // Fallback to current URL
      setShareUrl(window.location.href);
      setShowShareModal(true);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!run) {
    return null;
  }

  // Show processing state for pending/processing runs
  if (run.status === 'pending' || run.status === 'processing') {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div>
          <Link
            href="/reports"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            返回报告列表
          </Link>
          <h1 className="font-display text-2xl font-bold text-white">GEO 体检报告</h1>
          <p className="mt-1 text-slate-400">创建于 {formatDate(run.created_at)}</p>
        </div>

        {/* Processing Card */}
        <div className="bg-gradient-to-br from-primary-500/20 to-primary-600/10 rounded-2xl p-12 border border-primary-500/30 text-center">
          <div className="w-20 h-20 bg-primary-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            {run.status === 'pending' ? (
              <Clock className="w-10 h-10 text-primary-400" />
            ) : (
              <Loader2 className="w-10 h-10 text-primary-400 animate-spin" />
            )}
          </div>
          <h2 className="font-display text-2xl font-bold text-white mb-3">
            {run.status === 'pending' ? '等待处理中...' : '正在分析数据...'}
          </h2>
          <p className="text-slate-300 max-w-md mx-auto mb-6">
            {run.status === 'pending'
              ? '您的体检请求已加入队列，即将开始处理。'
              : '我们正在分析您的数据，这可能需要几分钟时间。页面会自动刷新。'}
          </p>
          <div className="flex items-center justify-center gap-2 text-sm text-slate-400">
            <RefreshCw className="w-4 h-4 animate-spin" />
            <span>自动刷新中...</span>
          </div>
        </div>

        {/* Link to Project */}
        <div className="text-center">
          <Link
            href={`/projects/${run.project_id}`}
            className="inline-flex items-center gap-2 text-primary-400 hover:text-primary-300 transition-colors"
          >
            查看项目
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    );
  }

  // Show error state for failed runs
  if (run.status === 'failed') {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div>
          <Link
            href="/reports"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            返回报告列表
          </Link>
          <h1 className="font-display text-2xl font-bold text-white">GEO 体检报告</h1>
          <p className="mt-1 text-slate-400">创建于 {formatDate(run.created_at)}</p>
        </div>

        {/* Error Card */}
        <div className="bg-gradient-to-br from-red-500/20 to-red-600/10 rounded-2xl p-12 border border-red-500/30 text-center">
          <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <XCircle className="w-10 h-10 text-red-400" />
          </div>
          <h2 className="font-display text-2xl font-bold text-white mb-3">分析失败</h2>
          <p className="text-slate-300 max-w-md mx-auto mb-2">
            抱歉，处理过程中发生了错误。请重试或联系支持。
          </p>
          {run.error_message && (
            <p className="text-red-400 text-sm mb-6">错误信息：{run.error_message}</p>
          )}
          <Link
            href={`/projects/${run.project_id}`}
            className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-6 py-3 rounded-lg font-medium transition-all"
          >
            返回项目重试
          </Link>
        </div>
      </div>
    );
  }

  // Show completed report
  if (!report) {
    // Fallback if report API fails
    const healthScore = run?.health_score || 0;
    return (
      <div className="space-y-6">
        <div>
          <Link
            href="/reports"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            返回报告列表
          </Link>
          <h1 className="font-display text-2xl font-bold text-white">GEO 体检报告</h1>
          <p className="mt-1 text-slate-400">健康度评分: {healthScore}</p>
        </div>
        <div className="text-center py-16 bg-slate-800/30 rounded-xl border border-slate-700/50">
          <p className="text-slate-400">报告生成中，请稍后刷新</p>
        </div>
      </div>
    );
  }

  const { summary, metrics, recommendations, comparison } = report;

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <Link
            href="/reports"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            返回报告列表
          </Link>
          <h1 className="font-display text-2xl font-bold text-white">{report.title}</h1>
          <p className="mt-1 text-slate-400">
            生成于 {formatDate(report.generated_at)} · {report.project_name}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* 复测按钮 */}
          <Link
            href={`/projects/${report.project_id}/import`}
            className="inline-flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-4 py-2.5 rounded-lg font-medium transition-all"
          >
            <RotateCcw className="w-5 h-5" />
            复测
          </Link>
          <button
            onClick={handleShare}
            className="inline-flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-4 py-2.5 rounded-lg font-medium transition-all"
          >
            <Share2 className="w-5 h-5" />
            分享
          </button>
          <div className="relative group">
            <button className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2.5 rounded-lg font-medium transition-all">
              <Download className="w-5 h-5" />
              导出
            </button>
            <div className="absolute right-0 mt-2 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
              <button
                onClick={async () => {
                  try {
                    const res = await api.get(`/reports/health/${reportId}/export`, {
                      params: { format: 'json' },
                      responseType: 'blob',
                    });
                    const blob = new Blob([res.data]);
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `health_report_${reportId}.json`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                  } catch (e) {
                    console.error('Export failed:', e);
                  }
                }}
                className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 hover:text-white rounded-t-lg"
              >
                导出 JSON 数据
              </button>
              <button
                onClick={async () => {
                  try {
                    const res = await api.get(`/reports/health/${reportId}/export`, {
                      params: { format: 'html' },
                      responseType: 'blob',
                    });
                    const blob = new Blob([res.data]);
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `health_report_${reportId}.html`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                  } catch (e) {
                    console.error('Export failed:', e);
                  }
                }}
                className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 hover:text-white"
              >
                下载 HTML 报告
              </button>
              <button
                onClick={async () => {
                  try {
                    const res = await api.get(`/reports/health/${reportId}/export`, {
                      params: { format: 'html' },
                      responseType: 'text',
                    });
                    const printWindow = window.open('', '_blank');
                    if (printWindow) {
                      printWindow.document.write(res.data);
                      printWindow.document.close();
                    }
                  } catch (e) {
                    console.error('Print failed:', e);
                  }
                }}
                className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 hover:text-white rounded-b-lg"
              >
                打印 / 导出 PDF
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Health Score Card */}
      <div
        className={cn(
          'bg-gradient-to-br rounded-2xl p-8 border border-slate-700/50',
          getHealthScoreBg(summary.health_score)
        )}
      >
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-8">
          <div className="flex items-center gap-8">
            <div className="text-center">
              <div className={cn('text-7xl font-bold', getHealthScoreColor(summary.health_score))}>
                {summary.health_score}
              </div>
              <div className="text-slate-400 text-sm mt-1">健康度评分</div>
            </div>
            <div className="w-px h-20 bg-slate-700/50 hidden lg:block" />
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                {summary.health_score >= 60 ? (
                  <CheckCircle className="w-5 h-5 text-green-400" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-yellow-400" />
                )}
                <span className={cn('font-medium text-lg', getHealthScoreColor(summary.health_score))}>
                  {summary.status_text}
                </span>
              </div>
              <p className="text-slate-400 text-sm max-w-md">
                {summary.health_score >= 80
                  ? '您的 GEO 表现出色，继续保持！'
                  : summary.health_score >= 60
                  ? '您的 GEO 表现良好，仍有提升空间。'
                  : '您的 GEO 表现需要改进，请查看下方建议。'}
              </p>
            </div>
          </div>
          
          {/* Industry Comparison */}
          {comparison && (
            <div className="flex gap-4 lg:gap-6 flex-wrap">
              <div className="text-center px-4">
                <div className="text-2xl font-bold text-white">{comparison.industry_avg}</div>
                <div className="text-xs text-slate-500">行业平均</div>
              </div>
              <div className="text-center px-4 border-x border-slate-700/50">
                <div className={cn(
                  'text-2xl font-bold',
                  comparison.vs_industry >= 0 ? 'text-green-400' : 'text-red-400'
                )}>
                  {comparison.vs_industry > 0 ? '+' : ''}{comparison.vs_industry}
                </div>
                <div className="text-xs text-slate-500">vs 行业</div>
              </div>
              <div className="text-center px-4">
                <div className="text-2xl font-bold text-primary-400">Top {100 - comparison.percentile}%</div>
                <div className="text-xs text-slate-500">百分位</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Object.entries(metrics || {}).map(([key, metric]) => (
          <div
            key={key}
            className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-5"
          >
            <div className="text-slate-400 text-sm mb-2">{metric.label}</div>
            <div className={cn(
              'text-3xl font-bold',
              metric.score >= 70 ? 'text-green-400' : metric.score >= 50 ? 'text-yellow-400' : 'text-red-400'
            )}>
              {metric.score}
            </div>
            <p className="text-xs text-slate-500 mt-2">{metric.description}</p>
          </div>
        ))}
      </div>

      {/* Recommendations */}
      {recommendations && recommendations.length > 0 && (
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
                    <h3 className="font-medium text-white text-lg">{rec.title}</h3>
                    <span className={cn('text-xs font-medium px-2 py-1 rounded', priority.color, 'bg-slate-800/50')}>
                      {priority.text}
                    </span>
                  </div>
                  <p className="text-slate-400 text-sm mb-4">{rec.description}</p>
                  <div className="space-y-2">
                    {rec.actions.map((action, actionIndex) => (
                      <div key={actionIndex} className="flex items-start gap-2 text-sm text-slate-300">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary-500 mt-2 flex-shrink-0" />
                        {action}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Link to Project */}
      {/* 升级提示 */}
      <div className="bg-gradient-to-r from-amber-500/10 via-orange-500/10 to-amber-500/10 rounded-xl border border-amber-500/20 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center flex-shrink-0">
              <Crown className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-white mb-1">
                解锁更多问题条数和复测对比
              </h3>
              <p className="text-slate-400 text-sm">
                升级到 Pro 版可追踪 100 条关键问题、查看月度复测对比、获取漂移预警通知
              </p>
            </div>
          </div>
          <Link
            href="/subscription"
            className="inline-flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-white px-5 py-2.5 rounded-lg font-medium transition-all whitespace-nowrap"
            onClick={() => analytics.trackUpgradeClicked('report_page')}
          >
            升级方案
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {run && (
        <div className="text-center">
          <Link
            href={`/projects/${run.project_id}`}
            className="inline-flex items-center gap-2 text-primary-400 hover:text-primary-300 transition-colors"
          >
            查看项目详情
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      )}

      {/* Share Modal */}
      {showShareModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setShowShareModal(false)}
          />
          <div className="relative bg-slate-800 rounded-2xl border border-slate-700 p-6 w-full max-w-md">
            <h3 className="font-display text-lg font-semibold text-white mb-4">
              分享报告
            </h3>
            <p className="text-slate-400 text-sm mb-4">
              复制以下链接分享报告，链接有效期 7 天。
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                readOnly
                value={shareUrl}
                className="flex-1 px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm"
              />
              <button
                onClick={handleCopy}
                className="px-4 py-2.5 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-all flex items-center gap-2"
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4" />
                    已复制
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    复制
                  </>
                )}
              </button>
            </div>
            <button
              onClick={() => setShowShareModal(false)}
              className="mt-4 w-full px-4 py-2 text-slate-400 hover:text-white transition-colors text-sm"
            >
              关闭
            </button>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {showToast && (
        <div className="fixed bottom-4 right-4 z-50 bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 shadow-lg flex items-center gap-3 animate-in slide-in-from-bottom-5">
          <Clock className="w-5 h-5 text-primary-400" />
          <span className="text-white">{toastMessage}</span>
        </div>
      )}
    </div>
  );
}
