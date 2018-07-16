
.. highlight: console

Python interface to map GRIB files to the
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


Installation
------------

System dependencies
~~~~~~~~~~~~~~~~~~~

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

Main package
~~~~~~~~~~~~

The package is installed from PyPI with::

    $ pip install cfgrib

You may run a simple self-check with::

    $ python -m cfgrib --selfcheck


Usage
-----

First, you need a well-formed GRIB file, if you don't have one download at hand download our
`ERA5 on pressure levels sample <https://github.com/ecmwf/cfgrib/blob/master/tests/sample-data/era5-levels-members.grib?raw=true>`_::

    $ wget https://github.com/ecmwf/cfgrib/blob/master/tests/sample-data/era5-levels-members.grib?raw=true -O era5-levels-members.grib

    $ python
    >>> import cfgrib
    >>> ds = cfgrib.Dataset.frompath('era5-levels-members.grib')
    >>> ds.dimensions
    OrderedDict([('number', 10), ('forecast_reference_time', 4), ('air_pressure', 2), ('latitude', 61), ('longitude', 120)])
    >>> sorted(ds.variables)
    ['air_pressure', 'forecast_period', 'forecast_reference_time', 'latitude', 'longitude', 'number', 't', 'time', 'z']
    >>> var = ds.variables['t']
    >>> var.dimensions
    ('number', 'forecast_reference_time', 'air_pressure', 'latitude', 'longitude')
    >>> var.data[:, :, :, :, :].mean()
    262.92133


Contributing
------------

Contributions are very welcome. Please see the CONTRIBUTING.rst document for the best way to help.
If you encounter any problems, please file an issue along with a detailed description.

Maintainer:

- Alessandro Amici - `@alexamici <https://github.com/alexamici>`_

Main contributors:

- Baudouin Raoult - ECMWF
- Leonardo Barcaroli - `@leophys <https://github.com/leophys>`_
- Aureliana Barghini - `@aurghs <https://github.com/aurghs>`_

See also the list of `contributors <https://github.com/ecmwf/cfgrib/contributors>`_ who participated in this project.
