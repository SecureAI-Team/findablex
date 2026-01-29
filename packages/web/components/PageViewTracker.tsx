'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { analytics } from '@/lib/analytics';

interface PageViewTrackerProps {
  pageName: string;
  properties?: Record<string, unknown>;
}

/**
 * 客户端组件用于追踪页面浏览
 * 可以在服务端组件中使用
 */
export function PageViewTracker({ pageName, properties }: PageViewTrackerProps) {
  const pathname = usePathname();

  useEffect(() => {
    analytics.trackPageView(pageName, {
      pathname,
      ...properties,
    });
  }, [pageName, pathname, properties]);

  return null;
}

export default PageViewTracker;
