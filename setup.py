#!/usr/bin/env python
#
# Copyright 2017-2021 European Centre for Medium-Range Weather Forecasts (ECMWF).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re

import setuptools  # type: ignore


def read(path: str) -> str:
    file_path = os.path.join(os.path.dirname(__file__), *path.split("/"))
    return open(file_path).read()


# single-sourcing the package version using method 1 of:
#   https://packaging.python.org/guides/single-sourcing-package-version/
def parse_version_from(path: str) -> str:
    version_file = read(path)
    version_match = re.search(r'^__version__ = "(.*)"', version_file, re.M)
    if version_match is None or len(version_match.groups()) > 1:
        raise ValueError("couldn't parse version")
    return version_match.group(1)


setuptools.setup(
    name="cfgrib",
    version=parse_version_from("cfgrib/__init__.py"),
    description="Python interface to map GRIB files to the NetCDF Common Data Model "
    "following the CF Convention using ecCodes.",
    long_description=read("README.rst") + read("CHANGELOG.rst"),
    author="European Centre for Medium-Range Weather Forecasts (ECMWF)",
    author_email="software.support@ecmwf.int",
    license="Apache License Version 2.0",
    url="https://github.com/ecmwf/cfgrib",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=["attrs>=19.2", "click", "eccodes>=0.9.8", "numpy"],
    python_requires=">=3.7",
    extras_require={
        "xarray": ["xarray>=0.15"],
        "tests": ["dask[array]", "flake8", "pytest", "pytest-cov", "scipy", "xarray>=0.15"],
    },
    zip_safe=True,
    keywords="eccodes grib xarray",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": ["cfgrib=cfgrib.__main__:cfgrib_cli"],
        "xarray.backends": ["cfgrib=cfgrib.xarray_plugin:CfGribBackend"],
    },
)
