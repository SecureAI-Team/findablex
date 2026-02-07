/**
 * Lightweight i18n system for FindableX.
 *
 * Supports Chinese (default) and English.
 * No heavy libraries needed — just a simple key-value map + React hook.
 *
 * Usage:
 *   import { useT, setLocale, getLocale } from '@/lib/i18n';
 *   const t = useT();
 *   <h1>{t('hero.title')}</h1>
 */

import { useCallback, useEffect, useState } from 'react';
import { zh } from './zh';
import { en } from './en';

export type Locale = 'zh' | 'en';

type Messages = Record<string, string>;

const messages: Record<Locale, Messages> = { zh, en };

// ── State ────────────────────────────────────────────────────────────

const STORAGE_KEY = 'findablex_locale';

let currentLocale: Locale = 'zh';

// Detect initial locale from storage or browser
function detectLocale(): Locale {
  if (typeof window === 'undefined') return 'zh';

  // 1. Stored preference
  const stored = localStorage.getItem(STORAGE_KEY) as Locale | null;
  if (stored && messages[stored]) return stored;

  // 2. Browser language
  const browserLang = navigator.language?.toLowerCase();
  if (browserLang?.startsWith('en')) return 'en';

  return 'zh';
}

// ── Public API ───────────────────────────────────────────────────────

const listeners = new Set<() => void>();

export function getLocale(): Locale {
  return currentLocale;
}

export function setLocale(locale: Locale) {
  if (!messages[locale]) return;
  currentLocale = locale;
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, locale);
    document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en';
  }
  listeners.forEach((fn) => fn());
}

export function t(key: string, params?: Record<string, string | number>): string {
  let text = messages[currentLocale]?.[key] || messages['zh']?.[key] || key;

  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      text = text.replace(`{${k}}`, String(v));
    });
  }

  return text;
}

/**
 * React hook for translations. Re-renders when locale changes.
 */
export function useT() {
  const [, forceUpdate] = useState(0);

  useEffect(() => {
    // Initialize locale on first mount
    currentLocale = detectLocale();

    const handler = () => forceUpdate((n) => n + 1);
    listeners.add(handler);
    return () => {
      listeners.delete(handler);
    };
  }, []);

  return useCallback(
    (key: string, params?: Record<string, string | number>) => t(key, params),
    []
  );
}

/**
 * React hook for current locale.
 */
export function useLocale(): [Locale, (l: Locale) => void] {
  const [, forceUpdate] = useState(0);

  useEffect(() => {
    const handler = () => forceUpdate((n) => n + 1);
    listeners.add(handler);
    return () => {
      listeners.delete(handler);
    };
  }, []);

  return [currentLocale, setLocale];
}
