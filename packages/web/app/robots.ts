import { MetadataRoute } from 'next';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://findablex.com';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: [
          '/api/',
          '/dashboard/',
          '/projects/',
          '/reports/',
          '/settings/',
          '/admin/',
          '/share/',
          '/team/',
          '/subscription/',
        ],
      },
      {
        userAgent: 'GPTBot',
        allow: [
          '/',
          '/about',
          '/pricing',
          '/faq',
          '/sample-report',
          '/articles',
          '/articles/*',
          '/research',
        ],
        disallow: ['/api/', '/dashboard/', '/admin/'],
      },
      {
        userAgent: 'ChatGPT-User',
        allow: [
          '/',
          '/about',
          '/pricing',
          '/faq',
          '/sample-report',
          '/articles',
          '/articles/*',
          '/research',
        ],
        disallow: ['/api/', '/dashboard/', '/admin/'],
      },
      {
        userAgent: 'PerplexityBot',
        allow: [
          '/',
          '/about',
          '/pricing',
          '/faq',
          '/sample-report',
          '/articles',
          '/articles/*',
          '/research',
        ],
        disallow: ['/api/', '/dashboard/', '/admin/'],
      },
      {
        userAgent: 'Google-Extended',
        allow: '/',
      },
      {
        userAgent: 'Bingbot',
        allow: '/',
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
