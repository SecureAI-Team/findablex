import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// 爬虫/机器人 User-Agent 模式
const BOT_PATTERNS = [
  // 搜索引擎爬虫
  'googlebot',
  'bingbot',
  'baiduspider',
  'yandexbot',
  'duckduckbot',
  'slurp',
  'sogou',
  '360spider',
  'bytespider',
  // AI 爬虫
  'gptbot',
  'chatgpt-user',
  'claudebot',
  'anthropic-ai',
  'perplexitybot',
  'cohere-ai',
  // 社交媒体爬虫
  'facebookexternalhit',
  'twitterbot',
  'linkedinbot',
  'whatsapp',
  'telegrambot',
  'slackbot',
  'discordbot',
  // SEO 工具
  'semrushbot',
  'ahrefsbot',
  'mj12bot',
  'dotbot',
  // 其他常见爬虫
  'applebot',
  'ccbot',
  'ia_archiver',
  'petalbot',
];

// 检测是否是爬虫
function isBot(userAgent: string): string | null {
  const ua = userAgent.toLowerCase();
  for (const pattern of BOT_PATTERNS) {
    if (ua.includes(pattern)) {
      return pattern;
    }
  }
  return null;
}

// 需要追踪的公开页面路径
const TRACKABLE_PATHS = [
  '/',
  '/about',
  '/pricing',
  '/faq',
  '/articles',
  '/research-center',
  '/sample-report',
  '/contact',
  '/terms',
  '/privacy',
];

// 检查路径是否应该追踪
function shouldTrack(pathname: string): boolean {
  // 精确匹配
  if (TRACKABLE_PATHS.includes(pathname)) {
    return true;
  }
  // 文章详情页
  if (pathname.startsWith('/articles/')) {
    return true;
  }
  // 百度验证文件等静态文件
  if (pathname.endsWith('.html') && pathname.startsWith('/baidu_verify')) {
    return true;
  }
  return false;
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const userAgent = request.headers.get('user-agent') || '';
  const referer = request.headers.get('referer') || '';
  
  // 只追踪公开页面的爬虫访问
  if (!shouldTrack(pathname)) {
    return NextResponse.next();
  }
  
  // 检测是否是爬虫
  const botPattern = isBot(userAgent);
  if (!botPattern) {
    return NextResponse.next();
  }
  
  // 异步记录爬虫访问（不阻塞响应）
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  
  // 使用 waitUntil 模式异步发送（如果可用），否则 fire-and-forget
  try {
    // Fire and forget - 不等待响应
    fetch(`${apiUrl}/api/v1/analytics/bot-visit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        path: pathname,
        user_agent: userAgent,
        referer: referer,
        bot_type: botPattern,
        timestamp: new Date().toISOString(),
      }),
    }).catch(() => {
      // 静默忽略错误，不影响页面加载
    });
  } catch {
    // 静默忽略
  }
  
  return NextResponse.next();
}

// 配置 middleware 匹配的路径
export const config = {
  matcher: [
    /*
     * 匹配所有请求路径，除了：
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - 其他静态资源
     */
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|css|js)$).*)',
  ],
};
