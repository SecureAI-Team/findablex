/**
 * ChatGPT Engine Adapter
 *
 * Handles RPA for https://chatgpt.com/
 * ChatGPT supports web browsing which produces citation links.
 */

import { BaseEngineAdapter } from './base';
import { registerAdapter } from '../injector';
import { Citation } from '../../lib/types';

class ChatGPTAdapter extends BaseEngineAdapter {
  readonly engineId = 'chatgpt';
  readonly engineUrl = 'https://chatgpt.com/';

  async isReady(): Promise<boolean> {
    const input = document.querySelector(
      'textarea#prompt-textarea, div[contenteditable="true"][id="prompt-textarea"]'
    );
    return !!input;
  }

  async isLoggedIn(): Promise<boolean> {
    const profileBtn = document.querySelector(
      'div[data-testid="profile-button"], button[aria-label*="user"], button[aria-label*="User"]'
    );
    return !!profileBtn;
  }

  async startNewChat(): Promise<void> {
    const selectors = ['a[href="/"]', 'nav a:first-child', 'button[class*="new"]'];
    for (const sel of selectors) {
      try {
        const btn = document.querySelector(sel) as HTMLElement;
        if (btn) { btn.click(); await this.delay(2000); return; }
      } catch { continue; }
    }
    window.location.href = this.engineUrl;
    await this.delay(3000);
  }

  async inputQuery(text: string): Promise<void> {
    // ChatGPT uses a contenteditable div or textarea
    const input = await this.waitForElement(
      'textarea#prompt-textarea, div[contenteditable="true"][id="prompt-textarea"]',
      15000,
    );
    if (!input) throw new Error('ChatGPT: Input not found');

    if (input instanceof HTMLTextAreaElement) {
      input.focus();
      await this.simulateTyping(input, text);
    } else {
      (input as HTMLElement).focus();
      // ChatGPT uses a <p> inside contenteditable
      input.innerHTML = `<p>${text}</p>`;
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }

  async submitQuery(): Promise<void> {
    await this.delay(500);
    const btn = document.querySelector(
      'button[data-testid="send-button"], button[aria-label="Send prompt"]'
    ) as HTMLElement;
    if (btn && !btn.getAttribute('disabled')) {
      btn.click();
    }
  }

  async extractResponse(): Promise<string> {
    const elements = document.querySelectorAll(
      'div[data-message-author-role="assistant"] .markdown'
    );
    if (elements.length > 0) {
      return (elements[elements.length - 1].textContent || '').trim();
    }
    return await super.extractResponse();
  }

  async extractCitations(): Promise<Citation[]> {
    const citations = await super.extractCitations();

    // ChatGPT browsing mode shows citations with superscript numbers
    try {
      const refs = document.querySelectorAll(
        'div[data-message-author-role="assistant"]:last-of-type a[href^="http"]:not([href*="chatgpt.com"]):not([href*="openai.com"])'
      );
      const seenUrls = new Set(citations.map(c => c.url));
      refs.forEach((el) => {
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

    return citations.slice(0, 30);
  }
}

registerAdapter(new ChatGPTAdapter());
console.log('[FindableX] ChatGPT adapter loaded');
