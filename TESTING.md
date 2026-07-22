# Testing

## Unit Tests

43 tests covering `app/core/` (validation, explanations, RAG engine, LangGraph
router) and `app/api/security.py` (API-key auth, rate limiting).

Tests run automatically in CI on every push and pull request
(`.github/workflows/ci.yml`).

### Run Tests

```bash
# Inside Docker (after ./run-local.sh)
docker exec fraudforge-backend python -m pytest tests/unit/ -v

# Or locally with a venv
cd backend
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/unit/ --cov=app.core --cov-report=term-missing

# Specific test file
.venv/bin/python -m pytest tests/unit/test_validation.py -v
```

### Test Files
- `tests/unit/test_validation.py` - LLM vs rule-based validation logic
- `tests/unit/test_explanations.py` - Explanation generation
- `tests/unit/test_rag_engine.py` - RAG engine
- `tests/unit/test_router.py` - LangGraph router
- `tests/unit/test_api_security.py` - API-key auth + rate limiter
