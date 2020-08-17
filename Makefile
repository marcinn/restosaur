PHONY = env

env:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

package:
	@rm -rf dist/
	@mkdir dist
	@source .env/bin/activate && python setup.py clean sdist bdist_wheel
	@source .env3/bin/activate && python setup.py bdist_wheel

upload:
	twine upload --skip-existing dist/*

