'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Plus,
  Bot,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  RefreshCw,
  Search,
  Filter,
  ExternalLink,
  Activity,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface CrawlTask {
  id: string;
  project_id: string;
  project_name: string;
  engine: string;
  status: string;
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

interface Quota {
  daily_limit: number;
  used_today: number;
  remaining: number;
}

const engineInfo: Record<string, { name: string; icon: string }> = {
  perplexity: { name: 'Perplexity', icon: '🔍' },
  google_sge: { name: 'Google SGE', icon: '🌐' },
  bing_copilot: { name: 'Bing Copilot', icon: '💠' },
  qwen: { name: '通义千问', icon: '☁️' },
  deepseek: { name: 'DeepSeek', icon: '🔮' },
  kimi: { name: 'Kimi', icon: '🌙' },
  doubao: { name: '豆包', icon: '🫘' },
  chatglm: { name: 'ChatGLM', icon: '🧠' },
  chatgpt: { name: 'ChatGPT', icon: '🤖' },
};

const statusConfig: Record<string, { label: string; color: string; icon: typeof Clock }> = {
  pending: { label: '等待中', color: 'text-slate-400 bg-slate-500/10', icon: Clock },
  running: { label: '运行中', color: 'text-blue-400 bg-blue-500/10', icon: Activity },
  completed: { label: '已完成', color: 'text-green-400 bg-green-500/10', icon: CheckCircle2 },
  failed: { label: '失败', color: 'text-red-400 bg-red-500/10', icon: XCircle },
  cancelled: { label: '已取消', color: 'text-slate-400 bg-slate-500/10', icon: AlertCircle },
};

export default function ResearchPage() {
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [quota, setQuota] = useState<Quota | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchData = async () => {
    try {
      const [tasksRes, quotaRes] = await Promise.all([
        api.get('/crawler/tasks'),
        api.get('/crawler/quota'),
      ]);
      setTasks(tasksRes.data);
      setQuota(quotaRes.data);
    } catch (error) {
      console.error('Failed to fetch research data:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchData();
  };

  const filteredTasks = tasks.filter((task) => {
    const matchesSearch =
      task.project_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      engineInfo[task.engine]?.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || task.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getProgress = (task: CrawlTask) => {
    if (task.total_queries === 0) return 0;
    return Math.round((task.successful_queries / task.total_queries) * 100);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-white">AI 研究</h1>
          <p className="mt-1 text-slate-400">
            使用 AI 搜索引擎获取品牌可见性数据
          </p>
        </div>
        <div className="flex items-center gap-3">
          {quota && (
            <div className="px-4 py-2 bg-slate-800/50 rounded-lg border border-slate-700/50">
              <div className="text-xs text-slate-400">今日配额</div>
              <div className="text-sm font-medium text-white">
                {quota.remaining} / {quota.daily_limit}
              </div>
            </div>
          )}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-700/50 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("w-5 h-5", isRefreshing && "animate-spin")} />
          </button>
          <Link
            href="/research/new"
            className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg transition-colors"
          >
            <Plus className="w-5 h-5" />
            新建研究
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="搜索项目或引擎..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">全部状态</option>
            <option value="pending">等待中</option>
            <option value="running">运行中</option>
            <option value="completed">已完成</option>
            <option value="failed">失败</option>
          </select>
        </div>
      </div>

      {/* Tasks List */}
      {filteredTasks.length === 0 ? (
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-12 text-center">
          <Bot className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">
            {searchQuery || statusFilter !== 'all' ? '没有找到匹配的研究任务' : '还没有研究任务'}
          </h3>
          <p className="text-slate-400 mb-6">
            {searchQuery || statusFilter !== 'all'
              ? '尝试调整搜索条件'
              : '创建新的 AI 研究任务来获取品牌可见性数据'}
          </p>
          {!searchQuery && statusFilter === 'all' && (
            <Link
              href="/research/new"
              className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg transition-colors"
            >
              <Plus className="w-5 h-5" />
              创建第一个研究
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filteredTasks.map((task) => {
            const status = statusConfig[task.status] || statusConfig.pending;
            const StatusIcon = status.icon;
            const engine = engineInfo[task.engine] || { name: task.engine, icon: '🤖' };
            const progress = getProgress(task);

            return (
              <Link
                key={task.id}
                href={`/research/${task.id}`}
                className="block bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 hover:border-primary-500/50 transition-all group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    {/* Engine Icon */}
                    <div className="w-10 h-10 bg-slate-700/50 rounded-lg flex items-center justify-center text-xl">
                      {engine.icon}
                    </div>

                    {/* Task Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-white font-medium truncate">
                          {task.project_name || '未知项目'}
                        </h3>
                        <span className="text-xs text-slate-500">·</span>
                        <span className="text-sm text-slate-400">{engine.name}</span>
                      </div>
                      <div className="flex items-center gap-4 text-sm">
                        <span className={cn("px-2 py-0.5 rounded text-xs font-medium", status.color)}>
                          <StatusIcon className="w-3 h-3 inline mr-1" />
                          {status.label}
                        </span>
                        <span className="text-slate-500">
                          {task.successful_queries}/{task.total_queries} 条
                        </span>
                        <span className="text-slate-500">
                          {formatDate(task.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Progress & Actions */}
                  <div className="flex items-center gap-4">
                    {task.status === 'running' && (
                      <div className="w-24">
                        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary-500 rounded-full transition-all"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                        <div className="text-xs text-slate-500 mt-1 text-center">
                          {progress}%
                        </div>
                      </div>
                    )}
                    <ExternalLink className="w-4 h-4 text-slate-500 group-hover:text-primary-400 transition-colors" />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* Stats Summary */}
      {tasks.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
          <div className="bg-slate-800/50 rounded-lg border border-slate-700/50 p-4 text-center">
            <div className="text-2xl font-bold text-white">{tasks.length}</div>
            <div className="text-sm text-slate-400">总任务数</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg border border-slate-700/50 p-4 text-center">
            <div className="text-2xl font-bold text-green-400">
              {tasks.filter((t) => t.status === 'completed').length}
            </div>
            <div className="text-sm text-slate-400">已完成</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg border border-slate-700/50 p-4 text-center">
            <div className="text-2xl font-bold text-blue-400">
              {tasks.filter((t) => t.status === 'running').length}
            </div>
            <div className="text-sm text-slate-400">运行中</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg border border-slate-700/50 p-4 text-center">
            <div className="text-2xl font-bold text-white">
              {tasks.reduce((sum, t) => sum + t.successful_queries, 0)}
            </div>
            <div className="text-sm text-slate-400">总查询数</div>
          </div>
        </div>
      )}
    </div>
  );
}
