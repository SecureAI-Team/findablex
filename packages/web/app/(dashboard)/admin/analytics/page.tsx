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
  Eye,
  UserCheck,
  Globe,
  FileText,
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

interface TrafficMetrics {
  summary: {
    total_pv: number;
    total_uv: number;
    today_dau: number;
    avg_daily_pv: number;
    avg_daily_uv: number;
    avg_daily_dau: number;
  };
  trends: {
    daily_pv: Array<{ date: string; pv: number }>;
    daily_uv: Array<{ date: string; uv: number }>;
    daily_dau: Array<{ date: string; dau: number }>;
  };
  top_pages: Array<{ page: string; count: number }>;
  period_days: number;
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
  const [trafficMetrics, setTrafficMetrics] = useState<TrafficMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [days, setDays] = useState(30);
  const [activeTab, setActiveTab] = useState<'traffic' | 'funnel' | 'events'>('traffic');

  // 获取用户时区偏移（小时）
  const getTzOffset = () => {
    // getTimezoneOffset() 返回分钟，且符号相反（UTC+8 返回 -480）
    const offsetMinutes = new Date().getTimezoneOffset();
    return -Math.round(offsetMinutes / 60);
  };

  const fetchData = async () => {
    setIsLoading(true);
    setError('');
    
    const tzOffset = getTzOffset();
    
    try {
      const [funnelRes, eventsRes, trafficRes] = await Promise.all([
        api.get(`/analytics/funnel?days=${days}&tz_offset=${tzOffset}`),
        api.get(`/analytics/events?days=${days}&tz_offset=${tzOffset}`),
        api.get(`/analytics/traffic?days=${days}&tz_offset=${tzOffset}`),
      ]);
      
      setFunnelMetrics(funnelRes.data);
      setEventCounts(eventsRes.data);
      setTrafficMetrics(trafficRes.data);
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

  // 简易折线图组件
  const MiniLineChart = ({ 
    data, 
    dataKey,
    color = 'primary',
    height = 60,
  }: { 
    data: Array<{ date: string; [key: string]: any }>;
    dataKey: string;
    color?: 'primary' | 'emerald' | 'blue';
    height?: number;
  }) => {
    if (!data || data.length === 0) {
      return (
        <div className="flex items-center justify-center text-slate-500 text-sm" style={{ height }}>
          暂无数据
        </div>
      );
    }
    
    const values = data.map(d => d[dataKey] || 0);
    const max = Math.max(...values, 1);
    const min = Math.min(...values);
    const range = max - min || 1;
    
    const colorClasses = {
      primary: 'stroke-primary-500',
      emerald: 'stroke-emerald-500',
      blue: 'stroke-blue-500',
    };
    
    const fillClasses = {
      primary: 'fill-primary-500/20',
      emerald: 'fill-emerald-500/20',
      blue: 'fill-blue-500/20',
    };
    
    const width = 100;
    const points = data.map((d, i) => {
      const x = (i / (data.length - 1 || 1)) * width;
      const y = height - ((d[dataKey] - min) / range) * (height - 10) - 5;
      return `${x},${y}`;
    }).join(' ');
    
    const areaPoints = `0,${height} ${points} ${width},${height}`;
    
    return (
      <svg 
        viewBox={`0 0 ${width} ${height}`} 
        className="w-full" 
        style={{ height }}
        preserveAspectRatio="none"
      >
        <polygon points={areaPoints} className={fillClasses[color]} />
        <polyline
          points={points}
          fill="none"
          className={colorClasses[color]}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  };

  // 流量指标卡片
  const TrafficCard = ({
    title,
    value,
    avgValue,
    trendData,
    dataKey,
    icon: Icon,
    color = 'primary',
  }: {
    title: string;
    value: number;
    avgValue: number;
    trendData: Array<{ date: string; [key: string]: any }>;
    dataKey: string;
    icon: any;
    color?: 'primary' | 'emerald' | 'blue';
  }) => {
    const colorClasses = {
      primary: 'bg-primary-500/10 text-primary-400',
      emerald: 'bg-emerald-500/10 text-emerald-400',
      blue: 'bg-blue-500/10 text-blue-400',
    };
    
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={cn("p-2 rounded-lg", colorClasses[color])}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <span className="text-sm text-slate-400">{title}</span>
              <div className="text-2xl font-bold text-white">{value.toLocaleString()}</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-slate-500">日均</div>
            <div className="text-lg font-semibold text-slate-300">{avgValue}</div>
          </div>
        </div>
        <MiniLineChart data={trendData} dataKey={dataKey} color={color} />
      </div>
    );
  };

  // 热门页面列表
  const TopPagesCard = ({ 
    pages 
  }: { 
    pages: Array<{ page: string; count: number }>;
  }) => {
    const pageLabels: Record<string, string> = {
      'dashboard': '仪表板',
      'projects': '项目列表',
      'reports': '报告',
      'settings': '设置',
      'team': '团队',
      'admin_users': '用户管理',
      'admin_analytics': '数据分析',
      'admin_audit': '审计日志',
      'landing': '首页',
      'articles': '资讯中心',
      'pricing': '定价',
      'research_center': '研究中心',
    };
    
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <div className="flex items-center gap-3 mb-4">
          <FileText className="w-5 h-5 text-slate-400" />
          <h3 className="text-lg font-semibold text-white">热门页面</h3>
        </div>
        
        {pages.length === 0 ? (
          <p className="text-sm text-slate-500">暂无数据</p>
        ) : (
          <div className="space-y-3">
            {pages.slice(0, 10).map((page, idx) => (
              <div key={page.page} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="w-5 h-5 flex items-center justify-center text-xs font-medium text-slate-500 bg-slate-700/50 rounded">
                    {idx + 1}
                  </span>
                  <span className="text-sm text-slate-300">
                    {pageLabels[page.page] || page.page}
                  </span>
                </div>
                <span className="text-sm font-medium text-white">{page.count}</span>
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
            <p className="mt-1 text-slate-400">流量监测、用户行为和转化漏斗分析</p>
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

      {/* Tab Navigation */}
      <div className="flex gap-1 p-1 bg-slate-800/50 rounded-lg border border-slate-700/50 mb-8 w-fit">
        <button
          onClick={() => setActiveTab('traffic')}
          className={cn(
            "px-4 py-2 rounded-md text-sm font-medium transition-all",
            activeTab === 'traffic'
              ? "bg-primary-500 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-700/50"
          )}
        >
          <span className="flex items-center gap-2">
            <Globe className="w-4 h-4" />
            流量概览
          </span>
        </button>
        <button
          onClick={() => setActiveTab('funnel')}
          className={cn(
            "px-4 py-2 rounded-md text-sm font-medium transition-all",
            activeTab === 'funnel'
              ? "bg-primary-500 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-700/50"
          )}
        >
          <span className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            转化漏斗
          </span>
        </button>
        <button
          onClick={() => setActiveTab('events')}
          className={cn(
            "px-4 py-2 rounded-md text-sm font-medium transition-all",
            activeTab === 'events'
              ? "bg-primary-500 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-700/50"
          )}
        >
          <span className="flex items-center gap-2">
            <Activity className="w-4 h-4" />
            事件明细
          </span>
        </button>
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
      ) : (
        <>
          {/* Traffic Tab */}
          {activeTab === 'traffic' && trafficMetrics && (
            <>
              {/* PV/UV/DAU Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <TrafficCard
                  title="页面浏览量 (PV)"
                  value={trafficMetrics.summary.total_pv}
                  avgValue={trafficMetrics.summary.avg_daily_pv}
                  trendData={trafficMetrics.trends.daily_pv}
                  dataKey="pv"
                  icon={Eye}
                  color="primary"
                />
                <TrafficCard
                  title="独立访客 (UV)"
                  value={trafficMetrics.summary.total_uv}
                  avgValue={trafficMetrics.summary.avg_daily_uv}
                  trendData={trafficMetrics.trends.daily_uv}
                  dataKey="uv"
                  icon={Users}
                  color="emerald"
                />
                <TrafficCard
                  title="今日活跃用户 (DAU)"
                  value={trafficMetrics.summary.today_dau}
                  avgValue={trafficMetrics.summary.avg_daily_dau}
                  trendData={trafficMetrics.trends.daily_dau}
                  dataKey="dau"
                  icon={UserCheck}
                  color="blue"
                />
              </div>

              {/* Top Pages & Key Metrics */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <TopPagesCard pages={trafficMetrics.top_pages} />
                
                {/* Quick Stats from Funnel */}
                {funnelMetrics && (
                  <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <BarChart3 className="w-5 h-5 text-slate-400" />
                      <h3 className="text-lg font-semibold text-white">关键指标</h3>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 bg-slate-700/30 rounded-lg">
                        <div className="text-sm text-slate-400 mb-1">总注册用户</div>
                        <div className="text-2xl font-bold text-white">
                          {funnelMetrics.key_metrics.total_registered}
                        </div>
                      </div>
                      <div className="p-4 bg-slate-700/30 rounded-lg">
                        <div className="text-sm text-slate-400 mb-1">激活率</div>
                        <div className="text-2xl font-bold text-emerald-400">
                          {funnelMetrics.key_metrics.activation_rate}%
                        </div>
                      </div>
                      <div className="p-4 bg-slate-700/30 rounded-lg">
                        <div className="text-sm text-slate-400 mb-1">转化率</div>
                        <div className="text-2xl font-bold text-purple-400">
                          {funnelMetrics.key_metrics.conversion_rate}%
                        </div>
                      </div>
                      <div className="p-4 bg-slate-700/30 rounded-lg">
                        <div className="text-sm text-slate-400 mb-1">报告生成数</div>
                        <div className="text-2xl font-bold text-blue-400">
                          {funnelMetrics.key_metrics.reports_generated}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Funnel Tab */}
          {activeTab === 'funnel' && funnelMetrics && (
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
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
            </>
          )}

          {/* Events Tab */}
          {activeTab === 'events' && eventCounts && (
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
      )}
    </div>
  );
}
