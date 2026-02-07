import { Metadata } from 'next';
import Link from 'next/link';
import {
  ArrowRight,
  Check,
  Eye,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Minus,
  Shield,
  Globe,
  MessageSquare,
  Star,
  AlertTriangle,
  CheckCircle,
  Target,
} from 'lucide-react';
import { Header, Footer } from '@/components';
import { generatePageMetadata, generateBreadcrumbSchema, JsonLd } from '@/lib/seo';

export const metadata: Metadata = generatePageMetadata({
  title: '样例报告 - AI 搜索可见性体检报告示例',
  description:
    'FindableX AI 搜索可见性体检报告样例。查看一份真实的 GEO 体检报告长什么样——品牌可见性评分、引擎覆盖率、引用质量分析和优化建议。无需注册即可查看。',
  path: '/sample-report',
});

// ── Sample data ─────────────────────────────────────────────────────
const sampleBrand = '示例科技';
const reportDate = '2026-02-01';

const overallScore = 72;

const engines = [
  { name: 'ChatGPT', score: 85, mentioned: true, cited: true, rank: 2, trend: 'up' as const },
  { name: 'Perplexity', score: 78, mentioned: true, cited: true, rank: 3, trend: 'up' as const },
  { name: '通义千问', score: 65, mentioned: true, cited: false, rank: 5, trend: 'stable' as const },
  { name: 'Kimi', score: 60, mentioned: true, cited: false, rank: 4, trend: 'down' as const },
  { name: 'DeepSeek', score: 55, mentioned: false, cited: false, rank: null, trend: 'down' as const },
  { name: '文心一言', score: 70, mentioned: true, cited: true, rank: 3, trend: 'stable' as const },
];

const queries = [
  { query: '最好的企业级SaaS工具', visibility: 90, mentioned: true },
  { query: '如何选择项目管理软件', visibility: 75, mentioned: true },
  { query: '国内最好的协同办公平台', visibility: 60, mentioned: true },
  { query: '中小企业数字化转型方案', visibility: 45, mentioned: false },
  { query: 'SaaS产品对比评测', visibility: 80, mentioned: true },
];

const recommendations = [
  {
    priority: 'high',
    title: '增加结构化数据标记',
    description: '在官网添加 JSON-LD Schema 标记，帮助 AI 引擎更准确地提取品牌信息。',
  },
  {
    priority: 'high',
    title: '优化品牌相关内容覆盖',
    description: '在 DeepSeek 和 Kimi 中品牌可见性较低，建议通过高质量第三方内容提升覆盖。',
  },
  {
    priority: 'medium',
    title: '提高引用率',
    description: '通义千问和 Kimi 中品牌被提及但未被引用，建议优化权威来源内容。',
  },
  {
    priority: 'medium',
    title: '发布对比类内容',
    description: '针对"对比评测"类查询创建专业的对比文章，提升在该类查询中的表现。',
  },
  {
    priority: 'low',
    title: '定期复测',
    description: '建议每 2 周进行一次体检，追踪各引擎的可见性变化趋势。',
  },
];

// ── Helpers ──────────────────────────────────────────────────────────

function TrendIcon({ trend }: { trend: 'up' | 'down' | 'stable' }) {
  if (trend === 'up') return <TrendingUp className="w-4 h-4 text-green-400" />;
  if (trend === 'down') return <TrendingDown className="w-4 h-4 text-red-400" />;
  return <Minus className="w-4 h-4 text-slate-400" />;
}

function ScoreBar({ score, color = 'primary' }: { score: number; color?: string }) {
  const colorClass =
    score >= 80
      ? 'bg-green-500'
      : score >= 60
        ? 'bg-primary-500'
        : score >= 40
          ? 'bg-amber-500'
          : 'bg-red-500';

  return (
    <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all ${colorClass}`}
        style={{ width: `${score}%` }}
      />
    </div>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const cls =
    priority === 'high'
      ? 'bg-red-500/10 text-red-400 border-red-500/20'
      : priority === 'medium'
        ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
        : 'bg-slate-500/10 text-slate-400 border-slate-500/20';
  const label = priority === 'high' ? '高' : priority === 'medium' ? '中' : '低';
  return (
    <span className={`text-xs px-2 py-0.5 rounded border ${cls}`}>{label}</span>
  );
}

// ── Page ─────────────────────────────────────────────────────────────

export default function SampleReportPage() {
  return (
    <>
      <JsonLd
        data={generateBreadcrumbSchema([
          { name: '首页', url: '/' },
          { name: '样例报告', url: '/sample-report' },
        ])}
      />
      <div className="min-h-screen bg-slate-900">
        <Header />

        {/* Hero */}
        <section className="pt-32 lg:pt-40 pb-10">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-xs bg-primary-500/10 text-primary-400 border border-primary-500/20 px-2 py-0.5 rounded">
                样例报告
              </span>
              <span className="text-xs text-slate-500">{reportDate}</span>
            </div>
            <h1 className="font-display text-3xl lg:text-4xl font-bold text-white mb-3">
              「{sampleBrand}」AI 搜索可见性体检报告
            </h1>
            <p className="text-slate-400 text-lg max-w-2xl">
              这是一份 FindableX 生成的真实体检报告示例，展示品牌在主流 AI 搜索引擎中的表现。
              <strong className="text-slate-300">无需注册即可查看。</strong>
            </p>
          </div>
        </section>

        {/* Overall Score */}
        <section className="pb-12">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid md:grid-cols-4 gap-6">
              {/* Main score */}
              <div className="md:col-span-1 bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 text-center">
                <div className="relative w-32 h-32 mx-auto mb-4">
                  <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r="52" fill="none" stroke="#334155" strokeWidth="8" />
                    <circle
                      cx="60"
                      cy="60"
                      r="52"
                      fill="none"
                      stroke="url(#scoreGradient)"
                      strokeWidth="8"
                      strokeLinecap="round"
                      strokeDasharray={`${overallScore * 3.27} 327`}
                    />
                    <defs>
                      <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#6366f1" />
                        <stop offset="100%" stopColor="#a855f7" />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-4xl font-bold text-white">{overallScore}</span>
                  </div>
                </div>
                <p className="text-sm text-slate-400">综合可见性评分</p>
              </div>

              {/* Quick stats */}
              <div className="md:col-span-3 grid grid-cols-2 sm:grid-cols-3 gap-4">
                {[
                  { label: '覆盖引擎', value: `${engines.filter(e => e.mentioned).length}/${engines.length}`, icon: Globe },
                  { label: '被引用', value: `${engines.filter(e => e.cited).length} 次`, icon: MessageSquare },
                  { label: '查询覆盖', value: `${queries.filter(q => q.mentioned).length}/${queries.length}`, icon: Target },
                  { label: '平均排名', value: '#3.4', icon: Star },
                  { label: '上升引擎', value: `${engines.filter(e => e.trend === 'up').length}`, icon: TrendingUp },
                  { label: '需关注', value: `${recommendations.filter(r => r.priority === 'high').length}`, icon: AlertTriangle },
                ].map((stat, i) => (
                  <div key={i} className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <stat.icon className="w-4 h-4 text-slate-500" />
                      <span className="text-xs text-slate-500">{stat.label}</span>
                    </div>
                    <p className="text-xl font-bold text-white">{stat.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Engine Breakdown */}
        <section className="py-12 bg-slate-800/30">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="font-display text-xl font-bold text-white mb-6 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-primary-400" />
              各引擎表现
            </h2>
            <div className="space-y-3">
              {engines.map((engine) => (
                <div
                  key={engine.name}
                  className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 flex items-center gap-4"
                >
                  <div className="w-24 text-sm font-medium text-white">{engine.name}</div>
                  <div className="flex-1">
                    <ScoreBar score={engine.score} />
                  </div>
                  <div className="w-12 text-right text-sm font-mono text-slate-300">{engine.score}</div>
                  <div className="flex items-center gap-3 w-32 justify-end">
                    {engine.mentioned ? (
                      <span className="text-xs bg-green-500/10 text-green-400 px-2 py-0.5 rounded">提及</span>
                    ) : (
                      <span className="text-xs bg-slate-700 text-slate-500 px-2 py-0.5 rounded">未提及</span>
                    )}
                    {engine.cited && (
                      <span className="text-xs bg-primary-500/10 text-primary-400 px-2 py-0.5 rounded">引用</span>
                    )}
                    <TrendIcon trend={engine.trend} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Query Performance */}
        <section className="py-12">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="font-display text-xl font-bold text-white mb-6 flex items-center gap-2">
              <Eye className="w-5 h-5 text-primary-400" />
              查询词表现
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-3 px-4 text-sm text-slate-400 font-medium">查询词</th>
                    <th className="text-center py-3 px-4 text-sm text-slate-400 font-medium w-48">可见性</th>
                    <th className="text-center py-3 px-4 text-sm text-slate-400 font-medium w-24">状态</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50">
                  {queries.map((q, i) => (
                    <tr key={i} className="hover:bg-slate-800/30">
                      <td className="py-3 px-4 text-sm text-slate-300">{q.query}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          <ScoreBar score={q.visibility} />
                          <span className="text-sm font-mono text-slate-400 w-8">{q.visibility}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        {q.mentioned ? (
                          <CheckCircle className="w-4 h-4 text-green-400 mx-auto" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-amber-400 mx-auto" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Recommendations */}
        <section className="py-12 bg-slate-800/30">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="font-display text-xl font-bold text-white mb-6 flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary-400" />
              优化建议
            </h2>
            <div className="space-y-3">
              {recommendations.map((rec, i) => (
                <div
                  key={i}
                  className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-5"
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      <PriorityBadge priority={rec.priority} />
                    </div>
                    <div>
                      <h3 className="font-medium text-white mb-1">{rec.title}</h3>
                      <p className="text-sm text-slate-400">{rec.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <div className="bg-gradient-to-br from-primary-500/10 to-purple-500/10 border border-primary-500/20 rounded-2xl p-8 lg:p-12">
              <h2 className="font-display text-2xl lg:text-3xl font-bold text-white mb-4">
                想看看你的品牌表现？
              </h2>
              <p className="text-slate-400 mb-8 max-w-lg mx-auto">
                免费注册 FindableX，获取您的品牌在 9 大 AI 搜索引擎中的可见性体检报告。
                每月 5 次免费体检。
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link
                  href="/register"
                  className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-8 py-3 rounded-xl font-medium transition-all shadow-lg shadow-primary-500/25 hover:shadow-primary-500/40"
                >
                  免费开始体检
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  href="/pricing"
                  className="inline-flex items-center gap-2 text-slate-400 hover:text-white px-6 py-3 rounded-xl font-medium transition-colors"
                >
                  查看定价方案
                </Link>
              </div>
            </div>
          </div>
        </section>

        <Footer />
      </div>
    </>
  );
}
