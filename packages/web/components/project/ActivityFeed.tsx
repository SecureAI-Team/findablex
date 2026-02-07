'use client';

import { useEffect, useState } from 'react';
import {
  Activity,
  Play,
  CheckCircle,
  AlertTriangle,
  MessageCircle,
  UserPlus,
  Zap,
  BarChart3,
  Clock,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface ActivityEvent {
  id: string;
  project_id: string;
  user_id: string | null;
  user_name: string | null;
  event_type: string;
  summary: string;
  metadata_json: Record<string, any> | null;
  created_at: string;
}

interface ActivityFeedProps {
  projectId: string;
}

const eventTypeConfig: Record<
  string,
  { icon: any; color: string; bgColor: string }
> = {
  run_started: {
    icon: Play,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
  },
  run_completed: {
    icon: CheckCircle,
    color: 'text-green-400',
    bgColor: 'bg-green-500/10',
  },
  checkup_triggered: {
    icon: Zap,
    color: 'text-primary-400',
    bgColor: 'bg-primary-500/10',
  },
  drift_detected: {
    icon: AlertTriangle,
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
  },
  comment_added: {
    icon: MessageCircle,
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-500/10',
  },
  member_joined: {
    icon: UserPlus,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
  },
  project_created: {
    icon: BarChart3,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10',
  },
  report_generated: {
    icon: BarChart3,
    color: 'text-indigo-400',
    bgColor: 'bg-indigo-500/10',
  },
};

const defaultConfig = {
  icon: Activity,
  color: 'text-slate-400',
  bgColor: 'bg-slate-500/10',
};

export default function ActivityFeed({ projectId }: ActivityFeedProps) {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchActivity = async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    else setIsRefreshing(true);

    try {
      const res = await api.get(`/projects/${projectId}/activity`, {
        params: { limit: 30 },
      });
      setEvents(res.data);
    } catch (err) {
      console.error('Failed to fetch activity:', err);
      setEvents([]);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchActivity();
  }, [projectId]);

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
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Group events by date
  const groupedEvents: Record<string, ActivityEvent[]> = {};
  for (const event of events) {
    const dateKey = new Date(event.created_at).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
    if (!groupedEvents[dateKey]) {
      groupedEvents[dateKey] = [];
    }
    groupedEvents[dateKey].push(event);
  }

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50">
      <div className="px-6 py-4 border-b border-slate-700/50 flex items-center justify-between">
        <h3 className="font-display text-sm font-semibold text-white flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary-400" />
          活动记录
        </h3>
        <button
          onClick={() => fetchActivity(false)}
          disabled={isRefreshing}
          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-colors"
          title="刷新"
        >
          <RefreshCw
            className={cn('w-4 h-4', isRefreshing && 'animate-spin')}
          />
        </button>
      </div>

      <div className="px-6 py-4">
        {isLoading ? (
          <div className="py-8 flex items-center justify-center">
            <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
          </div>
        ) : events.length === 0 ? (
          <div className="py-8 text-center">
            <Activity className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-sm text-slate-400">暂无活动记录</p>
            <p className="text-xs text-slate-500 mt-1">
              项目活动（体检、评论、变化检测等）会显示在这里
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(groupedEvents).map(([dateLabel, dayEvents]) => (
              <div key={dateLabel}>
                <div className="text-xs font-medium text-slate-500 mb-3">
                  {dateLabel}
                </div>
                <div className="relative">
                  {/* Timeline line */}
                  <div className="absolute left-4 top-0 bottom-0 w-px bg-slate-700/50" />

                  <div className="space-y-4">
                    {dayEvents.map((event) => {
                      const config =
                        eventTypeConfig[event.event_type] || defaultConfig;
                      const Icon = config.icon;

                      return (
                        <div
                          key={event.id}
                          className="relative flex items-start gap-4 group"
                        >
                          {/* Icon */}
                          <div
                            className={cn(
                              'relative z-10 w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                              config.bgColor
                            )}
                          >
                            <Icon className={cn('w-4 h-4', config.color)} />
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0 pt-0.5">
                            <p className="text-sm text-slate-300">
                              {event.user_name && (
                                <span className="text-white font-medium">
                                  {event.user_name}{' '}
                                </span>
                              )}
                              {event.summary}
                            </p>
                            <p className="text-xs text-slate-500 mt-0.5">
                              {formatTime(event.created_at)}
                            </p>

                            {/* Metadata chips */}
                            {event.metadata_json && (
                              <div className="flex flex-wrap gap-1.5 mt-1.5">
                                {event.metadata_json.engine && (
                                  <span className="px-2 py-0.5 bg-slate-700/50 text-slate-400 rounded text-[10px]">
                                    {event.metadata_json.engine}
                                  </span>
                                )}
                                {event.metadata_json.score !== undefined && (
                                  <span className="px-2 py-0.5 bg-slate-700/50 text-slate-400 rounded text-[10px]">
                                    评分: {event.metadata_json.score}
                                  </span>
                                )}
                                {event.metadata_json.severity && (
                                  <span
                                    className={cn(
                                      'px-2 py-0.5 rounded text-[10px]',
                                      event.metadata_json.severity === 'critical'
                                        ? 'bg-red-500/10 text-red-400'
                                        : 'bg-amber-500/10 text-amber-400'
                                    )}
                                  >
                                    {event.metadata_json.severity}
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
