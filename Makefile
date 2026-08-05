.PHONY: test test-backend test-frontend lint clean

test: test-backend

test-backend:
	cd backend && source venv/bin/activate && PYTHONPATH="$$PWD:$$PYTHONPATH" python -m pytest app/tests/ -v

test-frontend:
	cd frontend && npm run lint && npm run build

lint:
	cd backend && source venv/bin/activate && python -m flake8 app/ --max-line-length=120 --exclude=venv,__pycache__ || true

clean:
	rm -rf frontend/.next backend/app/__pycache__ backend/app/**/__pycache__
