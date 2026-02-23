"""
SkillKit + LangChain 示例
"""
from skillkit import SkillManager
from skillkit.integrations.langchain import create_langchain_tools

# 1. 初始化并发现 skills
manager = SkillManager(
    skill_dir="./skills",  # 指定 skills 目录
)
manager.discover()

# 2. 列出所有可用的 skills
print("=== Available Skills ===")
for skill in manager.list_skills():
    print(f"- {skill.name}: {skill.description}")

# 3. 转换为 LangChain Tools
tools = create_langchain_tools(manager)

print(f"\n=== Created {len(tools)} LangChain Tools ===")
for tool in tools:
    print(f"- {tool.name}: {tool.description}")

# 4. 创建 LangChain Agent（示例）
# from langchain.agents import create_agent
# from langchain_openai import ChatOpenAI
# 
# llm = ChatOpenAI(model="gpt-4")
# agent = create_agent(llm, tools, system_prompt="你是一个有帮助的助手...")
# 
# result = agent.invoke({"messages": [HumanMessage(content="用 code-reviewer 审查这段代码...")]})
