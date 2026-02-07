'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowRight,
  ArrowLeft,
  Building2,
  Globe,
  Search,
  Loader2,
  CheckCircle,
  Sparkles,
  Target,
  BarChart3,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

const industries = [
  { id: 'ot_security', name: 'OT安全/工业控制', icon: '🔒' },
  { id: 'cybersecurity', name: '网络安全', icon: '🛡️' },
  { id: 'industrial_software', name: '工业软件', icon: '🏭' },
  { id: 'saas', name: 'SaaS/企业服务', icon: '☁️' },
  { id: 'fintech', name: '金融科技', icon: '💳' },
  { id: 'healthcare', name: '医疗健康', icon: '🏥' },
  { id: 'education', name: '教育培训', icon: '📚' },
  { id: 'ecommerce', name: '电商零售', icon: '🛒' },
  { id: 'manufacturing', name: '制造业', icon: '⚙️' },
  { id: 'other', name: '其他行业', icon: '📋' },
];

const steps = [
  { id: 1, title: '选择行业', desc: '告诉我们您的行业' },
  { id: 2, title: '设置项目', desc: '创建您的第一个项目' },
  { id: 3, title: '开始体检', desc: '查看 AI 可见性报告' },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedIndustry, setSelectedIndustry] = useState('');
  const [projectName, setProjectName] = useState('');
  const [targetDomain, setTargetDomain] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [createdProjectId, setCreatedProjectId] = useState<string | null>(null);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false);
  const [templateApplied, setTemplateApplied] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchWorkspace = async () => {
      try {
        const res = await api.get('/auth/me');
        setWorkspaceId(res.data.default_workspace_id);
        if (res.data.full_name) {
          setCompanyName(res.data.company_name || '');
        }
      } catch (err) {
        console.error('Failed to fetch user info:', err);
      }
    };
    fetchWorkspace();
  }, []);

  const handleIndustrySelect = (industryId: string) => {
    setSelectedIndustry(industryId);
    const industry = industries.find((i) => i.id === industryId);
    if (industry && !projectName) {
      setProjectName(`${industry.name} - GEO 体检`);
    }
  };

  const handleCreateProject = async () => {
    if (!workspaceId || !projectName.trim()) return;

    setIsCreating(true);
    setError('');

    try {
      // Update user profile with industry
      try {
        await api.put('/auth/me', {
          industry: selectedIndustry,
          company_name: companyName || undefined,
        });
      } catch (profileErr) {
        // Non-critical, continue
        console.error('Failed to update profile:', profileErr);
      }

      // Create the project
      const projectRes = await api.post('/projects', {
        workspace_id: workspaceId,
        name: projectName.trim(),
        target_domains: targetDomain.trim() ? [targetDomain.trim()] : [],
        industry_template: selectedIndustry,
        description: `通过 GEO 体检了解品牌在 AI 搜索中的可见性`,
      });

      const projectId = projectRes.data.id;
      setCreatedProjectId(projectId);

      // Try to apply template queries
      setIsLoadingTemplates(true);
      try {
        // Check if there's a matching template
        const templatesRes = await api.get(
          `/templates/checkup?industry=${selectedIndustry}`
        );
        if (templatesRes.data && templatesRes.data.length > 0) {
          const template = templatesRes.data[0];
          await api.post(`/projects/${projectId}/queries/from-template`, {
            template_id: template.id,
          });
          setTemplateApplied(true);
        }
      } catch (templateErr) {
        // Template loading is optional
        console.error('Template not applied:', templateErr);
      }
      setIsLoadingTemplates(false);

      // Move to completion step
      setCurrentStep(3);
    } catch (err: any) {
      setError(err.response?.data?.detail || '创建项目失败，请重试');
    } finally {
      setIsCreating(false);
    }
  };

  const handleComplete = () => {
    if (createdProjectId) {
      router.push(`/projects/${createdProjectId}`);
    } else {
      router.push('/dashboard');
    }
  };

  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-2xl">
        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-2 mb-12">
          {steps.map((step, idx) => (
            <div key={step.id} className="flex items-center">
              <div
                className={cn(
                  'w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold transition-all',
                  currentStep > step.id
                    ? 'bg-green-500 text-white'
                    : currentStep === step.id
                    ? 'bg-primary-500 text-white'
                    : 'bg-slate-700 text-slate-400'
                )}
              >
                {currentStep > step.id ? (
                  <CheckCircle className="w-5 h-5" />
                ) : (
                  step.id
                )}
              </div>
              {idx < steps.length - 1 && (
                <div
                  className={cn(
                    'w-16 h-0.5 mx-2',
                    currentStep > step.id ? 'bg-green-500' : 'bg-slate-700'
                  )}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step 1: Industry Selection */}
        {currentStep === 1 && (
          <div className="space-y-8 animate-in fade-in duration-300">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-500/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Sparkles className="w-8 h-8 text-primary-400" />
              </div>
              <h1 className="font-display text-3xl font-bold text-white mb-3">
                欢迎使用 FindableX
              </h1>
              <p className="text-slate-400 text-lg">
                选择您的行业，我们将为您推荐最适合的体检模板
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {industries.map((industry) => (
                <button
                  key={industry.id}
                  onClick={() => handleIndustrySelect(industry.id)}
                  className={cn(
                    'p-4 rounded-xl border text-left transition-all hover:scale-[1.02]',
                    selectedIndustry === industry.id
                      ? 'bg-primary-500/10 border-primary-500 ring-1 ring-primary-500'
                      : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600'
                  )}
                >
                  <span className="text-2xl mb-2 block">{industry.icon}</span>
                  <span className="text-sm font-medium text-white">
                    {industry.name}
                  </span>
                </button>
              ))}
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setCurrentStep(2)}
                disabled={!selectedIndustry}
                className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/30 disabled:cursor-not-allowed text-white px-8 py-3 rounded-lg font-medium transition-all"
              >
                下一步
                <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Project Setup */}
        {currentStep === 2 && (
          <div className="space-y-8 animate-in fade-in duration-300">
            <div className="text-center">
              <div className="w-16 h-16 bg-accent-500/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Target className="w-8 h-8 text-accent-400" />
              </div>
              <h1 className="font-display text-3xl font-bold text-white mb-3">
                创建您的项目
              </h1>
              <p className="text-slate-400 text-lg">
                设置项目名称和目标域名，我们将自动加载查询模板
              </p>
            </div>

            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
                {error}
              </div>
            )}

            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  <Building2 className="w-4 h-4 inline mr-1.5" />
                  公司名称（可选）
                </label>
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="例如：某某科技有限公司"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  <Search className="w-4 h-4 inline mr-1.5" />
                  项目名称
                </label>
                <input
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="例如：品牌 GEO 体检"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  <Globe className="w-4 h-4 inline mr-1.5" />
                  目标域名（可选，用于品牌引用检测）
                </label>
                <input
                  type="text"
                  value={targetDomain}
                  onChange={(e) => setTargetDomain(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="例如：example.com"
                />
                <p className="mt-1.5 text-xs text-slate-500">
                  输入您的公司域名，系统将自动检测 AI 回答中对您品牌的引用
                </p>
              </div>
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => setCurrentStep(1)}
                className="inline-flex items-center gap-2 text-slate-400 hover:text-white px-4 py-3 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                上一步
              </button>
              <button
                onClick={handleCreateProject}
                disabled={!projectName.trim() || isCreating}
                className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/30 disabled:cursor-not-allowed text-white px-8 py-3 rounded-lg font-medium transition-all"
              >
                {isCreating ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    创建中...
                  </>
                ) : (
                  <>
                    创建项目
                    <ArrowRight className="w-5 h-5" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Complete */}
        {currentStep === 3 && (
          <div className="space-y-8 animate-in fade-in duration-300">
            <div className="text-center">
              <div className="w-20 h-20 bg-green-500/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-10 h-10 text-green-400" />
              </div>
              <h1 className="font-display text-3xl font-bold text-white mb-3">
                项目创建成功！
              </h1>
              <p className="text-slate-400 text-lg">
                {templateApplied
                  ? '已自动加载行业查询模板，您可以直接开始体检'
                  : '接下来您可以导入查询词或创建研究任务'}
              </p>
            </div>

            {/* Summary */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">项目名称</span>
                <span className="text-white font-medium">{projectName}</span>
              </div>
              {targetDomain && (
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">目标域名</span>
                  <span className="text-white font-medium">{targetDomain}</span>
                </div>
              )}
              <div className="flex items-center justify-between">
                <span className="text-slate-400">行业</span>
                <span className="text-white font-medium">
                  {industries.find((i) => i.id === selectedIndustry)?.name ||
                    '--'}
                </span>
              </div>
              {templateApplied && (
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">查询模板</span>
                  <span className="text-green-400 font-medium flex items-center gap-1">
                    <CheckCircle className="w-4 h-4" />
                    已加载
                  </span>
                </div>
              )}
            </div>

            {/* Next Steps */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <button
                onClick={handleComplete}
                className="p-4 bg-primary-500/10 border border-primary-500/30 rounded-xl text-left hover:bg-primary-500/20 transition-all group"
              >
                <BarChart3 className="w-8 h-8 text-primary-400 mb-3" />
                <h3 className="font-medium text-white group-hover:text-primary-300 transition-colors">
                  进入项目
                </h3>
                <p className="text-sm text-slate-400 mt-1">
                  查看项目详情，创建研究任务
                </p>
              </button>
              <button
                onClick={() => router.push('/dashboard')}
                className="p-4 bg-slate-800/50 border border-slate-700/50 rounded-xl text-left hover:bg-slate-700/30 transition-all group"
              >
                <Globe className="w-8 h-8 text-slate-400 mb-3" />
                <h3 className="font-medium text-white group-hover:text-slate-300 transition-colors">
                  返回仪表盘
                </h3>
                <p className="text-sm text-slate-400 mt-1">
                  稍后再配置项目详情
                </p>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
