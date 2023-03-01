.PHONY: env tests upload

env:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

package: tests
	@rm -rf dist/
	@mkdir dist
	@source env/bin/activate && python setup.py bdist_wheel

upload: package
	twine upload --skip-existing dist/*


tests:
	@tox -p all

tests-verbose:
	@tox -v
