/**
 * Bing Copilot Engine Adapter
 *
 * Handles RPA for https://www.bing.com/chat
 * Bing Copilot provides AI-powered search with citations.
 * Note: Bing uses Shadow DOM extensively, which complicates DOM access.
 */

import { BaseEngineAdapter } from './base';
import { registerAdapter } from '../injector';
import { Citation } from '../../lib/types';

class BingCopilotAdapter extends BaseEngineAdapter {
  readonly engineId = 'bing_copilot';
  readonly engineUrl = 'https://www.bing.com/chat';

  async isReady(): Promise<boolean> {
    // Bing chat uses a textarea or shadow DOM elements
    const input = document.querySelector(
      'textarea#searchbox, textarea[placeholder], cib-serp'
    );
    return !!input;
  }

  async isLoggedIn(): Promise<boolean> {
    const avatar = document.querySelector(
      'div[class*="avatar"], img[class*="avatar"], a[href*="account"]'
    );
    return !!avatar;
  }

  async startNewChat(): Promise<void> {
    // Navigate to fresh Bing chat
    window.location.href = 'https://www.bing.com/chat?q=&setlang=zh-cn';
    await this.delay(3000);
  }

  async inputQuery(text: string): Promise<void> {
    // Try regular textarea first
    let input = await this.waitForElement(
      'textarea#searchbox, textarea[placeholder]', 10000
    );

    if (input && input instanceof HTMLTextAreaElement) {
      input.focus();
      await this.simulateTyping(input, text);
      return;
    }

    // Try Shadow DOM access for Bing's web components
    try {
      const cibSerp = document.querySelector('cib-serp');
      if (cibSerp && cibSerp.shadowRoot) {
        const actionBar = cibSerp.shadowRoot.querySelector('cib-action-bar');
        if (actionBar && actionBar.shadowRoot) {
          const textarea = actionBar.shadowRoot.querySelector('textarea');
          if (textarea) {
            textarea.focus();
            await this.simulateTyping(textarea, text);
            return;
          }
        }
      }
    } catch {
      // Shadow DOM access might fail
    }

    throw new Error('Bing Copilot: Input not found');
  }

  async submitQuery(): Promise<void> {
    await this.delay(500);

    // Try regular button
    const btn = document.querySelector(
      'button[aria-label="Submit"], button#search_icon'
    ) as HTMLElement;
    if (btn) {
      btn.click();
      return;
    }

    // Try Shadow DOM submit
    try {
      const cibSerp = document.querySelector('cib-serp');
      if (cibSerp && cibSerp.shadowRoot) {
        const actionBar = cibSerp.shadowRoot.querySelector('cib-action-bar');
        if (actionBar && actionBar.shadowRoot) {
          const submitBtn = actionBar.shadowRoot.querySelector(
            'button[class*="submit"], button[aria-label="Submit"]'
          ) as HTMLElement;
          if (submitBtn) { submitBtn.click(); return; }
        }
      }
    } catch { /* fallback below */ }

    // Fallback: Enter key
    const input = document.querySelector('textarea');
    if (input) {
      input.dispatchEvent(new KeyboardEvent('keydown', {
        key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true,
      }));
    }
  }

  async waitForResponse(timeoutMs: number = 120000): Promise<boolean> {
    const startTime = Date.now();
    let lastLength = 0;
    let stableCount = 0;

    while (Date.now() - startTime < timeoutMs) {
      await this.delay(3000);

      const text = await this.extractResponseRaw();
      if (text.length > 0 && text.length === lastLength) {
        stableCount++;
      } else {
        stableCount = 0;
      }
      lastLength = text.length;

      if (stableCount >= 3 && lastLength > 50) return true;
    }

    return lastLength > 50;
  }

  private async extractResponseRaw(): Promise<string> {
    // Try regular DOM
    const selectors = [
      'cib-message-group[source="bot"]:last-of-type',
      'div[class*="response"]:last-of-type',
      'div[class*="bot-response"]:last-of-type',
    ];

    for (const sel of selectors) {
      try {
        const el = document.querySelector(sel);
        if (el) {
          const text = (el.textContent || '').trim();
          if (text.length > 30) return text;
        }
      } catch { continue; }
    }

    // Try Shadow DOM
    try {
      const cibSerp = document.querySelector('cib-serp');
      if (cibSerp && cibSerp.shadowRoot) {
        const conversation = cibSerp.shadowRoot.querySelector('cib-conversation');
        if (conversation && conversation.shadowRoot) {
          const messages = conversation.shadowRoot.querySelectorAll(
            'cib-message-group[source="bot"]'
          );
          if (messages.length > 0) {
            const lastMsg = messages[messages.length - 1];
            return (lastMsg.textContent || '').trim();
          }
        }
      }
    } catch { /* fallback */ }

    return '';
  }

  async extractResponse(): Promise<string> {
    return await this.extractResponseRaw();
  }

  async extractCitations(): Promise<Citation[]> {
    const citations: Citation[] = [];

    try {
      // Get links from bot response
      const botMessages = document.querySelectorAll(
        'cib-message-group[source="bot"]:last-of-type a[href^="http"]'
      );
      const seenUrls = new Set<string>();

      botMessages.forEach((el) => {
        const url = el.getAttribute('href') || '';
        if (url && !seenUrls.has(url) && !url.includes('bing.com') &&
            !url.includes('microsoft.com')) {
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

      // Also try regular page links
      const pageLinks = document.querySelectorAll(
        'div[class*="bot"] a[href^="http"]:not([href*="bing.com"])'
      );
      pageLinks.forEach((el) => {
        const url = el.getAttribute('href') || '';
        if (url && !seenUrls.has(url)) {
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
    } catch { /* non-critical */ }

    if (citations.length === 0) {
      return await super.extractCitations();
    }

    return citations.slice(0, 30);
  }
}

registerAdapter(new BingCopilotAdapter());
console.log('[FindableX] Bing Copilot adapter loaded');
