package:
	@rm -rf dist/
	@mkdir dist
	@python setup.py clean sdist bdist_wheel


upload:
	twine upload dist/*
