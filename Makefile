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

# ---------------------------------------------------------------------------
# Mean-reversion research system (src/quantlab/meanrev)
# ---------------------------------------------------------------------------
.PHONY: meanrev-synthetic meanrev-demo meanrev-app meanrev-signals meanrev-test

meanrev-synthetic:  ## offline end-to-end run on the simulated regime-switching market
	PYTHONPATH=src python -m quantlab.meanrev.cli run --config configs/meanrev_synthetic.yaml

meanrev-demo:       ## SPY, QQQ, AAPL, MSFT from Yahoo Finance (needs network)
	PYTHONPATH=src python -m quantlab.meanrev.cli run --config configs/meanrev_demo.yaml

meanrev-app:        ## research terminal on http://127.0.0.1:8050
	PYTHONPATH=src python -m quantlab.meanrev.cli app

meanrev-signals:    ## today's probabilities for the real-data demo run (incremental update)
	PYTHONPATH=src python -m quantlab.meanrev.cli signals --run artifacts/meanrev/runs/demo-real

meanrev-test:
	PYTHONPATH=src pytest -q tests/meanrev
