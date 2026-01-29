import { Metadata } from 'next';
import { generatePageMetadata, generateBreadcrumbSchema, JsonLd } from '@/lib/seo';

export const metadata: Metadata = generatePageMetadata({
  title: '样例报告 - AI 可见性分析报告演示',
  description:
    '查看 FindableX GEO 体检报告样例，了解 AI 可见性分析报告的内容结构，包括综合评分、引擎覆盖率、竞争对比、关键洞察和优化建议。',
  path: '/sample-report',
});

export default function SampleReportLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <JsonLd
        data={generateBreadcrumbSchema([
          { name: '首页', url: '/' },
          { name: '样例报告', url: '/sample-report' },
        ])}
      />
      {children}
    </>
  );
}
