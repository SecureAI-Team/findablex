'use client';

import { useEffect, useState } from 'react';
import {
  Gift,
  Copy,
  Check,
  Users,
  Zap,
  Share2,
  Loader2,
} from 'lucide-react';
import { api } from '@/lib/api';

interface ReferralInfo {
  referral_code: string;
  referral_url: string;
  total_referrals: number;
  total_bonus_earned: number;
}

export default function ReferralCard() {
  const [info, setInfo] = useState<ReferralInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [copied, setCopied] = useState<'code' | 'url' | null>(null);

  useEffect(() => {
    api
      .get('/referral/me')
      .then((res) => setInfo(res.data))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  const copyToClipboard = (text: string, type: 'code' | 'url') => {
    navigator.clipboard.writeText(text);
    setCopied(type);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleShare = async () => {
    if (!info) return;

    if (navigator.share) {
      try {
        await navigator.share({
          title: 'FindableX - AI 搜索可见性体检',
          text: '免费体检你的品牌在 AI 搜索引擎中的可见性，注册即送额外 3 次体检次数！',
          url: info.referral_url,
        });
      } catch {
        // User cancelled
      }
    } else {
      copyToClipboard(info.referral_url, 'url');
    }
  };

  if (isLoading) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 animate-pulse">
        <div className="h-6 bg-slate-700 rounded w-32 mb-4" />
        <div className="h-4 bg-slate-700 rounded w-48" />
      </div>
    );
  }

  if (!info) return null;

  return (
    <div className="bg-gradient-to-br from-amber-500/5 to-orange-500/5 border border-amber-500/20 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-amber-500/10 rounded-xl flex items-center justify-center">
          <Gift className="w-5 h-5 text-amber-400" />
        </div>
        <div>
          <h3 className="font-medium text-white">邀请有礼</h3>
          <p className="text-sm text-slate-400">
            每邀请一位好友注册，双方各得额外体检次数
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 mb-5">
        <div className="bg-slate-800/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Users className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-xs text-slate-500">已邀请</span>
          </div>
          <p className="text-lg font-bold text-white">{info.total_referrals}</p>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Zap className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-xs text-slate-500">获得次数</span>
          </div>
          <p className="text-lg font-bold text-amber-400">+{info.total_bonus_earned}</p>
        </div>
      </div>

      {/* Referral code */}
      <div className="mb-4">
        <label className="block text-xs text-slate-500 mb-1.5">您的邀请码</label>
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2.5">
            <span className="font-mono text-sm text-white tracking-wider">
              {info.referral_code}
            </span>
          </div>
          <button
            onClick={() => copyToClipboard(info.referral_code, 'code')}
            className="p-2.5 bg-slate-800/50 border border-slate-700 rounded-lg text-slate-400 hover:text-white transition-colors"
            title="复制邀请码"
          >
            {copied === 'code' ? (
              <Check className="w-4 h-4 text-green-400" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Share buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => copyToClipboard(info.referral_url, 'url')}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm font-medium transition-all"
        >
          {copied === 'url' ? (
            <>
              <Check className="w-4 h-4 text-green-400" />
              已复制
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              复制链接
            </>
          )}
        </button>
        <button
          onClick={handleShare}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-sm font-medium transition-all"
        >
          <Share2 className="w-4 h-4" />
          分享给好友
        </button>
      </div>

      {/* Reward info */}
      <div className="mt-4 text-xs text-slate-500 space-y-1">
        <p>• 好友通过您的链接注册后，您获得 <strong className="text-amber-400">5 次</strong> 额外体检</p>
        <p>• 好友同时获得 <strong className="text-amber-400">3 次</strong> 额外体检</p>
      </div>
    </div>
  );
}
