.PHONY: install dev lint typecheck test test-cov format clean build publish doctor

install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	playwright install chromium

lint:
	ruff check src/ tests/

typecheck:
	mypy src/agentux/

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=agentux --cov-report=html --cov-report=term-missing

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

clean:
	rm -rf dist/ build/ *.egg-info .mypy_cache .ruff_cache .pytest_cache htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +

build:
	python -m build

publish: build
	twine upload dist/*

doctor:
	agentux doctor
