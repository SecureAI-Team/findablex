'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  BarChart3,
  FileText,
  FolderKanban,
  TrendingUp,
  TrendingDown,
  Minus,
  Plus,
  Loader2,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import QuickCheckup from '@/components/QuickCheckup';
import ReferralCard from '@/components/ReferralCard';

interface Stats {
  projects_count: number;
  runs_count: number;
  completed_runs_count: number;
  avg_health_score: number | null;
}

interface Project {
  id: string;
  name: string;
  health_score: number | null;
  status: string;
  run_count: number;
  last_run_at: string | null;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentProjects, setRecentProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [userName, setUserName] = useState<string>('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Get user info and workspace
        const userRes = await api.get('/auth/me');
        const wsId = userRes.data.default_workspace_id;
        setWorkspaceId(wsId);
        setUserName(userRes.data.full_name || userRes.data.email.split('@')[0]);

        if (wsId) {
          // Fetch stats and projects in parallel
          const [statsRes, projectsRes] = await Promise.all([
            api.get(`/workspaces/${wsId}/stats`),
            api.get('/projects', { params: { workspace_id: wsId } }),
          ]);

          setStats(statsRes.data);
          // Take only the 5 most recent projects
          setRecentProjects(projectsRes.data.slice(0, 5));
        }
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
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

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '从未运行';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return '今天';
    if (diffDays === 1) return '昨天';
    if (diffDays < 7) return `${diffDays} 天前`;
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  // Empty state for new users - redirect to onboarding
  if (!stats || stats.projects_count === 0) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="font-display text-2xl font-bold text-white">
            欢迎, {userName}! 👋
          </h1>
          <p className="mt-1 text-slate-400">开始您的 GEO 可见性之旅</p>
        </div>

        {/* Guided Onboarding Card */}
        <div className="bg-gradient-to-br from-primary-500/20 via-primary-600/10 to-accent-500/20 rounded-2xl border border-primary-500/30 p-8 text-center">
          <div className="w-16 h-16 bg-primary-500/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <Sparkles className="w-8 h-8 text-primary-400" />
          </div>
          <h2 className="font-display text-2xl font-bold text-white mb-3">
            3 步开启 GEO 体检
          </h2>
          <p className="text-slate-300 max-w-md mx-auto mb-6">
            选择行业、创建项目、自动加载模板 — 只需 3 步即可看到您品牌在 AI 搜索中的表现
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/onboarding"
              className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-6 py-3 rounded-lg font-medium transition-all hover:scale-105"
            >
              <Sparkles className="w-5 h-5" />
              开始引导设置
            </Link>
            <Link
              href="/projects/new"
              className="inline-flex items-center gap-2 text-slate-300 hover:text-white border border-slate-600 hover:border-slate-500 px-6 py-3 rounded-lg font-medium transition-all"
            >
              <Plus className="w-5 h-5" />
              直接创建项目
            </Link>
          </div>
        </div>

        {/* Demo Report Link */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-accent-500/10 rounded-xl flex items-center justify-center flex-shrink-0">
              <BarChart3 className="w-6 h-6 text-accent-400" />
            </div>
            <div className="flex-1">
              <h3 className="font-display text-lg font-semibold text-white">查看样例报告</h3>
              <p className="text-sm text-slate-400 mt-1">先看看一份完整的 GEO 体检报告长什么样</p>
            </div>
            <Link
              href="/sample-report"
              className="inline-flex items-center gap-2 text-primary-400 hover:text-primary-300 text-sm font-medium"
            >
              免费体验
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>

        {/* Quick Checkup for new users */}
        <QuickCheckup />

        {/* Getting Started Steps */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
          <h3 className="font-display text-lg font-semibold text-white mb-4">快速开始指南</h3>
          <div className="space-y-4">
            {[
              { step: 1, title: '选择行业', desc: '选择您的行业，自动加载最适合的查询模板' },
              { step: 2, title: '创建项目', desc: '设置项目名称和目标域名，一键创建' },
              { step: 3, title: '查看报告', desc: '自动生成 GEO 体检报告，获取优化建议' },
            ].map((item) => (
              <div key={item.step} className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-primary-400 font-bold text-sm">{item.step}</span>
                </div>
                <div>
                  <h4 className="font-medium text-white">{item.title}</h4>
                  <p className="text-sm text-slate-400">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold text-white">概览</h1>
        <p className="mt-1 text-slate-400">查看您的 GEO 可见性整体状况</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 bg-primary-500/10 rounded-lg flex items-center justify-center">
              <FolderKanban className="w-5 h-5 text-primary-400" />
            </div>
          </div>
          <div className="mt-4">
            <p className="text-2xl font-bold text-white">{stats.projects_count}</p>
            <p className="text-sm text-slate-400">项目数量</p>
          </div>
        </div>

        <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 bg-accent-500/10 rounded-lg flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-accent-400" />
            </div>
          </div>
          <div className="mt-4">
            <p className="text-2xl font-bold text-white">{stats.runs_count}</p>
            <p className="text-sm text-slate-400">运行次数</p>
          </div>
        </div>

        <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 bg-green-500/10 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-green-400" />
            </div>
          </div>
          <div className="mt-4">
            <p className="text-2xl font-bold text-white">{stats.completed_runs_count}</p>
            <p className="text-sm text-slate-400">已完成报告</p>
          </div>
        </div>

        <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 bg-yellow-500/10 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-yellow-400" />
            </div>
          </div>
          <div className="mt-4">
            <p className={cn('text-2xl font-bold', getHealthScoreColor(stats.avg_health_score))}>
              {stats.avg_health_score !== null ? `${Math.round(stats.avg_health_score)}%` : '--'}
            </p>
            <p className="text-sm text-slate-400">平均健康度</p>
          </div>
        </div>
      </div>

      {/* Recent Projects */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50">
        <div className="p-6 border-b border-slate-700/50 flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-white">最近项目</h2>
          <Link
            href="/projects/new"
            className="inline-flex items-center gap-1.5 text-sm text-primary-400 hover:text-primary-300 transition-colors"
          >
            <Plus className="w-4 h-4" />
            新建项目
          </Link>
        </div>
        {recentProjects.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-slate-400">还没有项目</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-700/50">
            {recentProjects.map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.id}`}
                className="block p-6 hover:bg-slate-700/20 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-white">{project.name}</h3>
                    <p className="text-sm text-slate-400 mt-1">
                      {project.run_count} 次运行 · 最后运行: {formatDate(project.last_run_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className={cn('text-lg font-bold', getHealthScoreColor(project.health_score))}>
                        {project.health_score !== null ? project.health_score : '--'}
                      </p>
                      <p className="text-xs text-slate-500">健康度</p>
                    </div>
                    <ArrowRight className="w-5 h-5 text-slate-600" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
        <div className="p-4 border-t border-slate-700/50">
          <Link
            href="/projects"
            className="text-primary-400 hover:text-primary-300 text-sm font-medium transition-colors"
          >
            查看所有项目 →
          </Link>
        </div>
      </div>

      {/* One-click Checkup */}
      <QuickCheckup />

      {/* Quick Actions + Referral */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-6">
          <Link
            href="/projects/new"
            className="bg-gradient-to-r from-primary-500/20 to-primary-600/20 rounded-xl p-6 border border-primary-500/30 hover:border-primary-500/50 transition-all group"
          >
            <h3 className="font-display text-lg font-semibold text-white group-hover:text-primary-300 transition-colors">
              创建新项目
            </h3>
            <p className="mt-2 text-sm text-slate-400">
              开始一个新的 GEO 体检项目，监测您的品牌可见性
            </p>
          </Link>
          <Link
            href="/reports"
            className="bg-gradient-to-r from-accent-500/20 to-accent-600/20 rounded-xl p-6 border border-accent-500/30 hover:border-accent-500/50 transition-all group"
          >
            <h3 className="font-display text-lg font-semibold text-white group-hover:text-accent-300 transition-colors">
              查看报告
            </h3>
            <p className="mt-2 text-sm text-slate-400">
              浏览历史体检报告，追踪可见性变化趋势
            </p>
          </Link>
        </div>
        <ReferralCard />
      </div>
    </div>
  );
}
