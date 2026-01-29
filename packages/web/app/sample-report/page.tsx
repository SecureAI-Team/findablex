'use client';

import Link from 'next/link';
import {
  ArrowLeft,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  FileText,
  Download,
  Share2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Note: 由于是 'use client'，metadata 需要在单独的 layout 或通过 generateMetadata 导出
// 这里通过 Head 组件或父级 layout 处理 SEO

// 样例报告数据 - 与正式报告模板对齐
const sampleReport = {
  projectName: 'Acme 网络安全',
  overallScore: 72,
  generatedAt: '2026-01-26',
  reportId: 'FX-A7B3C2D1',
  scores: {
    avi: { score: 68, label: 'AI 可见性指数 (AVI)', description: '品牌在 AI 引擎中被提及的覆盖程度' },
    cqs: { score: 75, label: '引用质量评分 (CQS)', description: '引用来源的权威性和相关性评估' },
    cpi: { score: 74, label: '竞争定位指数 (CPI)', description: '相对竞争对手的可见性优势' },
  },
  engineCoverage: [
    { engine: 'ChatGPT', coverage: 85, trend: 'up', queries: 45, citations: 38 },
    { engine: 'Perplexity', coverage: 72, trend: 'stable', queries: 45, citations: 32 },
    { engine: 'DeepSeek', coverage: 78, trend: 'up', queries: 45, citations: 35 },
    { engine: '通义千问', coverage: 65, trend: 'up', queries: 45, citations: 29 },
    { engine: 'Kimi', coverage: 62, trend: 'stable', queries: 45, citations: 28 },
  ],
  topCompetitors: [
    { name: '深信服', score: 82, citations: 156, share: '28%' },
    { name: '奇安信', score: 78, citations: 134, share: '24%' },
    { name: 'Acme', score: 72, citations: 98, isYou: true, share: '18%' },
    { name: '启明星辰', score: 65, citations: 87, share: '16%' },
  ],
  topCitationSources: [
    { domain: 'freebuf.com', count: 23, title: 'FreeBuf 安全社区' },
    { domain: 'secrss.com', count: 18, title: '安全内参' },
    { domain: 'anquanke.com', count: 15, title: '安全客' },
    { domain: 'acme-security.com', count: 12, title: 'Acme 官网', isYou: true },
    { domain: '36kr.com', count: 9, title: '36氪' },
  ],
  queryDistribution: {
    byStage: [
      { stage: '认知阶段', count: 18, percentage: 40 },
      { stage: '考虑阶段', count: 15, percentage: 33 },
      { stage: '决策阶段', count: 12, percentage: 27 },
    ],
    byRisk: [
      { level: '低风险', count: 28, percentage: 62 },
      { level: '中风险', count: 12, percentage: 27 },
      { level: '高风险', count: 5, percentage: 11 },
    ],
  },
  calibrationErrors: [
    { query: '工业网络安全解决方案', error: '将 Acme 描述为"美国公司"，实为中国本土企业', severity: 'high' },
    { query: '零信任架构厂商', error: '未提及 Acme 的零信任产品线', severity: 'medium' },
  ],
  driftWarning: {
    hasWarning: true,
    message: '近7天可见性下降趋势',
    change: -5,
    affectedEngines: ['Google SGE'],
  },
  insights: [
    { type: 'positive', text: 'ChatGPT 中的引用率较上月提升了 12%' },
    { type: 'positive', text: '品牌在"网络安全最佳实践"相关问题中表现优秀' },
    { type: 'warning', text: 'Google SGE 中的可见性下降 5%，需要关注' },
    { type: 'warning', text: '检测到 2 处口径错误需要修正' },
    { type: 'info', text: '建议优化"零信任架构"相关内容以提升覆盖' },
  ],
  recommendations: [
    {
      priority: 'high',
      title: '修正口径错误',
      description: 'AI 引擎存在关于品牌的错误描述，可能影响用户认知',
      actions: ['联系 AI 平台提交纠错反馈', '在官网强化正确信息展示'],
    },
    {
      priority: 'high',
      title: '优化技术白皮书',
      description: '当前技术内容在 AI 引擎中的引用率较低',
      actions: ['添加更多结构化数据和 Schema 标记', '增加权威第三方引用来源'],
    },
    {
      priority: 'medium',
      title: '增加案例研究',
      description: 'AI 引擎倾向于引用具体案例',
      actions: ['发布更多客户成功案例', '在行业媒体投放案例内容'],
    },
    {
      priority: 'medium',
      title: '提升权威性信号',
      description: '增加行业认证、专家背书等信息',
      actions: ['展示行业资质和认证', '邀请专家背书或联名发布'],
    },
  ],
};

function ScoreRing({ score, size = 120, label }: { score: number; size?: number; label: string }) {
  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (score / 100) * circumference;
  
  const getColor = (s: number) => {
    if (s >= 80) return '#22c55e';
    if (s >= 60) return '#eab308';
    return '#ef4444';
  };
  
  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={45}
          fill="none"
          stroke="#334155"
          strokeWidth="8"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={45}
          fill="none"
          stroke={getColor(score)}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000"
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center" style={{ width: size, height: size }}>
        <span className="text-3xl font-bold text-white">{score}</span>
      </div>
      <span className="mt-2 text-sm text-slate-400">{label}</span>
    </div>
  );
}

export default function SampleReportPage() {
  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <div className="bg-slate-800/50 border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4" />
            返回首页
          </Link>
          <div className="flex items-center gap-3">
            <span className="px-3 py-1 bg-primary-500/20 text-primary-400 rounded-full text-sm">
              样例报告
            </span>
            <Link
              href="/register"
              className="bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
            >
              免费创建我的报告
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Report Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileText className="w-8 h-8 text-primary-400" />
              <div>
                <h1 className="text-2xl font-bold text-white">
                  {sampleReport.projectName} - AI 可见性研究报告
                </h1>
                <p className="text-slate-400 text-sm">
                  生成时间: {sampleReport.generatedAt} · 报告编号: {sampleReport.reportId}
                </p>
              </div>
            </div>
            <div className="hidden md:block">
              <span className="px-3 py-1 bg-amber-500/20 text-amber-400 rounded-full text-sm">
                📋 样例报告
              </span>
            </div>
          </div>
        </div>

        {/* Overall Score */}
        <div className="bg-gradient-to-r from-slate-800/50 to-slate-800/30 rounded-2xl border border-slate-700/50 p-8 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 items-center">
            <div className="md:col-span-1 flex justify-center">
              <div className="relative">
                <ScoreRing score={sampleReport.overallScore} size={160} label="综合评分" />
              </div>
            </div>
            <div className="md:col-span-3 grid grid-cols-3 gap-6">
              {Object.entries(sampleReport.scores).map(([key, data]) => (
                <div key={key} className="text-center">
                  <div className="relative inline-flex">
                    <ScoreRing score={data.score} size={100} label={data.label} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Engine Coverage */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
            <h2 className="text-lg font-semibold text-white mb-6">📊 AI 引擎覆盖分析</h2>
            <div className="space-y-4">
              {sampleReport.engineCoverage.map((item) => (
                <div key={item.engine} className="flex items-center justify-between">
                  <span className="text-slate-300">{item.engine}</span>
                  <div className="flex items-center gap-3">
                    <div className="w-32 h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all"
                        style={{ width: `${item.coverage}%` }}
                      />
                    </div>
                    <span className="text-white font-medium w-12">{item.coverage}%</span>
                    {item.trend === 'up' && <TrendingUp className="w-4 h-4 text-green-400" />}
                    {item.trend === 'down' && <TrendingDown className="w-4 h-4 text-red-400" />}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Competitive Analysis */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
            <h2 className="text-lg font-semibold text-white mb-6">🏆 竞争格局分析</h2>
            <div className="space-y-3">
              {sampleReport.topCompetitors.map((item, idx) => (
                <div
                  key={item.name}
                  className={cn(
                    'flex items-center justify-between p-3 rounded-lg',
                    item.isYou ? 'bg-primary-500/10 border border-primary-500/30' : 'bg-slate-700/30'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-slate-500 w-6">{idx + 1}</span>
                    <span className={cn('font-medium', item.isYou ? 'text-primary-400' : 'text-white')}>
                      {item.name}
                      {item.isYou && <span className="ml-2 text-xs">(您的品牌)</span>}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-slate-400 text-sm">{item.share}</span>
                    <span className="text-white font-bold">{item.score}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Top Citation Sources & Query Distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Top Citation Sources */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
            <h2 className="text-lg font-semibold text-white mb-6">🔗 Top 引用来源</h2>
            <div className="space-y-3">
              {sampleReport.topCitationSources.map((source, idx) => (
                <div
                  key={source.domain}
                  className={cn(
                    'flex items-center justify-between p-3 rounded-lg',
                    source.isYou ? 'bg-green-500/10 border border-green-500/30' : 'bg-slate-700/30'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-slate-500 w-6">{idx + 1}</span>
                    <div>
                      <span className={cn('font-medium', source.isYou ? 'text-green-400' : 'text-white')}>
                        {source.title}
                      </span>
                      <span className="text-slate-500 text-xs ml-2">{source.domain}</span>
                    </div>
                  </div>
                  <span className="text-white font-medium">{source.count} 次</span>
                </div>
              ))}
            </div>
          </div>

          {/* Query Distribution */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
            <h2 className="text-lg font-semibold text-white mb-6">📈 问题集分布</h2>
            <div className="space-y-6">
              <div>
                <h3 className="text-sm text-slate-400 mb-3">按采购阶段</h3>
                <div className="space-y-2">
                  {sampleReport.queryDistribution.byStage.map((item) => (
                    <div key={item.stage} className="flex items-center justify-between">
                      <span className="text-slate-300 text-sm">{item.stage}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500 rounded-full"
                            style={{ width: `${item.percentage}%` }}
                          />
                        </div>
                        <span className="text-slate-400 text-xs w-8">{item.percentage}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-sm text-slate-400 mb-3">按风险等级</h3>
                <div className="space-y-2">
                  {sampleReport.queryDistribution.byRisk.map((item) => (
                    <div key={item.level} className="flex items-center justify-between">
                      <span className="text-slate-300 text-sm">{item.level}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
                          <div
                            className={cn(
                              'h-full rounded-full',
                              item.level === '低风险' ? 'bg-green-500' :
                              item.level === '中风险' ? 'bg-yellow-500' : 'bg-red-500'
                            )}
                            style={{ width: `${item.percentage}%` }}
                          />
                        </div>
                        <span className="text-slate-400 text-xs w-8">{item.percentage}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Calibration Errors (Drift Warning) */}
        {sampleReport.calibrationErrors.length > 0 && (
          <div className="bg-red-500/10 rounded-xl border border-red-500/30 p-6 mb-8">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              ⚠️ 口径错误清单
            </h2>
            <p className="text-slate-400 text-sm mb-4">
              以下为 AI 引擎对您品牌的错误描述，建议及时修正以避免用户误解
            </p>
            <div className="space-y-3">
              {sampleReport.calibrationErrors.map((error, idx) => (
                <div
                  key={idx}
                  className={cn(
                    'p-4 rounded-lg border-l-4',
                    error.severity === 'high' ? 'bg-red-500/10 border-red-500' : 'bg-yellow-500/10 border-yellow-500'
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-white font-medium text-sm">{error.query}</p>
                      <p className="text-slate-400 text-sm mt-1">{error.error}</p>
                    </div>
                    <span
                      className={cn(
                        'px-2 py-0.5 rounded text-xs font-medium',
                        error.severity === 'high' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                      )}
                    >
                      {error.severity === 'high' ? '高优先' : '中优先'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Drift Warning */}
        {sampleReport.driftWarning.hasWarning && (
          <div className="bg-amber-500/10 rounded-xl border border-amber-500/30 p-6 mb-8">
            <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
              <TrendingDown className="w-5 h-5 text-amber-400" />
              📉 漂移预警
            </h2>
            <p className="text-slate-300">
              {sampleReport.driftWarning.message}：可见性变化 
              <span className="text-red-400 font-medium ml-1">{sampleReport.driftWarning.change}%</span>
            </p>
            <p className="text-slate-400 text-sm mt-1">
              受影响引擎: {sampleReport.driftWarning.affectedEngines.join(', ')}
            </p>
          </div>
        )}

        {/* Insights */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 mb-8">
          <h2 className="text-lg font-semibold text-white mb-6">关键洞察</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sampleReport.insights.map((insight, idx) => (
              <div
                key={idx}
                className={cn(
                  'p-4 rounded-lg border-l-4 flex items-start gap-3',
                  insight.type === 'positive' && 'bg-green-500/10 border-green-500',
                  insight.type === 'warning' && 'bg-yellow-500/10 border-yellow-500',
                  insight.type === 'info' && 'bg-blue-500/10 border-blue-500'
                )}
              >
                {insight.type === 'positive' && <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />}
                {insight.type === 'warning' && <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />}
                {insight.type === 'info' && <FileText className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />}
                <span className="text-slate-300">{insight.text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recommendations */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 mb-8">
          <h2 className="text-lg font-semibold text-white mb-6">💡 优化建议</h2>
          <div className="space-y-4">
            {sampleReport.recommendations.map((rec, idx) => (
              <div key={idx} className="p-4 bg-slate-700/30 rounded-lg">
                <div className="flex items-center gap-3 mb-2">
                  <span
                    className={cn(
                      'px-2 py-0.5 rounded text-xs font-medium',
                      rec.priority === 'high' && 'bg-red-500/20 text-red-400',
                      rec.priority === 'medium' && 'bg-yellow-500/20 text-yellow-400'
                    )}
                  >
                    {rec.priority === 'high' ? '高优先' : '中优先'}
                  </span>
                  <h3 className="font-medium text-white">{rec.title}</h3>
                </div>
                <p className="text-slate-400 text-sm mb-3">{rec.description}</p>
                {rec.actions && rec.actions.length > 0 && (
                  <ul className="space-y-1">
                    {rec.actions.map((action, actionIdx) => (
                      <li key={actionIdx} className="text-slate-300 text-sm flex items-start gap-2">
                        <span className="text-primary-400 mt-0.5">•</span>
                        {action}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="bg-gradient-to-r from-primary-500/20 to-accent-500/20 rounded-2xl border border-primary-500/30 p-8">
          <div className="flex flex-col md:flex-row items-center justify-center gap-8">
            {/* Left: Text */}
            <div className="text-center md:text-left">
              <h2 className="text-2xl font-bold text-white mb-4">
                想要获得您品牌的专属报告？
              </h2>
              <p className="text-slate-300 mb-6 max-w-lg">
                免费注册即可体验 10 条查询词的完整体检，获得详细的 AI 可见性分析报告。
              </p>
              <div className="flex flex-col sm:flex-row items-center gap-4 justify-center md:justify-start">
                <Link
                  href="/register"
                  className="bg-primary-500 hover:bg-primary-600 text-white px-8 py-3 rounded-xl font-medium transition-colors flex items-center gap-2"
                >
                  开始体检（免费 10 条）
                  <ArrowRight className="w-5 h-5" />
                </Link>
                <Link
                  href="/"
                  className="text-slate-300 hover:text-white px-6 py-3 rounded-xl font-medium border border-slate-600 hover:border-slate-500 transition-colors"
                >
                  了解更多
                </Link>
              </div>
            </div>
            
            {/* Right: WeChat QR */}
            <div className="flex flex-col items-center">
              <img 
                src="/wechat-qrcode.jpg" 
                alt="FindableX 公众号" 
                className="w-32 h-32 rounded-lg border border-slate-600"
              />
              <p className="text-slate-400 text-sm mt-3 text-center">
                关注公众号<br/>获取 GEO 最新资讯
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Note */}
      <div className="bg-slate-800/30 border-t border-slate-700 mt-12 py-6 text-center text-slate-500 text-sm space-y-2">
        <p>
          注：这是一份样例报告，数据为演示用途。您的实际报告将基于真实的 AI 引擎数据分析。
        </p>
        <a
          href="https://beian.miit.gov.cn/"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-slate-400 transition-colors"
        >
          苏ICP备2026005817号
        </a>
      </div>
    </div>
  );
}
