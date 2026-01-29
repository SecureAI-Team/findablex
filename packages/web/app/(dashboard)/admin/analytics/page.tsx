'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Loader2,
  TrendingUp,
  Users,
  Target,
  Zap,
  BarChart3,
  Activity,
  ArrowRight,
  RefreshCw,
  Calendar,
  AlertCircle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface FunnelStage {
  name: string;
  count: number;
  rate: number;
}

interface FunnelMetrics {
  activation_funnel: {
    stages: FunnelStage[];
    overall_rate: number;
  };
  conversion_funnel: {
    stages: FunnelStage[];
    overall_rate: number;
  };
  key_metrics: {
    total_registered: number;
    activation_rate: number;
    conversion_rate: number;
    reports_generated: number;
  };
}

interface EventCounts {
  period_days: number;
  total_events: number;
  by_event: Record<string, number>;
  by_category: {
    activation: Record<string, number>;
    value: Record<string, number>;
    conversion: Record<string, number>;
    retention: Record<string, number>;
  };
}

const eventLabels: Record<string, string> = {
  user_registered: '用户注册',
  template_selected: '选择模板',
  queries_generated: '生成查询词',
  first_answer_imported: '导入首条答案',
  first_crawl_completed: '首次爬取',
  first_report_viewed: '首次报告',
  activation_10min: '10分钟激活',
  report_viewed: '查看报告',
  report_dwell_time: '报告停留',
  report_exported: '导出报告',
  report_shared: '分享报告',
  calibration_error_clicked: '口径错误点击',
  calibration_reviewed: '口径复核',
  compare_report_viewed: '对比报告',
  upgrade_clicked: '点击升级',
  unlock_queries_clicked: '解锁问题',
  retest_compare_clicked: '复测对比',
  drift_warning_clicked: '漂移预警',
  plan_viewed: '查看套餐',
  contact_sales_clicked: '联系销售',
  contact_sales_submitted: '提交销售',
  payment_initiated: '发起支付',
  payment_completed: '完成支付',
  retest_triggered: '触发复测',
  monthly_retest: '月度复测',
  team_member_invited: '邀请成员',
  team_member_joined: '成员加入',
  project_created: '创建项目',
  login: '登录',
  workspace_created: '创建工作区',
};

const categoryLabels: Record<string, string> = {
  activation: '激活事件',
  value: '价值事件',
  conversion: '转化事件',
  retention: '留存事件',
};

const categoryColors: Record<string, string> = {
  activation: 'bg-emerald-500',
  value: 'bg-blue-500',
  conversion: 'bg-purple-500',
  retention: 'bg-orange-500',
};

export default function AnalyticsPage() {
  const [funnelMetrics, setFunnelMetrics] = useState<FunnelMetrics | null>(null);
  const [eventCounts, setEventCounts] = useState<EventCounts | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [days, setDays] = useState(30);

  const fetchData = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const [funnelRes, eventsRes] = await Promise.all([
        api.get(`/analytics/funnel?days=${days}`),
        api.get(`/analytics/events?days=${days}`),
      ]);
      
      setFunnelMetrics(funnelRes.data);
      setEventCounts(eventsRes.data);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('权限不足：仅管理员可查看分析数据');
      } else {
        setError(err.response?.data?.detail || '加载分析数据失败');
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [days]);

  const FunnelChart = ({ 
    stages, 
    title, 
    overallRate,
    color = 'primary',
  }: { 
    stages: FunnelStage[]; 
    title: string;
    overallRate: number;
    color?: 'primary' | 'purple';
  }) => {
    const colorClasses = color === 'purple' 
      ? 'bg-purple-500/20 border-purple-500/50' 
      : 'bg-primary-500/20 border-primary-500/50';
    const barColor = color === 'purple' ? 'bg-purple-500' : 'bg-primary-500';
    
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <div className={cn("px-3 py-1 rounded-full text-sm font-medium", colorClasses)}>
            总转化率 {overallRate}%
          </div>
        </div>
        
        <div className="space-y-4">
          {stages.map((stage, idx) => (
            <div key={stage.name} className="relative">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-400">{idx + 1}.</span>
                  <span className="text-sm text-white">{stage.name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-white">{stage.count}</span>
                  <span className="text-xs text-slate-400 w-12 text-right">{stage.rate}%</span>
                </div>
              </div>
              <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden">
                <div 
                  className={cn("h-full rounded-full transition-all duration-500", barColor)}
                  style={{ width: `${Math.max(stage.rate, 2)}%` }}
                />
              </div>
              {idx < stages.length - 1 && (
                <div className="absolute -bottom-3 left-4 text-slate-600">
                  <ArrowRight className="w-3 h-3 rotate-90" />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const MetricCard = ({ 
    title, 
    value, 
    unit = '',
    icon: Icon,
    color = 'primary',
  }: { 
    title: string; 
    value: number | string;
    unit?: string;
    icon: any;
    color?: 'primary' | 'emerald' | 'purple' | 'blue';
  }) => {
    const colorClasses = {
      primary: 'bg-primary-500/10 text-primary-400',
      emerald: 'bg-emerald-500/10 text-emerald-400',
      purple: 'bg-purple-500/10 text-purple-400',
      blue: 'bg-blue-500/10 text-blue-400',
    };
    
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <div className="flex items-center gap-3 mb-2">
          <div className={cn("p-2 rounded-lg", colorClasses[color])}>
            <Icon className="w-5 h-5" />
          </div>
          <span className="text-sm text-slate-400">{title}</span>
        </div>
        <div className="text-3xl font-bold text-white">
          {value}{unit && <span className="text-lg text-slate-400 ml-1">{unit}</span>}
        </div>
      </div>
    );
  };

  const EventCategoryCard = ({ 
    category, 
    events 
  }: { 
    category: string; 
    events: Record<string, number>;
  }) => {
    const sortedEvents = Object.entries(events)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 8);
    
    const totalCount = Object.values(events).reduce((a, b) => a + b, 0);
    
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className={cn("w-2 h-2 rounded-full", categoryColors[category] || 'bg-slate-500')} />
          <h3 className="text-lg font-semibold text-white">
            {categoryLabels[category] || category}
          </h3>
          <span className="text-sm text-slate-400">({totalCount} 次)</span>
        </div>
        
        {sortedEvents.length === 0 ? (
          <p className="text-sm text-slate-500">暂无数据</p>
        ) : (
          <div className="space-y-2">
            {sortedEvents.map(([event, count]) => (
              <div key={event} className="flex items-center justify-between">
                <span className="text-sm text-slate-300">
                  {eventLabels[event] || event}
                </span>
                <span className="text-sm font-medium text-white">{count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/settings"
          className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          返回设置
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-2xl font-bold text-white">数据分析</h1>
            <p className="mt-1 text-slate-400">用户行为埋点和转化漏斗分析</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-slate-400" />
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="px-3 py-1.5 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value={7}>最近 7 天</option>
                <option value={30}>最近 30 天</option>
                <option value={90}>最近 90 天</option>
              </select>
            </div>
            <button
              onClick={fetchData}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-slate-700/50 hover:bg-slate-600/50 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
              刷新
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm mb-6 flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
        </div>
      ) : funnelMetrics ? (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <MetricCard
              title="总注册用户"
              value={funnelMetrics.key_metrics.total_registered}
              icon={Users}
              color="primary"
            />
            <MetricCard
              title="激活率"
              value={funnelMetrics.key_metrics.activation_rate}
              unit="%"
              icon={Zap}
              color="emerald"
            />
            <MetricCard
              title="转化率"
              value={funnelMetrics.key_metrics.conversion_rate}
              unit="%"
              icon={Target}
              color="purple"
            />
            <MetricCard
              title="报告生成数"
              value={funnelMetrics.key_metrics.reports_generated}
              icon={BarChart3}
              color="blue"
            />
          </div>

          {/* Funnels */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <FunnelChart
              title="激活漏斗"
              stages={funnelMetrics.activation_funnel.stages}
              overallRate={funnelMetrics.activation_funnel.overall_rate}
              color="primary"
            />
            <FunnelChart
              title="转化漏斗"
              stages={funnelMetrics.conversion_funnel.stages}
              overallRate={funnelMetrics.conversion_funnel.overall_rate}
              color="purple"
            />
          </div>

          {/* Event Categories */}
          {eventCounts && (
            <>
              <div className="flex items-center gap-3 mb-4">
                <Activity className="w-5 h-5 text-slate-400" />
                <h2 className="text-lg font-semibold text-white">事件明细</h2>
                <span className="text-sm text-slate-400">
                  (共 {eventCounts.total_events} 次事件)
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <EventCategoryCard
                  category="activation"
                  events={eventCounts.by_category.activation}
                />
                <EventCategoryCard
                  category="value"
                  events={eventCounts.by_category.value}
                />
                <EventCategoryCard
                  category="conversion"
                  events={eventCounts.by_category.conversion}
                />
                <EventCategoryCard
                  category="retention"
                  events={eventCounts.by_category.retention}
                />
              </div>
            </>
          )}
        </>
      ) : null}
    </div>
  );
}
