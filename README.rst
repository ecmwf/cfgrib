
.. highlights:: bash

CF-GRIB
============

An Python interface to
map GRIB files to the NetCDF Common Data Model with CF Conventions.
The high level APIs are inspired by h5netcdf and NetCDF-python.
Low level access is done via the ECMWF ecCodes C library.

Write support is a planned feature.

The project targets Python 3, but aims to retain Python 2 compatibility as long as
possible.

.. warning::
    The internal Python 3 ecCodes bindings are intended to be private and are not
    compatible with the standard ecCodes python module.


Dependencies
------------

The python module depends on the ECMWF ecCodes library
that must be installed on the system and accessible as a shared library.
Some Linux distributions ship a binary version of ecCodes
that may be installed with the standard package manager.
On Ubuntu 18.04 use the command::

    $ sudo apt-get install libeccodes0

On a MacOS with HomeBrew use::

    $ brew install eccodes

As an alternative you may install the official source distribution
by following the ecCodes instructions at
https://software.ecmwf.int/wiki/display/ECC/ecCodes+installation
Note that ecCodes upport for the Windows operating system is experimental.


Development
-----------

After cloning the repository run::

    cd cfgrib
    pip install -r ci/requirements-tests.txt
    pip install -e .


Test
----

Unit test with::

    pytest -vv --flakes

You can test the GRIB driver on a larger set of products from the Climate Data Store.
In order to automatically download the data files you need to register fo the CDS:

    https://cds.climate.copernicus.eu/user/register

and set up your CDS API key as described in:

    https://cds.climate.copernicus.eu/api-how-to

Then you can run::

    pytest -vv tests/cds_test_*.py

