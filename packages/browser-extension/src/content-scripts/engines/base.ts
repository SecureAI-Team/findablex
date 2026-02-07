/**
 * Base Engine Adapter - Abstract class for all AI chatbot adapters.
 *
 * Each engine adapter extends this class and implements the
 * engine-specific DOM interaction logic.
 *
 * Features:
 * - CAPTCHA detection and notification
 * - Network error detection
 * - User-active tab check
 */

import { Citation, ExtResult, ExtTask } from '../../lib/types';
import { ENGINE_SELECTORS, EngineSelectors } from '../../lib/constants';

export abstract class BaseEngineAdapter {
  abstract readonly engineId: string;
  abstract readonly engineUrl: string;

  protected get selectors(): EngineSelectors {
    return ENGINE_SELECTORS[this.engineId];
  }

  // ============ Abstract Methods (must override) ============

  /**
   * Check if the page is ready for interaction.
   */
  abstract isReady(): Promise<boolean>;

  // ============ CAPTCHA Detection ============

  /**
   * Detect common CAPTCHA challenges on the page.
   * Returns true if a CAPTCHA or verification challenge is detected.
   */
  async detectCaptcha(): Promise<boolean> {
    // Common CAPTCHA indicators
    const captchaSelectors = [
      // reCAPTCHA
      'iframe[src*="recaptcha"]',
      'iframe[src*="google.com/recaptcha"]',
      '.g-recaptcha',
      '#recaptcha',
      // hCaptcha
      'iframe[src*="hcaptcha.com"]',
      '.h-captcha',
      // Cloudflare Turnstile / Challenge
      'iframe[src*="challenges.cloudflare.com"]',
      '#cf-challenge-running',
      '.cf-turnstile',
      '#challenge-running',
      '#challenge-form',
      // Slide to verify (Chinese sites)
      '.geetest_panel',
      '.geetest_holder',
      '#captcha-div',
      '.verify-wrap',
      '.slide-verify',
      '[class*="captcha"]',
      '[id*="captcha"]',
      // Generic verification pages
      '.verification-page',
      '.challenge-page',
    ];

    for (const selector of captchaSelectors) {
      try {
        const el = document.querySelector(selector);
        if (el) {
          // Verify the element is visible
          const rect = el.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0) {
            console.log(`[FindableX] CAPTCHA detected: ${selector}`);
            return true;
          }
        }
      } catch {
        // Invalid selector, skip
      }
    }

    // Check page title/body for common verification text
    const bodyText = document.body?.innerText?.toLowerCase() || '';
    const titleText = document.title?.toLowerCase() || '';
    const verifyPhrases = [
      'just a moment',
      'checking your browser',
      'verify you are human',
      'please verify',
      '请完成验证',
      '安全验证',
      '人机验证',
      'are you a robot',
    ];

    for (const phrase of verifyPhrases) {
      if (bodyText.includes(phrase) || titleText.includes(phrase)) {
        console.log(`[FindableX] CAPTCHA-like text detected: "${phrase}"`);
        return true;
      }
    }

    return false;
  }

  /**
   * Detect network errors or page load failures.
   */
  async detectNetworkError(): Promise<boolean> {
    const bodyText = document.body?.innerText?.toLowerCase() || '';
    const errorPhrases = [
      'err_connection_refused',
      'err_connection_reset',
      'err_internet_disconnected',
      'err_network_changed',
      'err_timed_out',
      'this site can\'t be reached',
      'no internet',
      'unable to connect',
      '无法访问此网站',
      '网络连接已中断',
    ];

    for (const phrase of errorPhrases) {
      if (bodyText.includes(phrase)) {
        return true;
      }
    }

    return false;
  }

  // ============ Common Methods ============

  /**
   * Check if the user is logged in.
   */
  async isLoggedIn(): Promise<boolean> {
    const sel = this.selectors;
    const loggedIn = document.querySelector(sel.loggedInIndicatorSelector);
    return !!loggedIn;
  }

  /**
   * Start a new chat (navigate to new chat page or click new chat button).
   */
  async startNewChat(): Promise<void> {
    const sel = this.selectors;
    const btn = document.querySelector(sel.newChatSelector) as HTMLElement;
    if (btn) {
      btn.click();
      await this.delay(2000);
    }
  }

  /**
   * Input query text into the chatbot's input field.
   */
  async inputQuery(text: string): Promise<void> {
    const sel = this.selectors;
    const input = await this.waitForElement(sel.inputSelector, 10000);
    if (!input) throw new Error('Input element not found');

    // Handle different input types
    if (input instanceof HTMLTextAreaElement || input instanceof HTMLInputElement) {
      input.focus();
      input.value = '';
      // Simulate typing for React/Vue controlled inputs
      await this.simulateTyping(input, text);
    } else if (input.getAttribute('contenteditable') === 'true') {
      input.focus();
      input.innerHTML = '';
      // For contenteditable, use execCommand or input events
      await this.simulateContentEditableTyping(input, text);
    }

    await this.delay(500);
  }

  /**
   * Click the submit/send button.
   */
  async submitQuery(): Promise<void> {
    const sel = this.selectors;
    // Give a moment for the input to register
    await this.delay(300);

    const btn = document.querySelector(sel.submitSelector) as HTMLElement;
    if (btn) {
      btn.click();
    } else {
      // Try pressing Enter on the input
      const input = document.querySelector(sel.inputSelector) as HTMLElement;
      if (input) {
        input.dispatchEvent(
          new KeyboardEvent('keydown', {
            key: 'Enter',
            code: 'Enter',
            keyCode: 13,
            which: 13,
            bubbles: true,
          }),
        );
      }
    }
  }

  /**
   * Wait for the AI response to complete.
   */
  async waitForResponse(timeoutMs: number = 180000): Promise<boolean> {
    const sel = this.selectors;
    const startTime = Date.now();
    let lastTextLength = 0;
    let stableCount = 0;
    const stableThreshold = 3;

    while (Date.now() - startTime < timeoutMs) {
      await this.delay(2000);

      // Check for CAPTCHA during response
      if (await this.detectCaptcha()) {
        throw new Error('CAPTCHA detected during response');
      }

      // Check for network errors
      if (await this.detectNetworkError()) {
        throw new Error('Network error detected');
      }

      // Check if loading indicator is gone
      const loading = document.querySelector(sel.loadingIndicatorSelector);
      const stopBtn = sel.stopButtonSelector
        ? document.querySelector(sel.stopButtonSelector)
        : null;

      // Check if response text is stable
      const responseEl = document.querySelector(sel.responseTextSelector);
      const currentLength = responseEl?.textContent?.length || 0;

      if (currentLength > 0 && currentLength === lastTextLength) {
        stableCount++;
      } else {
        stableCount = 0;
      }
      lastTextLength = currentLength;

      // Response is complete if:
      // 1. No loading indicator and no stop button, OR
      // 2. Text length is stable for 3 checks
      if (
        (!loading && !stopBtn && currentLength > 50) ||
        stableCount >= stableThreshold
      ) {
        await this.delay(1000);
        return true;
      }
    }

    return lastTextLength > 50;
  }

  /**
   * Extract the AI response text.
   */
  async extractResponse(): Promise<string> {
    const sel = this.selectors;
    const elements = document.querySelectorAll(sel.responseTextSelector);
    if (elements.length === 0) return '';

    const lastEl = elements[elements.length - 1];
    return (lastEl.textContent || '').trim();
  }

  /**
   * Extract citations/references from the response.
   */
  async extractCitations(): Promise<Citation[]> {
    const sel = this.selectors;
    const citations: Citation[] = [];

    const responseEls = document.querySelectorAll(sel.responseContainerSelector);
    const lastResponse = responseEls[responseEls.length - 1];
    if (!lastResponse) return citations;

    const links = lastResponse.querySelectorAll(sel.citationSelector);
    const seenUrls = new Set<string>();

    links.forEach((link, index) => {
      const url = link.getAttribute(sel.citationUrlAttr) || '';
      if (!url || seenUrls.has(url)) return;
      seenUrls.add(url);

      let title = '';
      if (sel.citationTitleSelector) {
        const titleEl = link.querySelector(sel.citationTitleSelector);
        title = titleEl?.textContent?.trim() || '';
      }
      if (!title) {
        title = link.textContent?.trim() || '';
      }

      let domain = '';
      try {
        domain = new URL(url).hostname;
      } catch {
        domain = url;
      }

      citations.push({
        position: index + 1,
        url,
        title: title.substring(0, 200),
        domain,
      });
    });

    return citations.slice(0, 30);
  }

  /**
   * Execute a full task: check CAPTCHA, input query, submit, wait, extract.
   */
  async executeTask(task: ExtTask): Promise<ExtResult> {
    const startTime = Date.now();

    try {
      // 0. Check for CAPTCHA before starting
      if (await this.detectCaptcha()) {
        throw new Error('CAPTCHA detected - please solve it manually');
      }

      // 0b. Check for network errors
      if (await this.detectNetworkError()) {
        throw new Error('Network error detected');
      }

      // 1. Check if ready
      const ready = await this.isReady();
      if (!ready) {
        throw new Error('Page not ready');
      }

      // 2. Check if logged in
      const loggedIn = await this.isLoggedIn();
      if (!loggedIn) {
        throw new Error('Login required - please sign in to ' + this.engineId);
      }

      // 3. Start new chat for clean response
      await this.startNewChat();
      await this.delay(1500);

      // 4. Input query
      await this.inputQuery(task.query_text);

      // 5. Submit
      await this.submitQuery();

      // 6. Wait for response (checks for CAPTCHA during wait)
      const completed = await this.waitForResponse();

      // 7. Extract response and citations
      const responseText = await this.extractResponse();
      const citations = await this.extractCitations();

      const elapsed = Date.now() - startTime;

      return {
        task_id: task.task_id,
        query_item_id: task.query_item_id,
        engine: task.engine,
        success: !!responseText && responseText.length > 50,
        response_text: responseText,
        citations,
        response_time_ms: elapsed,
      };
    } catch (err: any) {
      const elapsed = Date.now() - startTime;
      return {
        task_id: task.task_id,
        query_item_id: task.query_item_id,
        engine: task.engine,
        success: false,
        response_text: '',
        citations: [],
        error: err.message,
        response_time_ms: elapsed,
      };
    }
  }

  /**
   * Capture the current conversation (for manual mode / context menu).
   */
  async captureCurrentConversation(): Promise<{
    success: boolean;
    response_text: string;
    citations: Citation[];
    error?: string;
  }> {
    try {
      const responseText = await this.extractResponse();
      const citations = await this.extractCitations();

      return {
        success: !!responseText && responseText.length > 10,
        response_text: responseText,
        citations,
      };
    } catch (err: any) {
      return {
        success: false,
        response_text: '',
        citations: [],
        error: err.message,
      };
    }
  }

  // ============ Helper Methods ============

  protected async waitForElement(
    selector: string,
    timeoutMs: number = 10000,
  ): Promise<Element | null> {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const selectors = selector.split(',').map((s) => s.trim());
      for (const sel of selectors) {
        try {
          const el = document.querySelector(sel);
          if (el) return el;
        } catch {
          // Invalid selector, skip
        }
      }
      await this.delay(500);
    }
    return null;
  }

  protected async simulateTyping(
    element: HTMLInputElement | HTMLTextAreaElement,
    text: string,
  ): Promise<void> {
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement?.prototype || window.HTMLInputElement.prototype,
      'value',
    )?.set;

    if (nativeInputValueSetter) {
      nativeInputValueSetter.call(element, text);
    } else {
      element.value = text;
    }

    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
    element.dispatchEvent(
      new InputEvent('input', {
        bubbles: true,
        cancelable: true,
        data: text,
        inputType: 'insertText',
      }),
    );
  }

  protected async simulateContentEditableTyping(
    element: HTMLElement,
    text: string,
  ): Promise<void> {
    element.focus();
    element.textContent = text;

    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(
      new InputEvent('input', {
        bubbles: true,
        cancelable: true,
        data: text,
        inputType: 'insertText',
      }),
    );

    const range = document.createRange();
    const sel = window.getSelection();
    range.selectNodeContents(element);
    range.collapse(false);
    sel?.removeAllRanges();
    sel?.addRange(range);
  }

  protected delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
