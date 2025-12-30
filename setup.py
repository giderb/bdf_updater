#!/usr/bin/env python3
"""Setup script for BDF Property Updater."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bdf-property-updater",
    version="1.0.0",
    author="BDF Tools",
    author_email="bdf-tools@example.com",
    description="A PyQt5 GUI for updating Nastran BDF shell and bar properties",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/bdf-property-updater",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Engineers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pyNastran>=1.3.4",
        "PyQt5>=5.15.0",
        "pandas>=1.3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-qt>=4.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "bdf-updater=bdf_updater_gui:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["test_data/*.bdf", "test_data/*.csv"],
    },
)
