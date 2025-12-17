# -*- coding: utf-8 -*-
"""
Sitemap分析模块
基于静态截图推断App的页面结构和导航关系
"""

import os
import sys
import json
import base64
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# API
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class PageNode:
    """页面节点"""
    id: str                     # 唯一ID
    name: str                   # 页面名称
    screen_type: str            # 类型（Home/Feature/Content等）
    level: int                  # 层级（1=Tab页, 2=二级页, 3=三级页）
    parent_id: Optional[str]    # 父页面ID
    children: List[str]         # 子页面ID列表
    tab_name: Optional[str]     # 所属Tab名称
    is_modal: bool              # 是否是模态弹窗
    screenshots: List[str]      # 对应的截图文件名


@dataclass  
class SitemapResult:
    """Sitemap分析结果"""
    app_name: str
    tabs: List[Dict]            # Tab结构
    pages: Dict[str, PageNode]  # 所有页面
    navigation_paths: List[Dict] # 导航路径
    mermaid_diagram: str        # Mermaid图表


class SitemapAnalyzer:
    """Sitemap分析器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self.client = None
        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _load_api_key(self) -> str:
        """加载API Key"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config', 'api_keys.json'
        )
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config.get('ANTHROPIC_API_KEY', '')
        return os.environ.get('ANTHROPIC_API_KEY', '')
    
    def analyze(self, project_name: str) -> SitemapResult:
        """
        分析项目生成Sitemap
        
        Args:
            project_name: 项目名称（如Calm_Analysis）
        
        Returns:
            SitemapResult
        """
        print(f"\n{'='*60}")
        print(f"  SITEMAP ANALYZER - {project_name}")
        print(f"{'='*60}")
        
        # 加载分析结果
        project_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'projects', project_name
        )
        
        analysis_file = os.path.join(project_path, 'ai_analysis.json')
        if not os.path.exists(analysis_file):
            raise FileNotFoundError(f"Analysis file not found: {analysis_file}")
        
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        results = analysis_data.get('results', {})
        app_name = project_name.replace('_Analysis', '').replace('_', ' ')
        
        print(f"\n  Total Screenshots: {len(results)}")
        
        # Step 1: 识别Tab结构
        print(f"\n  [Step 1] Identifying Tab structure...")
        tabs = self._identify_tabs(results, project_path)
        print(f"  Found {len(tabs)} tabs: {[t['name'] for t in tabs]}")
        
        # Step 2: 构建页面层级
        print(f"\n  [Step 2] Building page hierarchy...")
        pages = self._build_hierarchy(results, tabs)
        print(f"  Built {len(pages)} page nodes")
        
        # Step 3: 推断导航路径
        print(f"\n  [Step 3] Inferring navigation paths...")
        paths = self._infer_navigation(results, pages)
        print(f"  Found {len(paths)} navigation paths")
        
        # Step 4: 生成Mermaid图
        print(f"\n  [Step 4] Generating Mermaid diagram...")
        mermaid = self._generate_mermaid(app_name, tabs, pages, paths)
        
        result = SitemapResult(
            app_name=app_name,
            tabs=tabs,
            pages={k: asdict(v) for k, v in pages.items()},
            navigation_paths=paths,
            mermaid_diagram=mermaid
        )
        
        # 保存结果
        output_file = os.path.join(project_path, 'sitemap.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)
        
        print(f"\n  Output: {output_file}")
        print(f"{'='*60}")
        
        return result
    
    def _identify_tabs(self, results: Dict, project_path: str) -> List[Dict]:
        """识别底部Tab结构"""
        tabs = []
        
        # 找所有Home类型的页面（通常是Tab入口）
        home_screens = []
        for filename, data in results.items():
            if data.get('screen_type') == 'Home':
                home_screens.append({
                    'filename': filename,
                    'index': data.get('index', 0),
                    'name': data.get('naming', {}).get('cn', '首页')
                })
        
        # 如果有多个Home，可能是不同Tab
        if len(home_screens) >= 1:
            # 用AI分析Tab结构
            tabs = self._ai_analyze_tabs(results, project_path)
        
        # 如果AI分析失败，用默认结构
        if not tabs:
            tabs = self._default_tabs(results)
        
        return tabs
    
    def _ai_analyze_tabs(self, results: Dict, project_path: str) -> List[Dict]:
        """用AI分析Tab结构"""
        if not self.client:
            return []
        
        # 收集所有screen_type
        type_counts = defaultdict(int)
        for data in results.values():
            st = data.get('screen_type', 'Unknown')
            type_counts[st] += 1
        
        # 构建提示词
        prompt = f"""分析这个App的底部Tab结构。

已知的页面类型分布：
{json.dumps(dict(type_counts), ensure_ascii=False, indent=2)}

根据常见的健康/冥想App设计模式，推断可能的Tab结构。

请返回JSON格式：
```json
{{
  "tabs": [
    {{"name": "Home", "icon": "home", "screen_types": ["Home"]}},
    {{"name": "Explore", "icon": "search", "screen_types": ["Content", "Feature"]}},
    {{"name": "Sleep", "icon": "moon", "screen_types": ["Content"]}},
    {{"name": "Profile", "icon": "user", "screen_types": ["Profile", "Settings"]}}
  ]
}}
```

只返回JSON，不要解释。"""

        try:
            response = self.client.messages.create(
                model='claude-sonnet-4-20250514',
                max_tokens=1000,
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            text = response.content[0].text
            # 提取JSON
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            
            data = json.loads(text.strip())
            return data.get('tabs', [])
            
        except Exception as e:
            print(f"  [Warning] AI tab analysis failed: {e}")
            return []
    
    def _default_tabs(self, results: Dict) -> List[Dict]:
        """默认Tab结构"""
        return [
            {"name": "Home", "icon": "home", "screen_types": ["Home"]},
            {"name": "Content", "icon": "play", "screen_types": ["Content", "Feature"]},
            {"name": "Tracking", "icon": "chart", "screen_types": ["Tracking", "Progress"]},
            {"name": "Profile", "icon": "user", "screen_types": ["Profile", "Settings"]}
        ]
    
    def _build_hierarchy(self, results: Dict, tabs: List[Dict]) -> Dict[str, PageNode]:
        """构建页面层级"""
        pages = {}
        
        # 按screen_type分组
        type_groups = defaultdict(list)
        for filename, data in results.items():
            st = data.get('screen_type', 'Unknown')
            type_groups[st].append({
                'filename': filename,
                'data': data
            })
        
        # 创建Tab页面（Level 1）
        for tab in tabs:
            tab_id = f"tab_{tab['name'].lower()}"
            pages[tab_id] = PageNode(
                id=tab_id,
                name=tab['name'],
                screen_type='Tab',
                level=1,
                parent_id=None,
                children=[],
                tab_name=tab['name'],
                is_modal=False,
                screenshots=[]
            )
        
        # 分配页面到Tab下（Level 2）
        for screen_type, items in type_groups.items():
            # 找对应的Tab
            parent_tab = None
            for tab in tabs:
                if screen_type in tab.get('screen_types', []):
                    parent_tab = f"tab_{tab['name'].lower()}"
                    break
            
            if not parent_tab:
                parent_tab = "tab_other"
                if parent_tab not in pages:
                    pages[parent_tab] = PageNode(
                        id=parent_tab,
                        name="Other",
                        screen_type='Tab',
                        level=1,
                        parent_id=None,
                        children=[],
                        tab_name="Other",
                        is_modal=False,
                        screenshots=[]
                    )
            
            # 创建二级页面
            page_id = f"page_{screen_type.lower()}"
            screenshots = [item['filename'] for item in items]
            
            pages[page_id] = PageNode(
                id=page_id,
                name=screen_type,
                screen_type=screen_type,
                level=2,
                parent_id=parent_tab,
                children=[],
                tab_name=pages[parent_tab].name if parent_tab in pages else None,
                is_modal=screen_type in ['Paywall', 'Referral', 'Permission'],
                screenshots=screenshots
            )
            
            # 添加到父节点
            if parent_tab in pages:
                pages[parent_tab].children.append(page_id)
        
        return pages
    
    def _infer_navigation(self, results: Dict, pages: Dict[str, PageNode]) -> List[Dict]:
        """推断导航路径"""
        paths = []
        
        # 基于截图顺序推断流程
        sorted_results = sorted(
            [(f, d) for f, d in results.items()],
            key=lambda x: x[1].get('index', 0)
        )
        
        # 找连续的类型变化
        prev_type = None
        for filename, data in sorted_results:
            curr_type = data.get('screen_type', 'Unknown')
            
            if prev_type and prev_type != curr_type:
                paths.append({
                    'from': f"page_{prev_type.lower()}",
                    'to': f"page_{curr_type.lower()}",
                    'type': 'flow'  # 流程跳转
                })
            
            prev_type = curr_type
        
        # 去重
        seen = set()
        unique_paths = []
        for p in paths:
            key = f"{p['from']}->{p['to']}"
            if key not in seen:
                seen.add(key)
                unique_paths.append(p)
        
        return unique_paths
    
    def _generate_mermaid(self, app_name: str, tabs: List[Dict], 
                          pages: Dict[str, PageNode], paths: List[Dict]) -> str:
        """生成Mermaid图表"""
        lines = [
            "graph TD",
            f"    App[{app_name}]"
        ]
        
        # 添加Tab节点
        for tab in tabs:
            tab_id = f"tab_{tab['name'].lower()}"
            lines.append(f"    App --> {tab_id}[{tab['name']}]")
        
        # 添加二级页面
        for page_id, page in pages.items():
            if page.level == 2 and page.parent_id:
                # 简化名称
                display_name = page.name
                count = len(page.screenshots)
                if count > 0:
                    display_name = f"{page.name} ({count})"
                
                lines.append(f"    {page.parent_id} --> {page_id}[{display_name}]")
        
        # 添加导航路径（用虚线）
        for path in paths[:10]:  # 只显示前10个，避免太乱
            if path['from'] in pages and path['to'] in pages:
                lines.append(f"    {path['from']} -.-> {path['to']}")
        
        return "\n".join(lines)


def analyze_sitemap(project_name: str) -> SitemapResult:
    """便捷函数"""
    analyzer = SitemapAnalyzer()
    return analyzer.analyze(project_name)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        project = sys.argv[1]
    else:
        project = "Calm_Analysis"
    
    result = analyze_sitemap(project)
    
    print("\n" + "="*60)
    print("  MERMAID DIAGRAM")
    print("="*60)
    print(result.mermaid_diagram)


Sitemap分析模块
基于静态截图推断App的页面结构和导航关系
"""

import os
import sys
import json
import base64
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# API
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class PageNode:
    """页面节点"""
    id: str                     # 唯一ID
    name: str                   # 页面名称
    screen_type: str            # 类型（Home/Feature/Content等）
    level: int                  # 层级（1=Tab页, 2=二级页, 3=三级页）
    parent_id: Optional[str]    # 父页面ID
    children: List[str]         # 子页面ID列表
    tab_name: Optional[str]     # 所属Tab名称
    is_modal: bool              # 是否是模态弹窗
    screenshots: List[str]      # 对应的截图文件名


@dataclass  
class SitemapResult:
    """Sitemap分析结果"""
    app_name: str
    tabs: List[Dict]            # Tab结构
    pages: Dict[str, PageNode]  # 所有页面
    navigation_paths: List[Dict] # 导航路径
    mermaid_diagram: str        # Mermaid图表


class SitemapAnalyzer:
    """Sitemap分析器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self.client = None
        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _load_api_key(self) -> str:
        """加载API Key"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config', 'api_keys.json'
        )
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config.get('ANTHROPIC_API_KEY', '')
        return os.environ.get('ANTHROPIC_API_KEY', '')
    
    def analyze(self, project_name: str) -> SitemapResult:
        """
        分析项目生成Sitemap
        
        Args:
            project_name: 项目名称（如Calm_Analysis）
        
        Returns:
            SitemapResult
        """
        print(f"\n{'='*60}")
        print(f"  SITEMAP ANALYZER - {project_name}")
        print(f"{'='*60}")
        
        # 加载分析结果
        project_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'projects', project_name
        )
        
        analysis_file = os.path.join(project_path, 'ai_analysis.json')
        if not os.path.exists(analysis_file):
            raise FileNotFoundError(f"Analysis file not found: {analysis_file}")
        
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        results = analysis_data.get('results', {})
        app_name = project_name.replace('_Analysis', '').replace('_', ' ')
        
        print(f"\n  Total Screenshots: {len(results)}")
        
        # Step 1: 识别Tab结构
        print(f"\n  [Step 1] Identifying Tab structure...")
        tabs = self._identify_tabs(results, project_path)
        print(f"  Found {len(tabs)} tabs: {[t['name'] for t in tabs]}")
        
        # Step 2: 构建页面层级
        print(f"\n  [Step 2] Building page hierarchy...")
        pages = self._build_hierarchy(results, tabs)
        print(f"  Built {len(pages)} page nodes")
        
        # Step 3: 推断导航路径
        print(f"\n  [Step 3] Inferring navigation paths...")
        paths = self._infer_navigation(results, pages)
        print(f"  Found {len(paths)} navigation paths")
        
        # Step 4: 生成Mermaid图
        print(f"\n  [Step 4] Generating Mermaid diagram...")
        mermaid = self._generate_mermaid(app_name, tabs, pages, paths)
        
        result = SitemapResult(
            app_name=app_name,
            tabs=tabs,
            pages={k: asdict(v) for k, v in pages.items()},
            navigation_paths=paths,
            mermaid_diagram=mermaid
        )
        
        # 保存结果
        output_file = os.path.join(project_path, 'sitemap.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)
        
        print(f"\n  Output: {output_file}")
        print(f"{'='*60}")
        
        return result
    
    def _identify_tabs(self, results: Dict, project_path: str) -> List[Dict]:
        """识别底部Tab结构"""
        tabs = []
        
        # 找所有Home类型的页面（通常是Tab入口）
        home_screens = []
        for filename, data in results.items():
            if data.get('screen_type') == 'Home':
                home_screens.append({
                    'filename': filename,
                    'index': data.get('index', 0),
                    'name': data.get('naming', {}).get('cn', '首页')
                })
        
        # 如果有多个Home，可能是不同Tab
        if len(home_screens) >= 1:
            # 用AI分析Tab结构
            tabs = self._ai_analyze_tabs(results, project_path)
        
        # 如果AI分析失败，用默认结构
        if not tabs:
            tabs = self._default_tabs(results)
        
        return tabs
    
    def _ai_analyze_tabs(self, results: Dict, project_path: str) -> List[Dict]:
        """用AI分析Tab结构"""
        if not self.client:
            return []
        
        # 收集所有screen_type
        type_counts = defaultdict(int)
        for data in results.values():
            st = data.get('screen_type', 'Unknown')
            type_counts[st] += 1
        
        # 构建提示词
        prompt = f"""分析这个App的底部Tab结构。

已知的页面类型分布：
{json.dumps(dict(type_counts), ensure_ascii=False, indent=2)}

根据常见的健康/冥想App设计模式，推断可能的Tab结构。

请返回JSON格式：
```json
{{
  "tabs": [
    {{"name": "Home", "icon": "home", "screen_types": ["Home"]}},
    {{"name": "Explore", "icon": "search", "screen_types": ["Content", "Feature"]}},
    {{"name": "Sleep", "icon": "moon", "screen_types": ["Content"]}},
    {{"name": "Profile", "icon": "user", "screen_types": ["Profile", "Settings"]}}
  ]
}}
```

只返回JSON，不要解释。"""

        try:
            response = self.client.messages.create(
                model='claude-sonnet-4-20250514',
                max_tokens=1000,
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            text = response.content[0].text
            # 提取JSON
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            
            data = json.loads(text.strip())
            return data.get('tabs', [])
            
        except Exception as e:
            print(f"  [Warning] AI tab analysis failed: {e}")
            return []
    
    def _default_tabs(self, results: Dict) -> List[Dict]:
        """默认Tab结构"""
        return [
            {"name": "Home", "icon": "home", "screen_types": ["Home"]},
            {"name": "Content", "icon": "play", "screen_types": ["Content", "Feature"]},
            {"name": "Tracking", "icon": "chart", "screen_types": ["Tracking", "Progress"]},
            {"name": "Profile", "icon": "user", "screen_types": ["Profile", "Settings"]}
        ]
    
    def _build_hierarchy(self, results: Dict, tabs: List[Dict]) -> Dict[str, PageNode]:
        """构建页面层级"""
        pages = {}
        
        # 按screen_type分组
        type_groups = defaultdict(list)
        for filename, data in results.items():
            st = data.get('screen_type', 'Unknown')
            type_groups[st].append({
                'filename': filename,
                'data': data
            })
        
        # 创建Tab页面（Level 1）
        for tab in tabs:
            tab_id = f"tab_{tab['name'].lower()}"
            pages[tab_id] = PageNode(
                id=tab_id,
                name=tab['name'],
                screen_type='Tab',
                level=1,
                parent_id=None,
                children=[],
                tab_name=tab['name'],
                is_modal=False,
                screenshots=[]
            )
        
        # 分配页面到Tab下（Level 2）
        for screen_type, items in type_groups.items():
            # 找对应的Tab
            parent_tab = None
            for tab in tabs:
                if screen_type in tab.get('screen_types', []):
                    parent_tab = f"tab_{tab['name'].lower()}"
                    break
            
            if not parent_tab:
                parent_tab = "tab_other"
                if parent_tab not in pages:
                    pages[parent_tab] = PageNode(
                        id=parent_tab,
                        name="Other",
                        screen_type='Tab',
                        level=1,
                        parent_id=None,
                        children=[],
                        tab_name="Other",
                        is_modal=False,
                        screenshots=[]
                    )
            
            # 创建二级页面
            page_id = f"page_{screen_type.lower()}"
            screenshots = [item['filename'] for item in items]
            
            pages[page_id] = PageNode(
                id=page_id,
                name=screen_type,
                screen_type=screen_type,
                level=2,
                parent_id=parent_tab,
                children=[],
                tab_name=pages[parent_tab].name if parent_tab in pages else None,
                is_modal=screen_type in ['Paywall', 'Referral', 'Permission'],
                screenshots=screenshots
            )
            
            # 添加到父节点
            if parent_tab in pages:
                pages[parent_tab].children.append(page_id)
        
        return pages
    
    def _infer_navigation(self, results: Dict, pages: Dict[str, PageNode]) -> List[Dict]:
        """推断导航路径"""
        paths = []
        
        # 基于截图顺序推断流程
        sorted_results = sorted(
            [(f, d) for f, d in results.items()],
            key=lambda x: x[1].get('index', 0)
        )
        
        # 找连续的类型变化
        prev_type = None
        for filename, data in sorted_results:
            curr_type = data.get('screen_type', 'Unknown')
            
            if prev_type and prev_type != curr_type:
                paths.append({
                    'from': f"page_{prev_type.lower()}",
                    'to': f"page_{curr_type.lower()}",
                    'type': 'flow'  # 流程跳转
                })
            
            prev_type = curr_type
        
        # 去重
        seen = set()
        unique_paths = []
        for p in paths:
            key = f"{p['from']}->{p['to']}"
            if key not in seen:
                seen.add(key)
                unique_paths.append(p)
        
        return unique_paths
    
    def _generate_mermaid(self, app_name: str, tabs: List[Dict], 
                          pages: Dict[str, PageNode], paths: List[Dict]) -> str:
        """生成Mermaid图表"""
        lines = [
            "graph TD",
            f"    App[{app_name}]"
        ]
        
        # 添加Tab节点
        for tab in tabs:
            tab_id = f"tab_{tab['name'].lower()}"
            lines.append(f"    App --> {tab_id}[{tab['name']}]")
        
        # 添加二级页面
        for page_id, page in pages.items():
            if page.level == 2 and page.parent_id:
                # 简化名称
                display_name = page.name
                count = len(page.screenshots)
                if count > 0:
                    display_name = f"{page.name} ({count})"
                
                lines.append(f"    {page.parent_id} --> {page_id}[{display_name}]")
        
        # 添加导航路径（用虚线）
        for path in paths[:10]:  # 只显示前10个，避免太乱
            if path['from'] in pages and path['to'] in pages:
                lines.append(f"    {path['from']} -.-> {path['to']}")
        
        return "\n".join(lines)


def analyze_sitemap(project_name: str) -> SitemapResult:
    """便捷函数"""
    analyzer = SitemapAnalyzer()
    return analyzer.analyze(project_name)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        project = sys.argv[1]
    else:
        project = "Calm_Analysis"
    
    result = analyze_sitemap(project)
    
    print("\n" + "="*60)
    print("  MERMAID DIAGRAM")
    print("="*60)
    print(result.mermaid_diagram)


Sitemap分析模块
基于静态截图推断App的页面结构和导航关系
"""

import os
import sys
import json
import base64
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# API
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class PageNode:
    """页面节点"""
    id: str                     # 唯一ID
    name: str                   # 页面名称
    screen_type: str            # 类型（Home/Feature/Content等）
    level: int                  # 层级（1=Tab页, 2=二级页, 3=三级页）
    parent_id: Optional[str]    # 父页面ID
    children: List[str]         # 子页面ID列表
    tab_name: Optional[str]     # 所属Tab名称
    is_modal: bool              # 是否是模态弹窗
    screenshots: List[str]      # 对应的截图文件名


@dataclass  
class SitemapResult:
    """Sitemap分析结果"""
    app_name: str
    tabs: List[Dict]            # Tab结构
    pages: Dict[str, PageNode]  # 所有页面
    navigation_paths: List[Dict] # 导航路径
    mermaid_diagram: str        # Mermaid图表


class SitemapAnalyzer:
    """Sitemap分析器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self.client = None
        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _load_api_key(self) -> str:
        """加载API Key"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config', 'api_keys.json'
        )
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config.get('ANTHROPIC_API_KEY', '')
        return os.environ.get('ANTHROPIC_API_KEY', '')
    
    def analyze(self, project_name: str) -> SitemapResult:
        """
        分析项目生成Sitemap
        
        Args:
            project_name: 项目名称（如Calm_Analysis）
        
        Returns:
            SitemapResult
        """
        print(f"\n{'='*60}")
        print(f"  SITEMAP ANALYZER - {project_name}")
        print(f"{'='*60}")
        
        # 加载分析结果
        project_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'projects', project_name
        )
        
        analysis_file = os.path.join(project_path, 'ai_analysis.json')
        if not os.path.exists(analysis_file):
            raise FileNotFoundError(f"Analysis file not found: {analysis_file}")
        
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        results = analysis_data.get('results', {})
        app_name = project_name.replace('_Analysis', '').replace('_', ' ')
        
        print(f"\n  Total Screenshots: {len(results)}")
        
        # Step 1: 识别Tab结构
        print(f"\n  [Step 1] Identifying Tab structure...")
        tabs = self._identify_tabs(results, project_path)
        print(f"  Found {len(tabs)} tabs: {[t['name'] for t in tabs]}")
        
        # Step 2: 构建页面层级
        print(f"\n  [Step 2] Building page hierarchy...")
        pages = self._build_hierarchy(results, tabs)
        print(f"  Built {len(pages)} page nodes")
        
        # Step 3: 推断导航路径
        print(f"\n  [Step 3] Inferring navigation paths...")
        paths = self._infer_navigation(results, pages)
        print(f"  Found {len(paths)} navigation paths")
        
        # Step 4: 生成Mermaid图
        print(f"\n  [Step 4] Generating Mermaid diagram...")
        mermaid = self._generate_mermaid(app_name, tabs, pages, paths)
        
        result = SitemapResult(
            app_name=app_name,
            tabs=tabs,
            pages={k: asdict(v) for k, v in pages.items()},
            navigation_paths=paths,
            mermaid_diagram=mermaid
        )
        
        # 保存结果
        output_file = os.path.join(project_path, 'sitemap.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)
        
        print(f"\n  Output: {output_file}")
        print(f"{'='*60}")
        
        return result
    
    def _identify_tabs(self, results: Dict, project_path: str) -> List[Dict]:
        """识别底部Tab结构"""
        tabs = []
        
        # 找所有Home类型的页面（通常是Tab入口）
        home_screens = []
        for filename, data in results.items():
            if data.get('screen_type') == 'Home':
                home_screens.append({
                    'filename': filename,
                    'index': data.get('index', 0),
                    'name': data.get('naming', {}).get('cn', '首页')
                })
        
        # 如果有多个Home，可能是不同Tab
        if len(home_screens) >= 1:
            # 用AI分析Tab结构
            tabs = self._ai_analyze_tabs(results, project_path)
        
        # 如果AI分析失败，用默认结构
        if not tabs:
            tabs = self._default_tabs(results)
        
        return tabs
    
    def _ai_analyze_tabs(self, results: Dict, project_path: str) -> List[Dict]:
        """用AI分析Tab结构"""
        if not self.client:
            return []
        
        # 收集所有screen_type
        type_counts = defaultdict(int)
        for data in results.values():
            st = data.get('screen_type', 'Unknown')
            type_counts[st] += 1
        
        # 构建提示词
        prompt = f"""分析这个App的底部Tab结构。

已知的页面类型分布：
{json.dumps(dict(type_counts), ensure_ascii=False, indent=2)}

根据常见的健康/冥想App设计模式，推断可能的Tab结构。

请返回JSON格式：
```json
{{
  "tabs": [
    {{"name": "Home", "icon": "home", "screen_types": ["Home"]}},
    {{"name": "Explore", "icon": "search", "screen_types": ["Content", "Feature"]}},
    {{"name": "Sleep", "icon": "moon", "screen_types": ["Content"]}},
    {{"name": "Profile", "icon": "user", "screen_types": ["Profile", "Settings"]}}
  ]
}}
```

只返回JSON，不要解释。"""

        try:
            response = self.client.messages.create(
                model='claude-sonnet-4-20250514',
                max_tokens=1000,
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            text = response.content[0].text
            # 提取JSON
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            
            data = json.loads(text.strip())
            return data.get('tabs', [])
            
        except Exception as e:
            print(f"  [Warning] AI tab analysis failed: {e}")
            return []
    
    def _default_tabs(self, results: Dict) -> List[Dict]:
        """默认Tab结构"""
        return [
            {"name": "Home", "icon": "home", "screen_types": ["Home"]},
            {"name": "Content", "icon": "play", "screen_types": ["Content", "Feature"]},
            {"name": "Tracking", "icon": "chart", "screen_types": ["Tracking", "Progress"]},
            {"name": "Profile", "icon": "user", "screen_types": ["Profile", "Settings"]}
        ]
    
    def _build_hierarchy(self, results: Dict, tabs: List[Dict]) -> Dict[str, PageNode]:
        """构建页面层级"""
        pages = {}
        
        # 按screen_type分组
        type_groups = defaultdict(list)
        for filename, data in results.items():
            st = data.get('screen_type', 'Unknown')
            type_groups[st].append({
                'filename': filename,
                'data': data
            })
        
        # 创建Tab页面（Level 1）
        for tab in tabs:
            tab_id = f"tab_{tab['name'].lower()}"
            pages[tab_id] = PageNode(
                id=tab_id,
                name=tab['name'],
                screen_type='Tab',
                level=1,
                parent_id=None,
                children=[],
                tab_name=tab['name'],
                is_modal=False,
                screenshots=[]
            )
        
        # 分配页面到Tab下（Level 2）
        for screen_type, items in type_groups.items():
            # 找对应的Tab
            parent_tab = None
            for tab in tabs:
                if screen_type in tab.get('screen_types', []):
                    parent_tab = f"tab_{tab['name'].lower()}"
                    break
            
            if not parent_tab:
                parent_tab = "tab_other"
                if parent_tab not in pages:
                    pages[parent_tab] = PageNode(
                        id=parent_tab,
                        name="Other",
                        screen_type='Tab',
                        level=1,
                        parent_id=None,
                        children=[],
                        tab_name="Other",
                        is_modal=False,
                        screenshots=[]
                    )
            
            # 创建二级页面
            page_id = f"page_{screen_type.lower()}"
            screenshots = [item['filename'] for item in items]
            
            pages[page_id] = PageNode(
                id=page_id,
                name=screen_type,
                screen_type=screen_type,
                level=2,
                parent_id=parent_tab,
                children=[],
                tab_name=pages[parent_tab].name if parent_tab in pages else None,
                is_modal=screen_type in ['Paywall', 'Referral', 'Permission'],
                screenshots=screenshots
            )
            
            # 添加到父节点
            if parent_tab in pages:
                pages[parent_tab].children.append(page_id)
        
        return pages
    
    def _infer_navigation(self, results: Dict, pages: Dict[str, PageNode]) -> List[Dict]:
        """推断导航路径"""
        paths = []
        
        # 基于截图顺序推断流程
        sorted_results = sorted(
            [(f, d) for f, d in results.items()],
            key=lambda x: x[1].get('index', 0)
        )
        
        # 找连续的类型变化
        prev_type = None
        for filename, data in sorted_results:
            curr_type = data.get('screen_type', 'Unknown')
            
            if prev_type and prev_type != curr_type:
                paths.append({
                    'from': f"page_{prev_type.lower()}",
                    'to': f"page_{curr_type.lower()}",
                    'type': 'flow'  # 流程跳转
                })
            
            prev_type = curr_type
        
        # 去重
        seen = set()
        unique_paths = []
        for p in paths:
            key = f"{p['from']}->{p['to']}"
            if key not in seen:
                seen.add(key)
                unique_paths.append(p)
        
        return unique_paths
    
    def _generate_mermaid(self, app_name: str, tabs: List[Dict], 
                          pages: Dict[str, PageNode], paths: List[Dict]) -> str:
        """生成Mermaid图表"""
        lines = [
            "graph TD",
            f"    App[{app_name}]"
        ]
        
        # 添加Tab节点
        for tab in tabs:
            tab_id = f"tab_{tab['name'].lower()}"
            lines.append(f"    App --> {tab_id}[{tab['name']}]")
        
        # 添加二级页面
        for page_id, page in pages.items():
            if page.level == 2 and page.parent_id:
                # 简化名称
                display_name = page.name
                count = len(page.screenshots)
                if count > 0:
                    display_name = f"{page.name} ({count})"
                
                lines.append(f"    {page.parent_id} --> {page_id}[{display_name}]")
        
        # 添加导航路径（用虚线）
        for path in paths[:10]:  # 只显示前10个，避免太乱
            if path['from'] in pages and path['to'] in pages:
                lines.append(f"    {path['from']} -.-> {path['to']}")
        
        return "\n".join(lines)


def analyze_sitemap(project_name: str) -> SitemapResult:
    """便捷函数"""
    analyzer = SitemapAnalyzer()
    return analyzer.analyze(project_name)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        project = sys.argv[1]
    else:
        project = "Calm_Analysis"
    
    result = analyze_sitemap(project)
    
    print("\n" + "="*60)
    print("  MERMAID DIAGRAM")
    print("="*60)
    print(result.mermaid_diagram)


Sitemap分析模块
基于静态截图推断App的页面结构和导航关系
"""

import os
import sys
import json
import base64
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# API
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class PageNode:
    """页面节点"""
    id: str                     # 唯一ID
    name: str                   # 页面名称
    screen_type: str            # 类型（Home/Feature/Content等）
    level: int                  # 层级（1=Tab页, 2=二级页, 3=三级页）
    parent_id: Optional[str]    # 父页面ID
    children: List[str]         # 子页面ID列表
    tab_name: Optional[str]     # 所属Tab名称
    is_modal: bool              # 是否是模态弹窗
    screenshots: List[str]      # 对应的截图文件名


@dataclass  
class SitemapResult:
    """Sitemap分析结果"""
    app_name: str
    tabs: List[Dict]            # Tab结构
    pages: Dict[str, PageNode]  # 所有页面
    navigation_paths: List[Dict] # 导航路径
    mermaid_diagram: str        # Mermaid图表


class SitemapAnalyzer:
    """Sitemap分析器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self.client = None
        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _load_api_key(self) -> str:
        """加载API Key"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config', 'api_keys.json'
        )
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config.get('ANTHROPIC_API_KEY', '')
        return os.environ.get('ANTHROPIC_API_KEY', '')
    
    def analyze(self, project_name: str) -> SitemapResult:
        """
        分析项目生成Sitemap
        
        Args:
            project_name: 项目名称（如Calm_Analysis）
        
        Returns:
            SitemapResult
        """
        print(f"\n{'='*60}")
        print(f"  SITEMAP ANALYZER - {project_name}")
        print(f"{'='*60}")
        
        # 加载分析结果
        project_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'projects', project_name
        )
        
        analysis_file = os.path.join(project_path, 'ai_analysis.json')
        if not os.path.exists(analysis_file):
            raise FileNotFoundError(f"Analysis file not found: {analysis_file}")
        
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        results = analysis_data.get('results', {})
        app_name = project_name.replace('_Analysis', '').replace('_', ' ')
        
        print(f"\n  Total Screenshots: {len(results)}")
        
        # Step 1: 识别Tab结构
        print(f"\n  [Step 1] Identifying Tab structure...")
        tabs = self._identify_tabs(results, project_path)
        print(f"  Found {len(tabs)} tabs: {[t['name'] for t in tabs]}")
        
        # Step 2: 构建页面层级
        print(f"\n  [Step 2] Building page hierarchy...")
        pages = self._build_hierarchy(results, tabs)
        print(f"  Built {len(pages)} page nodes")
        
        # Step 3: 推断导航路径
        print(f"\n  [Step 3] Inferring navigation paths...")
        paths = self._infer_navigation(results, pages)
        print(f"  Found {len(paths)} navigation paths")
        
        # Step 4: 生成Mermaid图
        print(f"\n  [Step 4] Generating Mermaid diagram...")
        mermaid = self._generate_mermaid(app_name, tabs, pages, paths)
        
        result = SitemapResult(
            app_name=app_name,
            tabs=tabs,
            pages={k: asdict(v) for k, v in pages.items()},
            navigation_paths=paths,
            mermaid_diagram=mermaid
        )
        
        # 保存结果
        output_file = os.path.join(project_path, 'sitemap.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)
        
        print(f"\n  Output: {output_file}")
        print(f"{'='*60}")
        
        return result
    
    def _identify_tabs(self, results: Dict, project_path: str) -> List[Dict]:
        """识别底部Tab结构"""
        tabs = []
        
        # 找所有Home类型的页面（通常是Tab入口）
        home_screens = []
        for filename, data in results.items():
            if data.get('screen_type') == 'Home':
                home_screens.append({
                    'filename': filename,
                    'index': data.get('index', 0),
                    'name': data.get('naming', {}).get('cn', '首页')
                })
        
        # 如果有多个Home，可能是不同Tab
        if len(home_screens) >= 1:
            # 用AI分析Tab结构
            tabs = self._ai_analyze_tabs(results, project_path)
        
        # 如果AI分析失败，用默认结构
        if not tabs:
            tabs = self._default_tabs(results)
        
        return tabs
    
    def _ai_analyze_tabs(self, results: Dict, project_path: str) -> List[Dict]:
        """用AI分析Tab结构"""
        if not self.client:
            return []
        
        # 收集所有screen_type
        type_counts = defaultdict(int)
        for data in results.values():
            st = data.get('screen_type', 'Unknown')
            type_counts[st] += 1
        
        # 构建提示词
        prompt = f"""分析这个App的底部Tab结构。

已知的页面类型分布：
{json.dumps(dict(type_counts), ensure_ascii=False, indent=2)}

根据常见的健康/冥想App设计模式，推断可能的Tab结构。

请返回JSON格式：
```json
{{
  "tabs": [
    {{"name": "Home", "icon": "home", "screen_types": ["Home"]}},
    {{"name": "Explore", "icon": "search", "screen_types": ["Content", "Feature"]}},
    {{"name": "Sleep", "icon": "moon", "screen_types": ["Content"]}},
    {{"name": "Profile", "icon": "user", "screen_types": ["Profile", "Settings"]}}
  ]
}}
```

只返回JSON，不要解释。"""

        try:
            response = self.client.messages.create(
                model='claude-sonnet-4-20250514',
                max_tokens=1000,
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            text = response.content[0].text
            # 提取JSON
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            
            data = json.loads(text.strip())
            return data.get('tabs', [])
            
        except Exception as e:
            print(f"  [Warning] AI tab analysis failed: {e}")
            return []
    
    def _default_tabs(self, results: Dict) -> List[Dict]:
        """默认Tab结构"""
        return [
            {"name": "Home", "icon": "home", "screen_types": ["Home"]},
            {"name": "Content", "icon": "play", "screen_types": ["Content", "Feature"]},
            {"name": "Tracking", "icon": "chart", "screen_types": ["Tracking", "Progress"]},
            {"name": "Profile", "icon": "user", "screen_types": ["Profile", "Settings"]}
        ]
    
    def _build_hierarchy(self, results: Dict, tabs: List[Dict]) -> Dict[str, PageNode]:
        """构建页面层级"""
        pages = {}
        
        # 按screen_type分组
        type_groups = defaultdict(list)
        for filename, data in results.items():
            st = data.get('screen_type', 'Unknown')
            type_groups[st].append({
                'filename': filename,
                'data': data
            })
        
        # 创建Tab页面（Level 1）
        for tab in tabs:
            tab_id = f"tab_{tab['name'].lower()}"
            pages[tab_id] = PageNode(
                id=tab_id,
                name=tab['name'],
                screen_type='Tab',
                level=1,
                parent_id=None,
                children=[],
                tab_name=tab['name'],
                is_modal=False,
                screenshots=[]
            )
        
        # 分配页面到Tab下（Level 2）
        for screen_type, items in type_groups.items():
            # 找对应的Tab
            parent_tab = None
            for tab in tabs:
                if screen_type in tab.get('screen_types', []):
                    parent_tab = f"tab_{tab['name'].lower()}"
                    break
            
            if not parent_tab:
                parent_tab = "tab_other"
                if parent_tab not in pages:
                    pages[parent_tab] = PageNode(
                        id=parent_tab,
                        name="Other",
                        screen_type='Tab',
                        level=1,
                        parent_id=None,
                        children=[],
                        tab_name="Other",
                        is_modal=False,
                        screenshots=[]
                    )
            
            # 创建二级页面
            page_id = f"page_{screen_type.lower()}"
            screenshots = [item['filename'] for item in items]
            
            pages[page_id] = PageNode(
                id=page_id,
                name=screen_type,
                screen_type=screen_type,
                level=2,
                parent_id=parent_tab,
                children=[],
                tab_name=pages[parent_tab].name if parent_tab in pages else None,
                is_modal=screen_type in ['Paywall', 'Referral', 'Permission'],
                screenshots=screenshots
            )
            
            # 添加到父节点
            if parent_tab in pages:
                pages[parent_tab].children.append(page_id)
        
        return pages
    
    def _infer_navigation(self, results: Dict, pages: Dict[str, PageNode]) -> List[Dict]:
        """推断导航路径"""
        paths = []
        
        # 基于截图顺序推断流程
        sorted_results = sorted(
            [(f, d) for f, d in results.items()],
            key=lambda x: x[1].get('index', 0)
        )
        
        # 找连续的类型变化
        prev_type = None
        for filename, data in sorted_results:
            curr_type = data.get('screen_type', 'Unknown')
            
            if prev_type and prev_type != curr_type:
                paths.append({
                    'from': f"page_{prev_type.lower()}",
                    'to': f"page_{curr_type.lower()}",
                    'type': 'flow'  # 流程跳转
                })
            
            prev_type = curr_type
        
        # 去重
        seen = set()
        unique_paths = []
        for p in paths:
            key = f"{p['from']}->{p['to']}"
            if key not in seen:
                seen.add(key)
                unique_paths.append(p)
        
        return unique_paths
    
    def _generate_mermaid(self, app_name: str, tabs: List[Dict], 
                          pages: Dict[str, PageNode], paths: List[Dict]) -> str:
        """生成Mermaid图表"""
        lines = [
            "graph TD",
            f"    App[{app_name}]"
        ]
        
        # 添加Tab节点
        for tab in tabs:
            tab_id = f"tab_{tab['name'].lower()}"
            lines.append(f"    App --> {tab_id}[{tab['name']}]")
        
        # 添加二级页面
        for page_id, page in pages.items():
            if page.level == 2 and page.parent_id:
                # 简化名称
                display_name = page.name
                count = len(page.screenshots)
                if count > 0:
                    display_name = f"{page.name} ({count})"
                
                lines.append(f"    {page.parent_id} --> {page_id}[{display_name}]")
        
        # 添加导航路径（用虚线）
        for path in paths[:10]:  # 只显示前10个，避免太乱
            if path['from'] in pages and path['to'] in pages:
                lines.append(f"    {path['from']} -.-> {path['to']}")
        
        return "\n".join(lines)


def analyze_sitemap(project_name: str) -> SitemapResult:
    """便捷函数"""
    analyzer = SitemapAnalyzer()
    return analyzer.analyze(project_name)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        project = sys.argv[1]
    else:
        project = "Calm_Analysis"
    
    result = analyze_sitemap(project)
    
    print("\n" + "="*60)
    print("  MERMAID DIAGRAM")
    print("="*60)
    print(result.mermaid_diagram)


Sitemap分析模块
基于静态截图推断App的页面结构和导航关系
"""

import os
import sys
import json
import base64
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# API
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class PageNode:
    """页面节点"""
    id: str                     # 唯一ID
    name: str                   # 页面名称
    screen_type: str            # 类型（Home/Feature/Content等）
    level: int                  # 层级（1=Tab页, 2=二级页, 3=三级页）
    parent_id: Optional[str]    # 父页面ID
    children: List[str]         # 子页面ID列表
    tab_name: Optional[str]     # 所属Tab名称
    is_modal: bool              # 是否是模态弹窗
    screenshots: List[str]      # 对应的截图文件名


@dataclass  
class SitemapResult:
    """Sitemap分析结果"""
    app_name: str
    tabs: List[Dict]            # Tab结构
    pages: Dict[str, PageNode]  # 所有页面
    navigation_paths: List[Dict] # 导航路径
    mermaid_diagram: str        # Mermaid图表


class SitemapAnalyzer:
    """Sitemap分析器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self.client = None
        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _load_api_key(self) -> str:
        """加载API Key"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config', 'api_keys.json'
        )
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config.get('ANTHROPIC_API_KEY', '')
        return os.environ.get('ANTHROPIC_API_KEY', '')
    
    def analyze(self, project_name: str) -> SitemapResult:
        """
        分析项目生成Sitemap
        
        Args:
            project_name: 项目名称（如Calm_Analysis）
        
        Returns:
            SitemapResult
        """
        print(f"\n{'='*60}")
        print(f"  SITEMAP ANALYZER - {project_name}")
        print(f"{'='*60}")
        
        # 加载分析结果
        project_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'projects', project_name
        )
        
        analysis_file = os.path.join(project_path, 'ai_analysis.json')
        if not os.path.exists(analysis_file):
            raise FileNotFoundError(f"Analysis file not found: {analysis_file}")
        
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        results = analysis_data.get('results', {})
        app_name = project_name.replace('_Analysis', '').replace('_', ' ')
        
        print(f"\n  Total Screenshots: {len(results)}")
        
        # Step 1: 识别Tab结构
        print(f"\n  [Step 1] Identifying Tab structure...")
        tabs = self._identify_tabs(results, project_path)
        print(f"  Found {len(tabs)} tabs: {[t['name'] for t in tabs]}")
        
        # Step 2: 构建页面层级
        print(f"\n  [Step 2] Building page hierarchy...")
        pages = self._build_hierarchy(results, tabs)
        print(f"  Built {len(pages)} page nodes")
        
        # Step 3: 推断导航路径
        print(f"\n  [Step 3] Inferring navigation paths...")
        paths = self._infer_navigation(results, pages)
        print(f"  Found {len(paths)} navigation paths")
        
        # Step 4: 生成Mermaid图
        print(f"\n  [Step 4] Generating Mermaid diagram...")
        mermaid = self._generate_mermaid(app_name, tabs, pages, paths)
        
        result = SitemapResult(
            app_name=app_name,
            tabs=tabs,
            pages={k: asdict(v) for k, v in pages.items()},
            navigation_paths=paths,
            mermaid_diagram=mermaid
        )
        
        # 保存结果
        output_file = os.path.join(project_path, 'sitemap.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)
        
        print(f"\n  Output: {output_file}")
        print(f"{'='*60}")
        
        return result
    
    def _identify_tabs(self, results: Dict, project_path: str) -> List[Dict]:
        """识别底部Tab结构"""
        tabs = []
        
        # 找所有Home类型的页面（通常是Tab入口）
        home_screens = []
        for filename, data in results.items():
            if data.get('screen_type') == 'Home':
                home_screens.append({
                    'filename': filename,
                    'index': data.get('index', 0),
                    'name': data.get('naming', {}).get('cn', '首页')
                })
        
        # 如果有多个Home，可能是不同Tab
        if len(home_screens) >= 1:
            # 用AI分析Tab结构
            tabs = self._ai_analyze_tabs(results, project_path)
        
        # 如果AI分析失败，用默认结构
        if not tabs:
            tabs = self._default_tabs(results)
        
        return tabs
    
    def _ai_analyze_tabs(self, results: Dict, project_path: str) -> List[Dict]:
        """用AI分析Tab结构"""
        if not self.client:
            return []
        
        # 收集所有screen_type
        type_counts = defaultdict(int)
        for data in results.values():
            st = data.get('screen_type', 'Unknown')
            type_counts[st] += 1
        
        # 构建提示词
        prompt = f"""分析这个App的底部Tab结构。

已知的页面类型分布：
{json.dumps(dict(type_counts), ensure_ascii=False, indent=2)}

根据常见的健康/冥想App设计模式，推断可能的Tab结构。

请返回JSON格式：
```json
{{
  "tabs": [
    {{"name": "Home", "icon": "home", "screen_types": ["Home"]}},
    {{"name": "Explore", "icon": "search", "screen_types": ["Content", "Feature"]}},
    {{"name": "Sleep", "icon": "moon", "screen_types": ["Content"]}},
    {{"name": "Profile", "icon": "user", "screen_types": ["Profile", "Settings"]}}
  ]
}}
```

只返回JSON，不要解释。"""

        try:
            response = self.client.messages.create(
                model='claude-sonnet-4-20250514',
                max_tokens=1000,
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            text = response.content[0].text
            # 提取JSON
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            
            data = json.loads(text.strip())
            return data.get('tabs', [])
            
        except Exception as e:
            print(f"  [Warning] AI tab analysis failed: {e}")
            return []
    
    def _default_tabs(self, results: Dict) -> List[Dict]:
        """默认Tab结构"""
        return [
            {"name": "Home", "icon": "home", "screen_types": ["Home"]},
            {"name": "Content", "icon": "play", "screen_types": ["Content", "Feature"]},
            {"name": "Tracking", "icon": "chart", "screen_types": ["Tracking", "Progress"]},
            {"name": "Profile", "icon": "user", "screen_types": ["Profile", "Settings"]}
        ]
    
    def _build_hierarchy(self, results: Dict, tabs: List[Dict]) -> Dict[str, PageNode]:
        """构建页面层级"""
        pages = {}
        
        # 按screen_type分组
        type_groups = defaultdict(list)
        for filename, data in results.items():
            st = data.get('screen_type', 'Unknown')
            type_groups[st].append({
                'filename': filename,
                'data': data
            })
        
        # 创建Tab页面（Level 1）
        for tab in tabs:
            tab_id = f"tab_{tab['name'].lower()}"
            pages[tab_id] = PageNode(
                id=tab_id,
                name=tab['name'],
                screen_type='Tab',
                level=1,
                parent_id=None,
                children=[],
                tab_name=tab['name'],
                is_modal=False,
                screenshots=[]
            )
        
        # 分配页面到Tab下（Level 2）
        for screen_type, items in type_groups.items():
            # 找对应的Tab
            parent_tab = None
            for tab in tabs:
                if screen_type in tab.get('screen_types', []):
                    parent_tab = f"tab_{tab['name'].lower()}"
                    break
            
            if not parent_tab:
                parent_tab = "tab_other"
                if parent_tab not in pages:
                    pages[parent_tab] = PageNode(
                        id=parent_tab,
                        name="Other",
                        screen_type='Tab',
                        level=1,
                        parent_id=None,
                        children=[],
                        tab_name="Other",
                        is_modal=False,
                        screenshots=[]
                    )
            
            # 创建二级页面
            page_id = f"page_{screen_type.lower()}"
            screenshots = [item['filename'] for item in items]
            
            pages[page_id] = PageNode(
                id=page_id,
                name=screen_type,
                screen_type=screen_type,
                level=2,
                parent_id=parent_tab,
                children=[],
                tab_name=pages[parent_tab].name if parent_tab in pages else None,
                is_modal=screen_type in ['Paywall', 'Referral', 'Permission'],
                screenshots=screenshots
            )
            
            # 添加到父节点
            if parent_tab in pages:
                pages[parent_tab].children.append(page_id)
        
        return pages
    
    def _infer_navigation(self, results: Dict, pages: Dict[str, PageNode]) -> List[Dict]:
        """推断导航路径"""
        paths = []
        
        # 基于截图顺序推断流程
        sorted_results = sorted(
            [(f, d) for f, d in results.items()],
            key=lambda x: x[1].get('index', 0)
        )
        
        # 找连续的类型变化
        prev_type = None
        for filename, data in sorted_results:
            curr_type = data.get('screen_type', 'Unknown')
            
            if prev_type and prev_type != curr_type:
                paths.append({
                    'from': f"page_{prev_type.lower()}",
                    'to': f"page_{curr_type.lower()}",
                    'type': 'flow'  # 流程跳转
                })
            
            prev_type = curr_type
        
        # 去重
        seen = set()
        unique_paths = []
        for p in paths:
            key = f"{p['from']}->{p['to']}"
            if key not in seen:
                seen.add(key)
                unique_paths.append(p)
        
        return unique_paths
    
    def _generate_mermaid(self, app_name: str, tabs: List[Dict], 
                          pages: Dict[str, PageNode], paths: List[Dict]) -> str:
        """生成Mermaid图表"""
        lines = [
            "graph TD",
            f"    App[{app_name}]"
        ]
        
        # 添加Tab节点
        for tab in tabs:
            tab_id = f"tab_{tab['name'].lower()}"
            lines.append(f"    App --> {tab_id}[{tab['name']}]")
        
        # 添加二级页面
        for page_id, page in pages.items():
            if page.level == 2 and page.parent_id:
                # 简化名称
                display_name = page.name
                count = len(page.screenshots)
                if count > 0:
                    display_name = f"{page.name} ({count})"
                
                lines.append(f"    {page.parent_id} --> {page_id}[{display_name}]")
        
        # 添加导航路径（用虚线）
        for path in paths[:10]:  # 只显示前10个，避免太乱
            if path['from'] in pages and path['to'] in pages:
                lines.append(f"    {path['from']} -.-> {path['to']}")
        
        return "\n".join(lines)


def analyze_sitemap(project_name: str) -> SitemapResult:
    """便捷函数"""
    analyzer = SitemapAnalyzer()
    return analyzer.analyze(project_name)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        project = sys.argv[1]
    else:
        project = "Calm_Analysis"
    
    result = analyze_sitemap(project)
    
    print("\n" + "="*60)
    print("  MERMAID DIAGRAM")
    print("="*60)
    print(result.mermaid_diagram)


Sitemap分析模块
基于静态截图推断App的页面结构和导航关系
"""

import os
import sys
import json
import base64
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# API
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class PageNode:
    """页面节点"""
    id: str                     # 唯一ID
    name: str                   # 页面名称
    screen_type: str            # 类型（Home/Feature/Content等）
    level: int                  # 层级（1=Tab页, 2=二级页, 3=三级页）
    parent_id: Optional[str]    # 父页面ID
    children: List[str]         # 子页面ID列表
    tab_name: Optional[str]     # 所属Tab名称
    is_modal: bool              # 是否是模态弹窗
    screenshots: List[str]      # 对应的截图文件名


@dataclass  
class SitemapResult:
    """Sitemap分析结果"""
    app_name: str
    tabs: List[Dict]            # Tab结构
    pages: Dict[str, PageNode]  # 所有页面
    navigation_paths: List[Dict] # 导航路径
    mermaid_diagram: str        # Mermaid图表


class SitemapAnalyzer:
    """Sitemap分析器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self.client = None
        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _load_api_key(self) -> str:
        """加载API Key"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config', 'api_keys.json'
        )
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config.get('ANTHROPIC_API_KEY', '')
        return os.environ.get('ANTHROPIC_API_KEY', '')
    
    def analyze(self, project_name: str) -> SitemapResult:
        """
        分析项目生成Sitemap
        
        Args:
            project_name: 项目名称（如Calm_Analysis）
        
        Returns:
            SitemapResult
        """
        print(f"\n{'='*60}")
        print(f"  SITEMAP ANALYZER - {project_name}")
        print(f"{'='*60}")
        
        # 加载分析结果
        project_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'projects', project_name
        )
        
        analysis_file = os.path.join(project_path, 'ai_analysis.json')
        if not os.path.exists(analysis_file):
            raise FileNotFoundError(f"Analysis file not found: {analysis_file}")
        
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        results = analysis_data.get('results', {})
        app_name = project_name.replace('_Analysis', '').replace('_', ' ')
        
        print(f"\n  Total Screenshots: {len(results)}")
        
        # Step 1: 识别Tab结构
        print(f"\n  [Step 1] Identifying Tab structure...")
        tabs = self._identify_tabs(results, project_path)
        print(f"  Found {len(tabs)} tabs: {[t['name'] for t in tabs]}")
        
        # Step 2: 构建页面层级
        print(f"\n  [Step 2] Building page hierarchy...")
        pages = self._build_hierarchy(results, tabs)
        print(f"  Built {len(pages)} page nodes")
        
        # Step 3: 推断导航路径
        print(f"\n  [Step 3] Inferring navigation paths...")
        paths = self._infer_navigation(results, pages)
        print(f"  Found {len(paths)} navigation paths")
        
        # Step 4: 生成Mermaid图
        print(f"\n  [Step 4] Generating Mermaid diagram...")
        mermaid = self._generate_mermaid(app_name, tabs, pages, paths)
        
        result = SitemapResult(
            app_name=app_name,
            tabs=tabs,
            pages={k: asdict(v) for k, v in pages.items()},
            navigation_paths=paths,
            mermaid_diagram=mermaid
        )
        
        # 保存结果
        output_file = os.path.join(project_path, 'sitemap.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)
        
        print(f"\n  Output: {output_file}")
        print(f"{'='*60}")
        
        return result
    
    def _identify_tabs(self, results: Dict, project_path: str) -> List[Dict]:
        """识别底部Tab结构"""
        tabs = []
        
        # 找所有Home类型的页面（通常是Tab入口）
        home_screens = []
        for filename, data in results.items():
            if data.get('screen_type') == 'Home':
                home_screens.append({
                    'filename': filename,
                    'index': data.get('index', 0),
                    'name': data.get('naming', {}).get('cn', '首页')
                })
        
        # 如果有多个Home，可能是不同Tab
        if len(home_screens) >= 1:
            # 用AI分析Tab结构
            tabs = self._ai_analyze_tabs(results, project_path)
        
        # 如果AI分析失败，用默认结构
        if not tabs:
            tabs = self._default_tabs(results)
        
        return tabs
    
    def _ai_analyze_tabs(self, results: Dict, project_path: str) -> List[Dict]:
        """用AI分析Tab结构"""
        if not self.client:
            return []
        
        # 收集所有screen_type
        type_counts = defaultdict(int)
        for data in results.values():
            st = data.get('screen_type', 'Unknown')
            type_counts[st] += 1
        
        # 构建提示词
        prompt = f"""分析这个App的底部Tab结构。

已知的页面类型分布：
{json.dumps(dict(type_counts), ensure_ascii=False, indent=2)}

根据常见的健康/冥想App设计模式，推断可能的Tab结构。

请返回JSON格式：
```json
{{
  "tabs": [
    {{"name": "Home", "icon": "home", "screen_types": ["Home"]}},
    {{"name": "Explore", "icon": "search", "screen_types": ["Content", "Feature"]}},
    {{"name": "Sleep", "icon": "moon", "screen_types": ["Content"]}},
    {{"name": "Profile", "icon": "user", "screen_types": ["Profile", "Settings"]}}
  ]
}}
```

只返回JSON，不要解释。"""

        try:
            response = self.client.messages.create(
                model='claude-sonnet-4-20250514',
                max_tokens=1000,
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            text = response.content[0].text
            # 提取JSON
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            
            data = json.loads(text.strip())
            return data.get('tabs', [])
            
        except Exception as e:
            print(f"  [Warning] AI tab analysis failed: {e}")
            return []
    
    def _default_tabs(self, results: Dict) -> List[Dict]:
        """默认Tab结构"""
        return [
            {"name": "Home", "icon": "home", "screen_types": ["Home"]},
            {"name": "Content", "icon": "play", "screen_types": ["Content", "Feature"]},
            {"name": "Tracking", "icon": "chart", "screen_types": ["Tracking", "Progress"]},
            {"name": "Profile", "icon": "user", "screen_types": ["Profile", "Settings"]}
        ]
    
    def _build_hierarchy(self, results: Dict, tabs: List[Dict]) -> Dict[str, PageNode]:
        """构建页面层级"""
        pages = {}
        
        # 按screen_type分组
        type_groups = defaultdict(list)
        for filename, data in results.items():
            st = data.get('screen_type', 'Unknown')
            type_groups[st].append({
                'filename': filename,
                'data': data
            })
        
        # 创建Tab页面（Level 1）
        for tab in tabs:
            tab_id = f"tab_{tab['name'].lower()}"
            pages[tab_id] = PageNode(
                id=tab_id,
                name=tab['name'],
                screen_type='Tab',
                level=1,
                parent_id=None,
                children=[],
                tab_name=tab['name'],
                is_modal=False,
                screenshots=[]
            )
        
        # 分配页面到Tab下（Level 2）
        for screen_type, items in type_groups.items():
            # 找对应的Tab
            parent_tab = None
            for tab in tabs:
                if screen_type in tab.get('screen_types', []):
                    parent_tab = f"tab_{tab['name'].lower()}"
                    break
            
            if not parent_tab:
                parent_tab = "tab_other"
                if parent_tab not in pages:
                    pages[parent_tab] = PageNode(
                        id=parent_tab,
                        name="Other",
                        screen_type='Tab',
                        level=1,
                        parent_id=None,
                        children=[],
                        tab_name="Other",
                        is_modal=False,
                        screenshots=[]
                    )
            
            # 创建二级页面
            page_id = f"page_{screen_type.lower()}"
            screenshots = [item['filename'] for item in items]
            
            pages[page_id] = PageNode(
                id=page_id,
                name=screen_type,
                screen_type=screen_type,
                level=2,
                parent_id=parent_tab,
                children=[],
                tab_name=pages[parent_tab].name if parent_tab in pages else None,
                is_modal=screen_type in ['Paywall', 'Referral', 'Permission'],
                screenshots=screenshots
            )
            
            # 添加到父节点
            if parent_tab in pages:
                pages[parent_tab].children.append(page_id)
        
        return pages
    
    def _infer_navigation(self, results: Dict, pages: Dict[str, PageNode]) -> List[Dict]:
        """推断导航路径"""
        paths = []
        
        # 基于截图顺序推断流程
        sorted_results = sorted(
            [(f, d) for f, d in results.items()],
            key=lambda x: x[1].get('index', 0)
        )
        
        # 找连续的类型变化
        prev_type = None
        for filename, data in sorted_results:
            curr_type = data.get('screen_type', 'Unknown')
            
            if prev_type and prev_type != curr_type:
                paths.append({
                    'from': f"page_{prev_type.lower()}",
                    'to': f"page_{curr_type.lower()}",
                    'type': 'flow'  # 流程跳转
                })
            
            prev_type = curr_type
        
        # 去重
        seen = set()
        unique_paths = []
        for p in paths:
            key = f"{p['from']}->{p['to']}"
            if key not in seen:
                seen.add(key)
                unique_paths.append(p)
        
        return unique_paths
    
    def _generate_mermaid(self, app_name: str, tabs: List[Dict], 
                          pages: Dict[str, PageNode], paths: List[Dict]) -> str:
        """生成Mermaid图表"""
        lines = [
            "graph TD",
            f"    App[{app_name}]"
        ]
        
        # 添加Tab节点
        for tab in tabs:
            tab_id = f"tab_{tab['name'].lower()}"
            lines.append(f"    App --> {tab_id}[{tab['name']}]")
        
        # 添加二级页面
        for page_id, page in pages.items():
            if page.level == 2 and page.parent_id:
                # 简化名称
                display_name = page.name
                count = len(page.screenshots)
                if count > 0:
                    display_name = f"{page.name} ({count})"
                
                lines.append(f"    {page.parent_id} --> {page_id}[{display_name}]")
        
        # 添加导航路径（用虚线）
        for path in paths[:10]:  # 只显示前10个，避免太乱
            if path['from'] in pages and path['to'] in pages:
                lines.append(f"    {path['from']} -.-> {path['to']}")
        
        return "\n".join(lines)


def analyze_sitemap(project_name: str) -> SitemapResult:
    """便捷函数"""
    analyzer = SitemapAnalyzer()
    return analyzer.analyze(project_name)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        project = sys.argv[1]
    else:
        project = "Calm_Analysis"
    
    result = analyze_sitemap(project)
    
    print("\n" + "="*60)
    print("  MERMAID DIAGRAM")
    print("="*60)
    print(result.mermaid_diagram)

