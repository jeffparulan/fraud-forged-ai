# Testing

## Core Unit Tests

35 tests with 59% coverage on `app/core/`

### Coverage
- `app/core/__init__.py`: 100%
- `app/core/explanations.py`: 81%
- `app/core/validation.py`: 74%
- `app/core/rag_engine.py`: 55%
- `app/core/router.py`: 41%

### Run Tests

```bash
# All tests
docker exec fraudforge-backend python -m pytest tests/unit/ -v

# With coverage
docker exec fraudforge-backend python -m pytest tests/unit/ --cov=app.core --cov-report=term-missing

# Specific test
docker exec fraudforge-backend python -m pytest tests/unit/test_validation.py -v
```

### Test Files
- `tests/unit/test_validation.py` - Validation logic
- `tests/unit/test_explanations.py` - Explanation generation
- `tests/unit/test_rag_engine.py` - RAG engine
- `tests/unit/test_router.py` - LangGraph router
