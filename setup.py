from setuptools import setup, find_packages

setup(name='restosaur',
      version='0.1-dev3',
      description='Damn simple RESTful library',
      classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Framework :: Django",
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
      install_requires = ['mimeparse'],
      keywords='web rest python django',
      packages=find_packages('.'),
      include_package_data=True,
      zip_safe=True,
      )
