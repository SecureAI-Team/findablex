'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  X,
  Loader2,
  Bot,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface QueryItem {
  id: string;
  query_text: string;
  query_type: string | null;
}

interface Engine {
  id: string;
  name: string;
  priority: string;
  method: string;
}

interface QuickCreateTaskDialogProps {
  projectId: string;
  projectName: string;
  queries: QueryItem[];
  onClose: () => void;
  onSuccess?: () => void;
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

export default function QuickCreateTaskDialog({
  projectId,
  projectName,
  queries,
  onClose,
  onSuccess,
}: QuickCreateTaskDialogProps) {
  const router = useRouter();
  const [step, setStep] = useState<'engine' | 'queries' | 'creating' | 'success'>('engine');
  const [engines, setEngines] = useState<Engine[]>([]);
  const [selectedEngine, setSelectedEngine] = useState<string | null>(null);
  const [selectedQueries, setSelectedQueries] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdTaskId, setCreatedTaskId] = useState<string | null>(null);

  useEffect(() => {
    // Fetch engines
    api.get('/crawler/engines').then((res) => {
      setEngines(res.data);
    });
    // Select all queries by default
    setSelectedQueries(new Set(queries.map((q) => q.id)));
  }, [queries]);

  const handleSelectAll = () => {
    if (selectedQueries.size === queries.length) {
      setSelectedQueries(new Set());
    } else {
      setSelectedQueries(new Set(queries.map((q) => q.id)));
    }
  };

  const toggleQuery = (queryId: string) => {
    const newSet = new Set(selectedQueries);
    if (newSet.has(queryId)) {
      newSet.delete(queryId);
    } else {
      newSet.add(queryId);
    }
    setSelectedQueries(newSet);
  };

  const handleCreate = async () => {
    if (!selectedEngine || selectedQueries.size === 0) return;

    setStep('creating');
    setError(null);

    try {
      const response = await api.post('/crawler/tasks', {
        project_id: projectId,
        engine: selectedEngine,
        query_ids: Array.from(selectedQueries),
        queries: [],
        region: 'cn',
        language: 'zh-CN',
        device_type: 'desktop',
        use_proxy: true,
      });

      setCreatedTaskId(response.data.id);
      setStep('success');
      onSuccess?.();
    } catch (err: any) {
      setError(err.response?.data?.detail || '创建任务失败');
      setStep('queries');
    }
  };

  const goToTask = () => {
    if (createdTaskId) {
      router.push(`/research/${createdTaskId}`);
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Dialog */}
      <div className="relative bg-slate-800 rounded-xl border border-slate-700 shadow-2xl w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Bot className="w-5 h-5 text-primary-400" />
              创建研究任务
            </h2>
            <p className="text-sm text-slate-400 mt-1">项目: {projectName}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {step === 'engine' && (
            <div className="space-y-4">
              <h3 className="text-white font-medium">选择 AI 引擎</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {engines.map((engine) => (
                  <button
                    key={engine.id}
                    onClick={() => setSelectedEngine(engine.id)}
                    className={cn(
                      'p-4 rounded-lg border text-center transition-all',
                      selectedEngine === engine.id
                        ? 'bg-primary-500/20 border-primary-500 ring-1 ring-primary-500'
                        : 'bg-slate-700/30 border-slate-600 hover:border-slate-500'
                    )}
                  >
                    <div className="text-2xl mb-2">{engineIcons[engine.id] || '🤖'}</div>
                    <div className="text-sm font-medium text-white">{engine.name}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 'queries' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-white font-medium">
                  选择查询词 ({selectedQueries.size}/{queries.length})
                </h3>
                <button
                  onClick={handleSelectAll}
                  className="text-sm text-primary-400 hover:text-primary-300"
                >
                  {selectedQueries.size === queries.length ? '取消全选' : '全选'}
                </button>
              </div>

              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-2 text-red-400 text-sm">
                  <AlertCircle className="w-4 h-4" />
                  {error}
                </div>
              )}

              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {queries.map((query) => (
                  <label
                    key={query.id}
                    className={cn(
                      'flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors',
                      selectedQueries.has(query.id)
                        ? 'bg-primary-500/10 border border-primary-500/30'
                        : 'bg-slate-700/30 border border-transparent hover:bg-slate-700/50'
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={selectedQueries.has(query.id)}
                      onChange={() => toggleQuery(query.id)}
                      className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-primary-500 focus:ring-primary-500"
                    />
                    <span className="text-white flex-1 truncate">{query.query_text}</span>
                    {query.query_type && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-slate-700 text-slate-300">
                        {query.query_type}
                      </span>
                    )}
                  </label>
                ))}
              </div>

              {queries.length === 0 && (
                <div className="text-center py-8 text-slate-400">
                  该项目没有查询词，请先添加查询词
                </div>
              )}
            </div>
          )}

          {step === 'creating' && (
            <div className="text-center py-12">
              <Loader2 className="w-12 h-12 text-primary-400 animate-spin mx-auto mb-4" />
              <p className="text-white font-medium">正在创建任务...</p>
              <p className="text-sm text-slate-400 mt-2">
                使用 {engines.find((e) => e.id === selectedEngine)?.name || selectedEngine} 引擎
              </p>
            </div>
          )}

          {step === 'success' && (
            <div className="text-center py-12">
              <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto mb-4" />
              <p className="text-white font-medium">任务创建成功！</p>
              <p className="text-sm text-slate-400 mt-2">
                {selectedQueries.size} 个查询词已提交到 {engines.find((e) => e.id === selectedEngine)?.name}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-slate-700">
          {step === 'engine' && (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
              >
                取消
              </button>
              <button
                onClick={() => setStep('queries')}
                disabled={!selectedEngine}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                下一步
                <ChevronRight className="w-4 h-4" />
              </button>
            </>
          )}

          {step === 'queries' && (
            <>
              <button
                onClick={() => setStep('engine')}
                className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
              >
                上一步
              </button>
              <button
                onClick={handleCreate}
                disabled={selectedQueries.size === 0}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                <Bot className="w-4 h-4" />
                创建任务 ({selectedQueries.size})
              </button>
            </>
          )}

          {step === 'success' && (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
              >
                关闭
              </button>
              <button
                onClick={goToTask}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg font-medium transition-colors"
              >
                查看任务
                <ChevronRight className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
