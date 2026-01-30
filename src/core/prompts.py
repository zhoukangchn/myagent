"""Prompt 模板定义"""

# 检查节点 (Check Node)
CHECK_PROMPT_REFLECTION = """之前的回答被评估为不够好，反思意见如下：
{reflection}

原问题: {last_message}

判断是否需要重新查询外部知识库来改进回答。
回答 YES 或 NO:"""

CHECK_PROMPT_DEFAULT = """判断以下问题是否需要查询外部知识库来回答。
如果是事实性问题、需要特定领域知识、或用户明确要求查询，回答 "YES"。
如果是闲聊、简单问候、或你能直接回答的通用问题，回答 "NO"。

问题: {last_message}

只回答 YES 或 NO:"""

# 检索节点 (Retrieve Node)
REFINE_PROMPT = """原问题: {query}

之前的回答不够好，反思意见: {reflection}

请生成一个更好的搜索查询来获取缺失的信息。只输出查询词，不要解释:"""

# 生成节点 (Generate Node)
GENERATE_SYSTEM_PROMPT_BASE = "你是一个有帮助的 AI 助手。请提供准确、完整、有深度的回答。"

GENERATE_SYSTEM_PROMPT_KNOWLEDGE = """

以下是从知识库中检索到的相关信息：

{knowledge_context}

请基于这些信息回答用户问题。如果信息不足，请诚实说明。"""

GENERATE_SYSTEM_PROMPT_REFLECTION = """

之前的回答有以下问题，请在这次回答中改进：
{reflection}"""

# 反思节点 (Reflect Node)
REFLECT_PROMPT = """请评估以下问答的质量。

用户问题: {question}

AI 回答: {answer}

可用知识: {knowledge_context}

请从以下几个方面评估：
1. 准确性：回答是否准确？有没有事实错误？
2. 完整性：回答是否完整？有没有遗漏重要信息？
3. 相关性：回答是否切题？有没有跑题？
4. 深度：回答是否有足够的深度和见解？

如果回答质量足够好，请回复：SATISFIED

如果回答需要改进，请回复：
NEEDS_IMPROVEMENT
[具体说明需要改进的地方，以及如何改进]"""
