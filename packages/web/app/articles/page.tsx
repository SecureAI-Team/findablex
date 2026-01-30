import Link from 'next/link';
import Image from 'next/image';
import { Metadata } from 'next';
import { Calendar, Clock, ArrowRight, Tag } from 'lucide-react';
import { Header, Footer, PageViewTracker } from '@/components';
import { getAllArticles } from '@/lib/articles';
import {
  generatePageMetadata,
  generateBreadcrumbSchema,
  JsonLd,
} from '@/lib/seo';

export const metadata: Metadata = generatePageMetadata({
  title: 'GEO 资讯中心 - 生成式引擎优化洞察与策略',
  description:
    '获取最新的 GEO（生成式引擎优化）行业洞察、实战指南和策略分析。了解如何提升品牌在 ChatGPT、Perplexity 等 AI 搜索引擎中的可见性。',
  path: '/articles',
});

export default function ArticlesPage() {
  const articles = getAllArticles();

  return (
    <>
      <JsonLd
        data={generateBreadcrumbSchema([
          { name: '首页', url: '/' },
          { name: '资讯中心', url: '/articles' },
        ])}
      />
      <PageViewTracker pageName="articles_list" properties={{ page_type: 'content' }} />

      <div className="min-h-screen bg-slate-900">
        <Header />

        {/* Hero Section */}
        <section className="pt-32 pb-16 relative overflow-hidden">
          <div className="absolute inset-0">
            <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
            <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center opacity-10" />
          </div>

          <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h1 className="font-display text-4xl lg:text-5xl font-bold text-white mb-6">
              GEO 资讯中心
            </h1>
            <p className="text-xl text-slate-300 max-w-2xl mx-auto">
              获取最新的生成式引擎优化洞察、实战指南和策略分析，
              帮助您的品牌在 AI 搜索时代赢得先机
            </p>
          </div>
        </section>

        {/* Articles Grid */}
        <section className="py-16">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {articles.map((article) => (
                <article
                  key={article.slug}
                  className="bg-slate-800/50 rounded-2xl border border-slate-700/50 overflow-hidden hover:border-primary-500/50 transition-all group"
                >
                  {/* Article Image */}
                  <div className="h-48 relative overflow-hidden">
                    <Image
                      src={article.image}
                      alt={article.title}
                      fill
                      className="object-cover group-hover:scale-105 transition-transform duration-300"
                      sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 33vw"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-900/60 to-transparent" />
                  </div>

                  <div className="p-6">
                    {/* Category */}
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-xs font-medium text-primary-400 bg-primary-500/10 px-2 py-1 rounded">
                        {article.category}
                      </span>
                      {article.featured && (
                        <span className="text-xs font-medium text-amber-400 bg-amber-500/10 px-2 py-1 rounded">
                          精选
                        </span>
                      )}
                    </div>

                    {/* Title */}
                    <h2 className="font-display text-lg font-semibold text-white mb-3 group-hover:text-primary-400 transition-colors line-clamp-2">
                      <Link href={`/articles/${article.slug}`}>
                        {article.title}
                      </Link>
                    </h2>

                    {/* Excerpt */}
                    <p className="text-slate-400 text-sm mb-4 line-clamp-2">
                      {article.excerpt}
                    </p>

                    {/* Meta */}
                    <div className="flex items-center gap-4 text-xs text-slate-500 mb-4">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {new Date(article.publishedAt).toLocaleDateString('zh-CN')}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {article.readingTime} 分钟阅读
                      </span>
                    </div>

                    {/* Read More */}
                    <Link
                      href={`/articles/${article.slug}`}
                      className="inline-flex items-center gap-1 text-sm text-primary-400 hover:text-primary-300 transition-colors group/link"
                    >
                      阅读全文
                      <ArrowRight className="w-4 h-4 group-hover/link:translate-x-1 transition-transform" />
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-16 bg-slate-800/30">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="font-display text-2xl lg:text-3xl font-bold text-white mb-4">
              想了解您的品牌在 AI 搜索中的表现？
            </h2>
            <p className="text-slate-300 mb-8">
              使用 FindableX 免费体检，获取专业的 GEO 可见性分析报告
            </p>
            <Link
              href="/register"
              className="inline-flex items-center gap-2 bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-white px-8 py-3 rounded-xl font-medium transition-all hover:shadow-xl hover:shadow-primary-500/25"
            >
              免费开始体检
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </section>

        <Footer />
      </div>
    </>
  );
}
