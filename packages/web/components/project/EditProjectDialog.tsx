'use client';

import { useState } from 'react';
import { X, Loader2, Save, Globe, FileText, Tag } from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Project {
  id: string;
  name: string;
  target_domains: string[];
  industry_template: string | null;
  description: string | null;
  status: string;
}

interface EditProjectDialogProps {
  project: Project;
  onSave: (updatedProject: Project) => void;
  onClose: () => void;
}

export default function EditProjectDialog({ project, onSave, onClose }: EditProjectDialogProps) {
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description || '');
  const [targetDomains, setTargetDomains] = useState(project.target_domains.join(', '));
  const [status, setStatus] = useState(project.status);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!name.trim()) {
      setError('项目名称不能为空');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const domains = targetDomains
        .split(/[,，\n]/)
        .map((d) => d.trim())
        .filter((d) => d.length > 0);

      const response = await api.put(`/projects/${project.id}`, {
        name: name.trim(),
        description: description.trim() || null,
        target_domains: domains.length > 0 ? domains : project.target_domains,
        status,
      });

      onSave(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || '保存失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Dialog */}
      <div className="relative bg-slate-800 rounded-xl border border-slate-700 shadow-2xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">编辑项目</h2>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Project Name */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-2">
              <Tag className="w-4 h-4" />
              项目名称
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="输入项目名称"
            />
          </div>

          {/* Description */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-2">
              <FileText className="w-4 h-4" />
              项目描述
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              placeholder="可选：描述项目目的和范围"
            />
          </div>

          {/* Target Domains */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-2">
              <Globe className="w-4 h-4" />
              目标域名
            </label>
            <textarea
              value={targetDomains}
              onChange={(e) => setTargetDomains(e.target.value)}
              rows={2}
              className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              placeholder="多个域名用逗号分隔，例如: apple.com, iphone.com"
            />
            <p className="text-xs text-slate-500 mt-1">多个域名用逗号或换行分隔</p>
          </div>

          {/* Status */}
          <div>
            <label className="text-sm font-medium text-slate-300 mb-2 block">项目状态</label>
            <div className="flex gap-3">
              <button
                onClick={() => setStatus('active')}
                className={cn(
                  'flex-1 px-4 py-2 rounded-lg border text-sm font-medium transition-colors',
                  status === 'active'
                    ? 'bg-green-500/20 border-green-500 text-green-400'
                    : 'bg-slate-700/30 border-slate-600 text-slate-400 hover:border-slate-500'
                )}
              >
                进行中
              </button>
              <button
                onClick={() => setStatus('paused')}
                className={cn(
                  'flex-1 px-4 py-2 rounded-lg border text-sm font-medium transition-colors',
                  status === 'paused'
                    ? 'bg-yellow-500/20 border-yellow-500 text-yellow-400'
                    : 'bg-slate-700/30 border-slate-600 text-slate-400 hover:border-slate-500'
                )}
              >
                已暂停
              </button>
              <button
                onClick={() => setStatus('completed')}
                className={cn(
                  'flex-1 px-4 py-2 rounded-lg border text-sm font-medium transition-colors',
                  status === 'completed'
                    ? 'bg-blue-500/20 border-blue-500 text-blue-400'
                    : 'bg-slate-700/30 border-slate-600 text-slate-400 hover:border-slate-500'
                )}
              >
                已完成
              </button>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-slate-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
            disabled={saving}
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                保存
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
