'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import {
  ArrowLeft,
  Check,
  Loader2,
  CheckCircle,
  AlertCircle,
  QrCode,
  X,
  MessageCircle,
  CreditCard,
  Building2,
  Clock,
  Copy,
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
      '每月 5 次体检',
      '最多 1 个项目',
      '基础指标分析',
      '7 天数据保留',
    ],
  },
  {
    code: 'pro',
    name: '专业版',
    price_monthly: 299,
    price_yearly: 2990,
    features: [
      '每月 50 次体检',
      '最多 10 个项目',
      '高级指标分析',
      '漂移监测预警',
      '报告导出与分享',
      '90 天数据保留',
    ],
  },
  {
    code: 'enterprise',
    name: '企业版',
    price_monthly: 999,
    price_yearly: 9990,
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

type PaymentMethod = 'wechat' | 'alipay' | 'bank_transfer';

const paymentMethods: { id: PaymentMethod; name: string; icon: React.ReactNode; desc: string }[] = [
  {
    id: 'wechat',
    name: '微信支付',
    icon: <MessageCircle className="w-5 h-5" />,
    desc: '微信扫码支付',
  },
  {
    id: 'alipay',
    name: '支付宝',
    icon: <CreditCard className="w-5 h-5" />,
    desc: '支付宝扫码支付',
  },
  {
    id: 'bank_transfer',
    name: '对公转账',
    icon: <Building2 className="w-5 h-5" />,
    desc: '银行转账',
  },
];

export default function SubscriptionPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('yearly');
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('wechat');

  // Payment modal state
  const [showPayModal, setShowPayModal] = useState(false);
  const [payModalPlan, setPayModalPlan] = useState<Plan | null>(null);
  const [orderData, setOrderData] = useState<any>(null);
  const [isCreatingOrder, setIsCreatingOrder] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [paymentConfirmed, setPaymentConfirmed] = useState(false);
  const [userNote, setUserNote] = useState('');
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

  const handleUpgrade = async (plan: Plan) => {
    if (plan.code === 'enterprise') {
      window.location.href = 'mailto:support@findablex.com?subject=企业版咨询';
      return;
    }
    if (plan.code === 'free') return;

    setPayModalPlan(plan);
    setShowPayModal(true);
    setError('');
    setPaymentConfirmed(false);
    setOrderData(null);
    setUserNote('');

    // Create order
    setIsCreatingOrder(true);
    try {
      const res = await api.post('/payment/orders', {
        plan_code: plan.code,
        billing_cycle: billingCycle,
        payment_method: paymentMethod,
      });
      setOrderData(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || '创建订单失败，请稍后重试');
    } finally {
      setIsCreatingOrder(false);
    }
  };

  const switchPaymentMethodInModal = async (method: PaymentMethod) => {
    setPaymentMethod(method);
    if (!payModalPlan) return;

    setIsCreatingOrder(true);
    setError('');
    try {
      const res = await api.post('/payment/orders', {
        plan_code: payModalPlan.code,
        billing_cycle: billingCycle,
        payment_method: method,
      });
      setOrderData(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || '切换支付方式失败');
    } finally {
      setIsCreatingOrder(false);
    }
  };

  const handleConfirmPayment = async () => {
    if (!orderData) return;

    setIsConfirming(true);
    setError('');
    try {
      await api.post(`/payment/orders/${orderData.order_id}/confirm`, {
        user_note: userNote,
      });
      setPaymentConfirmed(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || '确认失败，请重试');
    } finally {
      setIsConfirming(false);
    }
  };

  const copyOrderNo = () => {
    if (orderData?.order_id) {
      navigator.clipboard.writeText(orderData.order_id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
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
          年付 <span className="text-xs text-green-400 ml-1">省 17%</span>
        </button>
      </div>

      {/* Plans Grid */}
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        {plans.map((plan) => {
          const isCurrentPlan = plan.code === subscription?.plan_code ||
            (plan.code === 'free' && !subscription?.plan_code);
          const price = billingCycle === 'yearly' ? plan.price_yearly : plan.price_monthly;
          const isEnterprise = plan.code === 'enterprise';

          return (
            <div
              key={plan.code}
              className={cn(
                'bg-slate-800/50 rounded-xl border p-6 transition-all',
                isCurrentPlan ? 'border-primary-500 ring-1 ring-primary-500/20' : 'border-slate-700/50 hover:border-slate-600',
                plan.code === 'pro' && !isCurrentPlan && 'border-primary-500/30'
              )}
            >
              {plan.code === 'pro' && !isCurrentPlan && (
                <div className="text-xs text-primary-400 font-medium mb-2">推荐</div>
              )}
              <div className="mb-4">
                <h3 className="font-medium text-white">{plan.name}</h3>
                <div className="mt-2">
                  {price === 0 && plan.code === 'free' ? (
                    <span className="text-2xl font-bold text-white">免费</span>
                  ) : isEnterprise ? (
                    <>
                      <span className="text-3xl font-bold text-white">¥{price}</span>
                      <span className="text-slate-400 text-sm">
                        /{billingCycle === 'yearly' ? '年' : '月'}
                      </span>
                    </>
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
                    <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
                    {feature}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => !isCurrentPlan && handleUpgrade(plan)}
                disabled={isCurrentPlan}
                className={cn(
                  'w-full py-2.5 rounded-lg font-medium text-sm transition-all',
                  isCurrentPlan
                    ? 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
                    : plan.code === 'pro'
                      ? 'bg-primary-500 hover:bg-primary-600 text-white'
                      : 'bg-slate-700 hover:bg-slate-600 text-white'
                )}
              >
                {isCurrentPlan ? '当前套餐' : isEnterprise ? '联系咨询' : '升级'}
              </button>
            </div>
          );
        })}
      </div>

      {/* Payment Modal */}
      {showPayModal && payModalPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => !isConfirming && setShowPayModal(false)}
          />

          {/* Modal */}
          <div className="relative bg-slate-800 rounded-2xl border border-slate-700 w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-2xl">
            {/* Close button */}
            <button
              onClick={() => setShowPayModal(false)}
              className="absolute top-4 right-4 p-1 text-slate-400 hover:text-white transition-colors z-10"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="p-6">
              {/* Payment confirmed success */}
              {paymentConfirmed ? (
                <div className="text-center py-8">
                  <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-8 h-8 text-green-400" />
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2">付款确认已提交</h3>
                  <p className="text-slate-400 text-sm mb-6">
                    我们将在 1-2 个工作日内核实付款并为您开通服务。<br />
                    如有紧急需求，请联系 support@findablex.com
                  </p>
                  <button
                    onClick={() => setShowPayModal(false)}
                    className="px-6 py-2.5 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-all"
                  >
                    知道了
                  </button>
                </div>
              ) : (
                <>
                  {/* Header */}
                  <div className="mb-6">
                    <h2 className="text-lg font-bold text-white">
                      升级到{payModalPlan.name}
                    </h2>
                    <p className="text-sm text-slate-400 mt-1">
                      扫码支付后点击"我已完成付款"
                    </p>
                  </div>

                  {/* Order summary */}
                  <div className="bg-slate-700/30 rounded-lg p-4 mb-6">
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-slate-400">套餐</span>
                      <span className="text-white font-medium">{payModalPlan.name}</span>
                    </div>
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-slate-400">周期</span>
                      <span className="text-white">{billingCycle === 'yearly' ? '年付' : '月付'}</span>
                    </div>
                    <div className="flex justify-between text-sm pt-2 border-t border-slate-600">
                      <span className="text-slate-300 font-medium">应付金额</span>
                      <span className="text-xl font-bold text-primary-400">
                        ¥{billingCycle === 'yearly' ? payModalPlan.price_yearly : payModalPlan.price_monthly}
                      </span>
                    </div>
                  </div>

                  {/* Payment method tabs */}
                  <div className="flex gap-2 mb-6">
                    {paymentMethods.map((method) => (
                      <button
                        key={method.id}
                        onClick={() => switchPaymentMethodInModal(method.id)}
                        className={cn(
                          'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all',
                          paymentMethod === method.id
                            ? 'bg-primary-500/10 border border-primary-500/50 text-primary-400'
                            : 'border border-slate-600 text-slate-400 hover:text-white hover:border-slate-500'
                        )}
                      >
                        {method.icon}
                        <span className="hidden sm:inline">{method.name}</span>
                      </button>
                    ))}
                  </div>

                  {/* QR Code / Payment info */}
                  {isCreatingOrder ? (
                    <div className="flex items-center justify-center py-16">
                      <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
                    </div>
                  ) : error && !orderData ? (
                    <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm mb-4">
                      <div className="flex items-center gap-2">
                        <AlertCircle className="w-4 h-4" />
                        {error}
                      </div>
                    </div>
                  ) : orderData ? (
                    <div className="space-y-4">
                      {/* QR Code display */}
                      {(paymentMethod === 'wechat' || paymentMethod === 'alipay') && (
                        <div className="text-center">
                          <div className="inline-block bg-white rounded-xl p-4 mb-3">
                            {orderData.payment_data?.qr_image ? (
                              <Image
                                src={orderData.payment_data.qr_image}
                                alt={paymentMethod === 'wechat' ? '微信支付' : '支付宝'}
                                width={200}
                                height={200}
                                className="rounded-lg"
                              />
                            ) : (
                              <div className="w-[200px] h-[200px] flex items-center justify-center bg-slate-100 rounded-lg">
                                <QrCode className="w-12 h-12 text-slate-400" />
                              </div>
                            )}
                          </div>
                          <p className="text-sm text-slate-400">
                            {paymentMethod === 'wechat' ? '请使用微信扫一扫' : '请使用支付宝扫一扫'}
                          </p>
                        </div>
                      )}

                      {/* Bank transfer info */}
                      {paymentMethod === 'bank_transfer' && (
                        <div className="p-4 bg-slate-700/30 rounded-lg">
                          <h4 className="text-sm font-medium text-slate-300 mb-3">转账信息</h4>
                          <p className="text-sm text-slate-400">
                            请联系 support@findablex.com 获取转账账户信息
                          </p>
                        </div>
                      )}

                      {/* Order number */}
                      <div className="p-3 bg-slate-700/20 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="text-xs text-slate-500">订单号</span>
                            <p className="text-sm font-mono text-slate-300">{orderData.order_id}</p>
                          </div>
                          <button
                            onClick={copyOrderNo}
                            className="p-2 text-slate-400 hover:text-white transition-colors"
                            title="复制订单号"
                          >
                            {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                          </button>
                        </div>
                      </div>

                      {/* Payment note reminder */}
                      <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                        <div className="flex items-start gap-2">
                          <AlertCircle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                          <p className="text-xs text-amber-300">
                            付款时请在备注中填写订单号 <strong>{orderData.order_id}</strong>，以便快速核实
                          </p>
                        </div>
                      </div>

                      {/* User note input */}
                      <div>
                        <label className="block text-xs text-slate-400 mb-1">
                          付款备注（可选）
                        </label>
                        <input
                          type="text"
                          value={userNote}
                          onChange={(e) => setUserNote(e.target.value)}
                          placeholder="如：已通过微信转账"
                          className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-primary-500"
                        />
                      </div>

                      {error && (
                        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-xs">
                          {error}
                        </div>
                      )}

                      {/* Confirm button */}
                      <button
                        onClick={handleConfirmPayment}
                        disabled={isConfirming}
                        className="w-full py-3 bg-green-500 hover:bg-green-600 disabled:bg-green-500/50 text-white rounded-lg font-medium transition-all flex items-center justify-center gap-2"
                      >
                        {isConfirming ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <CheckCircle className="w-4 h-4" />
                        )}
                        我已完成付款
                      </button>

                      <p className="text-xs text-slate-500 text-center">
                        <Clock className="w-3 h-3 inline mr-1" />
                        确认后，我们将在 1-2 个工作日内核实并开通服务
                      </p>
                    </div>
                  ) : null}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
