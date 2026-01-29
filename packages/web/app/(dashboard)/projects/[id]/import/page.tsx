'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Loader2,
  Upload,
  FileText,
  Code,
  ClipboardPaste,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  X,
  HelpCircle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { analytics } from '@/lib/analytics';

type ImportMethod = 'paste' | 'csv' | 'json';

interface ParsedItem {
  query_text: string;
  response_text: string;
  citations?: string[];
  engine?: string;
  matchStatus?: 'matched' | 'unmatched' | 'partial';
  matchedQueryId?: string;
}

interface ProjectQuery {
  id: string;
  query_text: string;
  query_type?: string;
}

// AI 引擎选项
const engineOptions = [
  { id: 'chatgpt', label: 'ChatGPT' },
  { id: 'perplexity', label: 'Perplexity' },
  { id: 'google_sge', label: 'Google SGE' },
  { id: 'bing_copilot', label: 'Bing Copilot' },
  { id: 'tongyi', label: '通义千问' },
  { id: 'kimi', label: 'Kimi' },
  { id: 'deepseek', label: 'DeepSeek' },
  { id: 'other', label: '其他' },
];

const tabs: { id: ImportMethod; label: string; icon: any }[] = [
  { id: 'paste', label: '粘贴文本', icon: ClipboardPaste },
  { id: 'csv', label: 'CSV 文件', icon: FileText },
  { id: 'json', label: 'JSON 数据', icon: Code },
];

const csvExample = `query,response
"如何选择理财产品","选择理财产品需要考虑风险承受能力、投资期限、收益预期等因素。建议参考专业机构的评测报告。"
"最好的在线学习平台","目前主流的在线学习平台包括Coursera、edX等，各有特色，建议根据学习目标选择。"`;

const jsonExample = `[
  {
    "query_text": "如何选择理财产品",
    "response_text": "选择理财产品需要考虑风险承受能力...",
    "citations": ["example.com", "finance.com"]
  }
]`;

const pasteExample = `Q: 如何选择理财产品
选择理财产品需要考虑风险承受能力、投资期限、收益预期等因素。

Q: 最好的在线学习平台
目前主流的在线学习平台包括Coursera、edX等。`;

export default function ImportDataPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<any>(null);
  const [projectQueries, setProjectQueries] = useState<ProjectQuery[]>([]);
  const [activeTab, setActiveTab] = useState<ImportMethod>('paste');
  const [inputData, setInputData] = useState('');
  const [parsedItems, setParsedItems] = useState<ParsedItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isParsing, setIsParsing] = useState(false);
  const [error, setError] = useState('');
  const [parseError, setParseError] = useState('');
  const [selectedEngine, setSelectedEngine] = useState('chatgpt');

  useEffect(() => {
    const fetchProject = async () => {
      try {
        const [projectRes, queriesRes] = await Promise.all([
          api.get(`/projects/${projectId}`),
          api.get(`/projects/${projectId}/queries`),
        ]);
        setProject(projectRes.data);
        setProjectQueries(queriesRes.data.items || queriesRes.data || []);
      } catch (error) {
        router.push('/projects');
      }
    };
    fetchProject();
  }, [projectId, router]);

  // Match imported queries to project queries
  const matchQueries = (items: ParsedItem[]): ParsedItem[] => {
    return items.map((item) => {
      const normalizedImport = item.query_text.toLowerCase().trim();
      
      // Try exact match first
      const exactMatch = projectQueries.find(
        (q) => q.query_text.toLowerCase().trim() === normalizedImport
      );
      if (exactMatch) {
        return { ...item, matchStatus: 'matched' as const, matchedQueryId: exactMatch.id };
      }
      
      // Try partial match (contains)
      const partialMatch = projectQueries.find(
        (q) => 
          q.query_text.toLowerCase().includes(normalizedImport) ||
          normalizedImport.includes(q.query_text.toLowerCase())
      );
      if (partialMatch) {
        return { ...item, matchStatus: 'partial' as const, matchedQueryId: partialMatch.id };
      }
      
      return { ...item, matchStatus: 'unmatched' as const };
    });
  };

  const handleParse = () => {
    setIsParsing(true);
    setParseError('');
    setParsedItems([]);

    try {
      let items: ParsedItem[] = [];

      if (activeTab === 'json') {
        const parsed = JSON.parse(inputData);
        items = Array.isArray(parsed) ? parsed : [parsed];
      } else if (activeTab === 'csv') {
        items = parseCSV(inputData);
      } else {
        items = parsePaste(inputData);
      }

      if (items.length === 0) {
        setParseError('未能解析出有效数据');
      } else {
        // Match imported queries to project queries
        const matchedItems = projectQueries.length > 0 ? matchQueries(items) : items;
        setParsedItems(matchedItems);
      }
    } catch (err: any) {
      setParseError(err.message || '解析失败，请检查数据格式');
    } finally {
      setIsParsing(false);
    }
  };

  const parseCSV = (data: string): ParsedItem[] => {
    const lines = data.trim().split('\n');
    if (lines.length < 2) return [];

    const headers = lines[0].split(',').map((h) => h.trim().toLowerCase().replace(/"/g, ''));
    const queryIndex = headers.findIndex((h) => h === 'query' || h === 'question');
    const responseIndex = headers.findIndex((h) => h === 'response' || h === 'answer');

    if (queryIndex === -1 || responseIndex === -1) {
      throw new Error('CSV 必须包含 query/question 和 response/answer 列');
    }

    const items: ParsedItem[] = [];
    for (let i = 1; i < lines.length; i++) {
      const values = parseCSVLine(lines[i]);
      if (values.length > Math.max(queryIndex, responseIndex)) {
        items.push({
          query_text: values[queryIndex],
          response_text: values[responseIndex],
        });
      }
    }
    return items;
  };

  const parseCSVLine = (line: string): string[] => {
    const values: string[] = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        values.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
    values.push(current.trim());
    return values;
  };

  const parsePaste = (data: string): ParsedItem[] => {
    const blocks = data.trim().split(/\n\n+/);
    const items: ParsedItem[] = [];
    let currentQuery = '';
    let currentResponse: string[] = [];

    for (const block of blocks) {
      const lines = block.trim().split('\n');
      const firstLine = lines[0].trim();

      if (firstLine.match(/^(Q:|Query:|问:|查询:)/i)) {
        if (currentQuery && currentResponse.length > 0) {
          items.push({
            query_text: currentQuery,
            response_text: currentResponse.join('\n'),
          });
        }
        currentQuery = firstLine.replace(/^(Q:|Query:|问:|查询:)\s*/i, '');
        currentResponse = lines.slice(1);
      } else if (currentQuery) {
        currentResponse.push(...lines);
      }
    }

    if (currentQuery && currentResponse.length > 0) {
      items.push({
        query_text: currentQuery,
        response_text: currentResponse.join('\n'),
      });
    }

    return items;
  };

  const handleSubmit = async () => {
    if (parsedItems.length === 0) return;

    setIsLoading(true);
    setError('');

    try {
      // 为每个解析的条目添加引擎信息
      const dataWithEngine = parsedItems.map(item => ({
        ...item,
        engine: selectedEngine,
      }));
      
      const res = await api.post('/runs/import', {
        project_id: projectId,
        input_format: 'json',  // 统一使用 JSON 格式，便于携带 engine 信息
        input_data: JSON.stringify(dataWithEngine),
      });

      // Track import
      analytics.trackFirstAnswerImported(projectId, dataWithEngine.length, selectedEngine);

      router.push(`/projects/${projectId}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || '导入失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveItem = (index: number) => {
    setParsedItems(parsedItems.filter((_, i) => i !== index));
  };

  const getExample = () => {
    switch (activeTab) {
      case 'csv':
        return csvExample;
      case 'json':
        return jsonExample;
      default:
        return pasteExample;
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Link
          href={`/projects/${projectId}`}
          className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          返回项目
        </Link>
        <h1 className="font-display text-2xl font-bold text-white">导入数据</h1>
        <p className="mt-1 text-slate-400">
          {project?.name} - 导入 AI 搜索结果进行分析
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              setActiveTab(tab.id);
              setParsedItems([]);
              setParseError('');
            }}
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium text-sm transition-all',
              activeTab === tab.id
                ? 'bg-primary-500 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Engine Selector */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 mb-6">
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-slate-300 whitespace-nowrap">
            数据来源引擎:
          </label>
          <select
            value={selectedEngine}
            onChange={(e) => setSelectedEngine(e.target.value)}
            className="flex-1 max-w-xs px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            {engineOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>
          <span className="text-xs text-slate-500">
            选择获取这些答案的 AI 引擎
          </span>
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-medium text-white">输入数据</h2>
          <button
            onClick={() => setInputData(getExample())}
            className="text-sm text-primary-400 hover:text-primary-300 transition-colors"
          >
            使用示例数据
          </button>
        </div>

        <textarea
          value={inputData}
          onChange={(e) => {
            setInputData(e.target.value);
            setParsedItems([]);
          }}
          placeholder={
            activeTab === 'csv'
              ? '粘贴 CSV 数据，第一行为标题行（query, response）'
              : activeTab === 'json'
              ? '粘贴 JSON 数组，每个对象包含 query_text 和 response_text'
              : '粘贴问答对，使用 Q: 或 问: 标记问题'
          }
          className="w-full h-64 px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm resize-none"
        />

        {parseError && (
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <AlertCircle className="w-4 h-4" />
            {parseError}
          </div>
        )}

        <button
          onClick={handleParse}
          disabled={!inputData.trim() || isParsing}
          className="bg-slate-700 hover:bg-slate-600 disabled:bg-slate-700/50 disabled:text-slate-500 text-white px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2"
        >
          {isParsing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              解析中...
            </>
          ) : (
            '预览解析结果'
          )}
        </button>
      </div>

      {/* Preview */}
      {parsedItems.length > 0 && (
        <div className="mt-6 bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 space-y-4">
          {/* Summary */}
          <div className="flex items-center justify-between">
            <h2 className="font-medium text-white flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-400" />
              解析成功 - {parsedItems.length} 条数据
            </h2>
          </div>

          {/* Match status summary */}
          {projectQueries.length > 0 && (
            <div className="flex flex-wrap gap-3 p-3 bg-slate-700/30 rounded-lg">
              <div className="flex items-center gap-2 text-sm">
                <CheckCircle className="w-4 h-4 text-green-400" />
                <span className="text-slate-300">
                  已匹配: {parsedItems.filter(i => i.matchStatus === 'matched').length}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <span className="text-slate-300">
                  部分匹配: {parsedItems.filter(i => i.matchStatus === 'partial').length}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <HelpCircle className="w-4 h-4 text-slate-400" />
                <span className="text-slate-300">
                  未知查询: {parsedItems.filter(i => i.matchStatus === 'unmatched').length}
                </span>
              </div>
              {/* Missing queries warning */}
              {(() => {
                const importedQueryTexts = new Set(parsedItems.map(i => i.query_text.toLowerCase().trim()));
                const missingQueries = projectQueries.filter(
                  q => !importedQueryTexts.has(q.query_text.toLowerCase().trim())
                );
                if (missingQueries.length > 0) {
                  return (
                    <div className="flex items-center gap-2 text-sm">
                      <AlertCircle className="w-4 h-4 text-red-400" />
                      <span className="text-red-300">
                        缺失答案: {missingQueries.length} 条项目查询未导入
                      </span>
                    </div>
                  );
                }
                return null;
              })()}
            </div>
          )}

          <div className="space-y-3 max-h-96 overflow-y-auto">
            {parsedItems.map((item, index) => (
              <div
                key={index}
                className={cn(
                  'rounded-lg p-4 relative group',
                  item.matchStatus === 'matched' ? 'bg-green-900/20 border border-green-700/30' :
                  item.matchStatus === 'partial' ? 'bg-amber-900/20 border border-amber-700/30' :
                  item.matchStatus === 'unmatched' ? 'bg-slate-700/30 border border-slate-600/30' :
                  'bg-slate-700/30'
                )}
              >
                <button
                  onClick={() => handleRemoveItem(index)}
                  className="absolute top-2 right-2 p-1 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                >
                  <X className="w-4 h-4" />
                </button>
                
                {/* Match status badge */}
                {item.matchStatus && (
                  <div className="absolute top-2 right-10 flex items-center gap-1">
                    {item.matchStatus === 'matched' && (
                      <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" />
                        已匹配
                      </span>
                    )}
                    {item.matchStatus === 'partial' && (
                      <span className="text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" />
                        部分匹配
                      </span>
                    )}
                    {item.matchStatus === 'unmatched' && (
                      <span className="text-xs bg-slate-500/20 text-slate-400 px-2 py-0.5 rounded flex items-center gap-1">
                        <HelpCircle className="w-3 h-3" />
                        未知查询
                      </span>
                    )}
                  </div>
                )}
                
                <div className="mb-2">
                  <span className="text-xs text-primary-400 font-medium">查询</span>
                  <p className="text-white text-sm mt-1">{item.query_text}</p>
                </div>
                <div>
                  <span className="text-xs text-slate-400 font-medium">响应</span>
                  <p className="text-slate-300 text-sm mt-1 line-clamp-3">
                    {item.response_text}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-4 pt-4 border-t border-slate-700/50">
            <button
              onClick={() => {
                setParsedItems([]);
                setInputData('');
              }}
              className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
            >
              重新输入
            </button>
            <button
              onClick={handleSubmit}
              disabled={isLoading}
              className="bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/50 text-white px-6 py-2.5 rounded-lg font-medium transition-all flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  提交中...
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5" />
                  开始分析
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Help */}
      <div className="mt-6 p-4 bg-slate-800/30 rounded-lg border border-slate-700/50">
        <h3 className="text-sm font-medium text-white mb-2">数据格式说明</h3>
        <div className="text-sm text-slate-400 space-y-1">
          {activeTab === 'paste' && (
            <>
              <p>• 每个问答对使用空行分隔</p>
              <p>• 问题行以 &quot;Q:&quot; 或 &quot;问:&quot; 开头</p>
              <p>• 问题后面的所有行都被视为响应内容</p>
            </>
          )}
          {activeTab === 'csv' && (
            <>
              <p>• 第一行必须是标题行</p>
              <p>• 必须包含 query/question 和 response/answer 列</p>
              <p>• 如果内容包含逗号，请用双引号包裹</p>
            </>
          )}
          {activeTab === 'json' && (
            <>
              <p>• 数据格式为 JSON 数组</p>
              <p>• 每个对象必须包含 query_text 和 response_text 字段</p>
              <p>• 可选字段：citations（引用列表）</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
