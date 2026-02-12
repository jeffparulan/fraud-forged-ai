# Core Unit Tests

## Running Tests

```bash
# Rebuild with test dependencies
docker-compose down
docker-compose up --build -d

# Run all core tests
docker exec fraudforge-backend python -m pytest tests/unit/ -v

# Run with coverage
docker exec fraudforge-backend python -m pytest tests/unit/ --cov=app.core --cov-report=term-missing

# Run specific test file
docker exec fraudforge-backend python -m pytest tests/unit/test_validation.py -v
```

## Test Coverage

- `test_validation.py` - Validation logic (get_risk_level, validate_llm_result)
- `test_explanations.py` - Explanation generation for all sectors
- `test_rag_engine.py` - RAG engine initialization and queries
- `test_router.py` - LangGraph router and workflow

## Test Structure

```
tests/
├── unit/
│   ├── test_validation.py
│   ├── test_explanations.py
│   ├── test_rag_engine.py
│   └── test_router.py
├── integration/
└── e2e/
```
