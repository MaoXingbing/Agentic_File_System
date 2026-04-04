"""
ContextPipeline 上下文流水线
Constructor → Updater → Evaluator 三组件
"""

import jieba
from datetime import datetime
from typing import Dict, List, Tuple, Any
from core.afs import AFS
from core.context_repo import ContextRepo


class ContextConstructor:
    def __init__(self, afs: AFS, repo: ContextRepo):
        self.afs = afs
        self.repo = repo
        self.max_tokens = 8192
    
    def construct(self, task_id: str, query: str, session_id: str = None, agent_id: str = None) -> Tuple[str, Dict]:
        components = []
        manifest = {
            "task_id": task_id,
            "query": query,
            "created_at": datetime.now().isoformat(),
            "sources": [],
            "total_tokens": 0
        }
        
        if session_id:
            history = self.repo.read_history(session_id, limit=3)
            if history:
                history_text = "\n".join(history)
                components.append(f"[历史对话]\n{history_text}")
                manifest["sources"].append({"type": "history", "path": f"/context/history/{session_id}.log"})
        
        if agent_id:
            memory_results = self.repo.search_memory(agent_id, query)
            if memory_results:
                memory_text = "\n".join([r["snippet"] for r in memory_results[:3]])
                components.append(f"[相关记忆]\n{memory_text}")
                manifest["sources"].extend([{"type": "memory", "path": r["path"]} for r in memory_results[:3]])
            
            facts = self.repo.read_memory(agent_id, "facts")
            if facts:
                components.append(f"[用户画像]\n{facts}")
                manifest["sources"].append({"type": "memory", "path": f"/context/memory/{agent_id}/facts.txt"})
        
        scratchpad = self.repo.read_scratchpad(task_id)
        if scratchpad:
            components.append(f"[推理草稿]\n{scratchpad}")
            manifest["sources"].append({"type": "scratchpad", "path": f"/context/pad/{task_id}"})
        
        context = self._combine_and_compress(components)
        manifest["total_tokens"] = len(context) // 4
        
        return context, manifest
    
    def _combine_and_compress(self, components: List[str]) -> str:
        combined = "\n\n---\n\n".join(components)
        
        estimated_tokens = len(combined) // 4
        if estimated_tokens > self.max_tokens:
            ratio = self.max_tokens / estimated_tokens
            max_length = int(len(combined) * ratio * 4)
            combined = combined[:max_length] + "\n...[已截断]"
        
        return combined
    
    def set_token_limit(self, max_tokens: int):
        self.max_tokens = max_tokens


class ContextUpdater:
    def __init__(self, afs: AFS, repo: ContextRepo, llm_client: Any = None):
        self.afs = afs
        self.repo = repo
        self.llm_client = llm_client
    
    def set_llm_client(self, client: Any):
        self.llm_client = client
    
    def update(self, context: str, query: str, system_prompt: str = None) -> str:
        if self.llm_client is None:
            raise ValueError("LLM客户端未设置，请先调用 set_llm_client() 或在初始化时传入")
        
        if system_prompt is None:
            system_prompt = "你是一个智能助手，请根据上下文回答用户问题。"
        
        full_prompt = f"""
{system_prompt}

===上下文信息===
{context}

===用户问题===
{query}

请基于上下文信息回答用户问题：
"""
        
        response = self.llm_client.invoke(full_prompt)
        return response
    
    def inject_to_scratchpad(self, task_id: str, content: str) -> bool:
        return self.repo.write_scratchpad(task_id, "injected_context", content)
    
    def record_version(self, task_id: str, context: str, manifest: Dict) -> bool:
        version_data = {
            "context": context,
            "manifest": manifest,
            "timestamp": datetime.now().isoformat()
        }
        return self.afs.write_json(f"/context/pad/{task_id}/version.json", version_data)



# 上下文评估器
class ContextEvaluator:
    """
    上下文评估器 - 评估LLM输出与源上下文的一致性
    """
    def __init__(self, afs: AFS, repo: ContextRepo):
        self.afs = afs
        self.repo = repo
        self.consistency_threshold = 0.7  # 一致性阈值，低于此值视为不一致
    
    def evaluate(self, llm_output: str, source_context: str, agent_id: str = None) -> Dict:
        """
        评估LLM输出与源上下文的一致性
        
        Args:
            llm_output: LLM生成的输出文本
            source_context: 原始上下文信息
            agent_id: 智能体ID（可选）
        
        Returns:
            包含一致性判断、置信度和问题列表的字典
        """
        result = {
            "is_consistent": True,
            "confidence": 0.8,
            "issues": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # 幻觉检测指标：当输出中出现这些短语但上下文未出现时，可能存在幻觉
        hallucination_indicators = [
            "我不知道",
            "没有相关信息",
            "无法确定",
            "根据我的知识"
        ]
        
        # 检查是否存在可能的幻觉
        for indicator in hallucination_indicators:
            if indicator in llm_output:
                if indicator not in source_context:
                    result["issues"].append(f"可能的幻觉: {indicator}")
                    result["is_consistent"] = False


        # 基于关键词重叠计算置信度
        source_keywords = set(jieba.lcut(source_context.lower()))
        output_keywords = set(jieba.lcut(llm_output.lower()))
        
        if source_keywords:
            # 计算关键词重叠率
            overlap = len(source_keywords & output_keywords) / len(source_keywords)
            result["confidence"] = overlap
            
            # 如果重叠率低于阈值，标记为不一致
            if overlap < self.consistency_threshold:
                result["is_consistent"] = False
                result["issues"].append(f"关键词重叠率低: {overlap:.2%}")
        
        return result
    
    def process_evaluation_result(self, llm_output: str, evaluation: Dict, agent_id: str, task_id: str = None) -> str:
        """
        根据评估结果处理LLM输出
        
        Args:
            llm_output: LLM生成的输出文本
            evaluation: 评估结果字典
            agent_id: 智能体ID
            task_id: 任务ID（可选）
        
        Returns:
            处理目的地标识："memory"或"human_review"
        """
        if evaluation["is_consistent"]:
            # 一致性通过，写入智能体记忆
            self.repo.write_memory(agent_id, f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}", llm_output, {
                "confidence": evaluation["confidence"],
                "source": "llm_output"
            })
            return "memory"
        else:
            # 一致性未通过，提交人工审核
            self.repo.write_human_feedback("review", llm_output, {
                "agent_id": agent_id,
                "task_id": task_id,
                "issues": evaluation["issues"],
                "confidence": evaluation["confidence"]
            })
            return "human_review"
    
    def set_consistency_threshold(self, threshold: float):
        """
        设置一致性阈值
        
        Args:
            threshold: 新的阈值（0-1之间）
        """
        self.consistency_threshold = threshold


class ContextPipeline:
    def __init__(self, afs: AFS = None, repo: ContextRepo = None):
        if afs is None:
            afs = AFS()
        if repo is None:
            repo = ContextRepo(afs)
        
        self.afs = afs
        self.repo = repo
        self.constructor = ContextConstructor(afs, repo)
        self.updater = ContextUpdater(afs, repo)
        self.evaluator = ContextEvaluator(afs, repo)
    
    def set_llm_client(self, client: Any):
        self.updater.set_llm_client(client)
    
    def set_token_limit(self, max_tokens: int):
        self.constructor.set_token_limit(max_tokens)
    
    def set_consistency_threshold(self, threshold: float):
        self.evaluator.set_consistency_threshold(threshold)
    
    def execute(self, query: str, task_id: str, session_id: str = None, agent_id: str = None, system_prompt: str = None) -> Dict:
        context, manifest = self.constructor.construct(task_id, query, session_id, agent_id)
        
        self.updater.record_version(task_id, context, manifest)
        
        llm_output = self.updater.update(context, query, system_prompt)
        
        evaluation = self.evaluator.evaluate(llm_output, context, agent_id)
        
        destination = self.evaluator.process_evaluation_result(llm_output, evaluation, agent_id, task_id)
        
        if session_id:
            self.repo.append_history(session_id, {"role": "user", "content": query})
            self.repo.append_history(session_id, {"role": "agent", "content": llm_output})
        
        return {
            "query": query,
            "context": context,
            "manifest": manifest,
            "llm_output": llm_output,
            "evaluation": evaluation,
            "destination": destination
        }
    
    def run_interactive(self, query: str, agent_id: str = "default_agent", session_id: str = None) -> str:
        import uuid
        task_id = str(uuid.uuid4())[:8]
        
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d')}"
        
        result = self.execute(query, task_id, session_id, agent_id)
        return result["llm_output"]


if __name__ == "__main__":
    pipeline = ContextPipeline()
    
    pipeline.set_token_limit(4096)
    pipeline.set_consistency_threshold(0.6)
    
    result = pipeline.execute(
        query="用户喜欢什么编程语言？",
        task_id="task_001",
        session_id="session_001",
        agent_id="agent_001"
    )
    
    print(f"查询: {result['query']}")
    print(f"上下文: {result['context'][:200]}...")
    print(f"LLM输出: {result['llm_output']}")
    print(f"评估结果: {result['evaluation']}")
    print(f"输出目的地: {result['destination']}")
