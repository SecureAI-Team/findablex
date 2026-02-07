'use client';

import { useLocale, type Locale } from '@/lib/i18n';
import { Globe } from 'lucide-react';

const LABELS: Record<Locale, string> = {
  zh: '中文',
  en: 'EN',
};

export default function LanguageSwitcher() {
  const [locale, setLocale] = useLocale();

  const toggle = () => {
    setLocale(locale === 'zh' ? 'en' : 'zh');
  };

  return (
    <button
      onClick={toggle}
      className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-slate-400 hover:text-white border border-slate-700 hover:border-slate-600 rounded-lg transition-colors"
      title="Switch language"
    >
      <Globe className="w-3.5 h-3.5" />
      {LABELS[locale]}
    </button>
  );
}
