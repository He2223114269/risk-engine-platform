.PHONY: help install lint test run clean

help:
	@echo "风控引擎决策分析平台 — 常用命令"
	@echo ""
	@echo "make install    安装项目依赖"
	@echo "make lint       运行代码规范检查"
	@echo "make test       运行单元测试"
	@echo "make test-cov   运行测试并生成覆盖率报告"
	@echo "make run-dev    启动开发服务器"
	@echo "make migrate    执行数据库迁移"
	@echo "make clean      清理缓存文件"
	@echo "make docker     构建 Docker 镜像"
	@echo "make commit     每日自动提交（23:00 定时任务）"

install:
	pip install -e ".[dev,test]"

lint:
	black --check risk_engine/ backend/
	isort --check-only risk_engine/ backend/
	ruff check risk_engine/ backend/
	mypy risk_engine/ backend/

lint-fix:
	black risk_engine/ backend/
	isort risk_engine/ backend/
	ruff check --fix risk_engine/ backend/

test:
	pytest tests/unit

test-cov:
	pytest tests/unit --cov-report=html

run-dev:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	alembic upgrade head

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov

docker:
	docker compose -f docker/docker-compose.yml build

commit:
	@echo "=== 每日自动提交 ==="
	git add -A
	git diff --cached --quiet || git commit -m "chore: 每日自动更新 $(shell date '+%Y-%m-%d')" -m "自动提交内容包括当日代码变更和文档更新"
	git push origin master
