/**
 * Shared TypeScript types for FindableX
 */

// User types
export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

// Workspace types
export interface Workspace {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  settings: Record<string, any>;
  research_opt_in: boolean;
  created_at: string;
}

export interface Membership {
  id: string;
  user_id: string;
  workspace_id: string;
  role: Role;
  created_at: string;
}

export type Role = 'super_admin' | 'admin' | 'analyst' | 'researcher' | 'viewer';

// Project types
export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  industry_template: string | null;
  target_domains: string[];
  settings: Record<string, any>;
  status: string;
  created_by: string;
  created_at: string;
}

export interface QueryItem {
  id: string;
  project_id: string;
  query_text: string;
  query_type: QueryIntent | null;
  intent_category: string | null;
  metadata: Record<string, any>;
  position: number;
  created_at: string;
}

export type QueryIntent = 
  | 'informational'
  | 'navigational'
  | 'transactional'
  | 'commercial'
  | 'local';

// Run types
export interface Run {
  id: string;
  project_id: string;
  run_number: number;
  run_type: RunType;
  input_method: string;
  template_version: string;
  engine_version: string | null;
  parameters: Record<string, any>;
  region: string | null;
  language: string | null;
  status: RunStatus;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  total_queries: number;
  processed_queries: number;
  summary_metrics: Record<string, any>;
  created_by: string;
  created_at: string;
}

export type RunType = 'checkup' | 'retest' | 'experiment';
export type RunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

// Citation types
export interface Citation {
  id: string;
  run_id: string;
  query_item_id: string;
  position: number;
  source_url: string | null;
  source_domain: string | null;
  source_title: string | null;
  snippet: string | null;
  is_target_domain: boolean;
  relevance_score: number | null;
  extracted_at: string;
}

// Metric types
export interface Metric {
  id: string;
  run_id: string;
  query_item_id: string | null;
  metric_type: MetricType;
  metric_value: number;
  metric_details: Record<string, any> | null;
  calculated_at: string;
}

export type MetricType =
  | 'visibility_rate'
  | 'avg_citation_position'
  | 'citation_count'
  | 'top3_rate'
  | 'competitor_share'
  | 'health_score';

// Report types
export interface Report {
  id: string;
  run_id: string;
  report_type: string;
  title: string;
  content_html: string | null;
  content_json: Record<string, any>;
  generated_at: string;
  expires_at: string | null;
}

export interface ShareLink {
  id: string;
  report_id: string;
  token: string;
  view_count: number;
  max_views: number | null;
  expires_at: string | null;
  created_at: string;
  share_url: string;
}

// Drift types
export interface DriftEvent {
  id: string;
  project_id: string;
  baseline_run_id: string;
  compare_run_id: string;
  drift_type: DriftType;
  severity: DriftSeverity;
  affected_queries: string[];
  metric_name: string;
  baseline_value: number;
  current_value: number;
  change_percent: number;
  detected_at: string;
  acknowledged_at: string | null;
}

export type DriftType = 'position_drop' | 'visibility_loss' | 'new_competitor';
export type DriftSeverity = 'critical' | 'warning' | 'info';

// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Token {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
}
