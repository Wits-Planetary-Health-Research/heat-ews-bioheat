# One-command rebuild:  make all
# Steps can be run on their own, e.g. make thresholds

PY ?= python3

.PHONY: all install era5 thresholds bias test run clean

all: install era5 thresholds bias test run

install:
	$(PY) -m pip install -r requirements.txt

# Hourly ERA5 block around Soweto and RMMCH, 1991 to present (public NSF NCAR copy on AWS, about 15 min)
era5:
	$(PY) scripts/pull_ncar_era5.py 1991 $$(date +%Y) 12

# D1 threshold tables, replication check and independent recompute
thresholds:
	$(PY) scripts/build_d1.py
	$(PY) scripts/check_replication.py
	$(PY) scripts/recompute_independent.py > outputs/D1_independent.csv
	$(PY) scripts/compare_recompute.py

# Lead-dependent bias correction trained on past IFS forecasts vs ERA5
bias:
	$(PY) scripts/fit_bias.py

test:
	$(PY) -m pytest -q

run:
	$(PY) -m heatews.run

clean:
	rm -rf outputs docs/index.html docs/status.json
