
Python interface to map GRIB files to the
`Unidata's Common Data Model v4 <https://www.unidata.ucar.edu/software/thredds/current/netcdf-java/CDM/>`_
following the `CF Conventions <http://cfconventions.org/>`_.
The high level API is designed to support a GRIB engine for `xarray <http://xarray.pydata.org/>`_
and it is inspired by `netCDF4-python <http://unidata.github.io/netcdf4-python/>`_
and `h5netcdf <https://github.com/shoyer/h5netcdf>`_.
Low level access and decoding is performed via the
`ECMWF ecCodes library <https://software.ecmwf.int/wiki/display/ECC/>`_.

Features with development status **Beta**:

- enables the ``engine='cfgrib'`` option to read GRIB files with *xarray*,
- reads most GRIB 1 and 2 files including heterogeneous ones with ``cfgrib.open_datasets``,
- supports all modern versions of Python 3.7, 3.6, 3.5 and PyPy3,
- the 0.9.6.x series with support for Python 2 will stay active and receive critical bugfixes,
- works on *Linux*, *MacOS* and *Windows*, the *ecCodes* C-library is the only binary dependency,
- conda-forge package on all supported platforms,
- PyPI package with no install time build (binds via *CFFI* ABI mode),
- reads the data lazily and efficiently in terms of both memory usage and disk access,
- allows larger-than-memory and distributed processing via *dask*,
- supports translating coordinates to different data models and naming conventions,
- supports writing the index of a GRIB file to disk, to save a full-file scan on open.

Work in progress:

- **Alpha** install a ``cfgrib`` utility that can convert a GRIB file ``to_netcdf``
  with a optional conversion to a specific coordinates data model,
  see `#40 <https://github.com/ecmwf/cfgrib/issues/40>`_.
- **Alpha** support writing carefully-crafted ``xarray.Dataset``'s to a GRIB1 or GRIB2 file,
  see the *Advanced write usage* section below and
  `#18 <https://github.com/ecmwf/cfgrib/issues/18>`_.

Limitations:

- relies on *ecCodes* for the CF attributes of the data variables,
- relies on *ecCodes* for anything related to coordinate systems / ``gridType``,
  see `#28 <https://github.com/ecmwf/cfgrib/issues/28>`_.


Installation
============

The easiest way to install *cfgrib* and all its binary dependencies is via `Conda <https://conda.io/>`_::

    $ conda install -c conda-forge cfgrib

alternatively, if you install the binary dependencies yourself, you can install the
Python package from *PyPI* with::

    $ pip install cfgrib


Binary dependencies
-------------------

The Python module depends on the ECMWF *ecCodes* binary library
that must be installed on the system and accessible as a shared library.
Some Linux distributions ship a binary version that may be installed with the standard package manager.
On Ubuntu 18.04 use the command::

    $ sudo apt-get install libeccodes0

On a MacOS with HomeBrew use::

    $ brew install eccodes

Or if you manage binary packages with *Conda* use::

    $ conda install -c conda-forge eccodes

As an alternative you may install the official source distribution
by following the instructions at
https://software.ecmwf.int/wiki/display/ECC/ecCodes+installation

You may run a simple selfcheck command to ensure that your system is set up correctly::

    $ python -m cfgrib selfcheck
    Found: ecCodes v2.12.0.
    Your system is ready.


Usage
=====

First, you need a well-formed GRIB file, if you don't have one at hand you can download our
`ERA5 on pressure levels sample <http://download.ecmwf.int/test-data/cfgrib/era5-levels-members.grib>`_::

    $ wget http://download.ecmwf.int/test-data/cfgrib/era5-levels-members.grib


Read-only *xarray* GRIB engine
------------------------------

Most of *cfgrib* users want to open a GRIB file as a ``xarray.Dataset`` and
need to have *xarray>=0.12.0* installed::

    $ pip install xarray>=0.12.0

In a Python interpreter try:

.. code-block: python

>>> import xarray as xr
>>> ds = xr.open_dataset('era5-levels-members.grib', engine='cfgrib')
>>> ds
<xarray.Dataset>
Dimensions:        (isobaricInhPa: 2, latitude: 61, longitude: 120, number: 10, time: 4)
Coordinates:
  * number         (number) int64 0 1 2 3 4 5 6 7 8 9
  * time           (time) datetime64[ns] 2017-01-01 ... 2017-01-02T12:00:00
    step           timedelta64[ns] ...
  * isobaricInhPa  (isobaricInhPa) int64 850 500
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
    Conventions:             CF-1.7
    institution:             European Centre for Medium-Range Weather Forecasts
    history:                 ...

The *cfgrib* ``engine`` supports all read-only features of *xarray* like:

* merge the content of several GRIB files into a single dataset using ``xarray.open_mfdataset``,
* work with larger-than-memory datasets with `dask <https://dask.org/>`_,
* allow distributed processing with `dask.distributed <http://distributed.dask.org>`_.


Read arbitrary GRIB keys
------------------------

By default *cfgrib* reads a limited set of ecCodes recognised *keys* from the GRIB files
and exposes them as ``Dataset`` or ``DataArray`` attributes with the ``GRIB_`` prefix.
It is possible to have *cfgrib* read additional keys to the attributes by adding the
``read_keys`` dictionary key to the ``backend_kwargs`` with values the list of desired GRIB keys:

.. code-block: python

>>> ds = xr.open_dataset('era5-levels-members.grib', engine='cfgrib',
...                      backend_kwargs={'read_keys': ['experimentVersionNumber']})
>>> ds.t.attrs['GRIB_experimentVersionNumber']
'0001'


Translate to a custom data model
--------------------------------

Contrary to netCDF the GRIB data format is not self-describing and several details of the mapping
to the *Unidata Common Data Model* are arbitrarily set by the software components decoding the format.
Details like names and units of the coordinates are particularly important because
*xarray* broadcast and selection rules depend on them.
``cf2cfm`` is a small coordinate translation module distributed with *cfgrib* that make it easy to
translate CF compliant coordinates, like the one provided by *cfgrib*, to a user-defined
custom data model with set ``out_name``, ``units`` and ``stored_direction``.

For example to translate a *cfgrib* styled `xr.Dataset` to the classic *ECMWF* coordinate
naming conventions you can:

.. code-block: python

>>> import cf2cdm
>>> ds = xr.open_dataset('era5-levels-members.grib', engine='cfgrib')
>>> cf2cdm.translate_coords(ds, cf2cdm.ECMWF)
<xarray.Dataset>
Dimensions:     (latitude: 61, level: 2, longitude: 120, number: 10, time: 4)
Coordinates:
  * number      (number) int64 0 1 2 3 4 5 6 7 8 9
  * time        (time) datetime64[ns] 2017-01-01 ... 2017-01-02T12:00:00
    step        timedelta64[ns] ...
  * level       (level) int64 850 500
  * latitude    (latitude) float64 90.0 87.0 84.0 81.0 ... -84.0 -87.0 -90.0
  * longitude   (longitude) float64 0.0 3.0 6.0 9.0 ... 348.0 351.0 354.0 357.0
    valid_time  (time) datetime64[ns] ...
Data variables:
    z           (number, time, level, latitude, longitude) float32 ...
    t           (number, time, level, latitude, longitude) float32 ...
Attributes:
    GRIB_edition:            1
    GRIB_centre:             ecmf
    GRIB_centreDescription:  European Centre for Medium-Range Weather Forecasts
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             European Centre for Medium-Range Weather Forecasts
    history:                 ...

To translate to the Common Data Model of the Climate Data Store use:

.. code-block: python

>>> import cf2cdm
>>> cf2cdm.translate_coords(ds, cf2cdm.CDS)
<xarray.Dataset>
Dimensions:                  (forecast_reference_time: 4, lat: 61, lon: 120, plev: 2, realization: 10)
Coordinates:
  * realization              (realization) int64 0 1 2 3 4 5 6 7 8 9
  * forecast_reference_time  (forecast_reference_time) datetime64[ns] 2017-01-01 ... 2017-01-02T12:00:00
    leadtime                 timedelta64[ns] ...
  * plev                     (plev) float64 8.5e+04 5e+04
  * lat                      (lat) float64 -90.0 -87.0 -84.0 ... 84.0 87.0 90.0
  * lon                      (lon) float64 0.0 3.0 6.0 9.0 ... 351.0 354.0 357.0
    time                     (forecast_reference_time) datetime64[ns] ...
Data variables:
    z                        (realization, forecast_reference_time, plev, lat, lon) float32 ...
    t                        (realization, forecast_reference_time, plev, lat, lon) float32 ...
Attributes:
    GRIB_edition:            1
    GRIB_centre:             ecmf
    GRIB_centreDescription:  European Centre for Medium-Range Weather Forecasts
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             European Centre for Medium-Range Weather Forecasts
    history:                 ...


Filter heterogeneous GRIB files
-------------------------------

``xr.open_dataset`` can open a GRIB file only if all the messages
with the same ``shortName`` can be represented as a single hypercube.
For example, a variable ``t`` cannot have both ``isobaricInhPa`` and ``hybrid`` ``typeOfLevel``'s,
as this would result in multiple hypercubes for the same variable.
Opening a non-conformant GRIB file will fail with a ``ValueError: multiple values for unique key...``
error message, see `#2 <https://github.com/ecmwf/cfgrib/issues/2>`_.

Furthermore if different variables depend on the same coordinate, for example ``step``,
the values of the coordinate must match exactly.
For example, if variables ``t`` and ``z`` share the same ``step`` coordinate,
they must both have exactly the same set of steps.
Opening a non-conformant GRIB file will fail with a ``ValueError: key present and new value is different...``
error message, see `#13 <https://github.com/ecmwf/cfgrib/issues/13>`_.

In most cases you can handle complex GRIB files containing heterogeneous messages by passing
the ``filter_by_keys`` key in ``backend_kwargs`` to select which GRIB messages belong to a
well formed set of hypercubes.

For example to open
`US National Weather Service complex GRIB2 files <http://ftpprd.ncep.noaa.gov/data/nccf/com/nam/prod/>`_
you can use:

.. code-block: python

>>> xr.open_dataset('nam.t00z.awp21100.tm00.grib2', engine='cfgrib',
...     backend_kwargs={'filter_by_keys': {'typeOfLevel': 'surface'}})
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
    tp          (y, x) float32 ...
    acpcp       (y, x) float32 ...
    csnow       (y, x) float32 ...
    cicep       (y, x) float32 ...
    cfrzr       (y, x) float32 ...
    crain       (y, x) float32 ...
    cape        (y, x) float32 ...
    cin         (y, x) float32 ...
    hpbl        (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP...
    history:                 ...
>>> xr.open_dataset('nam.t00z.awp21100.tm00.grib2', engine='cfgrib',
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
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP...
    history:                 ...


Automatic filtering
-------------------

*cfgrib* also provides a function that automate the selection of appropriate ``filter_by_keys``
and returns a list of all valid ``xarray.Dataset``'s in the GRIB file.

.. code-block: python

>>> import cfgrib
>>> cfgrib.open_datasets('nam.t00z.awp21100.tm00.grib2')
[<xarray.Dataset>
Dimensions:     (x: 93, y: 65)
Coordinates:
    time        datetime64[ns] 2018-09-17
    step        timedelta64[ns] 00:00:00
    cloudBase   int64 0
    latitude    (y, x) float64 12.19 12.39 12.58 12.77 ... 57.68 57.49 57.29
    longitude   (y, x) float64 226.5 227.2 227.9 228.7 ... 308.5 309.6 310.6
    valid_time  datetime64[ns] 2018-09-17
Dimensions without coordinates: x, y
Data variables:
    pres        (y, x) float32 ...
    gh          (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:     (x: 93, y: 65)
Coordinates:
    time        datetime64[ns] 2018-09-17
    step        timedelta64[ns] 00:00:00
    cloudTop    int64 0
    latitude    (y, x) float64 12.19 12.39 12.58 12.77 ... 57.68 57.49 57.29
    longitude   (y, x) float64 226.5 227.2 227.9 228.7 ... 308.5 309.6 310.6
    valid_time  datetime64[ns] 2018-09-17
Dimensions without coordinates: x, y
Data variables:
    pres        (y, x) float32 ...
    t           (y, x) float32 ...
    gh          (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:            (x: 93, y: 65)
Coordinates:
    time               datetime64[ns] 2018-09-17
    step               timedelta64[ns] 00:00:00
    heightAboveGround  int64 10
    latitude           (y, x) float64 ...
    longitude          (y, x) float64 ...
    valid_time         datetime64[ns] ...
Dimensions without coordinates: x, y
Data variables:
    u10                (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:            (x: 93, y: 65)
Coordinates:
    time               datetime64[ns] 2018-09-17
    step               timedelta64[ns] 00:00:00
    heightAboveGround  int64 2
    latitude           (y, x) float64 12.19 12.39 12.58 ... 57.68 57.49 57.29
    longitude          (y, x) float64 226.5 227.2 227.9 ... 308.5 309.6 310.6
    valid_time         datetime64[ns] 2018-09-17
Dimensions without coordinates: x, y
Data variables:
    t2m                (y, x) float32 ...
    r2                 (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:                 (heightAboveGroundLayer: 2, x: 93, y: 65)
Coordinates:
    time                    datetime64[ns] 2018-09-17
    step                    timedelta64[ns] 00:00:00
  * heightAboveGroundLayer  (heightAboveGroundLayer) int64 1000 3000
    latitude                (y, x) float64 ...
    longitude               (y, x) float64 ...
    valid_time              datetime64[ns] ...
Dimensions without coordinates: x, y
Data variables:
    hlcy                    (heightAboveGroundLayer, y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:        (isobaricInhPa: 19, x: 93, y: 65)
Coordinates:
    time           datetime64[ns] 2018-09-17
    step           timedelta64[ns] 00:00:00
  * isobaricInhPa  (isobaricInhPa) int64 1000 950 900 850 ... 250 200 150 100
    latitude       (y, x) float64 12.19 12.39 12.58 12.77 ... 57.68 57.49 57.29
    longitude      (y, x) float64 226.5 227.2 227.9 228.7 ... 308.5 309.6 310.6
    valid_time     datetime64[ns] 2018-09-17
Dimensions without coordinates: x, y
Data variables:
    t              (isobaricInhPa, y, x) float32 ...
    u              (isobaricInhPa, y, x) float32 ...
    v              (isobaricInhPa, y, x) float32 ...
    w              (isobaricInhPa, y, x) float32 ...
    gh             (isobaricInhPa, y, x) float32 ...
    r              (isobaricInhPa, y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:        (isobaricInhPa: 5, x: 93, y: 65)
Coordinates:
    time           datetime64[ns] 2018-09-17
    step           timedelta64[ns] 00:00:00
  * isobaricInhPa  (isobaricInhPa) int64 1000 850 700 500 250
    latitude       (y, x) float64 ...
    longitude      (y, x) float64 ...
    valid_time     datetime64[ns] ...
Dimensions without coordinates: x, y
Data variables:
    absv           (isobaricInhPa, y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:       (x: 93, y: 65)
Coordinates:
    time          datetime64[ns] 2018-09-17
    step          timedelta64[ns] 00:00:00
    isothermZero  int64 0
    latitude      (y, x) float64 12.19 12.39 12.58 12.77 ... 57.68 57.49 57.29
    longitude     (y, x) float64 226.5 227.2 227.9 228.7 ... 308.5 309.6 310.6
    valid_time    datetime64[ns] 2018-09-17
Dimensions without coordinates: x, y
Data variables:
    gh            (y, x) float32 ...
    r             (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:     (x: 93, y: 65)
Coordinates:
    time        datetime64[ns] 2018-09-17
    step        timedelta64[ns] 00:00:00
    maxWind     int64 0
    latitude    (y, x) float64 12.19 12.39 12.58 12.77 ... 57.68 57.49 57.29
    longitude   (y, x) float64 226.5 227.2 227.9 228.7 ... 308.5 309.6 310.6
    valid_time  datetime64[ns] 2018-09-17
Dimensions without coordinates: x, y
Data variables:
    pres        (y, x) float32 ...
    u           (y, x) float32 ...
    v           (y, x) float32 ...
    gh          (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:     (x: 93, y: 65)
Coordinates:
    time        datetime64[ns] 2018-09-17
    step        timedelta64[ns] 00:00:00
    meanSea     int64 0
    latitude    (y, x) float64 12.19 12.39 12.58 12.77 ... 57.68 57.49 57.29
    longitude   (y, x) float64 226.5 227.2 227.9 228.7 ... 308.5 309.6 310.6
    valid_time  datetime64[ns] 2018-09-17
Dimensions without coordinates: x, y
Data variables:
    prmsl       (y, x) float32 ...
    mslet       (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:                  (pressureFromGroundLayer: 2, x: 93, y: 65)
Coordinates:
    time                     datetime64[ns] 2018-09-17
    step                     timedelta64[ns] 00:00:00
  * pressureFromGroundLayer  (pressureFromGroundLayer) int64 9000 18000
    latitude                 (y, x) float64 12.19 12.39 12.58 ... 57.49 57.29
    longitude                (y, x) float64 226.5 227.2 227.9 ... 309.6 310.6
    valid_time               datetime64[ns] 2018-09-17
Dimensions without coordinates: x, y
Data variables:
    cape                     (pressureFromGroundLayer, y, x) float32 ...
    cin                      (pressureFromGroundLayer, y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:                  (pressureFromGroundLayer: 5, x: 93, y: 65)
Coordinates:
    time                     datetime64[ns] 2018-09-17
    step                     timedelta64[ns] 00:00:00
  * pressureFromGroundLayer  (pressureFromGroundLayer) int64 3000 6000 ... 15000
    latitude                 (y, x) float64 12.19 12.39 12.58 ... 57.49 57.29
    longitude                (y, x) float64 226.5 227.2 227.9 ... 309.6 310.6
    valid_time               datetime64[ns] 2018-09-17
Dimensions without coordinates: x, y
Data variables:
    t                        (pressureFromGroundLayer, y, x) float32 ...
    u                        (pressureFromGroundLayer, y, x) float32 ...
    v                        (pressureFromGroundLayer, y, x) float32 ...
    r                        (pressureFromGroundLayer, y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:                  (x: 93, y: 65)
Coordinates:
    time                     datetime64[ns] 2018-09-17
    step                     timedelta64[ns] 00:00:00
    pressureFromGroundLayer  int64 3000
    latitude                 (y, x) float64 ...
    longitude                (y, x) float64 ...
    valid_time               datetime64[ns] ...
Dimensions without coordinates: x, y
Data variables:
    pli                      (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:                  (x: 93, y: 65)
Coordinates:
    time                     datetime64[ns] 2018-09-17
    step                     timedelta64[ns] 00:00:00
    pressureFromGroundLayer  int64 18000
    latitude                 (y, x) float64 ...
    longitude                (y, x) float64 ...
    valid_time               datetime64[ns] ...
Dimensions without coordinates: x, y
Data variables:
    4lftx                    (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:     (x: 93, y: 65)
Coordinates:
    time        datetime64[ns] 2018-09-17
    step        timedelta64[ns] 00:00:00
    surface     int64 0
    latitude    (y, x) float64 12.19 12.39 12.58 12.77 ... 57.68 57.49 57.29
    longitude   (y, x) float64 226.5 227.2 227.9 228.7 ... 308.5 309.6 310.6
    valid_time  datetime64[ns] 2018-09-17
Dimensions without coordinates: x, y
Data variables:
    cape        (y, x) float32 ...
    sp          (y, x) float32 ...
    acpcp       (y, x) float32 ...
    cin         (y, x) float32 ...
    orog        (y, x) float32 ...
    tp          (y, x) float32 ...
    crain       (y, x) float32 ...
    cfrzr       (y, x) float32 ...
    cicep       (y, x) float32 ...
    csnow       (y, x) float32 ...
    gust        (y, x) float32 ...
    hpbl        (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:     (x: 93, y: 65)
Coordinates:
    time        datetime64[ns] 2018-09-17
    step        timedelta64[ns] 00:00:00
    tropopause  int64 0
    latitude    (y, x) float64 12.19 12.39 12.58 12.77 ... 57.68 57.49 57.29
    longitude   (y, x) float64 226.5 227.2 227.9 228.7 ... 308.5 309.6 310.6
    valid_time  datetime64[ns] 2018-09-17
Dimensions without coordinates: x, y
Data variables:
    pres        (y, x) float32 ...
    t           (y, x) float32 ...
    u           (y, x) float32 ...
    v           (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP , <xarray.Dataset>
Dimensions:     (x: 93, y: 65)
Coordinates:
    time        datetime64[ns] 2018-09-17
    step        timedelta64[ns] 00:00:00
    level       int64 0
    latitude    (y, x) float64 ...
    longitude   (y, x) float64 ...
    valid_time  datetime64[ns] ...
Dimensions without coordinates: x, y
Data variables:
    pwat        (y, x) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             kwbc
    GRIB_centreDescription:  US National Weather Service - NCEP...
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             US National Weather Service - NCEP ]


Advanced usage
==============

Write support
=============

**Please note that write support is Alpha.**
Only ``xarray.Dataset``'s in *canonical* form,
that is, with the coordinates names matching exactly the *cfgrib* coordinates,
can be saved at the moment:

.. code-block: python

>>> ds = xr.open_dataset('era5-levels-members.grib', engine='cfgrib')
>>> ds
<xarray.Dataset>
Dimensions:        (isobaricInhPa: 2, latitude: 61, longitude: 120, number: 10, time: 4)
Coordinates:
  * number         (number) int64 0 1 2 3 4 5 6 7 8 9
  * time           (time) datetime64[ns] 2017-01-01 ... 2017-01-02T12:00:00
    step           timedelta64[ns] ...
  * isobaricInhPa  (isobaricInhPa) int64 850 500
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
    Conventions:             CF-1.7
    institution:             European Centre for Medium-Range Weather Forecasts
    history:                 ...
>>> cfgrib.to_grib(ds, 'out1.grib', grib_keys={'edition': 2})
>>> xr.open_dataset('out1.grib', engine='cfgrib')
<xarray.Dataset>
Dimensions:        (isobaricInhPa: 2, latitude: 61, longitude: 120, number: 10, time: 4)
Coordinates:
  * number         (number) int64 0 1 2 3 4 5 6 7 8 9
  * time           (time) datetime64[ns] 2017-01-01 ... 2017-01-02T12:00:00
    step           timedelta64[ns] ...
  * isobaricInhPa  (isobaricInhPa) int64 850 500
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
    Conventions:             CF-1.7
    institution:             European Centre for Medium-Range Weather Forecasts
    history:                 ...

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
>>> cfgrib.to_grib(ds2, 'out2.grib')
>>> xr.open_dataset('out2.grib', engine='cfgrib')
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
    Conventions:             CF-1.7
    institution:             Consensus
    history:                 ...

Dataset / Variable API
----------------------

The use of *xarray* is not mandatory and you can access the content of a GRIB file as
an hypercube with the high level API in a Python interpreter:

.. code-block: python

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


GRIB index file
---------------

By default *cfgrib* saves the index of the GRIB file to disk appending ``.idx``
to the GRIB file name.
Index files are an **experimental** and completely optional feature, feel free to
remove them and try again in case of problems. Index files saving can be disable passing
adding ``indexpath=''`` to the ``backend_kwargs`` keyword argument.


Project resources
=================

============= =========================================================
Development   https://github.com/ecmwf/cfgrib
Download      https://pypi.org/project/cfgrib
User support  https://stackoverflow.com/search?q=cfgrib
Code quality  .. image:: https://api.travis-ci.org/ecmwf/cfgrib.svg?branch=master
                :target: https://travis-ci.org/ecmwf/cfgrib/branches
                :alt: Build Status on Travis CI
              .. image:: https://ci.appveyor.com/api/projects/status/github/ecmwf/cfgrib?svg=true&passingText=passing&failingText=failing&pendingText=pending
                :target: https://ci.appveyor.com/project/StephanSiemen/cfgrib
                :alt: Build Status on Appveyor
              .. image:: https://coveralls.io/repos/ecmwf/cfgrib/badge.svg?branch=master&service=github
                :target: https://coveralls.io/github/ecmwf/cfgrib
                :alt: Coverage Status on Coveralls
============= =========================================================


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
=======

Copyright 2017-2019 European Centre for Medium-Range Weather Forecasts (ECMWF).

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at: http://www.apache.org/licenses/LICENSE-2.0.
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
