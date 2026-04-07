"""
ContextRepo 上下文存储库
管理 History / Memory / Scratchpad 三大区域
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from core.afs import AFS


class ContextRepo:
    def __init__(self, afs: AFS):
        # 初始化上下文存储库，注入 AFS 文件系统实例
        self.afs = afs
    
    def append_history(self, session_id: str, entry: Dict) -> bool:
        # 构建历史记录文件路径，按会话ID组织
        path = f"/context/history/{session_id}.log"
        # 格式化历史记录内容，包含时间戳、角色和消息内容
        content = f"[{datetime.now().isoformat()}] {entry.get('role', 'unknown')}: {entry.get('content', '')}"
        # 调用 AFS 写入方法，追加模式，附带会话元数据
        return self.afs.write(path, content, {"session_id": session_id, "type": "history"}, append=True)
    
    '''
    params:
    session_id:会话ID
    limit:返回的历史记录条数，默认10条
    return:返回的记录列表
    '''
    def read_history(self, session_id: str, limit: int = 10) -> List[str]:
        # 构建历史记录文件路径
        path = f"/context/history/{session_id}.log"
        # 从 AFS 读取文件内容
        content = self.afs.read(path)
        # 如果内容存在，按分隔符分割并返回最后 limit 条记录
        if content:
            entries = content.split("\n---\n")
            return entries[-limit:]
        # 内容不存在时返回空列表
        return []
    
    def write_memory(self, agent_id: str, key: str, value: str, metadata: Dict = None) -> bool:
        # 构建记忆文件路径，按 agent_id 和 key 组织存储
        path = f"/context/memory/{agent_id}/{key}.txt"
        # 如果未提供元数据，初始化空字典
        if metadata is None:
            metadata = {}
        # 注入 agent_id 和 memory_key 到元数据中，用于追踪归属
        metadata["agent_id"] = agent_id
        metadata["memory_key"] = key
        # 调用 AFS 写入记忆内容
        return self.afs.write(path, value, metadata)
    
    def read_memory(self, agent_id: str, key: str = "facts") -> Optional[str]:
        # 构建记忆文件路径，默认读取 facts.txt
        path = f"/context/memory/{agent_id}/{key}.txt"
        # 从 AFS 读取指定记忆内容
        return self.afs.read(path)
    
    def search_memory(self, agent_id: str, query: str) -> List[Dict]:
        # 构建记忆目录路径
        path = f"/context/memory/{agent_id}"
        # 在指定目录下搜索匹配 query 的记忆内容
        return self.afs.search(query, path)
    
    def list_memories(self, agent_id: str) -> List[str]:
        # 构建记忆目录路径
        path = f"/context/memory/{agent_id}"
        # 列出该 agent 的所有记忆文件列表
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
