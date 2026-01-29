'use client';

import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  User,
  Lock,
  Key,
  Bell,
  Loader2,
  CheckCircle,
  AlertCircle,
  Eye,
  EyeOff,
  Building2,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

const profileSchema = z.object({
  full_name: z.string().min(2, '姓名至少2个字符'),
});

const passwordSchema = z
  .object({
    current_password: z.string().min(1, '请输入当前密码'),
    new_password: z.string().min(8, '新密码至少8个字符'),
    confirm_password: z.string().min(1, '请确认新密码'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: '两次输入的密码不一致',
    path: ['confirm_password'],
  });

type ProfileForm = z.infer<typeof profileSchema>;
type PasswordForm = z.infer<typeof passwordSchema>;

type Tab = 'profile' | 'security' | 'workspace' | 'notifications' | 'api';

const tabs: { id: Tab; label: string; icon: any }[] = [
  { id: 'profile', label: '个人资料', icon: User },
  { id: 'security', label: '安全设置', icon: Lock },
  { id: 'workspace', label: '工作区', icon: Building2 },
  { id: 'notifications', label: '通知设置', icon: Bell },
  { id: 'api', label: 'API 密钥', icon: Key },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('profile');
  const [user, setUser] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isSavingPassword, setIsSavingPassword] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [profileError, setProfileError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [workspace, setWorkspace] = useState<any>(null);
  const [workspaceName, setWorkspaceName] = useState('');
  const [isSavingWorkspace, setIsSavingWorkspace] = useState(false);
  const [workspaceSuccess, setWorkspaceSuccess] = useState(false);
  const [notifications, setNotifications] = useState({
    drift_warning: true,
    retest_reminder: true,
    weekly_digest: false,
    marketing: false,
  });
  const [isSavingNotifications, setIsSavingNotifications] = useState(false);
  const [notificationsSuccess, setNotificationsSuccess] = useState(false);

  const profileForm = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
  });

  const passwordForm = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch user
        const userRes = await api.get('/auth/me');
        setUser(userRes.data);
        profileForm.reset({ full_name: userRes.data.full_name || '' });
        
        // Fetch workspace
        try {
          const workspacesRes = await api.get('/workspaces');
          if (workspacesRes.data.length > 0) {
            const ws = workspacesRes.data[0];
            setWorkspace(ws);
            setWorkspaceName(ws.name);
          }
        } catch (wsError) {
          console.error('Failed to fetch workspace:', wsError);
        }
      } catch (error) {
        console.error('Failed to fetch user:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleProfileSubmit = async (data: ProfileForm) => {
    setIsSavingProfile(true);
    setProfileError('');
    setProfileSuccess(false);

    try {
      await api.put('/auth/me', data);
      setProfileSuccess(true);
      setTimeout(() => setProfileSuccess(false), 3000);
    } catch (err: any) {
      setProfileError(err.response?.data?.detail || '保存失败');
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handlePasswordSubmit = async (data: PasswordForm) => {
    setIsSavingPassword(true);
    setPasswordError('');
    setPasswordSuccess(false);

    try {
      await api.put('/auth/me', { 
        current_password: data.current_password,
        password: data.new_password,
      });
      setPasswordSuccess(true);
      passwordForm.reset();
      setTimeout(() => setPasswordSuccess(false), 3000);
    } catch (err: any) {
      setPasswordError(err.response?.data?.detail || '修改密码失败');
    } finally {
      setIsSavingPassword(false);
    }
  };

  const handleWorkspaceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspace) return;
    
    setIsSavingWorkspace(true);
    setWorkspaceSuccess(false);

    try {
      await api.put(`/workspaces/${workspace.id}`, { name: workspaceName });
      setWorkspaceSuccess(true);
      setTimeout(() => setWorkspaceSuccess(false), 3000);
    } catch (err: any) {
      console.error('Failed to update workspace:', err);
    } finally {
      setIsSavingWorkspace(false);
    }
  };

  const handleNotificationsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingNotifications(true);
    setNotificationsSuccess(false);

    try {
      // Note: This would be a real API call in production
      // await api.put('/auth/me/notifications', notifications);
      setNotificationsSuccess(true);
      setTimeout(() => setNotificationsSuccess(false), 3000);
    } catch (err: any) {
      console.error('Failed to update notifications:', err);
    } finally {
      setIsSavingNotifications(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold text-white">设置</h1>
        <p className="mt-1 text-slate-400">管理您的账户和偏好设置</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar */}
        <div className="lg:w-48 flex-shrink-0">
          <nav className="flex lg:flex-col gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all w-full text-left',
                  activeTab === tab.id
                    ? 'bg-primary-500/10 text-primary-400'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800'
                )}
              >
                <tab.icon className="w-5 h-5" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 max-w-2xl">
          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <h2 className="font-display text-lg font-semibold text-white mb-6">
                个人资料
              </h2>

              {profileSuccess && (
                <div className="mb-6 p-4 bg-green-500/10 border border-green-500/50 rounded-lg text-green-400 text-sm flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  保存成功
                </div>
              )}

              {profileError && (
                <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  {profileError}
                </div>
              )}

              <form onSubmit={profileForm.handleSubmit(handleProfileSubmit)} className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    邮箱地址
                  </label>
                  <input
                    type="email"
                    value={user?.email || ''}
                    disabled
                    className="w-full px-4 py-3 bg-slate-700/30 border border-slate-600 rounded-lg text-slate-400 cursor-not-allowed"
                  />
                  <p className="mt-1.5 text-xs text-slate-500">邮箱地址不可修改</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    姓名
                  </label>
                  <input
                    type="text"
                    {...profileForm.register('full_name')}
                    className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="您的姓名"
                  />
                  {profileForm.formState.errors.full_name && (
                    <p className="mt-1.5 text-sm text-red-400">
                      {profileForm.formState.errors.full_name.message}
                    </p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={isSavingProfile}
                  className="bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/50 text-white px-6 py-2.5 rounded-lg font-medium transition-all flex items-center gap-2"
                >
                  {isSavingProfile ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      保存中...
                    </>
                  ) : (
                    '保存更改'
                  )}
                </button>
              </form>
            </div>
          )}

          {/* Security Tab */}
          {activeTab === 'security' && (
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <h2 className="font-display text-lg font-semibold text-white mb-6">
                修改密码
              </h2>

              {passwordSuccess && (
                <div className="mb-6 p-4 bg-green-500/10 border border-green-500/50 rounded-lg text-green-400 text-sm flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  密码修改成功
                </div>
              )}

              {passwordError && (
                <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  {passwordError}
                </div>
              )}

              <form onSubmit={passwordForm.handleSubmit(handlePasswordSubmit)} className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    当前密码
                  </label>
                  <div className="relative">
                    <input
                      type={showCurrentPassword ? 'text' : 'password'}
                      {...passwordForm.register('current_password')}
                      className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent pr-12"
                      placeholder="输入当前密码"
                    />
                    <button
                      type="button"
                      onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors"
                    >
                      {showCurrentPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                  {passwordForm.formState.errors.current_password && (
                    <p className="mt-1.5 text-sm text-red-400">
                      {passwordForm.formState.errors.current_password.message}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    新密码
                  </label>
                  <div className="relative">
                    <input
                      type={showNewPassword ? 'text' : 'password'}
                      {...passwordForm.register('new_password')}
                      className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent pr-12"
                      placeholder="至少8个字符"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors"
                    >
                      {showNewPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                  {passwordForm.formState.errors.new_password && (
                    <p className="mt-1.5 text-sm text-red-400">
                      {passwordForm.formState.errors.new_password.message}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    确认新密码
                  </label>
                  <input
                    type="password"
                    {...passwordForm.register('confirm_password')}
                    className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="再次输入新密码"
                  />
                  {passwordForm.formState.errors.confirm_password && (
                    <p className="mt-1.5 text-sm text-red-400">
                      {passwordForm.formState.errors.confirm_password.message}
                    </p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={isSavingPassword}
                  className="bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/50 text-white px-6 py-2.5 rounded-lg font-medium transition-all flex items-center gap-2"
                >
                  {isSavingPassword ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      修改中...
                    </>
                  ) : (
                    '修改密码'
                  )}
                </button>
              </form>
            </div>
          )}

          {/* Workspace Tab */}
          {activeTab === 'workspace' && (
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <h2 className="font-display text-lg font-semibold text-white mb-6">
                工作区设置
              </h2>

              {workspaceSuccess && (
                <div className="mb-6 p-4 bg-green-500/10 border border-green-500/50 rounded-lg text-green-400 text-sm flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  保存成功
                </div>
              )}

              <form onSubmit={handleWorkspaceSubmit} className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    工作区名称
                  </label>
                  <input
                    type="text"
                    value={workspaceName}
                    onChange={(e) => setWorkspaceName(e.target.value)}
                    className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="您的工作区名称"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    工作区 ID
                  </label>
                  <input
                    type="text"
                    value={workspace?.id || ''}
                    disabled
                    className="w-full px-4 py-3 bg-slate-700/30 border border-slate-600 rounded-lg text-slate-400 cursor-not-allowed font-mono text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    当前订阅
                  </label>
                  <div className="px-4 py-3 bg-slate-700/30 border border-slate-600 rounded-lg">
                    <span className="text-white font-medium">
                      {workspace?.subscription_plan === 'pro' ? 'Pro' :
                       workspace?.subscription_plan === 'enterprise' ? 'Enterprise' : 'Free'}
                    </span>
                    <span className="text-slate-400 ml-2">订阅</span>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSavingWorkspace}
                  className="bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/50 text-white px-6 py-2.5 rounded-lg font-medium transition-all flex items-center gap-2"
                >
                  {isSavingWorkspace ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      保存中...
                    </>
                  ) : (
                    '保存更改'
                  )}
                </button>
              </form>
            </div>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <h2 className="font-display text-lg font-semibold text-white mb-6">
                通知设置
              </h2>

              {notificationsSuccess && (
                <div className="mb-6 p-4 bg-green-500/10 border border-green-500/50 rounded-lg text-green-400 text-sm flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  保存成功
                </div>
              )}

              <form onSubmit={handleNotificationsSubmit} className="space-y-6">
                <div className="space-y-4">
                  <h3 className="text-sm font-medium text-slate-300">产品通知</h3>
                  
                  <label className="flex items-center justify-between p-4 bg-slate-700/30 rounded-lg cursor-pointer hover:bg-slate-700/40 transition-colors">
                    <div>
                      <div className="text-white font-medium">漂移预警</div>
                      <div className="text-sm text-slate-400">当引用来源或口径发生显著变化时通知我</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={notifications.drift_warning}
                      onChange={(e) => setNotifications((n) => ({ ...n, drift_warning: e.target.checked }))}
                      className="w-5 h-5 rounded border-slate-600 text-primary-500 focus:ring-primary-500 focus:ring-offset-0 bg-slate-700"
                    />
                  </label>

                  <label className="flex items-center justify-between p-4 bg-slate-700/30 rounded-lg cursor-pointer hover:bg-slate-700/40 transition-colors">
                    <div>
                      <div className="text-white font-medium">复测提醒</div>
                      <div className="text-sm text-slate-400">定期提醒进行复测以追踪变化</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={notifications.retest_reminder}
                      onChange={(e) => setNotifications((n) => ({ ...n, retest_reminder: e.target.checked }))}
                      className="w-5 h-5 rounded border-slate-600 text-primary-500 focus:ring-primary-500 focus:ring-offset-0 bg-slate-700"
                    />
                  </label>

                  <label className="flex items-center justify-between p-4 bg-slate-700/30 rounded-lg cursor-pointer hover:bg-slate-700/40 transition-colors">
                    <div>
                      <div className="text-white font-medium">每周摘要</div>
                      <div className="text-sm text-slate-400">每周发送 AI 可见性变化摘要邮件</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={notifications.weekly_digest}
                      onChange={(e) => setNotifications((n) => ({ ...n, weekly_digest: e.target.checked }))}
                      className="w-5 h-5 rounded border-slate-600 text-primary-500 focus:ring-primary-500 focus:ring-offset-0 bg-slate-700"
                    />
                  </label>
                </div>

                <div className="space-y-4">
                  <h3 className="text-sm font-medium text-slate-300">营销通知</h3>
                  
                  <label className="flex items-center justify-between p-4 bg-slate-700/30 rounded-lg cursor-pointer hover:bg-slate-700/40 transition-colors">
                    <div>
                      <div className="text-white font-medium">产品更新</div>
                      <div className="text-sm text-slate-400">新功能发布、行业洞察报告等</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={notifications.marketing}
                      onChange={(e) => setNotifications((n) => ({ ...n, marketing: e.target.checked }))}
                      className="w-5 h-5 rounded border-slate-600 text-primary-500 focus:ring-primary-500 focus:ring-offset-0 bg-slate-700"
                    />
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={isSavingNotifications}
                  className="bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/50 text-white px-6 py-2.5 rounded-lg font-medium transition-all flex items-center gap-2"
                >
                  {isSavingNotifications ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      保存中...
                    </>
                  ) : (
                    '保存设置'
                  )}
                </button>
              </form>
            </div>
          )}

          {/* API Tab */}
          {activeTab === 'api' && (
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
              <h2 className="font-display text-lg font-semibold text-white mb-2">
                API 密钥
              </h2>
              <p className="text-slate-400 text-sm mb-6">
                配置 AI 服务的 API 密钥以启用高级功能
              </p>

              <div className="space-y-6">
                <div className="p-4 bg-slate-700/30 rounded-lg border border-slate-600">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white">通义千问 API</span>
                      <span className="text-xs px-2 py-0.5 bg-slate-600 text-slate-300 rounded">
                        可选
                      </span>
                    </div>
                  </div>
                  <input
                    type="password"
                    placeholder="sk-xxxxxxxxxxxxxxxx"
                    className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
                  />
                  <p className="mt-2 text-xs text-slate-500">
                    提供您的通义千问 API 密钥以启用 AI 辅助分析功能
                  </p>
                </div>

                <div className="p-4 bg-slate-700/30 rounded-lg border border-slate-600">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white">OpenAI API</span>
                      <span className="text-xs px-2 py-0.5 bg-slate-600 text-slate-300 rounded">
                        可选
                      </span>
                    </div>
                  </div>
                  <input
                    type="password"
                    placeholder="sk-xxxxxxxxxxxxxxxx"
                    className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
                  />
                  <p className="mt-2 text-xs text-slate-500">
                    提供您的 OpenAI API 密钥以启用 GPT 模型辅助分析
                  </p>
                </div>

                <button className="bg-primary-500 hover:bg-primary-600 text-white px-6 py-2.5 rounded-lg font-medium transition-all">
                  保存密钥
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
