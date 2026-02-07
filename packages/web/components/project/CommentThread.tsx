'use client';

import { useEffect, useState, useRef } from 'react';
import {
  MessageCircle,
  Send,
  Loader2,
  MoreVertical,
  Trash2,
  Edit3,
  Reply,
  X,
  AtSign,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Comment {
  id: string;
  project_id: string;
  user_id: string;
  user_name: string | null;
  user_email: string | null;
  parent_id: string | null;
  content: string;
  target_type: string | null;
  target_id: string | null;
  mentions: string[] | null;
  is_edited: boolean;
  reply_count: number;
  created_at: string;
  updated_at: string | null;
}

interface CommentThreadProps {
  projectId: string;
  targetType?: string;
  targetId?: string;
}

export default function CommentThread({ projectId, targetType, targetId }: CommentThreadProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [newComment, setNewComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [replyTo, setReplyTo] = useState<Comment | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [expandedReplies, setExpandedReplies] = useState<Set<string>>(new Set());
  const [replies, setReplies] = useState<Record<string, Comment[]>>({});
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const fetchComments = async () => {
    try {
      const params: Record<string, any> = {};
      if (targetType && targetId) {
        params.target_type = targetType;
        params.target_id = targetId;
      }
      const res = await api.get(`/projects/${projectId}/comments`, { params });
      setComments(res.data);
    } catch (err) {
      console.error('Failed to fetch comments:', err);
      setComments([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchComments();
  }, [projectId, targetType, targetId]);

  const handleSubmit = async () => {
    if (!newComment.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const payload: any = {
        content: newComment.trim(),
        target_type: targetType || 'project',
        target_id: targetId || projectId,
      };
      if (replyTo) {
        payload.parent_id = replyTo.id;
      }
      const res = await api.post(`/projects/${projectId}/comments`, payload);

      if (replyTo) {
        setReplies((prev) => ({
          ...prev,
          [replyTo.id]: [res.data, ...(prev[replyTo.id] || [])],
        }));
        // Update reply count
        setComments((prev) =>
          prev.map((c) =>
            c.id === replyTo.id ? { ...c, reply_count: c.reply_count + 1 } : c
          )
        );
      } else {
        setComments((prev) => [res.data, ...prev]);
      }

      setNewComment('');
      setReplyTo(null);
    } catch (err) {
      console.error('Failed to create comment:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdate = async (commentId: string) => {
    if (!editContent.trim()) return;

    try {
      const res = await api.put(`/projects/${projectId}/comments/${commentId}`, {
        content: editContent.trim(),
      });

      setComments((prev) =>
        prev.map((c) => (c.id === commentId ? res.data : c))
      );

      // Also update in replies
      setReplies((prev) => {
        const updated = { ...prev };
        for (const key of Object.keys(updated)) {
          updated[key] = updated[key].map((c) =>
            c.id === commentId ? res.data : c
          );
        }
        return updated;
      });

      setEditingId(null);
      setEditContent('');
    } catch (err) {
      console.error('Failed to update comment:', err);
    }
  };

  const handleDelete = async (commentId: string) => {
    if (!confirm('确定要删除这条评论吗？')) return;

    try {
      await api.delete(`/projects/${projectId}/comments/${commentId}`);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
      setReplies((prev) => {
        const updated = { ...prev };
        for (const key of Object.keys(updated)) {
          updated[key] = updated[key].filter((c) => c.id !== commentId);
        }
        return updated;
      });
    } catch (err) {
      console.error('Failed to delete comment:', err);
    }
  };

  const loadReplies = async (parentId: string) => {
    if (expandedReplies.has(parentId)) {
      setExpandedReplies((prev) => {
        const next = new Set(prev);
        next.delete(parentId);
        return next;
      });
      return;
    }

    try {
      const res = await api.get(`/projects/${projectId}/comments`, {
        params: { parent_id: parentId },
      });
      setReplies((prev) => ({ ...prev, [parentId]: res.data }));
      setExpandedReplies((prev) => new Set(prev).add(parentId));
    } catch (err) {
      console.error('Failed to load replies:', err);
    }
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes} 分钟前`;
    if (hours < 24) return `${hours} 小时前`;
    if (days < 7) return `${days} 天前`;
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  };

  const getInitials = (name: string | null, email: string | null) => {
    if (name) return name.slice(0, 1).toUpperCase();
    if (email) return email.slice(0, 1).toUpperCase();
    return '?';
  };

  const renderComment = (comment: Comment, isReply = false) => (
    <div
      key={comment.id}
      className={cn(
        'group',
        isReply ? 'ml-10 mt-3' : 'py-4 border-b border-slate-700/30 last:border-0'
      )}
    >
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div className="w-8 h-8 rounded-full bg-primary-500/20 text-primary-400 flex items-center justify-center text-sm font-medium flex-shrink-0">
          {getInitials(comment.user_name, comment.user_email)}
        </div>

        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 text-sm">
            <span className="font-medium text-white">
              {comment.user_name || comment.user_email || '未知用户'}
            </span>
            <span className="text-slate-500 text-xs">
              {formatTime(comment.created_at)}
            </span>
            {comment.is_edited && (
              <span className="text-slate-600 text-xs">(已编辑)</span>
            )}
          </div>

          {/* Content */}
          {editingId === comment.id ? (
            <div className="mt-1.5 space-y-2">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white text-sm resize-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                rows={2}
              />
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleUpdate(comment.id)}
                  className="px-3 py-1 bg-primary-500 text-white rounded text-xs font-medium hover:bg-primary-600 transition-colors"
                >
                  保存
                </button>
                <button
                  onClick={() => {
                    setEditingId(null);
                    setEditContent('');
                  }}
                  className="px-3 py-1 text-slate-400 hover:text-white text-xs"
                >
                  取消
                </button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-300 mt-1 whitespace-pre-wrap break-words">
              {comment.content}
            </p>
          )}

          {/* Actions */}
          {editingId !== comment.id && (
            <div className="flex items-center gap-3 mt-2">
              {!isReply && (
                <button
                  onClick={() => {
                    setReplyTo(comment);
                    inputRef.current?.focus();
                  }}
                  className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-primary-400 transition-colors"
                >
                  <Reply className="w-3 h-3" />
                  回复
                </button>
              )}
              {comment.reply_count > 0 && !isReply && (
                <button
                  onClick={() => loadReplies(comment.id)}
                  className="text-xs text-primary-400 hover:text-primary-300 transition-colors"
                >
                  {expandedReplies.has(comment.id)
                    ? '收起回复'
                    : `${comment.reply_count} 条回复`}
                </button>
              )}

              {/* Menu */}
              <div className="relative ml-auto opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() =>
                    setOpenMenu(openMenu === comment.id ? null : comment.id)
                  }
                  className="p-1 text-slate-500 hover:text-white rounded transition-colors"
                >
                  <MoreVertical className="w-3.5 h-3.5" />
                </button>
                {openMenu === comment.id && (
                  <>
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setOpenMenu(null)}
                    />
                    <div className="absolute right-0 top-full mt-1 w-32 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-20 py-1">
                      <button
                        onClick={() => {
                          setEditingId(comment.id);
                          setEditContent(comment.content);
                          setOpenMenu(null);
                        }}
                        className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700 transition-colors"
                      >
                        <Edit3 className="w-3 h-3" />
                        编辑
                      </button>
                      <button
                        onClick={() => {
                          handleDelete(comment.id);
                          setOpenMenu(null);
                        }}
                        className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-red-400 hover:bg-slate-700 transition-colors"
                      >
                        <Trash2 className="w-3 h-3" />
                        删除
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Replies */}
          {expandedReplies.has(comment.id) &&
            replies[comment.id]?.map((reply) => renderComment(reply, true))}
        </div>
      </div>
    </div>
  );

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50">
      <div className="px-6 py-4 border-b border-slate-700/50 flex items-center gap-2">
        <MessageCircle className="w-5 h-5 text-primary-400" />
        <h3 className="font-display text-sm font-semibold text-white">
          讨论 ({comments.length})
        </h3>
      </div>

      {/* Comment Input */}
      <div className="px-6 py-4 border-b border-slate-700/30">
        {replyTo && (
          <div className="flex items-center gap-2 mb-2 px-3 py-1.5 bg-slate-700/30 rounded-lg">
            <Reply className="w-3.5 h-3.5 text-primary-400" />
            <span className="text-xs text-slate-400">
              回复 {replyTo.user_name || replyTo.user_email}
            </span>
            <button
              onClick={() => setReplyTo(null)}
              className="ml-auto text-slate-500 hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
        <div className="flex items-end gap-3">
          <textarea
            ref={inputRef}
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                handleSubmit();
              }
            }}
            placeholder={replyTo ? '输入回复...' : '输入评论... (Ctrl+Enter 发送)'}
            className="flex-1 px-3 py-2 bg-slate-700/30 border border-slate-600/50 rounded-lg text-white text-sm placeholder-slate-500 resize-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 min-h-[40px] max-h-[120px]"
            rows={1}
          />
          <button
            onClick={handleSubmit}
            disabled={!newComment.trim() || isSubmitting}
            className="flex-shrink-0 p-2.5 bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/30 text-white rounded-lg transition-colors"
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Comments List */}
      <div className="px-6">
        {isLoading ? (
          <div className="py-8 flex items-center justify-center">
            <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
          </div>
        ) : comments.length === 0 ? (
          <div className="py-8 text-center">
            <MessageCircle className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-sm text-slate-400">暂无评论，来说点什么吧</p>
          </div>
        ) : (
          comments.map((comment) => renderComment(comment))
        )}
      </div>
    </div>
  );
}
