"""Calibration error models for detecting AI response inaccuracies."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# 错误严重程度
SEVERITY_LEVELS = {
    "critical": {
        "name": "严重错误",
        "description": "可能导致严重后果的错误信息",
        "priority": 0,
    },
    "high": {
        "name": "高风险",
        "description": "明显的事实性错误",
        "priority": 1,
    },
    "medium": {
        "name": "中等风险",
        "description": "需要核实的可疑信息",
        "priority": 2,
    },
    "low": {
        "name": "低风险",
        "description": "轻微的表述不准确",
        "priority": 3,
    },
}

# 错误类型
ERROR_TYPES = {
    "brand_name": "品牌名称错误",
    "product_name": "产品名称错误",
    "data_error": "数据/数字错误",
    "competitor_confusion": "竞品混淆",
    "outdated_info": "过时信息",
    "missing_context": "缺少关键上下文",
    "false_claim": "虚假声明",
    "attribution_error": "引用来源错误",
    "compliance_risk": "合规风险表述",
    "other": "其他错误",
}


class CalibrationDictionary(Base):
    """Calibration dictionary for storing correct brand/product information."""
    
    __tablename__ = "calibration_dictionaries"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # 词典类型: brand, product, data, competitor
    dict_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="词典类型: brand, product, data, competitor",
    )
    
    # 正确的值
    correct_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="正确的品牌名/产品名/数据",
    )
    
    # 常见错误表述 (用于匹配检测)
    error_variants: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="常见的错误表述列表",
    )
    
    # 额外上下文/说明
    context: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="额外说明/上下文",
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    def __repr__(self) -> str:
        return f"<CalibrationDictionary {self.dict_type}: {self.correct_value}>"


class CalibrationError(Base):
    """Detected calibration errors in AI responses."""
    
    __tablename__ = "calibration_errors"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    # 关联到爬虫结果
    crawl_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crawl_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # 关联到项目 (冗余，方便查询)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # 错误类型
    error_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="错误类型: brand_name, product_name, data_error, etc.",
    )
    
    # 严重程度
    severity: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        nullable=False,
        comment="严重程度: critical, high, medium, low",
    )
    
    # 原始文本 (AI回答中的错误片段)
    original_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="AI回答中的原始文本片段",
    )
    
    # 正确的表述
    correct_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="正确的表述",
    )
    
    # 错误说明
    explanation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误说明/原因",
    )
    
    # 上下文 (原文的前后文)
    context: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误的上下文",
    )
    
    # 检测方式: rule, llm, manual
    detection_method: Mapped[str] = mapped_column(
        String(20),
        default="rule",
        nullable=False,
        comment="检测方式: rule, llm, manual",
    )
    
    # 人工复核状态
    review_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        comment="复核状态: pending, confirmed, dismissed, fixed",
    )
    
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="复核人ID",
    )
    
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    review_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="复核备注",
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    def __repr__(self) -> str:
        return f"<CalibrationError {self.error_type}: {self.original_text[:50]}>"
