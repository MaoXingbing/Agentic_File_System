"""
AFS (Agentic File System) 智能体文件系统
统一命名空间，所有上下文都是文件
"""
import os
import json
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path


class AFS:
    def __init__(self, root_path: str = None):
        """
        初始化AFS实例，设置根目录路径并确保目录结构存在
        
        Args:
            root_path: AFS根目录路径，默认为项目根目录下的afs文件夹
        """
        # 如果未指定根路径，则使用项目根目录下的afs文件夹作为默认路径
        if root_path is None:
            # 获取当前文件的父目录的父目录作为项目根目录
            project_root = os.path.dirname(os.path.dirname(__file__))
            # 拼接afs文件夹路径
            root_path = os.path.join(project_root, "afs")
        # 将路径转换为Path对象
        self.root = Path(root_path)
        # 确保目录结构存在
        self._ensure_structure()
    
    def _ensure_structure(self):
        """
        确保AFS的基础目录结构存在，创建必要的系统目录
        
        创建的目录包括：
        - /context/history: 历史记录存储
        - /context/memory: 记忆存储
        - /context/pad: 临时/草稿存储
        - /context/human: 人类相关上下文
        - /system: 系统文件
        - /system/logs: 操作日志
        """
        # 定义AFS基础目录结构列表
        directories = [
            "/context/history",    # 历史记录存储目录
            "/context/memory",     # 记忆存储目录
            "/context/pad",        # 临时/草稿存储目录
            "/context/human",      # 人类相关上下文目录
            "/system",             # 系统文件目录
            "/system/logs"         # 操作日志目录
        ]
        # 遍历目录列表，逐个创建目录
        for dir_path in directories:
            # 移除路径开头的/，构建相对于root的完整路径
            full_path = self.root / dir_path.lstrip("/")
            # 创建目录，parents=True表示自动创建父目录，exist_ok=True表示目录已存在时不报错
            full_path.mkdir(parents=True, exist_ok=True)
    
    def _resolve_path(self, path: str) -> Path:
        """
        将虚拟路径解析为实际文件系统路径
        
        Args:
            path: 以/开头的虚拟路径，如"/context/memory/agent_001/facts.txt"
        
        Returns:
            Path: 解析后的实际文件路径对象
        
        处理逻辑:
        - 移除路径开头的/，使其成为相对于root的相对路径
        - 与self.root拼接得到完整路径
        """
        if path.startswith("/"):
            path = path[1:]
        return self.root / path
    
    def read(self, path: str) -> Optional[str]:
        #读取文件内容的方法，返回文件内容的字符串或None
        # 将虚拟路径解析为实际文件系统路径
        full_path = self._resolve_path(path)
        # 检查文件是否存在
        if full_path.exists():
            # 读取文件内容并返回，使用UTF-8编码
            return full_path.read_text(encoding="utf-8")
        # 文件不存在时返回None
        return None
    
    # 读取JSON文件并解析为字典的方法
    def read_json(self, path: str) -> Optional[Dict]:
        # 调用read方法获取文件内容
        content = self.read(path)
        # 如果内容存在则解析JSON
        if content:
            # 将JSON字符串解析为Python字典并返回
            return json.loads(content)
        # 内容不存在时返回None
        return None
    
    # 写入文件内容的方法，支持元数据和追加模式
    def write(self, path: str, content: str, metadata: Dict = None, append: bool = False) -> bool:
        # 将虚拟路径解析为实际文件系统路径
        full_path = self._resolve_path(path)
        # 确保父目录存在，如果不存在则自动创建
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果元数据为None则初始化为空字典
        if metadata is None:
            metadata = {}
        
        # 添加时间戳到元数据
        metadata["timestamp"] = datetime.now().isoformat()
        # 添加文件路径到元数据
        metadata["path"] = path
        
        # 构建包含元数据和内容的条目字典
        entry = {
            "metadata": metadata,
            "content": content
        }
        
        # 根据append参数确定文件打开模式，追加模式为"a"，覆盖模式为"w"
        mode = "a" if append else "w"
        # 打开文件进行写入操作
        with open(full_path, mode, encoding="utf-8") as f:
            # 如果是追加模式且文件已存在且不为空，则添加分隔符
            if append and full_path.exists() and full_path.stat().st_size > 0:
                f.write("\n---\n")
            # 将条目字典序列化为JSON字符串并写入文件
            f.write(json.dumps(entry, ensure_ascii=False, indent=2))
        
        # 记录写入操作到日志
        self._log_operation("write", path, metadata)
        # 返回True表示写入成功
        return True
    
    # 将字典数据以JSON格式写入文件的方法
    def write_json(self, path: str, data: Dict, metadata: Dict = None) -> bool:
        # 将字典序列化为JSON字符串，然后调用write方法写入文件
        return self.write(path, json.dumps(data, ensure_ascii=False, indent=2), metadata)
    
    #这是 AFS 的"记忆检索"功能，让 Agent 能够根据关键词查找相关的历史记忆或文档。
    def search(self, query: str, root: str = "/") -> List[Dict]:
        #args:
        #    query:要搜索的关键词
        #    root:搜索的根路径，默认"/"
        #return:
        #    包含匹配文件路径、相关度和片段的字典列表
        #    return results
        #
        # 初始化搜索结果列表
        results = []
        # 将虚拟根路径解析为实际文件系统路径
        search_path = self._resolve_path(root)
        
        # 检查搜索路径是否存在，不存在则直接返回空结果
        if not search_path.exists():
            return results
        
        # 递归遍历搜索路径下的所有文件
        for file_path in search_path.rglob("*"):
            # 检查当前路径是否为文件
            if file_path.is_file(): 
                # 读取文件内容
                content = file_path.read_text(encoding="utf-8")
                # 检查查询字符串是否在文件内容中（不区分大小写）
                if query.lower() in content.lower():
                    # 计算相对路径，添加前导斜杠
                    relative_path = "/" + str(file_path.relative_to(self.root))
                    # 将匹配结果添加到结果列表
                    results.append({
                        "path": relative_path,
                        "relevance": content.lower().count(query.lower()),
                        "snippet": content[:200]
                    })
        
        # 按相关度降序排序结果
        results.sort(key=lambda x: x["relevance"], reverse=True)
        # 返回搜索结果列表
        return results
    
    #列出目录下的文件和文件夹
    def list_dir(self, path: str = "/") -> List[str]:
        # 将虚拟路径解析为实际文件系统路径
        full_path = self._resolve_path(path)
        
        # 检查路径是否存在，不存在则返回空列表
        if not full_path.exists():
            return []
        
        # 检查路径是否为目录，不是目录则返回空列表
        if not full_path.is_dir():
            return []
        
        # 初始化结果列表
        result = []
        # 遍历目录中的所有项目
        for item in full_path.iterdir():
            # 计算相对于根目录的相对路径
            relative = item.relative_to(self.root)
            # 将相对路径转换为字符串并添加到结果列表
            result.append(str(relative))
        
        # 返回目录内容列表
        return result
    
    def delete(self, path: str) -> bool:
        # 将虚拟路径解析为实际文件系统路径
        full_path = self._resolve_path(path)
        # 检查路径是否存在
        if full_path.exists():
            # 判断是否为目录
            if full_path.is_dir():
                # 导入shutil模块用于删除目录
                import shutil
                # 递归删除目录及其内容
                shutil.rmtree(full_path)
            else:
                # 删除单个文件
                full_path.unlink()
            # 记录删除操作到日志
            self._log_operation("delete", path, {})
            # 返回删除成功
            return True
        # 路径不存在时返回删除失败
        return False
    
    def mount(self, source: str, path: str) -> bool:
        mount_path = self._resolve_path(path)
        mount_path.parent.mkdir(parents=True, exist_ok=True)
        
        if os.path.exists(source):
            if os.path.isdir(source):
                import shutil
                if mount_path.exists():
                    shutil.rmtree(mount_path)
                shutil.copytree(source, mount_path)
            else:
                shutil.copy2(source, mount_path)
            
            self._log_operation("mount", path, {"source": source})
            return True
        return False
    
    def _log_operation(self, operation: str, path: str, metadata: Dict):
        log_path = self.root / "system" / "logs" / "operations.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "path": path,
            "metadata": metadata
        }
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def get_manifest(self, paths: List[str]) -> Dict:
        manifest = {
            "created_at": datetime.now().isoformat(),
            "files": [],
            "total_tokens": 0
        }
        
        for path in paths:
            content = self.read(path)
            if content:
                token_count = len(content) // 4
                manifest["files"].append({
                    "path": path,
                    "token_estimate": token_count,
                    "size": len(content)
                })
                manifest["total_tokens"] += token_count
        
        return manifest


if __name__ == "__main__":
    afs = AFS()
    
    afs.write("/context/memory/agent_001/facts.txt", "用户喜欢Python编程", {"agent_id": "agent_001"})
    afs.write("/context/history/session_001.log", "User: 你好\nAgent: 你好！", {"session_id": "session_001"})
    
    results = afs.search("Python", "/context")
    print(f"搜索结果: {results}")
    
    print(f"目录列表: {afs.list_dir('/context')}")
