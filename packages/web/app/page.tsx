import Link from 'next/link';
import Image from 'next/image';
import {
  ArrowRight,
  BarChart3,
  FileSearch,
  Shield,
  Zap,
  Upload,
  LineChart,
  FileText,
  Target,
  Building2,
  GraduationCap,
  TrendingUp,
  Bot,
  Search,
  AlertTriangle,
  Eye,
  Users,
  TrendingDown,
  Newspaper,
  Calendar,
  Clock,
  Quote,
  Chrome,
  Puzzle,
  Download,
  MonitorSmartphone,
  Sparkles,
} from 'lucide-react';
import { Header, Footer, FeatureCard, StepCard, PricingCard, FAQAccordion, PageViewTracker } from '@/components';
import { generateFAQSchema, generateSoftwareAppSchema, generateServiceSchema, generateBreadcrumbSchema, JsonLd } from '@/lib/seo';
import { getFeaturedArticles } from '@/lib/articles';
import { Metadata } from 'next';

// 首页专属 SEO 元数据
export const metadata: Metadata = {
  title: 'FindableX - GEO 体检平台 | 监测品牌在 AI 搜索中的可见性',
  description:
    'FindableX 是专业的 GEO（生成式引擎优化）体检平台。用行业问题集，体检您的品牌在 ChatGPT、Perplexity、通义千问等 AI 引擎中的被提及、被引用情况，识别口径错误与合规风险。免费开始体检。',
  keywords: [
    'GEO 体检',
    'AI 可见性',
    'ChatGPT 品牌监测',
    'Perplexity 排名',
    '通义千问优化',
    '品牌 AI 搜索',
    '生成式引擎优化',
  ],
};

const painPoints = [
  {
    icon: TrendingDown,
    title: '传统 SEO 失效',
    description:
      'AI 搜索引擎直接生成答案，用户不再点击传统搜索结果，您的 SEO 投入正在失去效果。',
  },
  {
    icon: Eye,
    title: '可见性盲区',
    description:
      '您不知道品牌是否被 ChatGPT、Perplexity 等 AI 引用，无法评估真实的营销效果。',
  },
  {
    icon: Users,
    title: '竞争失察',
    description:
      '不了解竞争对手在 AI 搜索中的表现，无法制定有效的差异化策略。',
  },
  {
    icon: AlertTriangle,
    title: '优化无据',
    description:
      '没有数据支撑 GEO 优化决策，只能盲目投入资源，效果难以衡量。',
  },
];

const features = [
  {
    icon: FileSearch,
    title: '智能引用分析',
    description:
      '自动提取 AI 引擎响应中的所有引用来源，深度分析您的品牌被引用的频率、位置和上下文。',
  },
  {
    icon: BarChart3,
    title: '多维指标计算',
    description:
      '可见性覆盖率、平均引用位置、Top3 出现率、竞争对手占比等核心 GEO 指标实时计算。',
  },
  {
    icon: Zap,
    title: '漂移监测预警',
    description:
      '定期自动复测，实时检测排名变化，当可见性下降时及时预警，帮助您快速响应。',
  },
  {
    icon: Shield,
    title: '科研实验支持',
    description:
      '对照实验设计、A/B 测试、批量运行、数据集导出，支持学术研究和深度分析需求。',
  },
];

const steps = [
  {
    number: 1,
    title: '导入数据',
    description: '上传 AI 引擎的搜索结果，支持 CSV、JSON 格式或直接粘贴。',
  },
  {
    number: 2,
    title: '智能分析',
    description: '系统自动提取引用、识别品牌、计算各项 GEO 指标。',
  },
  {
    number: 3,
    title: '生成报告',
    description: '获得详细的可见性分析报告，包含优化建议和竞争对比。',
  },
  {
    number: 4,
    title: '持续优化',
    description: '定期复测跟踪变化，根据数据驱动的洞察不断优化策略。',
  },
];

const useCases = [
  {
    icon: Building2,
    title: '品牌营销团队',
    description:
      '监测品牌在 AI 搜索中的曝光情况，了解用户通过 AI 获取品牌信息的方式，优化内容策略。',
  },
  {
    icon: Target,
    title: '竞争情报分析',
    description:
      '追踪竞争对手在各 AI 引擎中的表现，发现差距和机会，制定差异化策略。',
  },
  {
    icon: GraduationCap,
    title: '学术研究',
    description:
      '研究 AI 引擎的引用行为、偏见和变化趋势，支持论文数据需求和可重复实验。',
  },
];

const pricingPlans = [
  {
    name: '免费版',
    description: '适合个人用户体验',
    price: 0,
    features: [
      '每月 10 次体检',
      '最多 3 个项目',
      '基础指标分析',
      '7 天数据保留',
      '社区支持',
    ],
    cta: '免费开始',
    ctaHref: '/register',
  },
  {
    name: '专业版',
    description: '适合专业营销团队',
    price: '面议',
    features: [
      '每月 100 次体检',
      '无限项目',
      '高级指标分析',
      '漂移监测预警',
      '报告导出与分享',
      '90 天数据保留',
      '专属支持',
    ],
    cta: '联系咨询',
    ctaHref: '/contact',
    popular: true,
  },
  {
    name: '企业版',
    description: '适合大型企业和机构',
    price: '面议',
    features: [
      '无限次体检',
      '无限项目',
      '科研实验功能',
      'API 访问',
      '自定义指标',
      '无限数据保留',
      '专属客户经理',
      'SLA 保障',
    ],
    cta: '联系销售',
    ctaHref: '/contact',
  },
];

const faqs = [
  {
    question: '什么是 GEO（Generative Engine Optimization）？',
    answer:
      'GEO 是 Generative Engine Optimization 的缩写，即生成式引擎优化。随着 ChatGPT、Perplexity、Google SGE 等 AI 搜索引擎的兴起，用户越来越多地通过 AI 获取信息。GEO 关注的是如何让您的品牌和内容在这些 AI 生成的回答中被引用和推荐。',
  },
  {
    question: 'GEO 和 SEO 有什么区别？',
    answer:
      'SEO（搜索引擎优化）关注传统搜索引擎的排名，如 Google、百度的网页搜索结果。而 GEO 关注的是 AI 生成式搜索引擎，这些引擎不再简单展示网页列表，而是直接生成回答并引用来源。两者的优化策略和衡量指标都有所不同。',
  },
  {
    question: 'FindableX 支持哪些 AI 引擎？',
    answer:
      '目前我们支持分析来自 ChatGPT、Perplexity、Google SGE、Bing Copilot、通义千问等主流 AI 搜索引擎的结果。您可以导入这些引擎的搜索结果进行分析。',
  },
  {
    question: '数据是如何获取的？',
    answer:
      '我们采用用户主动导入的方式获取数据。您可以将 AI 引擎的搜索结果以 CSV、JSON 格式上传，或直接复制粘贴。我们也提供可选的 API 集成方案（需用户提供 API Token）。平台不会主动爬取任何第三方网站。',
  },
  {
    question: '我的数据安全吗？',
    answer:
      '绝对安全。所有数据都经过加密存储，我们遵循严格的数据安全标准。您可以随时导出或删除您的数据。如果您选择参与科研数据共享，我们会对数据进行去标识化处理。',
  },
  {
    question: '如何衡量 GEO 效果？',
    answer:
      '我们提供多维度的指标：可见性覆盖率（您的品牌被引用的查询比例）、平均引用位置、Top3 出现率、竞争对手占比等。通过定期复测，您可以追踪这些指标的变化趋势。',
  },
];

export default function HomePage() {
  return (
    <>
      {/* 结构化数据 for SEO */}
      <JsonLd data={generateSoftwareAppSchema()} />
      <JsonLd data={generateServiceSchema()} />
      <JsonLd data={generateFAQSchema(faqs)} />
      <JsonLd data={generateBreadcrumbSchema([
        { name: '首页', url: '/' },
      ])} />
      
      {/* 页面浏览追踪 */}
      <PageViewTracker pageName="landing_page" properties={{ page_type: 'marketing' }} />

      <div className="min-h-screen bg-slate-900">
        <Header />

        {/* Hero Section */}
        <section className="relative pt-32 lg:pt-40 pb-20 lg:pb-32 overflow-hidden">
          {/* Background */}
          <div className="absolute inset-0">
            <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
            <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center opacity-20" />
            <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-500/20 rounded-full blur-3xl" />
            <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-500/20 rounded-full blur-3xl" />
          </div>

          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-4xl mx-auto">
              {/* Badge */}
              <div className="inline-flex items-center gap-2 bg-primary-500/10 border border-primary-500/20 rounded-full px-4 py-1.5 mb-8">
                <Bot className="w-4 h-4 text-primary-400" />
                <span className="text-primary-400 text-sm font-medium">
                  AI 时代的品牌可见性体检
                </span>
              </div>

              {/* Title */}
              <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-bold text-white tracking-tight mb-6">
                AI 搜索
                <span className="bg-gradient-to-r from-primary-400 to-accent-400 bg-clip-text text-transparent">
                  {' '}说对了吗？{' '}
                </span>
              </h1>

              {/* Subtitle - 行业痛点入手 */}
              <p className="text-lg lg:text-xl text-slate-300 max-w-3xl mx-auto mb-10 leading-relaxed">
                用<span className="text-white font-medium">行业采购问题集</span>，体检您的品牌在 AI 搜索/回答中的被提及、被引用情况，
                <span className="text-amber-400">识别口径错误与合规风险</span>。
              </p>

              {/* CTA Buttons */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link
                  href="/register"
                  className="w-full sm:w-auto bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-white px-8 py-4 rounded-xl font-medium text-lg transition-all hover:shadow-xl hover:shadow-primary-500/25 flex items-center justify-center gap-2 group"
                >
                  开始体检（免费 10 条）
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>
                <Link
                  href="/sample-report"
                  className="w-full sm:w-auto text-slate-300 hover:text-white px-8 py-4 rounded-xl font-medium text-lg border border-slate-600 hover:border-slate-500 transition-all flex items-center justify-center gap-2"
                >
                  <FileText className="w-5 h-5" />
                  查看样例报告
                </Link>
              </div>
              
              {/* Quick note */}
              <p className="mt-4 text-sm text-slate-500">
                无需信用卡 · 1分钟注册 · 立即获得洞察
              </p>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-8 max-w-lg mx-auto mt-16 pt-8 border-t border-slate-700/50">
                {[
                  { value: '10K+', label: '体检次数' },
                  { value: '500+', label: '活跃用户' },
                  { value: '95%', label: '满意度' },
                ].map((stat) => (
                  <div key={stat.label} className="text-center">
                    <div className="font-display text-2xl lg:text-3xl font-bold text-white">
                      {stat.value}
                    </div>
                    <div className="text-slate-400 text-sm mt-1">{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* What is GEO Section */}
        <section className="py-20 lg:py-32 bg-slate-800/30">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
              {/* Content */}
              <div>
                <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-6">
                  什么是 GEO？
                  <br />
                  <span className="text-primary-400">为什么它很重要？</span>
                </h2>
                <div className="space-y-4 text-slate-300 leading-relaxed">
                  <p>
                    <strong className="text-white">GEO（Generative Engine Optimization）</strong>
                    是生成式引擎优化的缩写。随着 ChatGPT、Perplexity 等 AI
                    搜索引擎的普及，越来越多的用户直接通过 AI 获取信息和建议。
                  </p>
                  <p>
                    与传统 SEO 不同，GEO
                    关注的是您的品牌在 AI 生成的回答中被引用和推荐的程度。
                    AI 引擎不再只是展示链接列表，而是直接生成答案——您的品牌是否出现在这些答案中，决定了用户能否找到您。
                  </p>
                  <p>
                    研究表明，超过{' '}
                    <strong className="text-primary-400">40% 的 Z 世代</strong>{' '}
                    用户更倾向于使用 AI 搜索。GEO 不是未来，而是现在。
                  </p>
                </div>
              </div>

              {/* Comparison */}
              <div className="bg-slate-800/50 rounded-2xl p-6 lg:p-8 border border-slate-700/50">
                <h3 className="font-display text-xl font-semibold text-white mb-6 text-center">
                  SEO vs GEO
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {/* SEO Column */}
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 pb-3 border-b border-slate-700">
                      <Search className="w-5 h-5 text-slate-400" />
                      <span className="font-medium text-slate-300">传统 SEO</span>
                    </div>
                    <div className="space-y-3 text-sm text-slate-400">
                      <p>• 优化网页排名</p>
                      <p>• 关注关键词匹配</p>
                      <p>• 展示链接列表</p>
                      <p>• 点击率为王</p>
                    </div>
                  </div>
                  {/* GEO Column */}
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 pb-3 border-b border-primary-500/50">
                      <Bot className="w-5 h-5 text-primary-400" />
                      <span className="font-medium text-primary-400">新时代 GEO</span>
                    </div>
                    <div className="space-y-3 text-sm text-slate-300">
                      <p>• 优化 AI 引用率</p>
                      <p>• 关注语义理解</p>
                      <p>• 直接生成答案</p>
                      <p>• 被引用为王</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Pain Points Section */}
        <section className="py-20 lg:py-32">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <div className="inline-flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-full px-4 py-1.5 mb-6">
                <AlertTriangle className="w-4 h-4 text-red-400" />
                <span className="text-red-400 text-sm font-medium">
                  品牌面临的挑战
                </span>
              </div>
              <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
                您的品牌正在被 AI 时代甩在身后吗？
              </h2>
              <p className="text-slate-400 text-lg">
                AI 搜索正在改变用户获取信息的方式，传统营销策略已经不够
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              {painPoints.map((point) => (
                <div
                  key={point.title}
                  className="bg-slate-800/30 rounded-2xl p-6 lg:p-8 border border-red-500/10 hover:border-red-500/30 transition-all"
                >
                  <div className="w-12 h-12 lg:w-14 lg:h-14 bg-red-500/10 rounded-xl flex items-center justify-center mb-5">
                    <point.icon className="w-6 h-6 lg:w-7 lg:h-7 text-red-400" />
                  </div>
                  <h3 className="font-display text-lg lg:text-xl font-semibold text-white mb-3">
                    {point.title}
                  </h3>
                  <p className="text-slate-400 text-sm lg:text-base leading-relaxed">
                    {point.description}
                  </p>
                </div>
              ))}
            </div>

            {/* Transition to solution */}
            <div className="mt-16 text-center">
              <div className="inline-flex items-center gap-3 bg-gradient-to-r from-primary-500/10 to-accent-500/10 border border-primary-500/20 rounded-full px-6 py-3">
                <span className="text-slate-300">好消息是：</span>
                <span className="text-primary-400 font-medium">FindableX 可以帮您解决这些问题</span>
                <ArrowRight className="w-4 h-4 text-primary-400" />
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="py-20 lg:py-32 bg-slate-800/30">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
                强大的功能，简单的操作
              </h2>
              <p className="text-slate-400 text-lg">
                全方位的 GEO 可见性监测与优化工具，助您在 AI 时代赢得先机
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              {features.map((feature) => (
                <FeatureCard
                  key={feature.title}
                  icon={feature.icon}
                  title={feature.title}
                  description={feature.description}
                />
              ))}
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section id="how-it-works" className="py-20 lg:py-32">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
                简单四步，开启 GEO 体检
              </h2>
              <p className="text-slate-400 text-lg">
                无需技术背景，几分钟即可获得专业的可见性分析报告
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-4">
              {steps.map((step, index) => (
                <StepCard
                  key={step.number}
                  number={step.number}
                  title={step.title}
                  description={step.description}
                  isLast={index === steps.length - 1}
                />
              ))}
            </div>
          </div>
        </section>

        {/* Use Cases Section */}
        <section className="py-20 lg:py-32 bg-slate-800/30">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
                谁在使用 FindableX？
              </h2>
              <p className="text-slate-400 text-lg">
                从品牌营销到学术研究，FindableX 服务于各种 GEO 分析需求
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              {useCases.map((useCase) => (
                <div
                  key={useCase.title}
                  className="bg-gradient-to-b from-slate-800/50 to-transparent rounded-2xl p-8 border border-slate-700/50 text-center"
                >
                  <div className="w-16 h-16 bg-gradient-to-br from-primary-500/20 to-accent-500/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
                    <useCase.icon className="w-8 h-8 text-primary-400" />
                  </div>
                  <h3 className="font-display text-xl font-semibold text-white mb-3">
                    {useCase.title}
                  </h3>
                  <p className="text-slate-400 leading-relaxed">
                    {useCase.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Expert Quotes & Industry Data Section */}
        <section className="py-20 lg:py-32">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <div className="inline-flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 rounded-full px-4 py-1.5 mb-6">
                <Quote className="w-4 h-4 text-amber-400" />
                <span className="text-amber-400 text-sm font-medium">
                  权威观点
                </span>
              </div>
              <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
                行业领袖怎么看 AI 搜索？
              </h2>
              <p className="text-slate-400 text-lg">
                来自 Gartner、普林斯顿大学等权威机构的研究与洞察
              </p>
            </div>

            {/* Key Statistics */}
            <div className="grid md:grid-cols-4 gap-6 mb-16">
              {[
                { value: '25%', label: '传统搜索流量预计下降', source: 'Gartner 2024' },
                { value: '40%', label: 'Z 世代首选 AI 搜索', source: 'Pew Research' },
                { value: '3 亿+', label: 'ChatGPT 周活跃用户', source: 'OpenAI' },
                { value: '73%', label: '用户信任 AI 推荐品牌', source: 'HBR 调研' },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50 text-center"
                >
                  <div className="font-display text-3xl lg:text-4xl font-bold text-primary-400 mb-2">
                    {stat.value}
                  </div>
                  <div className="text-white font-medium mb-1">{stat.label}</div>
                  <div className="text-xs text-slate-500">{stat.source}</div>
                </div>
              ))}
            </div>

            {/* Expert Quotes */}
            <div className="grid md:grid-cols-2 gap-8">
              <div className="bg-gradient-to-br from-slate-800/80 to-slate-800/40 rounded-2xl p-8 border border-slate-700/50 relative">
                <Quote className="absolute top-6 right-6 w-8 h-8 text-primary-500/20" />
                <blockquote className="text-lg text-slate-300 leading-relaxed mb-6">
                  "到 2026 年，传统搜索引擎的流量将下降 25%。这不是衰退，而是向 AI 驱动的搜索体验的转型。品牌需要重新思考'被发现'的含义。"
                </blockquote>
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-primary-500/20 rounded-full flex items-center justify-center">
                    <span className="text-primary-400 font-bold">G</span>
                  </div>
                  <div>
                    <div className="text-white font-medium">Gartner</div>
                    <div className="text-sm text-slate-500">Predicts 2024: Search Will Transform</div>
                  </div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-slate-800/80 to-slate-800/40 rounded-2xl p-8 border border-slate-700/50 relative">
                <Quote className="absolute top-6 right-6 w-8 h-8 text-amber-500/20" />
                <blockquote className="text-lg text-slate-300 leading-relaxed mb-6">
                  "我们的研究表明，通过特定的优化策略，内容在生成式 AI 搜索结果中的可见性可以提升 40% 以上。这证明 GEO 是可行的，也是必要的。"
                </blockquote>
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-amber-500/20 rounded-full flex items-center justify-center">
                    <span className="text-amber-400 font-bold">P</span>
                  </div>
                  <div>
                    <div className="text-white font-medium">普林斯顿大学 GEO 研究团队</div>
                    <div className="text-sm text-slate-500">GEO: Generative Engine Optimization (2024)</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Browser Extension Promo Section */}
        <section id="extension" className="py-20 lg:py-32">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary-600/20 via-slate-800 to-accent-600/20 border border-primary-500/20">
              {/* Background decorations */}
              <div className="absolute top-0 right-0 w-80 h-80 bg-primary-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
              <div className="absolute bottom-0 left-0 w-64 h-64 bg-accent-500/10 rounded-full blur-3xl translate-y-1/2 -translate-x-1/3" />

              <div className="relative grid lg:grid-cols-2 gap-12 p-8 sm:p-12 lg:p-16 items-center">
                {/* Left: Text content */}
                <div>
                  <div className="inline-flex items-center gap-2 bg-primary-500/10 border border-primary-500/20 rounded-full px-4 py-1.5 mb-6">
                    <Puzzle className="w-4 h-4 text-primary-400" />
                    <span className="text-primary-400 text-sm font-medium">
                      浏览器插件
                    </span>
                  </div>

                  <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
                    安装插件，一键自动采集
                  </h2>

                  <p className="text-slate-300 text-lg mb-6 leading-relaxed">
                    安装 FindableX 浏览器插件后，系统会在后台自动从 ChatGPT、Perplexity、通义千问等 9 大 AI 引擎采集数据 —— 无需手动操作，全程无感知。
                  </p>

                  <ul className="space-y-3 mb-8">
                    {[
                      { icon: Sparkles, text: '登录即开启，全自动后台运行' },
                      { icon: MonitorSmartphone, text: '支持 Chrome、Edge、Firefox 多浏览器' },
                      { icon: Shield, text: '数据通过您自己的浏览器采集，安全可控' },
                      { icon: Zap, text: '智能防检测：自动处理验证码和限速' },
                    ].map((item) => (
                      <li key={item.text} className="flex items-center gap-3 text-slate-300">
                        <div className="flex-shrink-0 w-8 h-8 bg-primary-500/10 rounded-lg flex items-center justify-center">
                          <item.icon className="w-4 h-4 text-primary-400" />
                        </div>
                        {item.text}
                      </li>
                    ))}
                  </ul>

                  <div className="flex flex-wrap gap-3">
                    <a
                      href="/downloads/findablex-chrome.zip"
                      download
                      className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-6 py-3 rounded-xl font-medium transition-all shadow-lg shadow-primary-500/25 hover:shadow-primary-500/40"
                    >
                      <Download className="w-5 h-5" />
                      免费下载插件
                    </a>
                    <Link
                      href="/extension"
                      className="inline-flex items-center gap-2 border border-slate-600 hover:border-slate-500 text-slate-300 hover:text-white px-6 py-3 rounded-xl font-medium transition-all"
                    >
                      查看详情
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                </div>

                {/* Right: Visual mockup */}
                <div className="relative flex justify-center">
                  <div className="w-full max-w-sm">
                    {/* Browser extension popup mockup */}
                    <div className="bg-slate-900 rounded-2xl border border-slate-700 shadow-2xl overflow-hidden">
                      {/* Chrome bar mockup */}
                      <div className="bg-slate-800 px-4 py-2 flex items-center gap-2 border-b border-slate-700">
                        <div className="flex gap-1.5">
                          <div className="w-3 h-3 rounded-full bg-red-500/60" />
                          <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                          <div className="w-3 h-3 rounded-full bg-green-500/60" />
                        </div>
                        <div className="flex-1 bg-slate-700 rounded-md px-3 py-1 text-xs text-slate-400 ml-2">
                          chat.deepseek.com
                        </div>
                        <div className="w-6 h-6 bg-primary-500/20 rounded flex items-center justify-center">
                          <Puzzle className="w-3.5 h-3.5 text-primary-400" />
                        </div>
                      </div>

                      {/* Extension popup mockup */}
                      <div className="p-4">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <span className="text-sm">🔍</span>
                            <span className="text-sm font-semibold text-primary-400">FindableX</span>
                          </div>
                          <div className="w-10 h-5 bg-green-500 rounded-full relative">
                            <div className="absolute right-0.5 top-0.5 w-4 h-4 bg-white rounded-full" />
                          </div>
                        </div>

                        <div className="bg-slate-800 rounded-lg p-3 mb-3 flex items-center justify-between">
                          <span className="text-xs text-slate-300">Hi, 张三</span>
                          <span className="text-xs text-slate-400">今日: 12 完成, 0 失败</span>
                        </div>

                        <div className="flex justify-center gap-2 py-2">
                          {['🔮', '🌙', '☁️', '🤖', '🔍', '🫘', '🧠', '🌐', '💠'].map((emoji, i) => (
                            <div key={i} className="flex flex-col items-center gap-1">
                              <span className="text-sm">{emoji}</span>
                              <div className={`w-1.5 h-1.5 rounded-full ${i < 5 ? 'bg-green-400' : 'bg-slate-600'}`} />
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Floating badges */}
                    <div className="absolute -top-4 -right-4 bg-green-500/20 text-green-400 border border-green-500/30 rounded-full px-3 py-1 text-xs font-medium backdrop-blur-sm">
                      ✓ 自动运行中
                    </div>
                    <div className="absolute -bottom-3 -left-3 bg-primary-500/20 text-primary-400 border border-primary-500/30 rounded-full px-3 py-1 text-xs font-medium backdrop-blur-sm">
                      9 个引擎已连接
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Articles Section - 资讯中心 */}
        <section id="articles" className="py-20 lg:py-32 bg-slate-800/30">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <div className="inline-flex items-center gap-2 bg-primary-500/10 border border-primary-500/20 rounded-full px-4 py-1.5 mb-6">
                <Newspaper className="w-4 h-4 text-primary-400" />
                <span className="text-primary-400 text-sm font-medium">
                  GEO 资讯中心
                </span>
              </div>
              <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
                GEO 洞察与实战指南
              </h2>
              <p className="text-slate-400 text-lg">
                深度解读生成式引擎优化策略，帮助您在 AI 搜索时代保持领先
              </p>
            </div>

            {/* First row: 3 articles */}
            <div className="grid md:grid-cols-3 gap-8">
              {getFeaturedArticles().slice(0, 3).map((article) => (
                <article
                  key={article.slug}
                  className="bg-slate-800/50 rounded-2xl border border-slate-700/50 overflow-hidden hover:border-primary-500/50 transition-all group"
                >
                  <div className="h-48 relative overflow-hidden">
                    <Image
                      src={article.image}
                      alt={article.title}
                      fill
                      className="object-cover group-hover:scale-105 transition-transform duration-300"
                      sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 33vw"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-900/60 to-transparent" />
                    <span className="absolute top-4 right-4 text-xs font-medium text-amber-400 bg-amber-500/20 backdrop-blur px-2 py-1 rounded">
                      精选
                    </span>
                  </div>

                  <div className="p-6">
                    <span className="text-xs font-medium text-primary-400 bg-primary-500/10 px-2 py-1 rounded">
                      {article.category}
                    </span>

                    <h3 className="font-display text-lg font-semibold text-white mt-3 mb-3 group-hover:text-primary-400 transition-colors line-clamp-2">
                      <Link href={`/articles/${article.slug}`}>
                        {article.title}
                      </Link>
                    </h3>

                    <p className="text-slate-400 text-sm mb-4 line-clamp-2">
                      {article.excerpt}
                    </p>

                    <div className="flex items-center gap-4 text-xs text-slate-500 mb-4">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {new Date(article.publishedAt).toLocaleDateString('zh-CN')}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {article.readingTime} 分钟
                      </span>
                    </div>

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

            {/* Second row: 2 new articles (wider cards) */}
            {getFeaturedArticles().length > 3 && (
              <div className="grid md:grid-cols-2 gap-8 mt-8">
                {getFeaturedArticles().slice(3).map((article) => (
                  <article
                    key={article.slug}
                    className="bg-slate-800/50 rounded-2xl border border-slate-700/50 overflow-hidden hover:border-primary-500/50 transition-all group md:flex"
                  >
                    {/* Side Image (horizontal layout on desktop) */}
                    <div className="md:w-2/5 h-48 md:h-auto relative overflow-hidden flex-shrink-0">
                      <Image
                        src={article.image}
                        alt={article.title}
                        fill
                        className="object-cover group-hover:scale-105 transition-transform duration-300"
                        sizes="(max-width: 768px) 100vw, 40vw"
                      />
                      <div className="absolute inset-0 bg-gradient-to-r from-transparent to-slate-900/30 hidden md:block" />
                      <div className="absolute inset-0 bg-gradient-to-t from-slate-900/60 to-transparent md:hidden" />
                      <span className="absolute top-4 left-4 text-xs font-medium text-emerald-400 bg-emerald-500/20 backdrop-blur px-2 py-1 rounded">
                        新发布
                      </span>
                    </div>

                    <div className="p-6 flex flex-col justify-center">
                      <span className="text-xs font-medium text-primary-400 bg-primary-500/10 px-2 py-1 rounded w-fit">
                        {article.category}
                      </span>

                      <h3 className="font-display text-lg font-semibold text-white mt-3 mb-3 group-hover:text-primary-400 transition-colors line-clamp-2">
                        <Link href={`/articles/${article.slug}`}>
                          {article.title}
                        </Link>
                      </h3>

                      <p className="text-slate-400 text-sm mb-4 line-clamp-3">
                        {article.excerpt}
                      </p>

                      <div className="flex items-center gap-4 text-xs text-slate-500 mb-4">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {new Date(article.publishedAt).toLocaleDateString('zh-CN')}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {article.readingTime} 分钟
                        </span>
                      </div>

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
            )}

            {/* View All Link */}
            <div className="text-center mt-12">
              <Link
                href="/articles"
                className="inline-flex items-center gap-2 text-slate-300 hover:text-white border border-slate-600 hover:border-slate-500 px-6 py-3 rounded-xl transition-all"
              >
                查看全部文章
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </section>

        {/* Pricing Section */}
        <section id="pricing" className="py-20 lg:py-32">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
                透明定价，按需选择
              </h2>
              <p className="text-slate-400 text-lg">
                从免费体验到企业定制，总有适合您的方案
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
              {pricingPlans.map((plan) => (
                <PricingCard key={plan.name} {...plan} />
              ))}
            </div>
          </div>
        </section>

        {/* FAQ Section */}
        <section id="faq" className="py-20 lg:py-32 bg-slate-800/30">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
                常见问题
              </h2>
              <p className="text-slate-400 text-lg">
                关于 GEO 和 FindableX 的常见疑问解答
              </p>
            </div>

            <FAQAccordion items={faqs} />
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 lg:py-32 bg-gradient-to-b from-slate-800/50 to-slate-900">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-6">
              准备好提升您的 GEO 可见性了吗？
            </h2>
            <p className="text-slate-300 text-lg mb-10 max-w-2xl mx-auto">
              立即注册，免费获得首次 GEO 体检，了解您的品牌在 AI 时代的真实表现。
            </p>
            <Link
              href="/register"
              className="inline-flex items-center gap-2 bg-gradient-to-r from-primary-500 to-accent-500 hover:from-primary-600 hover:to-accent-600 text-white px-10 py-4 rounded-xl font-medium text-lg transition-all hover:shadow-xl hover:shadow-primary-500/25 group"
            >
              免费开始体检
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </section>

        <Footer />
      </div>
    </>
  );
}
