/**
 * FindableX Extension - Service Worker (Background Script)
 *
 * Core orchestration: polls for tasks, dispatches to tabs,
 * collects results, and submits to server.
 *
 * Features:
 * - Persists mode across restarts (uses storage, not in-memory)
 * - Uses chrome.alarms exclusively (no setTimeout for long waits)
 * - Context menu for manual capture
 * - Badge icon for status indication
 * - webextension-polyfill for cross-browser
 */

import browser from 'webextension-polyfill';
import { api } from '../lib/api';
import { getToken, getSettings, setState, updateStats, getState } from '../lib/storage';
import { ExtTask, ExtResult, ExtensionMode, ExtMessage } from '../lib/types';
import { taskManager } from './task-manager';
import { getOrCreateEngineTab, executeTaskInTab, closeEngineTab, closeAllCrawlTabs, cleanupTabs } from './tab-controller';
import { getBrowserName } from '../lib/browser-detect';

// ============ Alarm Names ============
const ALARM_POLL = 'findablex-poll';
const ALARM_HEARTBEAT = 'findablex-heartbeat';
const ALARM_SUBMIT = 'findablex-submit';
const ALARM_PROCESS = 'findablex-process-next';

// ============ State (persisted via storage) ============
let isProcessing = false;

/**
 * Get the current mode from persisted state.
 */
async function getCurrentMode(): Promise<ExtensionMode> {
  const state = await getState();
  return state.mode || 'idle';
}

/**
 * Set the mode and persist it.
 */
async function setCurrentMode(mode: ExtensionMode): Promise<void> {
  await setState({ mode });
}

// ============ Badge / Icon Status ============

function setBadgeStatus(status: 'active' | 'idle' | 'error'): void {
  const colors: Record<string, string> = {
    active: '#22c55e',  // green
    idle: '#64748b',    // gray
    error: '#ef4444',   // red
  };
  const texts: Record<string, string> = {
    active: 'ON',
    idle: '',
    error: '!',
  };

  try {
    browser.action.setBadgeBackgroundColor({ color: colors[status] });
    browser.action.setBadgeText({ text: texts[status] });
  } catch {
    // browser.action might not be available in all contexts
  }
}

// ============ Initialization ============

browser.runtime.onInstalled.addListener(async () => {
  console.log('[FindableX] Extension installed');
  await setState({
    isAuthenticated: false,
    mode: 'idle',
    isPolling: false,
    activeTaskId: null,
    stats: { completed: 0, failed: 0, totalToday: 0 },
  });
  setBadgeStatus('idle');

  // Create context menu for manual capture
  setupContextMenu();
});

// Restore state on service worker startup (e.g., after browser restart)
browser.runtime.onStartup.addListener(async () => {
  console.log('[FindableX] Service worker starting up');
  await taskManager.init();

  const mode = await getCurrentMode();
  if (mode === 'auto') {
    const token = await getToken();
    if (token) {
      console.log('[FindableX] Resuming auto mode after restart');
      await startAutoMode();
    } else {
      await setCurrentMode('idle');
      setBadgeStatus('idle');
    }
  }

  // Re-register context menu
  setupContextMenu();
});

// Also initialize task manager on any activation
(async () => {
  await taskManager.init();
})();

// ============ Context Menu ============

function setupContextMenu(): void {
  try {
    browser.contextMenus.removeAll().then(() => {
      browser.contextMenus.create({
        id: 'findablex-capture',
        title: '捕获当前 AI 对话 (FindableX)',
        contexts: ['page'],
        documentUrlPatterns: [
          'https://chat.deepseek.com/*',
          'https://kimi.moonshot.cn/*',
          'https://tongyi.aliyun.com/*',
          'https://chatgpt.com/*',
          'https://www.perplexity.ai/*',
          'https://www.doubao.com/*',
          'https://chatglm.cn/*',
          'https://www.google.com/*',
          'https://www.bing.com/*',
        ],
      });
    });
  } catch {
    // contextMenus API might not be available
  }
}

// Context menu click handler
try {
  browser.contextMenus.onClicked.addListener(async (info, tab) => {
    if (info.menuItemId === 'findablex-capture' && tab?.id) {
      try {
        const response = await browser.tabs.sendMessage(tab.id, {
          type: 'CAPTURE_PAGE',
          payload: {},
        });
        if (response && (response as any).type === 'CAPTURE_RESULT') {
          const payload = (response as any).payload;
          if (payload.success) {
            // Show notification instead of alert
            try {
              await browser.notifications.create('capture-success', {
                type: 'basic',
                iconUrl: browser.runtime.getURL('icons/icon-48.png'),
                title: 'FindableX',
                message: `捕获成功！提取了 ${payload.citations?.length || 0} 个引用`,
              });
            } catch {
              // notifications API might not be available
            }
          }
        }
      } catch {
        // Content script not available on this page
      }
    }
  });
} catch {
  // contextMenus not available
}

// ============ Alarm Handlers ============

browser.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === ALARM_POLL) {
    await pollTasks();
  } else if (alarm.name === ALARM_HEARTBEAT) {
    await sendHeartbeat();
  } else if (alarm.name === ALARM_SUBMIT) {
    await submitPendingResults();
  } else if (alarm.name === ALARM_PROCESS) {
    await processNextTask();
  }
});

// ============ Message Handler (from Popup & Content Scripts) ============

browser.runtime.onMessage.addListener((message: ExtMessage, sender) => {
  // Return a promise for async handling
  return handleMessage(message, sender);
});

async function handleMessage(
  message: ExtMessage,
  _sender: browser.Runtime.MessageSender,
): Promise<any> {
  switch (message.type) {
    case 'GET_STATUS': {
      const state = await getState();
      const stats = taskManager.getStats();
      const mode = await getCurrentMode();
      return {
        ...state,
        mode,
        queueStats: stats,
      };
    }

    case 'STATUS_UPDATE': {
      const { mode } = message.payload || {};
      if (mode === 'auto') {
        await startAutoMode();
      } else if (mode === 'idle') {
        await stopAutoMode();
      }
      const currentMode = await getCurrentMode();
      return { mode: currentMode };
    }

    case 'CAPTURE_PAGE': {
      return { status: 'ok', message: 'Use context menu on AI chat pages' };
    }

    case 'TASK_RESULT': {
      const result = message.payload as ExtResult;
      if (result) {
        await taskManager.markCompleted(
          `${result.task_id}_${result.query_item_id}`,
          result,
        );
        await submitPendingResults();
      }
      return { status: 'ok' };
    }

    case 'PING':
      return { status: 'alive', mode: await getCurrentMode() };

    default:
      return { error: 'Unknown message type' };
  }
}

// ============ Auto Mode ============

async function startAutoMode(): Promise<void> {
  await setCurrentMode('auto');
  await setState({ mode: 'auto', isPolling: true });
  setBadgeStatus('active');

  // Start polling alarm
  const settings = await getSettings();
  const intervalMinutes = Math.max(settings.pollIntervalMs / 60000, 0.1);
  await browser.alarms.create(ALARM_POLL, { periodInMinutes: intervalMinutes });

  // Heartbeat every 5 minutes
  await browser.alarms.create(ALARM_HEARTBEAT, { periodInMinutes: 5 });

  // Result submission check every 30 seconds
  await browser.alarms.create(ALARM_SUBMIT, { periodInMinutes: 0.5 });

  // Do an immediate poll
  await pollTasks();

  console.log('[FindableX] Auto mode started');
}

async function stopAutoMode(): Promise<void> {
  await setCurrentMode('idle');
  await setState({ mode: 'idle', isPolling: false, activeTaskId: null });
  setBadgeStatus('idle');

  await browser.alarms.clear(ALARM_POLL);
  await browser.alarms.clear(ALARM_HEARTBEAT);
  await browser.alarms.clear(ALARM_SUBMIT);
  await browser.alarms.clear(ALARM_PROCESS);

  // Submit any remaining results
  await submitPendingResults();

  // Close all crawl tabs
  await closeAllCrawlTabs();

  console.log('[FindableX] Auto mode stopped');
}

// ============ Task Polling ============

async function pollTasks(): Promise<void> {
  const token = await getToken();
  if (!token) {
    console.log('[FindableX] Not authenticated, skipping poll');
    return;
  }

  try {
    const { tasks } = await api.getExtensionTasks();

    if (tasks.length > 0) {
      console.log(`[FindableX] Got ${tasks.length} tasks`);
      await taskManager.enqueue(tasks);
      await processNextTask();
    }
  } catch (err: any) {
    console.error('[FindableX] Poll error:', err.message);
    if (err.message === 'Authentication expired') {
      await stopAutoMode();
      await setState({ isAuthenticated: false });
    }
  }
}

// ============ Task Processing ============

async function processNextTask(): Promise<void> {
  if (isProcessing) return;

  const settings = await getSettings();
  if (!taskManager.hasCapacity(settings.maxConcurrentTabs)) return;

  const managed = taskManager.getNextPending();
  if (!managed) return;

  isProcessing = true;
  const task = managed.task;

  try {
    await taskManager.markRunning(task.id);
    await setState({ activeTaskId: task.id });
    console.log(
      `[FindableX] Processing task: ${task.engine} - "${task.query_text.substring(0, 50)}..."`,
    );

    // Get or create tab for the engine
    const tab = await getOrCreateEngineTab(task.engine);
    if (!tab.id) throw new Error('Failed to get tab');

    // Execute task in the tab's content script
    const result = await executeTaskInTab(tab.id, task);

    // Mark completed
    await taskManager.markCompleted(task.id, result);

    // Close tab after use
    await closeEngineTab(task.engine);

    // Update stats
    if (result.success) {
      const state = await getState();
      await updateStats({
        completed: state.stats.completed + 1,
        totalToday: state.stats.totalToday + 1,
      });
    } else {
      const state = await getState();
      await updateStats({
        failed: state.stats.failed + 1,
        totalToday: state.stats.totalToday + 1,
      });
    }

    console.log(
      `[FindableX] Task ${result.success ? 'completed' : 'failed'}: ${task.id}`,
    );

    // Submit results immediately
    await submitPendingResults();

  } catch (err: any) {
    console.error(`[FindableX] Task error:`, err.message);
    const { retrying, category } = await taskManager.markFailed(task.id, err.message);

    if (category === 'captcha') {
      // Notify user about CAPTCHA
      try {
        await browser.notifications.create('captcha-detected', {
          type: 'basic',
          iconUrl: browser.runtime.getURL('icons/icon-48.png'),
          title: 'FindableX - 需要验证',
          message: `${task.engine} 需要人机验证，请手动完成后继续`,
        });
      } catch {
        // notifications not available
      }
    }

    if (!retrying) {
      const state = await getState();
      await updateStats({
        failed: state.stats.failed + 1,
        totalToday: state.stats.totalToday + 1,
      });
    }
  } finally {
    isProcessing = false;
    await setState({ activeTaskId: null });

    // Schedule next task processing via alarm instead of direct recursion
    const mode = await getCurrentMode();
    if (mode === 'auto') {
      const settings = await getSettings();
      // Use alarm for delay (service worker safe)
      await browser.alarms.create(ALARM_PROCESS, {
        delayInMinutes: settings.queryDelayMs / 60000,
      });
    }
  }
}

// ============ Result Submission ============

async function submitPendingResults(): Promise<void> {
  const results = taskManager.getUnsubmittedResults();
  if (results.length === 0) return;

  try {
    const response = await api.submitExtensionResults(results);
    console.log(`[FindableX] Submitted ${response.saved} results`);

    // Remove submitted tasks from queue
    const submittedIds = results.map(
      (r) => `${r.task_id}_${r.query_item_id}`,
    );
    await taskManager.removeSubmitted(submittedIds);
  } catch (err: any) {
    console.error('[FindableX] Submit error:', err.message);
  }
}

// ============ Heartbeat ============

async function sendHeartbeat(): Promise<void> {
  try {
    const manifest = browser.runtime.getManifest();
    const mode = await getCurrentMode();
    await api.sendHeartbeat({
      version: manifest.version,
      browser: getBrowserName(),
      active_engines: taskManager.getRunning().map((t) => t.task.engine),
      mode,
    });
  } catch {
    // Non-critical
  }
}

// ============ Tab Cleanup ============

browser.tabs.onRemoved.addListener((_tabId) => {
  cleanupTabs();
});
