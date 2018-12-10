PHONY = env

env: clean
	pip install -r requirements.txt
	pip install -r requirements-dev.txt


clean:
	find -name "*.py(c|o)" -exec rm {} \;


package:
	@rm -rf dist/
	@mkdir dist
	@python setup.py clean sdist bdist_wheel


upload:
	twine upload dist/*

