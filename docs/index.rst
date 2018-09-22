

=======
CF-GRIB
=======

:Version: |release|
:Date: |today|

Python interface to map GRIB files to the
`NetCDF Common Data Model <https://www.unidata.ucar.edu/software/thredds/current/netcdf-java/CDM/>`_
following the `CF Conventions <http://cfconventions.org/>`_.
The high level API is designed to support a GRIB backend for `xarray <http://xarray.pydata.org/>`_
and it is inspired by `NetCDF-python <http://unidata.github.io/netcdf4-python/>`_
and `h5netcdf <https://github.com/shoyer/h5netcdf>`_.
Low level access and decoding is performed via the
`ECMWF ecCodes library <https://software.ecmwf.int/wiki/display/ECC/>`_.

Features:

- read-only GRIB driver for *xarray*,
- support all modern versions of Python 3.7, 3.6, 3.5 and 2.7, plus PyPy and PyPy3,
- only system dependency is the ecCodes C-library (not the Python2-only module),
- no install time build (binds with *CFFI* ABI mode),
- read the data lazily and efficiently in terms of both memory usage and disk access,
- map a GRIB 1 or 2 file to a set of N-dimensional variables following the NetCDF Common Data Model,
- add CF Conventions attributes to known coordinate and data variables.

Work in progress:

- limited support to read GRIB files containing multiple hypecubes,
  see the *Advanced usage* section below and
  `#2 <https://github.com/ecmwf/cfgrib/issues/2>`_,
  `#13 <https://github.com/ecmwf/cfgrib/issues/13>`_,
- limited support to write carefully-crafted ``xarray.Dataset``'s to a GRIB2 file,
  see the *Advanced write usage* section below and
  `#18 <https://github.com/ecmwf/cfgrib/issues/18>`_,

Limitations:

- development stage: **Alpha**,
- target is correctness, not performance, for now,
- incomplete documentation, for now,
- no support for opening multiple GRIB files, see `#15 <https://github.com/ecmwf/cfgrib/issues/15>`_,
- no Windows support, see `#7 <https://github.com/ecmwf/cfgrib/issues/7>`_,
- rely on *ecCodes* for the CF attributes of the data variables,
- rely on *ecCodes* for the ``gridType`` handling.


.. toctree::
    :maxdepth: 2
    :caption: Table of Contents

    messages
    cfmessage
    dataset
    xarray_store
    xarray_to_grib