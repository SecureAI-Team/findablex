/**
 * 前端埋点服务
 * 
 * 用于追踪用户行为和产品使用情况
 */

import { api } from './api';

// 事件类型定义
export type EventCategory = 'activation' | 'value' | 'conversion' | 'retention';

export interface TrackEventOptions {
  userId?: string;
  workspaceId?: string;
  properties?: Record<string, unknown>;
}

// 事件名称常量
export const EVENTS = {
  // 激活事件
  USER_REGISTERED: 'user_registered',
  TEMPLATE_SELECTED: 'template_selected',
  QUERIES_GENERATED: 'queries_generated',
  FIRST_ANSWER_IMPORTED: 'first_answer_imported',
  FIRST_CRAWL_COMPLETED: 'first_crawl_completed',
  FIRST_REPORT_VIEWED: 'first_report_viewed',
  ACTIVATION_10MIN: 'activation_10min',
  
  // 价值事件
  REPORT_VIEWED: 'report_viewed',
  REPORT_DWELL_TIME: 'report_dwell_time',
  REPORT_EXPORTED: 'report_exported',
  REPORT_SHARED: 'report_shared',
  CALIBRATION_ERROR_CLICKED: 'calibration_error_clicked',
  CALIBRATION_REVIEWED: 'calibration_reviewed',
  COMPARE_REPORT_VIEWED: 'compare_report_viewed',
  
  // 转化事件
  UPGRADE_CLICKED: 'upgrade_clicked',
  UNLOCK_QUERIES_CLICKED: 'unlock_queries_clicked',
  RETEST_COMPARE_CLICKED: 'retest_compare_clicked',
  DRIFT_WARNING_CLICKED: 'drift_warning_clicked',
  PLAN_VIEWED: 'plan_viewed',
  CONTACT_SALES_CLICKED: 'contact_sales_clicked',
  PAYMENT_INITIATED: 'payment_initiated',
  
  // 留存事件
  RETEST_TRIGGERED: 'retest_triggered',
  MONTHLY_RETEST: 'monthly_retest',
  TEAM_MEMBER_INVITED: 'team_member_invited',
  TEAM_MEMBER_JOINED: 'team_member_joined',
  PROJECT_CREATED: 'project_created',
  LOGIN: 'login',
} as const;

class Analytics {
  private queue: Array<{ event: string; options?: TrackEventOptions }> = [];
  private isProcessing = false;

  /**
   * 追踪事件
   */
  async track(event: string, options?: TrackEventOptions): Promise<void> {
    // 添加到队列
    this.queue.push({ event, options });
    
    // 处理队列
    this.processQueue();
  }

  /**
   * 处理事件队列
   */
  private async processQueue(): Promise<void> {
    if (this.isProcessing || this.queue.length === 0) return;
    
    this.isProcessing = true;
    
    while (this.queue.length > 0) {
      const item = this.queue.shift();
      if (!item) continue;
      
      try {
        await this.sendEvent(item.event, item.options);
      } catch (error) {
        // 静默失败，不影响用户体验
        console.warn('Analytics event failed:', error);
      }
    }
    
    this.isProcessing = false;
  }

  /**
   * 发送事件到后端
   */
  private async sendEvent(event: string, options?: TrackEventOptions): Promise<void> {
    try {
      await api.post('/analytics/track', {
        event_type: event,
        properties: {
          ...options?.properties,
          // 自动添加的属性
          page_url: typeof window !== 'undefined' ? window.location.href : undefined,
          referrer: typeof document !== 'undefined' ? document.referrer : undefined,
          user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
          timestamp: new Date().toISOString(),
        },
      });
    } catch {
      // 如果API调用失败，可以考虑存储到localStorage后续重试
      // 这里简单忽略
    }
  }

  // ========== 便捷方法 ==========

  /**
   * 追踪页面浏览
   */
  trackPageView(pageName: string, properties?: Record<string, unknown>): void {
    this.track('page_view', {
      properties: {
        page_name: pageName,
        ...properties,
      },
    });
  }

  /**
   * 追踪用户注册
   */
  trackRegistration(properties?: Record<string, unknown>): void {
    this.track(EVENTS.USER_REGISTERED, { properties });
  }

  /**
   * 追踪模板选择
   */
  trackTemplateSelected(templateId: string, templateName: string): void {
    this.track(EVENTS.TEMPLATE_SELECTED, {
      properties: { template_id: templateId, template_name: templateName },
    });
  }

  /**
   * 追踪报告查看
   */
  trackReportViewed(reportId: string, reportType: string): void {
    this.track(EVENTS.REPORT_VIEWED, {
      properties: { report_id: reportId, report_type: reportType },
    });
  }

  /**
   * 追踪报告导出
   */
  trackReportExported(reportId: string, format: string): void {
    this.track(EVENTS.REPORT_EXPORTED, {
      properties: { report_id: reportId, format },
    });
  }

  /**
   * 追踪升级点击
   */
  trackUpgradeClicked(source: string, currentPlan?: string): void {
    this.track(EVENTS.UPGRADE_CLICKED, {
      properties: { source, current_plan: currentPlan },
    });
  }

  /**
   * 追踪联系销售
   */
  trackContactSalesClicked(source: string): void {
    this.track(EVENTS.CONTACT_SALES_CLICKED, {
      properties: { source },
    });
  }

  /**
   * 追踪项目创建
   */
  trackProjectCreated(projectId: string, industry?: string): void {
    this.track(EVENTS.PROJECT_CREATED, {
      properties: { project_id: projectId, industry },
    });
  }

  /**
   * 追踪复测触发
   */
  trackRetestTriggered(projectId: string): void {
    this.track(EVENTS.RETEST_TRIGGERED, {
      properties: { project_id: projectId },
    });
  }

  /**
   * 追踪导入
   */
  trackFirstAnswerImported(projectId: string, count: number, engine: string): void {
    this.track(EVENTS.FIRST_ANSWER_IMPORTED, {
      properties: { project_id: projectId, count, engine },
    });
  }

  /**
   * 追踪报告分享
   */
  trackReportShared(reportId: string): void {
    this.track(EVENTS.REPORT_SHARED, {
      properties: { report_id: reportId },
    });
  }

  /**
   * 追踪登录
   */
  trackLogin(): void {
    this.track(EVENTS.LOGIN);
  }

  /**
   * 追踪查询生成
   */
  trackQueriesGenerated(projectId: string, count: number, templateId?: string): void {
    this.track(EVENTS.QUERIES_GENERATED, {
      properties: { project_id: projectId, count, template_id: templateId },
    });
  }

  /**
   * 追踪团队成员邀请
   */
  trackTeamMemberInvited(workspaceId: string): void {
    this.track(EVENTS.TEAM_MEMBER_INVITED, {
      properties: { workspace_id: workspaceId },
    });
  }
}

// 导出单例
export const analytics = new Analytics();

// 导出默认值供便捷使用
export default analytics;
