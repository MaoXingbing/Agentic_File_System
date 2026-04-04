'''
最底层的数据存储机制，所有的文件都经过这里
'''

from ast import Dict
from datetime import datetime
import os
from pathlib import Path
import json
from typing import Optional


class AFS:
    def __init__(self,root_path:str=None) :
        #初始化afs目录
        #args：目录路径
        if root_path is None:
            #若指定目录为空 则自动构建
            project_path=os.path.dirname(os.path.dirname(__file__))
            #拼接路径
            root_path=os.path.join(project_path,"afs")
        #将路径转换为path对象
        self.root=Path(root_path)
        #构建目录结构
        self._ensure_structure()

    def _ensure_structure(self):
        #构建目录结构
        dir=[
            "context/history",
            "context/memory",
            "context/pad",
            "context/human",
            "system",
            "system/logs"
        ]
        for d in dir:
            #构建目录结构路径
            full_path=self.root/d
            #创建目录
            full_path.mkdir(parents=True,exist_ok=True)

    def _resolve_path(self,path:str) -> Path:
        #将虚拟路径转换为相对路径
        if path.startswith("/"):
            path=path[1:]
        return self.root/path

    #读取文件内容方法，返回文件内容的字符串或None
    def read(self,path:str)->Optional[str]:
        #将虚拟路径解析为实际文件系统路径
        full_path=self._resolve_path(path)
        if full_path.exists():
            #读取文件内容并返回
            return full_path.read_text(encoding="utf-8")
        #文件不存在时返回None
        return None

    #读取json文件并解析为字典的方法
    def read_json(self,path:str)->Optional[Dict]:
        content=self.read(path)
        #如果内容存在则解析JSON
        if content:
            #存在JSON字符串解析为字典并返回
            return json.loads(content)
        #内容为空返回none
        return None


    #写入文件内容的方法 支持元数据和追加模式
    def write(self,path:str,content:str,
            metadata:Dict=None,append:bool=False)->bool:
        '''
        args:
            path:文件路径(写入的文件路径)
            content:要写入的内容
            metadata:文件元数据
            append:是否追加写入
        return:
            是否写入成功
        '''
        
            # ：如果元数据位None则初始化字典
        if metadata is None:
            metadata={}

        try:
            
            #将虚拟路径解析为实际文件系统路径
            full_path=self._resolve_path(path)
            #确保父目录存在,不存在则创建
            full_path.parent.mkdir(parents=True,exist_ok=True)


            # ：添加时间戳到元数据
            metadata["timestamp"]=datetime.now().isoformat()
            # ：添加文件路劲到元数据
            metadata["path"]=path
            # ：构建元数据和content的字典
            data={
                "metadata":metadata,
                "content":content
            }
            # ：根据追加模式判断是否追加写入
            if append:
                mode="a"
            else:
                mode="w"
            #打开文件
            with open(full_path,mode,encoding="utf-8") as f:
                #如果是追加模式且文件不为空 则添加分割符
                if append and full_path.exists() and full_path.stat().st_size>0:
                    f.write("\n---\n")
                #不是追加模式或者添加完分割符后 将字典序列化为JSON然后写入
                file=json.dumps(data,ensure_ascii=False,indent=2)
                f.write(file)

            #记录操作到日志
            #TODO:编写日志记录方法
            self._log_operation("write",path,metadata)
            # 返回True 表示写入成功    
            return True 
        except Exception as e:
            #将错误写入日志
            self._log_operation("write",path,{"error":str(e)})
            # 返回False 表示写入失败    
            return False
            
        #将字典数据写入json文件的方法
    
    def write_json(self,path:str,
            content:Dict,
            metadata:Dict=None)->bool:
        '''
        args:
            path:文件路径(写入的文件路径)
            content:要写入的字典数据
            metadata:文件元数据
        return:
            是否写入成功
        '''
        return self.write(path,json.dumps(content,ensure_ascii=False,indent=2),metadata)        
        


    def search(self,path:str,query:str)->list[Dict]:
        pass
    #git修改~
        











    def list_dir(self,path:str):
        pass
    def delete(self,path:str):
        pass
    
        
        