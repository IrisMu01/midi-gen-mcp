.PHONY: install test clean

install:
	pip install -e ".[dev]"

update:
	pip install --upgrade --force-reinstall .

test:
	python -m pytest tests/ -v

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
