/**
 * Shared constants for FindableX
 */

export const INDUSTRY_TEMPLATES = {
  healthcare: {
    name: '医疗健康',
    description: '医疗机构、健康服务、医药品牌',
  },
  finance: {
    name: '金融服务',
    description: '银行、保险、投资理财',
  },
  legal: {
    name: '法律服务',
    description: '律师事务所、法律咨询',
  },
  education: {
    name: '教育培训',
    description: '学校、培训机构、在线教育',
  },
  tech: {
    name: '科技互联网',
    description: '软件服务、科技产品',
  },
  retail: {
    name: '零售电商',
    description: '电商平台、零售品牌',
  },
} as const;

export const METRIC_LABELS = {
  visibility_rate: '可见性覆盖率',
  avg_citation_position: '平均引用位置',
  citation_count: '引用总数',
  top3_rate: 'Top3 出现率',
  competitor_share: '竞争对手占比',
  health_score: '健康度评分',
} as const;

export const RUN_STATUS_LABELS = {
  pending: '等待中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
} as const;

export const RUN_TYPE_LABELS = {
  checkup: '体检',
  retest: '复测',
  experiment: '实验',
} as const;

export const ROLE_LABELS = {
  super_admin: '超级管理员',
  admin: '管理员',
  analyst: '分析师',
  researcher: '研究员',
  viewer: '观察者',
} as const;

export const DRIFT_SEVERITY_COLORS = {
  critical: 'red',
  warning: 'yellow',
  info: 'blue',
} as const;

export const HEALTH_SCORE_THRESHOLDS = {
  excellent: 80,
  good: 60,
  fair: 40,
} as const;

export function getHealthScoreStatus(score: number): 'excellent' | 'good' | 'fair' | 'poor' {
  if (score >= HEALTH_SCORE_THRESHOLDS.excellent) return 'excellent';
  if (score >= HEALTH_SCORE_THRESHOLDS.good) return 'good';
  if (score >= HEALTH_SCORE_THRESHOLDS.fair) return 'fair';
  return 'poor';
}

export function getHealthScoreColor(score: number): string {
  const status = getHealthScoreStatus(score);
  switch (status) {
    case 'excellent':
      return 'green';
    case 'good':
      return 'blue';
    case 'fair':
      return 'yellow';
    case 'poor':
      return 'red';
  }
}
