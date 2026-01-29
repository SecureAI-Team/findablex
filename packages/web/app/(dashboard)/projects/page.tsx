'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Plus,
  Search,
  FolderKanban,
  MoreVertical,
  Loader2,
  TrendingUp,
  TrendingDown,
  Minus,
  Calendar,
  Globe,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Project {
  id: string;
  name: string;
  target_domains: string[];
  status: string;
  health_score: number | null;
  created_at: string;
  last_run_at: string | null;
  run_count: number;
}

const statusLabels: Record<string, { label: string; color: string }> = {
  active: { label: '进行中', color: 'bg-green-500/10 text-green-400' },
  completed: { label: '已完成', color: 'bg-blue-500/10 text-blue-400' },
  archived: { label: '已归档', color: 'bg-slate-500/10 text-slate-400' },
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // First get user info to get workspace_id
        const userRes = await api.get('/auth/me');
        const wsId = userRes.data.default_workspace_id;
        setWorkspaceId(wsId);

        if (wsId) {
          const res = await api.get('/projects', {
            params: {
              workspace_id: wsId,
              status: statusFilter !== 'all' ? statusFilter : undefined,
            },
          });
          setProjects(res.data);
        }
      } catch (error) {
        console.error('Failed to fetch projects:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [statusFilter]);

  const filteredProjects = projects.filter((project) =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    project.target_domains.some((d) => d.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const getHealthScoreColor = (score: number | null) => {
    if (score === null) return 'text-slate-500';
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '从未';
    return new Date(dateString).toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
    });
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
          <h1 className="font-display text-2xl font-bold text-white">项目</h1>
          <p className="mt-1 text-slate-400">管理您的 GEO 体检项目</p>
        </div>
        <Link
          href="/projects/new"
          className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2.5 rounded-lg font-medium transition-all"
        >
          <Plus className="w-5 h-5" />
          创建项目
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
          <input
            type="text"
            placeholder="搜索项目..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2.5 bg-slate-800/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="all">全部状态</option>
          <option value="active">进行中</option>
          <option value="completed">已完成</option>
          <option value="archived">已归档</option>
        </select>
      </div>

      {/* Projects List */}
      {filteredProjects.length === 0 ? (
        <div className="text-center py-16 bg-slate-800/30 rounded-xl border border-slate-700/50">
          <FolderKanban className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">
            {searchQuery ? '没有找到匹配的项目' : '还没有项目'}
          </h3>
          <p className="text-slate-400 mb-6">
            {searchQuery ? '尝试其他搜索词' : '创建您的第一个 GEO 体检项目'}
          </p>
          {!searchQuery && (
            <Link
              href="/projects/new"
              className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg font-medium transition-all"
            >
              <Plus className="w-4 h-4" />
              创建项目
            </Link>
          )}
        </div>
      ) : (
        <div className="grid gap-4">
          {filteredProjects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="block bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 hover:border-primary-500/50 hover:bg-slate-800/80 transition-all group"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-medium text-white truncate group-hover:text-primary-400 transition-colors">
                      {project.name}
                    </h3>
                    <span
                      className={cn(
                        'px-2 py-0.5 rounded-full text-xs font-medium',
                        statusLabels[project.status]?.color || 'bg-slate-500/10 text-slate-400'
                      )}
                    >
                      {statusLabels[project.status]?.label || project.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-slate-400">
                    <span className="flex items-center gap-1.5">
                      <Globe className="w-4 h-4" />
                      {project.target_domains[0] || '无域名'}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Calendar className="w-4 h-4" />
                      {formatDate(project.created_at)}
                    </span>
                    <span>
                      {project.run_count || 0} 次运行
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <div className={cn('text-2xl font-bold', getHealthScoreColor(project.health_score))}>
                    {project.health_score !== null ? project.health_score : '--'}
                  </div>
                  <div className="text-xs text-slate-500">健康度</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
