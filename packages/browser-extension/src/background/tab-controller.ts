/**
 * Tab Controller - manages browser tabs for invisible crawling.
 *
 * Uses minimized windows or collapsed tab groups to hide automation.
 * Checks for user-active tabs to avoid interfering with the user.
 * Uses webextension-polyfill for cross-browser compatibility.
 */

import browser from 'webextension-polyfill';
import { ENGINE_URL_PATTERNS, ENGINE_NEW_CHAT_URLS } from '../lib/constants';
import { ExtTask, ExtResult, ExecuteTaskMessage, TaskResultMessage } from '../lib/types';
import { supportsTabGroups, supportsMinimizedWindows } from '../lib/browser-detect';

/** Map of engine -> tab ID for reuse */
const engineTabs: Map<string, number> = new Map();

/** ID of the minimized window used for crawl tabs */
let crawlWindowId: number | null = null;

/** ID of the tab group for crawl tabs (Chrome only) */
let crawlTabGroupId: number | null = null;

/**
 * Check if a tab is currently being actively used by the user.
 * We consider a tab "user-active" if it is the focused tab in the focused window.
 */
async function isTabActiveByUser(tabId: number): Promise<boolean> {
  try {
    const tab = await browser.tabs.get(tabId);
    if (!tab.active) return false;

    // Check if its window is focused
    if (tab.windowId !== undefined) {
      const win = await browser.windows.get(tab.windowId);
      return win.focused === true;
    }
    return false;
  } catch {
    return false;
  }
}

/**
 * Get or create a minimized window for crawl tabs.
 */
async function getOrCreateCrawlWindow(): Promise<number> {
  // Check if existing crawl window is still valid
  if (crawlWindowId !== null) {
    try {
      const win = await browser.windows.get(crawlWindowId);
      if (win) return crawlWindowId;
    } catch {
      crawlWindowId = null;
    }
  }

  // Create a new minimized window
  if (supportsMinimizedWindows()) {
    try {
      const win = await browser.windows.create({
        url: 'about:blank',
        state: 'minimized',
        focused: false,
      });
      if (win.id) {
        crawlWindowId = win.id;
        return crawlWindowId;
      }
    } catch {
      // Fall through to return -1
    }
  }

  return -1; // Signal that minimized window is not available
}

/**
 * Group a tab into the FindableX crawl tab group (Chrome only).
 */
async function groupCrawlTab(tabId: number): Promise<void> {
  if (!supportsTabGroups()) return;

  try {
    // Use chrome.tabs.group directly as polyfill doesn't cover tabGroups
    const groupId = await (chrome.tabs as any).group({
      tabIds: [tabId],
      ...(crawlTabGroupId ? { groupId: crawlTabGroupId } : {}),
    });

    if (!crawlTabGroupId && groupId) {
      crawlTabGroupId = groupId;
      // Collapse and name the group
      try {
        await (chrome.tabGroups as any).update(groupId, {
          title: 'FindableX',
          color: 'purple',
          collapsed: true,
        });
      } catch {
        // tabGroups API may not be available
      }
    }
  } catch {
    // Tab groups not supported or failed
  }
}

/**
 * Find an existing tab for the given engine.
 */
export async function findEngineTab(engine: string): Promise<browser.Tabs.Tab | null> {
  const tabId = engineTabs.get(engine);
  if (tabId) {
    try {
      const tab = await browser.tabs.get(tabId);
      if (tab && tab.url) {
        const pattern = ENGINE_URL_PATTERNS[engine];
        if (pattern && pattern.test(tab.url)) {
          return tab;
        }
      }
    } catch {
      // Tab no longer exists
      engineTabs.delete(engine);
    }
  }

  // Search all tabs
  const tabs = await browser.tabs.query({});
  const pattern = ENGINE_URL_PATTERNS[engine];
  if (pattern) {
    for (const tab of tabs) {
      if (tab.url && pattern.test(tab.url) && tab.id) {
        engineTabs.set(engine, tab.id);
        return tab;
      }
    }
  }

  return null;
}

/**
 * Get or create a tab for the given engine.
 * Creates tabs in a minimized window or collapsed tab group for invisibility.
 */
export async function getOrCreateEngineTab(engine: string): Promise<browser.Tabs.Tab> {
  // Try to find existing tab
  const existingTab = await findEngineTab(engine);
  if (existingTab && existingTab.id) {
    // Check if user is actively using this tab
    if (await isTabActiveByUser(existingTab.id)) {
      // User is on this tab -- create a new one instead of interfering
      console.log(`[FindableX] User is active on ${engine} tab, creating new one`);
    } else {
      // Existing tab is available, don't focus it
      await browser.tabs.update(existingTab.id, { active: false });
      return existingTab;
    }
  }

  // Determine where to create the tab
  const url = ENGINE_NEW_CHAT_URLS[engine];
  if (!url) {
    throw new Error(`Unknown engine: ${engine}`);
  }

  let tab: browser.Tabs.Tab;

  // Strategy 1: Create in minimized window
  const windowId = await getOrCreateCrawlWindow();
  if (windowId > 0) {
    tab = await browser.tabs.create({
      url,
      active: false,
      windowId,
    });
  } else {
    // Strategy 2: Create in current window but not active
    tab = await browser.tabs.create({
      url,
      active: false,
    });

    // Strategy 3: Group the tab to keep it organized
    if (tab.id) {
      await groupCrawlTab(tab.id);
    }
  }

  if (tab.id) {
    engineTabs.set(engine, tab.id);
  }

  // Wait for tab to finish loading
  await waitForTabLoad(tab.id!);

  return tab;
}

/**
 * Wait for a tab to finish loading.
 */
function waitForTabLoad(tabId: number, timeoutMs: number = 30000): Promise<void> {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      browser.tabs.onUpdated.removeListener(listener);
      reject(new Error('Tab load timeout'));
    }, timeoutMs);

    const listener = (
      updatedTabId: number,
      changeInfo: browser.Tabs.OnUpdatedChangeInfoType,
    ) => {
      if (updatedTabId === tabId && changeInfo.status === 'complete') {
        clearTimeout(timeout);
        browser.tabs.onUpdated.removeListener(listener);
        // Give extra time for JS to initialize
        setTimeout(resolve, 2000);
      }
    };

    browser.tabs.onUpdated.addListener(listener);
  });
}

/**
 * Send a task to a content script in the given tab.
 * Uses promise-based sendMessage (polyfill handles this).
 */
export async function executeTaskInTab(
  tabId: number,
  task: ExtTask,
): Promise<ExtResult> {
  return new Promise(async (resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error('Task execution timeout (180s)'));
    }, 180000);

    const message: ExecuteTaskMessage = {
      type: 'EXECUTE_TASK',
      payload: task,
    };

    try {
      const response = await browser.tabs.sendMessage(tabId, message) as TaskResultMessage | undefined;
      clearTimeout(timeout);
      if (response && response.type === 'TASK_RESULT') {
        resolve(response.payload);
      } else {
        reject(new Error('Invalid response from content script'));
      }
    } catch (err: any) {
      clearTimeout(timeout);
      reject(new Error(err.message || 'Failed to send message to content script'));
    }
  });
}

/**
 * Close a tab by engine and remove from tracking.
 */
export async function closeEngineTab(engine: string): Promise<void> {
  const tabId = engineTabs.get(engine);
  if (tabId) {
    try {
      await browser.tabs.remove(tabId);
    } catch {
      // Tab already closed
    }
    engineTabs.delete(engine);
  }
}

/**
 * Close all crawl tabs and the crawl window.
 */
export async function closeAllCrawlTabs(): Promise<void> {
  for (const [engine, tabId] of engineTabs.entries()) {
    try {
      await browser.tabs.remove(tabId);
    } catch {
      // Tab already closed
    }
    engineTabs.delete(engine);
  }

  // Close the crawl window
  if (crawlWindowId !== null) {
    try {
      await browser.windows.remove(crawlWindowId);
    } catch {
      // Window already closed
    }
    crawlWindowId = null;
  }
}

/**
 * Clean up tabs map (remove stale entries).
 */
export async function cleanupTabs(): Promise<void> {
  for (const [engine, tabId] of engineTabs.entries()) {
    try {
      await browser.tabs.get(tabId);
    } catch {
      engineTabs.delete(engine);
    }
  }
}
