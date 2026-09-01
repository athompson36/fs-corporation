.PHONY: demo test check status serve
PYTHON ?= python3
demo:
	$(PYTHON) -m company demo
test:
	$(PYTHON) -m unittest discover -s tests -v
check: test
	$(PYTHON) scripts/check_bundle.py
status:
	$(PYTHON) -m company status
serve:
	$(PYTHON) -m company.service --host 127.0.0.1 --port 8000
PYTHON ?= python3
demo:
	$(PYTHON) -m company demo
test:
	$(PYTHON) -m unittest discover -s tests -v
check: test
	$(PYTHON) scripts/check_bundle.py
status:
	$(PYTHON) -m company status
