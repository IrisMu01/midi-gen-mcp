.PHONY: install test clean sync

install:
	uv sync --all-extras

sync:
	uv sync

test:
	uv run pytest tests/ -v

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
