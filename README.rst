
.. highlights:: bash

ecCodes-GRIB
============

A Python interface to read GRIB files to a in-memory representation similar to the
NetCDF Common Data Model following the CF Conventions.
The high level APIs are inspired by h5netcdf and NetCDF-python.
Low level access is done via the ECMWF ecCodes C library.

Write support is a planned feature.

The project targets Python 3, but aims to retain Python 2 compatibility as long as
possible.

.. warning::
    The internal Python 3 ecCodes bindings are intended to be private and are not
    compatible with the standard ecCodes python module.


Development
-----------

After cloning the repository run::

    cd eccodes-grib
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

