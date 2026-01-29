"""
User agent rotation pool for anti-detection.

Provides realistic, up-to-date user agents for various platforms and browsers.
Supports random selection and engine-specific filtering.
"""
import random
from typing import List, Optional


# Chrome on Windows (most common)
CHROME_WINDOWS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Chrome on macOS
CHROME_MAC = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Edge on Windows
EDGE_WINDOWS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
]

# Firefox on Windows
FIREFOX_WINDOWS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

# Safari on macOS
SAFARI_MAC = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# Mobile user agents (for mobile simulation)
CHROME_ANDROID = [
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.280 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.280 Mobile Safari/537.36",
]

SAFARI_IOS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
]

# Combined pools
ALL_DESKTOP = CHROME_WINDOWS + CHROME_MAC + EDGE_WINDOWS + FIREFOX_WINDOWS + SAFARI_MAC
ALL_MOBILE = CHROME_ANDROID + SAFARI_IOS
ALL_USER_AGENTS = ALL_DESKTOP + ALL_MOBILE

# Weighted pools (Chrome Windows is most common)
WEIGHTED_DESKTOP = (
    CHROME_WINDOWS * 5 +  # 50% Chrome Windows
    CHROME_MAC * 2 +      # 20% Chrome Mac
    EDGE_WINDOWS * 2 +    # 20% Edge
    FIREFOX_WINDOWS +     # 10% Firefox
    SAFARI_MAC            # Rare Safari
)


def get_random_user_agent(
    platform: Optional[str] = None,
    browser: Optional[str] = None,
    weighted: bool = True,
) -> str:
    """
    Get a random user agent string.
    
    Args:
        platform: "windows", "mac", "android", "ios", or None for any
        browser: "chrome", "edge", "firefox", "safari", or None for any
        weighted: Use weighted selection (more common UAs selected more often)
    
    Returns:
        A realistic user agent string
    """
    pool = []
    
    # Filter by platform
    if platform == "windows":
        pool = CHROME_WINDOWS + EDGE_WINDOWS + FIREFOX_WINDOWS
    elif platform == "mac":
        pool = CHROME_MAC + SAFARI_MAC
    elif platform == "android":
        pool = CHROME_ANDROID
    elif platform == "ios":
        pool = SAFARI_IOS
    elif platform == "mobile":
        pool = ALL_MOBILE
    elif platform == "desktop":
        pool = WEIGHTED_DESKTOP if weighted else ALL_DESKTOP
    else:
        pool = WEIGHTED_DESKTOP if weighted else ALL_USER_AGENTS
    
    # Filter by browser
    if browser == "chrome":
        pool = [ua for ua in pool if "Chrome" in ua and "Edg" not in ua]
    elif browser == "edge":
        pool = [ua for ua in pool if "Edg" in ua]
    elif browser == "firefox":
        pool = [ua for ua in pool if "Firefox" in ua]
    elif browser == "safari":
        pool = [ua for ua in pool if "Safari" in ua and "Chrome" not in ua]
    
    if not pool:
        pool = CHROME_WINDOWS  # Fallback
    
    return random.choice(pool)


def get_user_agent_for_engine(engine: str) -> str:
    """
    Get a user agent optimized for a specific engine.
    
    Some engines may work better with certain browsers.
    
    Args:
        engine: Engine name (perplexity, google_sge, qwen, etc.)
    
    Returns:
        A user agent string suitable for the engine
    """
    # Engine-specific recommendations
    engine_preferences = {
        # International engines - use Chrome/Edge
        "perplexity": {"browser": "chrome", "platform": "desktop"},
        "google_sge": {"browser": "chrome", "platform": "desktop"},
        "bing_copilot": {"browser": "edge", "platform": "windows"},
        "chatgpt": {"browser": "chrome", "platform": "desktop"},
        
        # Chinese engines - use Chrome on Windows (most common in China)
        "qwen": {"browser": "chrome", "platform": "windows"},
        "deepseek": {"browser": "chrome", "platform": "windows"},
        "kimi": {"browser": "chrome", "platform": "windows"},
        "doubao": {"browser": "chrome", "platform": "windows"},
        "chatglm": {"browser": "chrome", "platform": "windows"},
    }
    
    prefs = engine_preferences.get(engine, {})
    return get_random_user_agent(
        platform=prefs.get("platform"),
        browser=prefs.get("browser"),
    )


def get_consistent_user_agent(session_id: str) -> str:
    """
    Get a consistent user agent for a session.
    
    Uses session_id as seed to always return the same UA for a session.
    
    Args:
        session_id: Unique session identifier
    
    Returns:
        User agent string (consistent for same session_id)
    """
    # Use session_id hash as random seed
    seed = hash(session_id) % (2**32)
    rng = random.Random(seed)
    return rng.choice(WEIGHTED_DESKTOP)


# Export commonly used
USER_AGENTS_CHROME = CHROME_WINDOWS + CHROME_MAC
USER_AGENTS_DESKTOP = ALL_DESKTOP
USER_AGENTS_MOBILE = ALL_MOBILE
