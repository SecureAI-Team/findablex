import { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Calendar, Clock, User, ArrowLeft, ArrowRight, Tag, Share2 } from 'lucide-react';
import { Header, Footer, PageViewTracker } from '@/components';
import {
  getArticleBySlug,
  getAllArticles,
  getRelatedArticles,
} from '@/lib/articles';
import {
  generateArticleSchema,
  generateBreadcrumbSchema,
  JsonLd,
} from '@/lib/seo';

interface Props {
  params: { slug: string };
}

// 生成静态路径
export async function generateStaticParams() {
  const articles = getAllArticles();
  return articles.map((article) => ({
    slug: article.slug,
  }));
}

// 生成动态元数据
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const article = getArticleBySlug(params.slug);

  if (!article) {
    return {
      title: '文章未找到',
    };
  }

  const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://findablex.com';

  return {
    title: article.title,
    description: article.description,
    keywords: article.tags,
    authors: [{ name: article.author }],
    openGraph: {
      title: article.title,
      description: article.description,
      type: 'article',
      publishedTime: article.publishedAt,
      modifiedTime: article.updatedAt,
      authors: [article.author],
      tags: article.tags,
      images: [
        {
          url: article.image || '/og-image.png',
          width: 1200,
          height: 630,
          alt: article.title,
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: article.title,
      description: article.description,
      images: [article.image || '/og-image.png'],
    },
    alternates: {
      canonical: `${SITE_URL}/articles/${article.slug}`,
    },
  };
}

// 简单的 Markdown 渲染（生产环境建议使用 react-markdown）
function renderMarkdown(content: string) {
  // 处理标题
  let html = content
    .replace(/^### (.*$)/gim, '<h3 class="text-xl font-semibold text-white mt-8 mb-4">$1</h3>')
    .replace(/^## (.*$)/gim, '<h2 class="text-2xl font-bold text-white mt-10 mb-5">$1</h2>')
    .replace(/^# (.*$)/gim, '<h1 class="text-3xl font-bold text-white mt-12 mb-6">$1</h1>');

  // 处理粗体
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>');

  // 处理代码块
  html = html.replace(/```([\s\S]*?)```/g, '<pre class="bg-slate-800 rounded-lg p-4 my-4 overflow-x-auto text-sm text-slate-300"><code>$1</code></pre>');

  // 处理行内代码
  html = html.replace(/`([^`]+)`/g, '<code class="bg-slate-800 px-1.5 py-0.5 rounded text-primary-400 text-sm">$1</code>');

  // 处理列表
  html = html.replace(/^\- (.*$)/gim, '<li class="ml-4 mb-2 text-slate-300">$1</li>');
  html = html.replace(/(<li.*<\/li>\n?)+/g, '<ul class="list-disc list-outside ml-4 my-4">$&</ul>');

  // 处理数字列表
  html = html.replace(/^\d+\. (.*$)/gim, '<li class="ml-4 mb-2 text-slate-300">$1</li>');

  // 处理表格 - 添加文字颜色
  html = html.replace(/\|(.+)\|/g, (match, content) => {
    const cells = content.split('|').map((cell: string) => cell.trim());
    if (cells.every((cell: string) => cell.match(/^-+$/))) {
      return ''; // 表头分隔行
    }
    const cellHtml = cells
      .map((cell: string) => `<td class="border border-slate-700 px-4 py-2 text-slate-300">${cell}</td>`)
      .join('');
    return `<tr class="text-slate-300">${cellHtml}</tr>`;
  });
  html = html.replace(/(<tr.*<\/tr>\n?)+/g, '<table class="w-full border-collapse my-6 text-sm text-slate-300"><tbody>$&</tbody></table>');

  // 处理链接
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-primary-400 hover:text-primary-300 underline">$1</a>');

  // 处理段落
  html = html.replace(/^(?!<[hultop])(.*$)/gim, (match) => {
    if (match.trim() === '' || match.startsWith('<')) return match;
    return `<p class="text-slate-300 leading-relaxed mb-4">${match}</p>`;
  });

  // 处理分隔线
  html = html.replace(/^---$/gim, '<hr class="border-slate-700 my-8" />');

  return html;
}

export default function ArticlePage({ params }: Props) {
  const article = getArticleBySlug(params.slug);

  if (!article) {
    notFound();
  }

  const relatedArticles = getRelatedArticles(params.slug);
  const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://findablex.com';

  return (
    <>
      {/* 结构化数据 - 对 SEO 和 GEO 都很重要 */}
      <JsonLd
        data={generateArticleSchema({
          title: article.title,
          description: article.description,
          url: `/articles/${article.slug}`,
          image: article.image,
          datePublished: article.publishedAt,
          dateModified: article.updatedAt,
          author: article.author,
        })}
      />
      <JsonLd
        data={generateBreadcrumbSchema([
          { name: '首页', url: '/' },
          { name: '资讯中心', url: '/articles' },
          { name: article.title, url: `/articles/${article.slug}` },
        ])}
      />
      <PageViewTracker 
        pageName="article_detail" 
        properties={{ 
          article_slug: article.slug,
          article_category: article.category,
          page_type: 'content' 
        }} 
      />

      <div className="min-h-screen bg-slate-900">
        <Header />

        {/* Article Header */}
        <article className="pt-32 pb-16">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            {/* Breadcrumb */}
            <nav className="flex items-center gap-2 text-sm text-slate-400 mb-8">
              <Link href="/" className="hover:text-white transition-colors">
                首页
              </Link>
              <span>/</span>
              <Link href="/articles" className="hover:text-white transition-colors">
                资讯中心
              </Link>
              <span>/</span>
              <span className="text-slate-500 truncate max-w-[200px]">
                {article.title}
              </span>
            </nav>

            {/* Category & Tags */}
            <div className="flex flex-wrap items-center gap-2 mb-6">
              <span className="text-sm font-medium text-primary-400 bg-primary-500/10 px-3 py-1 rounded-full">
                {article.category}
              </span>
              {article.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded"
                >
                  {tag}
                </span>
              ))}
            </div>

            {/* Title */}
            <h1 className="font-display text-3xl lg:text-4xl xl:text-5xl font-bold text-white mb-6 leading-tight">
              {article.title}
            </h1>

            {/* Description */}
            <p className="text-xl text-slate-300 mb-8 leading-relaxed">
              {article.description}
            </p>

            {/* Meta */}
            <div className="flex flex-wrap items-center gap-6 pb-8 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-primary-500/20 rounded-full flex items-center justify-center">
                  <User className="w-5 h-5 text-primary-400" />
                </div>
                <div>
                  <div className="text-white font-medium">{article.author}</div>
                  <div className="text-xs text-slate-500">{article.authorTitle}</div>
                </div>
              </div>
              <div className="flex items-center gap-1 text-slate-400">
                <Calendar className="w-4 h-4" />
                <span className="text-sm">
                  {new Date(article.publishedAt).toLocaleDateString('zh-CN', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </span>
              </div>
              <div className="flex items-center gap-1 text-slate-400">
                <Clock className="w-4 h-4" />
                <span className="text-sm">{article.readingTime} 分钟阅读</span>
              </div>
            </div>

            {/* Content */}
            <div
              className="prose prose-invert prose-slate max-w-none py-12"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(article.content) }}
            />

            {/* Share & Tags */}
            <div className="py-8 border-t border-slate-800">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <Tag className="w-4 h-4 text-slate-500" />
                  <div className="flex flex-wrap gap-2">
                    {article.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-sm text-slate-400 bg-slate-800 px-3 py-1 rounded-full hover:bg-slate-700 cursor-pointer transition-colors"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Author Box */}
            <div className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50 mb-12">
              <div className="flex items-start gap-4">
                <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-accent-500 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-2xl font-bold text-white">
                    {article.author.charAt(0)}
                  </span>
                </div>
                <div>
                  <h3 className="font-semibold text-white mb-1">{article.author}</h3>
                  <p className="text-sm text-slate-400 mb-3">{article.authorTitle}</p>
                  <p className="text-slate-300 text-sm">
                    FindableX 研究团队专注于 GEO（生成式引擎优化）领域的研究与实践，
                    致力于帮助品牌在 AI 搜索时代提升可见性。
                  </p>
                </div>
              </div>
            </div>

            {/* Related Articles */}
            {relatedArticles.length > 0 && (
              <div className="mb-12">
                <h2 className="text-2xl font-bold text-white mb-6">相关文章</h2>
                <div className="grid md:grid-cols-2 gap-6">
                  {relatedArticles.map((related) => (
                    <Link
                      key={related.slug}
                      href={`/articles/${related.slug}`}
                      className="bg-slate-800/30 rounded-xl p-6 border border-slate-700/50 hover:border-primary-500/50 transition-all group"
                    >
                      <span className="text-xs text-primary-400 font-medium">
                        {related.category}
                      </span>
                      <h3 className="text-lg font-semibold text-white mt-2 mb-2 group-hover:text-primary-400 transition-colors line-clamp-2">
                        {related.title}
                      </h3>
                      <p className="text-sm text-slate-400 line-clamp-2">
                        {related.excerpt}
                      </p>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Back to Articles */}
            <div className="flex justify-between items-center pt-8 border-t border-slate-800">
              <Link
                href="/articles"
                className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                返回资讯中心
              </Link>
              <Link
                href="/register"
                className="flex items-center gap-2 text-primary-400 hover:text-primary-300 transition-colors"
              >
                免费体验 FindableX
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </article>

        {/* CTA Section */}
        <section className="py-16 bg-gradient-to-b from-slate-800/50 to-slate-900">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="font-display text-2xl lg:text-3xl font-bold text-white mb-4">
              准备好提升您的 GEO 可见性了吗？
            </h2>
            <p className="text-slate-300 mb-8 max-w-2xl mx-auto">
              立即注册 FindableX，免费体检您的品牌在 AI 搜索引擎中的表现
            </p>
            <Link
              href="/register"
              className="inline-flex items-center gap-2 bg-gradient-to-r from-primary-500 to-accent-500 hover:from-primary-600 hover:to-accent-600 text-white px-8 py-4 rounded-xl font-medium text-lg transition-all hover:shadow-xl hover:shadow-primary-500/25"
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
