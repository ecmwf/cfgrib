
PACKAGE := cfgrib
IMAGE := $(PACKAGE)-image
MODULE := $(PACKAGE)

COV_REPORT := html

default: fix-code-style test

fix-code-style:
	black .
	isort .

unit-test: testclean
	python -m pytest -v --cov=. --cov-report=$(COV_REPORT) tests/

doc-test: testclean
	python -m pytest -v *.rst
	python -m pytest -v --doctest-modules cfgrib

test: unit-test doc-test

code-quality:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	mypy --strict cfgrib tests/test_*py

code-style:
	black --check .
	isort --check .

qc: code-quality

testclean:
	$(RM) -r */__pycache__ .coverage .cache tests/.ipynb_checkpoints *.idx tests/sample-data/*.idx out*.grib

distclean: testclean
	$(RM) -r */*.pyc htmlcov dist build .eggs *.egg-info
