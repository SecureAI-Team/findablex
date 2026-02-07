'use client';

import { useEffect, useState } from 'react';
import {
  Code2,
  Key,
  Webhook,
  Copy,
  Plus,
  Trash2,
  Check,
  AlertCircle,
  ExternalLink,
  Play,
  Loader2,
  CheckCircle,
  XCircle,
  Eye,
  EyeOff,
  RefreshCw,
  BookOpen,
  Terminal,
  Braces,
  Globe,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

// ============ Types ============

interface WebhookItem {
  id: string;
  workspace_id: string;
  name: string;
  url: string;
  secret: string;
  events: string[];
  is_active: boolean;
  last_triggered_at: string | null;
  last_status_code: number | null;
  last_error: string | null;
  failure_count: number;
  created_at: string;
}

interface WebhookDelivery {
  id: string;
  event_type: string;
  status_code: number | null;
  error: string | null;
  duration_ms: number | null;
  success: boolean;
  created_at: string;
}

interface WebhookEventType {
  type: string;
  description: string;
  payload_fields: string[];
}

// ============ Constants ============

const API_ENDPOINTS = [
  {
    method: 'GET',
    path: '/api/v1/projects',
    description: '列出工作区中的所有项目',
    params: 'workspace_id (可选)',
  },
  {
    method: 'POST',
    path: '/api/v1/projects',
    description: '创建新项目',
    params: 'name, target_domains[], workspace_id',
  },
  {
    method: 'GET',
    path: '/api/v1/projects/{id}',
    description: '获取项目详情',
    params: '-',
  },
  {
    method: 'GET',
    path: '/api/v1/projects/{id}/citations-summary',
    description: '获取项目引用统计（可见性评分）',
    params: '-',
  },
  {
    method: 'GET',
    path: '/api/v1/projects/{id}/trends',
    description: '获取项目趋势数据（引擎对比、历史变化）',
    params: 'days (7-90)',
  },
  {
    method: 'POST',
    path: '/api/v1/projects/{id}/auto-checkup',
    description: '一键触发自动体检',
    params: 'max_engines (可选)',
  },
  {
    method: 'GET',
    path: '/api/v1/projects/{id}/crawl-tasks',
    description: '列出项目的研究任务',
    params: 'status_filter (可选)',
  },
  {
    method: 'GET',
    path: '/api/v1/projects/{id}/crawl-results',
    description: '获取研究结果（含引用分析）',
    params: 'engine (可选)',
  },
  {
    method: 'GET',
    path: '/api/v1/projects/{id}/drift-events',
    description: '获取变化检测事件',
    params: 'severity, acknowledged, limit',
  },
  {
    method: 'GET',
    path: '/api/v1/projects/{id}/activity',
    description: '获取项目活动记录',
    params: 'event_type, limit',
  },
  {
    method: 'GET',
    path: '/api/v1/runs',
    description: '列出体检运行记录',
    params: 'project_id',
  },
  {
    method: 'GET',
    path: '/api/v1/reports/{run_id}',
    description: '获取体检报告',
    params: '-',
  },
];

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-green-500/10 text-green-400',
  POST: 'bg-blue-500/10 text-blue-400',
  PUT: 'bg-amber-500/10 text-amber-400',
  DELETE: 'bg-red-500/10 text-red-400',
};

type TabId = 'docs' | 'webhooks';

export default function DeveloperPage() {
  const [activeTab, setActiveTab] = useState<TabId>('docs');
  const [webhooks, setWebhooks] = useState<WebhookItem[]>([]);
  const [eventTypes, setEventTypes] = useState<WebhookEventType[]>([]);
  const [isLoadingWebhooks, setIsLoadingWebhooks] = useState(false);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [copiedText, setCopiedText] = useState<string | null>(null);
  const [testingWebhookId, setTestingWebhookId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ id: string; success: boolean; status?: number; error?: string } | null>(null);
  const [showSecrets, setShowSecrets] = useState<Set<string>>(new Set());

  // New webhook form
  const [newName, setNewName] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const [newEvents, setNewEvents] = useState<string[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState('');

  useEffect(() => {
    // Get workspace ID
    const fetchWorkspace = async () => {
      try {
        const res = await api.get('/workspaces');
        if (res.data?.length > 0) {
          setWorkspaceId(res.data[0].id);
        }
      } catch (err) {
        console.error('Failed to fetch workspaces:', err);
      }
    };
    fetchWorkspace();

    // Fetch event types
    const fetchEventTypes = async () => {
      try {
        const res = await api.get('/webhook-events');
        setEventTypes(res.data.events || []);
      } catch (err) {
        console.error('Failed to fetch event types:', err);
      }
    };
    fetchEventTypes();
  }, []);

  useEffect(() => {
    if (workspaceId && activeTab === 'webhooks') {
      fetchWebhooks();
    }
  }, [workspaceId, activeTab]);

  const fetchWebhooks = async () => {
    if (!workspaceId) return;
    setIsLoadingWebhooks(true);
    try {
      const res = await api.get(`/workspaces/${workspaceId}/webhooks`);
      setWebhooks(res.data);
    } catch (err) {
      console.error('Failed to fetch webhooks:', err);
    } finally {
      setIsLoadingWebhooks(false);
    }
  };

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(label);
    setTimeout(() => setCopiedText(null), 2000);
  };

  const handleCreateWebhook = async () => {
    if (!workspaceId || !newName.trim() || !newUrl.trim() || newEvents.length === 0) {
      setCreateError('请填写所有必填字段');
      return;
    }

    setIsCreating(true);
    setCreateError('');
    try {
      const res = await api.post(`/workspaces/${workspaceId}/webhooks`, {
        name: newName.trim(),
        url: newUrl.trim(),
        events: newEvents,
      });
      setWebhooks((prev) => [res.data, ...prev]);
      setShowCreateDialog(false);
      setNewName('');
      setNewUrl('');
      setNewEvents([]);
    } catch (err: any) {
      setCreateError(err.response?.data?.detail || '创建失败');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteWebhook = async (webhookId: string) => {
    if (!workspaceId || !confirm('确定要删除这个 Webhook 吗？')) return;
    try {
      await api.delete(`/workspaces/${workspaceId}/webhooks/${webhookId}`);
      setWebhooks((prev) => prev.filter((w) => w.id !== webhookId));
    } catch (err) {
      console.error('Failed to delete webhook:', err);
    }
  };

  const handleToggleWebhook = async (webhookId: string, isActive: boolean) => {
    if (!workspaceId) return;
    try {
      const res = await api.put(`/workspaces/${workspaceId}/webhooks/${webhookId}`, {
        is_active: !isActive,
      });
      setWebhooks((prev) => prev.map((w) => (w.id === webhookId ? res.data : w)));
    } catch (err) {
      console.error('Failed to toggle webhook:', err);
    }
  };

  const handleTestWebhook = async (webhookId: string) => {
    if (!workspaceId) return;
    setTestingWebhookId(webhookId);
    setTestResult(null);
    try {
      const res = await api.post(`/workspaces/${workspaceId}/webhooks/${webhookId}/test`);
      setTestResult({
        id: webhookId,
        success: res.data.success,
        status: res.data.status_code,
        error: res.data.error,
      });
    } catch (err: any) {
      setTestResult({
        id: webhookId,
        success: false,
        error: err.response?.data?.detail || '测试失败',
      });
    } finally {
      setTestingWebhookId(null);
    }
  };

  const toggleEventSelection = (eventType: string) => {
    setNewEvents((prev) =>
      prev.includes(eventType)
        ? prev.filter((e) => e !== eventType)
        : [...prev, eventType]
    );
  };

  const toggleSecretVisibility = (webhookId: string) => {
    setShowSecrets((prev) => {
      const next = new Set(prev);
      if (next.has(webhookId)) next.delete(webhookId);
      else next.add(webhookId);
      return next;
    });
  };

  const tabs = [
    { id: 'docs' as const, label: 'API 文档', icon: BookOpen },
    { id: 'webhooks' as const, label: 'Webhooks', icon: Webhook },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold text-white flex items-center gap-3">
          <Code2 className="w-7 h-7 text-primary-400" />
          开发者平台
        </h1>
        <p className="text-slate-400 mt-1">
          通过 API 和 Webhooks 将 FindableX 集成到您的工作流中
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-700/50">
        <nav className="flex gap-1 -mb-px">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'inline-flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-400'
                    : 'border-transparent text-slate-400 hover:text-white hover:border-slate-600'
                )}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* API Docs Tab */}
      {activeTab === 'docs' && (
        <div className="space-y-6">
          {/* Authentication */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
            <h2 className="font-display text-lg font-semibold text-white flex items-center gap-2 mb-4">
              <Key className="w-5 h-5 text-primary-400" />
              认证方式
            </h2>
            <p className="text-sm text-slate-400 mb-4">
              所有 API 请求需要在 HTTP Header 中携带 Bearer Token 进行认证。
              Token 可通过 <code className="px-1.5 py-0.5 bg-slate-700/50 rounded text-primary-400 text-xs">/api/v1/auth/login</code> 接口获取。
            </p>
            <div className="bg-slate-900/50 rounded-lg p-4 font-mono text-sm">
              <div className="text-slate-500 mb-1"># 请求示例</div>
              <div className="text-green-400">
                curl -H &quot;Authorization: Bearer {'<your-token>'}&quot; \
              </div>
              <div className="text-green-400 ml-5">
                https://api.findablex.com/api/v1/projects
              </div>
            </div>
          </div>

          {/* Base URL */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
            <h2 className="font-display text-lg font-semibold text-white flex items-center gap-2 mb-4">
              <Globe className="w-5 h-5 text-primary-400" />
              Base URL
            </h2>
            <div className="flex items-center gap-3">
              <code className="flex-1 px-4 py-2.5 bg-slate-900/50 rounded-lg text-primary-400 font-mono text-sm">
                https://api.findablex.com/api/v1
              </code>
              <button
                onClick={() => handleCopy('https://api.findablex.com/api/v1', 'base-url')}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
              >
                {copiedText === 'base-url' ? (
                  <Check className="w-4 h-4 text-green-400" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>

          {/* Endpoints */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50">
            <div className="px-6 py-4 border-b border-slate-700/50">
              <h2 className="font-display text-lg font-semibold text-white flex items-center gap-2">
                <Terminal className="w-5 h-5 text-primary-400" />
                API 端点
              </h2>
            </div>
            <div className="divide-y divide-slate-700/30">
              {API_ENDPOINTS.map((endpoint, i) => (
                <div key={i} className="px-6 py-4 hover:bg-slate-700/10 transition-colors">
                  <div className="flex items-start gap-3">
                    <span
                      className={cn(
                        'px-2 py-0.5 rounded text-xs font-bold flex-shrink-0 mt-0.5',
                        METHOD_COLORS[endpoint.method] || 'bg-slate-500/10 text-slate-400'
                      )}
                    >
                      {endpoint.method}
                    </span>
                    <div className="flex-1 min-w-0">
                      <code className="text-sm text-white font-mono">{endpoint.path}</code>
                      <p className="text-xs text-slate-400 mt-1">{endpoint.description}</p>
                      {endpoint.params !== '-' && (
                        <p className="text-xs text-slate-500 mt-0.5">
                          参数: <span className="text-slate-400">{endpoint.params}</span>
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Code Examples */}
          <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
            <h2 className="font-display text-lg font-semibold text-white flex items-center gap-2 mb-4">
              <Braces className="w-5 h-5 text-primary-400" />
              代码示例
            </h2>
            <div className="space-y-4">
              <div>
                <div className="text-xs text-slate-500 mb-2">Python</div>
                <div className="bg-slate-900/50 rounded-lg p-4 font-mono text-xs overflow-x-auto">
                  <pre className="text-slate-300">{`import requests

API_BASE = "https://api.findablex.com/api/v1"
TOKEN = "your-access-token"
headers = {"Authorization": f"Bearer {TOKEN}"}

# 获取项目列表
projects = requests.get(f"{API_BASE}/projects", headers=headers).json()

# 触发一键体检
checkup = requests.post(
    f"{API_BASE}/projects/{projects[0]['id']}/auto-checkup",
    headers=headers,
    json={"max_engines": 3}
).json()
print(f"体检已启动: {checkup['message']}")

# 查看品牌可见性
summary = requests.get(
    f"{API_BASE}/projects/{projects[0]['id']}/citations-summary",
    headers=headers
).json()
print(f"品牌可见性: {summary['visibility_score']}%")`}</pre>
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-2">JavaScript / Node.js</div>
                <div className="bg-slate-900/50 rounded-lg p-4 font-mono text-xs overflow-x-auto">
                  <pre className="text-slate-300">{`const API_BASE = 'https://api.findablex.com/api/v1';
const TOKEN = 'your-access-token';
const headers = { Authorization: \`Bearer \${TOKEN}\` };

// 获取项目趋势数据
const res = await fetch(
  \`\${API_BASE}/projects/\${projectId}/trends?days=30\`,
  { headers }
);
const trends = await res.json();
console.log(\`平均可见性: \${trends.summary.avg_visibility}%\`);
console.log(\`最佳引擎: \${trends.summary.best_engine}\`);`}</pre>
                </div>
              </div>
            </div>
          </div>

          {/* Webhook Events Documentation */}
          {eventTypes.length > 0 && (
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <h2 className="font-display text-lg font-semibold text-white flex items-center gap-2 mb-4">
                <Webhook className="w-5 h-5 text-primary-400" />
                Webhook 事件类型
              </h2>
              <div className="space-y-3">
                {eventTypes.map((event) => (
                  <div key={event.type} className="p-3 bg-slate-700/20 rounded-lg">
                    <div className="flex items-center gap-2 mb-1">
                      <code className="text-sm font-mono text-primary-400">{event.type}</code>
                    </div>
                    <p className="text-xs text-slate-400">{event.description}</p>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {event.payload_fields.map((field) => (
                        <span
                          key={field}
                          className="px-2 py-0.5 bg-slate-700/50 rounded text-[10px] text-slate-400 font-mono"
                        >
                          {field}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Webhooks Tab */}
      {activeTab === 'webhooks' && (
        <div className="space-y-6">
          {/* Create Button */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-400">
              通过 Webhook 接收 FindableX 的实时事件通知
            </p>
            <button
              onClick={() => setShowCreateDialog(true)}
              className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg font-medium text-sm transition-colors"
            >
              <Plus className="w-4 h-4" />
              创建 Webhook
            </button>
          </div>

          {/* Webhook List */}
          {isLoadingWebhooks ? (
            <div className="py-12 flex items-center justify-center">
              <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
            </div>
          ) : webhooks.length === 0 ? (
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-12 text-center">
              <Webhook className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">还没有 Webhook</h3>
              <p className="text-slate-400 text-sm mb-6">
                创建 Webhook 来在体检完成、变化检测等事件发生时接收通知
              </p>
              <button
                onClick={() => setShowCreateDialog(true)}
                className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg font-medium text-sm transition-colors"
              >
                <Plus className="w-4 h-4" />
                创建第一个 Webhook
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {webhooks.map((webhook) => (
                <div
                  key={webhook.id}
                  className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3">
                        <h3 className="font-medium text-white">{webhook.name}</h3>
                        <span
                          className={cn(
                            'px-2 py-0.5 rounded-full text-[10px] font-medium',
                            webhook.is_active
                              ? 'bg-green-500/10 text-green-400'
                              : 'bg-slate-500/10 text-slate-400'
                          )}
                        >
                          {webhook.is_active ? '活跃' : '已暂停'}
                        </span>
                        {webhook.failure_count > 0 && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-red-500/10 text-red-400">
                            {webhook.failure_count} 次失败
                          </span>
                        )}
                      </div>
                      <code className="text-xs text-slate-400 font-mono mt-1 block truncate">
                        {webhook.url}
                      </code>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {webhook.events.map((event) => (
                          <span
                            key={event}
                            className="px-2 py-0.5 bg-primary-500/10 text-primary-400 rounded text-[10px] font-mono"
                          >
                            {event}
                          </span>
                        ))}
                      </div>

                      {/* Secret */}
                      <div className="flex items-center gap-2 mt-3">
                        <span className="text-xs text-slate-500">Secret:</span>
                        <code className="text-xs text-slate-400 font-mono">
                          {showSecrets.has(webhook.id)
                            ? webhook.secret
                            : '••••••••••••••••••••'}
                        </code>
                        <button
                          onClick={() => toggleSecretVisibility(webhook.id)}
                          className="p-1 text-slate-500 hover:text-white transition-colors"
                        >
                          {showSecrets.has(webhook.id) ? (
                            <EyeOff className="w-3 h-3" />
                          ) : (
                            <Eye className="w-3 h-3" />
                          )}
                        </button>
                        <button
                          onClick={() => handleCopy(webhook.secret, `secret-${webhook.id}`)}
                          className="p-1 text-slate-500 hover:text-white transition-colors"
                        >
                          {copiedText === `secret-${webhook.id}` ? (
                            <Check className="w-3 h-3 text-green-400" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>

                      {/* Test result */}
                      {testResult && testResult.id === webhook.id && (
                        <div
                          className={cn(
                            'mt-3 px-3 py-2 rounded-lg text-xs flex items-center gap-2',
                            testResult.success
                              ? 'bg-green-500/10 text-green-400'
                              : 'bg-red-500/10 text-red-400'
                          )}
                        >
                          {testResult.success ? (
                            <CheckCircle className="w-3.5 h-3.5" />
                          ) : (
                            <XCircle className="w-3.5 h-3.5" />
                          )}
                          {testResult.success
                            ? `测试成功 (${testResult.status})`
                            : `测试失败: ${testResult.error || testResult.status}`}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                      <button
                        onClick={() => handleTestWebhook(webhook.id)}
                        disabled={testingWebhookId === webhook.id}
                        className="p-2 text-slate-400 hover:text-primary-400 hover:bg-slate-700 rounded-lg transition-colors"
                        title="发送测试事件"
                      >
                        {testingWebhookId === webhook.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Play className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => handleToggleWebhook(webhook.id, webhook.is_active)}
                        className="p-2 text-slate-400 hover:text-amber-400 hover:bg-slate-700 rounded-lg transition-colors"
                        title={webhook.is_active ? '暂停' : '启用'}
                      >
                        <RefreshCw className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteWebhook(webhook.id)}
                        className="p-2 text-slate-400 hover:text-red-400 hover:bg-slate-700 rounded-lg transition-colors"
                        title="删除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Create Webhook Dialog */}
          {showCreateDialog && (
            <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
              <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-lg shadow-2xl">
                <div className="px-6 py-4 border-b border-slate-700">
                  <h3 className="text-lg font-semibold text-white">创建 Webhook</h3>
                </div>
                <div className="px-6 py-4 space-y-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1.5">名称</label>
                    <input
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      placeholder="例如: 飞书通知"
                      className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-500 focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1.5">URL</label>
                    <input
                      value={newUrl}
                      onChange={(e) => setNewUrl(e.target.value)}
                      placeholder="https://your-server.com/webhook"
                      className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-500 focus:ring-1 focus:ring-primary-500 focus:border-primary-500 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1.5">订阅事件</label>
                    <div className="grid grid-cols-1 gap-2">
                      {eventTypes.map((event) => (
                        <label
                          key={event.type}
                          className={cn(
                            'flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                            newEvents.includes(event.type)
                              ? 'border-primary-500/50 bg-primary-500/5'
                              : 'border-slate-700 hover:border-slate-600'
                          )}
                        >
                          <input
                            type="checkbox"
                            checked={newEvents.includes(event.type)}
                            onChange={() => toggleEventSelection(event.type)}
                            className="mt-0.5 rounded border-slate-600 bg-slate-700 text-primary-500 focus:ring-primary-500"
                          />
                          <div>
                            <code className="text-xs font-mono text-primary-400">
                              {event.type}
                            </code>
                            <p className="text-xs text-slate-400 mt-0.5">
                              {event.description}
                            </p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                  {createError && (
                    <div className="flex items-center gap-2 text-sm text-red-400">
                      <AlertCircle className="w-4 h-4" />
                      {createError}
                    </div>
                  )}
                </div>
                <div className="px-6 py-4 border-t border-slate-700 flex items-center justify-end gap-3">
                  <button
                    onClick={() => {
                      setShowCreateDialog(false);
                      setCreateError('');
                    }}
                    className="px-4 py-2 text-slate-400 hover:text-white text-sm transition-colors"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleCreateWebhook}
                    disabled={isCreating || !newName.trim() || !newUrl.trim() || newEvents.length === 0}
                    className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/30 text-white px-4 py-2 rounded-lg font-medium text-sm transition-colors"
                  >
                    {isCreating ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Plus className="w-4 h-4" />
                    )}
                    创建
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
