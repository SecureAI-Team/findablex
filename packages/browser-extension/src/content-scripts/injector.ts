/**
 * FindableX Extension - Content Script Injector (Common)
 *
 * This script runs on all supported AI chatbot pages.
 * It sets up the message listener and coordinates with engine-specific adapters.
 *
 * The floating indicator has been removed for invisible automation.
 * Extension status is shown via the badge icon color instead.
 */

import browser from 'webextension-polyfill';
import { BaseEngineAdapter } from './engines/base';
import { ExtMessage, ExecuteTaskMessage } from '../lib/types';

// ============ Global Adapter Registry ============

let registeredAdapter: BaseEngineAdapter | null = null;

/**
 * Register an engine adapter. Called by engine-specific scripts.
 */
export function registerAdapter(adapter: BaseEngineAdapter): void {
  registeredAdapter = adapter;
  console.log(`[FindableX] Registered adapter: ${adapter.engineId}`);
}

/**
 * Get the registered adapter.
 */
export function getAdapter(): BaseEngineAdapter | null {
  return registeredAdapter;
}

// ============ Message Listener ============

browser.runtime.onMessage.addListener(
  (message: ExtMessage, _sender): Promise<any> => {
    return handleMessage(message);
  },
);

async function handleMessage(message: ExtMessage): Promise<any> {
  const adapter = getAdapter();

  switch (message.type) {
    case 'EXECUTE_TASK': {
      if (!adapter) {
        return {
          type: 'TASK_RESULT',
          payload: {
            success: false,
            error: 'No engine adapter registered for this page',
            task_id: (message as ExecuteTaskMessage).payload?.task_id,
            query_item_id: (message as ExecuteTaskMessage).payload?.query_item_id,
            engine: (message as ExecuteTaskMessage).payload?.engine,
            response_text: '',
            citations: [],
            response_time_ms: 0,
          },
        };
      }

      const task = (message as ExecuteTaskMessage).payload;
      const result = await adapter.executeTask(task);

      return {
        type: 'TASK_RESULT',
        payload: result,
      };
    }

    case 'CAPTURE_PAGE': {
      if (!adapter) {
        return {
          type: 'CAPTURE_RESULT',
          payload: {
            success: false,
            error: 'No engine adapter registered for this page',
          },
        };
      }

      const captureResult = await adapter.captureCurrentConversation();
      return {
        type: 'CAPTURE_RESULT',
        payload: captureResult,
      };
    }

    case 'CHECK_LOGIN': {
      if (!adapter) {
        return {
          type: 'LOGIN_STATUS',
          payload: { engine: 'unknown', isLoggedIn: false },
        };
      }

      const isLoggedIn = await adapter.isLoggedIn();
      return {
        type: 'LOGIN_STATUS',
        payload: { engine: adapter.engineId, isLoggedIn },
      };
    }

    case 'PING':
      return {
        type: 'PING',
        payload: {
          engine: adapter?.engineId || 'unknown',
          ready: adapter ? await adapter.isReady() : false,
        },
      };

    default:
      return { error: 'Unknown message type' };
  }
}

// No floating indicator -- status is conveyed via the extension badge icon color
// (green = active, gray = idle). This keeps the automation invisible to the user.

console.log('[FindableX] Content script injector loaded');
