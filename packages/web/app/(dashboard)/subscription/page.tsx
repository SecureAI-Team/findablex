'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Check,
  CreditCard,
  Building2,
  Loader2,
  CheckCircle,
  Copy,
  AlertCircle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Subscription {
  id: string;
  plan_code: string;
  status: string;
  billing_cycle: string;
  current_period_end?: string;
}

interface Usage {
  runs_this_month: number;
  runs_limit: number;
  projects_count: number;
  projects_limit: number;
}

interface Plan {
  code: string;
  name: string;
  price_monthly: number;
  price_yearly: number;
  features: string[];
}

const plans: Plan[] = [
  {
    code: 'free',
    name: '免费版',
    price_monthly: 0,
    price_yearly: 0,
    features: [
      '每月 10 次体检',
      '最多 3 个项目',
      '基础指标分析',
      '7 天数据保留',
    ],
  },
  {
    code: 'pro',
    name: '专业版',
    price_monthly: 299,
    price_yearly: 2870,
    features: [
      '每月 100 次体检',
      '无限项目',
      '高级指标分析',
      '漂移监测预警',
      '报告导出与分享',
      '90 天数据保留',
    ],
  },
  {
    code: 'enterprise',
    name: '企业版',
    price_monthly: 0,
    price_yearly: 0,
    features: [
      '无限次体检',
      '无限项目',
      '科研实验功能',
      'API 访问',
      '无限数据保留',
      '专属客户经理',
    ],
  },
];

export default function SubscriptionPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('yearly');
  const [isUpgrading, setIsUpgrading] = useState(false);
  const [upgradeResult, setUpgradeResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [subRes, usageRes] = await Promise.all([
          api.get('/subscriptions/current'),
          api.get('/subscriptions/usage'),
        ]);
        setSubscription(subRes.data);
        setUsage(usageRes.data);
      } catch (err) {
        console.error('Failed to fetch subscription data:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleUpgrade = async (planCode: string) => {
    if (planCode === 'enterprise') {
      // Redirect to contact page for enterprise
      window.location.href = '/contact';
      return;
    }

    setIsUpgrading(true);
    setError('');

    try {
      const res = await api.post('/subscriptions/upgrade', {
        target_plan: planCode,
        billing_cycle: billingCycle,
        payment_method: 'manual',
      });
      setUpgradeResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || '升级请求失败');
    } finally {
      setIsUpgrading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
      </div>
    );
  }

  // Show payment instructions after upgrade request
  if (upgradeResult) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <Link
            href="/settings"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            返回设置
          </Link>
          <h1 className="font-display text-2xl font-bold text-white">升级订阅</h1>
        </div>

        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 bg-green-500/10 rounded-xl flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <h2 className="font-medium text-white">升级请求已提交</h2>
              <p className="text-sm text-slate-400">请按以下方式完成付款</p>
            </div>
          </div>

          <div className="space-y-6">
            <div className="p-4 bg-slate-700/30 rounded-lg">
              <h3 className="text-sm font-medium text-slate-300 mb-3">付款信息</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">套餐</span>
                  <span className="text-white">{upgradeResult.plan_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">金额</span>
                  <span className="text-white font-medium">¥{upgradeResult.amount}</span>
                </div>
              </div>
            </div>

            {upgradeResult.payment_instructions?.bank_transfer && (
              <div className="p-4 bg-slate-700/30 rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <Building2 className="w-4 h-4 text-primary-400" />
                  <h3 className="text-sm font-medium text-slate-300">对公转账</h3>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">户名</span>
                    <span className="text-white">{upgradeResult.payment_instructions.bank_transfer.account_name}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">账号</span>
                    <div className="flex items-center gap-2">
                      <span className="text-white font-mono">{upgradeResult.payment_instructions.bank_transfer.account_number}</span>
                      <button
                        onClick={() => copyToClipboard(upgradeResult.payment_instructions.bank_transfer.account_number)}
                        className="p-1 text-slate-400 hover:text-white transition-colors"
                      >
                        {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">开户行</span>
                    <span className="text-white">{upgradeResult.payment_instructions.bank_transfer.bank_name}</span>
                  </div>
                </div>
              </div>
            )}

            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-amber-400 mt-0.5" />
                <div className="text-sm">
                  <p className="text-amber-300 font-medium">付款备注</p>
                  <p className="text-amber-200/80 mt-1">
                    请在付款时备注您的邮箱或用户名，以便我们快速为您开通服务。
                  </p>
                </div>
              </div>
            </div>

            <p className="text-sm text-slate-500">
              付款完成后，我们将在 1-2 个工作日内为您开通服务。如有问题请联系 support@findablex.com
            </p>

            <div className="flex gap-4">
              <button
                onClick={() => setUpgradeResult(null)}
                className="flex-1 px-4 py-2.5 text-slate-400 hover:text-white border border-slate-600 hover:border-slate-500 rounded-lg transition-all"
              >
                返回
              </button>
              <Link
                href="/contact"
                className="flex-1 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2.5 rounded-lg text-center transition-all"
              >
                联系客服
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const currentPlan = plans.find(p => p.code === subscription?.plan_code) || plans[0];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/settings"
          className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          返回设置
        </Link>
        <h1 className="font-display text-2xl font-bold text-white">订阅管理</h1>
        <p className="mt-1 text-slate-400">管理您的订阅计划和付款方式</p>
      </div>

      {/* Current Plan */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 mb-8">
        <h2 className="font-medium text-white mb-4">当前套餐</h2>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold text-white">{currentPlan.name}</span>
              <span className={cn(
                'text-xs px-2 py-0.5 rounded',
                subscription?.status === 'active' ? 'bg-green-500/10 text-green-400' : 'bg-slate-600/50 text-slate-400'
              )}>
                {subscription?.status === 'active' ? '活跃' : subscription?.status || '免费'}
              </span>
            </div>
            {subscription?.current_period_end && (
              <p className="text-sm text-slate-400 mt-1">
                有效期至 {new Date(subscription.current_period_end).toLocaleDateString('zh-CN')}
              </p>
            )}
          </div>
          {usage && (
            <div className="text-right">
              <p className="text-sm text-slate-400">
                本月已使用 <span className="text-white">{usage.runs_this_month}</span> / {usage.runs_limit === -1 ? '无限' : usage.runs_limit} 次
              </p>
              <p className="text-sm text-slate-400">
                项目数 <span className="text-white">{usage.projects_count}</span> / {usage.projects_limit === -1 ? '无限' : usage.projects_limit}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Billing Cycle Toggle */}
      <div className="flex items-center justify-center gap-4 mb-8">
        <button
          onClick={() => setBillingCycle('monthly')}
          className={cn(
            'px-4 py-2 rounded-lg text-sm font-medium transition-all',
            billingCycle === 'monthly'
              ? 'bg-primary-500 text-white'
              : 'text-slate-400 hover:text-white'
          )}
        >
          月付
        </button>
        <button
          onClick={() => setBillingCycle('yearly')}
          className={cn(
            'px-4 py-2 rounded-lg text-sm font-medium transition-all',
            billingCycle === 'yearly'
              ? 'bg-primary-500 text-white'
              : 'text-slate-400 hover:text-white'
          )}
        >
          年付 <span className="text-xs text-green-400 ml-1">省20%</span>
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm mb-6">
          {error}
        </div>
      )}

      {/* Plans */}
      <div className="grid md:grid-cols-3 gap-6">
        {plans.map((plan) => {
          const isCurrentPlan = plan.code === subscription?.plan_code;
          const price = billingCycle === 'yearly' ? plan.price_yearly : plan.price_monthly;
          const isEnterprise = plan.code === 'enterprise';

          return (
            <div
              key={plan.code}
              className={cn(
                'bg-slate-800/50 rounded-xl border p-6 transition-all',
                isCurrentPlan ? 'border-primary-500' : 'border-slate-700/50 hover:border-slate-600'
              )}
            >
              <div className="mb-4">
                <h3 className="font-medium text-white">{plan.name}</h3>
                <div className="mt-2">
                  {isEnterprise ? (
                    <span className="text-2xl font-bold text-white">定制</span>
                  ) : (
                    <>
                      <span className="text-3xl font-bold text-white">¥{price}</span>
                      <span className="text-slate-400 text-sm">
                        /{billingCycle === 'yearly' ? '年' : '月'}
                      </span>
                    </>
                  )}
                </div>
              </div>

              <ul className="space-y-2 mb-6">
                {plan.features.map((feature, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-slate-300">
                    <Check className="w-4 h-4 text-green-400" />
                    {feature}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => !isCurrentPlan && handleUpgrade(plan.code)}
                disabled={isCurrentPlan || isUpgrading}
                className={cn(
                  'w-full py-2.5 rounded-lg font-medium text-sm transition-all',
                  isCurrentPlan
                    ? 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
                    : 'bg-primary-500 hover:bg-primary-600 text-white'
                )}
              >
                {isCurrentPlan ? '当前套餐' : isEnterprise ? '联系销售' : '升级'}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
