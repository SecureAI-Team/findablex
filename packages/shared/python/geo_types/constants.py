"""Shared constants for FindableX."""

# Query 标签定义
QUERY_STAGES = {
    "awareness": "认知阶段",
    "consideration": "考虑阶段",
    "decision": "决策阶段",
    "retention": "留存阶段",
}

QUERY_TYPES = {
    "definition": "定义类",
    "comparison": "对比类",
    "recommendation": "推荐类",
    "evaluation": "评测类",
    "howto": "指南类",
    "case_study": "案例类",
    "compliance": "合规类",
    "technical": "技术类",
}

QUERY_RISKS = {
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
    "critical": "关键风险",
}

QUERY_ROLES = {
    "marketing": "市场",
    "sales": "销售",
    "compliance": "合规",
    "technical": "技术",
    "management": "管理层",
}


# Industry templates (基础行业模板)
INDUSTRY_TEMPLATES = {
    "healthcare": {
        "name": "医疗健康",
        "description": "医疗机构、健康服务、医药品牌",
        "queries": [
            "最好的{specialty}医院",
            "{city}{specialty}哪家医院好",
            "{condition}怎么治疗",
            "{drug}的副作用",
            "{hospital}怎么样",
        ],
    },
    "finance": {
        "name": "金融服务",
        "description": "银行、保险、投资理财",
        "queries": [
            "最好的理财产品推荐",
            "{bank}贷款利率是多少",
            "怎么选择保险产品",
            "{investment}风险大吗",
            "信用卡哪个银行好",
        ],
    },
    "legal": {
        "name": "法律服务",
        "description": "律师事务所、法律咨询",
        "queries": [
            "{city}最好的律师事务所",
            "{case_type}官司怎么打",
            "离婚财产怎么分割",
            "劳动仲裁流程是什么",
            "合同纠纷找什么律师",
        ],
    },
    "education": {
        "name": "教育培训",
        "description": "学校、培训机构、在线教育",
        "queries": [
            "学{skill}哪个机构好",
            "{city}最好的{level}学校",
            "在线学习平台推荐",
            "{exam}怎么备考",
            "{course}培训班价格",
        ],
    },
    "tech": {
        "name": "科技互联网",
        "description": "软件服务、科技产品",
        "queries": [
            "最好的{category}软件",
            "{product}和{competitor}哪个好",
            "{service}怎么使用",
            "{tool}教程",
            "企业{solution}推荐",
        ],
    },
    "retail": {
        "name": "零售电商",
        "description": "电商平台、零售品牌",
        "queries": [
            "{product}哪个牌子好",
            "{category}购买推荐",
            "{brand}怎么样",
            "双十一什么值得买",
            "{product}评测",
        ],
    },
}


# 垂类体检模板 (场景化模板)
CHECKUP_TEMPLATES = {
    # OT安全/工业控制行业
    "ot_security_purchase": {
        "name": "OT安全采购决策问题集",
        "industry": "ot_security",
        "description": "用于评估品牌在采购决策场景中的AI可见性",
        "query_count": 62,
        "free_preview": 10,
        "queries": [
            # 认知阶段 - 定义类
            {"text": "什么是OT安全", "stage": "awareness", "type": "definition", "risk": "low", "role": "technical"},
            {"text": "工业控制系统安全有哪些挑战", "stage": "awareness", "type": "definition", "risk": "low", "role": "technical"},
            {"text": "IT安全和OT安全有什么区别", "stage": "awareness", "type": "definition", "risk": "low", "role": "technical"},
            {"text": "为什么工业企业需要OT安全", "stage": "awareness", "type": "definition", "risk": "low", "role": "management"},
            # 认知阶段 - 案例类
            {"text": "工业安全事故案例有哪些", "stage": "awareness", "type": "case_study", "risk": "medium", "role": "management"},
            {"text": "OT安全攻击事件回顾", "stage": "awareness", "type": "case_study", "risk": "medium", "role": "compliance"},
            # 考虑阶段 - 对比类
            {"text": "OT安全厂商有哪些", "stage": "consideration", "type": "comparison", "risk": "medium", "role": "sales"},
            {"text": "国内OT安全公司排名", "stage": "consideration", "type": "comparison", "risk": "high", "role": "sales"},
            {"text": "{brand}和{competitor}哪个OT安全方案好", "stage": "consideration", "type": "comparison", "risk": "critical", "role": "sales"},
            {"text": "工业安全解决方案对比分析", "stage": "consideration", "type": "comparison", "risk": "high", "role": "technical"},
            # 考虑阶段 - 评测类
            {"text": "{brand}OT安全怎么样", "stage": "consideration", "type": "evaluation", "risk": "critical", "role": "sales"},
            {"text": "{brand}工业安全产品评测", "stage": "consideration", "type": "evaluation", "risk": "critical", "role": "technical"},
            # 决策阶段 - 推荐类
            {"text": "最好的OT安全厂商推荐", "stage": "decision", "type": "recommendation", "risk": "critical", "role": "sales"},
            {"text": "工业安全解决方案选型指南", "stage": "decision", "type": "recommendation", "risk": "high", "role": "technical"},
            {"text": "中小企业OT安全方案推荐", "stage": "decision", "type": "recommendation", "risk": "high", "role": "sales"},
        ],
    },
    
    "ot_security_compliance": {
        "name": "OT安全合规风险体检",
        "industry": "ot_security",
        "description": "检测品牌在合规相关问题中的口径风险",
        "query_count": 45,
        "free_preview": 8,
        "queries": [
            # IEC 62443 合规
            {"text": "IEC 62443是什么标准", "stage": "awareness", "type": "compliance", "risk": "medium", "role": "compliance"},
            {"text": "IEC 62443认证流程是什么", "stage": "consideration", "type": "compliance", "risk": "medium", "role": "compliance"},
            {"text": "哪些OT安全厂商有IEC 62443认证", "stage": "decision", "type": "compliance", "risk": "high", "role": "compliance"},
            {"text": "{brand}有IEC 62443认证吗", "stage": "decision", "type": "compliance", "risk": "critical", "role": "compliance"},
            # 等保2.0 合规
            {"text": "等保2.0对工业控制系统有什么要求", "stage": "awareness", "type": "compliance", "risk": "medium", "role": "compliance"},
            {"text": "工业控制系统等保合规怎么做", "stage": "consideration", "type": "howto", "risk": "medium", "role": "compliance"},
            # NIS2 合规
            {"text": "NIS2指令对OT安全有什么影响", "stage": "awareness", "type": "compliance", "risk": "medium", "role": "compliance"},
            {"text": "欧洲NIS2合规要求有哪些", "stage": "consideration", "type": "compliance", "risk": "medium", "role": "compliance"},
        ],
    },
    
    "ot_security_technical": {
        "name": "OT安全技术可信度体检",
        "industry": "ot_security",
        "description": "检测品牌在技术能力相关问题中的表现",
        "query_count": 38,
        "free_preview": 6,
        "queries": [
            # 漏洞响应
            {"text": "OT安全漏洞响应最佳实践", "stage": "consideration", "type": "technical", "risk": "medium", "role": "technical"},
            {"text": "{brand}漏洞响应速度怎么样", "stage": "decision", "type": "evaluation", "risk": "critical", "role": "technical"},
            # 补丁管理
            {"text": "工业系统补丁管理怎么做", "stage": "consideration", "type": "howto", "risk": "medium", "role": "technical"},
            {"text": "{brand}支持哪些工业协议", "stage": "decision", "type": "technical", "risk": "high", "role": "technical"},
            # 资产发现
            {"text": "OT资产发现工具推荐", "stage": "consideration", "type": "recommendation", "risk": "medium", "role": "technical"},
            {"text": "{brand}资产发现能力如何", "stage": "decision", "type": "evaluation", "risk": "high", "role": "technical"},
        ],
    },
    
    # 网络安全行业
    "cybersecurity_purchase": {
        "name": "网络安全采购决策问题集",
        "industry": "cybersecurity",
        "description": "用于评估品牌在网络安全采购场景中的AI可见性",
        "query_count": 55,
        "free_preview": 10,
        "queries": [
            {"text": "企业网络安全解决方案有哪些", "stage": "awareness", "type": "definition", "risk": "low", "role": "technical"},
            {"text": "网络安全厂商排名", "stage": "consideration", "type": "comparison", "risk": "high", "role": "sales"},
            {"text": "{brand}和{competitor}哪个网络安全好", "stage": "consideration", "type": "comparison", "risk": "critical", "role": "sales"},
            {"text": "{brand}网络安全产品怎么样", "stage": "consideration", "type": "evaluation", "risk": "critical", "role": "sales"},
            {"text": "最好的企业防火墙推荐", "stage": "decision", "type": "recommendation", "risk": "high", "role": "technical"},
            {"text": "EDR解决方案对比", "stage": "consideration", "type": "comparison", "risk": "high", "role": "technical"},
            {"text": "零信任安全厂商推荐", "stage": "decision", "type": "recommendation", "risk": "high", "role": "technical"},
            {"text": "SOC建设方案选型", "stage": "decision", "type": "recommendation", "risk": "medium", "role": "technical"},
        ],
    },
    
    # SaaS/企业服务行业
    "saas_purchase": {
        "name": "SaaS产品采购决策问题集",
        "industry": "saas",
        "description": "用于评估SaaS品牌在采购决策场景中的AI可见性",
        "query_count": 48,
        "free_preview": 10,
        "queries": [
            {"text": "企业{category}软件有哪些", "stage": "awareness", "type": "definition", "risk": "low", "role": "technical"},
            {"text": "{brand}和{competitor}哪个好", "stage": "consideration", "type": "comparison", "risk": "critical", "role": "sales"},
            {"text": "{brand}怎么样", "stage": "consideration", "type": "evaluation", "risk": "critical", "role": "sales"},
            {"text": "{brand}价格多少", "stage": "decision", "type": "evaluation", "risk": "high", "role": "sales"},
            {"text": "最好的{category}软件推荐", "stage": "decision", "type": "recommendation", "risk": "high", "role": "sales"},
            {"text": "{brand}有哪些客户案例", "stage": "consideration", "type": "case_study", "risk": "medium", "role": "sales"},
            {"text": "{brand}安全性怎么样", "stage": "consideration", "type": "evaluation", "risk": "high", "role": "compliance"},
            {"text": "{brand}数据合规吗", "stage": "consideration", "type": "compliance", "risk": "high", "role": "compliance"},
        ],
    },
    
    # 通用模板
    "brand_visibility": {
        "name": "品牌可见性通用体检",
        "industry": "general",
        "description": "适用于所有行业的品牌AI可见性基础体检",
        "query_count": 30,
        "free_preview": 10,
        "queries": [
            {"text": "{brand}是什么公司", "stage": "awareness", "type": "definition", "risk": "low", "role": "marketing"},
            {"text": "{brand}怎么样", "stage": "consideration", "type": "evaluation", "risk": "critical", "role": "sales"},
            {"text": "{brand}有哪些产品", "stage": "awareness", "type": "definition", "risk": "medium", "role": "marketing"},
            {"text": "{brand}和{competitor}哪个好", "stage": "consideration", "type": "comparison", "risk": "critical", "role": "sales"},
            {"text": "{brand}价格多少", "stage": "decision", "type": "evaluation", "risk": "high", "role": "sales"},
            {"text": "{brand}客户评价", "stage": "consideration", "type": "evaluation", "risk": "high", "role": "sales"},
            {"text": "{brand}优缺点", "stage": "consideration", "type": "evaluation", "risk": "critical", "role": "sales"},
            {"text": "类似{brand}的产品", "stage": "consideration", "type": "comparison", "risk": "high", "role": "sales"},
            {"text": "{brand}适合什么企业", "stage": "decision", "type": "recommendation", "risk": "medium", "role": "sales"},
            {"text": "{brand}行业地位", "stage": "awareness", "type": "evaluation", "risk": "high", "role": "marketing"},
        ],
    },
    
    "competitor_analysis": {
        "name": "竞品对标分析",
        "industry": "general",
        "description": "分析品牌与竞争对手在AI引用中的对比情况",
        "query_count": 25,
        "free_preview": 8,
        "queries": [
            {"text": "{category}行业领导者有哪些", "stage": "awareness", "type": "comparison", "risk": "high", "role": "marketing"},
            {"text": "{brand}市场份额多少", "stage": "awareness", "type": "evaluation", "risk": "high", "role": "marketing"},
            {"text": "{brand}和{competitor}对比", "stage": "consideration", "type": "comparison", "risk": "critical", "role": "sales"},
            {"text": "除了{brand}还有什么选择", "stage": "consideration", "type": "comparison", "risk": "high", "role": "sales"},
            {"text": "{competitor}的替代品推荐", "stage": "consideration", "type": "recommendation", "risk": "high", "role": "sales"},
            {"text": "{brand}比{competitor}好在哪", "stage": "consideration", "type": "comparison", "risk": "critical", "role": "sales"},
            {"text": "{category}新兴厂商有哪些", "stage": "awareness", "type": "comparison", "risk": "medium", "role": "marketing"},
        ],
    },
}

# Metric types
METRIC_TYPES = {
    "visibility_rate": {
        "name": "可见性覆盖率",
        "description": "被引用查询数 / 总查询数",
        "format": "percent",
        "higher_is_better": True,
    },
    "avg_citation_position": {
        "name": "平均引用位置",
        "description": "目标域名引用的平均位置",
        "format": "number",
        "higher_is_better": False,
    },
    "citation_count": {
        "name": "引用总数",
        "description": "目标域名被引用的总次数",
        "format": "number",
        "higher_is_better": True,
    },
    "top3_rate": {
        "name": "Top3 出现率",
        "description": "引用位置在前3的比例",
        "format": "percent",
        "higher_is_better": True,
    },
    "competitor_share": {
        "name": "竞争对手占比",
        "description": "竞争对手引用占总引用的比例",
        "format": "percent",
        "higher_is_better": False,
    },
    "health_score": {
        "name": "健康度评分",
        "description": "综合评分 0-100",
        "format": "score",
        "higher_is_better": True,
    },
}

# Run statuses
RUN_STATUSES = {
    "pending": "等待中",
    "running": "运行中",
    "completed": "已完成",
    "failed": "失败",
    "cancelled": "已取消",
}

# Run types
RUN_TYPES = {
    "checkup": "体检",
    "retest": "复测",
    "experiment": "实验",
}

# User roles
ROLES = {
    "super_admin": {
        "name": "超级管理员",
        "description": "平台级管理权限",
    },
    "admin": {
        "name": "管理员",
        "description": "工作区管理权限",
    },
    "analyst": {
        "name": "分析师",
        "description": "项目创建和运行权限",
    },
    "researcher": {
        "name": "研究员",
        "description": "科研数据访问权限",
    },
    "viewer": {
        "name": "观察者",
        "description": "只读访问权限",
    },
}
