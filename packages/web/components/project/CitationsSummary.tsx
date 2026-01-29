'use client';

import { useEffect, useState } from 'react';
import {
  Globe,
  Link as LinkIcon,
  Loader2,
  BarChart3,
  ExternalLink,
  TrendingUp,
  Target,
  CheckCircle,
  Eye,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface TargetDomainMatch {
  domain: string;
  url: string;
  title: string | null;
  engine: string;
  query_text: string | null;
}

interface CitationSummaryData {
  total_citations: number;
  unique_domains: number;
  top_domains: Array<{
    domain: string;
    count: number;
  }>;
  citations_by_engine: Record<string, number>;
  // Target domain analysis
  target_domains: string[];
  target_domain_citations: number;
  visibility_score: number;
  target_domain_matches: TargetDomainMatch[];
}

interface CitationsSummaryProps {
  projectId: string;
}

const engineNames: Record<string, string> = {
  deepseek: 'DeepSeek',
  kimi: 'Kimi',
  doubao: '豆包',
  chatglm: 'ChatGLM',
  chatgpt: 'ChatGPT',
  qwen: '通义千问',
  perplexity: 'Perplexity',
  google_sge: 'Google SGE',
  bing_copilot: 'Bing Copilot',
};

const engineColors: Record<string, string> = {
  deepseek: 'bg-purple-500',
  kimi: 'bg-blue-500',
  doubao: 'bg-orange-500',
  chatglm: 'bg-green-500',
  chatgpt: 'bg-teal-500',
  qwen: 'bg-cyan-500',
  perplexity: 'bg-indigo-500',
  google_sge: 'bg-red-500',
  bing_copilot: 'bg-sky-500',
};

export default function CitationsSummary({ projectId }: CitationsSummaryProps) {
  const [summary, setSummary] = useState<CitationSummaryData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSummary();
  }, [projectId]);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/projects/${projectId}/citations-summary`);
      setSummary(response.data);
    } catch (err) {
      console.error('Failed to fetch citations summary:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <div className="flex items-center gap-2 text-slate-400">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>加载引用统计...</span>
        </div>
      </div>
    );
  }

  if (!summary || summary.total_citations === 0) {
    return null;
  }

  const maxDomainCount = Math.max(...summary.top_domains.map((d) => d.count), 1);
  const totalEngineCount = Object.values(summary.citations_by_engine).reduce((a, b) => a + b, 0);

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
      <div className="p-6 border-b border-slate-700/50">
        <h2 className="font-display text-lg font-semibold text-white flex items-center gap-2">
          <LinkIcon className="w-5 h-5 text-primary-400" />
          引用统计
        </h2>
      </div>

      <div className="p-6 space-y-6">
        {/* Stats Overview */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-slate-700/30 rounded-lg p-4">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
              <TrendingUp className="w-4 h-4" />
              <span>总引用数</span>
            </div>
            <div className="text-3xl font-bold text-white">{summary.total_citations}</div>
          </div>
          <div className="bg-slate-700/30 rounded-lg p-4">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
              <Globe className="w-4 h-4" />
              <span>唯一域名</span>
            </div>
            <div className="text-3xl font-bold text-white">{summary.unique_domains}</div>
          </div>
          {summary.target_domains.length > 0 && (
            <>
              <div className="bg-slate-700/30 rounded-lg p-4">
                <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
                  <Target className="w-4 h-4" />
                  <span>品牌引用</span>
                </div>
                <div className="text-3xl font-bold text-green-400">{summary.target_domain_citations}</div>
              </div>
              <div className="bg-slate-700/30 rounded-lg p-4">
                <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
                  <Eye className="w-4 h-4" />
                  <span>可见性</span>
                </div>
                <div className={cn(
                  'text-3xl font-bold',
                  summary.visibility_score >= 50 ? 'text-green-400' :
                  summary.visibility_score >= 20 ? 'text-yellow-400' : 'text-red-400'
                )}>
                  {summary.visibility_score}%
                </div>
              </div>
            </>
          )}
        </div>

        {/* Target Domains Info */}
        {summary.target_domains.length > 0 && (
          <div className="bg-slate-700/20 rounded-lg p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 text-slate-300 text-sm mb-2">
              <Target className="w-4 h-4 text-primary-400" />
              <span className="font-medium">监测的目标域名</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {summary.target_domains.map((domain) => (
                <span
                  key={domain}
                  className="px-2 py-1 bg-primary-500/20 text-primary-300 text-xs rounded-md"
                >
                  {domain}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Target Domain Matches */}
        {summary.target_domain_matches.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-400" />
              品牌被引用记录 ({summary.target_domain_matches.length})
            </h3>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {summary.target_domain_matches.map((match, idx) => (
                <div
                  key={idx}
                  className="bg-green-500/10 border border-green-500/30 rounded-lg p-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-green-400 text-sm font-medium truncate">
                          {match.domain}
                        </span>
                        <span className="text-xs text-slate-500">
                          via {engineNames[match.engine] || match.engine}
                        </span>
                      </div>
                      {match.title && (
                        <div className="text-white text-sm truncate">{match.title}</div>
                      )}
                      {match.query_text && (
                        <div className="text-slate-400 text-xs mt-1 truncate">
                          查询: {match.query_text}
                        </div>
                      )}
                    </div>
                    {match.url && (
                      <a
                        href={match.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-slate-400 hover:text-white p-1"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top Domains */}
        {summary.top_domains.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-slate-400 mb-3">被引用最多的域名</h3>
            <div className="space-y-2">
              {summary.top_domains.slice(0, 5).map((item, idx) => (
                <div key={item.domain} className="flex items-center gap-3">
                  <span className="text-slate-500 text-sm w-5">{idx + 1}</span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-white text-sm truncate max-w-[200px]">
                        {item.domain}
                      </span>
                      <span className="text-slate-400 text-sm">{item.count}</span>
                    </div>
                    <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-500 rounded-full transition-all"
                        style={{ width: `${(item.count / maxDomainCount) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Citations by Engine */}
        {Object.keys(summary.citations_by_engine).length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-slate-400 mb-3">各引擎引用数</h3>
            <div className="flex flex-wrap gap-2">
              {Object.entries(summary.citations_by_engine).map(([engine, count]) => (
                <div
                  key={engine}
                  className="flex items-center gap-2 bg-slate-700/30 rounded-lg px-3 py-2"
                >
                  <div
                    className={cn(
                      'w-2 h-2 rounded-full',
                      engineColors[engine] || 'bg-slate-500'
                    )}
                  />
                  <span className="text-white text-sm">
                    {engineNames[engine] || engine}
                  </span>
                  <span className="text-slate-400 text-sm">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
