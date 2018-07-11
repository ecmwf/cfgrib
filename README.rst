
.. highlights:: bash

CF-GRIB
=======

A Python interface to map GRIB files to the
`NetCDF Common Data Model <https://www.unidata.ucar.edu/software/thredds/current/netcdf-java/CDM/>`_
following the `CF Conventions <http://cfconventions.org/>`_.
The high level API is designed to support a GRIB backend for `xarray <http://xarray.pydata.org/>`_
and it is inspired by `NetCDF-python <http://unidata.github.io/netcdf4-python/>`_
and `h5netcdf <https://github.com/shoyer/h5netcdf>`_.
Low level access and decoding is performed via the
ECMWF `ecCodes library <https://software.ecmwf.int/wiki/display/ECC/>`_.

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

Note that ecCodes support for the Windows operating system is experimental.


Development
-----------

After cloning the repository run::

    $ cd cfgrib
    $ pip install -r ci/requirements-tests.txt
    $ pip install -e .


Test
----

Unit test with::

    $ pytest -vv --flakes

You can test the CF-GRIB driver on a set of products downloaded from the Climate Data Store.
If you are not register to the CDS portal register at:

    https://cds.climate.copernicus.eu/user/register

In order to automatically download the GRIB files install and configure the `cdsapi` package::

    $ pip install cdsapi

The log into the CDS portal and setup the CDS API key as described in:

    https://cds.climate.copernicus.eu/api-how-to

Then you can run::

    $ pytest -vv tests/cds_test_*.py

