import { Metadata } from 'next';
import { generatePageMetadata, generateBreadcrumbSchema, JsonLd } from '@/lib/seo';

export const metadata: Metadata = generatePageMetadata({
  title: '联系我们 - 产品咨询与商务合作',
  description:
    '联系 FindableX 团队，获取 GEO 体检平台的产品咨询、技术支持或商务合作。我们期待为您提供专业的 AI 可见性优化服务。',
  path: '/contact',
});

export default function ContactLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <JsonLd
        data={generateBreadcrumbSchema([
          { name: '首页', url: '/' },
          { name: '联系我们', url: '/contact' },
        ])}
      />
      {children}
    </>
  );
}
