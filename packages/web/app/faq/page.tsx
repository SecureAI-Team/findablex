import { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { Header, Footer, FAQAccordion } from '@/components';
import { generatePageMetadata, generateFAQSchema, generateBreadcrumbSchema, JsonLd } from '@/lib/seo';

export const metadata: Metadata = generatePageMetadata({
  title: '常见问题 FAQ - GEO 与 AI 可见性',
  description:
    '关于 GEO（生成式引擎优化）和 FindableX 平台的常见问题解答。了解什么是 GEO、如何监测品牌在 ChatGPT/Perplexity 中的可见性、以及如何优化 AI 搜索表现。',
  path: '/faq',
});

const faqCategories = [
  {
    title: '关于 GEO',
    faqs: [
      {
        question: '什么是 GEO（Generative Engine Optimization）？',
        answer:
          'GEO 是 Generative Engine Optimization 的缩写，即生成式引擎优化。它关注的是如何让您的品牌和内容在 AI 生成式搜索引擎（如 ChatGPT、Perplexity、Google SGE）的回答中被引用和推荐。与传统 SEO 优化网页排名不同，GEO 优化的是 AI 引用您内容的概率和位置。',
      },
      {
        question: 'GEO 和 SEO 有什么区别？',
        answer:
          'SEO（搜索引擎优化）关注传统搜索引擎的网页排名，目标是让您的网页出现在搜索结果的前列。GEO 则关注 AI 生成式搜索引擎，这些引擎直接生成回答而非展示链接列表。GEO 的核心指标是被引用率和引用位置，而非传统的排名和点击率。两者需要不同的优化策略。',
      },
      {
        question: '为什么 GEO 很重要？',
        answer:
          '随着 ChatGPT、Perplexity 等 AI 搜索工具的普及，越来越多用户直接通过 AI 获取信息。研究显示超过 40% 的年轻用户更倾向使用 AI 搜索。如果您的品牌不出现在 AI 的回答中，您将失去这部分潜在用户。GEO 帮助您在 AI 时代保持竞争力。',
      },
    ],
  },
  {
    title: '关于 FindableX',
    faqs: [
      {
        question: 'FindableX 是什么？',
        answer:
          'FindableX 是专业的 GEO 体检平台。我们帮助品牌监测、分析和优化其在 AI 生成式搜索引擎中的可见性。通过导入 AI 搜索结果，我们自动提取引用、计算指标、生成报告，并提供优化建议。',
      },
      {
        question: 'FindableX 支持哪些 AI 引擎？',
        answer:
          '目前我们支持分析来自 ChatGPT、Perplexity、Google SGE、Bing Copilot、通义千问、文心一言等主流 AI 搜索引擎的结果。您可以导入这些引擎的搜索结果进行分析。',
      },
      {
        question: '数据是如何获取的？',
        answer:
          '我们采用用户主动导入的方式获取数据。您可以将 AI 引擎的搜索结果以 CSV、JSON 格式上传，或直接复制粘贴文本。我们也提供可选的 API 集成方案（需用户提供 API Token）。平台严格遵守合规要求，不会主动爬取任何第三方网站。',
      },
    ],
  },
  {
    title: '功能与使用',
    faqs: [
      {
        question: '如何开始使用 FindableX？',
        answer:
          '非常简单！1) 注册账号（支持免费试用）；2) 创建项目并设置目标域名；3) 导入 AI 搜索结果数据；4) 查看分析报告和优化建议。整个过程只需几分钟，无需技术背景。',
      },
      {
        question: 'FindableX 计算哪些指标？',
        answer:
          '我们提供多维度的 GEO 指标：可见性覆盖率（被引用的查询比例）、平均引用位置、Top3 出现率、引用总数、竞争对手占比、健康度评分等。这些指标帮助您全面了解品牌在 AI 搜索中的表现。',
      },
      {
        question: '什么是漂移监测？',
        answer:
          '漂移监测是 FindableX 的核心功能之一。通过定期复测相同的查询，系统会自动检测您的 GEO 指标变化。当可见性显著下降时，系统会及时预警，帮助您快速发现问题并采取行动。',
      },
      {
        question: '可以导出数据吗？',
        answer:
          '可以。专业版和企业版用户可以导出完整的分析数据，包括引用详情、指标时间序列、报告 PDF 等。企业版还支持通过 API 集成获取数据。',
      },
    ],
  },
  {
    title: '安全与隐私',
    faqs: [
      {
        question: '我的数据安全吗？',
        answer:
          '绝对安全。我们采用业界标准的加密技术保护您的数据，包括传输加密（TLS）和存储加密。我们遵循严格的数据安全标准，不会将您的数据用于任何未授权用途。',
      },
      {
        question: '可以删除我的数据吗？',
        answer:
          '可以。您可以随时删除项目和相关数据。根据 GDPR 等隐私法规，您也可以申请删除账户和所有关联数据。删除后数据将不可恢复。',
      },
      {
        question: '数据会被共享吗？',
        answer:
          '默认情况下不会。只有当您主动选择参与"科研数据共享"计划时，我们才会使用您的数据（经过去标识化处理）用于学术研究目的。这是完全可选的，您可以随时退出。',
      },
    ],
  },
];

// Flatten all FAQs for schema
const allFaqs = faqCategories.flatMap((cat) => cat.faqs);

export default function FAQPage() {
  return (
    <>
      <JsonLd data={generateFAQSchema(allFaqs)} />
      <JsonLd data={generateBreadcrumbSchema([
        { name: '首页', url: '/' },
        { name: '常见问题', url: '/faq' },
      ])} />

      <div className="min-h-screen bg-slate-900">
        <Header />

        {/* Hero */}
        <section className="pt-32 lg:pt-40 pb-16 lg:pb-20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h1 className="font-display text-4xl lg:text-5xl font-bold text-white mb-6">
              常见问题
            </h1>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              关于 GEO 和 FindableX 的常见疑问解答，帮助您快速了解和上手
            </p>
          </div>
        </section>

        {/* FAQ Categories */}
        <section className="pb-20 lg:pb-32">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="space-y-16">
              {faqCategories.map((category) => (
                <div key={category.title}>
                  <h2 className="font-display text-2xl font-bold text-white mb-8">
                    {category.title}
                  </h2>
                  <FAQAccordion items={category.faqs} />
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 bg-gradient-to-b from-slate-800/50 to-slate-900">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="font-display text-2xl lg:text-3xl font-bold text-white mb-6">
              还有其他问题？
            </h2>
            <p className="text-slate-400 mb-8">
              如果您的问题没有在这里找到答案，欢迎联系我们的支持团队
            </p>
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-6 py-3 rounded-lg font-medium transition-all"
            >
              联系我们
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>

        <Footer />
      </div>
    </>
  );
}
