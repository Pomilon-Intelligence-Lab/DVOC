.PHONY: test test-core test-os test-py test-web test-all

test-all:
	python -m pytest dvoc-core/tests/ --no-header -q --rootdir=dvoc-core
	python -m pytest dvoc-os/tests/ --no-header -q
	python -m pytest dvoc-py/tests/ --no-header -q
	python -m pytest dvoc-web/tests/ --no-header -q
	@echo "=== ALL PACKAGES PASSED ==="

test-core:
	python -m pytest dvoc-core/tests/ --no-header -v --rootdir=dvoc-core

test-web:
	python -m pytest dvoc-web/tests/ --no-header -v

install:
	pip install -e dvoc-core/
	pip install -e dvoc-os/
	pip install -e dvoc-py/
	pip install -e dvoc-web/

model-test:
	python examples/test_web_model.py

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf dvoc-core/build dvoc-core/dist dvoc-core/*.egg-info
	rm -rf dvoc-os/build dvoc-os/dist dvoc-os/*.egg-info
	rm -rf dvoc-py/build dvoc-py/dist dvoc-py/*.egg-info
	rm -rf dvoc-web/build dvoc-web/dist dvoc-web/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
