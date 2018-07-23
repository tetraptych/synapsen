lint:
	flake8 ./

test:
	python -m pytest -s tests

coverage:
	python -m pytest --cov=./ --cov-config .coveragerc --cov-fail-under=75 --cov-report term-missing
