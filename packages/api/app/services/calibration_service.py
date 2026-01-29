"""Calibration service for detecting AI response inaccuracies."""
import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calibration import CalibrationDictionary, CalibrationError
from app.models.crawler import CrawlResult
from app.models.project import Project


class CalibrationChecker:
    """
    口径错误检测器
    
    检测AI回答中的以下错误类型:
    - 品牌名称错误
    - 产品名称错误
    - 数据/数字错误
    - 竞品混淆
    - 过时信息
    - 合规风险表述
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._dictionaries: Dict[str, List[CalibrationDictionary]] = {}
    
    async def load_dictionaries(self, project_id: UUID) -> None:
        """加载项目的校准词典"""
        result = await self.db.execute(
            select(CalibrationDictionary)
            .where(CalibrationDictionary.project_id == project_id)
            .where(CalibrationDictionary.is_active == True)
        )
        dictionaries = list(result.scalars().all())
        
        self._dictionaries = {}
        for d in dictionaries:
            if d.dict_type not in self._dictionaries:
                self._dictionaries[d.dict_type] = []
            self._dictionaries[d.dict_type].append(d)
    
    async def check_response(
        self,
        crawl_result: CrawlResult,
        project: Project,
    ) -> List[Dict[str, Any]]:
        """
        检查单个爬虫结果的口径错误
        
        Returns:
            List of detected errors
        """
        if not crawl_result.response_text:
            return []
        
        # 确保词典已加载
        if not self._dictionaries:
            await self.load_dictionaries(project.id)
        
        errors = []
        response_text = crawl_result.response_text
        
        # 1. 基于词典的检测
        for dict_type, dictionaries in self._dictionaries.items():
            for d in dictionaries:
                for error_variant in d.error_variants:
                    if error_variant.lower() in response_text.lower():
                        # 找到错误变体，提取上下文
                        context = self._extract_context(response_text, error_variant)
                        errors.append({
                            "error_type": self._map_dict_type_to_error_type(dict_type),
                            "severity": self._determine_severity(dict_type),
                            "original_text": error_variant,
                            "correct_text": d.correct_value,
                            "explanation": f"检测到错误表述 '{error_variant}'，正确的表述应为 '{d.correct_value}'",
                            "context": context,
                            "detection_method": "rule",
                        })
        
        # 2. 基于规则的检测
        
        # 检测可能的数字错误 (例如: 价格、百分比等异常值)
        # 这里只做简单示例，实际应该根据业务定义规则
        
        # 检测负面表述 (可能的合规风险)
        negative_patterns = [
            (r"存在.*安全漏洞", "compliance_risk", "high"),
            (r"被.*黑客攻击", "compliance_risk", "high"),
            (r"数据泄露", "compliance_risk", "critical"),
            (r"已经.*停止.*更新", "outdated_info", "medium"),
            (r"不再.*支持", "outdated_info", "medium"),
        ]
        
        for pattern, error_type, severity in negative_patterns:
            matches = re.finditer(pattern, response_text, re.IGNORECASE)
            for match in matches:
                context = self._extract_context(response_text, match.group())
                errors.append({
                    "error_type": error_type,
                    "severity": severity,
                    "original_text": match.group(),
                    "correct_text": None,
                    "explanation": f"检测到可能的风险表述: '{match.group()}'",
                    "context": context,
                    "detection_method": "rule",
                })
        
        # 3. 检测品牌是否被提及但可能存在错误 (基于目标域名)
        target_domains = project.target_domains or []
        for domain in target_domains:
            brand_name = domain.replace("www.", "").split(".")[0]
            # 检测是否有品牌的变体拼写
            similar_names = self._find_similar_names(brand_name, response_text)
            for similar in similar_names:
                if similar.lower() != brand_name.lower():
                    context = self._extract_context(response_text, similar)
                    errors.append({
                        "error_type": "brand_name",
                        "severity": "medium",
                        "original_text": similar,
                        "correct_text": brand_name,
                        "explanation": f"品牌名称可能拼写错误: '{similar}'，应为 '{brand_name}'",
                        "context": context,
                        "detection_method": "rule",
                    })
        
        return errors
    
    async def save_errors(
        self,
        errors: List[Dict[str, Any]],
        crawl_result_id: UUID,
        project_id: UUID,
    ) -> List[CalibrationError]:
        """保存检测到的错误"""
        saved_errors = []
        
        for error_data in errors:
            error = CalibrationError(
                crawl_result_id=crawl_result_id,
                project_id=project_id,
                error_type=error_data["error_type"],
                severity=error_data["severity"],
                original_text=error_data["original_text"],
                correct_text=error_data.get("correct_text"),
                explanation=error_data.get("explanation"),
                context=error_data.get("context"),
                detection_method=error_data["detection_method"],
            )
            self.db.add(error)
            saved_errors.append(error)
        
        await self.db.commit()
        
        for error in saved_errors:
            await self.db.refresh(error)
        
        return saved_errors
    
    async def get_project_errors(
        self,
        project_id: UUID,
        severity: Optional[str] = None,
        review_status: Optional[str] = None,
        limit: int = 100,
    ) -> List[CalibrationError]:
        """获取项目的口径错误列表"""
        query = select(CalibrationError).where(
            CalibrationError.project_id == project_id
        )
        
        if severity:
            query = query.where(CalibrationError.severity == severity)
        if review_status:
            query = query.where(CalibrationError.review_status == review_status)
        
        query = query.order_by(CalibrationError.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_review_status(
        self,
        error_id: UUID,
        status: str,
        reviewer_id: UUID,
        notes: Optional[str] = None,
    ) -> Optional[CalibrationError]:
        """更新错误的复核状态"""
        from datetime import datetime, timezone
        
        result = await self.db.execute(
            select(CalibrationError).where(CalibrationError.id == error_id)
        )
        error = result.scalar_one_or_none()
        
        if not error:
            return None
        
        error.review_status = status
        error.reviewed_by = reviewer_id
        error.reviewed_at = datetime.now(timezone.utc)
        error.review_notes = notes
        
        await self.db.commit()
        await self.db.refresh(error)
        
        return error
    
    def _extract_context(self, text: str, target: str, window: int = 100) -> str:
        """提取目标文本的上下文"""
        pos = text.lower().find(target.lower())
        if pos == -1:
            return ""
        
        start = max(0, pos - window)
        end = min(len(text), pos + len(target) + window)
        
        context = text[start:end]
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."
        
        return context
    
    def _map_dict_type_to_error_type(self, dict_type: str) -> str:
        """将词典类型映射到错误类型"""
        mapping = {
            "brand": "brand_name",
            "product": "product_name",
            "data": "data_error",
            "competitor": "competitor_confusion",
        }
        return mapping.get(dict_type, "other")
    
    def _determine_severity(self, dict_type: str) -> str:
        """根据词典类型确定默认严重程度"""
        severity_map = {
            "brand": "high",
            "product": "high",
            "data": "critical",
            "competitor": "critical",
        }
        return severity_map.get(dict_type, "medium")
    
    def _find_similar_names(self, brand_name: str, text: str) -> List[str]:
        """查找文本中与品牌名相似的词汇 (简单的Levenshtein距离检测)"""
        # 简单实现: 查找包含品牌名前3个字符的词
        if len(brand_name) < 3:
            return []
        
        prefix = brand_name[:3].lower()
        words = re.findall(r'\b\w+\b', text)
        
        similar = []
        for word in words:
            if word.lower().startswith(prefix) and len(word) >= 3:
                if word.lower() != brand_name.lower():
                    similar.append(word)
        
        return list(set(similar))


async def run_calibration_check(
    db: AsyncSession,
    project_id: UUID,
) -> Dict[str, Any]:
    """
    对项目的所有爬虫结果运行口径检测
    
    Returns:
        Summary of detected errors
    """
    from app.models.project import QueryItem
    
    checker = CalibrationChecker(db)
    await checker.load_dictionaries(project_id)
    
    # 获取项目
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        return {"error": "Project not found"}
    
    # 获取所有查询词
    result = await db.execute(
        select(QueryItem).where(QueryItem.project_id == project_id)
    )
    query_items = list(result.scalars().all())
    
    # 获取所有爬虫结果
    all_errors = []
    total_checked = 0
    
    for query_item in query_items:
        result = await db.execute(
            select(CrawlResult).where(CrawlResult.query_item_id == query_item.id)
        )
        crawl_results = list(result.scalars().all())
        
        for crawl_result in crawl_results:
            total_checked += 1
            errors = await checker.check_response(crawl_result, project)
            
            if errors:
                saved_errors = await checker.save_errors(
                    errors, crawl_result.id, project_id
                )
                all_errors.extend(saved_errors)
    
    # 统计
    severity_counts = {}
    type_counts = {}
    
    for error in all_errors:
        severity_counts[error.severity] = severity_counts.get(error.severity, 0) + 1
        type_counts[error.error_type] = type_counts.get(error.error_type, 0) + 1
    
    return {
        "total_checked": total_checked,
        "total_errors": len(all_errors),
        "severity_counts": severity_counts,
        "type_counts": type_counts,
        "critical_count": severity_counts.get("critical", 0),
        "high_count": severity_counts.get("high", 0),
    }
