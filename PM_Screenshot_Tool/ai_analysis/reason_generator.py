"""
双模型AI理由生成器 - Dual Model Reason Generator

功能：
- 同时调用 Claude Opus 4.5 和 GPT-4o 分析决策矩阵
- 双模型独立生成推荐理由，便于对比质量
- 生成风险提示和缓解建议
- 输出对比视图，标注两个模型的差异点
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# 尝试导入 API 客户端
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class DualModelReasonGenerator:
    """双模型理由生成器 - Claude Opus 4.5 + GPT-5.2 Thinking (最新版)"""
    
    # 使用最新的模型 (2025年12月)
    CLAUDE_MODEL = "claude-opus-4-5-20251101"   # Claude Opus 4.5 - Anthropic 最新旗舰
    OPENAI_MODEL = "gpt-5.2"                     # GPT-5.2 Thinking - OpenAI 最新版本
    
    # 决策分析的系统提示
    SYSTEM_PROMPT = """你是一位资深产品经理和UX设计专家，正在帮助团队基于竞品分析做出设计决策。

你的任务是：
1. 分析给定的设计决策数据（多个竞品在同一流程步骤的设计选择）
2. 给出推荐的设计方案
3. 解释推荐理由（3-5条）
4. 指出潜在风险和缓解措施
5. 推荐参考的竞品截图

回复格式必须为 JSON：
{
    "recommended_choice": "推荐的设计选择",
    "reasons": [
        "理由1：xxx",
        "理由2：xxx",
        "理由3：xxx"
    ],
    "risks": [
        {
            "risk": "潜在风险描述",
            "mitigation": "缓解措施"
        }
    ],
    "confidence": 0.85,
    "reference_competitors": ["竞品1", "竞品2"],
    "additional_insights": "补充洞察（可选）"
}

分析原则：
- 基于数据统计，主流选择通常更安全
- 考虑用户体验和转化率
- 权衡实现成本和效果
- 如果分歧大，建议A/B测试
"""

    def __init__(self, config_path: str = None):
        """
        初始化双模型理由生成器
        
        Args:
            config_path: API 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.claude_client = None
        self.openai_client = None
        
        # 初始化 Claude
        if ANTHROPIC_AVAILABLE and self.config.get("ANTHROPIC_API_KEY"):
            self.claude_client = anthropic.Anthropic(
                api_key=self.config["ANTHROPIC_API_KEY"]
            )
            print(f"[OK] Claude initialized: {self.CLAUDE_MODEL}")
        else:
            print("[WARN] Claude not available")
        
        # 初始化 OpenAI
        if OPENAI_AVAILABLE and self.config.get("OPENAI_API_KEY"):
            try:
                self.openai_client = OpenAI(api_key=self.config["OPENAI_API_KEY"])
            except TypeError:
                import httpx
                self.openai_client = OpenAI(
                    api_key=self.config["OPENAI_API_KEY"],
                    http_client=httpx.Client()
                )
            print(f"[OK] OpenAI initialized: {self.OPENAI_MODEL}")
        else:
            print("[WARN] OpenAI not available")
    
    def _load_config(self, config_path: str = None) -> Dict:
        """加载 API 配置"""
        config = {}
        
        # 尝试从环境变量加载
        config["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")
        config["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
        
        # 尝试从配置文件加载
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config", "api_keys.json"
            )
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    if not config["ANTHROPIC_API_KEY"]:
                        config["ANTHROPIC_API_KEY"] = file_config.get("ANTHROPIC_API_KEY")
                    if not config["OPENAI_API_KEY"]:
                        config["OPENAI_API_KEY"] = file_config.get("OPENAI_API_KEY")
            except Exception as e:
                print(f"[WARN] Failed to load config: {e}")
        
        return config
    
    def _build_analysis_prompt(self, decision_entry: Dict) -> str:
        """
        构建分析提示
        
        Args:
            decision_entry: 单个决策矩阵条目
        """
        screen_type = decision_entry.get("screen_type", "")
        step = decision_entry.get("step", "")
        sub_type = decision_entry.get("sub_type", "")
        competitors_count = decision_entry.get("competitors_count", 0)
        design_choices = decision_entry.get("design_choices", {})
        statistics = decision_entry.get("statistics", {})
        
        prompt = f"""请分析以下设计决策数据，并给出推荐方案：

## 页面信息
- 页面类型：{screen_type}
- 步骤：{step}
- 子类型：{sub_type}
- 参与竞品数：{competitors_count}

## 设计选择分布
"""
        
        for dimension, choices in design_choices.items():
            prompt += f"\n### {dimension}\n"
            for choice, competitors in choices.items():
                prompt += f"- {choice}: {', '.join(competitors)}\n"
        
        prompt += "\n## 统计数据\n"
        for dimension, stats in statistics.items():
            majority = stats.get("majority", "")
            percentage = stats.get("percentage", 0)
            is_consensus = stats.get("is_consensus", False)
            distribution = stats.get("distribution", {})
            
            consensus_label = " [共识]" if is_consensus else " [分歧]"
            prompt += f"\n### {dimension}{consensus_label}\n"
            prompt += f"- 主流选择：{majority} ({percentage}%)\n"
            prompt += f"- 分布：{json.dumps(distribution, ensure_ascii=False)}\n"
        
        prompt += "\n请基于以上数据给出设计推荐。"
        return prompt
    
    def _call_claude(self, prompt: str) -> Dict:
        """调用 Claude Opus 4.5"""
        if not self.claude_client:
            return {"error": "Claude not available"}
        
        try:
            start_time = time.time()
            
            response = self.claude_client.messages.create(
                model=self.CLAUDE_MODEL,
                max_tokens=2000,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            
            elapsed = time.time() - start_time
            
            # 解析响应
            content = response.content[0].text
            
            # 提取 JSON
            result = self._parse_json_response(content)
            result["_meta"] = {
                "model": self.CLAUDE_MODEL,
                "response_time": round(elapsed, 2),
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
            
            return result
            
        except Exception as e:
            return {"error": str(e), "_meta": {"model": self.CLAUDE_MODEL}}
    
    def _call_openai(self, prompt: str) -> Dict:
        """调用 GPT-4o"""
        if not self.openai_client:
            return {"error": "OpenAI not available"}
        
        try:
            start_time = time.time()
            
            # GPT-5.2 不需要显式设置 token 限制
            response = self.openai_client.chat.completions.create(
                model=self.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            
            elapsed = time.time() - start_time
            
            # 解析响应
            content = response.choices[0].message.content
            
            # 提取 JSON
            result = self._parse_json_response(content)
            result["_meta"] = {
                "model": self.OPENAI_MODEL,
                "response_time": round(elapsed, 2),
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            }
            
            return result
            
        except Exception as e:
            return {"error": str(e), "_meta": {"model": self.OPENAI_MODEL}}
    
    def _parse_json_response(self, content: str) -> Dict:
        """从响应中提取 JSON"""
        # 尝试直接解析
        try:
            return json.loads(content)
        except:
            pass
        
        # 尝试提取 JSON 块
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # 尝试提取 { } 之间的内容
        brace_match = re.search(r'\{[\s\S]*\}', content)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except:
                pass
        
        # 无法解析，返回原始内容
        return {"raw_response": content}
    
    def _compare_results(self, claude_result: Dict, openai_result: Dict) -> Dict:
        """
        对比两个模型的结果
        
        Returns:
            对比分析结果
        """
        comparison = {
            "agreement": "unknown",
            "common_ground": [],
            "differences": [],
            "combined_confidence": 0.0
        }
        
        # 检查错误
        if "error" in claude_result or "error" in openai_result:
            comparison["agreement"] = "incomplete"
            if "error" in claude_result:
                comparison["differences"].append(f"Claude error: {claude_result['error']}")
            if "error" in openai_result:
                comparison["differences"].append(f"OpenAI error: {openai_result['error']}")
            return comparison
        
        # 对比推荐选择（处理字符串或字典格式）
        def normalize_choice(choice):
            if isinstance(choice, dict):
                return json.dumps(choice, ensure_ascii=False, sort_keys=True).lower()
            elif isinstance(choice, str):
                return choice.lower()
            return str(choice).lower()
        
        claude_choice = normalize_choice(claude_result.get("recommended_choice", ""))
        openai_choice = normalize_choice(openai_result.get("recommended_choice", ""))
        
        if claude_choice and openai_choice:
            # 简单的相似度检查
            if claude_choice == openai_choice:
                comparison["agreement"] = "full"
                comparison["common_ground"].append(f"两个模型都推荐：{claude_result.get('recommended_choice')}")
            elif any(word in openai_choice for word in claude_choice.split()) or \
                 any(word in claude_choice for word in openai_choice.split()):
                comparison["agreement"] = "partial"
                comparison["common_ground"].append("推荐方向相似")
                comparison["differences"].append(
                    f"Claude: {claude_result.get('recommended_choice')} vs GPT: {openai_result.get('recommended_choice')}"
                )
            else:
                comparison["agreement"] = "divergent"
                comparison["differences"].append(
                    f"推荐不同 - Claude: {claude_result.get('recommended_choice')}, GPT: {openai_result.get('recommended_choice')}"
                )
        
        # 对比理由
        claude_reasons = set(claude_result.get("reasons", []))
        openai_reasons = set(openai_result.get("reasons", []))
        
        # 找共同主题（简单的关键词匹配）
        common_themes = []
        theme_keywords = {
            "用户体验": ["用户", "体验", "user", "experience", "ux"],
            "转化率": ["转化", "conversion", "funnel"],
            "简洁性": ["简洁", "简单", "simple", "minimal", "减少"],
            "信任": ["信任", "trust", "安全", "security"],
            "个性化": ["个性化", "personalization", "定制"],
        }
        
        all_reasons_text = " ".join(list(claude_reasons) + list(openai_reasons)).lower()
        for theme, keywords in theme_keywords.items():
            if any(kw in all_reasons_text for kw in keywords):
                common_themes.append(theme)
        
        if common_themes:
            comparison["common_ground"].append(f"共同关注点：{', '.join(common_themes)}")
        
        # 计算综合置信度
        claude_conf = claude_result.get("confidence", 0.5)
        openai_conf = openai_result.get("confidence", 0.5)
        
        if comparison["agreement"] == "full":
            # 完全一致时，综合置信度较高
            comparison["combined_confidence"] = round((claude_conf + openai_conf) / 2 * 1.1, 2)
            comparison["combined_confidence"] = min(comparison["combined_confidence"], 1.0)
        elif comparison["agreement"] == "partial":
            comparison["combined_confidence"] = round((claude_conf + openai_conf) / 2, 2)
        else:
            # 分歧时降低置信度
            comparison["combined_confidence"] = round((claude_conf + openai_conf) / 2 * 0.7, 2)
        
        return comparison
    
    def generate_reason(self, decision_entry: Dict, parallel: bool = True) -> Dict:
        """
        为单个决策条目生成理由
        
        Args:
            decision_entry: 决策矩阵条目
            parallel: 是否并行调用两个模型
            
        Returns:
            包含两个模型结果和对比的字典
        """
        prompt = self._build_analysis_prompt(decision_entry)
        
        if parallel and self.claude_client and self.openai_client:
            # 并行调用
            with ThreadPoolExecutor(max_workers=2) as executor:
                claude_future = executor.submit(self._call_claude, prompt)
                openai_future = executor.submit(self._call_openai, prompt)
                
                claude_result = claude_future.result()
                openai_result = openai_future.result()
        else:
            # 串行调用
            claude_result = self._call_claude(prompt) if self.claude_client else {"error": "not available"}
            openai_result = self._call_openai(prompt) if self.openai_client else {"error": "not available"}
        
        # 对比结果
        comparison = self._compare_results(claude_result, openai_result)
        
        # 生成最终建议
        final_suggestion = self._generate_final_suggestion(
            decision_entry, claude_result, openai_result, comparison
        )
        
        return {
            "entry_key": f"{decision_entry.get('screen_type')}_{decision_entry.get('step')}",
            "claude": claude_result,
            "openai": openai_result,
            "model_comparison": comparison,
            "final_suggestion": final_suggestion
        }
    
    def _generate_final_suggestion(
        self, 
        decision_entry: Dict,
        claude_result: Dict, 
        openai_result: Dict, 
        comparison: Dict
    ) -> str:
        """生成最终建议"""
        agreement = comparison.get("agreement", "unknown")
        confidence = comparison.get("combined_confidence", 0.5)
        
        if agreement == "full":
            choice = claude_result.get("recommended_choice", "")
            return f"强烈推荐：{choice}（双模型一致，置信度 {confidence}）"
        elif agreement == "partial":
            claude_choice = claude_result.get("recommended_choice", "")
            return f"建议采用：{claude_choice}，可参考两个模型的理由进行优化（置信度 {confidence}）"
        elif agreement == "divergent":
            stats = decision_entry.get("statistics", {})
            # 找到最有共识的维度
            best_dim = None
            best_pct = 0
            for dim, dim_stats in stats.items():
                if dim_stats.get("percentage", 0) > best_pct:
                    best_pct = dim_stats.get("percentage", 0)
                    best_dim = dim_stats.get("majority", "")
            
            if best_pct >= 60:
                return f"建议参考市场主流选择：{best_dim}（{best_pct}%竞品采用），或进行A/B测试验证"
            else:
                return "建议进行A/B测试，两种方案各有优势"
        else:
            return "数据不足，建议补充更多竞品分析"
    
    def generate_all_reasons(
        self, 
        decision_matrix: Dict,
        max_concurrent: int = 3
    ) -> Dict:
        """
        为所有决策条目生成理由
        
        Args:
            decision_matrix: 完整的决策矩阵
            max_concurrent: 最大并发数
            
        Returns:
            所有决策的理由结果
        """
        results = {}
        entries = list(decision_matrix.items())
        total = len(entries)
        
        print(f"\n[INFO] Generating reasons for {total} decision entries...")
        
        for i, (key, entry) in enumerate(entries, 1):
            print(f"  [{i}/{total}] Processing {key}...")
            
            try:
                result = self.generate_reason(entry)
                results[key] = result
                
                # 显示简要结果
                agreement = result.get("model_comparison", {}).get("agreement", "unknown")
                print(f"    Agreement: {agreement}")
                
            except Exception as e:
                print(f"    [ERROR] {str(e)}")
                results[key] = {"error": str(e)}
            
            # 避免 API 限流
            if i < total:
                time.sleep(1)
        
        print(f"\n[OK] Generated reasons for {len(results)} entries")
        return results
    
    def export_reasons(self, results: Dict, output_path: str = None) -> str:
        """导出理由结果"""
        if output_path is None:
            projects_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "projects"
            )
            output_path = os.path.join(projects_dir, "decision_reasons.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] Reasons exported to: {output_path}")
        return output_path


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Dual Model Reason Generator")
    parser.add_argument("--matrix", "-m", type=str, help="Path to decision matrix JSON")
    parser.add_argument("--output", "-o", type=str, help="Output file path")
    parser.add_argument("--single", "-s", type=str, help="Generate for single entry key")
    parser.add_argument("--test", "-t", action="store_true", help="Test mode with first entry")
    
    args = parser.parse_args()
    
    # 默认矩阵路径
    if not args.matrix:
        projects_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "projects"
        )
        args.matrix = os.path.join(projects_dir, "decision_matrix.json")
    
    # 加载决策矩阵
    if not os.path.exists(args.matrix):
        print(f"[ERROR] Decision matrix not found: {args.matrix}")
        print("[INFO] Run decision_matrix.py first to generate the matrix")
        return
    
    with open(args.matrix, 'r', encoding='utf-8') as f:
        matrix_data = json.load(f)
    
    matrix = matrix_data.get("matrix", matrix_data)
    
    # 初始化生成器
    generator = DualModelReasonGenerator()
    
    if args.test:
        # 测试模式：只处理第一个条目
        first_key = list(matrix.keys())[0]
        first_entry = matrix[first_key]
        
        print(f"\n[TEST] Processing: {first_key}")
        result = generator.generate_reason(first_entry)
        
        print("\n" + "="*60)
        print("RESULT")
        print("="*60)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif args.single:
        # 单条目模式
        if args.single not in matrix:
            print(f"[ERROR] Entry not found: {args.single}")
            return
        
        result = generator.generate_reason(matrix[args.single])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    else:
        # 完整模式
        results = generator.generate_all_reasons(matrix)
        generator.export_reasons(results, args.output)


if __name__ == "__main__":
    main()

















