'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useState, useEffect, Suspense, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Eye,
  EyeOff,
  Loader2,
  Mail,
  Lock,
  User,
  Ticket,
  ArrowLeft,
  Check,
  X,
  Building2,
  Briefcase,
  Globe,
} from 'lucide-react';
import { api } from '@/lib/api';
import { analytics } from '@/lib/analytics';

// 行业选项
const industryOptions = [
  { value: 'ot_security', label: 'OT安全/工业控制' },
  { value: 'cybersecurity', label: '网络安全' },
  { value: 'industrial_software', label: '工业软件' },
  { value: 'saas', label: 'SaaS/企业服务' },
  { value: 'fintech', label: '金融科技' },
  { value: 'healthcare', label: '医疗健康' },
  { value: 'education', label: '教育培训' },
  { value: 'ecommerce', label: '电商零售' },
  { value: 'manufacturing', label: '制造业' },
  { value: 'other', label: '其他' },
];

// 业务角色选项
const roleOptions = [
  { value: 'marketing', label: '市场负责人' },
  { value: 'growth', label: '增长负责人' },
  { value: 'sales', label: '销售负责人' },
  { value: 'brand_pr', label: '品牌/公关' },
  { value: 'compliance', label: '法务合规' },
  { value: 'security', label: '安全负责人' },
  { value: 'presales', label: '售前/解决方案' },
  { value: 'product', label: '产品负责人' },
  { value: 'other', label: '其他' },
];

// 地区选项
const regionOptions = [
  { value: 'cn', label: '中国大陆' },
  { value: 'hk_tw', label: '港澳台' },
  { value: 'en_us', label: '北美' },
  { value: 'en_eu', label: '欧洲' },
  { value: 'apac', label: '亚太其他' },
  { value: 'global', label: '全球' },
];

const registerSchema = z.object({
  email: z.string().email('请输入有效的邮箱地址'),
  full_name: z.string().min(2, '姓名至少2个字符'),
  password: z.string().min(8, '密码至少8个字符'),
  company_name: z.string().optional(),
  industry: z.string().optional(),
  business_role: z.string().optional(),
  region: z.string().optional(),
  invite_code: z.string().optional(),
  agree_terms: z.boolean().refine((val) => val === true, {
    message: '请阅读并同意服务条款和隐私政策',
  }),
});

type RegisterForm = z.infer<typeof registerSchema>;

function PasswordStrength({ password }: { password: string }) {
  const checks = useMemo(() => {
    return {
      length: password.length >= 8,
      lowercase: /[a-z]/.test(password),
      uppercase: /[A-Z]/.test(password),
      number: /[0-9]/.test(password),
      special: /[^a-zA-Z0-9]/.test(password),
    };
  }, [password]);

  const strength = useMemo(() => {
    const passed = Object.values(checks).filter(Boolean).length;
    if (passed === 0) return { label: '', color: '', width: '0%' };
    if (passed <= 2) return { label: '弱', color: 'bg-red-500', width: '33%' };
    if (passed <= 4)
      return { label: '中', color: 'bg-yellow-500', width: '66%' };
    return { label: '强', color: 'bg-green-500', width: '100%' };
  }, [checks]);

  if (!password) return null;

  return (
    <div className="mt-3 space-y-2">
      {/* Progress Bar */}
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

      {/* Requirements */}
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

interface WorkspaceInviteInfo {
  valid: boolean;
  workspace_name?: string;
  role?: string;
  reason?: string;
}

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [workspaceInvite, setWorkspaceInvite] = useState<WorkspaceInviteInfo | null>(null);
  const [isValidatingInvite, setIsValidatingInvite] = useState(false);

  const plan = searchParams.get('plan');
  const inviteCode = searchParams.get('invite');

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      agree_terms: false,
      region: 'cn',
      invite_code: inviteCode || '',
    },
  });

  const password = watch('password', '');

  // Validate workspace invite code on load
  useEffect(() => {
    const validateInvite = async () => {
      if (!inviteCode) return;
      
      setIsValidatingInvite(true);
      try {
        const res = await api.get(`/invite-codes/workspace/${inviteCode}`);
        setWorkspaceInvite(res.data);
        if (res.data.valid) {
          setValue('invite_code', inviteCode);
        }
      } catch (err) {
        setWorkspaceInvite({ valid: false, reason: '邀请链接无效' });
      } finally {
        setIsValidatingInvite(false);
      }
    };
    
    validateInvite();
  }, [inviteCode, setValue]);

  const onSubmit = async (data: RegisterForm) => {
    setIsLoading(true);
    setError('');

    try {
      await api.post('/auth/register', {
        email: data.email,
        full_name: data.full_name,
        password: data.password,
        company_name: data.company_name || undefined,
        industry: data.industry || undefined,
        business_role: data.business_role || undefined,
        region: data.region || 'cn',
        invite_code: data.invite_code || undefined,
      });

      // Track registration
      analytics.trackRegistration({
        industry: data.industry,
        business_role: data.business_role,
        region: data.region || 'cn',
        has_invite_code: !!data.invite_code,
      });

      // Redirect to login with success message
      router.push('/login?registered=true');
    } catch (err: any) {
      setError(
        err.response?.data?.detail || '注册失败，请稍后重试'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-slate-900">
      {/* Left Panel - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-accent-600 to-primary-600 p-12 flex-col justify-between relative overflow-hidden">
        <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center opacity-10" />
        <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-white/10 rounded-full blur-3xl" />
        <div className="absolute -top-32 -left-32 w-96 h-96 bg-white/10 rounded-full blur-3xl" />

        <div className="relative">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 backdrop-blur rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xl">F</span>
            </div>
            <span className="font-display text-2xl font-bold text-white">
              FindableX
            </span>
          </Link>
        </div>

        <div className="relative">
          <h1 className="font-display text-4xl font-bold text-white mb-4">
            开启 GEO 优化之旅
          </h1>
          <p className="text-white/80 text-lg mb-8">
            注册账户，免费体验 AI 时代的品牌可见性分析
          </p>

          {/* Features List */}
          <div className="space-y-4">
            {[
              '免费获得 10 次体检机会',
              '支持主流 AI 搜索引擎',
              '专业的指标分析报告',
            ].map((feature) => (
              <div key={feature} className="flex items-center gap-3">
                <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center">
                  <Check className="w-3 h-3 text-white" />
                </div>
                <span className="text-white/90">{feature}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="relative text-white/60 text-sm">
          © {new Date().getFullYear()} FindableX. All rights reserved.
        </div>
      </div>

      {/* Right Panel - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 overflow-y-auto">
        <div className="w-full max-w-md py-8">
          {/* Mobile Logo */}
          <div className="lg:hidden text-center mb-8">
            <Link href="/" className="inline-flex items-center gap-2">
              <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xl">F</span>
              </div>
              <span className="font-display text-2xl font-bold text-white">
                FindableX
              </span>
            </Link>
          </div>

          {/* Back Link */}
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-8 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            返回首页
          </Link>

          <div className="mb-8">
            <h2 className="font-display text-2xl font-bold text-white mb-2">
              创建账户
              {plan === 'pro' && (
                <span className="ml-2 text-sm font-normal text-primary-400">
                  (专业版试用)
                </span>
              )}
            </h2>
            <p className="text-slate-400">
              已有账户？{' '}
              <Link
                href="/login"
                className="text-primary-400 hover:text-primary-300 transition-colors"
              >
                立即登录
              </Link>
            </p>
          </div>

          {/* Workspace Invite Banner */}
          {workspaceInvite && workspaceInvite.valid && (
            <div className="mb-6 p-4 bg-green-500/10 border border-green-500/50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center">
                  <Building2 className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <p className="text-green-400 text-sm font-medium">
                    您已被邀请加入
                  </p>
                  <p className="text-white font-semibold">
                    {workspaceInvite.workspace_name}
                  </p>
                  <p className="text-green-400/70 text-xs mt-0.5">
                    加入后的角色: {workspaceInvite.role === 'admin' ? '管理员' : 
                                  workspaceInvite.role === 'analyst' ? '分析师' :
                                  workspaceInvite.role === 'researcher' ? '研究员' : '查看者'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Invalid Invite Warning */}
          {workspaceInvite && !workspaceInvite.valid && (
            <div className="mb-6 p-4 bg-amber-500/10 border border-amber-500/50 rounded-lg text-amber-400 text-sm">
              邀请链接无效: {workspaceInvite.reason || '链接已过期或已被撤销'}
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                姓名
              </label>
              <div className="relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type="text"
                  {...register('full_name')}
                  className="w-full pl-12 pr-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  placeholder="您的姓名"
                />
              </div>
              {errors.full_name && (
                <p className="mt-1.5 text-sm text-red-400">
                  {errors.full_name.message}
                </p>
              )}
            </div>

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
                  className="w-full pl-12 pr-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  placeholder="you@example.com"
                />
              </div>
              {errors.email && (
                <p className="mt-1.5 text-sm text-red-400">
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                密码
              </label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  {...register('password')}
                  className="w-full pl-12 pr-12 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
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

            {/* Company Name */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                公司名称 <span className="text-slate-500">(可选)</span>
              </label>
              <div className="relative">
                <Building2 className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type="text"
                  {...register('company_name')}
                  className="w-full pl-12 pr-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  placeholder="您的公司名称"
                />
              </div>
            </div>

            {/* Industry & Role Row */}
            <div className="grid grid-cols-2 gap-4">
              {/* Industry */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  行业
                </label>
                <div className="relative">
                  <Briefcase className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 pointer-events-none" />
                  <select
                    {...register('industry')}
                    className="w-full pl-12 pr-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all appearance-none cursor-pointer"
                  >
                    <option value="">请选择</option>
                    {industryOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Business Role */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  角色
                </label>
                <div className="relative">
                  <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 pointer-events-none" />
                  <select
                    {...register('business_role')}
                    className="w-full pl-12 pr-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all appearance-none cursor-pointer"
                  >
                    <option value="">请选择</option>
                    {roleOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Region */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                地区
              </label>
              <div className="relative">
                <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 pointer-events-none" />
                <select
                  {...register('region')}
                  className="w-full pl-12 pr-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all appearance-none cursor-pointer"
                >
                  {regionOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Invite Code - Hidden when using workspace invite */}
            {!(workspaceInvite && workspaceInvite.valid) && (
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  邀请码 <span className="text-slate-500">(可选)</span>
                </label>
                <div className="relative">
                  <Ticket className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <input
                    type="text"
                    {...register('invite_code')}
                    className="w-full pl-12 pr-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                    placeholder="输入邀请码获得额外权益"
                  />
                </div>
              </div>
            )}
            
            {/* Hidden invite code for workspace invite */}
            {workspaceInvite && workspaceInvite.valid && (
              <input type="hidden" {...register('invite_code')} />
            )}

            {/* Terms Agreement */}
            <div>
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  id="agree_terms"
                  {...register('agree_terms')}
                  className="mt-1 w-4 h-4 rounded border-slate-600 bg-slate-800 text-primary-500 focus:ring-primary-500 focus:ring-offset-slate-900"
                />
                <label
                  htmlFor="agree_terms"
                  className="text-sm text-slate-400"
                >
                  我已阅读并同意{' '}
                  <Link
                    href="/terms"
                    className="text-primary-400 hover:text-primary-300"
                    target="_blank"
                  >
                    服务条款
                  </Link>{' '}
                  和{' '}
                  <Link
                    href="/privacy"
                    className="text-primary-400 hover:text-primary-300"
                    target="_blank"
                  >
                    隐私政策
                  </Link>
                </label>
              </div>
              {errors.agree_terms && (
                <p className="mt-1.5 text-sm text-red-400">
                  {errors.agree_terms.message}
                </p>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-primary-500 to-accent-500 hover:from-primary-600 hover:to-accent-600 disabled:from-primary-500/50 disabled:to-accent-500/50 text-white py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2 shadow-lg shadow-primary-500/25"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  注册中...
                </>
              ) : (
                '创建账户'
              )}
            </button>
          </form>

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

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-slate-900">
          <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
        </div>
      }
    >
      <RegisterForm />
    </Suspense>
  );
}
