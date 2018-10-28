
Python interface to map GRIB files to the
`NetCDF Common Data Model <https://www.unidata.ucar.edu/software/thredds/current/netcdf-java/CDM/>`_
following the `CF Conventions <http://cfconventions.org/>`_.
The high level API is designed to support a GRIB backend for `xarray <http://xarray.pydata.org/>`_
and it is inspired by `NetCDF-python <http://unidata.github.io/netcdf4-python/>`_
and `h5netcdf <https://github.com/shoyer/h5netcdf>`_.
Low level access and decoding is performed via the
`ECMWF ecCodes library <https://software.ecmwf.int/wiki/display/ECC/>`_.

Features with development status **Beta**:

- read-only GRIB driver for *xarray*,
- reads most GRIB 1 and 2 files, for limitations see the *Advanced usage* section below and
  `#13 <https://github.com/ecmwf/cfgrib/issues/13>`_,
- supports all modern versions of Python 3.7, 3.6, 3.5 and 2.7, plus PyPy and PyPy3,
- works on most *Linux* distributions and *MacOS*, the *ecCodes* C-library is the only system dependency,
- PyPI package with no install time build (binds with *CFFI* ABI mode),
- reads the data lazily and efficiently in terms of both memory usage and disk access.
- supports saving the index of a GRIB file to disk, to save a full-file scan on open,
  see `#20 <https://github.com/ecmwf/cfgrib/issues/20>`_.

Work in progress:

- **Pre-Alpha** limited support to write carefully-crafted ``xarray.Dataset``'s to a GRIB2 file,
  see the *Advanced write usage* section below and
  `#18 <https://github.com/ecmwf/cfgrib/issues/18>`_,
- the aim is mostly correctness, but we started working on performance as well.

Limitations:

- no *conda* package, for now,
  see `#5 <https://github.com/ecmwf/cfgrib/issues/5>`_,
- *PyPI* binary packages do not include ecCodes,
  see `#22 <https://github.com/ecmwf/cfgrib/issues/22>`_,
- incomplete documentation, for now,
- no Windows support,
  see `#7 <https://github.com/ecmwf/cfgrib/issues/7>`_,
- no support for opening multiple GRIB files,
  see `#15 <https://github.com/ecmwf/cfgrib/issues/15>`_,
- relys on *ecCodes* for the CF attributes of the data variables,
- relys on *ecCodes* for the ``gridType`` handling.


Installation
============

The package is installed from PyPI with::

    $ pip install cfgrib


System dependencies
-------------------

The Python module depends on the ECMWF *ecCodes* library
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
----------------------

You may try out the high level API in a Python interpreter:

.. code-block: python

>>> import cfgrib
>>> ds = cfgrib.open_file('era5-levels-members.grib')
>>> ds.attributes['GRIB_edition']
1
>>> sorted(ds.dimensions.items())
[('isobaricInhPa', 2), ('latitude', 61), ('longitude', 120), ('number', 10), ('time', 4)]
>>> sorted(ds.variables)
['isobaricInhPa', 'latitude', 'longitude', 'number', 'step', 't', 'time', 'valid_time', 'z']
>>> var = ds.variables['t']
>>> var.dimensions
('number', 'time', 'isobaricInhPa', 'latitude', 'longitude')
>>> var.data[:, :, :, :, :].mean()
262.92133
>>> ds = cfgrib.open_file('era5-levels-members.grib')
>>> ds.attributes['GRIB_edition']
1
>>> sorted(ds.dimensions.items())
[('isobaricInhPa', 2), ('latitude', 61), ('longitude', 120), ('number', 10), ('time', 4)]
>>> sorted(ds.variables)
['isobaricInhPa', 'latitude', 'longitude', 'number', 'step', 't', 'time', 'valid_time', 'z']
>>> var = ds.variables['t']
>>> var.dimensions
('number', 'time', 'isobaricInhPa', 'latitude', 'longitude')
>>> var.data[:, :, :, :, :].mean()
262.92133


Read-only *xarray* GRIB driver
------------------------------

Additionally if you have *xarray* installed ``cfgrib`` can open a GRIB file as a ``xarray.Dataset``::

    $ pip install xarray>=0.10.9

In a Python interpreter try:

.. code-block: python

>>> ds = cfgrib.open_dataset('era5-levels-members.grib')
>>> ds
<xarray.Dataset>
Dimensions:        (isobaricInhPa: 2, latitude: 61, longitude: 120, number: 10, time: 4)
Coordinates:
  * number         (number) int64 0 1 2 3 4 5 6 7 8 9
  * time           (time) datetime64[ns] 2017-01-01 ... 2017-01-02T12:00:00
    step           timedelta64[ns] ...
  * isobaricInhPa  (isobaricInhPa) float64 850.0 500.0
  * latitude       (latitude) float64 90.0 87.0 84.0 81.0 ... -84.0 -87.0 -90.0
  * longitude      (longitude) float64 0.0 3.0 6.0 9.0 ... 351.0 354.0 357.0
    valid_time     (time) datetime64[ns] ...
Data variables:
    z              (number, time, isobaricInhPa, latitude, longitude) float32 ...
    t              (number, time, isobaricInhPa, latitude, longitude) float32 ...
Attributes:
    GRIB_edition:            1
    GRIB_centre:             ecmf
    GRIB_centreDescription:  European Centre for Medium-Range Weather Forecasts
    GRIB_subCentre:          0
    history:                 GRIB to CDM+CF via cfgrib-0.9.../ecCodes-2...


Lower level APIs
----------------

Lower level APIs are not stable and should not be considered public yet.
In particular the internal Python 3 *ecCodes* bindings are not compatible with
the standard *ecCodes* python module.


Advanced usage
==============

``cfgrib.Dataset`` and ``cfgrib.open_dataset`` can open a GRIB file only if all the messages
with the same ``shortName`` can be represented as a single ``cfgrib.Variable`` hypercube.
For example, a variable ``t`` cannot have both ``isobaricInhPa`` and ``hybrid`` ``typeOfLevel``'s,
as this would result in multiple hypercubes for variable ``t``.
Opening a non-conformant GRIB file will fail with a ``ValueError: multiple values for unique key...``
error message, see `#2 <https://github.com/ecmwf/cfgrib/issues/2>`_.

Furthermore if different ``cfgrib.Variable``'s depend on the same coordinate,
the values of the coordinate must match exactly.
For example, if variables ``t`` and ``z`` share the same step coordinate,
they must both have exactly the same set of steps.
Opening a non-conformant GRIB file will fail with a ``ValueError: key present and new value is different...``
error message, see `#13 <https://github.com/ecmwf/cfgrib/issues/13>`_.

In most cases you can handle complex GRIB files containing heterogeneous messages by using
the ``filter_by_keys`` key in ``backend_kwargs`` to select which GRIB messages belong to a
well formed set of hypercubes.

For example to open
`US National Weather Service complex GRIB2 files <http://ftpprd.ncep.noaa.gov/data/nccf/com/nam/prod/>`_
you can use:

.. code-block: python

>>> cfgrib.open_dataset('nam.t00z.awp21100.tm00.grib2',
...     backend_kwargs={'filter_by_keys': {'typeOfLevel': 'surface', 'stepType': 'instant'}})
<xarray.Dataset>
Dimensions:     (x: 93, y: 65)
Coordinates:
    time        datetime64[ns] ...
    step        timedelta64[ns] ...
    surface     int64 ...
    latitude    (y, x) float64 ...
    longitude   (y, x) float64 ...
    valid_time  datetime64[ns] ...
Dimensions without coordinates: x, y
Data variables:
    gust        (y, x) float32 ...
    sp          (y, x) float32 ...
    orog        (y, x) float32 ...
    csnow       (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    history:                 GRIB to CDM+CF via cfgrib-0.9.../ecCodes-2...
>>> cfgrib.open_dataset('nam.t00z.awp21100.tm00.grib2',
...     backend_kwargs={'filter_by_keys': {'typeOfLevel': 'heightAboveGround', 'level': 2}})
<xarray.Dataset>
Dimensions:            (x: 93, y: 65)
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
    r2                 (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    history:                 GRIB to CDM+CF via cfgrib-0.9.../ecCodes-2...

*cfgrib* also provides an **experimental function** that automate the selection of
appropriate ``filter_by_keys`` and returns a list of all valid ``xarray.Dataset``'s
in the GRIB file. The ``open_datasets`` is intended for interactive exploration of a file
and it is not part of the stable API. In the future it may change or be removed altogether.

.. code-block: python

>>> from cfgrib import xarray_store
>>> xarray_store.open_datasets('nam.t00z.awp21100.tm00.grib2')
[<xarray.Dataset>
Dimensions:        (isobaricInhPa: 19, x: 93, y: 65)
Coordinates:
    time           datetime64[ns] ...
    step           timedelta64[ns] ...
  * isobaricInhPa  (isobaricInhPa) float64 1e+03 950.0 900.0 ... 150.0 100.0
    latitude       (y, x) float64 ...
    longitude      (y, x) float64 ...
    valid_time     datetime64[ns] ...
Dimensions without coordinates: x, y
Data variables:
    gh             (isobaricInhPa, y, x) float32 ...
    t              (isobaricInhPa, y, x) float32 ...
    r              (isobaricInhPa, y, x) float32 ...
    w              (isobaricInhPa, y, x) float32 ...
    u              (isobaricInhPa, y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    history:                 GRIB to CDM+CF via cfgrib-0.9.../ecCodes-2..., <xarray.Dataset>
Dimensions:     (x: 93, y: 65)
Coordinates:
    time        datetime64[ns] ...
    step        timedelta64[ns] ...
    cloudBase   int64 ...
    latitude    (y, x) float64 ...
    longitude   (y, x) float64 ...
    valid_time  datetime64[ns] ...
Dimensions without coordinates: x, y
Data variables:
    pres        (y, x) float32 ...
    gh          (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    history:                 GRIB to CDM+CF via cfgrib-0.9.../ecCodes-2..., <xarray.Dataset>
Dimensions:     (x: 93, y: 65)
Coordinates:
    time        datetime64[ns] ...
    step        timedelta64[ns] ...
    cloudTop    int64 ...
    latitude    (y, x) float64 ...
    longitude   (y, x) float64 ...
    valid_time  datetime64[ns] ...
Dimensions without coordinates: x, y
Data variables:
    pres        (y, x) float32 ...
    gh          (y, x) float32 ...
    t           (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    history:                 GRIB to CDM+CF via cfgrib-0.9.../ecCodes-2..., <xarray.Dataset>
Dimensions:     (x: 93, y: 65)
Coordinates:
    time        datetime64[ns] ...
    step        timedelta64[ns] ...
    maxWind     int64 ...
    latitude    (y, x) float64 ...
    longitude   (y, x) float64 ...
    valid_time  datetime64[ns] ...
Dimensions without coordinates: x, y
Data variables:
    pres        (y, x) float32 ...
    gh          (y, x) float32 ...
    u           (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    history:                 GRIB to CDM+CF via cfgrib-0.9.../ecCodes-2..., <xarray.Dataset>
Dimensions:       (x: 93, y: 65)
Coordinates:
    time          datetime64[ns] ...
    step          timedelta64[ns] ...
    isothermZero  int64 ...
    latitude      (y, x) float64 ...
    longitude     (y, x) float64 ...
    valid_time    datetime64[ns] ...
Dimensions without coordinates: x, y
Data variables:
    gh            (y, x) float32 ...
    r             (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    history:                 GRIB to CDM+CF via cfgrib-0.9.../ecCodes-2...]


Advanced write usage
====================

**Please note that write support is Pre-Alpha and highly experimental.**

Only ``xarray.Dataset``'s in *canonical* form,
that is, with the coordinates names matching exactly the *cfgrib* coordinates,
can be saved at the moment:

.. code-block: python

>>> ds = cfgrib.open_dataset('era5-levels-members.grib')
>>> ds
<xarray.Dataset>
Dimensions:        (isobaricInhPa: 2, latitude: 61, longitude: 120, number: 10, time: 4)
Coordinates:
  * number         (number) int64 0 1 2 3 4 5 6 7 8 9
  * time           (time) datetime64[ns] 2017-01-01 ... 2017-01-02T12:00:00
    step           timedelta64[ns] ...
  * isobaricInhPa  (isobaricInhPa) float64 850.0 500.0
  * latitude       (latitude) float64 90.0 87.0 84.0 81.0 ... -84.0 -87.0 -90.0
  * longitude      (longitude) float64 0.0 3.0 6.0 9.0 ... 351.0 354.0 357.0
    valid_time     (time) datetime64[ns] ...
Data variables:
    z              (number, time, isobaricInhPa, latitude, longitude) float32 ...
    t              (number, time, isobaricInhPa, latitude, longitude) float32 ...
Attributes:
    GRIB_edition:            1
    GRIB_centre:             ecmf
    GRIB_centreDescription:  European Centre for Medium-Range Weather Forecasts
    GRIB_subCentre:          0
    history:                 GRIB to CDM+CF via cfgrib-0.9.../ecCodes-2...
>>> cfgrib.canonical_dataset_to_grib(ds, 'out1.grib', grib_keys={'centre': 'ecmf'})
>>> cfgrib.open_dataset('out1.grib')
<xarray.Dataset>
Dimensions:        (isobaricInhPa: 2, latitude: 61, longitude: 120, number: 10, time: 4)
Coordinates:
  * number         (number) int64 0 1 2 3 4 5 6 7 8 9
  * time           (time) datetime64[ns] 2017-01-01 ... 2017-01-02T12:00:00
    step           timedelta64[ns] ...
  * isobaricInhPa  (isobaricInhPa) float64 850.0 500.0
  * latitude       (latitude) float64 90.0 87.0 84.0 81.0 ... -84.0 -87.0 -90.0
  * longitude      (longitude) float64 0.0 3.0 6.0 9.0 ... 351.0 354.0 357.0
    valid_time     (time) datetime64[ns] ...
Data variables:
    z              (number, time, isobaricInhPa, latitude, longitude) float32 ...
    t              (number, time, isobaricInhPa, latitude, longitude) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             ecmf
    GRIB_centreDescription:  European Centre for Medium-Range Weather Forecasts
    GRIB_subCentre:          0
    history:                 GRIB to CDM+CF via cfgrib-0.9.../ecCodes-2...

Per-variable GRIB keys can be set by setting the ``attrs`` variable with key prefixed by ``GRIB_``,
for example:

.. code-block: python

>>> import numpy as np
>>> import xarray as xr
>>> ds2 = xr.DataArray(
...     np.zeros((5, 6)) + 300.,
...     coords=[
...         np.linspace(90., -90., 5),
...         np.linspace(0., 360., 6, endpoint=False),
...     ],
...     dims=['latitude', 'longitude'],
... ).to_dataset(name='skin_temperature')
>>> ds2.skin_temperature.attrs['GRIB_shortName'] = 'skt'
>>> cfgrib.canonical_dataset_to_grib(ds2, 'out2.grib')
>>> cfgrib.open_dataset('out2.grib')
<xarray.Dataset>
Dimensions:     (latitude: 5, longitude: 6)
Coordinates:
    time        datetime64[ns] ...
    step        timedelta64[ns] ...
    surface     int64 ...
  * latitude    (latitude) float64 90.0 45.0 0.0 -45.0 -90.0
  * longitude   (longitude) float64 0.0 60.0 120.0 180.0 240.0 300.0
    valid_time  datetime64[ns] ...
Data variables:
    skt         (latitude, longitude) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             consensus
    GRIB_centreDescription:  Consensus
    GRIB_subCentre:          0
    history:                 GRIB to CDM+CF via cfgrib-0.9.../ecCodes-2...


Contributing
============

The main repository is hosted on GitHub,
testing, bug reports and contributions are highly welcomed and appreciated:

https://github.com/ecmwf/cfgrib

Please see the CONTRIBUTING.rst document for the best way to help.

Lead developer:

- `Alessandro Amici <https://github.com/alexamici>`_ - `B-Open <https://bopen.eu>`_

Main contributors:

- Baudouin Raoult - `ECMWF <https://ecmwf.int>`_
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
