'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Zap,
  X,
  ArrowRight,
  TrendingUp,
  Shield,
  BarChart3,
} from 'lucide-react';

/**
 * Global state for showing the upgrade modal.
 * This allows the API interceptor (non-React code) to trigger the modal.
 */
type UpgradeListener = (info: UpgradeInfo) => void;

interface UpgradeInfo {
  code: string;
  message: string;
  current?: number;
  limit?: number;
  feature?: string;
}

const listeners = new Set<UpgradeListener>();

export function triggerUpgradeModal(info: UpgradeInfo) {
  listeners.forEach((fn) => fn(info));
}

const upgradeReasons: Record<string, { title: string; icon: React.ReactNode; description: string }> = {
  RUN_LIMIT_EXCEEDED: {
    title: '本月体检次数已用尽',
    icon: <TrendingUp className="w-6 h-6" />,
    description: '升级后获取更多体检次数，持续追踪品牌 AI 可见性变化',
  },
  QUERY_LIMIT_EXCEEDED: {
    title: '查询词数量已达上限',
    icon: <BarChart3 className="w-6 h-6" />,
    description: '升级后可添加更多查询词，全面监测品牌表现',
  },
  FEATURE_NOT_AVAILABLE: {
    title: '此功能需要升级',
    icon: <Shield className="w-6 h-6" />,
    description: '升级到专业版解锁高级功能，获取更深入的分析',
  },
  PROJECT_LIMIT_EXCEEDED: {
    title: '项目数量已达上限',
    icon: <Zap className="w-6 h-6" />,
    description: '升级后可创建更多项目，管理多个品牌监测',
  },
};

const defaultReason = {
  title: '升级解锁更多功能',
  icon: <Zap className="w-6 h-6" />,
  description: '升级到专业版，获取更强大的 GEO 分析能力',
};

const proFeatures = [
  '每月 50 次体检',
  '最多 10 个项目',
  '高级指标分析',
  '漂移监测预警',
  '报告导出与分享',
];

export default function UpgradeModal() {
  const [show, setShow] = useState(false);
  const [info, setInfo] = useState<UpgradeInfo | null>(null);

  useEffect(() => {
    const handler: UpgradeListener = (upgradeInfo) => {
      setInfo(upgradeInfo);
      setShow(true);
    };

    listeners.add(handler);
    return () => {
      listeners.delete(handler);
    };
  }, []);

  if (!show || !info) return null;

  const reason = upgradeReasons[info.code] || defaultReason;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => setShow(false)}
      />

      {/* Modal */}
      <div className="relative bg-slate-800 rounded-2xl border border-slate-700 w-full max-w-md shadow-2xl overflow-hidden">
        {/* Gradient top bar */}
        <div className="h-1.5 bg-gradient-to-r from-primary-500 via-purple-500 to-pink-500" />

        {/* Close */}
        <button
          onClick={() => setShow(false)}
          className="absolute top-4 right-4 p-1 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="p-6">
          {/* Icon + Title */}
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-primary-500/10 rounded-xl flex items-center justify-center text-primary-400">
              {reason.icon}
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">{reason.title}</h3>
              <p className="text-sm text-slate-400">{reason.description}</p>
            </div>
          </div>

          {/* Current usage info */}
          {info.current !== undefined && info.limit !== undefined && (
            <div className="mb-5 p-3 bg-slate-700/30 rounded-lg">
              <div className="flex items-center justify-between text-sm mb-2">
                <span className="text-slate-400">使用情况</span>
                <span className="text-slate-300">
                  {info.current} / {info.limit}
                </span>
              </div>
              <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-red-500 to-orange-500 rounded-full"
                  style={{ width: '100%' }}
                />
              </div>
            </div>
          )}

          {/* Pro features */}
          <div className="mb-6">
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">
              专业版包含
            </p>
            <div className="grid grid-cols-1 gap-2">
              {proFeatures.map((feature, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-slate-300">
                  <div className="w-1.5 h-1.5 bg-primary-400 rounded-full" />
                  {feature}
                </div>
              ))}
            </div>
          </div>

          {/* CTA buttons */}
          <div className="space-y-3">
            <Link
              href="/subscription"
              onClick={() => setShow(false)}
              className="w-full flex items-center justify-center gap-2 py-3 bg-primary-500 hover:bg-primary-600 text-white rounded-xl font-medium transition-all"
            >
              <Zap className="w-4 h-4" />
              查看升级方案
              <ArrowRight className="w-4 h-4" />
            </Link>
            <button
              onClick={() => setShow(false)}
              className="w-full py-2.5 text-slate-400 hover:text-white text-sm transition-colors"
            >
              稍后再说
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
