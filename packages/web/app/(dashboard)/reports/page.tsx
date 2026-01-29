'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Search,
  FileText,
  Loader2,
  Calendar,
  Filter,
  Download,
  Share2,
  BarChart3,
  Eye,
  Bot,
  Plus,
  TrendingUp,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface HealthReport {
  id: string;
  run_id: string;
  title: string;
  report_type: 'health_check';
  generated_at: string;
  project_name: string;
  project_id: string;
  health_score: number | null;
}

interface ResearchProject {
  id: string;
  name: string;
  has_crawl_data: boolean;
  crawl_task_count: number;
  target_domains: string[];
}

type ReportItem = HealthReport | { type: 'research'; project: ResearchProject };

export default function ReportsPage() {
  const [healthReports, setHealthReports] = useState<HealthReport[]>([]);
  const [researchProjects, setResearchProjects] = useState<ResearchProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [dateFilter, setDateFilter] = useState<string>('all');
  const [reportType, setReportType] = useState<'all' | 'health' | 'research'>('all');

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Get user's workspace first
        const userRes = await api.get('/auth/me');
        const wsId = userRes.data.default_workspace_id;

        if (wsId) {
          // Get all projects
          const projectsRes = await api.get('/projects', {
            params: { workspace_id: wsId },
          });

          const projects = projectsRes.data;
          const allHealthReports: HealthReport[] = [];
          const allResearchProjects: ResearchProject[] = [];

          for (const project of projects) {
            // Get health check runs
            try {
              const runsRes = await api.get('/runs', {
                params: { project_id: project.id, status: 'completed' },
              });

              for (const run of runsRes.data) {
                allHealthReports.push({
                  id: run.id,
                  run_id: run.id,
                  title: `${project.name} - GEO 体检报告`,
                  report_type: 'health_check',
                  generated_at: run.completed_at || run.created_at,
                  project_name: project.name,
                  project_id: project.id,
                  health_score: run.health_score,
                });
              }
            } catch (e) {
              // Ignore runs fetch errors
            }

            // Get crawl tasks to check for research data
            try {
              const tasksRes = await api.get(`/projects/${project.id}/crawl-tasks`);
              const completedTasks = tasksRes.data.filter((t: any) => t.status === 'completed');
              
              if (completedTasks.length > 0 || project.target_domains?.length > 0) {
                allResearchProjects.push({
                  id: project.id,
                  name: project.name,
                  has_crawl_data: completedTasks.length > 0,
                  crawl_task_count: completedTasks.length,
                  target_domains: project.target_domains || [],
                });
              }
            } catch (e) {
              // Ignore crawl tasks fetch errors
            }
          }

          // Sort health reports by date
          allHealthReports.sort(
            (a, b) =>
              new Date(b.generated_at).getTime() - new Date(a.generated_at).getTime()
          );

          setHealthReports(allHealthReports);
          setResearchProjects(allResearchProjects);
        }
      } catch (error) {
        console.error('Failed to fetch reports:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const getHealthScoreColor = (score: number | null) => {
    if (score === null) return 'text-slate-500';
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getHealthScoreBg = (score: number | null) => {
    if (score === null) return 'bg-slate-500/10';
    if (score >= 80) return 'bg-green-500/10';
    if (score >= 60) return 'bg-yellow-500/10';
    return 'bg-red-500/10';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const filterByDate = (report: HealthReport) => {
    if (dateFilter === 'all') return true;

    const reportDate = new Date(report.generated_at);
    const now = new Date();

    switch (dateFilter) {
      case 'today':
        return reportDate.toDateString() === now.toDateString();
      case 'week':
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        return reportDate >= weekAgo;
      case 'month':
        const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        return reportDate >= monthAgo;
      default:
        return true;
    }
  };

  const filteredHealthReports = healthReports
    .filter(filterByDate)
    .filter(
      (report) =>
        report.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        report.project_name.toLowerCase().includes(searchQuery.toLowerCase())
    );

  const filteredResearchProjects = researchProjects.filter(
    (project) =>
      project.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const showHealthReports = reportType === 'all' || reportType === 'health';
  const showResearchReports = reportType === 'all' || reportType === 'research';

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-white flex items-center gap-3">
            <FileText className="w-7 h-7 text-primary-400" />
            报告中心
          </h1>
          <p className="mt-1 text-slate-400">查看 AI 可见性研究报告和 GEO 体检报告</p>
        </div>
      </div>

      {/* Report Type Tabs */}
      <div className="flex gap-2 border-b border-slate-700/50 pb-4">
        <button
          onClick={() => setReportType('all')}
          className={cn(
            'px-4 py-2 rounded-lg text-sm font-medium transition-all',
            reportType === 'all'
              ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
              : 'bg-slate-800/50 text-slate-400 hover:text-white border border-slate-700/50'
          )}
        >
          全部报告
        </button>
        <button
          onClick={() => setReportType('research')}
          className={cn(
            'px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2',
            reportType === 'research'
              ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
              : 'bg-slate-800/50 text-slate-400 hover:text-white border border-slate-700/50'
          )}
        >
          <Eye className="w-4 h-4" />
          研究报告
          <span className="ml-1 px-1.5 py-0.5 rounded bg-blue-500/20 text-xs">
            {researchProjects.length}
          </span>
        </button>
        <button
          onClick={() => setReportType('health')}
          className={cn(
            'px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2',
            reportType === 'health'
              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
              : 'bg-slate-800/50 text-slate-400 hover:text-white border border-slate-700/50'
          )}
        >
          <TrendingUp className="w-4 h-4" />
          体检报告
          <span className="ml-1 px-1.5 py-0.5 rounded bg-green-500/20 text-xs">
            {healthReports.length}
          </span>
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
          <input
            type="text"
            placeholder="搜索报告..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>
        {(reportType === 'all' || reportType === 'health') && (
          <select
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            className="px-4 py-2.5 bg-slate-800/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">全部时间</option>
            <option value="today">今天</option>
            <option value="week">最近一周</option>
            <option value="month">最近一月</option>
          </select>
        )}
      </div>

      {/* Research Reports Section */}
      {showResearchReports && (
        <section>
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <Eye className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h2 className="font-display text-lg font-semibold text-white">
                AI 可见性研究报告
              </h2>
              <p className="text-sm text-slate-400">
                基于爬虫数据分析品牌在 AI 引擎中的表现
              </p>
            </div>
          </div>

          {filteredResearchProjects.length === 0 ? (
            <div className="text-center py-12 bg-slate-800/30 rounded-xl border border-slate-700/50">
              <Bot className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">
                还没有研究数据
              </h3>
              <p className="text-slate-400 mb-6">
                先创建项目并运行研究任务，即可生成 AI 可见性报告
              </p>
              <Link
                href="/research"
                className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg font-medium transition-all"
              >
                <Plus className="w-5 h-5" />
                开始研究
              </Link>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {filteredResearchProjects.map((project) => (
                <Link
                  key={project.id}
                  href={`/reports/research/${project.id}`}
                  className="block bg-gradient-to-br from-blue-500/10 to-slate-800/50 rounded-xl border border-blue-500/30 p-6 hover:border-blue-400/50 hover:from-blue-500/20 transition-all group"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                        <BarChart3 className="w-5 h-5 text-blue-400" />
                      </div>
                      <div>
                        <h3 className="font-medium text-white group-hover:text-blue-400 transition-colors">
                          {project.name}
                        </h3>
                        <span className="text-sm text-slate-400">研究报告</span>
                      </div>
                    </div>
                    {project.has_crawl_data && (
                      <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">
                        有数据
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-sm text-slate-400">
                    <span className="flex items-center gap-1">
                      <FileText className="w-4 h-4" />
                      {project.crawl_task_count} 个任务
                    </span>
                    {project.target_domains.length > 0 && (
                      <span className="flex items-center gap-1">
                        <Eye className="w-4 h-4" />
                        {project.target_domains.length} 个目标域名
                      </span>
                    )}
                  </div>
                  <div className="mt-4 pt-4 border-t border-slate-700/50 flex items-center justify-between">
                    <span className="text-blue-400 text-sm">查看详细报告</span>
                    <span className="text-slate-500 text-xs">
                      独创 AVI / CQS / CPI 指标
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Health Reports Section */}
      {showHealthReports && (
        <section className={showResearchReports ? 'mt-8' : ''}>
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <TrendingUp className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <h2 className="font-display text-lg font-semibold text-white">
                GEO 体检报告
              </h2>
              <p className="text-sm text-slate-400">
                基于健康度评分的体检分析报告
              </p>
            </div>
          </div>

          {filteredHealthReports.length === 0 ? (
            <div className="text-center py-12 bg-slate-800/30 rounded-xl border border-slate-700/50">
              <FileText className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">
                {searchQuery || dateFilter !== 'all'
                  ? '没有找到匹配的报告'
                  : '还没有体检报告'}
              </h3>
              <p className="text-slate-400 mb-6">
                {searchQuery || dateFilter !== 'all'
                  ? '尝试其他筛选条件'
                  : '完成一次 GEO 体检后将自动生成报告'}
              </p>
              {!searchQuery && dateFilter === 'all' && (
                <Link
                  href="/projects"
                  className="inline-flex items-center gap-2 bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg font-medium transition-all"
                >
                  <Plus className="w-5 h-5" />
                  开始体检
                </Link>
              )}
            </div>
          ) : (
            <div className="grid gap-4">
              {filteredHealthReports.map((report) => (
                <Link
                  key={report.id}
                  href={`/reports/${report.id}`}
                  className="block bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 hover:border-green-500/50 hover:bg-slate-800/80 transition-all group"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4 flex-1 min-w-0">
                      <div
                        className={cn(
                          'w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0',
                          getHealthScoreBg(report.health_score)
                        )}
                      >
                        <span
                          className={cn(
                            'text-xl font-bold',
                            getHealthScoreColor(report.health_score)
                          )}
                        >
                          {report.health_score !== null ? report.health_score : '--'}
                        </span>
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-medium text-white truncate group-hover:text-green-400 transition-colors">
                          {report.title}
                        </h3>
                        <div className="flex items-center gap-4 mt-1 text-sm text-slate-400">
                          <span>{report.project_name}</span>
                          <span className="flex items-center gap-1.5">
                            <Calendar className="w-4 h-4" />
                            {formatDate(report.generated_at)}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-500/10 text-green-400">
                        体检报告
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Empty State for All */}
      {!showHealthReports && !showResearchReports && (
        <div className="text-center py-16 bg-slate-800/30 rounded-xl border border-slate-700/50">
          <FileText className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">
            选择报告类型
          </h3>
          <p className="text-slate-400">
            点击上方标签查看研究报告或体检报告
          </p>
        </div>
      )}
    </div>
  );
}
