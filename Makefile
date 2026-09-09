.PHONY: install test smoke run predict clean swing swing-fast swing-audit swing-predict swing-scan

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

# ---------------------------------------------------------------- swing engine
swing:  ## full adaptive swing research run on the uploaded file
	PYTHONPATH=src python -m quantlab.swing.cli run --config configs/swing.yaml

swing-fast:  ## quicker pass: fewer engines, smaller search
	PYTHONPATH=src python -m quantlab.swing.cli run --config configs/swing.yaml --fast

swing-audit:  ## data quality report only
	PYTHONPATH=src python -m quantlab.swing.cli audit --config configs/swing.yaml

swing-predict:  ## next-bar signal
	PYTHONPATH=src python -m quantlab.swing.cli predict --config configs/swing.yaml

swing-scan:  ## multi-instrument: pooled model over a folder of per-ticker files
	PYTHONPATH=src python -m quantlab.swing.cli scan --data uploads/universe
