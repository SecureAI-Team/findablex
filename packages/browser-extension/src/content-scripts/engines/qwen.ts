/**
 * Qwen (通义千问) Engine Adapter
 *
 * Handles RPA for https://tongyi.aliyun.com/qianwen/
 * Qwen supports web search and produces citation links.
 */

import { BaseEngineAdapter } from './base';
import { registerAdapter } from '../injector';
import { Citation } from '../../lib/types';

class QwenAdapter extends BaseEngineAdapter {
  readonly engineId = 'qwen';
  readonly engineUrl = 'https://tongyi.aliyun.com/qianwen/';

  async isReady(): Promise<boolean> {
    const input = document.querySelector(this.selectors.inputSelector);
    return !!input;
  }

  async isLoggedIn(): Promise<boolean> {
    const avatar = document.querySelector(
      'div[class*="avatar"], img[class*="avatar"], div[class*="user-center"]'
    );
    const loginPrompt = document.querySelector(
      'button[class*="login"], div[class*="login-prompt"], a[href*="login"]'
    );
    return !!avatar && !loginPrompt;
  }

  async startNewChat(): Promise<void> {
    const newChatSelectors = [
      'div[class*="new-chat"]',
      'button[class*="new"]',
      'a[href*="qianwen"]',
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

        if (el instanceof HTMLTextAreaElement) {
          el.focus();
          await this.simulateTyping(el, text);
          return;
        } else if (el.getAttribute('contenteditable') === 'true') {
          await this.simulateContentEditableTyping(el as HTMLElement, text);
          return;
        }
      } catch {
        continue;
      }
    }

    const input = await this.waitForElement(this.selectors.inputSelector, 15000);
    if (!input) throw new Error('Qwen: Input element not found');

    if (input instanceof HTMLTextAreaElement) {
      await this.simulateTyping(input, text);
    } else {
      await this.simulateContentEditableTyping(input as HTMLElement, text);
    }
  }

  async submitQuery(): Promise<void> {
    await this.delay(500);

    const sendSelectors = [
      'button[type="submit"]',
      'button[class*="send"]',
      'div[class*="send-btn"]',
      'button:has(svg[class*="send"])',
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

    // Fallback
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
      'div[class*="bot-message"]:last-of-type .markdown-body',
      'div[class*="assistant"]:last-of-type div[class*="content"]',
      'div[class*="message-content"]:last-of-type',
      'div[class*="answer"]:last-of-type',
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

    // Qwen often shows source references with numbered footnotes
    try {
      const refElements = document.querySelectorAll(
        'div[class*="source"] a, div[class*="reference"] a, a[class*="footnote"]'
      );
      const seenUrls = new Set(citations.map(c => c.url));

      refElements.forEach((el) => {
        const url = el.getAttribute('href') || '';
        if (url && url.startsWith('http') && !seenUrls.has(url) &&
            !url.includes('tongyi.aliyun') && !url.includes('aliyun.com')) {
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

registerAdapter(new QwenAdapter());
console.log('[FindableX] Qwen adapter loaded');
