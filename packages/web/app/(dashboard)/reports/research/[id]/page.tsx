'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Loader2,
  Download,
  Share2,
  Eye,
  Target,
  TrendingUp,
  Award,
  AlertCircle,
  CheckCircle,
  ChevronRight,
  ExternalLink,
  BarChart3,
  PieChart,
  Zap,
  Shield,
  Copy,
  Check,
  Crown,
  RotateCcw,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { analytics } from '@/lib/analytics';

interface ScoreBreakdown {
  score: number;
  breakdown: Record<string, number>;
  interpretation: string;
  details?: Record<string, any>;
}

interface Recommendation {
  priority: string;
  category: string;
  title: string;
  description: string;
  actions: string[];
  expected_impact?: string;
}

interface EngineAnalysis {
  engines: Record<string, {
    coverage_rate: number;
    citation_rate: number;
    score: number;
    total_queries: number;
    brand_mentions: number;
  }>;
  best_engine: string | null;
  worst_engine: string | null;
}

interface QueryAnalysis {
  queries: Array<{
    query_id: string;
    query_text: string;
    effectiveness_score: number;
    brand_citations: number;
    total_citations: number;
  }>;
  best_performing: Array<any>;
  avg_effectiveness: number;
}

interface CompetitorAnalysis {
  top_competitors: Array<{
    domain: string;
    citations: number;
    threat_level: string;
  }>;
  total_competitor_domains: number;
}

interface QueryDistribution {
  by_stage: Record<string, { count: number; visibility_rate: number }>;
  by_risk: Record<string, { count: number; visibility_rate: number }>;
  by_role: Record<string, { count: number; visibility_rate: number }>;
  problem_areas: string[];
}

interface TopCitationSources {
  sources: Array<{
    domain: string;
    citations: number;
    share: number;
    avg_position: number;
  }>;
  total_sources: number;
  concentration_index: number;
  insights: string[];
}

interface CalibrationSummary {
  total_errors: number;
  by_severity: Record<string, number>;
  has_critical: boolean;
  attention_needed: boolean;
  summary_message: string;
}

interface DriftWarning {
  has_warning: boolean;
  warning_level: string | null;
  days_since_last_update: number;
  message: string;
}

interface ResearchReport {
  report_type: string;
  title: string;
  project_id: string;
  project_name: string;
  generated_at: string;
  summary: {
    overall_score: number;
    status: string;
    total_queries: number;
    total_results: number;
    target_domains: string[];
  };
  scores: {
    avi: ScoreBreakdown;
    cqs: ScoreBreakdown;
    cpi: ScoreBreakdown;
  };
  engine_analysis: EngineAnalysis;
  query_analysis: QueryAnalysis;
  competitor_analysis: CompetitorAnalysis;
  recommendations: Recommendation[];
  // New fields from backend
  query_distribution?: QueryDistribution;
  top_citation_sources?: TopCitationSources;
  calibration_summary?: CalibrationSummary;
  drift_warning?: DriftWarning;
  metadata?: {
    next_retest_date?: string;
    report_version?: string;
  };
}

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

export default function ResearchReportPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [report, setReport] = useState<ResearchReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showShareModal, setShowShareModal] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchReport();
  }, [projectId]);

  const fetchReport = async () => {
    try {
      setIsLoading(true);
      const res = await api.get(`/reports/research/${projectId}`);
      setReport(res.data);
      
      // Track report view
      analytics.trackReportViewed(projectId, 'research');
    } catch (err: any) {
      console.error('Failed to fetch research report:', err);
      setError('获取报告失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExport = async (format: 'json' | 'html') => {
    try {
      const res = await api.get(`/reports/research/${projectId}/export`, {
        params: { format },
        responseType: 'blob',
      });
      
      const blob = new Blob([res.data]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `research_report_${projectId}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Failed to export report:', err);
    }
  };

  const handlePrintReport = async () => {
    // 获取 HTML 报告并在新窗口打开
    try {
      const res = await api.get(`/reports/research/${projectId}/export`, {
        params: { format: 'html' },
        responseType: 'text',
      });
      
      // 创建新窗口并写入 HTML
      const printWindow = window.open('', '_blank');
      if (printWindow) {
        printWindow.document.write(res.data);
        printWindow.document.close();
      }
    } catch (err) {
      console.error('Failed to open print view:', err);
    }
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    if (score >= 40) return 'text-orange-400';
    return 'text-red-400';
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return 'from-green-500/20 to-green-500/5';
    if (score >= 60) return 'from-yellow-500/20 to-yellow-500/5';
    if (score >= 40) return 'from-orange-500/20 to-orange-500/5';
    return 'from-red-500/20 to-red-500/5';
  };

  const getPriorityConfig = (priority: string) => {
    switch (priority) {
      case 'critical':
        return { color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30', label: '紧急' };
      case 'high':
        return { color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/30', label: '高优' };
      case 'medium':
        return { color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30', label: '中等' };
      default:
        return { color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/30', label: '建议' };
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <AlertCircle className="w-12 h-12 text-red-400" />
        <p className="text-slate-300">{error || '报告不存在'}</p>
        <Link
          href="/reports"
          className="text-primary-400 hover:text-primary-300"
        >
          返回报告列表
        </Link>
      </div>
    );
  }

  const { summary, scores, engine_analysis, query_analysis, competitor_analysis, recommendations } = report;

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <Link
            href="/reports"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            返回报告列表
          </Link>
          <h1 className="font-display text-2xl font-bold text-white flex items-center gap-3">
            <BarChart3 className="w-7 h-7 text-primary-400" />
            {report.title}
          </h1>
          <p className="mt-1 text-slate-400">
            生成于 {formatDate(report.generated_at)} · {report.project_name}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* 复测按钮 */}
          <Link
            href={`/projects/${projectId}/import`}
            className="inline-flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-4 py-2.5 rounded-lg font-medium transition-all"
          >
            <RotateCcw className="w-5 h-5" />
            复测
          </Link>
          <button
            onClick={() => setShowShareModal(true)}
            className="inline-flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-4 py-2.5 rounded-lg font-medium transition-all"
          >
            <Share2 className="w-5 h-5" />
            分享
          </button>
          <div className="relative group">
            <button className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2.5 rounded-lg font-medium transition-all">
              <Download className="w-5 h-5" />
              导出
            </button>
            <div className="absolute right-0 mt-2 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
              <button
                onClick={() => handleExport('json')}
                className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 hover:text-white rounded-t-lg"
              >
                导出 JSON 数据
              </button>
              <button
                onClick={() => handleExport('html')}
                className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 hover:text-white"
              >
                下载 HTML 报告
              </button>
              <button
                onClick={handlePrintReport}
                className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 hover:text-white rounded-b-lg"
              >
                打印 / 导出 PDF
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 综合评分卡片 */}
      <div className={cn(
        'bg-gradient-to-br rounded-2xl p-8 border border-slate-700/50',
        getScoreBg(summary.overall_score)
      )}>
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-8">
          <div className="flex items-center gap-8">
            <div className="text-center">
              <div className={cn('text-7xl font-bold', getScoreColor(summary.overall_score))}>
                {summary.overall_score}
              </div>
              <div className="text-slate-400 text-sm mt-1">综合评分</div>
            </div>
            <div className="w-px h-20 bg-slate-700/50 hidden lg:block" />
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                {summary.overall_score >= 60 ? (
                  <CheckCircle className="w-5 h-5 text-green-400" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-yellow-400" />
                )}
                <span className={cn('font-medium text-lg', getScoreColor(summary.overall_score))}>
                  {summary.status === 'excellent' ? '优秀' : 
                   summary.status === 'good' ? '良好' : 
                   summary.status === 'fair' ? '一般' : '需改进'}
                </span>
              </div>
              <div className="text-slate-400 text-sm">
                分析了 {summary.total_queries} 个查询词，{summary.total_results} 条爬虫结果
              </div>
            </div>
          </div>
          
          {summary.target_domains.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {summary.target_domains.map((domain) => (
                <span
                  key={domain}
                  className="px-3 py-1 bg-primary-500/20 text-primary-300 text-sm rounded-full"
                >
                  {domain}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 三大指标 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* AVI */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Eye className="w-5 h-5 text-blue-400" />
              <span className="text-slate-400 text-sm">AI 可见性指数</span>
            </div>
            <span className="text-xs text-slate-500">AVI</span>
          </div>
          <div className={cn('text-4xl font-bold mb-2', getScoreColor(scores.avi.score))}>
            {scores.avi.score}
          </div>
          <p className="text-slate-400 text-sm mb-4">{scores.avi.interpretation}</p>
          <div className="space-y-2">
            {Object.entries(scores.avi.breakdown || {}).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-sm">
                <span className="text-slate-500">
                  {key === 'citation_rate' ? '引用率' :
                   key === 'position_score' ? '位置分' :
                   key === 'engine_coverage' ? '引擎覆盖' :
                   key === 'consistency_score' ? '一致性' : key}
                </span>
                <span className="text-white">{value}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* CQS */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Award className="w-5 h-5 text-purple-400" />
              <span className="text-slate-400 text-sm">引用质量评分</span>
            </div>
            <span className="text-xs text-slate-500">CQS</span>
          </div>
          <div className={cn('text-4xl font-bold mb-2', getScoreColor(scores.cqs.score))}>
            {scores.cqs.score}
          </div>
          <p className="text-slate-400 text-sm mb-4">{scores.cqs.interpretation}</p>
          {scores.cqs.breakdown && (
            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-white">
                  {scores.cqs.breakdown.total_brand_citations || 0}
                </div>
                <div className="text-xs text-slate-500">品牌引用数</div>
              </div>
            </div>
          )}
        </div>

        {/* CPI */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Target className="w-5 h-5 text-green-400" />
              <span className="text-slate-400 text-sm">竞争定位指数</span>
            </div>
            <span className="text-xs text-slate-500">CPI</span>
          </div>
          <div className={cn('text-4xl font-bold mb-2', getScoreColor(scores.cpi.score))}>
            {scores.cpi.score}
          </div>
          <p className="text-slate-400 text-sm mb-4">{scores.cpi.interpretation}</p>
          <div className="space-y-2">
            {Object.entries(scores.cpi.breakdown || {}).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-sm">
                <span className="text-slate-500">
                  {key === 'share_of_voice' ? '市场声量' :
                   key === 'ranking_score' ? '排名分数' :
                   key === 'dominance_score' ? '主导力' : key}
                </span>
                <span className="text-white">{value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 引擎覆盖分析 */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
        <div className="p-6 border-b border-slate-700/50">
          <h2 className="font-display text-lg font-semibold text-white flex items-center gap-2">
            <PieChart className="w-5 h-5 text-primary-400" />
            AI 引擎覆盖分析
          </h2>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {Object.entries(engine_analysis.engines || {}).map(([engine, data]) => (
              <div
                key={engine}
                className={cn(
                  'p-4 rounded-lg border',
                  engine === engine_analysis.best_engine
                    ? 'bg-green-500/10 border-green-500/30'
                    : engine === engine_analysis.worst_engine
                    ? 'bg-red-500/10 border-red-500/30'
                    : 'bg-slate-700/30 border-slate-600/30'
                )}
              >
                <div className="text-white font-medium mb-2">
                  {engineNames[engine] || engine}
                </div>
                <div className={cn('text-2xl font-bold', getScoreColor(data.score))}>
                  {data.score}
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  覆盖率 {data.coverage_rate}%
                </div>
                <div className="text-xs text-slate-500">
                  品牌引用 {data.brand_mentions}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 竞争对手分析 */}
      {competitor_analysis.top_competitors.length > 0 && (
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
          <div className="p-6 border-b border-slate-700/50">
            <h2 className="font-display text-lg font-semibold text-white flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary-400" />
              竞争格局分析
            </h2>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              {competitor_analysis.top_competitors.slice(0, 5).map((comp, idx) => (
                <div
                  key={comp.domain}
                  className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-slate-500 text-sm w-6">{idx + 1}</span>
                    <span className="text-white">{comp.domain}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-slate-400 text-sm">{comp.citations} 次引用</span>
                    <span className={cn(
                      'px-2 py-0.5 rounded text-xs',
                      comp.threat_level === 'high' ? 'bg-red-500/20 text-red-400' :
                      comp.threat_level === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-green-500/20 text-green-400'
                    )}>
                      {comp.threat_level === 'high' ? '高威胁' :
                       comp.threat_level === 'medium' ? '中等' : '低威胁'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 text-sm text-slate-500">
              共发现 {competitor_analysis.total_competitor_domains} 个竞争域名
            </div>
          </div>
        </div>
      )}

      {/* 优化建议 */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
        <div className="p-6 border-b border-slate-700/50">
          <h2 className="font-display text-lg font-semibold text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary-400" />
            优化建议
          </h2>
        </div>
        <div className="divide-y divide-slate-700/50">
          {recommendations.map((rec, idx) => {
            const config = getPriorityConfig(rec.priority);
            return (
              <div key={idx} className={cn('p-6', config.bg, 'border-l-4')}>
                <div className="flex items-start justify-between gap-4 mb-3">
                  <h3 className="font-medium text-white text-lg">{rec.title}</h3>
                  <span className={cn('px-2 py-0.5 rounded text-xs font-medium', config.color, 'bg-slate-800/50')}>
                    {config.label}
                  </span>
                </div>
                <p className="text-slate-400 mb-4">{rec.description}</p>
                <div className="space-y-2">
                  {rec.actions.map((action, actionIdx) => (
                    <div key={actionIdx} className="flex items-start gap-2 text-sm text-slate-300">
                      <div className="w-1.5 h-1.5 rounded-full bg-primary-500 mt-2 flex-shrink-0" />
                      {action}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top 引用来源 */}
      {report.top_citation_sources?.sources && report.top_citation_sources.sources.length > 0 && (
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
          <div className="p-6 border-b border-slate-700/50">
            <h2 className="font-display text-lg font-semibold text-white flex items-center gap-2">
              <ExternalLink className="w-5 h-5 text-primary-400" />
              Top 引用来源
            </h2>
            <p className="text-slate-400 text-sm mt-1">谁在定义行业叙事</p>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              {report.top_citation_sources.sources.slice(0, 10).map((source, idx) => (
                <div
                  key={source.domain}
                  className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-slate-500 text-sm w-6">{idx + 1}</span>
                    <span className="text-white">{source.domain}</span>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-slate-400">{source.citations} 次引用</span>
                    <span className="text-primary-400">{(source.share * 100).toFixed(1)}%</span>
                  </div>
                </div>
              ))}
            </div>
            {report.top_citation_sources.insights && report.top_citation_sources.insights.length > 0 && (
              <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <div className="text-sm text-blue-300">
                  {report.top_citation_sources.insights.map((insight, i) => (
                    <p key={i} className="mb-1">• {insight}</p>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 问题集分布 */}
      {report.query_distribution && (
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
          <div className="p-6 border-b border-slate-700/50">
            <h2 className="font-display text-lg font-semibold text-white flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-primary-400" />
              问题集分布
            </h2>
            <p className="text-slate-400 text-sm mt-1">哪类问题你强，哪类问题缺席</p>
          </div>
          <div className="p-6">
            <div className="grid md:grid-cols-3 gap-6">
              {/* 按阶段 */}
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-3">按购买阶段</h3>
                <div className="space-y-2">
                  {Object.entries(report.query_distribution.by_stage || {}).map(([stage, data]) => (
                    <div key={stage} className="flex items-center justify-between text-sm">
                      <span className="text-slate-400">
                        {stage === 'awareness' ? '认知' :
                         stage === 'consideration' ? '考虑' :
                         stage === 'decision' ? '决策' :
                         stage === 'retention' ? '留存' :
                         stage === 'unknown' ? '未分类' : stage}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500">{data.count} 条</span>
                        <span className={cn(
                          'font-medium',
                          data.visibility_rate >= 70 ? 'text-green-400' :
                          data.visibility_rate >= 40 ? 'text-yellow-400' : 'text-red-400'
                        )}>
                          {data.visibility_rate.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 按风险 */}
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-3">按风险等级</h3>
                <div className="space-y-2">
                  {Object.entries(report.query_distribution.by_risk || {}).map(([risk, data]) => (
                    <div key={risk} className="flex items-center justify-between text-sm">
                      <span className={cn(
                        'text-slate-400',
                        risk === 'critical' && 'text-red-400',
                        risk === 'high' && 'text-orange-400'
                      )}>
                        {risk === 'critical' ? '关键' :
                         risk === 'high' ? '高风险' :
                         risk === 'medium' ? '中风险' :
                         risk === 'low' ? '低风险' :
                         risk === 'unknown' ? '未分类' : risk}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500">{data.count} 条</span>
                        <span className={cn(
                          'font-medium',
                          data.visibility_rate >= 70 ? 'text-green-400' :
                          data.visibility_rate >= 40 ? 'text-yellow-400' : 'text-red-400'
                        )}>
                          {data.visibility_rate.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 按角色 */}
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-3">按目标角色</h3>
                <div className="space-y-2">
                  {Object.entries(report.query_distribution.by_role || {}).map(([role, data]) => (
                    <div key={role} className="flex items-center justify-between text-sm">
                      <span className="text-slate-400">
                        {role === 'marketing' ? '市场' :
                         role === 'sales' ? '销售' :
                         role === 'compliance' ? '合规' :
                         role === 'technical' ? '技术' :
                         role === 'management' ? '管理层' :
                         role === 'unknown' ? '未分类' : role}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500">{data.count} 条</span>
                        <span className={cn(
                          'font-medium',
                          data.visibility_rate >= 70 ? 'text-green-400' :
                          data.visibility_rate >= 40 ? 'text-yellow-400' : 'text-red-400'
                        )}>
                          {data.visibility_rate.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* 问题区域 */}
            {report.query_distribution.problem_areas && report.query_distribution.problem_areas.length > 0 && (
              <div className="mt-6 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <h4 className="text-sm font-medium text-amber-300 mb-2">需关注的问题区域</h4>
                <div className="text-sm text-amber-200/80">
                  {report.query_distribution.problem_areas.map((area, i) => (
                    <p key={i}>• {area}</p>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 口径错误清单 */}
      {report.calibration_summary && report.calibration_summary.total_errors > 0 && (
        <div className={cn(
          'rounded-xl border overflow-hidden',
          report.calibration_summary.has_critical
            ? 'bg-red-900/20 border-red-500/30'
            : 'bg-slate-800/50 border-slate-700/50'
        )}>
          <div className="p-6 border-b border-slate-700/50">
            <h2 className="font-display text-lg font-semibold text-white flex items-center gap-2">
              <AlertCircle className={cn(
                'w-5 h-5',
                report.calibration_summary.has_critical ? 'text-red-400' : 'text-amber-400'
              )} />
              口径错误清单
            </h2>
            <p className="text-slate-400 text-sm mt-1">AI 把你说错了什么？</p>
          </div>
          <div className="p-6">
            <div className="flex items-center gap-6 mb-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-white">{report.calibration_summary.total_errors}</div>
                <div className="text-xs text-slate-500">总错误数</div>
              </div>
              {Object.entries(report.calibration_summary.by_severity || {}).map(([severity, count]) => (
                count > 0 && (
                  <div key={severity} className="text-center">
                    <div className={cn(
                      'text-2xl font-bold',
                      severity === 'critical' ? 'text-red-400' :
                      severity === 'high' ? 'text-orange-400' :
                      severity === 'medium' ? 'text-yellow-400' : 'text-slate-400'
                    )}>
                      {count}
                    </div>
                    <div className="text-xs text-slate-500">
                      {severity === 'critical' ? '严重' :
                       severity === 'high' ? '高' :
                       severity === 'medium' ? '中' : '低'}
                    </div>
                  </div>
                )
              ))}
            </div>
            <p className="text-slate-400 text-sm">{report.calibration_summary.summary_message}</p>
            <Link
              href={`/calibration/${projectId}`}
              className="inline-flex items-center gap-1 mt-4 text-sm text-primary-400 hover:text-primary-300"
            >
              查看详细口径错误
              <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      )}

      {/* 漂移预警 / 复测日期 */}
      {(report.drift_warning?.has_warning || report.metadata?.next_retest_date) && (
        <div className={cn(
          'rounded-xl border p-6',
          report.drift_warning?.warning_level === 'critical'
            ? 'bg-red-900/20 border-red-500/30'
            : report.drift_warning?.warning_level === 'high'
            ? 'bg-amber-900/20 border-amber-500/30'
            : 'bg-slate-800/50 border-slate-700/50'
        )}>
          <div className="flex items-start justify-between">
            <div>
              {report.drift_warning?.has_warning && (
                <div className="flex items-center gap-2 mb-2">
                  <AlertCircle className={cn(
                    'w-5 h-5',
                    report.drift_warning.warning_level === 'critical' ? 'text-red-400' :
                    report.drift_warning.warning_level === 'high' ? 'text-amber-400' : 'text-slate-400'
                  )} />
                  <span className={cn(
                    'font-medium',
                    report.drift_warning.warning_level === 'critical' ? 'text-red-300' :
                    report.drift_warning.warning_level === 'high' ? 'text-amber-300' : 'text-slate-300'
                  )}>
                    漂移预警
                  </span>
                </div>
              )}
              <p className="text-slate-400 text-sm">
                {report.drift_warning?.message || '定期复测可追踪引擎漂移和竞品动态'}
              </p>
            </div>
            {report.metadata?.next_retest_date && (
              <div className="text-right">
                <div className="text-xs text-slate-500">建议复测日期</div>
                <div className="text-white font-medium">
                  {new Date(report.metadata.next_retest_date).toLocaleDateString('zh-CN')}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 升级提示 */}
      <div className="bg-gradient-to-r from-amber-500/10 via-orange-500/10 to-amber-500/10 rounded-xl border border-amber-500/20 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center flex-shrink-0">
              <Crown className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-white mb-1">
                解锁更多问题条数和复测对比
              </h3>
              <p className="text-slate-400 text-sm">
                升级到 Pro 版可追踪 100 条关键问题、查看月度复测对比、获取漂移预警通知
              </p>
            </div>
          </div>
          <Link
            href="/subscription"
            className="inline-flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-white px-5 py-2.5 rounded-lg font-medium transition-all whitespace-nowrap"
            onClick={() => analytics.trackUpgradeClicked('research_report_page')}
          >
            升级方案
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* 查看项目链接 */}
      <div className="text-center">
        <Link
          href={`/projects/${projectId}`}
          className="inline-flex items-center gap-2 text-primary-400 hover:text-primary-300 transition-colors"
        >
          查看项目详情
          <ChevronRight className="w-4 h-4" />
        </Link>
      </div>

      {/* 分享弹窗 */}
      {showShareModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setShowShareModal(false)}
          />
          <div className="relative bg-slate-800 rounded-2xl border border-slate-700 p-6 w-full max-w-md">
            <h3 className="font-display text-lg font-semibold text-white mb-4">
              分享报告
            </h3>
            <p className="text-slate-400 text-sm mb-4">
              复制以下链接分享此研究报告
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                readOnly
                value={window.location.href}
                className="flex-1 px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm"
              />
              <button
                onClick={handleCopyLink}
                className="px-4 py-2.5 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-all flex items-center gap-2"
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4" />
                    已复制
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    复制
                  </>
                )}
              </button>
            </div>
            <button
              onClick={() => setShowShareModal(false)}
              className="mt-4 w-full px-4 py-2 text-slate-400 hover:text-white transition-colors text-sm"
            >
              关闭
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
