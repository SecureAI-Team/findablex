/**
 * FindableX Extension - Popup Script (Simplified)
 *
 * Two states only:
 * - Logged out: email + password + login
 * - Logged in: single ON/OFF toggle, one stat line, compact engine icons
 *
 * Features:
 * - No API URL field (default to production, hidden advanced for override)
 * - Auto-start after login
 * - Toast notifications instead of alert()
 * - webextension-polyfill for cross-browser
 */

import browser from 'webextension-polyfill';
import { api } from '../lib/api';
import {
  getToken, setToken, setRefreshToken, clearAuth,
  getUser, setUser, getSettings, setApiUrl,
} from '../lib/storage';
import { ENGINE_NAMES } from '../lib/constants';
import { ExtMessage, DEFAULT_SETTINGS } from '../lib/types';

// ============ DOM Elements ============

const loginView = document.getElementById('login-view')!;
const mainView = document.getElementById('main-view')!;
const loginBtn = document.getElementById('login-btn')!;
const loginError = document.getElementById('login-error')!;
const logoutBtn = document.getElementById('logout-btn')!;

// Inputs
const emailInput = document.getElementById('email') as HTMLInputElement;
const passwordInput = document.getElementById('password') as HTMLInputElement;
const apiUrlInput = document.getElementById('api-url') as HTMLInputElement;
const advancedSection = document.getElementById('advanced-section')!;

// Main view
const autoToggle = document.getElementById('auto-toggle') as HTMLInputElement;
const greeting = document.getElementById('greeting')!;
const statLine = document.getElementById('stat-line')!;
const engineRow = document.getElementById('engine-row')!;
const toastArea = document.getElementById('toast-area')!;

// ============ Long-press to show advanced ============
let logoLongPressTimer: ReturnType<typeof setTimeout> | null = null;
const logoIcon = document.querySelector('.logo-icon');
if (logoIcon) {
  logoIcon.addEventListener('mousedown', () => {
    logoLongPressTimer = setTimeout(() => {
      advancedSection.style.display =
        advancedSection.style.display === 'none' ? 'block' : 'none';
    }, 1500);
  });
  logoIcon.addEventListener('mouseup', () => {
    if (logoLongPressTimer) clearTimeout(logoLongPressTimer);
  });
  logoIcon.addEventListener('mouseleave', () => {
    if (logoLongPressTimer) clearTimeout(logoLongPressTimer);
  });
}

// ============ Initialization ============

document.addEventListener('DOMContentLoaded', async () => {
  // Load API URL setting (default if not set)
  const settings = await getSettings();
  apiUrlInput.value = settings.apiUrl || DEFAULT_SETTINGS.apiUrl;

  // Check if authenticated
  const token = await getToken();
  if (token) {
    await showMainView();
  } else {
    showLoginView();
  }

  // Set up event listeners
  setupEventListeners();

  // Start status polling
  setInterval(refreshStatus, 3000);
});

// ============ Event Listeners ============

function setupEventListeners(): void {
  loginBtn.addEventListener('click', handleLogin);
  logoutBtn.addEventListener('click', handleLogout);

  // Toggle switch
  autoToggle.addEventListener('change', async () => {
    if (autoToggle.checked) {
      await sendMessage({ type: 'STATUS_UPDATE', payload: { mode: 'auto' } });
      showToast('自动采集已开启', 'success');
    } else {
      await sendMessage({ type: 'STATUS_UPDATE', payload: { mode: 'idle' } });
      showToast('自动采集已暂停');
    }
  });

  // Enter key on password field
  passwordInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleLogin();
  });
}

// ============ Authentication ============

async function handleLogin(): Promise<void> {
  const email = emailInput.value.trim();
  const password = passwordInput.value;

  if (!email || !password) {
    showLoginError('请填写邮箱和密码');
    return;
  }

  // Use custom API URL if provided in advanced, otherwise use default
  const customUrl = apiUrlInput.value.trim();
  const apiUrl = customUrl || DEFAULT_SETTINGS.apiUrl;

  loginBtn.setAttribute('disabled', 'true');
  loginError.style.display = 'none';

  try {
    // Save API URL
    await setApiUrl(apiUrl);

    // Login
    const data = await api.login(email, password, apiUrl);

    // Save tokens
    await setToken(data.access_token);
    if (data.refresh_token) {
      await setRefreshToken(data.refresh_token);
    }

    // Get user info
    try {
      const me = await api.getMe();
      await setUser({ id: me.id, email: me.email, full_name: me.full_name });
    } catch {
      if (data.user) {
        await setUser(data.user);
      }
    }

    await showMainView();

    // Auto-start: enable auto mode immediately after login
    autoToggle.checked = true;
    await sendMessage({ type: 'STATUS_UPDATE', payload: { mode: 'auto' } });
    showToast('FindableX 正在后台采集数据', 'success');
  } catch (err: any) {
    showLoginError(err.message || '登录失败');
  } finally {
    loginBtn.removeAttribute('disabled');
  }
}

async function handleLogout(): Promise<void> {
  await clearAuth();
  await sendMessage({ type: 'STATUS_UPDATE', payload: { mode: 'idle' } });
  showLoginView();
}

function showLoginError(message: string): void {
  loginError.textContent = message;
  loginError.style.display = 'block';
}

function showLoginView(): void {
  loginView.style.display = 'block';
  mainView.style.display = 'none';
}

async function showMainView(): Promise<void> {
  loginView.style.display = 'none';
  mainView.style.display = 'block';

  // Show user name
  const user = await getUser();
  if (user) {
    greeting.textContent = `Hi, ${user.full_name || user.email}`;
  }

  // Populate engine icons
  populateEngineIcons();

  // Refresh status
  await refreshStatus();
}

// ============ Status Refresh ============

async function refreshStatus(): Promise<void> {
  try {
    const status = await sendMessage({ type: 'GET_STATUS' });
    if (!status) return;

    // Update stats line
    const completed = status.stats?.completed || 0;
    const failed = status.stats?.failed || 0;
    statLine.textContent = `今日: ${completed} 完成, ${failed} 失败`;

    // Update toggle
    const mode = status.mode || 'idle';
    autoToggle.checked = mode === 'auto';
  } catch {
    // Service worker might not be ready
  }
}

// ============ Engine Icons ============

const ENGINE_ICONS: Record<string, string> = {
  deepseek: '🔮', kimi: '🌙', qwen: '☁️', chatgpt: '🤖',
  perplexity: '🔍', doubao: '🫘', chatglm: '🧠',
  google_sge: '🌐', bing_copilot: '💠',
};

function populateEngineIcons(): void {
  const engines = Object.entries(ENGINE_NAMES);

  engineRow.innerHTML = engines
    .map(
      ([id, name]) => `
    <div class="engine-icon-item" title="${name}" data-engine="${id}">
      <span class="engine-emoji">${ENGINE_ICONS[id] || '🤖'}</span>
      <span class="engine-dot" id="dot-${id}"></span>
    </div>
  `,
    )
    .join('');

  // Check engine login status
  checkEngineStatus();
}

async function checkEngineStatus(): Promise<void> {
  try {
    const tabs = await browser.tabs.query({});
    const enginePatterns: Record<string, RegExp> = {
      deepseek: /chat\.deepseek\.com/,
      kimi: /kimi\.moonshot\.cn/,
      qwen: /tongyi\.aliyun\.com/,
      chatgpt: /chatgpt\.com/,
      perplexity: /perplexity\.ai/,
      doubao: /doubao\.com/,
      chatglm: /chatglm\.cn/,
      google_sge: /google\.com/,
      bing_copilot: /bing\.com/,
    };

    for (const [engine, pattern] of Object.entries(enginePatterns)) {
      const hasTab = tabs.some((tab) => tab.url && pattern.test(tab.url));
      const dot = document.getElementById(`dot-${engine}`);
      if (dot) {
        dot.className = `engine-dot${hasTab ? ' online' : ''}`;
      }
    }
  } catch {
    // Permissions might not allow tab querying
  }
}

// ============ Toast Notifications ============

function showToast(
  message: string,
  type: 'success' | 'error' | 'info' = 'info',
  durationMs: number = 3000,
): void {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  toastArea.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('fade-out');
    setTimeout(() => toast.remove(), 300);
  }, durationMs);
}

// ============ Utilities ============

async function sendMessage(message: ExtMessage): Promise<any> {
  try {
    return await browser.runtime.sendMessage(message);
  } catch {
    return null;
  }
}
