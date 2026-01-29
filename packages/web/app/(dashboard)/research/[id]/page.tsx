'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Bot,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ExternalLink,
  FileText,
  BarChart3,
  Globe,
  Loader2,
  StopCircle,
  Copy,
  Check,
  Download,
} from 'lucide-react';
import { api } from '@/lib/api';
import { analytics, EVENTS } from '@/lib/analytics';
import { clsx } from 'clsx';

interface CrawlTask {
  id: string;
  project_id: string;
  engine: string;
  status: string;
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  created_at: string;
}

interface CrawlResult {
  query: string;
  response_text: string;
  citations: Citation[];
  error?: string;
  crawled_at: string;
}

interface Citation {
  position: number;
  url: string;
  title: string;
  domain?: string;
  source?: string;
}

const statusConfig: Record<string, { icon: typeof Clock; color: string; bgColor: string; label: string }> = {
  pending: { icon: Clock, color: 'text-yellow-400', bgColor: 'bg-yellow-500/10', label: '等待中' },
  running: { icon: RefreshCw, color: 'text-blue-400', bgColor: 'bg-blue-500/10', label: '运行中' },
  completed: { icon: CheckCircle2, color: 'text-green-400', bgColor: 'bg-green-500/10', label: '已完成' },
  failed: { icon: XCircle, color: 'text-red-400', bgColor: 'bg-red-500/10', label: '失败' },
  cancelled: { icon: AlertCircle, color: 'text-slate-400', bgColor: 'bg-slate-500/10', label: '已取消' },
};

const engineIcons: Record<string, string> = {
  deepseek: '🔮',
  kimi: '🌙',
  doubao: '🫘',
  chatglm: '🧠',
  chatgpt: '🤖',
  qwen: '☁️',
  perplexity: '🔍',
  google_sge: '🌐',
  bing_copilot: '💠',
};

const engineNames: Record<string, string> = {
  deepseek: 'DeepSeek',
  kimi: 'Kimi',
  doubao: '豆包',
  chatglm: '智谱清言',
  chatgpt: 'ChatGPT',
  qwen: '通义千问',
  perplexity: 'Perplexity',
  google_sge: 'Google SGE',
  bing_copilot: 'Bing Copilot',
};

export default function CrawlTaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.id as string;
  
  const [task, setTask] = useState<CrawlTask | null>(null);
  const [results, setResults] = useState<CrawlResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [selectedResult, setSelectedResult] = useState<number>(0);

  useEffect(() => {
    fetchTask();
    // Poll for updates if task is running
    const interval = setInterval(() => {
      if (task?.status === 'running' || task?.status === 'pending') {
        fetchTask();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [taskId, task?.status]);

  const fetchTask = async () => {
    try {
      const res = await api.get(`/crawler/tasks/${taskId}`);
      const prevStatus = task?.status;
      setTask(res.data);
      
      // Fetch results if completed
      if (res.data.status === 'completed') {
        // Track first crawl completed when task transitions to completed
        if (prevStatus && prevStatus !== 'completed') {
          analytics.track(EVENTS.FIRST_CRAWL_COMPLETED, {
            properties: {
              task_id: taskId,
              engine: res.data.engine,
              total_queries: res.data.total_queries,
              successful_queries: res.data.successful_queries,
            },
          });
        }
        
        try {
          const resultsRes = await api.get(`/crawler/tasks/${taskId}/results`);
          setResults(resultsRes.data || []);
        } catch {
          // Results endpoint might not exist yet, use mock data
          setResults(getMockResults(res.data));
        }
      }
      setError(null);
    } catch (err: any) {
      setError('加载任务详情失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!task || !confirm('确定要取消此任务吗？')) return;
    
    try {
      setCancelling(true);
      await api.post(`/crawler/tasks/${taskId}/cancel`);
      await fetchTask();
    } catch (err: any) {
      setError(err.response?.data?.detail || '取消任务失败');
    } finally {
      setCancelling(false);
    }
  };

  const handleRetry = async () => {
    if (!task) return;
    
    try {
      setRetrying(true);
      await api.post(`/crawler/tasks/${taskId}/retry`);
      await fetchTask();
    } catch (err: any) {
      setError(err.response?.data?.detail || '重试任务失败');
    } finally {
      setRetrying(false);
    }
  };

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      setExporting(true);
      const response = await api.get(`/crawler/tasks/${taskId}/results/export`, {
        params: { format },
        responseType: 'blob',
      });
      
      // Create download link
      const blob = new Blob([response.data], {
        type: format === 'csv' ? 'text/csv' : 'application/json',
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `crawl_results_${taskId}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      setError(err.response?.data?.detail || '导出失败');
    } finally {
      setExporting(false);
    }
  };

  const handleCopy = async (text: string, index: number) => {
    await navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  // Mock results for demo (when results API doesn't exist)
  const getMockResults = (taskData: CrawlTask): CrawlResult[] => {
    if (taskData.successful_queries === 0) return [];
    return Array.from({ length: taskData.successful_queries }, (_, i) => ({
      query: `示例查询 ${i + 1}`,
      response_text: `这是来自 ${engineNames[taskData.engine]} 的模拟响应内容。在实际使用中，这里会显示 AI 引擎返回的完整回答，包括品牌提及和引用信息。\n\n根据最新数据，这个查询涉及多个品牌和产品...`,
      citations: [
        { position: 1, url: 'https://example.com/article1', title: '示例文章 1', domain: 'example.com' },
        { position: 2, url: 'https://brand.com/product', title: '品牌产品页', domain: 'brand.com' },
        { position: 3, url: 'https://review.com/comparison', title: '产品对比评测', domain: 'review.com' },
      ],
      crawled_at: new Date().toISOString(),
    }));
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4">
        <AlertCircle className="w-12 h-12 text-red-400" />
        <p className="text-slate-300">{error || '任务不存在'}</p>
        <Link href="/research" className="text-primary-400 hover:text-primary-300">
          返回任务列表
        </Link>
      </div>
    );
  }

  const status = statusConfig[task.status] || statusConfig.pending;
  const StatusIcon = status.icon;
  const progress =
    task.total_queries > 0
      ? Math.round(((task.successful_queries + task.failed_queries) / task.total_queries) * 100)
      : 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="flex items-start gap-4">
          <Link
            href="/research"
            className="p-2 rounded-lg hover:bg-slate-700/50 transition-colors mt-1"
          >
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <span className="text-3xl">{engineIcons[task.engine] || '🤖'}</span>
              <div>
                <h1 className="font-display text-2xl font-bold text-white">
                  {engineNames[task.engine] || task.engine} 爬虫任务
                </h1>
                <p className="text-slate-400 text-sm mt-1">
                  创建于 {formatDate(task.created_at)}
                </p>
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {(task.status === 'pending' || task.status === 'failed') && (
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {retrying ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              {task.status === 'pending' ? '立即执行' : '重新执行'}
            </button>
          )}
          {(task.status === 'pending' || task.status === 'running') && (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="inline-flex items-center gap-2 px-4 py-2 text-red-400 hover:text-red-300 border border-red-500/30 hover:border-red-500/50 rounded-lg transition-colors"
            >
              {cancelling ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <StopCircle className="w-4 h-4" />
              )}
              取消任务
            </button>
          )}
          <button
            onClick={fetchTask}
            className="inline-flex items-center gap-2 px-4 py-2 text-slate-400 hover:text-white border border-slate-700 hover:border-slate-600 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
          {task.status === 'completed' && results.length > 0 && (
            <div className="relative group">
              <button
                disabled={exporting}
                className="inline-flex items-center gap-2 px-4 py-2 text-slate-400 hover:text-white border border-slate-700 hover:border-slate-600 rounded-lg transition-colors disabled:opacity-50"
              >
                {exporting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                导出
              </button>
              <div className="absolute right-0 top-full mt-1 w-32 bg-slate-800 border border-slate-700 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                <button
                  onClick={() => handleExport('json')}
                  className="w-full px-4 py-2 text-sm text-left text-slate-300 hover:bg-slate-700 rounded-t-lg"
                >
                  导出 JSON
                </button>
                <button
                  onClick={() => handleExport('csv')}
                  className="w-full px-4 py-2 text-sm text-left text-slate-300 hover:bg-slate-700 rounded-b-lg"
                >
                  导出 CSV
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Status Card */}
      <div className={clsx('rounded-xl border p-6', status.bgColor, 'border-slate-700/50')}>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className={clsx('p-3 rounded-xl', status.bgColor)}>
              <StatusIcon
                className={clsx('w-8 h-8', status.color, task.status === 'running' && 'animate-spin')}
              />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className={clsx('text-lg font-semibold', status.color)}>{status.label}</span>
              </div>
              <p className="text-slate-400 text-sm mt-1">
                {task.status === 'running' && '正在爬取数据，请稍候...'}
                {task.status === 'pending' && '任务已加入队列，等待执行...'}
                {task.status === 'completed' && '任务已完成，可以查看结果'}
                {task.status === 'failed' && '任务执行失败，请检查配置后重试'}
                {task.status === 'cancelled' && '任务已被取消'}
              </p>
            </div>
          </div>
          
          {/* Progress */}
          <div className="sm:w-64">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-slate-400">进度</span>
              <span className="text-white font-medium">{progress}%</span>
            </div>
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={clsx(
                  'h-full rounded-full transition-all duration-500',
                  task.status === 'completed'
                    ? 'bg-green-500'
                    : task.status === 'failed'
                    ? 'bg-red-500'
                    : 'bg-primary-500'
                )}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            <FileText className="w-4 h-4" />
            <span className="text-sm">总查询数</span>
          </div>
          <p className="text-2xl font-bold text-white">{task.total_queries}</p>
        </div>
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
          <div className="flex items-center gap-2 text-green-400 mb-2">
            <CheckCircle2 className="w-4 h-4" />
            <span className="text-sm">成功</span>
          </div>
          <p className="text-2xl font-bold text-green-400">{task.successful_queries}</p>
        </div>
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
          <div className="flex items-center gap-2 text-red-400 mb-2">
            <XCircle className="w-4 h-4" />
            <span className="text-sm">失败</span>
          </div>
          <p className="text-2xl font-bold text-red-400">{task.failed_queries}</p>
        </div>
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
          <div className="flex items-center gap-2 text-primary-400 mb-2">
            <BarChart3 className="w-4 h-4" />
            <span className="text-sm">引用提取</span>
          </div>
          <p className="text-2xl font-bold text-primary-400">
            {results.reduce((acc, r) => acc + r.citations.length, 0)}
          </p>
        </div>
      </div>

      {/* Results */}
      {task.status === 'completed' && results.length > 0 && (
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Query List */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-700/50">
              <h3 className="font-medium text-white">查询列表</h3>
            </div>
            <div className="max-h-[600px] overflow-y-auto">
              {results.map((result, index) => (
                <button
                  key={index}
                  onClick={() => setSelectedResult(index)}
                  className={clsx(
                    'w-full text-left px-4 py-3 border-b border-slate-700/30 hover:bg-slate-700/30 transition-colors',
                    selectedResult === index && 'bg-slate-700/50'
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white truncate">{result.query}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-slate-400">
                          {result.citations.length} 个引用
                        </span>
                        {result.error && (
                          <span className="text-xs text-red-400">失败</span>
                        )}
                      </div>
                    </div>
                    {selectedResult === index && (
                      <div className="w-1.5 h-1.5 rounded-full bg-primary-400 mt-2" />
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Result Detail */}
          <div className="lg:col-span-2 space-y-4">
            {/* Response */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50">
              <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between">
                <h3 className="font-medium text-white">AI 响应内容</h3>
                <button
                  onClick={() => handleCopy(results[selectedResult]?.response_text || '', -1)}
                  className="text-slate-400 hover:text-white p-1.5 rounded transition-colors"
                >
                  {copiedIndex === -1 ? (
                    <Check className="w-4 h-4 text-green-400" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
              </div>
              <div className="p-4 max-h-[300px] overflow-y-auto">
                <p className="text-slate-300 text-sm whitespace-pre-wrap leading-relaxed">
                  {results[selectedResult]?.response_text || '无响应内容'}
                </p>
              </div>
            </div>

            {/* Citations */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50">
              <div className="px-4 py-3 border-b border-slate-700/50">
                <h3 className="font-medium text-white">
                  引用来源 ({results[selectedResult]?.citations.length || 0})
                </h3>
              </div>
              <div className="divide-y divide-slate-700/30">
                {results[selectedResult]?.citations.length === 0 ? (
                  <div className="p-8 text-center text-slate-400">
                    未提取到引用链接
                  </div>
                ) : (
                  results[selectedResult]?.citations.map((citation, index) => (
                    <div
                      key={index}
                      className="p-4 hover:bg-slate-700/20 transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-6 h-6 rounded-full bg-primary-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span className="text-xs font-bold text-primary-400">
                            {citation.position}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <a
                            href={citation.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-white hover:text-primary-400 font-medium text-sm flex items-center gap-1.5"
                          >
                            {citation.title || citation.url}
                            <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                          </a>
                          <div className="flex items-center gap-2 mt-1">
                            <Globe className="w-3.5 h-3.5 text-slate-500" />
                            <span className="text-xs text-slate-400 truncate">
                              {citation.domain || new URL(citation.url).hostname}
                            </span>
                          </div>
                        </div>
                        <button
                          onClick={() => handleCopy(citation.url, index)}
                          className="text-slate-400 hover:text-white p-1.5 rounded transition-colors"
                        >
                          {copiedIndex === index ? (
                            <Check className="w-4 h-4 text-green-400" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty state for non-completed tasks */}
      {task.status !== 'completed' && (
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-12 text-center">
          <Bot className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400">
            {task.status === 'running' && '正在爬取数据，完成后将显示结果...'}
            {task.status === 'pending' && '任务等待执行中，点击上方"立即执行"按钮开始爬取'}
            {task.status === 'failed' && '任务执行失败，点击"重新执行"重试'}
            {task.status === 'cancelled' && '任务已取消，无结果'}
          </p>
          {task.status === 'pending' && (
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="mt-4 inline-flex items-center gap-2 px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {retrying ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              立即执行
            </button>
          )}
        </div>
      )}
    </div>
  );
}
