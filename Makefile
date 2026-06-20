.PHONY: dev test test-unit test-integration lint streamlit

# Backend FastAPI (in dev / CI)
dev:
	uvicorn bepi.app:create_app --factory --reload

# Test
test:
	pytest tests/

test-unit:
	pytest tests/unit/

test-integration:
	pytest tests/integration/

# Lint
lint:
	ruff check src/ tests/

# Streamlit (runtime principale — `streamlit_app.py` nella root)
streamlit:
	streamlit run streamlit_app.py

# Migration e seed sono gestiti da Supabase CLI:
#   supabase db push
#   supabase functions deploy send-invitation
# Vedi docs/SETUP_EMAILS.md per la Edge Function.
