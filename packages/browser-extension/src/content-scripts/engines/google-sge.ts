/**
 * Google SGE / AI Overview Engine Adapter
 *
 * Handles extraction from Google Search AI Overview results.
 * Unlike other engines, Google SGE uses the search page, not a chat interface.
 * The query is entered in the search bar and the AI Overview section is extracted.
 */

import { BaseEngineAdapter } from './base';
import { registerAdapter } from '../injector';
import { Citation } from '../../lib/types';

class GoogleSGEAdapter extends BaseEngineAdapter {
  readonly engineId = 'google_sge';
  readonly engineUrl = 'https://www.google.com/';

  async isReady(): Promise<boolean> {
    const input = document.querySelector('textarea[name="q"], input[name="q"]');
    return !!input;
  }

  async isLoggedIn(): Promise<boolean> {
    // Google login is optional for search
    const avatar = document.querySelector('a[href*="accounts.google.com"][aria-label]');
    return !!avatar;
  }

  async startNewChat(): Promise<void> {
    // For Google, navigate to clean search page
    window.location.href = 'https://www.google.com/';
    await this.delay(2000);
  }

  async inputQuery(text: string): Promise<void> {
    const input = await this.waitForElement(
      'textarea[name="q"], input[name="q"]', 15000
    );
    if (!input) throw new Error('Google: Search input not found');

    if (input instanceof HTMLTextAreaElement || input instanceof HTMLInputElement) {
      input.focus();
      input.value = '';
      await this.simulateTyping(input as HTMLInputElement, text);
    }
  }

  async submitQuery(): Promise<void> {
    await this.delay(300);

    // Submit the search form
    const form = document.querySelector('form[action="/search"]') as HTMLFormElement;
    if (form) {
      form.submit();
    } else {
      const btn = document.querySelector(
        'button[type="submit"], input[type="submit"], button[aria-label*="Search"]'
      ) as HTMLElement;
      if (btn) btn.click();
    }
  }

  async waitForResponse(timeoutMs: number = 30000): Promise<boolean> {
    // For Google, wait for the page to load and AI Overview to appear
    const startTime = Date.now();

    while (Date.now() - startTime < timeoutMs) {
      await this.delay(2000);

      // Check for AI Overview section
      const aiOverview = document.querySelector(
        'div[class*="ai-overview"], div[data-attrid*="ai"], div[jsname][data-sgrd], div[id*="kp-wp-tab"]'
      );
      if (aiOverview && aiOverview.textContent && aiOverview.textContent.length > 50) {
        return true;
      }
    }

    // Check if there are at least regular search results
    const results = document.querySelectorAll('div.g, div[data-sokoban-grid]');
    return results.length > 0;
  }

  async extractResponse(): Promise<string> {
    // Try to find AI Overview section
    const overviewSelectors = [
      'div[class*="ai-overview"] div[class*="markdown"]',
      'div[data-attrid*="ai"]',
      'div[jsname][data-sgrd]',
      'div[id*="kp-wp-tab"]',
    ];

    for (const sel of overviewSelectors) {
      try {
        const el = document.querySelector(sel);
        if (el) {
          const text = (el.textContent || '').trim();
          if (text.length > 30) return text;
        }
      } catch { continue; }
    }

    // Fallback: extract featured snippet
    const snippet = document.querySelector('div.xpdopen, div[data-attrid="wa:/description"]');
    if (snippet) {
      return (snippet.textContent || '').trim();
    }

    return '';
  }

  async extractCitations(): Promise<Citation[]> {
    const citations: Citation[] = [];

    try {
      // Extract from AI Overview links
      const aiLinks = document.querySelectorAll(
        'div[class*="ai-overview"] a[href^="/url"], div[data-sgrd] a[href]'
      );
      const seenUrls = new Set<string>();

      aiLinks.forEach((el) => {
        let url = el.getAttribute('href') || '';
        // Google wraps URLs in /url?q=...
        if (url.startsWith('/url')) {
          try {
            const params = new URLSearchParams(url.split('?')[1]);
            url = params.get('q') || url;
          } catch { /* use as-is */ }
        }
        if (url && url.startsWith('http') && !seenUrls.has(url) &&
            !url.includes('google.com') && !url.includes('youtube.com')) {
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

      // Also get top organic results as potential citations
      const organicResults = document.querySelectorAll('div.g a[href^="http"]');
      organicResults.forEach((el) => {
        const url = el.getAttribute('href') || '';
        if (url && !seenUrls.has(url) && !url.includes('google.com') &&
            citations.length < 15) {
          seenUrls.add(url);
          let domain = '';
          try { domain = new URL(url).hostname; } catch { domain = url; }
          const heading = el.querySelector('h3');
          citations.push({
            position: citations.length + 1,
            url,
            title: (heading?.textContent || el.textContent || '').trim().substring(0, 200),
            domain,
          });
        }
      });
    } catch { /* non-critical */ }

    return citations.slice(0, 30);
  }
}

registerAdapter(new GoogleSGEAdapter());
console.log('[FindableX] Google SGE adapter loaded');
