/**
 * Doubao (豆包) Engine Adapter
 *
 * Handles RPA for https://www.doubao.com/chat/
 * Doubao supports web search with citation links.
 */

import { BaseEngineAdapter } from './base';
import { registerAdapter } from '../injector';
import { Citation } from '../../lib/types';

class DoubaoAdapter extends BaseEngineAdapter {
  readonly engineId = 'doubao';
  readonly engineUrl = 'https://www.doubao.com/chat/';

  async isReady(): Promise<boolean> {
    const input = document.querySelector(this.selectors.inputSelector);
    return !!input;
  }

  async isLoggedIn(): Promise<boolean> {
    const avatar = document.querySelector(
      'div[class*="avatar"], img[class*="avatar"], div[class*="user"]'
    );
    return !!avatar;
  }

  async startNewChat(): Promise<void> {
    const selectors = [
      'button[class*="new"]', 'div[class*="new-chat"]', 'a[href*="chat"]',
    ];
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
    const input = await this.waitForElement(this.selectors.inputSelector, 15000);
    if (!input) throw new Error('Doubao: Input not found');

    if (input instanceof HTMLTextAreaElement) {
      await this.simulateTyping(input, text);
    } else if (input.getAttribute('contenteditable') === 'true') {
      await this.simulateContentEditableTyping(input as HTMLElement, text);
    }
  }

  async submitQuery(): Promise<void> {
    await this.delay(500);
    const selectors = [
      'button[class*="send"]', 'button:has(svg[class*="send"])',
      'div[class*="send"]',
    ];
    for (const sel of selectors) {
      try {
        const btn = document.querySelector(sel) as HTMLElement;
        if (btn) { btn.click(); return; }
      } catch { continue; }
    }
  }

  async extractResponse(): Promise<string> {
    const selectors = [
      'div[class*="assistant"]:last-of-type div[class*="content"]',
      'div[class*="message-content"]:last-of-type',
      'div[class*="bot"]:last-of-type',
    ];
    for (const sel of selectors) {
      try {
        const elements = document.querySelectorAll(sel);
        if (elements.length > 0) {
          const text = (elements[elements.length - 1].textContent || '').trim();
          if (text.length > 50) return text;
        }
      } catch { continue; }
    }
    return await super.extractResponse();
  }

  async extractCitations(): Promise<Citation[]> {
    return await super.extractCitations();
  }
}

registerAdapter(new DoubaoAdapter());
console.log('[FindableX] Doubao adapter loaded');
