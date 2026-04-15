.PHONY: setup create-schema seed-rag seed-bq demo demo-dry demo-continuous demo-continuous-fast demo-incident reset-anomaly test lint clean

setup:
	pip install -e ".[dev]"

create-schema:
	python -m scripts.create_schema

seed-rag:
	python -m scripts.seed_rag

seed-bq:
	python -m scripts.seed_bigquery

demo: seed-rag
	python -m scripts.run_demo

demo-dry: seed-rag
	PIPELINE_MODE=dry python -m scripts.run_demo

demo-continuous: seed-rag
	python -m scripts.run_continuous --interval 300

demo-continuous-fast: seed-rag
	python -m scripts.run_continuous --interval 60

demo-incident: seed-rag
	python -m scripts.run_continuous --interval 60 --incident

reset-anomaly:
	rm -f .anomaly_state.json

test:
	pytest -v --tb=short

lint:
	ruff check .
	ruff format --check .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf .pytest_cache .ruff_cache *.egg-info
