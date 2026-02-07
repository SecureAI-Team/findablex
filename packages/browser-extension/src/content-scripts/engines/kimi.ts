/**
 * Kimi Engine Adapter
 *
 * Handles RPA for https://kimi.moonshot.cn/
 * Kimi supports web search and file analysis with citation links.
 */

import { BaseEngineAdapter } from './base';
import { registerAdapter } from '../injector';
import { Citation } from '../../lib/types';

class KimiAdapter extends BaseEngineAdapter {
  readonly engineId = 'kimi';
  readonly engineUrl = 'https://kimi.moonshot.cn/';

  async isReady(): Promise<boolean> {
    const input = document.querySelector(this.selectors.inputSelector);
    return !!input;
  }

  async isLoggedIn(): Promise<boolean> {
    const avatar = document.querySelector(
      'div[class*="avatar"], div[class*="user"], img[class*="avatar"]'
    );
    const loginBtn = document.querySelector(
      'button[class*="login"], a[href*="login"], div[class*="login"]'
    );
    return !!avatar && !loginBtn;
  }

  async startNewChat(): Promise<void> {
    const newChatSelectors = [
      'div[class*="new-chat"]',
      'button[class*="new"]',
      'a[href="/"]',
      'div[class*="sidebar"] button:first-child',
    ];

    for (const selector of newChatSelectors) {
      try {
        const btn = document.querySelector(selector) as HTMLElement;
        if (btn) {
          btn.click();
          await this.delay(2000);
          return;
        }
      } catch {
        continue;
      }
    }

    window.location.href = this.engineUrl;
    await this.delay(3000);
  }

  async inputQuery(text: string): Promise<void> {
    const selectors = this.selectors.inputSelector.split(',').map(s => s.trim());

    for (const selector of selectors) {
      try {
        const el = document.querySelector(selector);
        if (!el) continue;

        if (el.getAttribute('contenteditable') === 'true') {
          await this.simulateContentEditableTyping(el as HTMLElement, text);
          return;
        } else if (el instanceof HTMLTextAreaElement) {
          await this.simulateTyping(el, text);
          return;
        }
      } catch {
        continue;
      }
    }

    const input = await this.waitForElement(this.selectors.inputSelector, 15000);
    if (!input) throw new Error('Kimi: Input element not found');

    if (input.getAttribute('contenteditable') === 'true') {
      await this.simulateContentEditableTyping(input as HTMLElement, text);
    } else if (input instanceof HTMLTextAreaElement) {
      await this.simulateTyping(input, text);
    }
  }

  async submitQuery(): Promise<void> {
    await this.delay(500);

    const sendSelectors = [
      'button[data-testid="send-button"]',
      'button[class*="send"]',
      'button:has(svg[class*="send"])',
      'div[class*="send-btn"]',
    ];

    for (const selector of sendSelectors) {
      try {
        const btn = document.querySelector(selector) as HTMLElement;
        if (btn && !btn.getAttribute('disabled')) {
          btn.click();
          return;
        }
      } catch {
        continue;
      }
    }

    // Fallback: Enter key
    const input = document.querySelector(this.selectors.inputSelector);
    if (input) {
      input.dispatchEvent(new KeyboardEvent('keydown', {
        key: 'Enter',
        code: 'Enter',
        keyCode: 13,
        bubbles: true,
      }));
    }
  }

  async extractResponse(): Promise<string> {
    const responseSelectors = [
      'div[class*="assistant-message"]:last-of-type .markdown-body',
      'div[class*="message-content"]:last-of-type',
      'div[class*="bot"]:last-of-type .markdown-body',
      'div[class*="response"]:last-of-type',
    ];

    for (const selector of responseSelectors) {
      try {
        const elements = document.querySelectorAll(selector);
        if (elements.length > 0) {
          const lastEl = elements[elements.length - 1];
          const text = (lastEl.textContent || '').trim();
          if (text.length > 50) return text;
        }
      } catch {
        continue;
      }
    }

    return await super.extractResponse();
  }

  async extractCitations(): Promise<Citation[]> {
    const citations = await super.extractCitations();

    // Kimi often shows search result cards with links
    try {
      const searchCards = document.querySelectorAll(
        'div[class*="search-result"] a, div[class*="source"] a, div[class*="reference"] a'
      );
      const seenUrls = new Set(citations.map(c => c.url));

      searchCards.forEach((el) => {
        const url = el.getAttribute('href') || '';
        if (url && url.startsWith('http') && !seenUrls.has(url) &&
            !url.includes('kimi.moonshot') && !url.includes('moonshot.cn')) {
          seenUrls.add(url);
          let domain = '';
          try { domain = new URL(url).hostname; } catch { domain = url; }
          citations.push({
            position: citations.length + 1,
            url,
            title: (el.textContent || '').trim().substring(0, 200),
            domain,
          });
        }
      });
    } catch {
      // Non-critical
    }

    return citations.slice(0, 30);
  }
}

registerAdapter(new KimiAdapter());
console.log('[FindableX] Kimi adapter loaded');
