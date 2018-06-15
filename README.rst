
.. highlights:: bash

ecCodes-GRIB
============

Python interface to read and write GRIB files via the ECMWF ecCodes C library.

The project targets Python 3, but aims to retain Python 2 compatibility as long as
possible.

.. warning::
    The API is not compatible and it is not intended to be compatible with ecCodes python bindings.


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

