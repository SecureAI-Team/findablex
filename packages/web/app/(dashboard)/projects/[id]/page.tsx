'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Loader2,
  Play,
  Upload,
  BarChart3,
  Clock,
  FileText,
  Globe,
  Calendar,
  CheckCircle,
  XCircle,
  MoreVertical,
  Trash2,
  Settings,
  Search,
  BookOpen,
  List,
  Bot,
  Eye,
  Target,
  RotateCcw,
} from 'lucide-react';
import { analytics } from '@/lib/analytics';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import CrawlResultsTab from '@/components/project/CrawlResultsTab';
import CitationsSummary from '@/components/project/CitationsSummary';
import EditProjectDialog from '@/components/project/EditProjectDialog';
import QueryManager from '@/components/project/QueryManager';
import QuickCreateTaskDialog from '@/components/project/QuickCreateTaskDialog';

interface Project {
  id: string;
  name: string;
  target_domains: string[];
  industry_template: string | null;
  description: string | null;
  status: string;
  health_score: number | null;
  run_count: number;
  created_at: string;
}

interface Run {
  id: string;
  run_type: string;
  status: string;
  health_score: number | null;
  created_at: string;
  completed_at: string | null;
  input_method: string;
}

interface CrawlTask {
  id: string;
  engine: string;
  status: string;
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

interface QueryItem {
  id: string;
  query_text: string;
  query_type: string | null;
  position: number | null;
}

const runStatusConfig: Record<string, { label: string; icon: any; color: string }> = {
  pending: { label: '等待中', icon: Clock, color: 'text-slate-400' },
  processing: { label: '处理中', icon: Loader2, color: 'text-yellow-400' },
  running: { label: '运行中', icon: Loader2, color: 'text-blue-400' },
  completed: { label: '已完成', icon: CheckCircle, color: 'text-green-400' },
  failed: { label: '失败', icon: XCircle, color: 'text-red-400' },
};

const engineNames: Record<string, string> = {
  deepseek: 'DeepSeek',
  kimi: 'Kimi',
  doubao: '豆包',
  chatglm: 'ChatGLM',
  chatgpt: 'ChatGPT',
  qwen: '通义千问',
  perplexity: 'Perplexity',
  google_sge: 'Google SGE',
  bing_copilot: 'Bing Copilot',
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

type TabId = 'overview' | 'runs' | 'queries' | 'research';

const tabs: { id: TabId; label: string; icon: any }[] = [
  { id: 'overview', label: '概览', icon: BarChart3 },
  { id: 'runs', label: '运行记录', icon: Play },
  { id: 'queries', label: '查询词', icon: List },
  { id: 'research', label: '研究结果', icon: Bot },
];

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [crawlTasks, setCrawlTasks] = useState<CrawlTask[]>([]);
  const [queries, setQueries] = useState<QueryItem[]>([]);
  const [visibilityScore, setVisibilityScore] = useState<number | null>(null);
  const [targetDomainCitations, setTargetDomainCitations] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showMenu, setShowMenu] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showCreateTaskDialog, setShowCreateTaskDialog] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>(
    (searchParams.get('tab') as TabId) || 'overview'
  );

  useEffect(() => {
    const fetchData = async () => {
      try {
        // First, fetch the project - this is required
        const projectRes = await api.get(`/projects/${projectId}`);
        setProject(projectRes.data);
        
        // Then fetch runs and queries separately - these can fail without redirecting
        try {
          const runsRes = await api.get('/runs', { params: { project_id: projectId } });
          setRuns(runsRes.data);
        } catch (runsError) {
          console.error('Failed to fetch runs:', runsError);
          setRuns([]);
        }
        
        try {
          const queriesRes = await api.get(`/projects/${projectId}/queries`);
          setQueries(queriesRes.data);
        } catch (queriesError) {
          console.error('Failed to fetch queries:', queriesError);
          setQueries([]);
        }
        
        try {
          const crawlTasksRes = await api.get(`/projects/${projectId}/crawl-tasks`);
          setCrawlTasks(crawlTasksRes.data);
        } catch (crawlTasksError) {
          console.error('Failed to fetch crawl tasks:', crawlTasksError);
          setCrawlTasks([]);
        }
        
        // Fetch visibility score from citations summary
        try {
          const citationsRes = await api.get(`/projects/${projectId}/citations-summary`);
          if (citationsRes.data) {
            setVisibilityScore(citationsRes.data.visibility_score);
            setTargetDomainCitations(citationsRes.data.target_domain_citations);
          }
        } catch (citationsError) {
          console.error('Failed to fetch citations summary:', citationsError);
        }
      } catch (error: any) {
        console.error('Failed to fetch project:', error);
        // Only redirect if project not found (404) or forbidden (403)
        if (error.response?.status === 404 || error.response?.status === 403) {
          router.push('/projects');
        } else {
          // Show error message for other errors
          setLoadError(error.response?.data?.detail || '加载项目失败，请刷新页面重试');
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [projectId, router]);

  const handleTabChange = (tabId: TabId) => {
    setActiveTab(tabId);
    router.replace(`/projects/${projectId}?tab=${tabId}`, { scroll: false });
  };

  const handleRetest = async (runId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    try {
      const res = await api.post(`/runs/${runId}/retest`);
      // Add new run to the list
      setRuns((prev) => [res.data, ...prev]);
      // Track retest
      analytics.trackRetestTriggered(projectId);
    } catch (error) {
      console.error('Failed to trigger retest:', error);
    }
  };

  const handleDelete = async () => {
    if (!confirm('确定要删除这个项目吗？此操作不可恢复。')) return;

    try {
      await api.delete(`/projects/${projectId}`);
      router.push('/projects');
    } catch (error) {
      console.error('Failed to delete project:', error);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getHealthScoreColor = (score: number | null) => {
    if (score === null) return 'text-slate-500';
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="text-red-400 text-center">
          <p className="text-lg font-medium">加载失败</p>
          <p className="text-sm text-slate-400 mt-1">{loadError}</p>
        </div>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
        >
          刷新页面
        </button>
      </div>
    );
  }

  if (!project) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <Link
            href="/projects"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            返回项目列表
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="font-display text-2xl font-bold text-white">{project.name}</h1>
            <span
              className={cn(
                'px-2 py-0.5 rounded-full text-xs font-medium',
                project.status === 'active'
                  ? 'bg-green-500/10 text-green-400'
                  : 'bg-slate-500/10 text-slate-400'
              )}
            >
              {project.status === 'active' ? '进行中' : project.status}
            </span>
          </div>
          <div className="flex items-center gap-4 mt-2 text-sm text-slate-400">
            <span className="flex items-center gap-1.5">
              <Globe className="w-4 h-4" />
              {project.target_domains[0] || '无域名'}
            </span>
            <span className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4" />
              创建于 {formatDate(project.created_at)}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/reports/research/${projectId}`}
            className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2.5 rounded-lg font-medium transition-all"
          >
            <FileText className="w-5 h-5" />
            查看报告
          </Link>
          <button
            onClick={() => setShowCreateTaskDialog(true)}
            className="inline-flex items-center gap-2 bg-accent-500 hover:bg-accent-600 text-white px-4 py-2.5 rounded-lg font-medium transition-all"
          >
            <Bot className="w-5 h-5" />
            创建研究任务
          </button>
          <Link
            href={`/projects/${projectId}/import`}
            className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2.5 rounded-lg font-medium transition-all"
          >
            <Upload className="w-5 h-5" />
            导入数据
          </Link>
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-2.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
            >
              <MoreVertical className="w-5 h-5" />
            </button>
            {showMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowMenu(false)}
                />
                <div className="absolute right-0 top-full mt-1 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-20 py-1">
                  <button
                    onClick={() => {
                      setShowMenu(false);
                      setShowEditDialog(true);
                    }}
                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                  >
                    <Settings className="w-4 h-4" />
                    项目设置
                  </button>
                  <button
                    onClick={() => {
                      setShowMenu(false);
                      handleDelete();
                    }}
                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-slate-700 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                    删除项目
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-700/50">
        <nav className="flex gap-1 -mb-px">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                className={cn(
                  'inline-flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-400'
                    : 'border-transparent text-slate-400 hover:text-white hover:border-slate-600'
                )}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-sm">品牌可见性</span>
                <Eye className="w-5 h-5 text-primary-400" />
              </div>
              <div className={cn(
                'text-3xl font-bold mt-2',
                visibilityScore === null ? 'text-slate-500' :
                visibilityScore >= 50 ? 'text-green-400' :
                visibilityScore >= 20 ? 'text-yellow-400' : 'text-red-400'
              )}>
                {visibilityScore !== null ? `${visibilityScore}%` : '--'}
              </div>
              {targetDomainCitations > 0 && (
                <div className="text-xs text-slate-500 mt-1">{targetDomainCitations} 次品牌引用</div>
              )}
            </div>
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-sm">研究任务</span>
                <Bot className="w-5 h-5 text-accent-400" />
              </div>
              <div className="text-3xl font-bold text-white mt-2">{crawlTasks.length}</div>
            </div>
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-sm">查询词数量</span>
                <List className="w-5 h-5 text-green-400" />
              </div>
              <div className="text-3xl font-bold text-white mt-2">{queries.length}</div>
            </div>
            {project.target_domains && project.target_domains.length > 0 && (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 text-sm">目标域名</span>
                  <Target className="w-5 h-5 text-cyan-400" />
                </div>
                <div className="text-3xl font-bold text-white mt-2">{project.target_domains.length}</div>
              </div>
            )}
          </div>

          {/* Citations Summary */}
          <CitationsSummary projectId={projectId} />

          {/* Recent Research Tasks */}
          {crawlTasks.length > 0 && (
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-display text-lg font-semibold text-white">最近研究任务</h2>
                <button
                  onClick={() => handleTabChange('runs')}
                  className="text-sm text-primary-400 hover:text-primary-300"
                >
                  查看全部
                </button>
              </div>
              <div className="space-y-3">
                {crawlTasks.slice(0, 3).map((task) => {
                  const statusInfo = runStatusConfig[task.status] || runStatusConfig.pending;
                  const StatusIcon = statusInfo.icon;
                  const progress = task.total_queries > 0
                    ? Math.round(((task.successful_queries + task.failed_queries) / task.total_queries) * 100)
                    : 0;
                  return (
                    <Link
                      key={task.id}
                      href={`/research/${task.id}`}
                      className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-lg">{engineIcons[task.engine] || '🤖'}</span>
                        <span className="text-white">{engineNames[task.engine] || task.engine}</span>
                        <span className={cn('text-sm', statusInfo.color)}>{statusInfo.label}</span>
                        <span className="text-slate-400 text-sm">{formatDate(task.created_at)}</span>
                      </div>
                      <div className="text-sm text-slate-400">
                        {task.status === 'completed'
                          ? `${task.successful_queries}/${task.total_queries} 成功`
                          : `${progress}%`}
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          )}

          {/* Recent Runs */}
          {runs.length > 0 && (
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-display text-lg font-semibold text-white">最近运行</h2>
                <button
                  onClick={() => handleTabChange('runs')}
                  className="text-sm text-primary-400 hover:text-primary-300"
                >
                  查看全部
                </button>
              </div>
              <div className="space-y-3">
                {runs.slice(0, 3).map((run) => {
                  const statusInfo = runStatusConfig[run.status] || runStatusConfig.pending;
                  const StatusIcon = statusInfo.icon;
                  return (
                    <Link
                      key={run.id}
                      href={`/reports/${run.id}`}
                      className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <StatusIcon className={cn('w-4 h-4', statusInfo.color)} />
                        <span className="text-white">
                          {run.run_type === 'checkup' ? '体检' : run.run_type}
                        </span>
                        <span className="text-slate-400 text-sm">{formatDate(run.created_at)}</span>
                      </div>
                      {run.health_score !== null && (
                        <span className={cn('font-bold', getHealthScoreColor(run.health_score))}>
                          {run.health_score}
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'runs' && (
        <div className="space-y-6">
          {/* Research Tasks */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50">
            <div className="p-6 border-b border-slate-700/50 flex items-center justify-between">
              <h2 className="font-display text-lg font-semibold text-white flex items-center gap-2">
                <Bot className="w-5 h-5 text-primary-400" />
                研究任务 ({crawlTasks.length})
              </h2>
              <button
                onClick={() => setShowCreateTaskDialog(true)}
                className="text-sm text-primary-400 hover:text-primary-300"
              >
                + 新建任务
              </button>
            </div>

            {crawlTasks.length === 0 ? (
              <div className="p-12 text-center">
                <Bot className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-white mb-2">还没有研究任务</h3>
                <p className="text-slate-400 mb-6">创建研究任务来分析 AI 引擎的回复</p>
                <button
                  onClick={() => setShowCreateTaskDialog(true)}
                  className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg font-medium transition-all"
                >
                  <Bot className="w-4 h-4" />
                  创建研究任务
                </button>
              </div>
            ) : (
              <div className="divide-y divide-slate-700/50">
                {crawlTasks.map((task) => {
                  const statusInfo = runStatusConfig[task.status] || runStatusConfig.pending;
                  const StatusIcon = statusInfo.icon;
                  const progress = task.total_queries > 0
                    ? Math.round(((task.successful_queries + task.failed_queries) / task.total_queries) * 100)
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
                                {engineNames[task.engine] || task.engine}
                              </span>
                              <span className={cn('text-sm', statusInfo.color)}>
                                {statusInfo.label}
                              </span>
                            </div>
                            <div className="text-sm text-slate-400 mt-0.5">
                              {formatDate(task.created_at)} · {task.total_queries} 个查询
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          {task.status === 'completed' ? (
                            <>
                              <div className="text-xl font-bold text-green-400">
                                {task.successful_queries}/{task.total_queries}
                              </div>
                              <div className="text-xs text-slate-500">成功</div>
                            </>
                          ) : (
                            <>
                              <div className="text-xl font-bold text-white">{progress}%</div>
                              <div className="text-xs text-slate-500">进度</div>
                            </>
                          )}
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>

          {/* GEO Health Runs */}
          {runs.length > 0 && (
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50">
              <div className="p-6 border-b border-slate-700/50">
                <h2 className="font-display text-lg font-semibold text-white flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-accent-400" />
                  体检记录 ({runs.length})
                </h2>
              </div>
              <div className="divide-y divide-slate-700/50">
                {runs.map((run) => {
                  const statusInfo = runStatusConfig[run.status] || runStatusConfig.pending;
                  const StatusIcon = statusInfo.icon;

                  return (
                    <div
                      key={run.id}
                      className="p-6 hover:bg-slate-700/20 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <Link
                          href={`/reports/${run.id}`}
                          className="flex items-center gap-4 flex-1"
                        >
                          <div
                            className={cn(
                              'w-10 h-10 rounded-lg flex items-center justify-center',
                              run.status === 'completed'
                                ? 'bg-green-500/10'
                                : run.status === 'processing'
                                ? 'bg-yellow-500/10'
                                : 'bg-slate-500/10'
                            )}
                          >
                            <StatusIcon
                              className={cn(
                                'w-5 h-5',
                                statusInfo.color,
                                run.status === 'processing' && 'animate-spin'
                              )}
                            />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-white">
                                {run.run_type === 'checkup' ? '体检' : run.run_type === 'retest' ? '复测' : run.run_type}
                              </span>
                              <span className={cn('text-sm', statusInfo.color)}>
                                {statusInfo.label}
                              </span>
                            </div>
                            <div className="text-sm text-slate-400 mt-0.5">
                              {formatDate(run.created_at)} · {run.input_method === 'import' ? '导入' : run.input_method}
                            </div>
                          </div>
                        </Link>
                        <div className="flex items-center gap-4">
                          {run.status === 'completed' && (
                            <>
                              <div className="text-right">
                                <div className={cn('text-xl font-bold', getHealthScoreColor(run.health_score))}>
                                  {run.health_score !== null ? run.health_score : '--'}
                                </div>
                                <div className="text-xs text-slate-500">健康度</div>
                              </div>
                              <button
                                onClick={(e) => handleRetest(run.id, e)}
                                className="p-2 text-slate-400 hover:text-primary-400 hover:bg-slate-700 rounded-lg transition-colors"
                                title="复测"
                              >
                                <RotateCcw className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'queries' && (
        <QueryManager
          projectId={projectId}
          queries={queries}
          onQueriesChange={setQueries}
        />
      )}

      {activeTab === 'research' && (
        <CrawlResultsTab projectId={projectId} />
      )}

      {/* Edit Project Dialog */}
      {showEditDialog && project && (
        <EditProjectDialog
          project={project}
          onSave={(updatedProject) => {
            // Merge updated fields with existing project to preserve all properties
            setProject({ ...project, ...updatedProject });
            setShowEditDialog(false);
          }}
          onClose={() => setShowEditDialog(false)}
        />
      )}

      {/* Quick Create Task Dialog */}
      {showCreateTaskDialog && project && (
        <QuickCreateTaskDialog
          projectId={projectId}
          projectName={project.name}
          queries={queries}
          onClose={() => setShowCreateTaskDialog(false)}
          onSuccess={() => {
            // Optionally refresh data or navigate
          }}
        />
      )}
    </div>
  );
}
