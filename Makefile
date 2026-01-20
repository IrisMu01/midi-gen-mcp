.PHONY: install test clean sync

install:
	uv sync --all-extras

sync:
	uv sync

test:
	uv run pytest tests/ -v

inspect:
	npx @modelcontextprotocol/inspector \
  	uv \
  	--directory /Users/lingyimu/Projects/midi-gen-mcp/src/midi_gen_mcp \
  	run \
	midi-gen-mcp \

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
