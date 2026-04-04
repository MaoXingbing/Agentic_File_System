"""
文件系统三层架构 - 上下文工程 MVP
主执行入口
"""
import sys
import os

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from core.afs import AFS
from core.context_repo import ContextRepo
from core.context_pipeline import ContextPipeline


def demo_basic_usage():
    print("=" * 60)
    print("演示1: 基础使用流程")
    print("=" * 60)
    
    afs = AFS()
    repo = ContextRepo(afs)
    pipeline = ContextPipeline(afs, repo)
    
    session_id = f"session_{datetime.now().strftime('%Y%m%d')}"
    agent_id = "agent_001"
    
    repo.write_memory(agent_id, "facts", "用户是Python开发者，喜欢使用LangChain框架")
    repo.write_memory(agent_id, "preferences", "用户偏好简洁、技术性强的回答")
    
    queries = [
        "你好，请介绍一下你自己",
        "我最近在学什么技术？",
        "你能帮我解决什么问题？"
    ]
    
    for i, query in enumerate(queries):
        task_id = f"task_{i+1:03d}"
        print(f"\n--- 第 {i+1} 轮对话 ---")
        print(f"用户: {query}")
        
        result = pipeline.execute(
            query=query,
            task_id=task_id,
            session_id=session_id,
            agent_id=agent_id
        )
        
        print(f"助手: {result['llm_output']}")
        print(f"上下文来源: {len(result['manifest']['sources'])} 个")
        print(f"评估结果: {'通过' if result['evaluation']['is_consistent'] else '需人工审核'}")


def demo_context_flow():
    print("\n" + "=" * 60)
    print("演示2: 上下文流转过程")
    print("=" * 60)
    
    afs = AFS()
    repo = ContextRepo(afs)
    pipeline = ContextPipeline(afs, repo)
    
    agent_id = "agent_002"
    task_id = "task_flow_001"
    session_id = "session_flow"
    
    repo.write_memory(agent_id, "facts", "用户正在开发一个AI聊天机器人项目")
    repo.write_scratchpad(task_id, "plan", """
1. 分析用户需求
2. 检索相关记忆
3. 构建上下文
4. 生成回答
""")
    
    print("\n步骤1: 构造上下文")
    context, manifest = pipeline.constructor.construct(task_id, "我的项目进展如何？", session_id, agent_id)
    print(f"上下文长度: {len(context)} 字符")
    print(f"来源数量: {len(manifest['sources'])}")
    
    print("\n步骤2: 更新注入")
    pipeline.updater.record_version(task_id, context, manifest)
    print("版本已记录")
    
    print("\n步骤3: 评估输出")
    evaluation = pipeline.evaluator.evaluate("根据记录，您正在开发AI聊天机器人项目", context, agent_id)
    print(f"一致性: {evaluation['is_consistent']}")
    print(f"置信度: {evaluation['confidence']:.2%}")


def demo_file_system_operations():
    print("\n" + "=" * 60)
    print("演示3: AFS 文件系统操作")
    print("=" * 60)
    
    afs = AFS()
    
    print("\n1. 写入文件")
    afs.write("/context/memory/test_agent/profile.txt", "测试用户画像", {"type": "profile"})
    print("已写入: /context/memory/test_agent/profile.txt")
    
    print("\n2. 读取文件")
    content = afs.read("/context/memory/test_agent/profile.txt")
    print(f"内容: {content[:100]}...")
    
    print("\n3. 搜索文件")
    results = afs.search("测试", "/context/memory")
    print(f"搜索结果: {len(results)} 条")
    
    print("\n4. 列出目录")
    files = afs.list_dir("/context/memory")
    print(f"目录内容: {files}")


def demo_human_in_loop():
    print("\n" + "=" * 60)
    print("演示4: 人在环路审核")
    print("=" * 60)
    
    afs = AFS()
    repo = ContextRepo(afs)
    pipeline = ContextPipeline(afs, repo)
    
    pipeline.set_consistency_threshold(0.9)
    
    result = pipeline.execute(
        query="请预测明天的股票价格",
        task_id="task_review_001",
        session_id="session_review",
        agent_id="agent_review"
    )
    
    print(f"查询: {result['query']}")
    print(f"输出目的地: {result['destination']}")
    
    if result['destination'] == 'human_review':
        print("需要人工审核!")
        print(f"问题: {result['evaluation']['issues']}")
    
    feedback_list = repo.list_human_feedback()
    print(f"\n待审核项目: {len(feedback_list)} 条")


if __name__ == "__main__":
    demo_basic_usage()
    demo_context_flow()
    demo_file_system_operations()
    demo_human_in_loop()
    
    print("\n" + "=" * 60)
    print("所有演示完成!")
    print("=" * 60)
