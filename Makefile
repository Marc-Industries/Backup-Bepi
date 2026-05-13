.PHONY: dev test test-unit test-integration lint migrate seed streamlit

dev:
	uvicorn bepi.app:create_app --factory --reload

test:
	pytest tests/

test-unit:
	pytest tests/unit/

test-integration:
	pytest tests/integration/

lint:
	ruff check src/ tests/

migrate:
	alembic upgrade head

seed:
	python -m bepi.scripts.seed_ecss && python -m bepi.scripts.seed_demo

streamlit:
	streamlit run src/bepi/dashboard.py
