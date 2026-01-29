import { Metadata } from 'next';
import { Header, Footer } from '@/components';
import { generatePageMetadata } from '@/lib/seo';

export const metadata: Metadata = generatePageMetadata({
  title: '服务条款',
  description: 'FindableX 服务条款。使用我们的服务前，请仔细阅读本条款。',
  path: '/terms',
});

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-slate-900">
      <Header />

      {/* Content */}
      <section className="pt-32 lg:pt-40 pb-20 lg:pb-32">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="font-display text-4xl lg:text-5xl font-bold text-white mb-8">
            服务条款
          </h1>

          <div className="text-slate-400 text-sm mb-8">
            最后更新日期：2026 年 1 月 1 日
          </div>

          <div className="prose prose-invert prose-slate max-w-none">
            <div className="space-y-8 text-slate-300 leading-relaxed">
              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  1. 服务接受
                </h2>
                <p>
                  欢迎使用 FindableX 服务（以下简称"服务"）。使用本服务即表示您同意遵守本服务条款（以下简称"条款"）。如果您不同意这些条款，请勿使用本服务。
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  2. 服务描述
                </h2>
                <p>
                  FindableX 是一个 GEO（Generative Engine Optimization）体检平台，提供以下服务：
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>AI 搜索结果的引用分析</li>
                  <li>GEO 指标计算和报告生成</li>
                  <li>可见性变化的漂移监测</li>
                  <li>科研实验功能（部分套餐）</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  3. 账户注册
                </h2>
                <p>
                  使用本服务需要注册账户。您同意：
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>提供真实、准确、完整的注册信息</li>
                  <li>维护和更新您的账户信息</li>
                  <li>保护您的账户凭据安全</li>
                  <li>对您账户下的所有活动负责</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  4. 用户行为规范
                </h2>
                <p>在使用本服务时，您同意不会：</p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>违反任何适用的法律法规</li>
                  <li>侵犯他人的知识产权或隐私权</li>
                  <li>上传恶意软件或有害内容</li>
                  <li>尝试未经授权访问系统或数据</li>
                  <li>干扰服务的正常运行</li>
                  <li>使用自动化工具滥用服务</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  5. 数据来源合规
                </h2>
                <p>
                  您理解并同意，您上传到平台的数据应当通过合法方式获取：
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>手动复制粘贴 AI 搜索结果</li>
                  <li>使用官方 API（需自行获取授权）</li>
                  <li>其他符合相关平台使用条款的方式</li>
                </ul>
                <p className="mt-4">
                  FindableX 不鼓励、不支持任何违反第三方平台使用条款的数据获取行为。您对上传数据的来源合法性负全部责任。
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  6. 知识产权
                </h2>
                <p>
                  您上传的内容的知识产权归您所有。您授予我们有限的许可，允许我们处理您的数据以提供服务。我们的服务、商标、代码等知识产权归
                  FindableX 所有。
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  7. 付费服务
                </h2>
                <p>
                  部分功能需要付费订阅。关于付费服务：
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>费用按照公布的价格收取</li>
                  <li>订阅自动续费，除非您取消</li>
                  <li>退款政策请参阅我们的退款说明</li>
                  <li>我们保留调整价格的权利，会提前通知</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  8. 服务可用性
                </h2>
                <p>
                  我们努力保持服务的稳定运行，但不保证服务永远可用、无中断或无错误。我们可能因维护、升级或其他原因暂停服务，将尽量提前通知。
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  9. 免责声明
                </h2>
                <p>
                  服务按"现状"提供。我们不对以下内容做任何明示或暗示的保证：
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>服务的准确性、可靠性或完整性</li>
                  <li>分析结果的商业适用性</li>
                  <li>基于我们服务做出的决策结果</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  10. 责任限制
                </h2>
                <p>
                  在法律允许的最大范围内，FindableX 及其关联方对任何间接、附带、特殊或后果性损害不承担责任，包括但不限于利润损失、数据丢失等。
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  11. 账户终止
                </h2>
                <p>
                  我们保留因违反本条款而终止或暂停您账户的权利。您也可以随时删除您的账户。账户终止后，您对数据的访问权将终止。
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  12. 条款修改
                </h2>
                <p>
                  我们可能会修改本条款。重大修改将通过邮件或网站公告通知。继续使用服务即表示您接受修改后的条款。
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  13. 法律适用
                </h2>
                <p>
                  本条款受中华人民共和国法律管辖。任何争议应提交至我们所在地有管辖权的法院解决。
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-white mb-4">
                  14. 联系我们
                </h2>
                <p>
                  如果您对本服务条款有任何疑问，请联系：
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>邮箱：legal@findablex.com</li>
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
