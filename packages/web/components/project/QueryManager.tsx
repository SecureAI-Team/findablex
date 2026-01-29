'use client';

import { useState } from 'react';
import {
  Plus,
  Trash2,
  Edit2,
  Check,
  X,
  Search,
  Upload,
  Loader2,
  AlertCircle,
  Copy,
  CheckCircle,
  Download,
  ChevronDown,
} from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface QueryItem {
  id: string;
  query_text: string;
  query_type: string | null;
  position: number | null;
  stage?: string | null;
  risk_level?: string | null;
  target_role?: string | null;
}

interface QueryManagerProps {
  projectId: string;
  queries: QueryItem[];
  onQueriesChange: (queries: QueryItem[]) => void;
}

type CopyFormat = 'text' | 'numbered' | 'markdown' | 'json';

export default function QueryManager({ projectId, queries, onQueriesChange }: QueryManagerProps) {
  const [newQueryText, setNewQueryText] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showCopyMenu, setShowCopyMenu] = useState(false);
  const [selectedQueries, setSelectedQueries] = useState<Set<string>>(new Set());
  const [selectMode, setSelectMode] = useState(false);

  // 复制功能
  const copyQueries = async (format: CopyFormat, onlySelected: boolean = false) => {
    const queriesToCopy = onlySelected && selectedQueries.size > 0
      ? queries.filter(q => selectedQueries.has(q.id))
      : queries;

    let text = '';
    
    switch (format) {
      case 'text':
        text = queriesToCopy.map(q => q.query_text).join('\n');
        break;
      case 'numbered':
        text = queriesToCopy.map((q, i) => `${i + 1}. ${q.query_text}`).join('\n');
        break;
      case 'markdown':
        text = queriesToCopy.map(q => `- ${q.query_text}`).join('\n');
        break;
      case 'json':
        text = JSON.stringify(
          queriesToCopy.map(q => ({
            query_text: q.query_text,
            query_type: q.query_type,
            stage: q.stage,
            risk_level: q.risk_level,
            target_role: q.target_role,
          })),
          null,
          2
        );
        break;
    }

    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setShowCopyMenu(false);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const toggleSelectAll = () => {
    if (selectedQueries.size === queries.length) {
      setSelectedQueries(new Set());
    } else {
      setSelectedQueries(new Set(queries.map(q => q.id)));
    }
  };

  const toggleQuerySelection = (id: string) => {
    const newSelected = new Set(selectedQueries);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedQueries(newSelected);
  };

  const handleAddQuery = async () => {
    if (!newQueryText.trim()) return;

    setLoading('add');
    setError(null);

    try {
      const response = await api.post(`/projects/${projectId}/queries`, {
        query_text: newQueryText.trim(),
        query_type: 'informational',
      });
      onQueriesChange([...queries, response.data]);
      setNewQueryText('');
      setShowAddForm(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || '添加失败');
    } finally {
      setLoading(null);
    }
  };

  const handleUpdateQuery = async (queryId: string) => {
    if (!editText.trim()) return;

    setLoading(queryId);
    setError(null);

    try {
      const response = await api.put(`/projects/${projectId}/queries/${queryId}`, {
        query_text: editText.trim(),
      });
      onQueriesChange(
        queries.map((q) => (q.id === queryId ? response.data : q))
      );
      setEditingId(null);
      setEditText('');
    } catch (err: any) {
      setError(err.response?.data?.detail || '更新失败');
    } finally {
      setLoading(null);
    }
  };

  const handleDeleteQuery = async (queryId: string) => {
    if (!confirm('确定要删除这个查询词吗？')) return;

    setLoading(queryId);
    setError(null);

    try {
      await api.delete(`/projects/${projectId}/queries/${queryId}`);
      onQueriesChange(queries.filter((q) => q.id !== queryId));
    } catch (err: any) {
      setError(err.response?.data?.detail || '删除失败');
    } finally {
      setLoading(null);
    }
  };

  const startEditing = (query: QueryItem) => {
    setEditingId(query.id);
    setEditText(query.query_text);
  };

  // 复制前10条
  const copyFirst10 = async (format: CopyFormat = 'text') => {
    const first10 = queries.slice(0, 10);
    let text = '';
    
    switch (format) {
      case 'text':
        text = first10.map(q => q.query_text).join('\n');
        break;
      case 'numbered':
        text = first10.map((q, i) => `${i + 1}. ${q.query_text}`).join('\n');
        break;
      case 'markdown':
        text = first10.map(q => `- ${q.query_text}`).join('\n');
        break;
    }

    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setShowCopyMenu(false);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // 导出功能
  const exportQueries = (format: 'csv' | 'json') => {
    let content = '';
    let filename = '';
    let mimeType = '';

    if (format === 'csv') {
      const headers = ['query_text', 'query_type', 'stage', 'risk_level', 'target_role'];
      const rows = queries.map(q => [
        `"${q.query_text.replace(/"/g, '""')}"`,
        q.query_type || '',
        q.stage || '',
        q.risk_level || '',
        q.target_role || '',
      ].join(','));
      content = [headers.join(','), ...rows].join('\n');
      filename = `queries_${projectId}.csv`;
      mimeType = 'text/csv';
    } else {
      content = JSON.stringify(
        queries.map(q => ({
          query_text: q.query_text,
          query_type: q.query_type,
          stage: q.stage,
          risk_level: q.risk_level,
          target_role: q.target_role,
        })),
        null,
        2
      );
      filename = `queries_${projectId}.json`;
      mimeType = 'application/json';
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditText('');
  };

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50">
      {/* Header */}
      <div className="p-6 border-b border-slate-700/50">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-white">
            查询词列表 ({queries.length})
          </h2>
          <div className="flex items-center gap-2">
            {/* Copy Button with Dropdown */}
            {queries.length > 0 && (
              <div className="relative">
                <button
                  onClick={() => setShowCopyMenu(!showCopyMenu)}
                  className={cn(
                    "inline-flex items-center gap-2 text-sm px-3 py-1.5 rounded-lg transition-colors",
                    copied 
                      ? "bg-green-500/20 text-green-400" 
                      : "bg-slate-700 hover:bg-slate-600 text-white"
                  )}
                >
                  {copied ? (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      已复制!
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      复制
                      <ChevronDown className="w-3 h-3" />
                    </>
                  )}
                </button>
                {showCopyMenu && !copied && (
                  <>
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setShowCopyMenu(false)}
                    />
                    <div className="absolute right-0 top-full mt-1 w-56 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-20 py-1">
                      {/* 快捷操作 - 复制前10条 */}
                      {queries.length >= 10 && (
                        <>
                          <div className="px-3 py-2 text-xs text-amber-400 border-b border-slate-700 flex items-center gap-1">
                            <span>⚡</span> 快捷复制
                          </div>
                          <button
                            onClick={() => copyFirst10('numbered')}
                            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-amber-300 hover:bg-slate-700 transition-colors"
                          >
                            一键复制前 10 条 (编号)
                          </button>
                        </>
                      )}
                      
                      <div className="px-3 py-2 text-xs text-slate-500 border-b border-slate-700">
                        复制全部 ({queries.length} 条)
                      </div>
                      <button
                        onClick={() => copyQueries('text')}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                      >
                        纯文本 (每行一条)
                      </button>
                      <button
                        onClick={() => copyQueries('numbered')}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                      >
                        编号列表 (1. 2. 3.)
                      </button>
                      <button
                        onClick={() => copyQueries('markdown')}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                      >
                        Markdown (- 列表)
                      </button>
                      <button
                        onClick={() => copyQueries('json')}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                      >
                        JSON 格式
                      </button>
                      
                      {/* 导出下载 */}
                      <div className="px-3 py-2 text-xs text-slate-500 border-t border-slate-700 mt-1">
                        下载导出
                      </div>
                      <button
                        onClick={() => { exportQueries('csv'); setShowCopyMenu(false); }}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                      >
                        <Download className="w-4 h-4" />
                        导出为 CSV
                      </button>
                      <button
                        onClick={() => { exportQueries('json'); setShowCopyMenu(false); }}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                      >
                        <Download className="w-4 h-4" />
                        导出为 JSON
                      </button>
                      
                      {selectedQueries.size > 0 && (
                        <>
                          <div className="px-3 py-2 text-xs text-slate-500 border-t border-slate-700 mt-1">
                            复制选中 ({selectedQueries.size} 条)
                          </div>
                          <button
                            onClick={() => copyQueries('text', true)}
                            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-primary-400 hover:bg-slate-700 transition-colors"
                          >
                            复制选中为纯文本
                          </button>
                        </>
                      )}
                    </div>
                  </>
                )}
              </div>
            )}
            
            {/* Select Mode Toggle */}
            {queries.length > 0 && (
              <button
                onClick={() => {
                  setSelectMode(!selectMode);
                  if (selectMode) setSelectedQueries(new Set());
                }}
                className={cn(
                  "inline-flex items-center gap-2 text-sm px-3 py-1.5 rounded-lg transition-colors",
                  selectMode
                    ? "bg-primary-500/20 text-primary-400"
                    : "bg-slate-700 hover:bg-slate-600 text-white"
                )}
              >
                {selectMode ? '取消选择' : '多选'}
              </button>
            )}
            
            <button
              onClick={() => setShowAddForm(true)}
              className="inline-flex items-center gap-2 text-sm bg-primary-500 hover:bg-primary-600 text-white px-3 py-1.5 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              添加查询词
            </button>
            <Link
              href={`/projects/${projectId}/import`}
              className="inline-flex items-center gap-2 text-sm text-primary-400 hover:text-primary-300"
            >
              <Upload className="w-4 h-4" />
              批量导入
            </Link>
          </div>
        </div>
        
        {/* Select All Bar */}
        {selectMode && queries.length > 0 && (
          <div className="mt-4 flex items-center gap-4 p-3 bg-slate-700/30 rounded-lg">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedQueries.size === queries.length}
                onChange={toggleSelectAll}
                className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-primary-500 focus:ring-primary-500"
              />
              <span className="text-sm text-slate-300">
                全选 ({selectedQueries.size}/{queries.length})
              </span>
            </label>
            {selectedQueries.size > 0 && (
              <button
                onClick={() => copyQueries('text', true)}
                className="text-sm text-primary-400 hover:text-primary-300"
              >
                复制选中
              </button>
            )}
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="mx-6 mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-2 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4" />
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-400 hover:text-red-300"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Add Query Form */}
      {showAddForm && (
        <div className="p-4 border-b border-slate-700/50 bg-slate-700/20">
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={newQueryText}
              onChange={(e) => setNewQueryText(e.target.value)}
              placeholder="输入新的查询词..."
              className="flex-1 px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleAddQuery();
                if (e.key === 'Escape') {
                  setShowAddForm(false);
                  setNewQueryText('');
                }
              }}
              autoFocus
            />
            <button
              onClick={handleAddQuery}
              disabled={loading === 'add' || !newQueryText.trim()}
              className="inline-flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {loading === 'add' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Check className="w-4 h-4" />
              )}
              添加
            </button>
            <button
              onClick={() => {
                setShowAddForm(false);
                setNewQueryText('');
              }}
              className="p-2 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {/* Query List */}
      {queries.length === 0 ? (
        <div className="p-12 text-center">
          <Search className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">还没有查询词</h3>
          <p className="text-slate-400 mb-6">添加查询词开始研究</p>
          <button
            onClick={() => setShowAddForm(true)}
            className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg font-medium transition-all"
          >
            <Plus className="w-4 h-4" />
            添加第一个查询词
          </button>
        </div>
      ) : (
        <div className="divide-y divide-slate-700/50">
          {queries.map((query, index) => (
            <div
              key={query.id}
              className={cn(
                'p-4 flex items-center gap-4 transition-colors',
                loading === query.id ? 'opacity-50' : 'hover:bg-slate-700/20',
                selectMode && selectedQueries.has(query.id) && 'bg-primary-500/10'
              )}
            >
              {/* Selection Checkbox */}
              {selectMode && (
                <input
                  type="checkbox"
                  checked={selectedQueries.has(query.id)}
                  onChange={() => toggleQuerySelection(query.id)}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-primary-500 focus:ring-primary-500"
                />
              )}
              
              <span className="text-slate-500 text-sm w-8 text-right">{index + 1}</span>
              
              {editingId === query.id ? (
                // Edit Mode
                <div className="flex-1 flex items-center gap-3">
                  <input
                    type="text"
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="flex-1 px-3 py-1.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleUpdateQuery(query.id);
                      if (e.key === 'Escape') cancelEditing();
                    }}
                    autoFocus
                  />
                  <button
                    onClick={() => handleUpdateQuery(query.id)}
                    disabled={loading === query.id || !editText.trim()}
                    className="p-1.5 text-green-400 hover:text-green-300 transition-colors disabled:opacity-50"
                    title="保存"
                  >
                    {loading === query.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Check className="w-4 h-4" />
                    )}
                  </button>
                  <button
                    onClick={cancelEditing}
                    className="p-1.5 text-slate-400 hover:text-white transition-colors"
                    title="取消"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                // View Mode
                <>
                  <span className="text-white flex-1">{query.query_text}</span>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {query.stage && (
                      <span className="px-2 py-0.5 rounded text-xs bg-blue-500/20 text-blue-400">
                        {query.stage}
                      </span>
                    )}
                    {query.risk_level && (
                      <span className={cn(
                        "px-2 py-0.5 rounded text-xs",
                        query.risk_level === 'critical' ? 'bg-red-500/20 text-red-400' :
                        query.risk_level === 'high' ? 'bg-orange-500/20 text-orange-400' :
                        query.risk_level === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-green-500/20 text-green-400'
                      )}>
                        {query.risk_level}
                      </span>
                    )}
                    {query.query_type && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-slate-700 text-slate-300">
                        {query.query_type}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => startEditing(query)}
                      disabled={loading === query.id}
                      className="p-1.5 text-slate-400 hover:text-primary-400 transition-colors"
                      title="编辑"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteQuery(query.id)}
                      disabled={loading === query.id}
                      className="p-1.5 text-slate-400 hover:text-red-400 transition-colors"
                      title="删除"
                    >
                      {loading === query.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
