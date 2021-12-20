import os

from setuptools import find_packages, setup

README_PATH = os.path.join(os.path.dirname(__file__), "README.md")

setup(
    name="restosaur",
    version="0.7.0b18",
    description="Framework independent RESTful library",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 1.11",
        "Framework :: Django :: 2.2",
        "Framework :: Django :: 3.0",
        "Framework :: Django :: 3.1",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
    ],
    author="Marcin Nowak",
    author_email="marcin.j.nowak@gmail.com",
    url="https://github.com/marcinn/restosaur",
    install_requires=["times2==0.8", "six"],
    keywords="web rest python django",
    packages=find_packages("."),
    include_package_data=True,
    test_suite="nose.collector",
    zip_safe=True,
    long_description=open(README_PATH).read(),
    long_description_content_type="text/markdown",
)
