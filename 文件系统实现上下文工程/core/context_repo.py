"""
ContextRepo 上下文存储库
管理 History / Memory / Scratchpad 三大区域
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from core.afs import AFS


class ContextRepo:
    def __init__(self, afs: AFS):
        self.afs = afs
    
    def append_history(self, session_id: str, entry: Dict) -> bool:
        path = f"/context/history/{session_id}.log"
        content = f"[{datetime.now().isoformat()}] {entry.get('role', 'unknown')}: {entry.get('content', '')}"
        return self.afs.write(path, content, {"session_id": session_id, "type": "history"}, append=True)
    
    def read_history(self, session_id: str, limit: int = 10) -> List[str]:
        path = f"/context/history/{session_id}.log"
        content = self.afs.read(path)
        if content:
            entries = content.split("\n---\n")
            return entries[-limit:]
        return []
    
    def write_memory(self, agent_id: str, key: str, value: str, metadata: Dict = None) -> bool:
        path = f"/context/memory/{agent_id}/{key}.txt"
        if metadata is None:
            metadata = {}
        metadata["agent_id"] = agent_id
        metadata["memory_key"] = key
        return self.afs.write(path, value, metadata)
    
    def read_memory(self, agent_id: str, key: str = "facts") -> Optional[str]:
        path = f"/context/memory/{agent_id}/{key}.txt"
        return self.afs.read(path)
    
    def search_memory(self, agent_id: str, query: str) -> List[Dict]:
        path = f"/context/memory/{agent_id}"
        return self.afs.search(query, path)
    
    def list_memories(self, agent_id: str) -> List[str]:
        path = f"/context/memory/{agent_id}"
        return self.afs.list_dir(path)
    
    def write_scratchpad(self, task_id: str, name: str, content: str, metadata: Dict = None) -> bool:
        path = f"/context/pad/{task_id}/{name}.md"
        if metadata is None:
            metadata = {}
        metadata["task_id"] = task_id
        metadata["scratchpad_type"] = name
        return self.afs.write(path, content, metadata)
    
    def read_scratchpad(self, task_id: str, name: str = "scratch") -> Optional[str]:
        path = f"/context/pad/{task_id}/{name}.md"
        return self.afs.read(path)
    
    def clear_scratchpad(self, task_id: str) -> bool:
        path = f"/context/pad/{task_id}"
        return self.afs.delete(path)
    
    def archive_scratchpad(self, task_id: str, agent_id: str) -> bool:
        scratchpad_content = self.read_scratchpad(task_id)
        if scratchpad_content:
            archive_key = f"archive_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            return self.write_memory(agent_id, archive_key, scratchpad_content, {"archived_from": "scratchpad"})
        return False
    
    def write_human_feedback(self, feedback_type: str, content: str, metadata: Dict = None) -> bool:
        path = f"/context/human/{feedback_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        if metadata is None:
            metadata = {}
        metadata["feedback_type"] = feedback_type
        return self.afs.write(path, content, metadata)
    
    def list_human_feedback(self) -> List[str]:
        return self.afs.list_dir("/context/human")
    
    def get_context_window(self, session_id: str, agent_id: str, task_id: str, max_entries: int = 5) -> Dict:
        history = self.read_history(session_id, limit=max_entries)
        memory = self.read_memory(agent_id)
        scratchpad = self.read_scratchpad(task_id)
        
        return {
            "history": history,
            "memory": memory,
            "scratchpad": scratchpad,
            "metadata": {
                "session_id": session_id,
                "agent_id": agent_id,
                "task_id": task_id,
                "retrieved_at": datetime.now().isoformat()
            }
        }


if __name__ == "__main__":
    afs = AFS()
    repo = ContextRepo(afs)
    
    repo.append_history("session_001", {"role": "user", "content": "你好"})
    repo.append_history("session_001", {"role": "agent", "content": "你好！有什么可以帮助你的？"})
    
    repo.write_memory("agent_001", "facts", "用户是Python开发者，喜欢使用LangChain")
    repo.write_memory("agent_001", "preferences", "用户偏好简洁的回答")
    
    repo.write_scratchpad("task_001", "plan", "1. 分析用户需求\n2. 检索相关记忆\n3. 生成回答")
    repo.write_scratchpad("task_001", "scratch", "正在思考...")
    
    context = repo.get_context_window("session_001", "agent_001", "task_001")
    print(f"上下文窗口: {context}")
