'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useState, Suspense, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Loader2,
  Lock,
  Eye,
  EyeOff,
  ArrowLeft,
  CheckCircle,
  AlertCircle,
  Check,
  X,
} from 'lucide-react';
import { api } from '@/lib/api';

const resetPasswordSchema = z
  .object({
    password: z.string().min(8, '密码至少8个字符'),
    confirmPassword: z.string().min(1, '请确认密码'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: '两次输入的密码不一致',
    path: ['confirmPassword'],
  });

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>;

function PasswordStrength({ password }: { password: string }) {
  const checks = useMemo(() => {
    return {
      length: password.length >= 8,
      lowercase: /[a-z]/.test(password),
      uppercase: /[A-Z]/.test(password),
      number: /[0-9]/.test(password),
    };
  }, [password]);

  const strength = useMemo(() => {
    const passed = Object.values(checks).filter(Boolean).length;
    if (passed === 0) return { label: '', color: '', width: '0%' };
    if (passed <= 2) return { label: '弱', color: 'bg-red-500', width: '33%' };
    if (passed <= 3)
      return { label: '中', color: 'bg-yellow-500', width: '66%' };
    return { label: '强', color: 'bg-green-500', width: '100%' };
  }, [checks]);

  if (!password) return null;

  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full ${strength.color} transition-all duration-300`}
            style={{ width: strength.width }}
          />
        </div>
        <span
          className={`text-xs ${strength.color.replace('bg-', 'text-')}`}
        >
          {strength.label}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-1.5 text-xs">
        {[
          { key: 'length', label: '至少8个字符' },
          { key: 'lowercase', label: '包含小写字母' },
          { key: 'uppercase', label: '包含大写字母' },
          { key: 'number', label: '包含数字' },
        ].map(({ key, label }) => (
          <div
            key={key}
            className={`flex items-center gap-1.5 ${
              checks[key as keyof typeof checks]
                ? 'text-green-400'
                : 'text-slate-500'
            }`}
          >
            {checks[key as keyof typeof checks] ? (
              <Check className="w-3 h-3" />
            ) : (
              <X className="w-3 h-3" />
            )}
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);

  const token = searchParams.get('token');

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ResetPasswordForm>({
    resolver: zodResolver(resetPasswordSchema),
  });

  const password = watch('password', '');

  const onSubmit = async (data: ResetPasswordForm) => {
    if (!token) {
      setError('无效的重置链接');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      await api.post('/auth/reset-password', {
        token,
        password: data.password,
      });

      setIsSuccess(true);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          '密码重置失败，链接可能已过期，请重新申请'
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Invalid Token State
  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 px-4">
        <div className="w-full max-w-md text-center">
          <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <AlertCircle className="w-8 h-8 text-red-400" />
          </div>
          <h2 className="font-display text-xl font-bold text-white mb-3">
            无效的链接
          </h2>
          <p className="text-slate-400 text-sm mb-6">
            此密码重置链接无效或已过期，请重新申请。
          </p>
          <Link
            href="/forgot-password"
            className="inline-block bg-primary-500 hover:bg-primary-600 text-white px-6 py-3 rounded-lg font-medium transition-all"
          >
            重新申请
          </Link>
        </div>
      </div>
    );
  }

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
          {isSuccess ? (
            // Success State
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-8 h-8 text-green-400" />
              </div>
              <h2 className="font-display text-xl font-bold text-white mb-3">
                密码已重置
              </h2>
              <p className="text-slate-400 text-sm mb-6">
                您的密码已成功重置，现在可以使用新密码登录了。
              </p>
              <Link
                href="/login"
                className="block w-full bg-primary-500 hover:bg-primary-600 text-white py-3 rounded-lg font-medium transition-all text-center"
              >
                前往登录
              </Link>
            </div>
          ) : (
            // Form State
            <>
              {/* Back Link */}
              <Link
                href="/login"
                className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-6 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                返回登录
              </Link>

              <div className="mb-6">
                <h2 className="font-display text-xl font-bold text-white mb-2">
                  重置密码
                </h2>
                <p className="text-slate-400 text-sm">请输入您的新密码。</p>
              </div>

              {/* Error Message */}
              {error && (
                <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                {/* New Password */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    新密码
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      {...register('password')}
                      className="w-full pl-12 pr-12 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                      placeholder="至少8个字符"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors"
                    >
                      {showPassword ? (
                        <EyeOff className="w-5 h-5" />
                      ) : (
                        <Eye className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                  {errors.password && (
                    <p className="mt-1.5 text-sm text-red-400">
                      {errors.password.message}
                    </p>
                  )}
                  <PasswordStrength password={password} />
                </div>

                {/* Confirm Password */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    确认密码
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      {...register('confirmPassword')}
                      className="w-full pl-12 pr-12 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                      placeholder="再次输入密码"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors"
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="w-5 h-5" />
                      ) : (
                        <Eye className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                  {errors.confirmPassword && (
                    <p className="mt-1.5 text-sm text-red-400">
                      {errors.confirmPassword.message}
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
                      重置中...
                    </>
                  ) : (
                    '重置密码'
                  )}
                </button>
              </form>
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

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-slate-900">
          <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
        </div>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
