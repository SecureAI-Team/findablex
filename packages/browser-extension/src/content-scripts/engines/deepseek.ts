/**
 * DeepSeek Engine Adapter
 *
 * Handles RPA for https://chat.deepseek.com/
 * DeepSeek supports web search (联网搜索) which produces citations.
 */

import { BaseEngineAdapter } from './base';
import { registerAdapter } from '../injector';

class DeepSeekAdapter extends BaseEngineAdapter {
  readonly engineId = 'deepseek';
  readonly engineUrl = 'https://chat.deepseek.com/';

  async isReady(): Promise<boolean> {
    // Check if the chat input is available
    const input = document.querySelector(this.selectors.inputSelector);
    return !!input;
  }

  async isLoggedIn(): Promise<boolean> {
    // DeepSeek shows user avatar/profile when logged in
    const avatar = document.querySelector(
      'div[class*="avatar"], img[alt*="avatar"], div[class*="user-info"], div[class*="profile"]'
    );
    // Also check for absence of login button
    const loginBtn = document.querySelector(
      'a[href*="login"], button:has-text("登录"), a:has-text("登录")'
    );
    return !!avatar || !loginBtn;
  }

  async startNewChat(): Promise<void> {
    // Try clicking new chat button
    const newChatSelectors = [
      'a[href="/"]',
      'div[class*="new-chat"]',
      'button[class*="new"]',
      'nav a:first-child',
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

    // Fallback: navigate to root
    window.location.href = this.engineUrl;
    await this.delay(3000);
  }

  async inputQuery(text: string): Promise<void> {
    // DeepSeek uses a textarea or contenteditable div
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

    // Fallback: wait and retry
    const input = await this.waitForElement(this.selectors.inputSelector, 15000);
    if (!input) throw new Error('DeepSeek: Input element not found');

    if (input instanceof HTMLTextAreaElement) {
      await this.simulateTyping(input, text);
    } else {
      await this.simulateContentEditableTyping(input as HTMLElement, text);
    }
  }

  async submitQuery(): Promise<void> {
    await this.delay(500);

    // Try clicking send button
    const sendSelectors = [
      'div[class*="ds-icon-button"]:not([class*="disabled"])',
      'button[class*="send"]',
      'button[aria-label*="Send"]',
      'button[aria-label*="发送"]',
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

    // Fallback: press Enter on the input
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
    // DeepSeek renders responses in markdown containers
    const responseSelectors = [
      '.ds-markdown:last-of-type',
      '.markdown-body:last-of-type',
      'div[class*="assistant"]:last-of-type .ds-markdown',
      'div[class*="message"]:last-of-type .markdown-body',
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

  async extractCitations(): Promise<import('../../lib/types').Citation[]> {
    // DeepSeek with web search shows citation links
    // They often appear as numbered references or footnotes
    const citations = await super.extractCitations();

    // Also look for DeepSeek's specific citation format (numbered references)
    try {
      const refElements = document.querySelectorAll(
        'a[class*="citation"], a[class*="reference"], sup a[href^="http"]'
      );
      const seenUrls = new Set(citations.map(c => c.url));

      refElements.forEach((el, idx) => {
        const url = el.getAttribute('href') || '';
        if (url && url.startsWith('http') && !seenUrls.has(url) && !url.includes('deepseek.com')) {
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

// Register the adapter
registerAdapter(new DeepSeekAdapter());
console.log('[FindableX] DeepSeek adapter loaded');
