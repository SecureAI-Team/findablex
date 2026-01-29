import { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, Target, Users, Lightbulb, Award } from 'lucide-react';
import { Header, Footer } from '@/components';
import { generatePageMetadata, generateBreadcrumbSchema, JsonLd } from '@/lib/seo';

export const metadata: Metadata = generatePageMetadata({
  title: '关于我们 - FindableX GEO 体检平台',
  description:
    'FindableX 是国内领先的 GEO（生成式引擎优化）体检平台，成立于 2024 年，致力于帮助品牌监测和提升在 ChatGPT、Perplexity、通义千问等 AI 搜索引擎中的可见性。',
  path: '/about',
});

const values = [
  {
    icon: Target,
    title: '使命驱动',
    description:
      '帮助每一个品牌在 AI 时代被发现，让优质内容获得应有的曝光。',
  },
  {
    icon: Users,
    title: '用户至上',
    description: '倾听用户需求，持续优化产品体验，让 GEO 分析简单易用。',
  },
  {
    icon: Lightbulb,
    title: '持续创新',
    description: '紧跟 AI 搜索技术发展，不断探索 GEO 优化的最佳实践。',
  },
  {
    icon: Award,
    title: '品质保证',
    description: '以专业的数据分析和严谨的方法论，为用户提供可信赖的洞察。',
  },
];

const milestones = [
  { year: '2024 Q3', event: '项目启动，完成核心功能开发' },
  { year: '2024 Q4', event: '公测上线，服务首批用户' },
  { year: '2025 Q2', event: '发布专业版，支持团队协作' },
  { year: '2025 Q4', event: '推出企业版和 API 服务' },
  { year: '2026 Q1', event: '平台全面升级，支持更多 AI 引擎' },
];

export default function AboutPage() {
  return (
    <>
      <JsonLd data={generateBreadcrumbSchema([
        { name: '首页', url: '/' },
        { name: '关于我们', url: '/about' },
      ])} />
    <div className="min-h-screen bg-slate-900">
      <Header />

      {/* Hero */}
      <section className="pt-32 lg:pt-40 pb-16 lg:pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <h1 className="font-display text-4xl lg:text-5xl font-bold text-white mb-6">
              让品牌在 AI 搜索中
              <span className="text-primary-400">被发现</span>
            </h1>
            <p className="text-slate-400 text-lg leading-relaxed">
              FindableX 成立于 2024
              年，是国内领先的 GEO（Generative Engine Optimization）体检平台。
              我们专注于帮助品牌理解和优化其在 AI 生成式搜索引擎中的可见性。
            </p>
          </div>
        </div>
      </section>

      {/* Mission */}
      <section className="py-20 lg:py-32 bg-slate-800/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-6">
                我们的使命
              </h2>
              <div className="space-y-4 text-slate-300 leading-relaxed">
                <p>
                  随着 ChatGPT、Perplexity、Google SGE 等 AI
                  搜索引擎的快速普及，用户获取信息的方式正在发生根本性变革。
                </p>
                <p>
                  传统的 SEO
                  优化方法已经无法完全适应这个新时代。品牌需要新的工具和方法来理解
                  AI 是如何引用和推荐他们的内容。
                </p>
                <p>
                  FindableX
                  应运而生。我们的使命是成为品牌在 AI 时代的可见性专家，提供专业的
                  GEO 监测、分析和优化建议，帮助每一个优质品牌被 AI 发现和推荐。
                </p>
              </div>
            </div>
            <div className="bg-gradient-to-br from-primary-500/10 to-accent-500/10 rounded-2xl p-8 border border-slate-700/50">
              <blockquote className="text-xl lg:text-2xl text-white font-medium italic">
                "在 AI 搜索时代，被引用比被搜索到更重要。"
              </blockquote>
              <p className="mt-4 text-slate-400">— FindableX 创始团队</p>
            </div>
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="py-20 lg:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
              我们的价值观
            </h2>
            <p className="text-slate-400 text-lg">
              这些原则指导着我们的每一个决策
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {values.map((value) => (
              <div key={value.title} className="text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-primary-500/20 to-accent-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <value.icon className="w-8 h-8 text-primary-400" />
                </div>
                <h3 className="font-display text-lg font-semibold text-white mb-2">
                  {value.title}
                </h3>
                <p className="text-slate-400 text-sm">{value.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Timeline */}
      <section className="py-20 lg:py-32 bg-slate-800/30">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
              发展历程
            </h2>
            <p className="text-slate-400 text-lg">我们的成长之路</p>
          </div>

          <div className="space-y-8">
            {milestones.map((milestone, i) => (
              <div key={i} className="flex gap-6">
                <div className="flex flex-col items-center">
                  <div className="w-4 h-4 rounded-full bg-primary-500" />
                  {i < milestones.length - 1 && (
                    <div className="w-0.5 h-full bg-slate-700 mt-2" />
                  )}
                </div>
                <div className="pb-8">
                  <span className="text-primary-400 text-sm font-medium">
                    {milestone.year}
                  </span>
                  <p className="text-white mt-1">{milestone.event}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 lg:py-32">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-display text-2xl lg:text-3xl font-bold text-white mb-6">
            加入我们的旅程
          </h2>
          <p className="text-slate-400 mb-8 max-w-2xl mx-auto">
            无论您是想提升品牌可见性，还是对 GEO 领域感兴趣，我们都欢迎您的加入
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/register"
              className="w-full sm:w-auto bg-primary-500 hover:bg-primary-600 text-white px-8 py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2"
            >
              开始使用
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/contact"
              className="w-full sm:w-auto text-slate-300 hover:text-white px-8 py-3 rounded-lg font-medium border border-slate-600 hover:border-slate-500 transition-all text-center"
            >
              联系我们
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
    </>
  );
}
