
PACKAGE := cfgrib
IMAGE := $(PACKAGE)-image
MODULE := $(PACKAGE)
PYTHONS := python3.7 python3.6 python3.5 pypy3 python2.7 pypy
PYTHON := python

PYTESTFLAGS_TEST := -v --flakes --doctest-glob '*.rst' --cov=$(MODULE) --cov=cf2cdm --cov-report=html --cache-clear
PYTESTFLAGS_QC := --pep8 --mccabe $(PYTESTFLAGS_TEST)

export WHEELHOUSE := ~/.wheelhouse
export PIP_FIND_LINKS := $(WHEELHOUSE)
export PIP_WHEEL_DIR := $(WHEELHOUSE)
export PIP_INDEX_URL

DOCKERBUILDFLAGS := --build-arg PIP_INDEX_URL=$(PIP_INDEX_URL)
DOCKERFLAGS := -e WHEELHOUSE=$(WHEELHOUSE) \
	-e PIP_FIND_LINKS=$(PIP_FIND_LINKS) \
	-e PIP_WHEEL_DIR=$(PIP_WHEEL_DIR) \
	-e PIP_INDEX_URL=$(PIP_INDEX_URL)
PIP := $(PYTHON) -m pip
MKDIR = mkdir -p

ifeq ($(shell [ -d $(WHEELHOUSE) ] && echo true),true)
    DOCKERFLAGS += -v $(WHEELHOUSE):/root/.wheelhouse
endif

RUNTIME := $(shell [ -f /proc/1/cgroup ] && cat /proc/1/cgroup | grep -q docker && echo docker)
ifneq ($(RUNTIME),docker)
    override TOXFLAGS += --workdir=.docker-tox
    RUN = docker run --rm -it -v$$(pwd):/src -w/src $(DOCKERFLAGS) $(IMAGE)
endif


default:
	@echo No default

# local targets

$(PIP_FIND_LINKS):
	$(MKDIR) $@

local-wheelhouse-one:
	$(PIP) install wheel
	$(PIP) wheel -r ci/requirements-tests.txt
	$(PIP) wheel -r ci/requirements-docs.txt

local-wheelhouse:
	for PYTHON in $(PYTHONS); do $(MAKE) local-wheelhouse-one PYTHON=$$PYTHON; done
	$(PIP) wheel -r ci/requirements-dev.txt

local-install-dev-req:
	$(PIP) install -r ci/requirements-dev.txt

local-install-test-req: $(PIP_FIND_LINKS)
	$(PIP) install -r ci/requirements-tests.txt
	$(PIP) install -r ci/requirements-docs.txt

local-develop:
	$(PIP) install -e .

local-wheel:
	$(PIP) wheel -e .

testclean:
	$(RM) -r */__pycache__ .coverage .cache tests/.ipynb_checkpoints *.idx tests/sample-data/*.idx out*.grib

clean: testclean
	$(RM) -r */*.pyc htmlcov dist build .eggs

distclean: clean
	$(RM) -r .tox .docker-tox *.egg-info

cacheclean:
	$(RM) -r $(WHEELHOUSE)/* ~/.cache/*

# container targets

shell:
	$(RUN)

notebook: DOCKERFLAGS += -p 8888:8888
notebook:
	$(RUN) jupyter notebook --ip=0.0.0.0 --allow-root

wheelhouse:
	$(RUN) make local-wheelhouse

update-req:
	$(RUN) pip-compile -o ci/requirements-tests.txt -U setup.py ci/requirements-tests.in
	$(RUN) pip-compile -o ci/requirements-docs.txt -U setup.py ci/requirements-docs.in

test: testclean
	$(RUN) $(PYTHON) setup.py test --addopts "$(PYTESTFLAGS_TEST)"

qc: testclean
	$(RUN) $(PYTHON) setup.py test --addopts "$(PYTESTFLAGS_QC)"

doc:
	$(RUN) $(PYTHON) setup.py build_sphinx

tox: testclean
	$(RUN) tox $(TOXFLAGS)

detox: testclean
	$(RUN) detox $(TOXFLAGS)

# image build

image:
	docker build -t $(IMAGE) $(DOCKERBUILDFLAGS) .
