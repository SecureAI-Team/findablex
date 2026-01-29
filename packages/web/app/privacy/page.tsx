import { Metadata } from 'next';
import { Header, Footer } from '@/components';
import { generatePageMetadata } from '@/lib/seo';

export const metadata: Metadata = generatePageMetadata({
  title: '隐私政策',
  description:
    'FindableX 隐私政策。了解我们如何收集、使用和保护您的个人信息。',
  path: '/privacy',
});

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-slate-900">
      <Header />

      {/* Content */}
      <section className="pt-32 lg:pt-40 pb-20 lg:pb-32">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="font-display text-4xl lg:text-5xl font-bold text-white mb-8">
            隐私政策
          </h1>

          <div className="text-slate-400 text-sm mb-8">
            最后更新日期：2026 年 1 月 1 日
          </div>

          <div className="prose prose-invert prose-slate max-w-none">
            <div className="space-y-8 text-slate-300 leading-relaxed">
              <section>
                <h2 className="text-xl font-semibold text-white mb-4">1. 概述</h2>
                <p>
                  FindableX（以下简称"我们"）非常重视用户隐私保护。本隐私政策说明了我们如何收集、使用、存储和保护您的个人信息。使用我们的服务即表示您同意本政策的条款。
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  2. 信息收集
                </h2>
                <p>我们收集以下类型的信息：</p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>
                    <strong className="text-white">账户信息</strong>
                    ：注册时提供的邮箱地址、姓名等
                  </li>
                  <li>
                    <strong className="text-white">使用数据</strong>
                    ：您上传的 AI 搜索结果、创建的项目、生成的报告等
                  </li>
                  <li>
                    <strong className="text-white">日志信息</strong>
                    ：访问时间、IP 地址、浏览器类型等
                  </li>
                  <li>
                    <strong className="text-white">支付信息</strong>
                    ：如果您购买付费服务，我们通过安全的第三方支付处理商处理支付信息
                  </li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  3. 信息使用
                </h2>
                <p>我们使用收集的信息用于：</p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>提供、维护和改进我们的服务</li>
                  <li>处理您的请求和交易</li>
                  <li>发送服务通知和更新</li>
                  <li>分析使用趋势以改进用户体验</li>
                  <li>防止欺诈和保护安全</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  4. 信息共享
                </h2>
                <p>
                  我们不会出售您的个人信息。我们仅在以下情况下共享信息：
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>经您明确同意</li>
                  <li>与服务提供商合作（如云服务、支付处理）</li>
                  <li>遵守法律要求或响应合法的法律程序</li>
                  <li>
                    科研数据共享（仅当您主动选择参与，且数据经过去标识化处理）
                  </li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  5. 数据安全
                </h2>
                <p>
                  我们采取多种安全措施保护您的信息：
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>数据传输采用 TLS 加密</li>
                  <li>敏感数据存储采用 AES-256 加密</li>
                  <li>定期进行安全审计和漏洞扫描</li>
                  <li>严格的访问控制和权限管理</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  6. 数据保留
                </h2>
                <p>
                  我们根据您的订阅计划保留数据（免费版 7 天，专业版 90
                  天，企业版无限期）。您可以随时删除您的项目和数据。账户删除后，我们将在
                  30 天内删除所有关联数据。
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  7. 您的权利
                </h2>
                <p>您有权：</p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>访问和获取您的个人信息副本</li>
                  <li>更正不准确的信息</li>
                  <li>删除您的账户和数据</li>
                  <li>导出您的数据</li>
                  <li>撤回同意（如科研数据共享）</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  8. Cookie 使用
                </h2>
                <p>
                  我们使用 Cookie 和类似技术来记住您的偏好、分析网站流量。您可以通过浏览器设置控制
                  Cookie 的使用。
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  9. 儿童隐私
                </h2>
                <p>
                  我们的服务不面向 18 岁以下的用户。我们不会故意收集儿童的个人信息。
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  10. 政策更新
                </h2>
                <p>
                  我们可能会不时更新本隐私政策。更新后的政策将在本页面发布，重大变更将通过邮件通知您。
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  11. 联系我们
                </h2>
                <p>
                  如果您对本隐私政策有任何疑问，请通过以下方式联系我们：
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>邮箱：privacy@findablex.com</li>
                </ul>
              </section>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
