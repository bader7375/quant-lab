.PHONY: install test smoke run predict clean

install:
	pip install -r requirements.txt

test:
	PYTHONPATH=src pytest -q

smoke:  ## offline end-to-end run on synthetic data
	PYTHONPATH=src python -m quantlab.cli run --config configs/synthetic.yaml

run:    ## real S&P 500 data (needs network access to Yahoo Finance)
	PYTHONPATH=src python -m quantlab.cli run --config configs/default.yaml

predict:
	PYTHONPATH=src python -m quantlab.cli predict --config configs/default.yaml

clean:
	rm -rf artifacts data/cache
