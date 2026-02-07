/**
 * Sentry error monitoring for the frontend.
 *
 * Lightweight wrapper: if @sentry/nextjs is not installed or DSN is empty,
 * all calls gracefully no-op. This avoids build failures when the SDK is
 * not yet added to dependencies.
 *
 * To enable:
 *   1. npm install @sentry/nextjs
 *   2. Set NEXT_PUBLIC_SENTRY_DSN in .env
 *   3. Optionally run `npx @sentry/wizard@latest -i nextjs` for full setup
 */

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN || '';

let Sentry: any = null;

/**
 * Initialize Sentry on the client side.
 * Called once in the root layout or _app.
 */
export function initSentry() {
  if (!SENTRY_DSN) return;

  try {
    // Dynamic import to avoid build error if not installed
    Sentry = require('@sentry/nextjs');
    if (Sentry && Sentry.init) {
      Sentry.init({
        dsn: SENTRY_DSN,
        environment: process.env.NODE_ENV,
        tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.2 : 1.0,
        replaysOnErrorSampleRate: 1.0,
        replaysSessionSampleRate: 0,
      });
      console.log('[Sentry] Frontend initialized');
    }
  } catch {
    // @sentry/nextjs not installed – silently skip
    console.log('[Sentry] SDK not installed, skipping frontend monitoring');
  }
}

/**
 * Capture an exception manually.
 */
export function captureException(error: Error, context?: Record<string, any>) {
  if (Sentry?.captureException) {
    Sentry.captureException(error, { extra: context });
  } else {
    console.error('[Error]', error);
  }
}

/**
 * Capture a message manually.
 */
export function captureMessage(message: string, level: 'info' | 'warning' | 'error' = 'info') {
  if (Sentry?.captureMessage) {
    Sentry.captureMessage(message, level);
  }
}
