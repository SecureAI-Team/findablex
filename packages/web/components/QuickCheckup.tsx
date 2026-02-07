'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Zap,
  Loader2,
  Globe,
  Tag,
  ArrowRight,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

const INDUSTRIES = [
  { value: '', label: '不指定' },
  { value: 'saas', label: 'SaaS / 软件' },
  { value: 'ecommerce', label: '电商 / 零售' },
  { value: 'education', label: '教育 / 培训' },
  { value: 'finance', label: '金融 / 理财' },
  { value: 'health', label: '健康 / 医疗' },
];

export default function QuickCheckup() {
  const router = useRouter();
  const [brandName, setBrandName] = useState('');
  const [domain, setDomain] = useState('');
  const [industry, setIndustry] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<any>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!brandName.trim()) return;

    setIsLoading(true);
    setError('');
    setResult(null);

    try {
      const res = await api.post('/projects/quick-checkup', {
        brand_name: brandName.trim(),
        domain: domain.trim(),
        industry,
        max_engines: 3,
      });
      setResult(res.data);

      // Auto-navigate to project after 2s
      setTimeout(() => {
        router.push(`/projects/${res.data.project_id}`);
      }, 2000);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (detail?.message) {
        setError(detail.message);
      } else {
        setError('体检启动失败，请稍后重试');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-gradient-to-br from-primary-500/5 to-purple-500/5 border border-primary-500/20 rounded-2xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-primary-500/10 rounded-xl flex items-center justify-center">
          <Zap className="w-5 h-5 text-primary-400" />
        </div>
        <div>
          <h3 className="font-medium text-white">一键体检</h3>
          <p className="text-sm text-slate-400">输入品牌名，自动生成查询词并开始 AI 可见性体检</p>
        </div>
      </div>

      {result ? (
        <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
          <div className="flex items-center gap-3 mb-3">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <span className="font-medium text-white">体检已启动！</span>
          </div>
          <p className="text-sm text-slate-400 mb-3">{result.message}</p>
          <div className="flex flex-wrap gap-2 mb-4">
            {result.engines_used?.map((engine: string) => (
              <span
                key={engine}
                className="text-xs bg-primary-500/10 text-primary-400 px-2 py-1 rounded"
              >
                {engine}
              </span>
            ))}
          </div>
          <p className="text-xs text-slate-500">
            预计 {result.estimated_time_minutes} 分钟完成，正在跳转到项目页面...
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Brand name input */}
          <div className="relative">
            <Tag className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              placeholder="输入品牌名称，如：华为、小米、蔚来..."
              className="w-full pl-10 pr-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-white placeholder:text-slate-500 focus:outline-none focus:border-primary-500 transition-colors"
              disabled={isLoading}
            />
          </div>

          {/* Advanced toggle */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-xs text-slate-500 hover:text-slate-400 transition-colors"
          >
            {showAdvanced ? '收起高级选项' : '展开高级选项（域名、行业）'}
          </button>

          {/* Advanced fields */}
          {showAdvanced && (
            <div className="space-y-3">
              <div className="relative">
                <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  placeholder="官网域名（可选），如：huawei.com"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-800/50 border border-slate-700 rounded-lg text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-primary-500 transition-colors"
                  disabled={isLoading}
                />
              </div>
              <select
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-800/50 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-primary-500 transition-colors"
                disabled={isLoading}
              >
                {INDUSTRIES.map((ind) => (
                  <option key={ind.value} value={ind.value}>
                    {ind.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 text-sm text-red-400">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={isLoading || !brandName.trim()}
            className={cn(
              'w-full flex items-center justify-center gap-2 py-3 rounded-xl font-medium transition-all',
              isLoading || !brandName.trim()
                ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                : 'bg-primary-500 hover:bg-primary-600 text-white shadow-lg shadow-primary-500/25'
            )}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                正在生成查询词并启动体检...
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                开始一键体检
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>
      )}
    </div>
  );
}
