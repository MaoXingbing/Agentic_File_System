'''
ContextRepo上下文存储库
管理 History、Memory、Scratchpad 三大区域
'''

from ast import Dict
from datetime import datetime
from afs import AFS


class ContextRepo():
    def __init__(self,afs:AFS) -> None:
        self.afs = afs

    #构建历史记录
    '''
    args:session_id 会话ID：会话隔离，不同的用户对话分开存储进行隔离
    entry 历史记录条目
    '''
    #history中的数据由这个方法和afs.write()共同构造
    def append_history(self,session_id:str,entry:Dict)->bool:
        #构建存储的地址
        path=f"context/history/{session_id}.log"
        #构建存储信息
        content=f"[{datetime.now().isoformat()}]{entry.get('role','unkown')}:{entry.get('content','none')}"
        metadata={
            "session_id":session_id,
            "type":"history",
        }
        #写入
        is_write=self.afs.write(self,path,content,metadata)
        #返回是否成功
        return is_write

    #读取最近N条历史记录
    def read_history(self,session_id:str,k:int=10)->List[str]:
        #会构建历史记录路径
        path=f"/context/history/{session_id}.log"
        #读取文件内容
        content=self.afs.read(path)
        #若内容存在 按分隔符分割并返回n条记录
        if content:
            real_conmtent=content.split("\n---\n")
            return real_conmtent[-k:]
        #若内容不存在 则返回空列表
        return []
        


    def write_memory():
        pass
    def read_memory():
        pass
    def search_memory():
        pass
    def list_memory():
        pass
