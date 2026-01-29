'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Bot,
  Plus,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ChevronRight,
  Search,
  Filter,
  Loader2,
  Link as LinkIcon,
  Globe,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from 'lucide-react';
import { api } from '@/lib/api';
import { clsx } from 'clsx';

interface CrawlTask {
  id: string;
  project_id: string;
  project_name?: string;
  engine: string;
  status: string;
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

interface Engine {
  id: string;
  name: string;
  priority: string;
  method: string;
}

interface Project {
  id: string;
  name: string;
}

const statusConfig: Record<string, { icon: typeof Clock; color: string; label: string }> = {
  pending: { icon: Clock, color: 'text-yellow-400', label: '等待中' },
  running: { icon: RefreshCw, color: 'text-blue-400', label: '运行中' },
  completed: { icon: CheckCircle2, color: 'text-green-400', label: '已完成' },
  failed: { icon: XCircle, color: 'text-red-400', label: '失败' },
  cancelled: { icon: AlertCircle, color: 'text-slate-400', label: '已取消' },
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

// Engine feature support configuration
const engineFeatures: Record<string, { 
  citations: boolean;
  webSearch: boolean;
  implemented: boolean;
  note?: string;
}> = {
  perplexity: { citations: true, webSearch: true, implemented: true },
  kimi: { citations: true, webSearch: true, implemented: true },
  deepseek: { citations: true, webSearch: true, implemented: true, note: '联网搜索模式' },
  qwen: { citations: true, webSearch: true, implemented: true, note: '联网搜索模式' },
  google_sge: { citations: true, webSearch: true, implemented: true, note: 'AI Overview' },
  bing_copilot: { citations: true, webSearch: true, implemented: true },
  doubao: { citations: false, webSearch: false, implemented: true, note: '需要登录' },
  chatglm: { citations: false, webSearch: false, implemented: true, note: '需要登录' },
  chatgpt: { citations: false, webSearch: false, implemented: true, note: '需要登录' },
};

type SortField = 'created_at' | 'status' | 'progress';
type SortOrder = 'asc' | 'desc';

export default function ResearchPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [engines, setEngines] = useState<Engine[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [engineFilter, setEngineFilter] = useState<string>('all');
  const [projectFilter, setProjectFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [tasksRes, enginesRes, projectsRes] = await Promise.all([
        api.get('/crawler/tasks'),
        api.get('/crawler/engines'),
        api.get('/projects'),
      ]);
      setTasks(tasksRes.data);
      setEngines(enginesRes.data);
      setProjects(projectsRes.data);
      setError(null);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('您没有研究员权限，无法访问此页面');
      } else {
        setError('加载数据失败');
      }
    } finally {
      setLoading(false);
    }
  };

  const getEngineName = (engineId: string) => {
    const engine = engines.find((e) => e.id === engineId);
    return engine?.name || engineId;
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const statusOrder: Record<string, number> = {
    running: 0,
    pending: 1,
    completed: 2,
    failed: 3,
    cancelled: 4,
  };

  const filteredAndSortedTasks = tasks
    .filter((task) => {
      if (statusFilter !== 'all' && task.status !== statusFilter) return false;
      if (engineFilter !== 'all' && task.engine !== engineFilter) return false;
      if (projectFilter !== 'all' && task.project_id !== projectFilter) return false;
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const engineName = getEngineName(task.engine).toLowerCase();
        const projectName = (task.project_name || '').toLowerCase();
        return engineName.includes(query) || projectName.includes(query);
      }
      return true;
    })
    .sort((a, b) => {
      let comparison = 0;
      
      if (sortField === 'created_at') {
        comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      } else if (sortField === 'status') {
        comparison = (statusOrder[a.status] || 99) - (statusOrder[b.status] || 99);
      } else if (sortField === 'progress') {
        const progressA = a.total_queries > 0 
          ? (a.successful_queries + a.failed_queries) / a.total_queries 
          : 0;
        const progressB = b.total_queries > 0 
          ? (b.successful_queries + b.failed_queries) / b.total_queries 
          : 0;
        comparison = progressA - progressB;
      }
      
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4">
        <AlertCircle className="w-12 h-12 text-red-400" />
        <p className="text-slate-300">{error}</p>
        <button
          onClick={() => router.push('/dashboard')}
          className="text-primary-400 hover:text-primary-300"
        >
          返回概览
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-white flex items-center gap-3">
            <Bot className="w-7 h-7 text-primary-400" />
            AI 爬虫研究
          </h1>
          <p className="mt-1 text-slate-400">
            使用 AI 引擎爬取品牌可见性数据，进行 GEO 研究分析
          </p>
        </div>
        <Link
          href="/research/new"
          className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2.5 rounded-lg font-medium transition-all hover:scale-105"
        >
          <Plus className="w-5 h-5" />
          新建爬虫任务
        </Link>
      </div>

      {/* Supported Engines */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <h2 className="font-display text-lg font-semibold text-white mb-4">支持的 AI 引擎</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {engines.map((engine) => {
            const features = engineFeatures[engine.id] || { citations: false, webSearch: false, implemented: false };
            return (
              <div
                key={engine.id}
                className={clsx(
                  'bg-slate-700/30 rounded-lg p-3 text-center hover:bg-slate-700/50 transition-colors relative',
                  !features.implemented && 'opacity-60'
                )}
              >
                <div className="text-2xl mb-1">{engineIcons[engine.id] || '🤖'}</div>
                <div className="text-sm font-medium text-white">{engine.name}</div>
                <div className="text-xs text-slate-400 mt-0.5">{engine.method}</div>
                
                {/* Feature indicators */}
                <div className="flex items-center justify-center gap-1.5 mt-2">
                  {features.citations && (
                    <span 
                      className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] bg-green-500/20 text-green-400"
                      title="支持引用提取"
                    >
                      <LinkIcon className="w-2.5 h-2.5" />
                      引用
                    </span>
                  )}
                  {features.webSearch && (
                    <span 
                      className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] bg-blue-500/20 text-blue-400"
                      title="支持联网搜索"
                    >
                      <Globe className="w-2.5 h-2.5" />
                      联网
                    </span>
                  )}
                </div>
                
                {!features.implemented && (
                  <div className="absolute inset-0 flex items-center justify-center bg-slate-900/60 rounded-lg">
                    <span className="text-xs text-slate-400">即将支持</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
        
        {/* Legend */}
        <div className="flex items-center gap-4 mt-4 pt-4 border-t border-slate-700/50 text-xs text-slate-400">
          <span className="flex items-center gap-1">
            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-green-500/20 text-green-400">
              <LinkIcon className="w-2.5 h-2.5" />
              引用
            </span>
            = 提取来源链接
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">
              <Globe className="w-2.5 h-2.5" />
              联网
            </span>
            = 实时搜索
          </span>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="space-y-4">
        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索任务（引擎名称、项目名称）..."
            className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
            >
              ×
            </button>
          )}
        </div>

        {/* Filters and Sort */}
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={projectFilter}
              onChange={(e) => setProjectFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">全部项目</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">全部状态</option>
              <option value="pending">等待中</option>
              <option value="running">运行中</option>
              <option value="completed">已完成</option>
              <option value="failed">失败</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={engineFilter}
              onChange={(e) => setEngineFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">全部引擎</option>
              {engines.map((engine) => (
                <option key={engine.id} value={engine.id}>
                  {engine.name}
                </option>
              ))}
            </select>
          </div>

          {/* Sort Controls */}
          <div className="flex items-center gap-2">
            <ArrowUpDown className="w-4 h-4 text-slate-400" />
            <select
              value={sortField}
              onChange={(e) => setSortField(e.target.value as SortField)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="created_at">按时间</option>
              <option value="status">按状态</option>
              <option value="progress">按进度</option>
            </select>
            <button
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              className="p-1.5 text-slate-400 hover:text-white transition-colors"
              title={sortOrder === 'asc' ? '升序' : '降序'}
            >
              {sortOrder === 'asc' ? (
                <ArrowUp className="w-4 h-4" />
              ) : (
                <ArrowDown className="w-4 h-4" />
              )}
            </button>
          </div>

          <button
            onClick={fetchData}
            className="ml-auto inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
        </div>
      </div>

      {/* Task List */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-700/50">
          <h2 className="font-display text-lg font-semibold text-white">
            爬虫任务 ({filteredAndSortedTasks.length})
          </h2>
        </div>

        {filteredAndSortedTasks.length === 0 ? (
          <div className="p-12 text-center">
            <Bot className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400 mb-4">还没有爬虫任务</p>
            <Link
              href="/research/new"
              className="inline-flex items-center gap-2 text-primary-400 hover:text-primary-300"
            >
              <Plus className="w-4 h-4" />
              创建第一个任务
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-slate-700/50">
            {filteredAndSortedTasks.map((task) => {
              const status = statusConfig[task.status] || statusConfig.pending;
              const StatusIcon = status.icon;
              const progress =
                task.total_queries > 0
                  ? Math.round(
                      ((task.successful_queries + task.failed_queries) / task.total_queries) * 100
                    )
                  : 0;

              return (
                <Link
                  key={task.id}
                  href={`/research/${task.id}`}
                  className="block p-6 hover:bg-slate-700/20 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="text-2xl">{engineIcons[task.engine] || '🤖'}</div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-white">
                            {getEngineName(task.engine)}
                          </span>
                          {task.project_name && (
                            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-primary-500/20 text-primary-300">
                              {task.project_name}
                            </span>
                          )}
                          <span
                            className={clsx(
                              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                              status.color,
                              'bg-slate-700/50'
                            )}
                          >
                            <StatusIcon
                              className={clsx('w-3 h-3', task.status === 'running' && 'animate-spin')}
                            />
                            {status.label}
                          </span>
                        </div>
                        <div className="text-sm text-slate-400 mt-1">
                          {task.total_queries} 个查询 · {formatDate(task.created_at)}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-6">
                      {/* Progress */}
                      <div className="hidden sm:block w-32">
                        <div className="flex justify-between text-xs text-slate-400 mb-1">
                          <span>进度</span>
                          <span>{progress}%</span>
                        </div>
                        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                          <div
                            className={clsx(
                              'h-full rounded-full transition-all',
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
                      {/* Stats */}
                      <div className="hidden md:flex items-center gap-4 text-sm">
                        <div className="text-center">
                          <div className="text-green-400 font-medium">{task.successful_queries}</div>
                          <div className="text-xs text-slate-500">成功</div>
                        </div>
                        <div className="text-center">
                          <div className="text-red-400 font-medium">{task.failed_queries}</div>
                          <div className="text-xs text-slate-500">失败</div>
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-slate-600" />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
