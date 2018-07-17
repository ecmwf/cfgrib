

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
ECMWF `ecCodes library <https://software.ecmwf.int/wiki/display/ECC/>`_.

Features:

- map a GRIB file to a set of N-dimensional variables following the NetCDF Common Data Model,
- map CF Conventions attributes coordinate and data variables,
- access data variable values from disk efficiently,
- no write support yet.


.. toctree::
    :maxdepth: 2
    :caption: Table of Contents

    messages
    dataset
    xarray_store