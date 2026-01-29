"""
Comprehensive anti-detection stealth scripts for Playwright.

These scripts help bypass bot detection by:
- Hiding automation indicators
- Randomizing browser fingerprints
- Simulating realistic browser behavior
"""
from typing import Dict, Optional


def get_stealth_scripts(level: str = "high") -> str:
    """
    Get stealth scripts based on protection level.
    
    Args:
        level: "low", "medium", or "high"
    
    Returns:
        JavaScript code to inject into browser context
    """
    if level == "low":
        return BASIC_STEALTH_SCRIPT
    elif level == "medium":
        return BASIC_STEALTH_SCRIPT + FINGERPRINT_STEALTH_SCRIPT
    else:  # high
        return BASIC_STEALTH_SCRIPT + FINGERPRINT_STEALTH_SCRIPT + ADVANCED_STEALTH_SCRIPT


# Basic stealth: Hide obvious automation indicators
BASIC_STEALTH_SCRIPT = """
(function() {
    'use strict';
    
    // ===== Navigator.webdriver =====
    // Most important: hide webdriver flag
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });
    
    // Delete webdriver from navigator prototype
    delete Navigator.prototype.webdriver;
    
    // ===== Chrome Runtime =====
    // Add chrome object that real Chrome has
    if (!window.chrome) {
        window.chrome = {};
    }
    window.chrome.runtime = {
        id: undefined,
        connect: function() {},
        sendMessage: function() {},
        onMessage: { addListener: function() {} }
    };
    window.chrome.loadTimes = function() {
        return {
            requestTime: Date.now() / 1000 - Math.random() * 100,
            startLoadTime: Date.now() / 1000 - Math.random() * 10,
            commitLoadTime: Date.now() / 1000 - Math.random() * 5,
            finishDocumentLoadTime: Date.now() / 1000 - Math.random() * 2,
            finishLoadTime: Date.now() / 1000 - Math.random(),
            firstPaintTime: Date.now() / 1000 - Math.random() * 3,
            firstPaintAfterLoadTime: 0,
            navigationType: 'Other',
            wasFetchedViaSpdy: false,
            wasNpnNegotiated: true,
            npnNegotiatedProtocol: 'h2',
            wasAlternateProtocolAvailable: false,
            connectionInfo: 'h2'
        };
    };
    window.chrome.csi = function() {
        return {
            onloadT: Date.now(),
            startE: Date.now() - Math.random() * 1000,
            pageT: Math.random() * 10000,
            tran: 15
        };
    };
    
    // ===== Permissions API =====
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => {
        if (parameters.name === 'notifications') {
            return Promise.resolve({ state: Notification.permission });
        }
        return originalQuery.call(window.navigator.permissions, parameters);
    };
    
    // ===== Console.debug =====
    // Some detectors check if console.debug is native
    const originalDebug = console.debug;
    console.debug = function(...args) {
        return originalDebug.apply(console, args);
    };
    
    // ===== Error.stack =====
    // Hide Playwright from stack traces
    const originalError = Error;
    Error = function(...args) {
        const error = new originalError(...args);
        const stack = error.stack;
        if (stack && stack.includes('playwright')) {
            error.stack = stack.replace(/playwright[^\n]*/g, '');
        }
        return error;
    };
    Error.prototype = originalError.prototype;
    Error.captureStackTrace = originalError.captureStackTrace;
    
})();
"""


# Fingerprint stealth: Randomize browser fingerprints
FINGERPRINT_STEALTH_SCRIPT = """
(function() {
    'use strict';
    
    // ===== Canvas Fingerprint Protection =====
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    const originalToBlob = HTMLCanvasElement.prototype.toBlob;
    
    // Add subtle noise to canvas
    function addNoise(imageData) {
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
            // Add very subtle noise (±2) to RGB values
            data[i] = Math.max(0, Math.min(255, data[i] + (Math.random() - 0.5) * 4));
            data[i+1] = Math.max(0, Math.min(255, data[i+1] + (Math.random() - 0.5) * 4));
            data[i+2] = Math.max(0, Math.min(255, data[i+2] + (Math.random() - 0.5) * 4));
        }
        return imageData;
    }
    
    HTMLCanvasElement.prototype.toDataURL = function(...args) {
        const ctx = this.getContext('2d');
        if (ctx) {
            const imageData = ctx.getImageData(0, 0, this.width, this.height);
            addNoise(imageData);
            ctx.putImageData(imageData, 0, 0);
        }
        return originalToDataURL.apply(this, args);
    };
    
    CanvasRenderingContext2D.prototype.getImageData = function(...args) {
        const imageData = originalGetImageData.apply(this, args);
        return addNoise(imageData);
    };
    
    // ===== WebGL Fingerprint Protection =====
    const getParameterProxyHandler = {
        apply: function(target, thisArg, args) {
            const param = args[0];
            // UNMASKED_VENDOR_WEBGL
            if (param === 37445) {
                return 'Intel Inc.';
            }
            // UNMASKED_RENDERER_WEBGL
            if (param === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return Reflect.apply(target, thisArg, args);
        }
    };
    
    if (WebGLRenderingContext.prototype.getParameter) {
        WebGLRenderingContext.prototype.getParameter = new Proxy(
            WebGLRenderingContext.prototype.getParameter,
            getParameterProxyHandler
        );
    }
    if (WebGL2RenderingContext && WebGL2RenderingContext.prototype.getParameter) {
        WebGL2RenderingContext.prototype.getParameter = new Proxy(
            WebGL2RenderingContext.prototype.getParameter,
            getParameterProxyHandler
        );
    }
    
    // ===== Audio Context Fingerprint Protection =====
    const originalCreateAnalyser = AudioContext.prototype.createAnalyser;
    AudioContext.prototype.createAnalyser = function() {
        const analyser = originalCreateAnalyser.apply(this, arguments);
        const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;
        analyser.getFloatFrequencyData = function(array) {
            originalGetFloatFrequencyData.call(this, array);
            // Add noise to audio fingerprint
            for (let i = 0; i < array.length; i++) {
                array[i] = array[i] + (Math.random() - 0.5) * 0.1;
            }
        };
        return analyser;
    };
    
    // ===== Font Fingerprint Protection =====
    // Limit detectable fonts to common ones
    const originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth');
    const originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
    
    // Add slight randomization to prevent font detection
    if (originalOffsetWidth && originalOffsetWidth.get) {
        Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
            get: function() {
                const width = originalOffsetWidth.get.call(this);
                // Only add noise to spans (commonly used for font detection)
                if (this.tagName === 'SPAN' && this.style.fontFamily) {
                    return width + (Math.random() - 0.5) * 2;
                }
                return width;
            }
        });
    }
    
    // ===== Navigator Properties =====
    // Override with realistic values
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const plugins = [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
            ];
            plugins.length = 3;
            plugins.item = (i) => plugins[i];
            plugins.namedItem = (name) => plugins.find(p => p.name === name);
            plugins.refresh = () => {};
            return plugins;
        }
    });
    
    Object.defineProperty(navigator, 'mimeTypes', {
        get: () => {
            const mimeTypes = [
                { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
                { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format' },
                { type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable' },
                { type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client Executable' }
            ];
            mimeTypes.length = 4;
            mimeTypes.item = (i) => mimeTypes[i];
            mimeTypes.namedItem = (type) => mimeTypes.find(m => m.type === type);
            return mimeTypes;
        }
    });
    
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-CN', 'zh', 'en-US', 'en']
    });
    
    Object.defineProperty(navigator, 'platform', {
        get: () => 'Win32'
    });
    
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8
    });
    
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8
    });
    
})();
"""


# Advanced stealth: Additional protections
ADVANCED_STEALTH_SCRIPT = """
(function() {
    'use strict';
    
    // ===== Iframe Protection =====
    // Ensure contentWindow properties match parent
    const originalContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
    if (originalContentWindow && originalContentWindow.get) {
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
            get: function() {
                const win = originalContentWindow.get.call(this);
                if (win) {
                    try {
                        // Try to apply stealth to iframe too
                        Object.defineProperty(win.navigator, 'webdriver', { get: () => undefined });
                    } catch(e) {}
                }
                return win;
            }
        });
    }
    
    // ===== History Length =====
    // Realistic history length
    Object.defineProperty(history, 'length', {
        get: () => Math.floor(Math.random() * 10) + 5
    });
    
    // ===== Screen Properties =====
    // Realistic screen properties
    Object.defineProperty(screen, 'availWidth', { get: () => screen.width });
    Object.defineProperty(screen, 'availHeight', { get: () => screen.height - 40 }); // Taskbar
    Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
    Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });
    
    // ===== Performance API Protection =====
    // Some detectors use performance.now() timing
    const originalPerformanceNow = performance.now;
    performance.now = function() {
        // Add slight jitter to prevent timing analysis
        return originalPerformanceNow.call(performance) + Math.random() * 0.5;
    };
    
    // ===== Battery API Protection =====
    // Return realistic battery info
    if (navigator.getBattery) {
        navigator.getBattery = async function() {
            return {
                charging: true,
                chargingTime: Infinity,
                dischargingTime: Infinity,
                level: 0.9 + Math.random() * 0.1,
                addEventListener: () => {},
                removeEventListener: () => {}
            };
        };
    }
    
    // ===== Connection API Protection =====
    if (navigator.connection) {
        Object.defineProperty(navigator, 'connection', {
            get: () => ({
                downlink: 10,
                effectiveType: '4g',
                rtt: 50,
                saveData: false,
                addEventListener: () => {},
                removeEventListener: () => {}
            })
        });
    }
    
    // ===== Date/Timezone Protection =====
    // Ensure consistent timezone
    const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
    Date.prototype.getTimezoneOffset = function() {
        return -480; // UTC+8 (China Standard Time)
    };
    
    // ===== Mouse Event Protection =====
    // Some detectors check if events have isTrusted = true
    // We can't override isTrusted, but we can ensure events look normal
    
    // ===== Notification API =====
    // Return proper notification permission
    if (window.Notification) {
        const originalPermission = Object.getOwnPropertyDescriptor(Notification, 'permission');
        Object.defineProperty(Notification, 'permission', {
            get: () => 'default'
        });
    }
    
    // ===== WebRTC Protection =====
    // Disable WebRTC IP leak
    if (window.RTCPeerConnection) {
        const originalRTCPeerConnection = window.RTCPeerConnection;
        window.RTCPeerConnection = function(config) {
            if (config && config.iceServers) {
                // Remove STUN/TURN servers to prevent IP leak
                config.iceServers = [];
            }
            return new originalRTCPeerConnection(config);
        };
        window.RTCPeerConnection.prototype = originalRTCPeerConnection.prototype;
    }
    
    // ===== Headless Detection =====
    // Override properties that indicate headless mode
    Object.defineProperty(document, 'hidden', { get: () => false });
    Object.defineProperty(document, 'visibilityState', { get: () => 'visible' });
    
    // ===== Automation Detection =====
    // Remove automation-related properties
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    
    // ===== CDP Detection =====
    // Hide Chrome DevTools Protocol markers
    const cdpMarkers = [
        '__webdriver_evaluate',
        '__selenium_evaluate',
        '__webdriver_script_function',
        '__webdriver_script_func',
        '__webdriver_script_fn',
        '__fxdriver_evaluate',
        '__driver_unwrapped',
        '__webdriver_unwrapped',
        '__driver_evaluate',
        '__selenium_unwrapped',
        '__fxdriver_unwrapped'
    ];
    
    cdpMarkers.forEach(marker => {
        delete window[marker];
        delete document[marker];
    });
    
    // ===== Outerwidth/Outerheight Protection =====
    // Headless browsers often have outerWidth/outerHeight = 0
    if (window.outerWidth === 0) {
        Object.defineProperty(window, 'outerWidth', { get: () => window.innerWidth + 16 });
    }
    if (window.outerHeight === 0) {
        Object.defineProperty(window, 'outerHeight', { get: () => window.innerHeight + 88 });
    }
    
})();
"""


def get_init_script_for_context(
    locale: str = "zh-CN",
    timezone: str = "Asia/Shanghai",
    stealth_level: str = "high"
) -> str:
    """
    Get a complete init script for browser context.
    
    Args:
        locale: Browser locale
        timezone: Browser timezone
        stealth_level: Protection level (low, medium, high)
    
    Returns:
        Complete JavaScript init script
    """
    stealth = get_stealth_scripts(stealth_level)
    
    # Add locale/timezone specific overrides
    locale_script = f"""
(function() {{
    // Locale-specific overrides
    Object.defineProperty(navigator, 'language', {{ get: () => '{locale}' }});
    Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {{
        value: function() {{
            return {{
                locale: '{locale}',
                timeZone: '{timezone}',
                calendar: 'gregory',
                numberingSystem: 'latn'
            }};
        }}
    }});
}})();
"""
    
    return stealth + locale_script


# Precompiled scripts for common configurations
STEALTH_SCRIPTS_CN = get_init_script_for_context("zh-CN", "Asia/Shanghai", "high")
STEALTH_SCRIPTS_EN = get_init_script_for_context("en-US", "America/New_York", "high")


def get_stealth_launch_args() -> list:
    """Get browser launch arguments for stealth mode."""
    return [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-infobars",
        "--disable-background-networking",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-breakpad",
        "--disable-component-extensions-with-background-pages",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-extensions",
        "--disable-features=TranslateUI",
        "--disable-hang-monitor",
        "--disable-ipc-flooding-protection",
        "--disable-popup-blocking",
        "--disable-prompt-on-repost",
        "--disable-renderer-backgrounding",
        "--disable-sync",
        "--enable-features=NetworkService,NetworkServiceInProcess",
        "--force-color-profile=srgb",
        "--metrics-recording-only",
        "--no-first-run",
        "--password-store=basic",
        "--use-mock-keychain",
        "--export-tagged-pdf",
        # Additional anti-detection
        "--disable-features=IsolateOrigins,site-per-process",
        "--flag-switches-begin",
        "--flag-switches-end",
    ]


def get_viewport_configs() -> list:
    """Get realistic viewport configurations."""
    return [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 1280, "height": 720},
        {"width": 2560, "height": 1440},
    ]
