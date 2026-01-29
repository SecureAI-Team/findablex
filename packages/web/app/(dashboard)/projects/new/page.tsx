'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Loader2, Plus, X, Globe, Tag, FileText, Sparkles, Lock } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { analytics } from '@/lib/analytics';

const projectSchema = z.object({
  name: z.string().min(2, '项目名称至少2个字符'),
  target_domain: z.string().min(1, '请输入目标域名'),
  description: z.string().optional(),
});

type ProjectForm = z.infer<typeof projectSchema>;

// 备用模板（API 加载失败时使用）
const fallbackTemplates = [
  { id: 'healthcare', name: '医疗健康', industry: 'healthcare', query_count: 30, free_preview: 10, preview_queries: [] },
  { id: 'finance', name: '金融科技', industry: 'fintech', query_count: 30, free_preview: 10, preview_queries: [] },
  { id: 'custom', name: '自定义', industry: 'custom', query_count: 0, free_preview: 10, preview_queries: [] },
];

interface CheckupTemplate {
  id: string;
  name: string;
  industry: string;
  description?: string;
  query_count: number;
  free_preview: number;
  preview_queries: Array<{
    text: string;
    stage?: string;
    type?: string;
    risk?: string;
    role?: string;
  }>;
}

export default function NewProjectPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [userIndustry, setUserIndustry] = useState<string | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('custom');
  const [customQueries, setCustomQueries] = useState<string[]>(['']);
  const [templates, setTemplates] = useState<CheckupTemplate[]>(fallbackTemplates);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProjectForm>({
    resolver: zodResolver(projectSchema),
  });

  // 行业到模板的映射
  const industryTemplateMap: Record<string, string[]> = {
    'ot_security': ['ot_security_purchase', 'ot_security_compliance', 'ot_security_technical'],
    'industrial_software': ['ot_security_purchase', 'ot_security_technical'],
    'cybersecurity': ['cybersecurity_purchase', 'ot_security_compliance'],
    'saas': ['saas_purchase', 'brand_visibility'],
    'fintech': ['brand_visibility', 'competitor_analysis'],
    'healthcare': ['brand_visibility', 'competitor_analysis'],
    'education': ['brand_visibility', 'competitor_analysis'],
    'ecommerce': ['brand_visibility', 'competitor_analysis'],
    'manufacturing': ['ot_security_purchase', 'ot_security_technical'],
  };

  const isRecommendedTemplate = (templateId: string) => {
    if (!userIndustry) return false;
    const recommendedTemplates = industryTemplateMap[userIndustry] || [];
    return recommendedTemplates.includes(templateId);
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch user data including industry
        const userRes = await api.get('/auth/me');
        setWorkspaceId(userRes.data.default_workspace_id);
        setUserIndustry(userRes.data.industry || null);
        
        // Fetch checkup templates from API (filter by user industry if available)
        const industry = userRes.data.industry;
        const templatesUrl = industry 
          ? `/projects/templates/checkup?industry=${industry}`
          : '/projects/templates/checkup';
        const templatesRes = await api.get(templatesUrl);
        
        if (templatesRes.data && templatesRes.data.length > 0) {
          // Sort templates: recommended first, then general, then custom at end
          const sortedTemplates = [...templatesRes.data].sort((a, b) => {
            const aRecommended = industry && industryTemplateMap[industry]?.includes(a.id);
            const bRecommended = industry && industryTemplateMap[industry]?.includes(b.id);
            if (aRecommended && !bRecommended) return -1;
            if (!aRecommended && bRecommended) return 1;
            return 0;
          });
          
          // Add custom template option at the end
          setTemplates([
            ...sortedTemplates,
            { id: 'custom', name: '自定义', industry: 'custom', query_count: 0, free_preview: 10, preview_queries: [] },
          ]);
          
          // Auto-select first recommended template if available
          if (industry && industryTemplateMap[industry]?.length > 0) {
            const firstRecommended = sortedTemplates.find(t => industryTemplateMap[industry].includes(t.id));
            if (firstRecommended) {
              setSelectedTemplateId(firstRecommended.id);
            }
          }
        }
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setIsLoadingTemplates(false);
      }
    };
    fetchData();
  }, []);

  const handleAddQuery = () => {
    setCustomQueries([...customQueries, '']);
  };

  const handleRemoveQuery = (index: number) => {
    setCustomQueries(customQueries.filter((_, i) => i !== index));
  };

  const handleQueryChange = (index: number, value: string) => {
    const updated = [...customQueries];
    updated[index] = value;
    setCustomQueries(updated);
  };

  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId);

  const onSubmit = async (data: ProjectForm) => {
    if (!workspaceId) {
      setError('无法获取工作空间信息');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      // Create project
      const cleanDomain = data.target_domain.replace(/^https?:\/\//, '').replace(/\/$/, '');
      const projectRes = await api.post('/projects', {
        workspace_id: workspaceId,
        name: data.name,
        target_domains: [cleanDomain],
        industry_template: selectedTemplateId !== 'custom' ? selectedTemplateId : undefined,
        description: data.description,
      });

      const projectId = projectRes.data.id;

      // Track project creation
      analytics.trackProjectCreated(projectId, selectedTemplate?.industry);

      // Add queries from template or custom
      let queriesCount = 0;
      if (selectedTemplateId === 'custom') {
        const queries = customQueries.filter((q) => q.trim());
        if (queries.length > 0) {
          await api.post(`/projects/${projectId}/queries/import`, {
            queries: queries.map((q) => ({ query_text: q, category: 'default' })),
          });
          queriesCount = queries.length;
        }
      } else if (selectedTemplate) {
        // Use the full template queries (API will handle this based on template_id)
        // Queries are loaded from the template on the backend
        await api.post(`/projects/${projectId}/queries/from-template`, {
          template_id: selectedTemplateId,
        });
        
        // Track template selection
        analytics.trackTemplateSelected(selectedTemplateId, selectedTemplate.name);
        queriesCount = selectedTemplate.query_count;
      }

      // Track queries generated
      if (queriesCount > 0) {
        analytics.trackQueriesGenerated(projectId, queriesCount, selectedTemplateId);
      }

      router.push(`/projects/${projectId}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || '创建项目失败');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/projects"
          className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          返回项目列表
        </Link>
        <h1 className="font-display text-2xl font-bold text-white">创建新项目</h1>
        <p className="mt-1 text-slate-400">设置您的 GEO 体检项目</p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Basic Info */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 space-y-5">
          <h2 className="font-medium text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary-400" />
            基本信息
          </h2>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              项目名称 <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              {...register('name')}
              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="例如：品牌 GEO 监测"
            />
            {errors.name && (
              <p className="mt-1.5 text-sm text-red-400">{errors.name.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              目标域名 <span className="text-red-400">*</span>
            </label>
            <div className="relative">
              <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
              <input
                type="text"
                {...register('target_domain')}
                className="w-full pl-12 pr-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="example.com"
              />
            </div>
            {errors.target_domain && (
              <p className="mt-1.5 text-sm text-red-400">{errors.target_domain.message}</p>
            )}
            <p className="mt-1.5 text-xs text-slate-500">
              输入您要监测的域名，系统将分析该域名在 AI 搜索中的引用情况
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              项目描述
            </label>
            <textarea
              {...register('description')}
              rows={3}
              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              placeholder="描述这个项目的目的..."
            />
          </div>
        </div>

        {/* Industry Template */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 space-y-5">
          <h2 className="font-medium text-white flex items-center gap-2">
            <Tag className="w-5 h-5 text-primary-400" />
            体检模板
          </h2>
          <p className="text-sm text-slate-400">
            选择行业体检模板，获取预置的关键问题集
          </p>

          {isLoadingTemplates ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {templates.map((template) => (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => setSelectedTemplateId(template.id)}
                  className={cn(
                    'p-4 rounded-lg border text-left transition-all',
                    selectedTemplateId === template.id
                      ? 'border-primary-500 bg-primary-500/10'
                      : 'border-slate-600 hover:border-slate-500'
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className={cn(
                      'font-medium',
                      selectedTemplateId === template.id ? 'text-primary-400' : 'text-white'
                    )}>
                      {template.name}
                    </span>
                    {template.id !== 'custom' && isRecommendedTemplate(template.id) && (
                      <span className="flex items-center gap-1 text-xs text-green-400 bg-green-400/10 px-2 py-0.5 rounded">
                        <Sparkles className="w-3 h-3" />
                        为您推荐
                      </span>
                    )}
                    {template.id !== 'custom' && !isRecommendedTemplate(template.id) && template.industry === 'general' && (
                      <span className="flex items-center gap-1 text-xs text-slate-400 bg-slate-600/30 px-2 py-0.5 rounded">
                        通用
                      </span>
                    )}
                  </div>
                  {template.description && (
                    <p className="text-xs text-slate-500 mt-1">{template.description}</p>
                  )}
                  {template.id !== 'custom' && template.query_count > 0 && (
                    <div className="mt-3 flex items-center gap-3 text-xs">
                      <span className="text-slate-300">
                        覆盖 <span className="text-primary-400 font-medium">{template.query_count}</span> 条关键问题
                      </span>
                      <span className="flex items-center gap-1 text-slate-500">
                        <Lock className="w-3 h-3" />
                        免费版可测 {template.free_preview} 条
                      </span>
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}

          {selectedTemplateId !== 'custom' && selectedTemplate && selectedTemplate.preview_queries.length > 0 && (
            <div className="mt-4 p-4 bg-slate-700/30 rounded-lg">
              <p className="text-sm text-slate-400 mb-2">问题预览（共 {selectedTemplate.query_count} 条）：</p>
              <ul className="space-y-1">
                {selectedTemplate.preview_queries.map((q, i) => (
                  <li key={i} className="text-sm text-slate-300 flex items-center gap-2">
                    <span>• {q.text}</span>
                    {q.stage && (
                      <span className="text-xs bg-slate-600/50 px-1.5 py-0.5 rounded text-slate-400">
                        {q.stage}
                      </span>
                    )}
                  </li>
                ))}
                {selectedTemplate.query_count > 5 && (
                  <li className="text-xs text-slate-500 mt-2">
                    ...还有 {selectedTemplate.query_count - 5} 条问题
                  </li>
                )}
              </ul>
            </div>
          )}

          {selectedTemplateId === 'custom' && (
            <div className="space-y-3">
              <p className="text-sm text-slate-400">添加自定义查询（可选）：</p>
              {customQueries.map((query, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => handleQueryChange(index, e.target.value)}
                    className="flex-1 px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder={`查询 ${index + 1}`}
                  />
                  {customQueries.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveQuery(index)}
                      className="p-2.5 text-slate-400 hover:text-red-400 transition-colors"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={handleAddQuery}
                className="inline-flex items-center gap-2 text-sm text-primary-400 hover:text-primary-300 transition-colors"
              >
                <Plus className="w-4 h-4" />
                添加查询
              </button>
            </div>
          )}
        </div>

        {/* Submit */}
        <div className="flex items-center justify-end gap-4">
          <Link
            href="/projects"
            className="px-6 py-2.5 text-slate-400 hover:text-white transition-colors"
          >
            取消
          </Link>
          <button
            type="submit"
            disabled={isLoading}
            className="bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/50 text-white px-6 py-2.5 rounded-lg font-medium transition-all flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                创建中...
              </>
            ) : (
              '创建项目'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
