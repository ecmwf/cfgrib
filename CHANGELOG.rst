
Changelog for cfgrib
====================

0.9.6 (2019-02-26)
------------------

- Add support for *Windows* by installing *ecCodes* via *conda*.
  See: `#7 <https://github.com/ecmwf/cfgrib/issues/7>`_.
- Added *conda-forge* package.
  See: `#5 <https://github.com/ecmwf/cfgrib/issues/5>`_.


0.9.5.7 (2019-02-24)
--------------------

- Fixed a serious bug in the computation of the suggested ``filter_by_keys`` for non-cubic
  GRIB files. As a result ``cfgrib.xarray_store.open_datasets`` was not finding all the
  variables in the files.
  See: `#54 <https://github.com/ecmwf/cfgrib/issues/54>`_.
- Fixed a serious bug in variable naming that could drop or at worse mix the values of variables.
  Again see: `#54 <https://github.com/ecmwf/cfgrib/issues/54>`_.
- Re-opened `#45 <https://github.com/ecmwf/cfgrib/issues/45>`_ as the fix was returning wrong data.
  Now we are back to dropping all variable in a MULTI-FIELD except the first.


0.9.5.6 (2019-02-04)
--------------------

- Do not set explicit timezone in ``units`` to avoid crashing some versions of *xarray*.
  See: `#44 <https://github.com/ecmwf/cfgrib/issues/44>`_.


0.9.5.5 (2019-02-02)
--------------------

- Enable ecCodes implicit MULTI-FIELD support by default, needed for NAM Products by NCEP.
  See: `#45 <https://github.com/ecmwf/cfgrib/issues/45>`_.
- Added support for ``depthBelowLand`` coordinate.


0.9.5.4 (2019-01-25)
--------------------

- Add support for building ``valid_time`` from a bad ``time-step`` hypercube.


0.9.5.3 (2019-01-25)
--------------------

- Also convert is ``valid_time`` can index all times and steps in ``translate_coords``.


0.9.5.2 (2019-01-24)
--------------------

- Set ``valid_time`` as preferred time dimension for the CDS data model.
- Fall back to using the generic ``GRIB2`` *ecCodes* template when no better option is found.
  See: `#39 <https://github.com/ecmwf/cfgrib/issues/39>`_.


0.9.5.1 (2018-12-27)
--------------------

- Fix the crash when using ``cf2cdm.translate_coords`` on datasets with non-dimension coordinates.
  See: `#41 <https://github.com/ecmwf/cfgrib/issues/41>`_.
- Added a ``cfgrib`` script that can translate GRIB to netCDF.
  See: `#40 <https://github.com/ecmwf/cfgrib/issues/40>`_.


0.9.5 (2018-12-20)
------------------

- Drop support for *xarray* versions prior to *v0.11* to reduce complexity.
  (This is really only v0.10.9).
  See: `#32 <https://github.com/ecmwf/cfgrib/issues/32>`_.
- Declare the data as ``CF-1.7`` compliant via the  ``Conventions`` global attribute.
  See: `#36 <https://github.com/ecmwf/cfgrib/issues/36>`_.
- Tested larger-than-memory and distributed processing via *dask* and *dask.distributed*.
  See: `#33 <https://github.com/ecmwf/cfgrib/issues/33>`_.
- Promote write support via ``cfgrib.to_grib`` to **Alpha**.
  See: `#18 <https://github.com/ecmwf/cfgrib/issues/18>`_.
- Provide the ``cf2cdm.translate_coords`` utility function to translate the coordinates
  between CF-compliant data models, defined by ``out_name``, ``units`` and ``store_direction``.
  See: `#24 <https://github.com/ecmwf/cfgrib/issues/24>`_.
- Provide ``cfgrib.__version__``.
  See: `#31 <https://github.com/ecmwf/cfgrib/issues/31>`_.
- Raise with a better error message when users attempt to open a file that is not a GRIB.
  See: `#34 <https://github.com/ecmwf/cfgrib/issues/34>`_.
- Make 2D grids for ``rotated_ll`` and ``rotated_gg`` ``gridType``'s.
  See: `#35 <https://github.com/ecmwf/cfgrib/issues/35>`_.


0.9.4.1 (2018-11-08)
--------------------

- Fix formatting for PyPI page.


0.9.4 (2018-11-08)
------------------

- Saves one index file per set of ``index_keys`` in a much more robust way.
- Refactor CF-encoding and add the new ``encode_cf`` option to ``backend_kwargs``.
  See: `#23 <https://github.com/ecmwf/cfgrib/issues/23>`_.
- Refactor error handling and the option to ignore errors (not well documented yet).
  See: `#13 <https://github.com/ecmwf/cfgrib/issues/13>`_.
- Do not crash on ``gridType`` not fully supported by the installed *ecCodes*
  See: `#27 <https://github.com/ecmwf/cfgrib/issues/27>`_.
- Several smaller bug fixes and performance improvements.


0.9.3.1 (2018-10-28)
--------------------

- Assorted README fixes, in particular advertise index file support as alpha.


0.9.3 (2018-10-28)
------------------

- Big performance improvement: add alpha support to save to and read from disk
  the GRIB index produced by the full-file scan at the first open.
  See: `#20 <https://github.com/ecmwf/cfgrib/issues/20>`_.


0.9.2 (2018-10-22)
------------------

- Rename coordinate ``air_pressure`` to ``isobaricInhPa`` for consistency
  with all other vertical ``level`` coordinates.
  See: `#25 <https://github.com/ecmwf/cfgrib/issues/25>`_.


0.9.1.post1 (2018-10-19)
------------------------

- Fix PyPI description.


0.9.1 (2018-10-19)
------------------

- Change the usage of ``cfgrib.open_dataset`` to allign it with ``xarray.open_dataset``,
  in particular ``filter_by_key`` must be added into the ``backend_kwargs`` dictionary.
  See: `#21 <https://github.com/ecmwf/cfgrib/issues/21>`_.

0.9.0 (2018-10-14)
------------------

- Beta release with read support.
