'use client';

import { useEffect, useState } from 'react';
import {
  Bot,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Loader2,
  Search,
  AlertCircle,
  MessageSquare,
  Link as LinkIcon,
  RefreshCw,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface CrawlResult {
  id: string;
  query_item_id: string;
  query_text: string;
  engine: string;
  response_text: string | null;
  citations: Array<{
    url?: string;
    title?: string;
    domain?: string;
  }>;
  crawled_at: string | null;
  error: string | null;
}

interface QueryWithResults {
  query_id: string;
  query_text: string;
  query_type: string | null;
  crawl_count: number;
  latest_crawl: string | null;
  results: CrawlResult[];
}

interface CrawlResultsTabProps {
  projectId: string;
}

const engineIcons: Record<string, string> = {
  deepseek: '🔮',
  kimi: '🌙',
  doubao: '🫘',
  chatglm: '🧠',
  chatgpt: '🤖',
  qwen: '☁️',
  perplexity: '🔍',
  google_sge: '🌐',
  bing_copilot: '💠',
};

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

export default function CrawlResultsTab({ projectId }: CrawlResultsTabProps) {
  const [queryResults, setQueryResults] = useState<QueryWithResults[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedQueryId, setSelectedQueryId] = useState<string | null>(null);
  const [engineFilter, setEngineFilter] = useState<string>('all');

  useEffect(() => {
    fetchResults();
  }, [projectId]);

  const fetchResults = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/projects/${projectId}/crawl-results`);
      setQueryResults(response.data);
      // Auto-select first query with results
      const firstWithResults = response.data.find((q: QueryWithResults) => q.crawl_count > 0);
      if (firstWithResults) {
        setSelectedQueryId(firstWithResults.query_id);
      }
      setError(null);
    } catch (err: any) {
      setError('加载研究结果失败');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '未知';
    return new Date(dateString).toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const selectedQuery = queryResults.find((q) => q.query_id === selectedQueryId);
  const filteredResults = selectedQuery?.results.filter(
    (r) => engineFilter === 'all' || r.engine === engineFilter
  ) || [];

  // Get unique engines from all results
  const availableEngines = Array.from(
    new Set(queryResults.flatMap((q) => q.results.map((r) => r.engine)))
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-12 text-center">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <p className="text-slate-300">{error}</p>
        <button
          onClick={fetchResults}
          className="mt-4 text-primary-400 hover:text-primary-300"
        >
          重试
        </button>
      </div>
    );
  }

  const totalResults = queryResults.reduce((acc, q) => acc + q.crawl_count, 0);

  if (totalResults === 0) {
    return (
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-12 text-center">
        <Bot className="w-12 h-12 text-slate-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-white mb-2">还没有研究结果</h3>
        <p className="text-slate-400 mb-6">
          前往研究页面创建爬虫任务，采集 AI 引擎的回复数据
        </p>
        <a
          href="/research/new"
          className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg font-medium transition-all"
        >
          <Bot className="w-4 h-4" />
          创建爬虫任务
        </a>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Query List (Left Panel) */}
      <div className="lg:col-span-1 bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
        <div className="p-4 border-b border-slate-700/50 flex items-center justify-between">
          <h3 className="font-medium text-white">查询词 ({queryResults.length})</h3>
          <button
            onClick={fetchResults}
            className="p-1.5 text-slate-400 hover:text-white transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        <div className="max-h-[600px] overflow-y-auto divide-y divide-slate-700/50">
          {queryResults.map((query) => (
            <button
              key={query.query_id}
              onClick={() => setSelectedQueryId(query.query_id)}
              className={cn(
                'w-full p-4 text-left transition-colors',
                selectedQueryId === query.query_id
                  ? 'bg-primary-500/10 border-l-2 border-primary-500'
                  : 'hover:bg-slate-700/30 border-l-2 border-transparent'
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="text-white text-sm line-clamp-2">{query.query_text}</span>
                <span
                  className={cn(
                    'flex-shrink-0 px-2 py-0.5 rounded-full text-xs font-medium',
                    query.crawl_count > 0
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-slate-700 text-slate-400'
                  )}
                >
                  {query.crawl_count}
                </span>
              </div>
              {query.latest_crawl && (
                <div className="text-xs text-slate-500 mt-1">
                  最近: {formatDate(query.latest_crawl)}
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Results Detail (Right Panel) */}
      <div className="lg:col-span-2 space-y-4">
        {selectedQuery ? (
          <>
            {/* Selected Query Header */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="font-medium text-white text-lg">{selectedQuery.query_text}</h3>
                  <div className="flex items-center gap-4 mt-2 text-sm text-slate-400">
                    <span>{selectedQuery.crawl_count} 个结果</span>
                    {selectedQuery.query_type && (
                      <span className="px-2 py-0.5 bg-slate-700 rounded-full text-xs">
                        {selectedQuery.query_type}
                      </span>
                    )}
                  </div>
                </div>
                {/* Engine Filter */}
                <select
                  value={engineFilter}
                  onChange={(e) => setEngineFilter(e.target.value)}
                  className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="all">全部引擎</option>
                  {availableEngines.map((engine) => (
                    <option key={engine} value={engine}>
                      {engineNames[engine] || engine}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Results List */}
            <div className="space-y-4">
              {filteredResults.length === 0 ? (
                <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-8 text-center">
                  <Search className="w-8 h-8 text-slate-600 mx-auto mb-3" />
                  <p className="text-slate-400">没有符合条件的结果</p>
                </div>
              ) : (
                filteredResults.map((result) => (
                  <ResultCard key={result.id} result={result} />
                ))
              )}
            </div>
          </>
        ) : (
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-12 text-center">
            <Search className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400">选择左侧查询词查看详细结果</p>
          </div>
        )}
      </div>
    </div>
  );
}

function ResultCard({ result }: { result: CrawlResult }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
      {/* Header */}
      <div
        className="p-4 border-b border-slate-700/50 flex items-center justify-between cursor-pointer hover:bg-slate-700/30 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <span className="text-xl">{engineIcons[result.engine] || '🤖'}</span>
          <div>
            <span className="font-medium text-white">
              {engineNames[result.engine] || result.engine}
            </span>
            <div className="text-xs text-slate-500 mt-0.5">
              {result.crawled_at ? new Date(result.crawled_at).toLocaleString('zh-CN') : '未知时间'}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {result.citations.length > 0 && (
            <span className="px-2 py-0.5 bg-primary-500/20 text-primary-300 rounded-full text-xs">
              {result.citations.length} 引用
            </span>
          )}
          {expanded ? (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-slate-400" />
          )}
        </div>
      </div>

      {/* Content */}
      {expanded && (
        <div className="p-4 space-y-4">
          {result.error ? (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
              <div className="flex items-center gap-2 text-red-400 mb-2">
                <AlertCircle className="w-4 h-4" />
                <span className="font-medium">爬取失败</span>
              </div>
              <p className="text-red-300 text-sm">{result.error}</p>
            </div>
          ) : (
            <>
              {/* AI Response */}
              <div>
                <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
                  <MessageSquare className="w-4 h-4" />
                  <span>AI 回复</span>
                </div>
                <div className="bg-slate-700/30 rounded-lg p-4 text-slate-200 text-sm leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto">
                  {result.response_text || '无内容'}
                </div>
              </div>

              {/* Citations */}
              {result.citations.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
                    <LinkIcon className="w-4 h-4" />
                    <span>引用来源 ({result.citations.length})</span>
                  </div>
                  <div className="space-y-2">
                    {result.citations.map((citation, idx) => (
                      <a
                        key={idx}
                        href={citation.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-3 p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors group"
                      >
                        <span className="flex-shrink-0 w-6 h-6 rounded bg-slate-600 flex items-center justify-center text-xs text-slate-300">
                          {idx + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="text-white text-sm truncate group-hover:text-primary-300 transition-colors">
                            {citation.title || citation.url}
                          </div>
                          <div className="text-xs text-slate-500 truncate">
                            {citation.domain || citation.url}
                          </div>
                        </div>
                        <ExternalLink className="w-4 h-4 text-slate-500 group-hover:text-primary-400 transition-colors flex-shrink-0" />
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
