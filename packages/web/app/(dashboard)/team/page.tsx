'use client';

import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Crown,
  Loader2,
  Mail,
  MoreVertical,
  Plus,
  Shield,
  Trash2,
  User,
  UserCheck,
  UserCog,
  Users,
  X,
  Eye,
  FlaskConical,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

const inviteSchema = z.object({
  email: z.string().email('请输入有效的邮箱地址'),
  role: z.enum(['admin', 'analyst', 'researcher', 'viewer']),
});

type InviteForm = z.infer<typeof inviteSchema>;

interface Member {
  id: string;
  user_id: string;
  workspace_id: string;
  role: string;
  created_at: string;
  user_email: string;
  user_name: string;
}

const roleLabels: Record<string, { label: string; icon: any; color: string }> = {
  admin: { label: '管理员', icon: Crown, color: 'text-yellow-400 bg-yellow-400/10' },
  analyst: { label: '分析师', icon: UserCog, color: 'text-blue-400 bg-blue-400/10' },
  researcher: { label: '研究员', icon: FlaskConical, color: 'text-purple-400 bg-purple-400/10' },
  viewer: { label: '查看者', icon: Eye, color: 'text-slate-400 bg-slate-400/10' },
};

export default function TeamPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [isInviting, setIsInviting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<InviteForm>({
    resolver: zodResolver(inviteSchema),
    defaultValues: {
      role: 'viewer',
    },
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Get current user and workspace
        const userRes = await api.get('/auth/me');
        setCurrentUserId(userRes.data.id);
        const wsId = userRes.data.default_workspace_id;
        setWorkspaceId(wsId);

        if (wsId) {
          // Fetch members
          const membersRes = await api.get(`/workspaces/${wsId}/members`);
          setMembers(membersRes.data);

          // Check if current user is admin
          const currentMember = membersRes.data.find(
            (m: Member) => m.user_id === userRes.data.id
          );
          setIsAdmin(
            currentMember?.role === 'admin' || userRes.data.is_superuser
          );
        }
      } catch (error) {
        console.error('Failed to fetch team data:', error);
        setError('加载团队数据失败');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleInvite = async (data: InviteForm) => {
    if (!workspaceId) return;

    setIsInviting(true);
    setError('');

    try {
      await api.post(`/workspaces/${workspaceId}/invite`, {
        email: data.email,
        role: data.role,
      });

      // Refresh members list
      const membersRes = await api.get(`/workspaces/${workspaceId}/members`);
      setMembers(membersRes.data);

      setSuccess('邀请成功！');
      setTimeout(() => setSuccess(''), 3000);
      setShowInviteModal(false);
      reset();
    } catch (err: any) {
      setError(err.response?.data?.detail || '邀请失败');
    } finally {
      setIsInviting(false);
    }
  };

  const handleChangeRole = async (memberId: string, newRole: string) => {
    if (!workspaceId) return;

    try {
      await api.put(`/workspaces/${workspaceId}/members/${memberId}`, {
        role: newRole,
      });

      // Refresh members list
      const membersRes = await api.get(`/workspaces/${workspaceId}/members`);
      setMembers(membersRes.data);

      setSuccess('角色已更新');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || '更新角色失败');
    }
    setMenuOpenId(null);
  };

  const handleRemoveMember = async (memberId: string) => {
    if (!workspaceId) return;
    if (!confirm('确定要移除此成员吗？')) return;

    try {
      await api.delete(`/workspaces/${workspaceId}/members/${memberId}`);

      // Refresh members list
      const membersRes = await api.get(`/workspaces/${workspaceId}/members`);
      setMembers(membersRes.data);

      setSuccess('成员已移除');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || '移除成员失败');
    }
    setMenuOpenId(null);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-white">团队管理</h1>
          <p className="mt-1 text-slate-400">管理工作空间成员和权限</p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setShowInviteModal(true)}
            className="inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white px-4 py-2.5 rounded-lg font-medium transition-all"
          >
            <Plus className="w-5 h-5" />
            邀请成员
          </button>
        )}
      </div>

      {/* Success/Error Messages */}
      {success && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg px-4 py-3 text-green-400">
          {success}
        </div>
      )}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400">
          {error}
        </div>
      )}

      {/* Members List */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50">
        <div className="p-6 border-b border-slate-700/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-500/10 rounded-lg flex items-center justify-center">
              <Users className="w-5 h-5 text-primary-400" />
            </div>
            <div>
              <h2 className="font-display text-lg font-semibold text-white">
                团队成员
              </h2>
              <p className="text-sm text-slate-400">{members.length} 名成员</p>
            </div>
          </div>
        </div>

        <div className="divide-y divide-slate-700/50">
          {members.map((member) => {
            const roleInfo = roleLabels[member.role] || roleLabels.viewer;
            const RoleIcon = roleInfo.icon;
            const isCurrentUser = member.user_id === currentUserId;

            return (
              <div
                key={member.id}
                className="p-4 flex items-center justify-between hover:bg-slate-700/20 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-slate-700 rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-slate-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white">
                        {member.user_name || '未设置姓名'}
                      </span>
                      {isCurrentUser && (
                        <span className="text-xs bg-primary-500/20 text-primary-400 px-2 py-0.5 rounded">
                          你
                        </span>
                      )}
                    </div>
                    <span className="text-sm text-slate-400">
                      {member.user_email}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium',
                      roleInfo.color
                    )}
                  >
                    <RoleIcon className="w-4 h-4" />
                    {roleInfo.label}
                  </div>

                  {isAdmin && !isCurrentUser && (
                    <div className="relative">
                      <button
                        onClick={() =>
                          setMenuOpenId(menuOpenId === member.id ? null : member.id)
                        }
                        className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
                      >
                        <MoreVertical className="w-5 h-5" />
                      </button>

                      {menuOpenId === member.id && (
                        <>
                          <div
                            className="fixed inset-0 z-10"
                            onClick={() => setMenuOpenId(null)}
                          />
                          <div className="absolute right-0 top-full mt-1 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-20 py-1">
                            <div className="px-3 py-2 text-xs text-slate-500 font-medium">
                              更改角色
                            </div>
                            {Object.entries(roleLabels).map(([role, info]) => (
                              <button
                                key={role}
                                onClick={() => handleChangeRole(member.id, role)}
                                className={cn(
                                  'w-full flex items-center gap-2 px-4 py-2 text-sm transition-colors',
                                  member.role === role
                                    ? 'text-primary-400 bg-primary-500/10'
                                    : 'text-slate-300 hover:bg-slate-700'
                                )}
                              >
                                <info.icon className="w-4 h-4" />
                                {info.label}
                                {member.role === role && (
                                  <UserCheck className="w-4 h-4 ml-auto" />
                                )}
                              </button>
                            ))}
                            <div className="border-t border-slate-700 my-1" />
                            <button
                              onClick={() => handleRemoveMember(member.id)}
                              className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-slate-700 transition-colors"
                            >
                              <Trash2 className="w-4 h-4" />
                              移除成员
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Role Descriptions */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <h3 className="font-display text-lg font-semibold text-white mb-4">
          角色说明
        </h3>
        <div className="grid md:grid-cols-2 gap-4">
          {Object.entries(roleLabels).map(([role, info]) => {
            const RoleIcon = info.icon;
            const descriptions: Record<string, string> = {
              admin: '完全控制权限，可以管理成员、项目和所有设置',
              analyst: '可以创建和管理项目、运行分析、查看和分享报告',
              researcher: '可以查看项目和报告，触发爬虫任务，导出匿名数据',
              viewer: '只读权限，可以查看项目、运行记录和报告',
            };

            return (
              <div
                key={role}
                className="flex items-start gap-3 p-4 bg-slate-700/30 rounded-lg"
              >
                <div
                  className={cn(
                    'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
                    info.color
                  )}
                >
                  <RoleIcon className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-medium text-white">{info.label}</h4>
                  <p className="text-sm text-slate-400 mt-1">
                    {descriptions[role]}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-2xl border border-slate-700 w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b border-slate-700">
              <h2 className="font-display text-xl font-semibold text-white">
                邀请成员
              </h2>
              <button
                onClick={() => {
                  setShowInviteModal(false);
                  reset();
                  setError('');
                }}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit(handleInvite)} className="p-6 space-y-4">
              {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  邮箱地址
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <input
                    {...register('email')}
                    type="email"
                    placeholder="请输入成员邮箱"
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg py-2.5 pl-10 pr-4 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500"
                  />
                </div>
                {errors.email && (
                  <p className="mt-1 text-sm text-red-400">{errors.email.message}</p>
                )}
                <p className="mt-1 text-xs text-slate-500">
                  被邀请者需要先注册账号
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  角色
                </label>
                <select
                  {...register('role')}
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg py-2.5 px-4 text-white focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500"
                >
                  <option value="viewer">查看者 - 只读权限</option>
                  <option value="analyst">分析师 - 可创建项目和分析</option>
                  <option value="researcher">研究员 - 可触发爬虫和导出</option>
                  <option value="admin">管理员 - 完全控制</option>
                </select>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowInviteModal(false);
                    reset();
                    setError('');
                  }}
                  className="flex-1 bg-slate-700 hover:bg-slate-600 text-white py-2.5 rounded-lg font-medium transition-all"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={isInviting}
                  className="flex-1 bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/50 text-white py-2.5 rounded-lg font-medium transition-all flex items-center justify-center gap-2"
                >
                  {isInviting ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      邀请中...
                    </>
                  ) : (
                    '发送邀请'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
