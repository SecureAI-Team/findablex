'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Loader2,
  Search,
  Filter,
  Calendar,
  User,
  Activity,
  FileText,
  Settings,
  Database,
  AlertCircle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface AuditLog {
  id: string;
  workspace_id?: string;
  user_id?: string;
  user_email?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  ip_address?: string;
  created_at: string;
}

const actionLabels: Record<string, string> = {
  'user.login': '用户登录',
  'user.logout': '用户登出',
  'user.created': '用户创建',
  'user.updated': '用户更新',
  'project.created': '项目创建',
  'project.updated': '项目更新',
  'project.deleted': '项目删除',
  'run.started': '运行开始',
  'run.completed': '运行完成',
  'report.exported': '报告导出',
  'report.shared': '报告分享',
  'member.invited': '成员邀请',
  'member.removed': '成员移除',
  'settings.updated': '设置更新',
};

const resourceIcons: Record<string, any> = {
  user: User,
  project: FileText,
  run: Activity,
  report: FileText,
  settings: Settings,
  workspace: Database,
};

export default function AuditLogPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState({
    action: '',
    user_id: '',
    resource_type: '',
  });
  const [page, setPage] = useState(0);
  const limit = 50;

  useEffect(() => {
    const fetchLogs = async () => {
      setIsLoading(true);
      setError('');
      
      try {
        const params = new URLSearchParams();
        params.append('limit', String(limit));
        params.append('offset', String(page * limit));
        
        if (filter.action) params.append('action', filter.action);
        if (filter.user_id) params.append('user_id', filter.user_id);
        
        const res = await api.get(`/admin/audit-logs?${params.toString()}`);
        setLogs(res.data);
      } catch (err: any) {
        if (err.response?.status === 403) {
          setError('权限不足：仅管理员可查看审计日志');
        } else {
          setError(err.response?.data?.detail || '加载审计日志失败');
        }
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchLogs();
  }, [page, filter]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getActionLabel = (action: string) => {
    return actionLabels[action] || action;
  };

  const getResourceIcon = (resourceType: string) => {
    const Icon = resourceIcons[resourceType] || Activity;
    return Icon;
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/settings"
          className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          返回设置
        </Link>
        <h1 className="font-display text-2xl font-bold text-white">审计日志</h1>
        <p className="mt-1 text-slate-400">查看系统操作历史记录</p>
      </div>

      {/* Filters */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 mb-6">
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-400">筛选:</span>
          </div>
          
          <select
            value={filter.action}
            onChange={(e) => {
              setFilter({ ...filter, action: e.target.value });
              setPage(0);
            }}
            className="px-3 py-1.5 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">所有操作</option>
            <option value="user.login">用户登录</option>
            <option value="project.created">项目创建</option>
            <option value="project.updated">项目更新</option>
            <option value="run.started">运行开始</option>
            <option value="report.exported">报告导出</option>
            <option value="member.invited">成员邀请</option>
          </select>

          <select
            value={filter.resource_type}
            onChange={(e) => {
              setFilter({ ...filter, resource_type: e.target.value });
              setPage(0);
            }}
            className="px-3 py-1.5 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">所有资源</option>
            <option value="user">用户</option>
            <option value="project">项目</option>
            <option value="run">运行</option>
            <option value="report">报告</option>
            <option value="workspace">工作空间</option>
          </select>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm mb-6 flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Logs Table */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-12">
            <Activity className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400">暂无审计日志</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700 bg-slate-800/50">
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-400">时间</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-400">操作</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-400">资源</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-400">用户</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-400">IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {logs.map((log) => {
                  const ResourceIcon = getResourceIcon(log.resource_type);
                  return (
                    <tr key={log.id} className="hover:bg-slate-700/20 transition-colors">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2 text-sm text-slate-300">
                          <Calendar className="w-4 h-4 text-slate-500" />
                          {formatDate(log.created_at)}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-white">{getActionLabel(log.action)}</span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <ResourceIcon className="w-4 h-4 text-slate-500" />
                          <span className="text-sm text-slate-300">{log.resource_type}</span>
                          {log.resource_id && (
                            <span className="text-xs text-slate-500 font-mono">
                              {log.resource_id.substring(0, 8)}...
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-slate-400">
                          {log.user_email || log.user_id?.substring(0, 8) || '-'}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-slate-500 font-mono">
                          {log.ip_address || '-'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {logs.length > 0 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="px-3 py-1.5 text-sm text-slate-400 hover:text-white disabled:text-slate-600 disabled:cursor-not-allowed transition-colors"
            >
              上一页
            </button>
            <span className="text-sm text-slate-500">第 {page + 1} 页</span>
            <button
              onClick={() => setPage(page + 1)}
              disabled={logs.length < limit}
              className="px-3 py-1.5 text-sm text-slate-400 hover:text-white disabled:text-slate-600 disabled:cursor-not-allowed transition-colors"
            >
              下一页
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
