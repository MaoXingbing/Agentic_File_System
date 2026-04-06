'''
最底层的数据存储机制，所有的文件都经过这里
'''

import os
import json
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path
import os
import sys
import shutil
sys.stdout.reconfigure(encoding='utf-8')


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
        
    #从建构中采取精确查找的方式进行检索  path是检索的目录 query是检索的字符串
    def search(self,path:str,query:str)->List[Dict]:
        #初始化
        res=[]
        #将虚拟路径解析为实际文件系统路径
        fullpath=self._resolve_path(path)
        if fullpath is None or not fullpath.exists():
            return res
        
        #递归遍历所有目录
        for tpath in fullpath.rglob("*"):
            #若是文件夹则递归
            #若是文件
            if tpath.is_file():
                content = tpath.read_text(encoding="utf-8")
                #检查字符串是否在文件内容中
                #如果包含
                if query in content:
                    #计算query在文件中出现的次数
                    count=content.lower().count(query.lower())
                    #则添加到结果列表
                    res.append({
                        "path": "/" + str(tpath.relative_to(self.root)), # 文件路径
                        "relevance":count,  # 相关性评分（出现次数）
                        #TODO:需要思考一个问题 为什么是前200字符
                        "snippet":content[:200]  # 内容片段（前200字符）
                    })

        #按照出现的次数进行排序
        res.sort(key=lambda x:x["relevance"],reverse=True)
        #返回结果
        return res

    #列出目录下的文件和文件夹
    def list_dir(self,path:str):
        #将虚拟路径解析为实际路径
        full_path=self._resolve_path(path)
        #检查路径是否存在
        if full_path is None or not full_path.exists():
            return []
        #检查路径是否为目录
        if not full_path.is_dir():
            return []
        #初始化结果列表
        result=[]
        #遍历目录下的所有项目
        for item in full_path.iterdir():
            #计算相对于根目录的相对路径
            relative_path=item.relative_to(self.root)
            #将路径转为字符串添加到结果列表
            result.append(str(relative_path))
        #返回结果
        return result

    #删除文件或目录
    def delete(self,path:str)->bool:
        #将虚拟路径解析为实际路径
        full_path=self._resolve_path(path)
        #检查路径是否存在
        if full_path.exists():
        #路径若存在 判断是不是目录
            if full_path.is_dir():
        #是目录 递归删除
                
                shutil.rmtree(full_path)
        #是文件 删除文件
            else:
                full_path.unlink()
        #记录操作到日志
            self._log_operation("delete",full_path,{})
        #返回成功
            return True
        return False
    
    #将外部文件挂载到内部系统
    def mount(self,source:str,path:str)->bool:
        #将虚拟路径解析为实际路径:实际存储的路径
        mount_path=self._resolve_path(path)
        source=Path(source)
        #检查路径是否存在
        if source.exists():
            #判断是否为目录 若是目录 递归挂载
            if source.is_dir():
                shutil.copytree(source,mount_path)
            #若是文件 直接挂载
            elif source.is_file():
                shutil.copy(source,mount_path)
            #记录操作到日志
            self._log_operation("mount", path, {"source": source, "mount_path": mount_path})
            #返回成功
            return True
        #返回失败
        return False

    def _log_operation(self,operation:str,path:str,metadata:Dict):
        log_path=self.root/"system"/"logs"/"operations.log"
        #确保父目录存在
        log_path.parent.mkdir(parents=True, exist_ok=True)

        #构建日志数据结构
        log_entry={
            "timestamp":datetime.now().isoformat(),
            "operation":operation,
            "path":path,
            "metadata":metadata
        }

        #写入日志文件
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    test_dir = os.path.join(os.path.dirname(__file__), "..", "test")
    afs = AFS(test_dir)
    results = afs.search("/", "你好")
    print(results)
        
        