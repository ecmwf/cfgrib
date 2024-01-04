

=======
CF-GRIB
=======

:Version: |release|
:Date: |today|

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
- supports all modern versions of Python and PyPy3,
- the 0.9.6.x series with support for Python 2 will stay active and receive critical bugfixes,
- works on *Linux*, *MacOS* and *Windows*, the *ecCodes* C-library is the only binary dependency,
- conda-forge package on all supported platforms,
- PyPI package with no install time build (binds via *CFFI* ABI mode),
- reads the data lazily and efficiently in terms of both memory usage and disk access,
- allows larger-than-memory and distributed processing via *dask*,
- supports translating coordinates to different data models and naming conventions,
- supports writing the index of a GRIB file to disk, to save a full-file scan on open.

Work in progress:

- **Alpha** limited support for MULTI-FIELD messages, e.g. u-v components,
  see `#76 <https://github.com/ecmwf/cfgrib/issues/76>`_.
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


.. toctree::
    :maxdepth: 2
    :caption: Table of Contents

    messages
    cfmessage
    dataset
    xarray_store
    xarray_to_grib
