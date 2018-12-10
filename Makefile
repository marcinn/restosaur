PHONY = env

env:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

package:
	@rm -rf dist/
	@mkdir dist
	@python setup.py clean sdist bdist_wheel


upload:
	twine upload dist/*


