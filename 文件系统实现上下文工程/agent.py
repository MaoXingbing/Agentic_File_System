"""
集成 LLM 的 Agent 实现
将文件系统上下文工程与 zhisaotong 的模型工厂集成
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from typing import Dict, Any, Optional
from core.afs import AFS
from core.context_repo import ContextRepo
from core.context_pipeline import ContextPipeline

try:
    from zhisaotong.model.factory import chat_model
    HAS_LLM = True
except ImportError:
    HAS_LLM = False
    print("警告: 未找到 zhisaotong 模块，将使用模拟模式")


class ContextAwareAgent:
    def __init__(self, agent_id: str = "default_agent"):
        self.agent_id = agent_id
        self.afs = AFS()
        self.repo = ContextRepo(self.afs)
        self.pipeline = ContextPipeline(self.afs, self.repo)
        
        if HAS_LLM:
            self.pipeline.set_llm_client(chat_model.generater())
        
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._init_agent_memory()
    
    def _init_agent_memory(self):
        facts = self.repo.read_memory(self.agent_id, "facts")
        if not facts:
            self.repo.write_memory(self.agent_id, "facts", "新用户，暂无画像信息")
    
    def chat(self, query: str) -> Dict[str, Any]:
        import uuid
        task_id = str(uuid.uuid4())[:8]
        
        result = self.pipeline.execute(
            query=query,
            task_id=task_id,
            session_id=self.session_id,
            agent_id=self.agent_id
        )
        
        return {
            "response": result["llm_output"],
            "context_used": len(result["manifest"]["sources"]),
            "is_consistent": result["evaluation"]["is_consistent"],
            "destination": result["destination"],
            "task_id": task_id
        }
    
    def update_memory(self, key: str, value: str):
        self.repo.write_memory(self.agent_id, key, value)
    
    def get_memory(self, key: str = "facts") -> Optional[str]:
        return self.repo.read_memory(self.agent_id, key)
    
    def get_history(self, limit: int = 10) -> list:
        return self.repo.read_history(self.session_id, limit)
    
    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt


def interactive_chat():
    print("=" * 60)
    print("文件系统上下文工程 - 交互式聊天")
    print("=" * 60)
    print("输入 'quit' 退出, 'history' 查看历史, 'memory' 查看记忆")
    print()
    
    agent = ContextAwareAgent("interactive_agent")
    
    while True:
        try:
            user_input = input("用户: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("再见!")
                break
            
            if user_input.lower() == 'history':
                history = agent.get_history()
                print("\n历史对话:")
                for h in history:
                    print(f"  {h[:100]}...")
                print()
                continue
            
            if user_input.lower() == 'memory':
                memory = agent.get_memory()
                print(f"\n当前记忆: {memory}\n")
                continue
            
            result = agent.chat(user_input)
            
            print(f"助手: {result['response']}")
            print(f"[上下文来源: {result['context_used']}, 一致性: {result['is_consistent']}]")
            print()
            
        except KeyboardInterrupt:
            print("\n再见!")
            break


if __name__ == "__main__":
    interactive_chat()
