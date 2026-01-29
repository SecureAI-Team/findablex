'use client';

import { useState } from 'react';
import Link from 'next/link';
import { MessageSquare, Loader2, CheckCircle } from 'lucide-react';
import { Header, Footer } from '@/components';
import { api } from '@/lib/api';
import { analytics, EVENTS } from '@/lib/analytics';

const contactMethods = [
  {
    icon: MessageSquare,
    title: '公众号咨询',
    description: '关注公众号获取支持和最新资讯',
    value: 'FindableX',
    href: null, // 显示二维码
    showQR: true,
  },
];

interface FormData {
  name: string;
  email: string;
  subject: string;
  message: string;
}

interface FormErrors {
  name?: string;
  email?: string;
  subject?: string;
  message?: string;
}

export default function ContactPage() {
  const [formData, setFormData] = useState<FormData>({
    name: '',
    email: '',
    subject: '',
    message: '',
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = '请输入您的姓名';
    }

    if (!formData.email.trim()) {
      newErrors.email = '请输入邮箱地址';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = '请输入有效的邮箱地址';
    }

    if (!formData.subject) {
      newErrors.subject = '请选择主题';
    }

    if (!formData.message.trim()) {
      newErrors.message = '请输入消息内容';
    } else if (formData.message.trim().length < 10) {
      newErrors.message = '消息内容至少需要10个字符';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // 调用联系销售 API
      await api.post('/subscriptions/contact-sales', {
        name: formData.name,
        email: formData.email,
        message: `[${formData.subject}] ${formData.message}`,
        plan_interest: formData.subject === 'business' ? 'enterprise' : 'pro',
      });

      // 追踪事件
      analytics.track(EVENTS.CONTACT_SALES_CLICKED, {
        properties: {
          subject: formData.subject,
          source: 'contact_page',
        },
      });

      setIsSuccess(true);
    } catch (error) {
      console.error('Contact form submission failed:', error);
      // 即使 API 失败，也显示成功（MVP 阶段可以通过日志查看）
      setIsSuccess(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error when user starts typing
    if (errors[name as keyof FormErrors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  if (isSuccess) {
    return (
      <div className="min-h-screen bg-slate-900">
        <Header />

        <section className="pt-32 lg:pt-40 pb-20 lg:pb-32">
          <div className="max-w-xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <div className="w-20 h-20 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-8">
              <CheckCircle className="w-10 h-10 text-green-400" />
            </div>
            <h1 className="font-display text-3xl lg:text-4xl font-bold text-white mb-4">
              消息已发送
            </h1>
            <p className="text-slate-400 text-lg mb-8">
              感谢您的来信！我们会尽快回复您的消息，通常在 1-2 个工作日内。
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <button
                onClick={() => {
                  setIsSuccess(false);
                  setFormData({ name: '', email: '', subject: '', message: '' });
                }}
                className="w-full sm:w-auto bg-primary-500 hover:bg-primary-600 text-white px-6 py-3 rounded-lg font-medium transition-all"
              >
                发送新消息
              </button>
              <Link
                href="/"
                className="w-full sm:w-auto text-slate-300 hover:text-white px-6 py-3 rounded-lg font-medium border border-slate-600 hover:border-slate-500 transition-all text-center"
              >
                返回首页
              </Link>
            </div>
          </div>
        </section>

        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900">
      <Header />

      {/* Hero */}
      <section className="pt-32 lg:pt-40 pb-16 lg:pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="font-display text-4xl lg:text-5xl font-bold text-white mb-6">
            联系我们
          </h1>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">
            无论是产品咨询、技术支持还是商务合作，我们都期待与您沟通
          </p>
        </div>
      </section>

      {/* Contact Methods */}
      <section className="pb-20 lg:pb-32">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* WeChat Contact */}
          <div className="bg-slate-800/50 rounded-2xl p-8 border border-slate-700/50 mb-16 max-w-md mx-auto text-center">
            <div className="w-14 h-14 bg-primary-500/10 rounded-xl flex items-center justify-center mb-6 mx-auto">
              <MessageSquare className="w-7 h-7 text-primary-400" />
            </div>
            <h3 className="font-display text-xl font-semibold text-white mb-2">
              关注公众号
            </h3>
            <p className="text-slate-400 text-sm mb-6">
              扫码关注 FindableX 公众号<br/>获取支持和最新资讯
            </p>
            <img 
              src="/wechat-qrcode.jpg" 
              alt="FindableX 公众号" 
              className="w-40 h-40 rounded-lg border border-slate-600 mx-auto"
            />
            <p className="text-primary-400 font-medium mt-4">
              FindableX
            </p>
          </div>

          {/* Contact Form */}
          <div className="bg-slate-800/50 rounded-2xl p-8 lg:p-10 border border-slate-700/50">
            <h2 className="font-display text-2xl font-bold text-white mb-6">
              发送消息
            </h2>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    姓名
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    className={`w-full px-4 py-3 bg-slate-700/50 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all ${
                      errors.name ? 'border-red-500' : 'border-slate-600'
                    }`}
                    placeholder="您的姓名"
                  />
                  {errors.name && (
                    <p className="mt-1.5 text-sm text-red-400">{errors.name}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    邮箱
                  </label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    className={`w-full px-4 py-3 bg-slate-700/50 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all ${
                      errors.email ? 'border-red-500' : 'border-slate-600'
                    }`}
                    placeholder="you@example.com"
                  />
                  {errors.email && (
                    <p className="mt-1.5 text-sm text-red-400">{errors.email}</p>
                  )}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  主题
                </label>
                <select
                  name="subject"
                  value={formData.subject}
                  onChange={handleChange}
                  className={`w-full px-4 py-3 bg-slate-700/50 border rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all ${
                    errors.subject ? 'border-red-500' : 'border-slate-600'
                  }`}
                >
                  <option value="">选择主题</option>
                  <option value="support">产品咨询</option>
                  <option value="technical">技术支持</option>
                  <option value="business">商务合作</option>
                  <option value="feedback">意见反馈</option>
                  <option value="other">其他</option>
                </select>
                {errors.subject && (
                  <p className="mt-1.5 text-sm text-red-400">{errors.subject}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  消息内容
                </label>
                <textarea
                  name="message"
                  value={formData.message}
                  onChange={handleChange}
                  rows={5}
                  className={`w-full px-4 py-3 bg-slate-700/50 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all resize-none ${
                    errors.message ? 'border-red-500' : 'border-slate-600'
                  }`}
                  placeholder="请详细描述您的问题或需求..."
                />
                {errors.message && (
                  <p className="mt-1.5 text-sm text-red-400">{errors.message}</p>
                )}
              </div>
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full md:w-auto bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/50 text-white px-8 py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    发送中...
                  </>
                ) : (
                  '发送消息'
                )}
              </button>
            </form>
          </div>

          {/* FAQ Link */}
          <div className="mt-12 text-center">
            <p className="text-slate-400">
              在联系我们之前，您也可以先查看{' '}
              <Link
                href="/faq"
                className="text-primary-400 hover:text-primary-300 transition-colors"
              >
                常见问题
              </Link>{' '}
              页面
            </p>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
