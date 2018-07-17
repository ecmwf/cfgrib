
Python interface to map GRIB files to the
`NetCDF Common Data Model <https://www.unidata.ucar.edu/software/thredds/current/netcdf-java/CDM/>`_
following the `CF Conventions <http://cfconventions.org/>`_.
The high level API is designed to support a GRIB backend for `xarray <http://xarray.pydata.org/>`_
and it is inspired by `NetCDF-python <http://unidata.github.io/netcdf4-python/>`_
and `h5netcdf <https://github.com/shoyer/h5netcdf>`_.
Low level access and decoding is performed via the
ECMWF `ecCodes library <https://software.ecmwf.int/wiki/display/ECC/>`_.

Features:

- map a GRIB file to a set of N-dimensional variables following the NetCDF Common Data Model,
- map CF Conventions attributes coordinate and data variables,
- access data variable values from disk efficiently,
- provisional `xarray` GRIB driver,
- no write support yet.

.. highlight: console


Installation
------------

The package is installed from PyPI with::

    $ pip install cfgrib


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

You may run a simple self-check command to ensure that your system is set up correctly::

    $ python -m cfgrib --selfcheck
    Found: ecCodes v2.7.0.
    Your system is ready.


Usage
-----

First, you need a well-formed GRIB file, if you don't have one at hand you can download our
`ERA5 on pressure levels sample <https://github.com/ecmwf/cfgrib/blob/master/tests/sample-data/era5-levels-members.grib?raw=true>`_::

    $ wget https://github.com/ecmwf/cfgrib/blob/master/tests/sample-data/era5-levels-members.grib?raw=true -O era5-levels-members.grib


Dataset / Variable API
~~~~~~~~~~~~~~~~~~~~~~

You may try out the high level API in a python interpreter:

.. highlight: python

>>> import cfgrib
>>> ds = cfgrib.Dataset.frompath('era5-levels-members.grib')
>>> ds.attributes['GRIB_edition']
1
>>> ds.dimensions.items()
[('number', 10), ('forecast_reference_time', 4), ('air_pressure', 2), ('latitude', 61), ('longitude', 120)]
>>> sorted(ds.variables)
['air_pressure', 'forecast_period', 'forecast_reference_time', 'latitude', 'longitude', 'number', 't', 'time', 'z']
>>> var = ds.variables['t']
>>> var.dimensions
('number', 'forecast_reference_time', 'air_pressure', 'latitude', 'longitude')
>>> var.data[:, :, :, :, :].mean()
262.92133


Provisional `xarray` GRIB driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have xarray installed `cfgrib` can open a GRIB file as a `xarray.Dataset`::

    $ pip install xarray

In a Python interpreter try:

.. code-block: python

>>> from cfgrib import xarray_store
>>> ds = xarray_store.open_dataset('era5-levels-members.grib')
>>> ds
<xarray.Dataset>
Dimensions:     (latitude: 61, level: 2, longitude: 120, number: 10, time: 4)
Coordinates:
  * number      (number) int64 0 1 2 3 4 5 6 7 8 9
  * time        (time) datetime64[ns] 2017-01-01 2017-01-01T12:00:00 ...
    step        timedelta64[ns] ...
  * level       (level) float64 8.5e+04 5e+04
  * latitude    (latitude) float64 90.0 87.0 84.0 81.0 78.0 75.0 72.0 69.0 ...
  * longitude   (longitude) float64 0.0 3.0 6.0 9.0 12.0 15.0 18.0 21.0 24.0 ...
    valid_time  (time) datetime64[ns] ...
Data variables:
    z           (number, time, level, latitude, longitude) float32 ...
    t           (number, time, level, latitude, longitude) float32 ...
Attributes:
    GRIB_edition:            1
    GRIB_centre:             ecmf
    GRIB_centreDescription:  European Centre for Medium-Range Weather Forecasts
    GRIB_subCentre:          0
    GRIB_table2Version:      128
    history:                 GRIB to CDM+CF via cfgrib-0.8.0/ecCodes-2.7.0


Lower level APIs
~~~~~~~~~~~~~~~~

Lower level APIs are not stable and should not be considered public yet.
In particular the internal Python 3 ecCodes bindings are not compatible with
the standard ecCodes python module.


Contributing
------------

Contributions are very welcome. Please see the CONTRIBUTING.rst document for the best way to help.
If you encounter any problems, please file an issue along with a detailed description.

Lead developer:

- `Alessandro Amici <https://github.com/alexamici>`_ - B-Open

Main contributors:

- Baudouin Raoult - ECMWF
- `Iain Russell <https://github.com/iainrussell>`_ - ECMWF
- `Leonardo Barcaroli <https://github.com/leophys>`_ - B-Open
- `Aureliana Barghini <https://github.com/aurghs>`_ - B-Open

See also the list of `contributors <https://github.com/ecmwf/cfgrib/contributors>`_ who participated in this project.


License
-------

Copyright 2017-2018 European Centre for Medium-Range Weather Forecasts (ECMWF).

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
