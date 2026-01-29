.PHONY: help install dev format lint typecheck test test-cov serve clean all

# 默认目标
.DEFAULT_GOAL := help

# Python 版本
PYTHON := uv run python
PYTEST := uv run pytest
RUFF := uv run ruff

# 颜色
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

help: ## 显示帮助信息
	@echo "$(BLUE)RAG Agent 项目命令$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2}'

install: ## 安装依赖
	uv sync

dev: ## 启动开发服务器
	$(PYTHON) -m src.api.app

format: ## 格式化代码
	$(RUFF) format .

lint: ## 检查代码规范
	$(RUFF) check . --fix

typecheck: ## 类型检查
	$(PYTHON) -m mypy src --ignore-missing-imports

test: ## 运行测试
	$(PYTEST) tests/ -v

test-cov: ## 运行测试并生成覆盖率报告
	$(PYTEST) tests/ -v --cov=src --cov-report=html --cov-report=term

serve: ## 启动生产服务器
	$(PYTHON) -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000

clean: ## 清理缓存文件
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

all: format lint test ## 运行所有检查（格式化 + lint + 测试）
	@echo "$(GREEN)✓ 所有检查通过$(RESET)"
