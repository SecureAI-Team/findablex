import Link from 'next/link';
import { Metadata } from 'next';
import { FileText, Download, ArrowRight, BookOpen, BarChart3, Users, TrendingUp } from 'lucide-react';
import { Header, Footer, PageViewTracker } from '@/components';
import {
  generatePageMetadata,
  generateBreadcrumbSchema,
  JsonLd,
} from '@/lib/seo';

export const metadata: Metadata = generatePageMetadata({
  title: 'GEO 研究中心 - 白皮书与行业报告',
  description:
    '获取 FindableX 发布的 GEO（生成式引擎优化）研究报告、白皮书和行业洞察。基于权威数据和实证研究，帮助品牌理解 AI 搜索趋势。',
  path: '/research',
});

const researchItems = [
  {
    type: '白皮书',
    title: '2025 品牌 GEO 优化实践指南',
    description: '基于 100+ 品牌案例的 GEO 优化最佳实践总结，包含完整的策略框架、实施步骤和效果评估方法。',
    highlights: [
      '100+ 真实品牌案例分析',
      '完整的 GEO 优化框架',
      '可落地的执行清单',
      '效果评估指标体系',
    ],
    pages: 45,
    downloadUrl: '#',
    image: '📘',
    featured: true,
  },
  {
    type: '研究报告',
    title: '2025 AI 搜索市场研究报告',
    description: '全面分析全球和中国 AI 搜索市场的规模、增长、用户行为和竞争格局，为品牌决策提供数据支持。',
    highlights: [
      'Gartner、IDC 等权威数据',
      '主流 AI 引擎深度分析',
      '用户行为研究洞察',
      '品牌机遇与挑战',
    ],
    pages: 32,
    downloadUrl: '/articles/ai-search-market-report-2025',
    image: '📊',
    featured: true,
  },
  {
    type: '案例研究',
    title: 'SaaS 品牌 GEO 优化案例集',
    description: '详细记录多个 SaaS 品牌通过 GEO 优化提升 AI 可见性的完整过程，包含具体策略和数据结果。',
    highlights: [
      '真实品牌案例',
      '可复制的策略',
      '量化效果数据',
      '实施时间表',
    ],
    pages: 28,
    downloadUrl: '/articles/case-study-saas-brand-geo-optimization',
    image: '📋',
    featured: false,
  },
  {
    type: '方法论',
    title: 'GEO 指标体系与评分标准',
    description: '详解 FindableX 的 GEO 评分体系，包括 AVI、CQS、CPI 等核心指标的计算方法和解读指南。',
    highlights: [
      'AVI 可见性指数详解',
      'CQS 引用质量评分',
      'CPI 竞争定位指数',
      '行业基准数据',
    ],
    pages: 18,
    downloadUrl: '#',
    image: '📐',
    featured: false,
  },
];

const stats = [
  { label: '研究报告', value: '10+', icon: FileText },
  { label: '案例分析', value: '50+', icon: BarChart3 },
  { label: '数据来源', value: '20+', icon: BookOpen },
  { label: '引用次数', value: '500+', icon: TrendingUp },
];

export default function ResearchPage() {
  return (
    <>
      <JsonLd
        data={generateBreadcrumbSchema([
          { name: '首页', url: '/' },
          { name: '研究中心', url: '/research' },
        ])}
      />
      <PageViewTracker pageName="research_center" properties={{ page_type: 'content' }} />

      <div className="min-h-screen bg-slate-900">
        <Header />

        {/* Hero Section */}
        <section className="pt-32 pb-16 relative overflow-hidden">
          <div className="absolute inset-0">
            <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
            <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center opacity-10" />
            <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl" />
          </div>

          <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <div className="inline-flex items-center gap-2 bg-primary-500/10 border border-primary-500/20 rounded-full px-4 py-1.5 mb-6">
              <BookOpen className="w-4 h-4 text-primary-400" />
              <span className="text-primary-400 text-sm font-medium">
                FindableX 研究中心
              </span>
            </div>
            
            <h1 className="font-display text-4xl lg:text-5xl font-bold text-white mb-6">
              GEO 研究与行业洞察
            </h1>
            <p className="text-xl text-slate-300 max-w-2xl mx-auto mb-12">
              基于权威数据和实证研究，为品牌提供 AI 搜索时代的战略决策支持
            </p>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto">
              {stats.map((stat) => (
                <div
                  key={stat.label}
                  className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50"
                >
                  <stat.icon className="w-6 h-6 text-primary-400 mx-auto mb-2" />
                  <div className="font-display text-2xl font-bold text-white">
                    {stat.value}
                  </div>
                  <div className="text-sm text-slate-400">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Research Items */}
        <section className="py-16">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid md:grid-cols-2 gap-8">
              {researchItems.map((item) => (
                <div
                  key={item.title}
                  className={`bg-slate-800/50 rounded-2xl border overflow-hidden transition-all hover:border-primary-500/50 ${
                    item.featured
                      ? 'border-primary-500/30'
                      : 'border-slate-700/50'
                  }`}
                >
                  {/* Header */}
                  <div className="p-6 pb-4">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="text-4xl">{item.image}</div>
                        <div>
                          <span className="text-xs font-medium text-primary-400 bg-primary-500/10 px-2 py-1 rounded">
                            {item.type}
                          </span>
                          {item.featured && (
                            <span className="ml-2 text-xs font-medium text-amber-400 bg-amber-500/10 px-2 py-1 rounded">
                              推荐
                            </span>
                          )}
                        </div>
                      </div>
                      <span className="text-sm text-slate-500">
                        {item.pages} 页
                      </span>
                    </div>

                    <h3 className="font-display text-xl font-semibold text-white mb-3">
                      {item.title}
                    </h3>
                    <p className="text-slate-400 text-sm mb-4">
                      {item.description}
                    </p>
                  </div>

                  {/* Highlights */}
                  <div className="px-6 pb-4">
                    <div className="text-xs text-slate-500 mb-2">包含内容</div>
                    <ul className="grid grid-cols-2 gap-2">
                      {item.highlights.map((highlight) => (
                        <li
                          key={highlight}
                          className="flex items-center gap-1.5 text-sm text-slate-300"
                        >
                          <span className="w-1 h-1 bg-primary-400 rounded-full" />
                          {highlight}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Action */}
                  <div className="p-6 pt-4 border-t border-slate-700/50">
                    <Link
                      href={item.downloadUrl}
                      className={`inline-flex items-center gap-2 w-full justify-center py-3 rounded-lg font-medium transition-all ${
                        item.downloadUrl === '#'
                          ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                          : 'bg-primary-500 hover:bg-primary-600 text-white'
                      }`}
                    >
                      {item.downloadUrl === '#' ? (
                        <>即将发布</>
                      ) : (
                        <>
                          阅读报告
                          <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Research Partners */}
        <section className="py-16 bg-slate-800/30">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="font-display text-2xl font-bold text-white text-center mb-4">
              数据来源与研究合作
            </h2>
            <p className="text-slate-400 text-center mb-12">
              我们的研究基于权威机构的数据和学术研究
            </p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 items-center justify-items-center opacity-60">
              {['Gartner', 'IDC', 'Statista', 'Similarweb', 'Pew Research', 'QuestMobile', '艾瑞咨询', 'Princeton'].map(
                (partner) => (
                  <div
                    key={partner}
                    className="text-slate-400 font-medium text-lg"
                  >
                    {partner}
                  </div>
                )
              )}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-16">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="font-display text-2xl lg:text-3xl font-bold text-white mb-4">
              获取定制化研究报告
            </h2>
            <p className="text-slate-300 mb-8 max-w-2xl mx-auto">
              需要针对您的行业或品牌的专项研究？联系我们获取定制化的 GEO 分析报告
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/contact"
                className="inline-flex items-center gap-2 bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-white px-8 py-3 rounded-xl font-medium transition-all hover:shadow-xl hover:shadow-primary-500/25"
              >
                联系我们
                <ArrowRight className="w-5 h-5" />
              </Link>
              <Link
                href="/articles"
                className="inline-flex items-center gap-2 text-slate-300 hover:text-white border border-slate-600 hover:border-slate-500 px-8 py-3 rounded-xl font-medium transition-all"
              >
                浏览所有文章
              </Link>
            </div>
          </div>
        </section>

        <Footer />
      </div>
    </>
  );
}
