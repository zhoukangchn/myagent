# Multi-Agent Migration Plan (rag-test)

## Goals
Transform the existing single-agent reflective RAG loop into a modular multi-agent system (Searcher, Writer, Reviewer) using LangGraph.

## Strategy
- Use **LangGraph** for orchestration.
- Implement **Unit Tests** for each new node/agent.
- Follow **PEP8** and project coding standards.
- Run tests before any git commit.

## Phase 1: Infrastructure & Analysis (Current)
- [x] Define Multi-Agent state schema in `src/app/agents/state.py`.
- [x] Research existing tests to ensure compatibility.
- [x] Create this migration plan.

## Phase 2: Node Refactoring (Specialized Agents)
- [ ] Create `src/app/agents/specialized_nodes.py`.
- [ ] Implement `searcher_node` (Tavily focus).
- [ ] Implement `writer_node` (Drafting focus).
- [ ] Implement `reviewer_node` (Reflection focus).

## Phase 3: Graph Re-construction
- [ ] Update `src/app/agents/graph.py` to use the new multi-agent flow.
- [ ] Implement a `router` for dynamic handoffs.

## Phase 4: Verification & Deployment
- [ ] Write integration tests for the full multi-agent graph.
- [ ] Verify all tests pass.
- [ ] Commit changes using `git-essentials`.

---
*Created by Ah Long (🦞) for Kang.*
