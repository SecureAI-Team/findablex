/**
 * Task Manager - handles task queue, persistence, error classification,
 * and exponential backoff for the extension.
 */

import { ExtTask, ExtResult, TaskStatus, ErrorCategory } from '../lib/types';
import { getPersistedTaskQueue, setPersistedTaskQueue } from '../lib/storage';

export interface ManagedTask {
  task: ExtTask;
  status: TaskStatus;
  startedAt: number;
  completedAt?: number;
  result?: ExtResult;
  retryCount: number;
  /** Exponential backoff: next retry time (Date.now() ms). */
  retryAfter?: number;
  /** Backoff delay in ms, doubles each retry. */
  retryDelayMs: number;
  /** Last error message. */
  lastError?: string;
  /** Error category for retry logic. */
  errorCategory?: ErrorCategory;
}

/**
 * Classify an error into a category that determines retry behavior.
 *
 * - retryable: network timeout, transient errors - will retry with backoff
 * - captcha: CAPTCHA detected - pause automation, notify user
 * - login_required: engine login expired - skip this engine
 * - skip: permanent error - don't retry
 */
export function classifyError(error: string): ErrorCategory {
  const lower = error.toLowerCase();

  // CAPTCHA-related
  if (
    lower.includes('captcha') ||
    lower.includes('recaptcha') ||
    lower.includes('hcaptcha') ||
    lower.includes('cloudflare') ||
    lower.includes('challenge') ||
    lower.includes('verify')
  ) {
    return 'captcha';
  }

  // Login required
  if (
    lower.includes('login') ||
    lower.includes('sign in') ||
    lower.includes('unauthorized') ||
    lower.includes('session expired') ||
    lower.includes('authentication')
  ) {
    return 'login_required';
  }

  // Retryable network/transient errors
  if (
    lower.includes('timeout') ||
    lower.includes('network') ||
    lower.includes('fetch') ||
    lower.includes('connection') ||
    lower.includes('econnreset') ||
    lower.includes('tab load') ||
    lower.includes('page not ready')
  ) {
    return 'retryable';
  }

  // Default: skip (permanent error)
  return 'skip';
}

const BASE_RETRY_DELAY_MS = 10_000; // 10 seconds
const MAX_RETRY_DELAY_MS = 300_000; // 5 minutes

class TaskManager {
  private queue: ManagedTask[] = [];
  private maxRetries = 3;
  private initialized = false;

  /**
   * Initialize from persisted storage.
   */
  async init(): Promise<void> {
    if (this.initialized) return;
    try {
      const persisted = await getPersistedTaskQueue();
      if (persisted && persisted.length > 0) {
        // Restore queue; reset any 'running' tasks back to 'pending'
        this.queue = persisted.map((t: ManagedTask) => ({
          ...t,
          status: t.status === 'running' ? 'pending' : t.status,
        }));
        console.log(`[FindableX] Restored ${this.queue.length} tasks from storage`);
      }
    } catch (err) {
      console.error('[FindableX] Failed to restore task queue:', err);
    }
    this.initialized = true;
  }

  /**
   * Persist current queue to storage.
   */
  private async persist(): Promise<void> {
    try {
      // Only persist active tasks (pending, running), limit size
      const toSave = this.queue.filter(
        (t) => t.status === 'pending' || t.status === 'running',
      );
      await setPersistedTaskQueue(toSave);
    } catch {
      // Non-critical
    }
  }

  /**
   * Add tasks to the queue (deduplicates by id).
   */
  async enqueue(tasks: ExtTask[]): Promise<void> {
    for (const task of tasks) {
      if (!this.queue.find((t) => t.task.id === task.id)) {
        this.queue.push({
          task,
          status: 'pending',
          startedAt: 0,
          retryCount: 0,
          retryDelayMs: BASE_RETRY_DELAY_MS,
        });
      }
    }
    await this.persist();
  }

  /**
   * Get next pending task that is ready to run (respects retryAfter).
   */
  getNextPending(): ManagedTask | null {
    const now = Date.now();
    return (
      this.queue.find(
        (t) =>
          t.status === 'pending' &&
          (!t.retryAfter || now >= t.retryAfter),
      ) || null
    );
  }

  /**
   * Get currently running tasks.
   */
  getRunning(): ManagedTask[] {
    return this.queue.filter((t) => t.status === 'running');
  }

  /**
   * Mark a task as running.
   */
  async markRunning(taskId: string): Promise<void> {
    const task = this.queue.find((t) => t.task.id === taskId);
    if (task) {
      task.status = 'running';
      task.startedAt = Date.now();
      await this.persist();
    }
  }

  /**
   * Mark a task as completed with result.
   */
  async markCompleted(taskId: string, result: ExtResult): Promise<void> {
    const task = this.queue.find((t) => t.task.id === taskId);
    if (task) {
      task.status = 'completed';
      task.completedAt = Date.now();
      task.result = result;
      await this.persist();
    }
  }

  /**
   * Mark a task as failed. Uses error classification + exponential backoff.
   * Returns: { retrying: boolean, category: ErrorCategory }
   */
  async markFailed(
    taskId: string,
    error: string,
  ): Promise<{ retrying: boolean; category: ErrorCategory }> {
    const task = this.queue.find((t) => t.task.id === taskId);
    if (!task) return { retrying: false, category: 'skip' };

    const category = classifyError(error);
    task.lastError = error;
    task.errorCategory = category;
    task.retryCount++;

    switch (category) {
      case 'captcha':
        // Pause -- don't retry automatically, user must solve
        task.status = 'failed';
        task.completedAt = Date.now();
        task.result = this.buildFailedResult(task, error);
        await this.persist();
        return { retrying: false, category };

      case 'login_required':
        // Skip -- don't retry, engine needs login
        task.status = 'failed';
        task.completedAt = Date.now();
        task.result = this.buildFailedResult(task, error);
        await this.persist();
        return { retrying: false, category };

      case 'retryable':
        if (task.retryCount <= this.maxRetries) {
          // Exponential backoff
          task.retryDelayMs = Math.min(
            task.retryDelayMs * 2,
            MAX_RETRY_DELAY_MS,
          );
          task.retryAfter = Date.now() + task.retryDelayMs;
          task.status = 'pending';
          await this.persist();
          return { retrying: true, category };
        }
        // Exhausted retries
        task.status = 'failed';
        task.completedAt = Date.now();
        task.result = this.buildFailedResult(task, error);
        await this.persist();
        return { retrying: false, category };

      case 'skip':
      default:
        task.status = 'failed';
        task.completedAt = Date.now();
        task.result = this.buildFailedResult(task, error);
        await this.persist();
        return { retrying: false, category };
    }
  }

  private buildFailedResult(task: ManagedTask, error: string): ExtResult {
    return {
      task_id: task.task.task_id,
      query_item_id: task.task.query_item_id,
      engine: task.task.engine,
      success: false,
      response_text: '',
      citations: [],
      error,
      response_time_ms: 0,
    };
  }

  /**
   * Get all completed results that haven't been submitted yet.
   */
  getUnsubmittedResults(): ExtResult[] {
    return this.queue
      .filter((t) => (t.status === 'completed' || t.status === 'failed') && t.result)
      .map((t) => t.result!);
  }

  /**
   * Remove submitted tasks from queue.
   */
  async removeSubmitted(taskIds: string[]): Promise<void> {
    this.queue = this.queue.filter(
      (t) =>
        !taskIds.includes(t.task.id) ||
        t.status === 'pending' ||
        t.status === 'running',
    );
    await this.persist();
  }

  /**
   * Clear all tasks.
   */
  async clear(): Promise<void> {
    this.queue = [];
    await this.persist();
  }

  /**
   * Get queue stats.
   */
  getStats(): {
    pending: number;
    running: number;
    completed: number;
    failed: number;
    total: number;
  } {
    const stats = {
      pending: 0,
      running: 0,
      completed: 0,
      failed: 0,
      total: this.queue.length,
    };
    for (const t of this.queue) {
      stats[t.status]++;
    }
    return stats;
  }

  /**
   * Check if there's capacity for more tasks.
   */
  hasCapacity(maxConcurrent: number): boolean {
    return this.getRunning().length < maxConcurrent;
  }
}

export const taskManager = new TaskManager();
