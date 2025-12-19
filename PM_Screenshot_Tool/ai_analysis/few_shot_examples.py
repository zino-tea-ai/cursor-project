# -*- coding: utf-8 -*-
"""
Few-shot样本获取模块
从数据库中获取高质量分类样本用于提示词增强
"""

import os
import sys
from typing import Dict, List, Optional
import random

# 数据库
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from data.db_manager import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


class FewShotProvider:
    """Few-shot样本提供器"""
    
    # 每种类型获取的样本数
    SAMPLES_PER_TYPE = 2
    
    # 最低置信度要求
    MIN_CONFIDENCE = 0.85
    
    def __init__(self):
        self.db = get_db() if DB_AVAILABLE else None
        self._cache = {}  # 缓存样本
    
    def get_examples_for_type(self, screen_type: str, exclude_product: str = None) -> List[Dict]:
        """
        获取某类型的高质量样本
        
        Args:
            screen_type: 目标类型
            exclude_product: 排除的产品（避免用自己的数据做样本）
        
        Returns:
            样本列表 [{product, filename, naming, core_function, features}]
        """
        if not self.db:
            return []
        
        cache_key = f"{screen_type}_{exclude_product}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # 查询高置信度样本
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT s.*, p.name as product_name, p.folder_name
                FROM screenshots s
                JOIN products p ON s.product_id = p.id
                WHERE s.screen_type = ?
                AND s.confidence >= ?
            """
            params = [screen_type, self.MIN_CONFIDENCE]
            
            if exclude_product:
                query += " AND p.folder_name != ?"
                params.append(exclude_product)
            
            query += " ORDER BY s.confidence DESC LIMIT ?"
            params.append(self.SAMPLES_PER_TYPE * 3)  # 多取一些，随机选
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # 转换为样本格式
            samples = []
            for row in rows:
                samples.append({
                    'product': row['product_name'],
                    'filename': row['filename'],
                    'naming_cn': row['naming_cn'] or '',
                    'naming_en': row['naming_en'] or '',
                    'core_function_cn': row['core_function_cn'] or '',
                    'core_function_en': row['core_function_en'] or '',
                    'confidence': row['confidence']
                })
            
            # 随机选择指定数量
            if len(samples) > self.SAMPLES_PER_TYPE:
                samples = random.sample(samples, self.SAMPLES_PER_TYPE)
            
            self._cache[cache_key] = samples
            return samples
            
        except Exception as e:
            print(f"[FewShot] Error getting examples: {e}")
            return []
    
    def get_examples_prompt(self, target_types: List[str] = None, exclude_product: str = None) -> str:
        """
        生成Few-shot示例提示词
        
        Args:
            target_types: 要获取样本的类型列表（None表示获取常见类型）
            exclude_product: 排除的产品
        
        Returns:
            格式化的示例提示词
        """
        if not self.db:
            return ""
        
        # 默认获取这些容易混淆的类型
        if target_types is None:
            target_types = ['Onboarding', 'Welcome', 'Feature', 'Paywall', 'Home']
        
        lines = ["## 参考示例（来自已分析的其他产品）\n"]
        
        for type_name in target_types:
            examples = self.get_examples_for_type(type_name, exclude_product)
            
            if not examples:
                continue
            
            lines.append(f"### {type_name} 示例：")
            
            for ex in examples:
                lines.append(f"- {ex['product']} - {ex['naming_cn']}")
                lines.append(f"  功能：{ex['core_function_cn']}")
            
            lines.append("")
        
        if len(lines) <= 1:
            return ""  # 没有示例
        
        return "\n".join(lines)
    
    def get_onboarding_examples(self, exclude_product: str = None) -> str:
        """
        专门获取Onboarding的详细示例（因为这是最容易混淆的类型）
        """
        examples = self.get_examples_for_type('Onboarding', exclude_product)
        
        if not examples:
            return ""
        
        lines = [
            "## Onboarding详细示例（从已分析产品中学习）\n",
            "以下是其他产品中被正确识别为Onboarding的页面：\n"
        ]
        
        for ex in examples:
            lines.append(f"**{ex['product']} - {ex['naming_cn']} ({ex['naming_en']})**")
            lines.append(f"- 核心功能：{ex['core_function_cn']}")
            lines.append(f"- 置信度：{ex['confidence']:.0%}")
            lines.append("")
        
        lines.append("如果当前截图的内容与上述示例相似（收集用户信息/偏好/目标），应该分类为Onboarding。\n")
        
        return "\n".join(lines)


# 全局实例
_provider = None

def get_few_shot_provider() -> FewShotProvider:
    """获取全局样本提供器"""
    global _provider
    if _provider is None:
        _provider = FewShotProvider()
    return _provider


def get_examples_prompt(exclude_product: str = None) -> str:
    """便捷函数：获取示例提示词"""
    return get_few_shot_provider().get_examples_prompt(exclude_product=exclude_product)


def get_onboarding_examples(exclude_product: str = None) -> str:
    """便捷函数：获取Onboarding示例"""
    return get_few_shot_provider().get_onboarding_examples(exclude_product=exclude_product)


"""
Few-shot样本获取模块
从数据库中获取高质量分类样本用于提示词增强
"""

import os
import sys
from typing import Dict, List, Optional
import random

# 数据库
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from data.db_manager import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


class FewShotProvider:
    """Few-shot样本提供器"""
    
    # 每种类型获取的样本数
    SAMPLES_PER_TYPE = 2
    
    # 最低置信度要求
    MIN_CONFIDENCE = 0.85
    
    def __init__(self):
        self.db = get_db() if DB_AVAILABLE else None
        self._cache = {}  # 缓存样本
    
    def get_examples_for_type(self, screen_type: str, exclude_product: str = None) -> List[Dict]:
        """
        获取某类型的高质量样本
        
        Args:
            screen_type: 目标类型
            exclude_product: 排除的产品（避免用自己的数据做样本）
        
        Returns:
            样本列表 [{product, filename, naming, core_function, features}]
        """
        if not self.db:
            return []
        
        cache_key = f"{screen_type}_{exclude_product}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # 查询高置信度样本
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT s.*, p.name as product_name, p.folder_name
                FROM screenshots s
                JOIN products p ON s.product_id = p.id
                WHERE s.screen_type = ?
                AND s.confidence >= ?
            """
            params = [screen_type, self.MIN_CONFIDENCE]
            
            if exclude_product:
                query += " AND p.folder_name != ?"
                params.append(exclude_product)
            
            query += " ORDER BY s.confidence DESC LIMIT ?"
            params.append(self.SAMPLES_PER_TYPE * 3)  # 多取一些，随机选
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # 转换为样本格式
            samples = []
            for row in rows:
                samples.append({
                    'product': row['product_name'],
                    'filename': row['filename'],
                    'naming_cn': row['naming_cn'] or '',
                    'naming_en': row['naming_en'] or '',
                    'core_function_cn': row['core_function_cn'] or '',
                    'core_function_en': row['core_function_en'] or '',
                    'confidence': row['confidence']
                })
            
            # 随机选择指定数量
            if len(samples) > self.SAMPLES_PER_TYPE:
                samples = random.sample(samples, self.SAMPLES_PER_TYPE)
            
            self._cache[cache_key] = samples
            return samples
            
        except Exception as e:
            print(f"[FewShot] Error getting examples: {e}")
            return []
    
    def get_examples_prompt(self, target_types: List[str] = None, exclude_product: str = None) -> str:
        """
        生成Few-shot示例提示词
        
        Args:
            target_types: 要获取样本的类型列表（None表示获取常见类型）
            exclude_product: 排除的产品
        
        Returns:
            格式化的示例提示词
        """
        if not self.db:
            return ""
        
        # 默认获取这些容易混淆的类型
        if target_types is None:
            target_types = ['Onboarding', 'Welcome', 'Feature', 'Paywall', 'Home']
        
        lines = ["## 参考示例（来自已分析的其他产品）\n"]
        
        for type_name in target_types:
            examples = self.get_examples_for_type(type_name, exclude_product)
            
            if not examples:
                continue
            
            lines.append(f"### {type_name} 示例：")
            
            for ex in examples:
                lines.append(f"- {ex['product']} - {ex['naming_cn']}")
                lines.append(f"  功能：{ex['core_function_cn']}")
            
            lines.append("")
        
        if len(lines) <= 1:
            return ""  # 没有示例
        
        return "\n".join(lines)
    
    def get_onboarding_examples(self, exclude_product: str = None) -> str:
        """
        专门获取Onboarding的详细示例（因为这是最容易混淆的类型）
        """
        examples = self.get_examples_for_type('Onboarding', exclude_product)
        
        if not examples:
            return ""
        
        lines = [
            "## Onboarding详细示例（从已分析产品中学习）\n",
            "以下是其他产品中被正确识别为Onboarding的页面：\n"
        ]
        
        for ex in examples:
            lines.append(f"**{ex['product']} - {ex['naming_cn']} ({ex['naming_en']})**")
            lines.append(f"- 核心功能：{ex['core_function_cn']}")
            lines.append(f"- 置信度：{ex['confidence']:.0%}")
            lines.append("")
        
        lines.append("如果当前截图的内容与上述示例相似（收集用户信息/偏好/目标），应该分类为Onboarding。\n")
        
        return "\n".join(lines)


# 全局实例
_provider = None

def get_few_shot_provider() -> FewShotProvider:
    """获取全局样本提供器"""
    global _provider
    if _provider is None:
        _provider = FewShotProvider()
    return _provider


def get_examples_prompt(exclude_product: str = None) -> str:
    """便捷函数：获取示例提示词"""
    return get_few_shot_provider().get_examples_prompt(exclude_product=exclude_product)


def get_onboarding_examples(exclude_product: str = None) -> str:
    """便捷函数：获取Onboarding示例"""
    return get_few_shot_provider().get_onboarding_examples(exclude_product=exclude_product)


"""
Few-shot样本获取模块
从数据库中获取高质量分类样本用于提示词增强
"""

import os
import sys
from typing import Dict, List, Optional
import random

# 数据库
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from data.db_manager import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


class FewShotProvider:
    """Few-shot样本提供器"""
    
    # 每种类型获取的样本数
    SAMPLES_PER_TYPE = 2
    
    # 最低置信度要求
    MIN_CONFIDENCE = 0.85
    
    def __init__(self):
        self.db = get_db() if DB_AVAILABLE else None
        self._cache = {}  # 缓存样本
    
    def get_examples_for_type(self, screen_type: str, exclude_product: str = None) -> List[Dict]:
        """
        获取某类型的高质量样本
        
        Args:
            screen_type: 目标类型
            exclude_product: 排除的产品（避免用自己的数据做样本）
        
        Returns:
            样本列表 [{product, filename, naming, core_function, features}]
        """
        if not self.db:
            return []
        
        cache_key = f"{screen_type}_{exclude_product}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # 查询高置信度样本
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT s.*, p.name as product_name, p.folder_name
                FROM screenshots s
                JOIN products p ON s.product_id = p.id
                WHERE s.screen_type = ?
                AND s.confidence >= ?
            """
            params = [screen_type, self.MIN_CONFIDENCE]
            
            if exclude_product:
                query += " AND p.folder_name != ?"
                params.append(exclude_product)
            
            query += " ORDER BY s.confidence DESC LIMIT ?"
            params.append(self.SAMPLES_PER_TYPE * 3)  # 多取一些，随机选
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # 转换为样本格式
            samples = []
            for row in rows:
                samples.append({
                    'product': row['product_name'],
                    'filename': row['filename'],
                    'naming_cn': row['naming_cn'] or '',
                    'naming_en': row['naming_en'] or '',
                    'core_function_cn': row['core_function_cn'] or '',
                    'core_function_en': row['core_function_en'] or '',
                    'confidence': row['confidence']
                })
            
            # 随机选择指定数量
            if len(samples) > self.SAMPLES_PER_TYPE:
                samples = random.sample(samples, self.SAMPLES_PER_TYPE)
            
            self._cache[cache_key] = samples
            return samples
            
        except Exception as e:
            print(f"[FewShot] Error getting examples: {e}")
            return []
    
    def get_examples_prompt(self, target_types: List[str] = None, exclude_product: str = None) -> str:
        """
        生成Few-shot示例提示词
        
        Args:
            target_types: 要获取样本的类型列表（None表示获取常见类型）
            exclude_product: 排除的产品
        
        Returns:
            格式化的示例提示词
        """
        if not self.db:
            return ""
        
        # 默认获取这些容易混淆的类型
        if target_types is None:
            target_types = ['Onboarding', 'Welcome', 'Feature', 'Paywall', 'Home']
        
        lines = ["## 参考示例（来自已分析的其他产品）\n"]
        
        for type_name in target_types:
            examples = self.get_examples_for_type(type_name, exclude_product)
            
            if not examples:
                continue
            
            lines.append(f"### {type_name} 示例：")
            
            for ex in examples:
                lines.append(f"- {ex['product']} - {ex['naming_cn']}")
                lines.append(f"  功能：{ex['core_function_cn']}")
            
            lines.append("")
        
        if len(lines) <= 1:
            return ""  # 没有示例
        
        return "\n".join(lines)
    
    def get_onboarding_examples(self, exclude_product: str = None) -> str:
        """
        专门获取Onboarding的详细示例（因为这是最容易混淆的类型）
        """
        examples = self.get_examples_for_type('Onboarding', exclude_product)
        
        if not examples:
            return ""
        
        lines = [
            "## Onboarding详细示例（从已分析产品中学习）\n",
            "以下是其他产品中被正确识别为Onboarding的页面：\n"
        ]
        
        for ex in examples:
            lines.append(f"**{ex['product']} - {ex['naming_cn']} ({ex['naming_en']})**")
            lines.append(f"- 核心功能：{ex['core_function_cn']}")
            lines.append(f"- 置信度：{ex['confidence']:.0%}")
            lines.append("")
        
        lines.append("如果当前截图的内容与上述示例相似（收集用户信息/偏好/目标），应该分类为Onboarding。\n")
        
        return "\n".join(lines)


# 全局实例
_provider = None

def get_few_shot_provider() -> FewShotProvider:
    """获取全局样本提供器"""
    global _provider
    if _provider is None:
        _provider = FewShotProvider()
    return _provider


def get_examples_prompt(exclude_product: str = None) -> str:
    """便捷函数：获取示例提示词"""
    return get_few_shot_provider().get_examples_prompt(exclude_product=exclude_product)


def get_onboarding_examples(exclude_product: str = None) -> str:
    """便捷函数：获取Onboarding示例"""
    return get_few_shot_provider().get_onboarding_examples(exclude_product=exclude_product)


"""
Few-shot样本获取模块
从数据库中获取高质量分类样本用于提示词增强
"""

import os
import sys
from typing import Dict, List, Optional
import random

# 数据库
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from data.db_manager import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


class FewShotProvider:
    """Few-shot样本提供器"""
    
    # 每种类型获取的样本数
    SAMPLES_PER_TYPE = 2
    
    # 最低置信度要求
    MIN_CONFIDENCE = 0.85
    
    def __init__(self):
        self.db = get_db() if DB_AVAILABLE else None
        self._cache = {}  # 缓存样本
    
    def get_examples_for_type(self, screen_type: str, exclude_product: str = None) -> List[Dict]:
        """
        获取某类型的高质量样本
        
        Args:
            screen_type: 目标类型
            exclude_product: 排除的产品（避免用自己的数据做样本）
        
        Returns:
            样本列表 [{product, filename, naming, core_function, features}]
        """
        if not self.db:
            return []
        
        cache_key = f"{screen_type}_{exclude_product}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # 查询高置信度样本
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT s.*, p.name as product_name, p.folder_name
                FROM screenshots s
                JOIN products p ON s.product_id = p.id
                WHERE s.screen_type = ?
                AND s.confidence >= ?
            """
            params = [screen_type, self.MIN_CONFIDENCE]
            
            if exclude_product:
                query += " AND p.folder_name != ?"
                params.append(exclude_product)
            
            query += " ORDER BY s.confidence DESC LIMIT ?"
            params.append(self.SAMPLES_PER_TYPE * 3)  # 多取一些，随机选
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # 转换为样本格式
            samples = []
            for row in rows:
                samples.append({
                    'product': row['product_name'],
                    'filename': row['filename'],
                    'naming_cn': row['naming_cn'] or '',
                    'naming_en': row['naming_en'] or '',
                    'core_function_cn': row['core_function_cn'] or '',
                    'core_function_en': row['core_function_en'] or '',
                    'confidence': row['confidence']
                })
            
            # 随机选择指定数量
            if len(samples) > self.SAMPLES_PER_TYPE:
                samples = random.sample(samples, self.SAMPLES_PER_TYPE)
            
            self._cache[cache_key] = samples
            return samples
            
        except Exception as e:
            print(f"[FewShot] Error getting examples: {e}")
            return []
    
    def get_examples_prompt(self, target_types: List[str] = None, exclude_product: str = None) -> str:
        """
        生成Few-shot示例提示词
        
        Args:
            target_types: 要获取样本的类型列表（None表示获取常见类型）
            exclude_product: 排除的产品
        
        Returns:
            格式化的示例提示词
        """
        if not self.db:
            return ""
        
        # 默认获取这些容易混淆的类型
        if target_types is None:
            target_types = ['Onboarding', 'Welcome', 'Feature', 'Paywall', 'Home']
        
        lines = ["## 参考示例（来自已分析的其他产品）\n"]
        
        for type_name in target_types:
            examples = self.get_examples_for_type(type_name, exclude_product)
            
            if not examples:
                continue
            
            lines.append(f"### {type_name} 示例：")
            
            for ex in examples:
                lines.append(f"- {ex['product']} - {ex['naming_cn']}")
                lines.append(f"  功能：{ex['core_function_cn']}")
            
            lines.append("")
        
        if len(lines) <= 1:
            return ""  # 没有示例
        
        return "\n".join(lines)
    
    def get_onboarding_examples(self, exclude_product: str = None) -> str:
        """
        专门获取Onboarding的详细示例（因为这是最容易混淆的类型）
        """
        examples = self.get_examples_for_type('Onboarding', exclude_product)
        
        if not examples:
            return ""
        
        lines = [
            "## Onboarding详细示例（从已分析产品中学习）\n",
            "以下是其他产品中被正确识别为Onboarding的页面：\n"
        ]
        
        for ex in examples:
            lines.append(f"**{ex['product']} - {ex['naming_cn']} ({ex['naming_en']})**")
            lines.append(f"- 核心功能：{ex['core_function_cn']}")
            lines.append(f"- 置信度：{ex['confidence']:.0%}")
            lines.append("")
        
        lines.append("如果当前截图的内容与上述示例相似（收集用户信息/偏好/目标），应该分类为Onboarding。\n")
        
        return "\n".join(lines)


# 全局实例
_provider = None

def get_few_shot_provider() -> FewShotProvider:
    """获取全局样本提供器"""
    global _provider
    if _provider is None:
        _provider = FewShotProvider()
    return _provider


def get_examples_prompt(exclude_product: str = None) -> str:
    """便捷函数：获取示例提示词"""
    return get_few_shot_provider().get_examples_prompt(exclude_product=exclude_product)


def get_onboarding_examples(exclude_product: str = None) -> str:
    """便捷函数：获取Onboarding示例"""
    return get_few_shot_provider().get_onboarding_examples(exclude_product=exclude_product)



"""
Few-shot样本获取模块
从数据库中获取高质量分类样本用于提示词增强
"""

import os
import sys
from typing import Dict, List, Optional
import random

# 数据库
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from data.db_manager import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


class FewShotProvider:
    """Few-shot样本提供器"""
    
    # 每种类型获取的样本数
    SAMPLES_PER_TYPE = 2
    
    # 最低置信度要求
    MIN_CONFIDENCE = 0.85
    
    def __init__(self):
        self.db = get_db() if DB_AVAILABLE else None
        self._cache = {}  # 缓存样本
    
    def get_examples_for_type(self, screen_type: str, exclude_product: str = None) -> List[Dict]:
        """
        获取某类型的高质量样本
        
        Args:
            screen_type: 目标类型
            exclude_product: 排除的产品（避免用自己的数据做样本）
        
        Returns:
            样本列表 [{product, filename, naming, core_function, features}]
        """
        if not self.db:
            return []
        
        cache_key = f"{screen_type}_{exclude_product}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # 查询高置信度样本
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT s.*, p.name as product_name, p.folder_name
                FROM screenshots s
                JOIN products p ON s.product_id = p.id
                WHERE s.screen_type = ?
                AND s.confidence >= ?
            """
            params = [screen_type, self.MIN_CONFIDENCE]
            
            if exclude_product:
                query += " AND p.folder_name != ?"
                params.append(exclude_product)
            
            query += " ORDER BY s.confidence DESC LIMIT ?"
            params.append(self.SAMPLES_PER_TYPE * 3)  # 多取一些，随机选
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # 转换为样本格式
            samples = []
            for row in rows:
                samples.append({
                    'product': row['product_name'],
                    'filename': row['filename'],
                    'naming_cn': row['naming_cn'] or '',
                    'naming_en': row['naming_en'] or '',
                    'core_function_cn': row['core_function_cn'] or '',
                    'core_function_en': row['core_function_en'] or '',
                    'confidence': row['confidence']
                })
            
            # 随机选择指定数量
            if len(samples) > self.SAMPLES_PER_TYPE:
                samples = random.sample(samples, self.SAMPLES_PER_TYPE)
            
            self._cache[cache_key] = samples
            return samples
            
        except Exception as e:
            print(f"[FewShot] Error getting examples: {e}")
            return []
    
    def get_examples_prompt(self, target_types: List[str] = None, exclude_product: str = None) -> str:
        """
        生成Few-shot示例提示词
        
        Args:
            target_types: 要获取样本的类型列表（None表示获取常见类型）
            exclude_product: 排除的产品
        
        Returns:
            格式化的示例提示词
        """
        if not self.db:
            return ""
        
        # 默认获取这些容易混淆的类型
        if target_types is None:
            target_types = ['Onboarding', 'Welcome', 'Feature', 'Paywall', 'Home']
        
        lines = ["## 参考示例（来自已分析的其他产品）\n"]
        
        for type_name in target_types:
            examples = self.get_examples_for_type(type_name, exclude_product)
            
            if not examples:
                continue
            
            lines.append(f"### {type_name} 示例：")
            
            for ex in examples:
                lines.append(f"- {ex['product']} - {ex['naming_cn']}")
                lines.append(f"  功能：{ex['core_function_cn']}")
            
            lines.append("")
        
        if len(lines) <= 1:
            return ""  # 没有示例
        
        return "\n".join(lines)
    
    def get_onboarding_examples(self, exclude_product: str = None) -> str:
        """
        专门获取Onboarding的详细示例（因为这是最容易混淆的类型）
        """
        examples = self.get_examples_for_type('Onboarding', exclude_product)
        
        if not examples:
            return ""
        
        lines = [
            "## Onboarding详细示例（从已分析产品中学习）\n",
            "以下是其他产品中被正确识别为Onboarding的页面：\n"
        ]
        
        for ex in examples:
            lines.append(f"**{ex['product']} - {ex['naming_cn']} ({ex['naming_en']})**")
            lines.append(f"- 核心功能：{ex['core_function_cn']}")
            lines.append(f"- 置信度：{ex['confidence']:.0%}")
            lines.append("")
        
        lines.append("如果当前截图的内容与上述示例相似（收集用户信息/偏好/目标），应该分类为Onboarding。\n")
        
        return "\n".join(lines)


# 全局实例
_provider = None

def get_few_shot_provider() -> FewShotProvider:
    """获取全局样本提供器"""
    global _provider
    if _provider is None:
        _provider = FewShotProvider()
    return _provider


def get_examples_prompt(exclude_product: str = None) -> str:
    """便捷函数：获取示例提示词"""
    return get_few_shot_provider().get_examples_prompt(exclude_product=exclude_product)


def get_onboarding_examples(exclude_product: str = None) -> str:
    """便捷函数：获取Onboarding示例"""
    return get_few_shot_provider().get_onboarding_examples(exclude_product=exclude_product)


"""
Few-shot样本获取模块
从数据库中获取高质量分类样本用于提示词增强
"""

import os
import sys
from typing import Dict, List, Optional
import random

# 数据库
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from data.db_manager import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


class FewShotProvider:
    """Few-shot样本提供器"""
    
    # 每种类型获取的样本数
    SAMPLES_PER_TYPE = 2
    
    # 最低置信度要求
    MIN_CONFIDENCE = 0.85
    
    def __init__(self):
        self.db = get_db() if DB_AVAILABLE else None
        self._cache = {}  # 缓存样本
    
    def get_examples_for_type(self, screen_type: str, exclude_product: str = None) -> List[Dict]:
        """
        获取某类型的高质量样本
        
        Args:
            screen_type: 目标类型
            exclude_product: 排除的产品（避免用自己的数据做样本）
        
        Returns:
            样本列表 [{product, filename, naming, core_function, features}]
        """
        if not self.db:
            return []
        
        cache_key = f"{screen_type}_{exclude_product}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # 查询高置信度样本
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT s.*, p.name as product_name, p.folder_name
                FROM screenshots s
                JOIN products p ON s.product_id = p.id
                WHERE s.screen_type = ?
                AND s.confidence >= ?
            """
            params = [screen_type, self.MIN_CONFIDENCE]
            
            if exclude_product:
                query += " AND p.folder_name != ?"
                params.append(exclude_product)
            
            query += " ORDER BY s.confidence DESC LIMIT ?"
            params.append(self.SAMPLES_PER_TYPE * 3)  # 多取一些，随机选
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # 转换为样本格式
            samples = []
            for row in rows:
                samples.append({
                    'product': row['product_name'],
                    'filename': row['filename'],
                    'naming_cn': row['naming_cn'] or '',
                    'naming_en': row['naming_en'] or '',
                    'core_function_cn': row['core_function_cn'] or '',
                    'core_function_en': row['core_function_en'] or '',
                    'confidence': row['confidence']
                })
            
            # 随机选择指定数量
            if len(samples) > self.SAMPLES_PER_TYPE:
                samples = random.sample(samples, self.SAMPLES_PER_TYPE)
            
            self._cache[cache_key] = samples
            return samples
            
        except Exception as e:
            print(f"[FewShot] Error getting examples: {e}")
            return []
    
    def get_examples_prompt(self, target_types: List[str] = None, exclude_product: str = None) -> str:
        """
        生成Few-shot示例提示词
        
        Args:
            target_types: 要获取样本的类型列表（None表示获取常见类型）
            exclude_product: 排除的产品
        
        Returns:
            格式化的示例提示词
        """
        if not self.db:
            return ""
        
        # 默认获取这些容易混淆的类型
        if target_types is None:
            target_types = ['Onboarding', 'Welcome', 'Feature', 'Paywall', 'Home']
        
        lines = ["## 参考示例（来自已分析的其他产品）\n"]
        
        for type_name in target_types:
            examples = self.get_examples_for_type(type_name, exclude_product)
            
            if not examples:
                continue
            
            lines.append(f"### {type_name} 示例：")
            
            for ex in examples:
                lines.append(f"- {ex['product']} - {ex['naming_cn']}")
                lines.append(f"  功能：{ex['core_function_cn']}")
            
            lines.append("")
        
        if len(lines) <= 1:
            return ""  # 没有示例
        
        return "\n".join(lines)
    
    def get_onboarding_examples(self, exclude_product: str = None) -> str:
        """
        专门获取Onboarding的详细示例（因为这是最容易混淆的类型）
        """
        examples = self.get_examples_for_type('Onboarding', exclude_product)
        
        if not examples:
            return ""
        
        lines = [
            "## Onboarding详细示例（从已分析产品中学习）\n",
            "以下是其他产品中被正确识别为Onboarding的页面：\n"
        ]
        
        for ex in examples:
            lines.append(f"**{ex['product']} - {ex['naming_cn']} ({ex['naming_en']})**")
            lines.append(f"- 核心功能：{ex['core_function_cn']}")
            lines.append(f"- 置信度：{ex['confidence']:.0%}")
            lines.append("")
        
        lines.append("如果当前截图的内容与上述示例相似（收集用户信息/偏好/目标），应该分类为Onboarding。\n")
        
        return "\n".join(lines)


# 全局实例
_provider = None

def get_few_shot_provider() -> FewShotProvider:
    """获取全局样本提供器"""
    global _provider
    if _provider is None:
        _provider = FewShotProvider()
    return _provider


def get_examples_prompt(exclude_product: str = None) -> str:
    """便捷函数：获取示例提示词"""
    return get_few_shot_provider().get_examples_prompt(exclude_product=exclude_product)


def get_onboarding_examples(exclude_product: str = None) -> str:
    """便捷函数：获取Onboarding示例"""
    return get_few_shot_provider().get_onboarding_examples(exclude_product=exclude_product)










































