#!/usr/bin/env python3
"""
FindableX Crawler Agent
本地浏览器爬虫代理，用于在本地机器上执行爬虫任务

用法:
    python agent.py [--headless] [--once]
"""

import asyncio
import base64
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ============ 配置 ============
API_URL = os.getenv('API_URL', 'http://localhost:8000/api/v1')
AGENT_TOKEN = os.getenv('AGENT_TOKEN', '')
HEADLESS = os.getenv('HEADLESS', 'false').lower() == 'true'
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '5'))  # 秒
BROWSER_USER_DATA = os.getenv('BROWSER_USER_DATA', '')
MAX_RETRIES = 3


class CrawlerAgent:
    """爬虫代理客户端"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.running = True
        self.http_client = httpx.AsyncClient(
            base_url=API_URL,
            headers={'Authorization': f'Bearer {AGENT_TOKEN}'},
            timeout=60.0
        )
        
    async def start(self):
        """启动 Agent"""
        logger.info("=" * 50)
        logger.info("FindableX Crawler Agent 启动中...")
        logger.info(f"服务器地址: {API_URL}")
        logger.info(f"无头模式: {self.headless}")
        logger.info("=" * 50)
        
        # 启动浏览器
        await self._start_browser()
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # 开始轮询任务
        await self._poll_tasks()
        
    async def _start_browser(self):
        """启动浏览器"""
        self.playwright = await async_playwright().start()
        
        launch_options = {
            'headless': self.headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        }
        
        self.browser = await self.playwright.chromium.launch(**launch_options)
        
        # 创建上下文
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'locale': 'zh-CN',
        }
        
        # 如果指定了用户数据目录，使用持久化上下文
        if BROWSER_USER_DATA and Path(BROWSER_USER_DATA).exists():
            logger.info(f"使用用户数据目录: {BROWSER_USER_DATA}")
            self.context = await self.playwright.chromium.launch_persistent_context(
                BROWSER_USER_DATA,
                **{**launch_options, **context_options}
            )
        else:
            self.context = await self.browser.new_context(**context_options)
        
        # 注入反检测脚本
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
        """)
        
        logger.info("浏览器启动成功")
        
    async def _poll_tasks(self):
        """轮询任务队列"""
        logger.info("开始轮询任务...")
        
        while self.running:
            try:
                # 获取任务
                tasks = await self._fetch_tasks()
                
                if tasks:
                    logger.info(f"获取到 {len(tasks)} 个任务")
                    for task in tasks:
                        if not self.running:
                            break
                        await self._execute_task(task)
                else:
                    logger.debug("暂无任务")
                    
            except httpx.HTTPError as e:
                logger.error(f"网络错误: {e}")
            except Exception as e:
                logger.exception(f"轮询错误: {e}")
                
            # 等待下次轮询
            await asyncio.sleep(POLL_INTERVAL)
            
    async def _fetch_tasks(self) -> List[Dict]:
        """从服务器获取待执行任务"""
        try:
            response = await self.http_client.get('/crawler/agent/tasks')
            if response.status_code == 200:
                data = response.json()
                return data.get('tasks', [])
            elif response.status_code == 401:
                logger.error("认证失败，请检查 AGENT_TOKEN")
                self.running = False
            return []
        except Exception as e:
            logger.error(f"获取任务失败: {e}")
            return []
            
    async def _execute_task(self, task: Dict):
        """执行单个爬虫任务"""
        task_id = task.get('id')
        engine = task.get('engine', 'unknown')
        query = task.get('query', '')
        config = task.get('config', {})
        
        logger.info(f"执行任务: {task_id} | 引擎: {engine} | 查询: {query[:30]}...")
        
        result = {
            'task_id': task_id,
            'success': False,
            'response_text': '',
            'citations': [],
            'error': None,
            'screenshot_base64': None
        }
        
        try:
            # 根据引擎选择爬虫方法
            if engine == 'deepseek':
                result = await self._crawl_deepseek(task_id, query, config)
            elif engine == 'kimi':
                result = await self._crawl_kimi(task_id, query, config)
            elif engine == 'qwen':
                result = await self._crawl_qwen(task_id, query, config)
            else:
                result['error'] = f"不支持的引擎: {engine}"
                
        except Exception as e:
            logger.exception(f"任务执行失败: {e}")
            result['error'] = str(e)
            
        # 报告结果
        await self._report_result(result)
        
    async def _crawl_deepseek(self, task_id: str, query: str, config: Dict) -> Dict:
        """爬取 DeepSeek"""
        page = await self.context.new_page()
        result = {
            'task_id': task_id,
            'success': False,
            'response_text': '',
            'citations': [],
            'error': None,
            'screenshot_base64': None
        }
        
        try:
            # 访问 DeepSeek
            logger.info("[DeepSeek] 访问页面...")
            await page.goto('https://chat.deepseek.com/', wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)
            
            # 启用联网搜索（如果需要）
            if config.get('enable_web_search', True):
                logger.info("[DeepSeek] 启用联网搜索...")
                try:
                    # 尝试点击联网搜索按钮
                    search_btn = page.locator('text=联网搜索').first
                    if await search_btn.is_visible():
                        await search_btn.click()
                        await asyncio.sleep(1)
                except:
                    pass
            
            # 输入问题
            logger.info(f"[DeepSeek] 输入查询: {query[:30]}...")
            textarea = page.locator('textarea').first
            await textarea.fill(query)
            await asyncio.sleep(0.5)
            
            # 发送
            await textarea.press('Enter')
            
            # 等待响应完成
            logger.info("[DeepSeek] 等待响应...")
            await self._wait_for_response(page, max_wait=180)
            
            # 提取响应
            result['response_text'] = await self._extract_text(page)
            result['citations'] = await self._extract_citations(page)
            
            # 截图
            screenshot = await page.screenshot(type='png')
            result['screenshot_base64'] = base64.b64encode(screenshot).decode('utf-8')
            
            result['success'] = len(result['response_text']) > 50 or len(result['citations']) > 0
            logger.info(f"[DeepSeek] 完成: {len(result['response_text'])} 字符, {len(result['citations'])} 引用")
            
        except Exception as e:
            logger.error(f"[DeepSeek] 错误: {e}")
            result['error'] = str(e)
            
            # 尝试截图
            try:
                screenshot = await page.screenshot(type='png')
                result['screenshot_base64'] = base64.b64encode(screenshot).decode('utf-8')
            except:
                pass
                
        finally:
            await page.close()
            
        return result
        
    async def _crawl_kimi(self, task_id: str, query: str, config: Dict) -> Dict:
        """爬取 Kimi"""
        page = await self.context.new_page()
        result = {
            'task_id': task_id,
            'success': False,
            'response_text': '',
            'citations': [],
            'error': None,
            'screenshot_base64': None
        }
        
        try:
            logger.info("[Kimi] 访问页面...")
            await page.goto('https://kimi.moonshot.cn/', wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)
            
            # 输入问题
            logger.info(f"[Kimi] 输入查询: {query[:30]}...")
            textarea = page.locator('textarea, [contenteditable="true"]').first
            await textarea.fill(query)
            await asyncio.sleep(0.5)
            
            # 发送
            send_btn = page.locator('button[type="submit"], button:has-text("发送")').first
            if await send_btn.is_visible():
                await send_btn.click()
            else:
                await textarea.press('Enter')
            
            # 等待响应
            logger.info("[Kimi] 等待响应...")
            await self._wait_for_response(page, max_wait=180)
            
            # 提取内容
            result['response_text'] = await self._extract_text(page)
            result['citations'] = await self._extract_citations(page)
            
            # 截图
            screenshot = await page.screenshot(type='png')
            result['screenshot_base64'] = base64.b64encode(screenshot).decode('utf-8')
            
            result['success'] = len(result['response_text']) > 50 or len(result['citations']) > 0
            
        except Exception as e:
            logger.error(f"[Kimi] 错误: {e}")
            result['error'] = str(e)
            
        finally:
            await page.close()
            
        return result
        
    async def _crawl_qwen(self, task_id: str, query: str, config: Dict) -> Dict:
        """爬取通义千问"""
        page = await self.context.new_page()
        result = {
            'task_id': task_id,
            'success': False,
            'response_text': '',
            'citations': [],
            'error': None,
            'screenshot_base64': None
        }
        
        try:
            logger.info("[Qwen] 访问页面...")
            await page.goto('https://tongyi.aliyun.com/qianwen/', wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)
            
            # 输入问题
            logger.info(f"[Qwen] 输入查询: {query[:30]}...")
            textarea = page.locator('textarea').first
            await textarea.fill(query)
            await asyncio.sleep(0.5)
            
            # 发送
            await textarea.press('Enter')
            
            # 等待响应
            logger.info("[Qwen] 等待响应...")
            await self._wait_for_response(page, max_wait=180)
            
            # 提取内容
            result['response_text'] = await self._extract_text(page)
            result['citations'] = await self._extract_citations(page)
            
            # 截图
            screenshot = await page.screenshot(type='png')
            result['screenshot_base64'] = base64.b64encode(screenshot).decode('utf-8')
            
            result['success'] = len(result['response_text']) > 50 or len(result['citations']) > 0
            
        except Exception as e:
            logger.error(f"[Qwen] 错误: {e}")
            result['error'] = str(e)
            
        finally:
            await page.close()
            
        return result
        
    async def _wait_for_response(self, page: Page, max_wait: int = 180):
        """等待 AI 响应完成"""
        start_time = time.time()
        last_text_length = 0
        stable_count = 0
        
        while time.time() - start_time < max_wait:
            # 检查是否仍在生成
            generating = await page.evaluate("""
                () => {
                    const stopBtn = document.querySelector('[aria-label*="停止"], button:has-text("停止")');
                    const loading = document.querySelector('.loading, [class*="loading"], [class*="typing"]');
                    return !!(stopBtn || loading);
                }
            """)
            
            if generating:
                stable_count = 0
                await asyncio.sleep(2)
                continue
                
            # 检查文本是否稳定
            current_text = await self._extract_text(page)
            if len(current_text) == last_text_length and len(current_text) > 50:
                stable_count += 1
                if stable_count >= 3:
                    return  # 文本稳定，认为完成
            else:
                stable_count = 0
                last_text_length = len(current_text)
                
            await asyncio.sleep(2)
            
        logger.warning("等待响应超时")
        
    async def _extract_text(self, page: Page) -> str:
        """提取响应文本"""
        try:
            text = await page.evaluate("""
                () => {
                    const selectors = [
                        '[class*="markdown"]',
                        '[class*="message"]',
                        '[class*="response"]',
                        '[class*="answer"]',
                        '[role="main"]',
                        'main'
                    ];
                    
                    for (const sel of selectors) {
                        const els = document.querySelectorAll(sel);
                        for (const el of els) {
                            const text = el.innerText?.trim();
                            if (text && text.length > 100) {
                                return text;
                            }
                        }
                    }
                    return '';
                }
            """)
            return text
        except:
            return ''
            
    async def _extract_citations(self, page: Page) -> List[Dict]:
        """提取引用链接"""
        try:
            citations = await page.evaluate("""
                () => {
                    const links = [];
                    const seen = new Set();
                    
                    document.querySelectorAll('a[href^="http"]').forEach((a, i) => {
                        const url = a.href;
                        const title = a.innerText?.trim() || a.title || '';
                        
                        if (url && !seen.has(url) && 
                            !url.includes('deepseek.com') && 
                            !url.includes('kimi.moonshot.cn') &&
                            !url.includes('tongyi.aliyun.com')) {
                            seen.add(url);
                            links.push({
                                position: links.length + 1,
                                url: url,
                                title: title.slice(0, 200),
                                domain: new URL(url).hostname
                            });
                        }
                    });
                    
                    return links.slice(0, 20);
                }
            """)
            return citations
        except:
            return []
            
    async def _report_result(self, result: Dict):
        """报告任务结果给服务器"""
        try:
            response = await self.http_client.post(
                '/crawler/agent/results',
                json=result
            )
            if response.status_code == 200:
                logger.info(f"结果已报告: {result['task_id']}")
            else:
                logger.error(f"报告失败: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"报告结果失败: {e}")
            
    def _signal_handler(self, signum, frame):
        """处理退出信号"""
        logger.info("收到退出信号，正在关闭...")
        self.running = False
        
    async def stop(self):
        """停止 Agent"""
        self.running = False
        
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
            
        await self.http_client.aclose()
        logger.info("Agent 已停止")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='FindableX Crawler Agent')
    parser.add_argument('--headless', action='store_true', help='无头模式运行')
    parser.add_argument('--once', action='store_true', help='只执行一次任务后退出')
    args = parser.parse_args()
    
    # 验证配置
    if not AGENT_TOKEN:
        logger.error("错误: 未设置 AGENT_TOKEN")
        logger.info("请在 .env 文件中设置 AGENT_TOKEN")
        sys.exit(1)
        
    agent = CrawlerAgent(headless=args.headless or HEADLESS)
    
    try:
        await agent.start()
    finally:
        await agent.stop()


if __name__ == '__main__':
    asyncio.run(main())
