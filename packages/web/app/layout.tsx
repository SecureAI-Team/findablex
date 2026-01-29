import type { Metadata, Viewport } from 'next';
import { Inter, Space_Grotesk, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import {
  generateOrganizationSchema,
  generateWebSiteSchema,
  JsonLd,
} from '@/lib/seo';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-space-grotesk',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains',
  display: 'swap',
});

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://findablex.com';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: 'FindableX - GEO 体检平台 | AI 搜索品牌可见性监测与优化',
    template: '%s | FindableX',
  },
  description:
    'FindableX 是专业的 GEO（生成式引擎优化）体检平台，帮助品牌监测和提升在 ChatGPT、Perplexity、通义千问等 AI 搜索引擎中的可见性、被引用率和品牌表现。免费开始体检。',
  keywords: [
    'GEO',
    'GEO 优化',
    'Generative Engine Optimization',
    '生成式引擎优化',
    'AI SEO',
    'AI 搜索优化',
    'AI 可见性',
    '品牌可见性监测',
    'ChatGPT 优化',
    'ChatGPT 品牌',
    'Perplexity 排名',
    'AI 引用分析',
    '通义千问优化',
    '数字营销',
    'AI 营销',
    '品牌监测',
    'SEO 替代',
  ],
  authors: [{ name: 'FindableX Team', url: SITE_URL }],
  creator: 'FindableX',
  publisher: 'FindableX',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  category: 'technology',
  classification: 'Business Software',
  openGraph: {
    type: 'website',
    locale: 'zh_CN',
    url: SITE_URL,
    siteName: 'FindableX',
    title: 'FindableX - GEO 体检平台 | AI 搜索品牌可见性监测',
    description:
      '专业的 GEO 体检平台，监测您的品牌在 ChatGPT、Perplexity、通义千问等 AI 搜索引擎中的可见性表现。免费开始体检。',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'FindableX - AI 搜索品牌可见性体检平台',
        type: 'image/png',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FindableX - GEO 体检平台 | AI 搜索品牌可见性',
    description: '监测和优化您的品牌在 AI 生成式搜索引擎中的可见性，免费开始体检',
    images: ['/og-image.png'],
    creator: '@findablex',
  },
  robots: {
    index: true,
    follow: true,
    nocache: false,
    googleBot: {
      index: true,
      follow: true,
      noimageindex: false,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  verification: {
    // google: 'your-google-verification-code',
    // yandex: 'your-yandex-verification-code',
  },
  alternates: {
    canonical: SITE_URL,
    languages: {
      'zh-CN': SITE_URL,
    },
  },
  other: {
    'baidu-site-verification': '', // 百度站长验证
    'msvalidate.01': '', // Bing 验证
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0f172a' },
  ],
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="icon" href="/icon.svg" type="image/svg+xml" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="manifest" href="/manifest.json" />
        <JsonLd data={generateOrganizationSchema()} />
        <JsonLd data={generateWebSiteSchema()} />
      </head>
      <body
        className={`${inter.variable} ${spaceGrotesk.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
