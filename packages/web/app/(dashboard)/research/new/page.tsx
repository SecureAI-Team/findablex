'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Bot,
  Send,
  Plus,
  Trash2,
  AlertCircle,
  Loader2,
  CheckCircle2,
  Info,
} from 'lucide-react';
import { api } from '@/lib/api';
import { clsx } from 'clsx';

interface Engine {
  id: string;
  name: string;
  priority: string;
  method: string;
}

interface Project {
  id: string;
  name: string;
}

interface Quota {
  daily_limit: number;
  used_today: number;
  remaining: number;
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

const engineDescriptions: Record<string, string> = {
  deepseek: '深度求索，支持联网搜索和深度思考',
  kimi: '月之暗面，擅长长文本理解和生成',
  doubao: '字节跳动豆包，通用对话能力强',
  chatglm: '智谱清言，中文理解能力出色',
  chatgpt: 'OpenAI GPT，全球领先的对话模型',
  qwen: '阿里通义千问，支持多模态理解',
  perplexity: '专注搜索增强的 AI 助手',
  google_sge: 'Google 搜索生成体验',
  bing_copilot: '微软 Bing AI 助手',
};

export default function NewCrawlTaskPage() {
  const router = useRouter();
  const [engines, setEngines] = useState<Engine[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [quota, setQuota] = useState<Quota | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form state
  const [selectedEngine, setSelectedEngine] = useState<string>('');
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [queries, setQueries] = useState<string[]>(['']);
  const [bulkInput, setBulkInput] = useState('');
  const [inputMode, setInputMode] = useState<'single' | 'bulk'>('single');
  const [region, setRegion] = useState('cn');
  const [language, setLanguage] = useState('zh-CN');
  const [enableWebSearch, setEnableWebSearch] = useState(true);
  
  // Engines that support web search mode
  const webSearchEngines = ['deepseek', 'kimi', 'qwen'];

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [enginesRes, projectsRes, quotaRes] = await Promise.all([
        api.get('/crawler/engines'),
        api.get('/projects'),
        api.get('/crawler/quota'),
      ]);
      setEngines(enginesRes.data);
      setProjects(projectsRes.data.items || projectsRes.data);
      setQuota(quotaRes.data);
      setError(null);
    } catch (err: any) {
      setError('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAddQuery = () => {
    setQueries([...queries, '']);
  };

  const handleRemoveQuery = (index: number) => {
    if (queries.length > 1) {
      setQueries(queries.filter((_, i) => i !== index));
    }
  };

  const handleQueryChange = (index: number, value: string) => {
    const newQueries = [...queries];
    newQueries[index] = value;
    setQueries(newQueries);
  };

  const handleBulkInputChange = (value: string) => {
    setBulkInput(value);
    // Parse bulk input (one query per line)
    const lines = value.split('\n').filter((line) => line.trim());
    if (lines.length > 0) {
      setQueries(lines);
    }
  };

  const getValidQueries = () => {
    return queries.filter((q) => q.trim().length > 0);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const validQueries = getValidQueries();
    
    if (!selectedEngine) {
      setError('请选择 AI 引擎');
      return;
    }
    if (!selectedProject) {
      setError('请选择项目');
      return;
    }
    if (validQueries.length === 0) {
      setError('请输入至少一个查询');
      return;
    }
    if (quota && validQueries.length > quota.remaining) {
      setError(`查询数量超过剩余配额 (${quota.remaining})`);
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      // Note: In a real implementation, we'd need to create QueryItems first
      // For now, we'll send the queries directly and let the backend handle it
      await api.post('/crawler/tasks', {
        project_id: selectedProject,
        engine: selectedEngine,
        query_ids: [], // Will be created by backend
        queries: validQueries, // Send raw queries
        region,
        language,
        device_type: 'desktop',
        use_proxy: true,
        enable_web_search: webSearchEngines.includes(selectedEngine) ? enableWebSearch : false,
      });

      setSuccess(true);
      setTimeout(() => {
        router.push('/research');
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || '创建任务失败');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4">
        <CheckCircle2 className="w-16 h-16 text-green-400" />
        <h2 className="text-xl font-semibold text-white">任务创建成功！</h2>
        <p className="text-slate-400">正在跳转到任务列表...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/research"
          className="p-2 rounded-lg hover:bg-slate-700/50 transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-slate-400" />
        </Link>
        <div>
          <h1 className="font-display text-2xl font-bold text-white">新建爬虫任务</h1>
          <p className="mt-1 text-slate-400">选择 AI 引擎和查询内容，获取品牌可见性数据</p>
        </div>
      </div>

      {/* Quota Info */}
      {quota && (
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-primary-400" />
              <span className="text-sm text-slate-300">今日配额</span>
            </div>
            <div className="text-sm">
              <span className="text-white font-medium">{quota.remaining}</span>
              <span className="text-slate-400"> / {quota.daily_limit} 次查询</span>
            </div>
          </div>
          <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-500 rounded-full"
              style={{ width: `${(quota.remaining / quota.daily_limit) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Error Message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* Step 1: Select Project */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
          <h2 className="font-display text-lg font-semibold text-white mb-4">
            1. 选择项目
          </h2>
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">选择项目...</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
          {projects.length === 0 && (
            <p className="mt-2 text-sm text-slate-400">
              还没有项目？
              <Link href="/projects/new" className="text-primary-400 hover:text-primary-300 ml-1">
                创建一个
              </Link>
            </p>
          )}
        </div>

        {/* Step 2: Select Engine */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
          <h2 className="font-display text-lg font-semibold text-white mb-4">
            2. 选择 AI 引擎
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {engines.map((engine) => (
              <button
                key={engine.id}
                type="button"
                onClick={() => setSelectedEngine(engine.id)}
                className={clsx(
                  'relative p-4 rounded-xl border-2 transition-all text-left',
                  selectedEngine === engine.id
                    ? 'border-primary-500 bg-primary-500/10'
                    : 'border-slate-700 hover:border-slate-600 bg-slate-700/30'
                )}
              >
                {selectedEngine === engine.id && (
                  <div className="absolute top-2 right-2">
                    <CheckCircle2 className="w-4 h-4 text-primary-400" />
                  </div>
                )}
                <div className="text-2xl mb-2">{engineIcons[engine.id] || '🤖'}</div>
                <div className="font-medium text-white text-sm">{engine.name}</div>
                <div className="text-xs text-slate-400 mt-1 line-clamp-2">
                  {engineDescriptions[engine.id] || engine.method}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Step 3: Input Queries */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display text-lg font-semibold text-white">
              3. 输入查询内容
            </h2>
            <div className="flex bg-slate-700/50 rounded-lg p-1">
              <button
                type="button"
                onClick={() => setInputMode('single')}
                className={clsx(
                  'px-3 py-1 text-sm rounded-md transition-colors',
                  inputMode === 'single'
                    ? 'bg-primary-500 text-white'
                    : 'text-slate-400 hover:text-white'
                )}
              >
                逐条输入
              </button>
              <button
                type="button"
                onClick={() => setInputMode('bulk')}
                className={clsx(
                  'px-3 py-1 text-sm rounded-md transition-colors',
                  inputMode === 'bulk'
                    ? 'bg-primary-500 text-white'
                    : 'text-slate-400 hover:text-white'
                )}
              >
                批量输入
              </button>
            </div>
          </div>

          {inputMode === 'single' ? (
            <div className="space-y-3">
              {queries.map((query, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => handleQueryChange(index, e.target.value)}
                    placeholder={`查询 ${index + 1}: 例如 "最好的智能手机推荐"`}
                    className="flex-1 bg-slate-700/50 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  {queries.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveQuery(index)}
                      className="p-3 text-slate-400 hover:text-red-400 transition-colors"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={handleAddQuery}
                className="flex items-center gap-2 text-primary-400 hover:text-primary-300 text-sm"
              >
                <Plus className="w-4 h-4" />
                添加更多查询
              </button>
            </div>
          ) : (
            <div>
              <textarea
                value={bulkInput}
                onChange={(e) => handleBulkInputChange(e.target.value)}
                placeholder="每行一个查询，例如：&#10;最好的智能手机推荐&#10;2024年笔记本电脑排行&#10;如何选择蓝牙耳机"
                rows={8}
                className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none font-mono text-sm"
              />
              <p className="mt-2 text-sm text-slate-400">
                已识别 <span className="text-white font-medium">{getValidQueries().length}</span> 个查询
              </p>
            </div>
          )}
        </div>

        {/* Step 4: Advanced Options */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
          <h2 className="font-display text-lg font-semibold text-white mb-4">
            4. 高级选项
          </h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-2">地区</label>
              <select
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="cn">中国大陆</option>
                <option value="hk">香港</option>
                <option value="tw">台湾</option>
                <option value="us">美国</option>
                <option value="jp">日本</option>
                <option value="kr">韩国</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-2">语言</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="zh-CN">简体中文</option>
                <option value="zh-TW">繁体中文</option>
                <option value="en-US">English (US)</option>
                <option value="ja-JP">日本語</option>
                <option value="ko-KR">한국어</option>
              </select>
            </div>
          </div>
          
          {/* Web Search Option - only show for supported engines */}
          {webSearchEngines.includes(selectedEngine) && (
            <div className="mt-4 pt-4 border-t border-slate-700/50">
              <label className="flex items-center gap-3 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={enableWebSearch}
                  onChange={(e) => setEnableWebSearch(e.target.checked)}
                  className="w-5 h-5 rounded border-slate-600 bg-slate-700/50 text-primary-500 focus:ring-primary-500 focus:ring-offset-0 focus:ring-2"
                />
                <div>
                  <span className="text-white group-hover:text-primary-300 transition-colors">
                    启用联网搜索
                  </span>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {selectedEngine === 'deepseek' && '开启后 DeepSeek 会实时搜索网页以提供最新信息和引用来源'}
                    {selectedEngine === 'kimi' && '开启后 Kimi 会搜索网络获取实时信息'}
                    {selectedEngine === 'qwen' && '开启后通义千问会进行联网搜索'}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    💡 提示: 联网搜索响应时间较长，请耐心等待
                  </p>
                </div>
              </label>
            </div>
          )}
        </div>

        {/* Submit */}
        <div className="flex items-center justify-between">
          <div className="text-sm text-slate-400">
            将爬取 <span className="text-white font-medium">{getValidQueries().length}</span> 个查询
            {selectedEngine && (
              <>
                ，使用 <span className="text-white font-medium">{engines.find(e => e.id === selectedEngine)?.name}</span>
              </>
            )}
          </div>
          <div className="flex gap-3">
            <Link
              href="/research"
              className="px-6 py-2.5 text-slate-400 hover:text-white transition-colors"
            >
              取消
            </Link>
            <button
              type="submit"
              disabled={submitting || !selectedEngine || !selectedProject || getValidQueries().length === 0}
              className={clsx(
                'inline-flex items-center gap-2 px-6 py-2.5 rounded-lg font-medium transition-all',
                submitting || !selectedEngine || !selectedProject || getValidQueries().length === 0
                  ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                  : 'bg-primary-500 hover:bg-primary-600 text-white hover:scale-105'
              )}
            >
              {submitting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  创建中...
                </>
              ) : (
                <>
                  <Send className="w-5 h-5" />
                  创建任务
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
