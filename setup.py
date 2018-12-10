from setuptools import setup, find_packages

setup(name='restosaur',
      version='0.7.0b5',
      description='Framework independent RESTful library',
      classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 1.8",
        "Framework :: Django :: 1.9",
        "Framework :: Django :: 1.10",
        "Framework :: Django :: 1.11",
        "Framework :: Django :: 2.0",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
        ],
      author='Marcin Nowak',
      author_email='marcin.j.nowak@gmail.com',
      url='https://github.com/marcinn/restosaur',
      install_requires=['times>=0.7', 'six'],
      keywords='web rest python django',
      packages=find_packages('.'),
      include_package_data=True,
      test_suite='nose.collector',
      zip_safe=True,
      long_description=open('README.md').read(),
      long_description_content_type='text/markdown',
      )
