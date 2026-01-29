'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  ArrowUp,
  ArrowDown,
  Minus,
  TrendingUp,
  TrendingDown,
  Loader2,
  AlertCircle,
  Calendar,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface ComparisonData {
  project_id: string;
  project_name: string;
  generated_at: string;
  current: {
    summary: { overall_score: number };
    scores: {
      avi: { score: number };
      cqs: { score: number };
      cpi: { score: number };
    };
    report_date: string;
  };
  previous: {
    summary: { overall_score: number };
    scores: {
      avi: { score: number };
      cqs: { score: number };
      cpi: { score: number };
    };
    report_date: string;
  };
  comparison: {
    overall: {
      current: number;
      previous: number;
      change: number;
      change_pct: number;
      trend: 'up' | 'down' | 'stable';
    };
    status: string;
    status_text: string;
    scores: {
      avi: { change: number; change_pct: number; trend: string };
      cqs: { change: number; change_pct: number; trend: string };
      cpi: { change: number; change_pct: number; trend: string };
    };
    insights: Array<{ type: string; text: string }>;
  };
}

function TrendIndicator({
  trend,
  value,
}: {
  trend: string;
  value: number;
}) {
  if (trend === 'up') {
    return (
      <span className="flex items-center gap-1 text-green-400">
        <ArrowUp className="w-4 h-4" />
        +{value}
      </span>
    );
  }
  if (trend === 'down') {
    return (
      <span className="flex items-center gap-1 text-red-400">
        <ArrowDown className="w-4 h-4" />
        {value}
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-slate-400">
      <Minus className="w-4 h-4" />
      {value}
    </span>
  );
}

function ScoreCompareCard({
  label,
  current,
  previous,
  change,
  changePct,
  trend,
}: {
  label: string;
  current: number;
  previous: number;
  change: number;
  changePct: number;
  trend: string;
}) {
  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
      <div className="text-sm text-slate-400 mb-4">{label}</div>
      <div className="flex items-end justify-between">
        <div>
          <div className="text-4xl font-bold text-white">{current}</div>
          <div className="text-sm text-slate-500 mt-1">
            上次: {previous}
          </div>
        </div>
        <div
          className={cn(
            'text-right',
            trend === 'up' && 'text-green-400',
            trend === 'down' && 'text-red-400',
            trend === 'stable' && 'text-slate-400'
          )}
        >
          <div className="flex items-center gap-1 text-2xl font-semibold">
            {trend === 'up' && <TrendingUp className="w-6 h-6" />}
            {trend === 'down' && <TrendingDown className="w-6 h-6" />}
            {trend === 'stable' && <Minus className="w-6 h-6" />}
            {change > 0 ? '+' : ''}{change}
          </div>
          <div className="text-sm">
            {changePct > 0 ? '+' : ''}{changePct}%
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CompareReportPage() {
  const params = useParams();
  const projectId = params.id as string;
  
  const [data, setData] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.get(`/reports/compare/${projectId}`);
        setData(res.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || '加载失败');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [projectId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-slate-400">{error || '数据加载失败'}</p>
          <Link
            href="/reports"
            className="text-primary-400 hover:text-primary-300 mt-4 inline-block"
          >
            返回报告列表
          </Link>
        </div>
      </div>
    );
  }

  const { current, previous, comparison } = data;

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Link
          href={`/reports/research/${projectId}`}
          className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          返回报告
        </Link>
        
        <h1 className="text-2xl font-bold text-white mb-2">
          {data.project_name} - 对比分析
        </h1>
        
        <div className="flex items-center gap-4 text-sm text-slate-400">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            本次: {new Date(current.report_date).toLocaleDateString('zh-CN')}
          </span>
          <span>vs</span>
          <span>
            上次: {new Date(previous.report_date).toLocaleDateString('zh-CN')}
          </span>
        </div>
      </div>

      {/* Overall Change Summary */}
      <div
        className={cn(
          'rounded-xl p-6 mb-8 border',
          comparison.overall.trend === 'up' &&
            'bg-green-500/10 border-green-500/30',
          comparison.overall.trend === 'down' &&
            'bg-red-500/10 border-red-500/30',
          comparison.overall.trend === 'stable' &&
            'bg-slate-700/30 border-slate-700/50'
        )}
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="text-lg text-slate-300 mb-1">
              综合评分变化
            </div>
            <div className="text-3xl font-bold text-white">
              {comparison.status_text}
            </div>
          </div>
          <div className="text-right">
            <div
              className={cn(
                'text-5xl font-bold',
                comparison.overall.trend === 'up' && 'text-green-400',
                comparison.overall.trend === 'down' && 'text-red-400',
                comparison.overall.trend === 'stable' && 'text-slate-400'
              )}
            >
              {comparison.overall.change > 0 ? '+' : ''}{comparison.overall.change}
            </div>
            <div className="text-slate-400">
              {comparison.overall.previous} → {comparison.overall.current}
            </div>
          </div>
        </div>
      </div>

      {/* Score Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <ScoreCompareCard
          label="AI 可见性指数 (AVI)"
          current={current.scores.avi.score}
          previous={previous.scores.avi.score}
          change={comparison.scores.avi.change}
          changePct={comparison.scores.avi.change_pct}
          trend={comparison.scores.avi.trend}
        />
        <ScoreCompareCard
          label="引用质量评分 (CQS)"
          current={current.scores.cqs.score}
          previous={previous.scores.cqs.score}
          change={comparison.scores.cqs.change}
          changePct={comparison.scores.cqs.change_pct}
          trend={comparison.scores.cqs.trend}
        />
        <ScoreCompareCard
          label="竞争定位指数 (CPI)"
          current={current.scores.cpi.score}
          previous={previous.scores.cpi.score}
          change={comparison.scores.cpi.change}
          changePct={comparison.scores.cpi.change_pct}
          trend={comparison.scores.cpi.trend}
        />
      </div>

      {/* Insights */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">分析洞察</h2>
        <div className="space-y-3">
          {comparison.insights.map((insight, idx) => (
            <div
              key={idx}
              className={cn(
                'p-4 rounded-lg border-l-4',
                insight.type === 'positive' &&
                  'bg-green-500/10 border-green-500',
                insight.type === 'negative' &&
                  'bg-red-500/10 border-red-500',
                insight.type === 'neutral' &&
                  'bg-slate-700/30 border-slate-500'
              )}
            >
              <p
                className={cn(
                  insight.type === 'positive' && 'text-green-300',
                  insight.type === 'negative' && 'text-red-300',
                  insight.type === 'neutral' && 'text-slate-300'
                )}
              >
                {insight.text}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="mt-8 flex items-center gap-4">
        <Link
          href={`/reports/research/${projectId}`}
          className="bg-primary-500 hover:bg-primary-600 text-white px-6 py-2.5 rounded-lg font-medium transition-colors"
        >
          查看完整报告
        </Link>
        <Link
          href={`/projects/${projectId}`}
          className="bg-slate-700 hover:bg-slate-600 text-white px-6 py-2.5 rounded-lg font-medium transition-colors"
        >
          返回项目
        </Link>
      </div>
    </div>
  );
}
