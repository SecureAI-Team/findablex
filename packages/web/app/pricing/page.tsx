import { Metadata } from 'next';
import Link from 'next/link';
import { Check, ArrowRight } from 'lucide-react';
import { Header, Footer, PricingCard } from '@/components';
import { generatePageMetadata, generatePricingSchema, generateBreadcrumbSchema, JsonLd } from '@/lib/seo';

export const metadata: Metadata = generatePageMetadata({
  title: '定价方案 - GEO 体检服务价格',
  description:
    'FindableX GEO 体检平台定价方案：免费版（每月 10 次体检）、专业版和企业版（面议）。灵活选择，满足从个人到企业的 AI 可见性监测需求。',
  path: '/pricing',
});

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
    cta: '联系咨询',
    ctaHref: '/contact',
  },
];

const faqs = [
  {
    question: '可以随时升级或降级套餐吗？',
    answer:
      '可以。您可以随时升级到更高级别的套餐，费用按剩余天数比例计算。降级将在当前计费周期结束后生效。',
  },
  {
    question: '支持哪些付款方式？',
    answer:
      '我们支持支付宝、微信支付、银行卡等多种付款方式。企业客户还可以选择对公转账。',
  },
  {
    question: '有没有年付优惠？',
    answer: '有的。选择年付可享受 8 折优惠，相当于免费使用 2 个月以上。',
  },
  {
    question: '试用期内可以取消吗？',
    answer:
      '专业版提供 14 天免费试用期，试用期内可随时取消，不会产生任何费用。',
  },
];

export default function PricingPage() {
  return (
    <>
      <JsonLd data={generateBreadcrumbSchema([
        { name: '首页', url: '/' },
        { name: '定价方案', url: '/pricing' },
      ])} />
      <JsonLd
        data={generatePricingSchema([
          { name: '免费版', description: '个人体验', price: 0, currency: 'CNY' },
          {
            name: '专业版',
            description: '专业团队（面议）',
            price: 0,
            currency: 'CNY',
          },
          {
            name: '企业版',
            description: '企业定制（面议）',
            price: 0,
            currency: 'CNY',
          },
        ])}
      />

      <div className="min-h-screen bg-slate-900">
        <Header />

        {/* Hero */}
        <section className="pt-32 lg:pt-40 pb-16 lg:pb-20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h1 className="font-display text-4xl lg:text-5xl font-bold text-white mb-6">
              透明定价，按需选择
            </h1>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              从免费体验到企业定制，FindableX 提供灵活的方案满足您的 GEO 分析需求
            </p>
          </div>
        </section>

        {/* Pricing Cards */}
        <section className="pb-20 lg:pb-32">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid md:grid-cols-3 gap-8">
              {pricingPlans.map((plan) => (
                <PricingCard key={plan.name} {...plan} />
              ))}
            </div>
          </div>
        </section>

        {/* Feature Comparison */}
        <section className="py-20 lg:py-32 bg-slate-800/30">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="font-display text-2xl lg:text-3xl font-bold text-white text-center mb-12">
              功能对比
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-4 px-4 text-slate-400 font-medium">
                      功能
                    </th>
                    <th className="text-center py-4 px-4 text-slate-300 font-medium">
                      免费版
                    </th>
                    <th className="text-center py-4 px-4 text-primary-400 font-medium">
                      专业版
                    </th>
                    <th className="text-center py-4 px-4 text-slate-300 font-medium">
                      企业版
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50">
                  {[
                    ['每月体检次数', '10', '100', '无限'],
                    ['项目数量', '3', '无限', '无限'],
                    ['数据保留', '7 天', '90 天', '无限'],
                    ['基础指标', true, true, true],
                    ['高级指标', false, true, true],
                    ['漂移监测', false, true, true],
                    ['报告导出', false, true, true],
                    ['API 访问', false, false, true],
                    ['科研实验', false, false, true],
                    ['专属支持', false, false, true],
                  ].map(([feature, free, pro, enterprise], i) => (
                    <tr key={i}>
                      <td className="py-4 px-4 text-slate-300">{feature}</td>
                      <td className="py-4 px-4 text-center">
                        {typeof free === 'boolean' ? (
                          free ? (
                            <Check className="w-5 h-5 text-green-400 mx-auto" />
                          ) : (
                            <span className="text-slate-600">—</span>
                          )
                        ) : (
                          <span className="text-slate-400">{free}</span>
                        )}
                      </td>
                      <td className="py-4 px-4 text-center">
                        {typeof pro === 'boolean' ? (
                          pro ? (
                            <Check className="w-5 h-5 text-primary-400 mx-auto" />
                          ) : (
                            <span className="text-slate-600">—</span>
                          )
                        ) : (
                          <span className="text-primary-400">{pro}</span>
                        )}
                      </td>
                      <td className="py-4 px-4 text-center">
                        {typeof enterprise === 'boolean' ? (
                          enterprise ? (
                            <Check className="w-5 h-5 text-green-400 mx-auto" />
                          ) : (
                            <span className="text-slate-600">—</span>
                          )
                        ) : (
                          <span className="text-slate-400">{enterprise}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="py-20 lg:py-32">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="font-display text-2xl lg:text-3xl font-bold text-white text-center mb-12">
              定价常见问题
            </h2>

            <div className="space-y-6">
              {faqs.map((faq, i) => (
                <div
                  key={i}
                  className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50"
                >
                  <h3 className="font-medium text-white mb-2">{faq.question}</h3>
                  <p className="text-slate-400 text-sm">{faq.answer}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 bg-gradient-to-b from-slate-800/50 to-slate-900">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="font-display text-2xl lg:text-3xl font-bold text-white mb-6">
              还有疑问？
            </h2>
            <p className="text-slate-400 mb-8">
              我们的团队随时为您解答关于定价和功能的任何问题
            </p>
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-6 py-3 rounded-lg font-medium transition-all"
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
