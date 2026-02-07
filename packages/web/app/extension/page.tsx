import Link from 'next/link';
import {
  ArrowRight,
  Chrome,
  Download,
  Puzzle,
  Shield,
  Zap,
  MonitorSmartphone,
  Sparkles,
  Eye,
  CheckCircle2,
  Globe,
} from 'lucide-react';
import { Header, Footer, PageViewTracker } from '@/components';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'FindableX 浏览器插件 - 自动采集 AI 搜索数据',
  description:
    '安装 FindableX 浏览器插件，自动从 ChatGPT、Perplexity、通义千问等 9 大 AI 引擎采集品牌可见性数据。支持 Chrome、Edge、Firefox。',
};

const features = [
  {
    icon: Sparkles,
    title: '全自动后台运行',
    description: '登录后自动开始采集，无需手动操作。插件在后台静默运行，不干扰您的日常浏览。',
  },
  {
    icon: Eye,
    title: '完全无感知',
    description: '采集过程在最小化窗口或折叠标签组中进行，您不会看到任何弹窗或页面跳转。',
  },
  {
    icon: Shield,
    title: '安全可控',
    description: '数据通过您自己的浏览器采集，使用您已登录的 AI 账号，所有数据加密传输。',
  },
  {
    icon: Zap,
    title: '智能防检测',
    description: '自动识别验证码并通知您处理，智能限速和指数退避重试，避免被 AI 引擎封锁。',
  },
  {
    icon: MonitorSmartphone,
    title: '多浏览器支持',
    description: '支持 Chrome、Microsoft Edge、Firefox，一套插件跨平台兼容。',
  },
  {
    icon: Globe,
    title: '覆盖 9 大 AI 引擎',
    description: 'DeepSeek、Kimi、通义千问、ChatGPT、Perplexity、豆包、ChatGLM、Google SGE、Bing Copilot。',
  },
];

const steps = [
  {
    step: '1',
    title: '下载安装插件',
    description: '点击下方按钮下载，将插件安装到您的浏览器中。',
  },
  {
    step: '2',
    title: '登录 FindableX 账号',
    description: '在插件弹窗中使用您的 FindableX 账号登录，插件会自动开启采集模式。',
  },
  {
    step: '3',
    title: '自动采集数据',
    description: '插件在后台自动访问各 AI 引擎，执行查询任务并提取结果，全程无需您操作。',
  },
  {
    step: '4',
    title: '查看分析报告',
    description: '采集的数据自动同步到 FindableX 平台，您可以在仪表板中查看完整的分析报告。',
  },
];

export default function ExtensionPage() {
  return (
    <>
      <PageViewTracker pageName="extension_page" properties={{ page_type: 'extension' }} />

      <div className="min-h-screen bg-slate-900">
        <Header />

        {/* Hero */}
        <section className="relative pt-32 lg:pt-40 pb-20 lg:pb-32 overflow-hidden">
          <div className="absolute inset-0">
            <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900" />
            <div className="absolute top-1/3 left-1/4 w-96 h-96 bg-primary-500/20 rounded-full blur-3xl" />
            <div className="absolute bottom-1/3 right-1/4 w-80 h-80 bg-accent-500/15 rounded-full blur-3xl" />
          </div>

          <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <div className="inline-flex items-center gap-2 bg-primary-500/10 border border-primary-500/20 rounded-full px-4 py-1.5 mb-8">
              <Puzzle className="w-4 h-4 text-primary-400" />
              <span className="text-primary-400 text-sm font-medium">
                浏览器插件 v1.0
              </span>
            </div>

            <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight mb-6">
              安装插件
              <span className="bg-gradient-to-r from-primary-400 to-accent-400 text-transparent bg-clip-text">
                {' '}自动采集{' '}
              </span>
              AI 数据
            </h1>

            <p className="text-slate-400 text-lg sm:text-xl max-w-2xl mx-auto mb-10">
              一次安装，自动从 9 大 AI 搜索引擎采集品牌可见性数据。
              无需手动操作，后台静默运行，数据安全加密传输。
            </p>

            {/* Download buttons */}
            <div className="flex flex-wrap justify-center gap-4 mb-8">
              <a
                href="#"
                className="inline-flex items-center gap-3 bg-primary-500 hover:bg-primary-600 text-white px-8 py-4 rounded-xl font-medium text-lg transition-all shadow-lg shadow-primary-500/25 hover:shadow-primary-500/40"
              >
                <Chrome className="w-6 h-6" />
                Chrome / Edge 下载
              </a>
              <a
                href="#"
                className="inline-flex items-center gap-3 border border-slate-600 hover:border-slate-500 text-slate-300 hover:text-white px-8 py-4 rounded-xl font-medium text-lg transition-all"
              >
                <Globe className="w-6 h-6" />
                Firefox 下载
              </a>
            </div>

            <p className="text-sm text-slate-500">
              没有 FindableX 账号？
              <Link href="/register" className="text-primary-400 hover:text-primary-300 ml-1">
                免费注册
              </Link>
              {' '}后即可使用插件
            </p>
          </div>
        </section>

        {/* Features */}
        <section className="py-20 lg:py-32 bg-slate-800/30">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
                为什么使用浏览器插件？
              </h2>
              <p className="text-slate-400 text-lg">
                利用您自己的浏览器环境采集数据，比服务端爬虫更稳定、更真实
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {features.map((feature) => (
                <div
                  key={feature.title}
                  className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50 hover:border-primary-500/30 transition-all"
                >
                  <div className="w-12 h-12 bg-primary-500/10 rounded-xl flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-primary-400" />
                  </div>
                  <h3 className="font-display text-lg font-semibold text-white mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-slate-400 text-sm leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="py-20 lg:py-32">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
                四步开始使用
              </h2>
            </div>

            <div className="space-y-8">
              {steps.map((item, index) => (
                <div key={item.step} className="flex gap-6 items-start">
                  <div className="flex-shrink-0 w-12 h-12 bg-primary-500/20 rounded-full flex items-center justify-center border border-primary-500/30">
                    <span className="text-primary-400 font-bold text-lg">{item.step}</span>
                  </div>
                  <div className="pt-1">
                    <h3 className="text-white font-semibold text-lg mb-1">{item.title}</h3>
                    <p className="text-slate-400">{item.description}</p>
                  </div>
                  {index < steps.length - 1 && (
                    <div className="hidden" />
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Supported Engines */}
        <section className="py-20 lg:py-32 bg-slate-800/30">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
              支持的 AI 引擎
            </h2>
            <p className="text-slate-400 text-lg mb-12">
              一个插件覆盖国内外主流 AI 搜索引擎
            </p>

            <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-4">
              {[
                { emoji: '🔮', name: 'DeepSeek' },
                { emoji: '🌙', name: 'Kimi' },
                { emoji: '☁️', name: '通义千问' },
                { emoji: '🤖', name: 'ChatGPT' },
                { emoji: '🔍', name: 'Perplexity' },
                { emoji: '🫘', name: '豆包' },
                { emoji: '🧠', name: 'ChatGLM' },
                { emoji: '🌐', name: 'Google SGE' },
                { emoji: '💠', name: 'Bing Copilot' },
              ].map((engine) => (
                <div
                  key={engine.name}
                  className="flex flex-col items-center gap-2 p-4 bg-slate-800/50 rounded-xl border border-slate-700/50"
                >
                  <span className="text-2xl">{engine.emoji}</span>
                  <span className="text-xs text-slate-400 text-center leading-tight">{engine.name}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="py-20 lg:py-32">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
              立即开始自动采集
            </h2>
            <p className="text-slate-400 text-lg mb-8">
              免费注册 FindableX 账号，安装插件后即可自动采集 AI 搜索数据
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <a
                href="#"
                className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-8 py-4 rounded-xl font-medium text-lg transition-all shadow-lg shadow-primary-500/25"
              >
                <Download className="w-5 h-5" />
                下载浏览器插件
              </a>
              <Link
                href="/register"
                className="inline-flex items-center gap-2 border border-slate-600 hover:border-slate-500 text-slate-300 hover:text-white px-8 py-4 rounded-xl font-medium text-lg transition-all"
              >
                免费注册
                <ArrowRight className="w-5 h-5" />
              </Link>
            </div>
          </div>
        </section>

        <Footer />
      </div>
    </>
  );
}
