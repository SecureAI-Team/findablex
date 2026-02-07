/**
 * Perplexity Engine Adapter
 *
 * Handles RPA for https://www.perplexity.ai/
 * Perplexity is a search-first AI that always produces citations.
 */

import { BaseEngineAdapter } from './base';
import { registerAdapter } from '../injector';
import { Citation } from '../../lib/types';

class PerplexityAdapter extends BaseEngineAdapter {
  readonly engineId = 'perplexity';
  readonly engineUrl = 'https://www.perplexity.ai/';

  async isReady(): Promise<boolean> {
    const input = document.querySelector('textarea[placeholder], textarea.overflow-auto');
    return !!input;
  }

  async isLoggedIn(): Promise<boolean> {
    // Perplexity works without login, but has profile when logged in
    const profile = document.querySelector(
      'div[class*="avatar"], button[class*="user"], img[class*="avatar"]'
    );
    return !!profile;
  }

  async startNewChat(): Promise<void> {
    const selectors = ['a[href="/"]', 'button[class*="new"]', 'a[href="/search"]'];
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
    const input = await this.waitForElement(
      'textarea[placeholder], textarea.overflow-auto', 15000
    );
    if (!input) throw new Error('Perplexity: Input not found');
    await this.simulateTyping(input as HTMLTextAreaElement, text);
  }

  async submitQuery(): Promise<void> {
    await this.delay(500);
    const btn = document.querySelector(
      'button[aria-label="Submit"], button.bg-super, button[class*="submit"]'
    ) as HTMLElement;
    if (btn) {
      btn.click();
    } else {
      const input = document.querySelector('textarea');
      if (input) {
        input.dispatchEvent(new KeyboardEvent('keydown', {
          key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true,
        }));
      }
    }
  }

  async extractResponse(): Promise<string> {
    const elements = document.querySelectorAll('div[class*="prose"]');
    if (elements.length > 0) {
      return (elements[elements.length - 1].textContent || '').trim();
    }
    return await super.extractResponse();
  }

  async extractCitations(): Promise<Citation[]> {
    const citations: Citation[] = [];

    // Perplexity has rich citation support
    try {
      // Look for citation elements
      const citationEls = document.querySelectorAll(
        'a[data-testid], a.citation, a[class*="citation"], div[class*="source"] a'
      );
      const seenUrls = new Set<string>();

      citationEls.forEach((el) => {
        const url = el.getAttribute('href') || '';
        if (url && url.startsWith('http') && !seenUrls.has(url) &&
            !url.includes('perplexity.ai')) {
          seenUrls.add(url);
          let domain = '';
          try { domain = new URL(url).hostname; } catch { domain = url; }

          const titleEl = el.querySelector('span, div');
          const title = titleEl?.textContent?.trim() || el.textContent?.trim() || '';

          citations.push({
            position: citations.length + 1,
            url,
            title: title.substring(0, 200),
            domain,
          });
        }
      });

      // Also check for numbered source cards
      const sourceCards = document.querySelectorAll(
        'div[class*="source-card"] a, div[class*="sources"] a'
      );
      sourceCards.forEach((el) => {
        const url = el.getAttribute('href') || '';
        if (url && url.startsWith('http') && !seenUrls.has(url)) {
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

registerAdapter(new PerplexityAdapter());
console.log('[FindableX] Perplexity adapter loaded');
