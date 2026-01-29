'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, Mail, ArrowLeft, CheckCircle } from 'lucide-react';
import { api } from '@/lib/api';

const forgotPasswordSchema = z.object({
  email: z.string().email('请输入有效的邮箱地址'),
});

type ForgotPasswordForm = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPasswordPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordForm>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordForm) => {
    setIsLoading(true);
    setError('');

    try {
      await api.post('/auth/forgot-password', {
        email: data.email,
      });

      setSubmittedEmail(data.email);
      setIsSuccess(true);
    } catch (err: any) {
      // Don't reveal if email exists or not for security
      setSubmittedEmail(data.email);
      setIsSuccess(true);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xl">F</span>
            </div>
            <span className="font-display text-2xl font-bold text-white">
              FindableX
            </span>
          </Link>
        </div>

        <div className="bg-slate-800/50 rounded-2xl p-8 border border-slate-700/50 backdrop-blur-sm">
          {/* Back Link */}
          <Link
            href="/login"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-6 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            返回登录
          </Link>

          {isSuccess ? (
            // Success State
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-8 h-8 text-green-400" />
              </div>
              <h2 className="font-display text-xl font-bold text-white mb-3">
                邮件已发送
              </h2>
              <p className="text-slate-400 text-sm mb-6">
                如果 <span className="text-white">{submittedEmail}</span>{' '}
                是已注册的邮箱地址，您将收到一封包含密码重置链接的邮件。
              </p>
              <p className="text-slate-500 text-xs mb-6">
                请检查您的收件箱和垃圾邮件文件夹。链接有效期为 24 小时。
              </p>
              <div className="space-y-3">
                <Link
                  href="/login"
                  className="block w-full bg-primary-500 hover:bg-primary-600 text-white py-3 rounded-lg font-medium transition-all text-center"
                >
                  返回登录
                </Link>
                <button
                  onClick={() => {
                    setIsSuccess(false);
                    setSubmittedEmail('');
                  }}
                  className="block w-full text-slate-400 hover:text-white py-2 text-sm transition-colors"
                >
                  使用其他邮箱
                </button>
              </div>
            </div>
          ) : (
            // Form State
            <>
              <div className="mb-6">
                <h2 className="font-display text-xl font-bold text-white mb-2">
                  忘记密码
                </h2>
                <p className="text-slate-400 text-sm">
                  输入您的注册邮箱，我们将向您发送密码重置链接。
                </p>
              </div>

              {/* Error Message */}
              {error && (
                <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                {/* Email */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    邮箱地址
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                    <input
                      type="email"
                      {...register('email')}
                      className="w-full pl-12 pr-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                      placeholder="you@example.com"
                    />
                  </div>
                  {errors.email && (
                    <p className="mt-1.5 text-sm text-red-400">
                      {errors.email.message}
                    </p>
                  )}
                </div>

                {/* Submit */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/50 text-white py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      发送中...
                    </>
                  ) : (
                    '发送重置链接'
                  )}
                </button>
              </form>

              <div className="mt-6 text-center">
                <p className="text-slate-500 text-sm">
                  想起密码了？{' '}
                  <Link
                    href="/login"
                    className="text-primary-400 hover:text-primary-300 transition-colors"
                  >
                    立即登录
                  </Link>
                </p>
              </div>
            </>
          )}

          {/* ICP */}
          <div className="mt-8 text-center">
            <a
              href="https://beian.miit.gov.cn/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-500 hover:text-slate-400 text-xs transition-colors"
            >
              苏ICP备2026005817号
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
