from setuptools import setup, find_packages

setup(name='restosaur',
      version='0.6.8',
      description='Damn simple RESTful library',
      classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 1.6",
        "Framework :: Django :: 1.7",
        "Framework :: Django :: 1.8",
        "Framework :: Django :: 1.9",
        #"Framework :: Django :: 1.10",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
        ],
      author='Marcin Nowak',
      author_email='marcin.j.nowak@gmail.com',
      url='https://github.com/marcinn/restosaur',
      install_requires = ['mimeparse', 'times>=0.7'],
      keywords='web rest python django',
      packages=find_packages('.'),
      include_package_data=True,
      test_suite='nose.collector',
      zip_safe=True,
      )
