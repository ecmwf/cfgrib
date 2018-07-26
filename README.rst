
Python interface to map GRIB files to the
`NetCDF Common Data Model <https://www.unidata.ucar.edu/software/thredds/current/netcdf-java/CDM/>`_
following the `CF Conventions <http://cfconventions.org/>`_.
The high level API is designed to support a GRIB backend for `xarray <http://xarray.pydata.org/>`_
and it is inspired by `NetCDF-python <http://unidata.github.io/netcdf4-python/>`_
and `h5netcdf <https://github.com/shoyer/h5netcdf>`_.
Low level access and decoding is performed via the
`ECMWF ecCodes library <https://software.ecmwf.int/wiki/display/ECC/>`_.

Features:

- provisional GRIB driver for *xarray*,
- support all modern versions of Python 3.7, 3.6, 3.5 and 2.7, plus PyPy and PyPy3,
- read the data lazily and efficiently in terms of both memory usage and disk access,
- map a GRIB 1 or 2 file to a set of N-dimensional variables following the NetCDF Common Data Model,
- add CF Conventions attributes to known coordinate and data variables.

Limitations:

- development stage: **Alpha**,
- limited support for multi-variable GRIB files (yet),
- no write support (yet),
- no support for opening multiple GRIB files (yet),
- incomplete documentation (yet),
- rely on *ecCodes* for the CF attributes of the data variables,
- rely on *ecCodes* for the ``gridType`` handling.


Installation
------------

The package is installed from PyPI with::

    $ pip install cfgrib


System dependencies
~~~~~~~~~~~~~~~~~~~

The python module depends on the ECMWF *ecCodes* library
that must be installed on the system and accessible as a shared library.
Some Linux distributions ship a binary version that may be installed with the standard package manager.
On Ubuntu 18.04 use the command::

    $ sudo apt-get install libeccodes0

On a MacOS with HomeBrew use::

    $ brew install eccodes

As an alternative you may install the official source distribution
by following the instructions at
https://software.ecmwf.int/wiki/display/ECC/ecCodes+installation

Note that *ecCodes* support for the Windows operating system is experimental.

You may run a simple selfcheck command to ensure that your system is set up correctly::

    $ python -m cfgrib selfcheck
    Found: ecCodes v2.7.0.
    Your system is ready.


Usage
-----

First, you need a well-formed GRIB file, if you don't have one at hand you can download our
`ERA5 on pressure levels sample <http://download.ecmwf.int/test-data/cfgrib/era5-levels-members.grib>`_::

    $ wget http://download.ecmwf.int/test-data/cfgrib/era5-levels-members.grib


Dataset / Variable API
~~~~~~~~~~~~~~~~~~~~~~

You may try out the high level API in a python interpreter:

.. code-block: python

>>> import cfgrib
>>> ds = cfgrib.Dataset.frompath('era5-levels-members.grib')
>>> ds.attributes['GRIB_edition']
1
>>> sorted(ds.dimensions.items())
[('air_pressure', 2), ('latitude', 61), ('longitude', 120), ('number', 10), ('time', 4)]
>>> sorted(ds.variables)
['air_pressure', 'latitude', 'longitude', 'number', 'step', 't', 'time', 'valid_time', 'z']
>>> var = ds.variables['t']
>>> var.dimensions
('number', 'time', 'air_pressure', 'latitude', 'longitude')
>>> var.data[:, :, :, :, :].mean()
262.92133


Provisional *xarray* GRIB driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have xarray installed ``cfgrib`` can open a GRIB file as a ``xarray.Dataset``::

    $ pip install xarray

In a Python interpreter try:

.. code-block: python

>>> from cfgrib import xarray_store
>>> ds = xarray_store.open_dataset('era5-levels-members.grib')
>>> ds
<xarray.Dataset>
Dimensions:       (air_pressure: 2, latitude: 61, longitude: 120, number: 10, time: 4)
Coordinates:
  * number        (number) int64 0 1 2 3 4 5 6 7 8 9
  * time          (time) datetime64[ns] 2017-01-01 2017-01-01T12:00:00 ...
    step          timedelta64[ns] ...
  * air_pressure  (air_pressure) float64 850.0 500.0
  * latitude      (latitude) float64 90.0 87.0 84.0 81.0 78.0 75.0 72.0 69.0 ...
  * longitude     (longitude) float64 0.0 3.0 6.0 9.0 12.0 15.0 18.0 21.0 ...
    valid_time    (time) datetime64[ns] ...
Data variables:
    z             (number, time, air_pressure, latitude, longitude) float32 ...
    t             (number, time, air_pressure, latitude, longitude) float32 ...
Attributes:
    GRIB_edition:            1
    GRIB_centre:             ecmf
    GRIB_centreDescription:  European Centre for Medium-Range Weather Forecasts
    GRIB_subCentre:          0
    history:                 GRIB to CDM+CF via cfgrib-0.8.../ecCodes-2...


Lower level APIs
~~~~~~~~~~~~~~~~

Lower level APIs are not stable and should not be considered public yet.
In particular the internal Python 3 *ecCodes* bindings are not compatible with
the standard *ecCodes* python module.


Advanced usage
--------------

``cfgrib.Dataset`` can open a GRIB file only if all the messages
with the same ``shortName`` can be respresented as as a single ``cfgrib.Variable`` hypercube.
For example, a variable ``t`` cannot have both ``isobaricInhPa`` and ``hybrid`` ``typeOfLevel``'s,
as this would result in multiple hypercubes for variable ``t``.
Furthermore if different ``cfgrib.Variable``'s depend on the same coordinate,
the values of the coordinate must match exactly.
For example, if variables ``t`` and ``z`` share the same step coordinate,
they must both have exactly the same set of steps.

You can handle complex GRIB files containing heterogeneous messages by using
the ``filter_by_keys`` keyword to select which GRIB messages belong to a
well formed set of hypercubes.

For example to open
`US National Weather Service complex GRIB2 files <http://ftpprd.ncep.noaa.gov/data/nccf/com/nam/prod/>`_
you can use:

.. code-block: python

>>> from cfgrib.xarray_store import open_dataset
>>> open_dataset('nam.t00z.awip1200.tm00.grib2',
...              filter_by_keys={'typeOfLevel': 'surface', 'stepType': 'instant'})
<xarray.Dataset>
Dimensions:     (x: 614, y: 428)
Coordinates:
    time        datetime64[ns] ...
    step        timedelta64[ns] ...
    surface     int64 ...
    latitude    (y, x) float64 ...
    longitude   (y, x) float64 ...
    valid_time  datetime64[ns] ...
Dimensions without coordinates: x, y
Data variables:
    vis         (y, x) float32 ...
    gust        (y, x) float32 ...
    hindex      (y, x) float32 ...
    sp          (y, x) float32 ...
    orog        (y, x) float32 ...
    t           (y, x) float32 ...
    unknown     (y, x) float32 ...
    sdwe        (y, x) float32 ...
    sde         (y, x) float32 ...
    prate       (y, x) float32 ...
    sr          (y, x) float32 ...
    veg         (y, x) float32 ...
    slt         (y, x) float32 ...
    lsm         (y, x) float32 ...
    ci          (y, x) float32 ...
    al          (y, x) float32 ...
    sst         (y, x) float32 ...
    shtfl       (y, x) float32 ...
    lhtfl       (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    history:                 GRIB to CDM+CF via cfgrib-0.8.../ecCodes-2...
>>> open_dataset('nam.t00z.awip1200.tm00.grib2',
...              filter_by_keys={'typeOfLevel': 'heightAboveGround', 'topLevel': 2})
<xarray.Dataset>
Dimensions:            (x: 614, y: 428)
Coordinates:
    time               datetime64[ns] ...
    step               timedelta64[ns] ...
    heightAboveGround  int64 ...
    latitude           (y, x) float64 ...
    longitude          (y, x) float64 ...
    valid_time         datetime64[ns] ...
Dimensions without coordinates: x, y
Data variables:
    t2m                (y, x) float32 ...
    q                  (y, x) float32 ...
    d2m                (y, x) float32 ...
    r2                 (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    history:                 GRIB to CDM+CF via cfgrib-0.8.../ecCodes-2...


Contributing
------------

The main repository is hosted on GitHub,
testing, bug reports and contributions are highly welcomed and appreciated:

https://github.com/ecmwf/cfgrib

Please see the CONTRIBUTING.rst document for the best way to help.

Lead developer:

- `Alessandro Amici <https://github.com/alexamici>`_ - B-Open

Main contributors:

- Baudouin Raoult - ECMWF
- `Aureliana Barghini <https://github.com/aurghs>`_ - B-Open
- `Iain Russell <https://github.com/iainrussell>`_ - ECMWF
- `Leonardo Barcaroli <https://github.com/leophys>`_ - B-Open

See also the list of `contributors <https://github.com/ecmwf/cfgrib/contributors>`_ who participated in this project.


License
-------

Copyright 2017-2018 European Centre for Medium-Range Weather Forecasts (ECMWF).

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at: http://www.apache.org/licenses/LICENSE-2.0.
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
