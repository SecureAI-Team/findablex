'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Loader2,
  Search,
  Filter,
  User,
  Users,
  Shield,
  ShieldOff,
  Trash2,
  Key,
  MoreVertical,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Building2,
  Mail,
  Calendar,
  FolderKanban,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface UserItem {
  id: string;
  email: string;
  full_name?: string;
  company_name?: string;
  industry?: string;
  business_role?: string;
  is_active: boolean;
  is_superuser: boolean;
  email_verified_at?: string;
  created_at: string;
  updated_at: string;
  workspace_count: number;
}

interface UserListResponse {
  items: UserItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface UserDetail extends UserItem {
  memberships: Array<{
    workspace_id: string;
    workspace_name: string;
    role: string;
    joined_at?: string;
  }>;
}

const industryLabels: Record<string, string> = {
  ot_security: 'OT安全/工业控制',
  cybersecurity: '网络安全',
  industrial_software: '工业软件',
  saas: 'SaaS/企业服务',
  fintech: '金融科技',
  healthcare: '医疗健康',
  education: '教育培训',
  ecommerce: '电商零售',
  manufacturing: '制造业',
  other: '其他',
};

const roleLabels: Record<string, string> = {
  marketing: '市场负责人',
  growth: '增长负责人',
  sales: '销售负责人',
  brand_pr: '品牌/公关',
  compliance: '法务合规',
  security: '安全负责人',
  presales: '售前/解决方案',
  product: '产品负责人',
  other: '其他',
};

export default function UsersPage() {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [selectedUser, setSelectedUser] = useState<UserDetail | null>(null);
  const [showUserModal, setShowUserModal] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{
    type: 'delete' | 'toggle_active' | 'toggle_superuser' | 'reset_password';
    userId: string;
    userName: string;
    newValue?: boolean;
  } | null>(null);
  
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({
    is_active: undefined as boolean | undefined,
    is_superuser: undefined as boolean | undefined,
    industry: '',
  });
  const pageSize = 20;

  const fetchUsers = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const params = new URLSearchParams();
      params.append('page', String(page));
      params.append('page_size', String(pageSize));
      
      if (search) params.append('search', search);
      if (filters.is_active !== undefined) params.append('is_active', String(filters.is_active));
      if (filters.is_superuser !== undefined) params.append('is_superuser', String(filters.is_superuser));
      if (filters.industry) params.append('industry', filters.industry);
      
      const res = await api.get<UserListResponse>(`/admin/users?${params.toString()}`);
      setUsers(res.data.items);
      setTotalUsers(res.data.total);
      setTotalPages(res.data.total_pages);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('权限不足：仅平台管理员可管理用户');
      } else {
        setError(err.response?.data?.detail || '加载用户列表失败');
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [page, filters]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (search !== '') {
        setPage(1);
        fetchUsers();
      } else {
        fetchUsers();
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const handleViewUser = async (userId: string) => {
    try {
      const res = await api.get<UserDetail>(`/admin/users/${userId}`);
      setSelectedUser(res.data);
      setShowUserModal(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || '获取用户详情失败');
    }
  };

  const handleConfirmAction = (action: typeof confirmAction) => {
    setConfirmAction(action);
    setShowConfirmModal(true);
  };

  const executeAction = async () => {
    if (!confirmAction) return;
    
    try {
      switch (confirmAction.type) {
        case 'delete':
          await api.delete(`/admin/users/${confirmAction.userId}`);
          setSuccessMessage(`已删除用户 ${confirmAction.userName}`);
          break;
        case 'toggle_active':
          await api.put(`/admin/users/${confirmAction.userId}`, {
            is_active: confirmAction.newValue,
          });
          setSuccessMessage(confirmAction.newValue ? '已启用用户' : '已禁用用户');
          break;
        case 'toggle_superuser':
          await api.put(`/admin/users/${confirmAction.userId}`, {
            is_superuser: confirmAction.newValue,
          });
          setSuccessMessage(confirmAction.newValue ? '已授予管理员权限' : '已撤销管理员权限');
          break;
        case 'reset_password':
          const res = await api.post(`/admin/users/${confirmAction.userId}/reset-password`);
          setSuccessMessage(`密码已重置为: ${res.data.temporary_password} (请及时告知用户)`);
          break;
      }
      await fetchUsers();
    } catch (err: any) {
      setError(err.response?.data?.detail || '操作失败');
    } finally {
      setShowConfirmModal(false);
      setConfirmAction(null);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Clear success message after 5 seconds
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(''), 5000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-2xl font-bold text-white flex items-center gap-3">
              <Users className="w-7 h-7 text-primary-500" />
              用户管理
            </h1>
            <p className="mt-1 text-slate-400">管理平台所有用户账户</p>
          </div>
          <div className="text-sm text-slate-400">
            共 {totalUsers} 位用户
          </div>
        </div>
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className="p-4 bg-green-500/10 border border-green-500/50 rounded-lg text-green-400 text-sm mb-6 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          {successMessage}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm mb-6 flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Search and Filters */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 mb-6">
        <div className="flex flex-wrap gap-4">
          {/* Search */}
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="搜索邮箱、姓名、公司..."
                className="w-full pl-10 pr-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
          </div>
          
          <select
            value={filters.is_active === undefined ? '' : String(filters.is_active)}
            onChange={(e) => {
              const val = e.target.value;
              setFilters({
                ...filters,
                is_active: val === '' ? undefined : val === 'true',
              });
              setPage(1);
            }}
            className="px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">所有状态</option>
            <option value="true">已启用</option>
            <option value="false">已禁用</option>
          </select>

          <select
            value={filters.is_superuser === undefined ? '' : String(filters.is_superuser)}
            onChange={(e) => {
              const val = e.target.value;
              setFilters({
                ...filters,
                is_superuser: val === '' ? undefined : val === 'true',
              });
              setPage(1);
            }}
            className="px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">所有角色</option>
            <option value="true">管理员</option>
            <option value="false">普通用户</option>
          </select>

          <select
            value={filters.industry}
            onChange={(e) => {
              setFilters({ ...filters, industry: e.target.value });
              setPage(1);
            }}
            className="px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">所有行业</option>
            {Object.entries(industryLabels).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
          </div>
        ) : users.length === 0 ? (
          <div className="text-center py-12">
            <Users className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400">暂无用户</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700 bg-slate-800/50">
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-400">用户</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-400">公司</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-400">工作区</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-400">状态</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-400">注册时间</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-slate-400">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-slate-700/20 transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          "w-9 h-9 rounded-full flex items-center justify-center text-white font-medium text-sm",
                          user.is_superuser ? "bg-amber-500/20 text-amber-400" : "bg-slate-600"
                        )}>
                          {user.full_name?.[0] || user.email[0].toUpperCase()}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-white">
                              {user.full_name || '未设置'}
                            </span>
                            {user.is_superuser && (
                              <span title="平台管理员">
                                <Shield className="w-3.5 h-3.5 text-amber-400" />
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-1 text-xs text-slate-400">
                            <Mail className="w-3 h-3" />
                            {user.email}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {user.company_name ? (
                        <div className="flex items-center gap-1 text-sm text-slate-300">
                          <Building2 className="w-3.5 h-3.5 text-slate-500" />
                          {user.company_name}
                        </div>
                      ) : (
                        <span className="text-sm text-slate-500">-</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1 text-sm text-slate-300">
                        <FolderKanban className="w-3.5 h-3.5 text-slate-500" />
                        {user.workspace_count}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={cn(
                        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs",
                        user.is_active
                          ? "bg-green-500/10 text-green-400"
                          : "bg-red-500/10 text-red-400"
                      )}>
                        {user.is_active ? (
                          <><CheckCircle2 className="w-3 h-3" /> 已启用</>
                        ) : (
                          <><XCircle className="w-3 h-3" /> 已禁用</>
                        )}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1 text-sm text-slate-400">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        {formatDate(user.created_at)}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleViewUser(user.id)}
                          className="p-2 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-colors"
                          title="查看详情"
                        >
                          <User className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleConfirmAction({
                            type: 'toggle_active',
                            userId: user.id,
                            userName: user.email,
                            newValue: !user.is_active,
                          })}
                          className={cn(
                            "p-2 rounded-lg transition-colors",
                            user.is_active
                              ? "text-slate-400 hover:text-red-400 hover:bg-red-500/10"
                              : "text-slate-400 hover:text-green-400 hover:bg-green-500/10"
                          )}
                          title={user.is_active ? '禁用用户' : '启用用户'}
                        >
                          {user.is_active ? (
                            <ShieldOff className="w-4 h-4" />
                          ) : (
                            <Shield className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={() => handleConfirmAction({
                            type: 'reset_password',
                            userId: user.id,
                            userName: user.email,
                          })}
                          className="p-2 text-slate-400 hover:text-amber-400 hover:bg-amber-500/10 rounded-lg transition-colors"
                          title="重置密码"
                        >
                          <Key className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleConfirmAction({
                            type: 'delete',
                            userId: user.id,
                            userName: user.email,
                          })}
                          className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                          title="删除用户"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {users.length > 0 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 text-sm text-slate-400 hover:text-white disabled:text-slate-600 disabled:cursor-not-allowed transition-colors"
            >
              上一页
            </button>
            <span className="text-sm text-slate-500">
              第 {page} / {totalPages} 页
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page === totalPages}
              className="px-3 py-1.5 text-sm text-slate-400 hover:text-white disabled:text-slate-600 disabled:cursor-not-allowed transition-colors"
            >
              下一页
            </button>
          </div>
        )}
      </div>

      {/* User Detail Modal */}
      {showUserModal && selectedUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl border border-slate-700 max-w-lg w-full max-h-[80vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-start justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "w-12 h-12 rounded-full flex items-center justify-center text-white font-medium text-lg",
                    selectedUser.is_superuser ? "bg-amber-500/20 text-amber-400" : "bg-slate-600"
                  )}>
                    {selectedUser.full_name?.[0] || selectedUser.email[0].toUpperCase()}
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-white">
                      {selectedUser.full_name || '未设置姓名'}
                    </h2>
                    <p className="text-sm text-slate-400">{selectedUser.email}</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowUserModal(false)}
                  className="text-slate-400 hover:text-white"
                >
                  <XCircle className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">状态</label>
                    <span className={cn(
                      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs",
                      selectedUser.is_active
                        ? "bg-green-500/10 text-green-400"
                        : "bg-red-500/10 text-red-400"
                    )}>
                      {selectedUser.is_active ? '已启用' : '已禁用'}
                    </span>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">角色</label>
                    <span className={cn(
                      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs",
                      selectedUser.is_superuser
                        ? "bg-amber-500/10 text-amber-400"
                        : "bg-slate-500/10 text-slate-400"
                    )}>
                      {selectedUser.is_superuser ? '平台管理员' : '普通用户'}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">公司</label>
                    <p className="text-sm text-white">{selectedUser.company_name || '-'}</p>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">行业</label>
                    <p className="text-sm text-white">
                      {selectedUser.industry ? industryLabels[selectedUser.industry] || selectedUser.industry : '-'}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">职务</label>
                    <p className="text-sm text-white">
                      {selectedUser.business_role ? roleLabels[selectedUser.business_role] || selectedUser.business_role : '-'}
                    </p>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">邮箱验证</label>
                    <p className="text-sm text-white">
                      {selectedUser.email_verified_at ? '已验证' : '未验证'}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">注册时间</label>
                    <p className="text-sm text-white">{formatDate(selectedUser.created_at)}</p>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">最后更新</label>
                    <p className="text-sm text-white">{formatDate(selectedUser.updated_at)}</p>
                  </div>
                </div>

                {/* Memberships */}
                <div>
                  <label className="block text-xs text-slate-500 mb-2">所属工作区</label>
                  {selectedUser.memberships.length === 0 ? (
                    <p className="text-sm text-slate-400">无</p>
                  ) : (
                    <div className="space-y-2">
                      {selectedUser.memberships.map((m) => (
                        <div
                          key={m.workspace_id}
                          className="flex items-center justify-between p-2 bg-slate-700/30 rounded-lg"
                        >
                          <span className="text-sm text-white">{m.workspace_name}</span>
                          <span className={cn(
                            "text-xs px-2 py-0.5 rounded",
                            m.role === 'admin' ? "bg-amber-500/10 text-amber-400" : "bg-slate-500/10 text-slate-400"
                          )}>
                            {m.role}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 mt-6 pt-6 border-t border-slate-700">
                <button
                  onClick={() => {
                    setShowUserModal(false);
                    handleConfirmAction({
                      type: 'toggle_superuser',
                      userId: selectedUser.id,
                      userName: selectedUser.email,
                      newValue: !selectedUser.is_superuser,
                    });
                  }}
                  className={cn(
                    "flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors",
                    selectedUser.is_superuser
                      ? "bg-slate-700 text-slate-300 hover:bg-slate-600"
                      : "bg-amber-500/20 text-amber-400 hover:bg-amber-500/30"
                  )}
                >
                  {selectedUser.is_superuser ? '撤销管理员权限' : '授予管理员权限'}
                </button>
                <button
                  onClick={() => setShowUserModal(false)}
                  className="px-4 py-2 bg-slate-700 text-white rounded-lg text-sm font-medium hover:bg-slate-600 transition-colors"
                >
                  关闭
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Confirm Modal */}
      {showConfirmModal && confirmAction && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl border border-slate-700 max-w-md w-full p-6">
            <h3 className="text-lg font-semibold text-white mb-2">
              {confirmAction.type === 'delete' && '确认删除用户'}
              {confirmAction.type === 'toggle_active' && (confirmAction.newValue ? '确认启用用户' : '确认禁用用户')}
              {confirmAction.type === 'toggle_superuser' && (confirmAction.newValue ? '确认授予管理员权限' : '确认撤销管理员权限')}
              {confirmAction.type === 'reset_password' && '确认重置密码'}
            </h3>
            <p className="text-slate-400 mb-6">
              {confirmAction.type === 'delete' && (
                <>此操作将永久删除用户 <span className="text-white">{confirmAction.userName}</span>，包括其所有工作区成员身份。此操作不可恢复。</>
              )}
              {confirmAction.type === 'toggle_active' && (
                <>将{confirmAction.newValue ? '启用' : '禁用'}用户 <span className="text-white">{confirmAction.userName}</span> 的账户。{!confirmAction.newValue && '禁用后该用户将无法登录。'}</>
              )}
              {confirmAction.type === 'toggle_superuser' && (
                <>将{confirmAction.newValue ? '授予' : '撤销'}用户 <span className="text-white">{confirmAction.userName}</span> 的平台管理员权限。</>
              )}
              {confirmAction.type === 'reset_password' && (
                <>将为用户 <span className="text-white">{confirmAction.userName}</span> 生成新的临时密码。</>
              )}
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowConfirmModal(false);
                  setConfirmAction(null);
                }}
                className="flex-1 py-2 px-4 bg-slate-700 text-white rounded-lg text-sm font-medium hover:bg-slate-600 transition-colors"
              >
                取消
              </button>
              <button
                onClick={executeAction}
                className={cn(
                  "flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors",
                  confirmAction.type === 'delete'
                    ? "bg-red-500 text-white hover:bg-red-600"
                    : "bg-primary-500 text-white hover:bg-primary-600"
                )}
              >
                确认
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
