'use client';

import { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  BarChart,
  Bar,
} from 'recharts';
import { TrendingUp, Radar as RadarIcon, BarChart3, Loader2, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface EngineSummary {
  engine: string;
  engine_label: string;
  visibility_score: number;
  citation_rate: number;
  avg_response_time: number | null;
  total_citations: number;
  total_queries: number;
}

interface TrendDataPoint {
  date: string;
  datetime: string;
  engine: string;
  engine_label: string;
  visibility: number;
  citations: number;
  queries: number;
}

interface HealthHistoryPoint {
  date: string;
  datetime: string;
  engine: string;
  engine_label: string;
  success_rate: number;
  successful: number;
  total: number;
}

interface TrendsData {
  trend_data: TrendDataPoint[];
  engine_summaries: EngineSummary[];
  health_history: HealthHistoryPoint[];
  summary: {
    engines_tested: number;
    avg_visibility: number;
    total_citations: number;
    best_engine: string | null;
    best_engine_score: number;
    total_tasks: number;
    period_days: number;
  };
}

const ENGINE_COLORS: Record<string, string> = {
  deepseek: '#a855f7',
  kimi: '#6366f1',
  doubao: '#f97316',
  chatglm: '#10b981',
  chatgpt: '#22d3ee',
  qwen: '#3b82f6',
  perplexity: '#ec4899',
  google_sge: '#eab308',
  bing_copilot: '#06b6d4',
};

export default function ProjectTrends({ projectId }: { projectId: string }) {
  const [data, setData] = useState<TrendsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeChart, setActiveChart] = useState<'trend' | 'radar' | 'engines'>('radar');

  useEffect(() => {
    const fetchTrends = async () => {
      try {
        const res = await api.get(`/projects/${projectId}/trends`, {
          params: { days: 30 },
        });
        setData(res.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || '加载趋势数据失败');
      } finally {
        setIsLoading(false);
      }
    };
    fetchTrends();
  }, [projectId]);

  if (isLoading) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-8 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-8 text-center">
        <AlertCircle className="w-8 h-8 text-slate-600 mx-auto mb-2" />
        <p className="text-sm text-slate-400">{error || '暂无趋势数据'}</p>
      </div>
    );
  }

  const { engine_summaries, trend_data, health_history, summary } = data;

  // Prepare radar chart data
  const radarData = engine_summaries.map((e) => ({
    engine: e.engine_label,
    可见性: e.visibility_score,
    引用率: e.citation_rate,
    fullMark: 100,
  }));

  // Prepare trend line data: pivot by date with engines as columns
  const trendByDate: Record<string, Record<string, number>> = {};
  for (const point of trend_data) {
    if (!trendByDate[point.date]) {
      trendByDate[point.date] = { date: point.date as any };
    }
    trendByDate[point.date][point.engine_label] = point.visibility;
  }
  const trendChartData = Object.values(trendByDate);

  // Get unique engines for line chart
  const engines = Array.from(new Set(trend_data.map((d) => d.engine_label)));
  const engineKeys = Array.from(new Set(trend_data.map((d) => d.engine)));

  // Engine bar chart data
  const engineBarData = engine_summaries.map((e) => ({
    name: e.engine_label,
    可见性: e.visibility_score,
    引用率: e.citation_rate,
    引用数: e.total_citations,
    查询数: e.total_queries,
  }));

  const hasData = engine_summaries.length > 0;

  const chartTabs = [
    { id: 'radar' as const, label: '引擎对比', icon: RadarIcon },
    { id: 'trend' as const, label: '趋势变化', icon: TrendingUp },
    { id: 'engines' as const, label: '引擎详情', icon: BarChart3 },
  ];

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
          <div className="text-xs text-slate-500 mb-1">已测试引擎</div>
          <div className="text-2xl font-bold text-white">{summary.engines_tested}</div>
        </div>
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
          <div className="text-xs text-slate-500 mb-1">平均可见性</div>
          <div className={cn(
            'text-2xl font-bold',
            summary.avg_visibility >= 50 ? 'text-green-400' :
            summary.avg_visibility >= 20 ? 'text-yellow-400' : 'text-red-400'
          )}>
            {summary.avg_visibility}%
          </div>
        </div>
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
          <div className="text-xs text-slate-500 mb-1">品牌引用</div>
          <div className="text-2xl font-bold text-primary-400">{summary.total_citations}</div>
        </div>
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
          <div className="text-xs text-slate-500 mb-1">最佳引擎</div>
          <div className="text-lg font-bold text-white truncate">
            {summary.best_engine || '--'}
          </div>
          {summary.best_engine && (
            <div className="text-xs text-green-400">{summary.best_engine_score}%</div>
          )}
        </div>
      </div>

      {/* Charts */}
      {hasData && (
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50">
          {/* Chart Tabs */}
          <div className="flex items-center gap-1 p-4 border-b border-slate-700/50">
            {chartTabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveChart(tab.id)}
                  className={cn(
                    'inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors',
                    activeChart === tab.id
                      ? 'bg-primary-500/10 text-primary-400'
                      : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          <div className="p-4">
            {/* Radar Chart */}
            {activeChart === 'radar' && radarData.length > 0 && (
              <div className="flex flex-col items-center">
                <ResponsiveContainer width="100%" height={360}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#334155" />
                    <PolarAngleAxis
                      dataKey="engine"
                      tick={{ fill: '#94a3b8', fontSize: 12 }}
                    />
                    <PolarRadiusAxis
                      angle={90}
                      domain={[0, 100]}
                      tick={{ fill: '#64748b', fontSize: 10 }}
                    />
                    <Radar
                      name="可见性"
                      dataKey="可见性"
                      stroke="#6366f1"
                      fill="#6366f1"
                      fillOpacity={0.3}
                    />
                    <Radar
                      name="引用率"
                      dataKey="引用率"
                      stroke="#22c55e"
                      fill="#22c55e"
                      fillOpacity={0.15}
                    />
                    <Legend
                      wrapperStyle={{ fontSize: 12, color: '#94a3b8' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '8px',
                        color: '#f1f5f9',
                        fontSize: 12,
                      }}
                      formatter={(value: number) => `${value}%`}
                    />
                  </RadarChart>
                </ResponsiveContainer>
                <p className="text-xs text-slate-500 mt-2">
                  对比各 AI 引擎的品牌可见性与引用率
                </p>
              </div>
            )}

            {/* Trend Line Chart */}
            {activeChart === 'trend' && (
              <>
                {trendChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={320}>
                    <LineChart data={trendChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis
                        dataKey="date"
                        tick={{ fill: '#64748b', fontSize: 11 }}
                        axisLine={{ stroke: '#334155' }}
                      />
                      <YAxis
                        domain={[0, 100]}
                        tick={{ fill: '#64748b', fontSize: 11 }}
                        axisLine={{ stroke: '#334155' }}
                        tickFormatter={(v) => `${v}%`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1e293b',
                          border: '1px solid #334155',
                          borderRadius: '8px',
                          color: '#f1f5f9',
                          fontSize: 12,
                        }}
                        formatter={(value: number) => `${value}%`}
                      />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      {engines.map((engineLabel, i) => {
                        const engineKey = engineKeys[i] || '';
                        return (
                          <Line
                            key={engineLabel}
                            type="monotone"
                            dataKey={engineLabel}
                            stroke={ENGINE_COLORS[engineKey] || `hsl(${i * 60}, 70%, 50%)`}
                            strokeWidth={2}
                            dot={{ r: 3 }}
                            activeDot={{ r: 5 }}
                          />
                        );
                      })}
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
                    <div className="text-center">
                      <TrendingUp className="w-10 h-10 text-slate-600 mx-auto mb-2" />
                      <p>需要多次体检才能显示趋势数据</p>
                      <p className="text-xs text-slate-600 mt-1">完成至少 2 次体检后可查看变化趋势</p>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Engine Detail Bar Chart */}
            {activeChart === 'engines' && engineBarData.length > 0 && (
              <div className="space-y-4">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={engineBarData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis
                      type="number"
                      domain={[0, 100]}
                      tick={{ fill: '#64748b', fontSize: 11 }}
                      tickFormatter={(v) => `${v}%`}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={80}
                      tick={{ fill: '#94a3b8', fontSize: 12 }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '8px',
                        color: '#f1f5f9',
                        fontSize: 12,
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="可见性" fill="#6366f1" radius={[0, 4, 4, 0]} />
                    <Bar dataKey="引用率" fill="#22c55e" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                
                {/* Engine detail table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-700/50">
                        <th className="text-left py-2 px-3 text-slate-400 font-medium">引擎</th>
                        <th className="text-right py-2 px-3 text-slate-400 font-medium">可见性</th>
                        <th className="text-right py-2 px-3 text-slate-400 font-medium">引用率</th>
                        <th className="text-right py-2 px-3 text-slate-400 font-medium">品牌引用</th>
                        <th className="text-right py-2 px-3 text-slate-400 font-medium">查询数</th>
                        <th className="text-right py-2 px-3 text-slate-400 font-medium">响应时间</th>
                      </tr>
                    </thead>
                    <tbody>
                      {engine_summaries.map((e) => (
                        <tr key={e.engine} className="border-b border-slate-800/50 hover:bg-slate-700/20">
                          <td className="py-2 px-3 text-white font-medium">{e.engine_label}</td>
                          <td className={cn(
                            'py-2 px-3 text-right font-bold',
                            e.visibility_score >= 50 ? 'text-green-400' :
                            e.visibility_score >= 20 ? 'text-yellow-400' : 'text-red-400'
                          )}>
                            {e.visibility_score}%
                          </td>
                          <td className="py-2 px-3 text-right text-slate-300">{e.citation_rate}%</td>
                          <td className="py-2 px-3 text-right text-primary-400">{e.total_citations}</td>
                          <td className="py-2 px-3 text-right text-slate-400">{e.total_queries}</td>
                          <td className="py-2 px-3 text-right text-slate-400">
                            {e.avg_response_time ? `${e.avg_response_time}ms` : '--'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Health History Timeline */}
      {health_history.length > 0 && (
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-primary-400" />
            体检成功率趋势
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={health_history}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#64748b', fontSize: 11 }}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: '#64748b', fontSize: 11 }}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                  color: '#f1f5f9',
                  fontSize: 12,
                }}
                formatter={(value: number, name: string) => [`${value}%`, '成功率']}
                labelFormatter={(label) => `日期: ${label}`}
              />
              <Bar
                dataKey="success_rate"
                fill="#6366f1"
                radius={[4, 4, 0, 0]}
                name="成功率"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
