import { Metadata } from 'next';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://findablex.com';
const SITE_NAME = 'FindableX';
const SITE_DESCRIPTION = '专业的 GEO（生成式引擎优化）体检平台，帮助品牌监测和优化在 AI 搜索引擎中的可见性';
const COMPANY_INFO = {
  name: 'FindableX',
  legalName: 'FindableX Inc.',
  foundingDate: '2024',
  founders: ['FindableX Team'],
  address: {
    '@type': 'PostalAddress',
    addressLocality: '上海',
    addressCountry: 'CN',
  },
  contactPoint: {
    '@type': 'ContactPoint',
    contactType: 'customer service',
    email: 'support@findablex.com',
    availableLanguage: ['Chinese', 'English'],
  },
};

export interface PageSEOProps {
  title: string;
  description: string;
  path?: string;
  image?: string;
  noIndex?: boolean;
}

/**
 * Generate page-level metadata for SEO
 */
export function generatePageMetadata({
  title,
  description,
  path = '',
  image = '/og-image.png',
  noIndex = false,
}: PageSEOProps): Metadata {
  const url = `${SITE_URL}${path}`;
  const fullTitle = path === '' ? title : `${title} | ${SITE_NAME}`;

  return {
    title: fullTitle,
    description,
    metadataBase: new URL(SITE_URL),
    alternates: {
      canonical: url,
    },
    openGraph: {
      title: fullTitle,
      description,
      url,
      siteName: SITE_NAME,
      images: [
        {
          url: image,
          width: 1200,
          height: 630,
          alt: title,
        },
      ],
      locale: 'zh_CN',
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title: fullTitle,
      description,
      images: [image],
    },
    robots: noIndex
      ? { index: false, follow: false }
      : { index: true, follow: true },
  };
}

/**
 * JSON-LD Schema for Organization
 */
export function generateOrganizationSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    '@id': `${SITE_URL}/#organization`,
    name: SITE_NAME,
    legalName: COMPANY_INFO.legalName,
    url: SITE_URL,
    logo: {
      '@type': 'ImageObject',
      url: `${SITE_URL}/icon.svg`,
      width: 512,
      height: 512,
    },
    image: `${SITE_URL}/og-image.png`,
    description: SITE_DESCRIPTION,
    foundingDate: COMPANY_INFO.foundingDate,
    address: COMPANY_INFO.address,
    contactPoint: COMPANY_INFO.contactPoint,
    sameAs: [
      // 社交媒体链接 (未来可添加)
    ],
  };
}

/**
 * JSON-LD Schema for WebSite with SearchAction
 */
export function generateWebSiteSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    '@id': `${SITE_URL}/#website`,
    name: SITE_NAME,
    url: SITE_URL,
    description: SITE_DESCRIPTION,
    publisher: {
      '@id': `${SITE_URL}/#organization`,
    },
    inLanguage: 'zh-CN',
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: `${SITE_URL}/dashboard?q={search_term_string}`,
      },
      'query-input': 'required name=search_term_string',
    },
  };
}

/**
 * JSON-LD Schema for BreadcrumbList
 */
export function generateBreadcrumbSchema(
  items: Array<{ name: string; url: string }>
) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: item.url.startsWith('http') ? item.url : `${SITE_URL}${item.url}`,
    })),
  };
}

/**
 * JSON-LD Schema for Article/Blog
 */
export function generateArticleSchema({
  title,
  description,
  url,
  image,
  datePublished,
  dateModified,
  author = 'FindableX Team',
}: {
  title: string;
  description: string;
  url: string;
  image?: string;
  datePublished: string;
  dateModified?: string;
  author?: string;
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: title,
    description,
    url: url.startsWith('http') ? url : `${SITE_URL}${url}`,
    image: image || `${SITE_URL}/og-image.png`,
    datePublished,
    dateModified: dateModified || datePublished,
    author: {
      '@type': 'Person',
      name: author,
    },
    publisher: {
      '@id': `${SITE_URL}/#organization`,
    },
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': url.startsWith('http') ? url : `${SITE_URL}${url}`,
    },
  };
}

/**
 * JSON-LD Schema for Service
 */
export function generateServiceSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Service',
    name: 'GEO 体检服务',
    description: '品牌在 AI 生成式搜索引擎（ChatGPT、Perplexity、通义千问等）中的可见性监测与优化分析服务',
    provider: {
      '@id': `${SITE_URL}/#organization`,
    },
    serviceType: 'GEO Analytics',
    areaServed: {
      '@type': 'Country',
      name: 'China',
    },
    hasOfferCatalog: {
      '@type': 'OfferCatalog',
      name: 'FindableX 订阅方案',
      itemListElement: [
        {
          '@type': 'Offer',
          itemOffered: {
            '@type': 'Service',
            name: '免费版',
            description: '每月 10 次体检，适合个人体验',
          },
          price: '0',
          priceCurrency: 'CNY',
        },
        {
          '@type': 'Offer',
          itemOffered: {
            '@type': 'Service',
            name: '专业版',
            description: '每月 100 次体检，适合专业团队（面议）',
          },
          priceSpecification: {
            '@type': 'PriceSpecification',
            priceCurrency: 'CNY',
            description: '面议',
          },
        },
      ],
    },
  };
}

/**
 * JSON-LD Schema for FAQPage
 */
export function generateFAQSchema(
  faqs: Array<{ question: string; answer: string }>
) {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map((faq) => ({
      '@type': 'Question',
      name: faq.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faq.answer,
      },
    })),
  };
}

/**
 * JSON-LD Schema for SoftwareApplication
 */
export function generateSoftwareAppSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: SITE_NAME,
    applicationCategory: 'BusinessApplication',
    operatingSystem: 'Web',
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'CNY',
      description: '免费开始使用',
    },
    aggregateRating: {
      '@type': 'AggregateRating',
      ratingValue: '4.8',
      ratingCount: '150',
    },
  };
}

/**
 * JSON-LD Schema for Product (Pricing)
 */
export function generatePricingSchema(
  plans: Array<{
    name: string;
    description: string;
    price: number;
    currency: string;
  }>
) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: `${SITE_NAME} 订阅服务`,
    description: 'GEO 体检与优化平台订阅服务',
    offers: plans.map((plan) => ({
      '@type': 'Offer',
      name: plan.name,
      description: plan.description,
      price: plan.price,
      priceCurrency: plan.currency,
      priceValidUntil: new Date(
        new Date().setFullYear(new Date().getFullYear() + 1)
      ).toISOString(),
    })),
  };
}

/**
 * JSON-LD wrapper component
 */
export function JsonLd({ data }: { data: object }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
