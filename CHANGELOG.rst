
Changelog for cfgrib
====================

0.9.14.0 (2024-07-19)
---------------------

- Added `coords_as_attributes` argument to `open_dataset()` to allow selected dimensions
  to be stored as attributes rather than dimensions, allowing more heterogeneous data
  to be encoded as an xarray dataset.
  See `#394 <https://github.com/ecmwf/cfgrib/pull/394>`_.

- Added valid_month dimension if monthlyVerificationDate and validityTime are available.
  See `#393 <https://github.com/ecmwf/cfgrib/pull/393>`_.

- Added uvRelativeToGrid to list of GRIB keys read by default.
  See `#379 <https://github.com/ecmwf/cfgrib/pull/379>`_.

0.9.13.0 (2024-06-27)
---------------------

- Allow users to pass of list of values to filter a key by.
  See `#384 <https://github.com/ecmwf/cfgrib/pull/384>`_.

- Functionality to ignore keys when reading a grib file
  See `#382 <https://github.com/ecmwf/cfgrib/pull/382>`_.

- Preserve coordinate encoding in cfgrib.open_datasets
  See `#381 <https://github.com/ecmwf/cfgrib/pull/381>`_.

0.9.12.0 (2024-05-26)
---------------------

- fixed issue where GRIB messages with non-hourly steps could not be read
  See `#370 <https://github.com/ecmwf/cfgrib/pull/370>`_.


0.9.11.0 (2024-04-05)
---------------------

- added automatic caching of geographic coordinates for improved performance
  See `#341 <https://github.com/ecmwf/cfgrib/pull/341>`_.

- fixed issue where to_grib() could crash if given a dataset with a single-valued dimension
  See `#347 <https://github.com/ecmwf/cfgrib/issues/347>`_.

- fixed issue where values could not be extracted when alternativeRowScanning=1 and
  grid is not represented as 2D
  See `#358 <https://github.com/ecmwf/cfgrib/issues/358>`_.

- fixed issue where the `grib_errors` parameter was not being handled correctly.
  This parameter has now been renamed to `errors`.
  See `#349 <https://github.com/ecmwf/cfgrib/issues/349>`_.

- dropped support for Python 3.6.
  See `#363 <https://github.com/ecmwf/cfgrib/issues/363>`_.


0.9.10.4 (2023-05-19)
---------------------

- added --var-encoding-json (or -v) option to the to_netcdf tool, e.g.
  ``cfgrib to_netcdf -v '{"dtype": "float", "scale_factor": 0.1}' -o $OUTFILE $INFILE``
  See `#334 <https://github.com/ecmwf/cfgrib/pull/334>`_.
- fix issue where xarrays derived from Gaussian grids did not have the correct
  geometry when written back out as GRIB
  See `#330 <https://github.com/ecmwf/cfgrib/issues/330>`_.
- fix issue where open_datasets() could merge different GRIB fields
  that have the same data values
  See `#336 <https://github.com/ecmwf/cfgrib/issues/336>`_.

0.9.10.3 (2022-11-24)
---------------------

- large reduction in memory leak
  See `#320 <https://github.com/ecmwf/cfgrib/pull/320/>`_.

- Replaced ``distutils.version`` by ``packaging.version`` and
  added description and url to the xarray plugin.
  See `#318 <https://github.com/ecmwf/cfgrib/pull/318/>`_.


0.9.10.2 (2022-10-04)
---------------------

- added --netcdf_kwargs_json option to 'cfgrib to_netcdf'
  See `#294 <https://github.com/ecmwf/cfgrib/pull/294/>`_.
- fixed support for GRIB files with alternativeRowScanning=1
  See  `#296 <https://github.com/ecmwf/cfgrib/pull/296/>`_.
- fixed support for missing values
  See `#313 <https://github.com/ecmwf/cfgrib/issues/313>`_.


0.9.10.1 (2022-03-16)
---------------------

- Fix failure to read index files.
  See `#292 <https://github.com/ecmwf/cfgrib/issues/292>`_.
- Allow backend kwargs to be provided in the to_netcdf executable,
  either via a json format string, or a path to a json file via -b.
  See `#288 <https://github.com/ecmwf/cfgrib/pull/288/>`_.
- Fixed issue where the use of relpath() could cause a problem on Windows.
  See `#284 <https://github.com/ecmwf/cfgrib/issues/284>`_.
- Fix passing of pathlib.Path.
  See `#282 <https://github.com/ecmwf/cfgrib/issues/282>`_.
- Fixed issue where writing an ensemble number into a GRIB file caused an error.
  See `#278 <https://github.com/ecmwf/cfgrib/issues/278>`_.


0.9.10.0 (2022-01-31)
---------------------

- Big internal refactor to add support for a generic ``Fieldset`` similar to Metview.
  See `#243 <https://github.com/ecmwf/cfgrib/issues/243>`_.


0.9.9.1 (2021-09-29)
--------------------

- Fix the plugin interface that was missing ``extra_coords``.
  See `#231 <https://github.com/ecmwf/cfgrib/issues/231>`_.
- Fix the crash when ``extra_coords`` return a scalar.
  See `#238 <https://github.com/ecmwf/cfgrib/issues/238>`_.
- Improve type-hints.
  Needed by `#243 <https://github.com/ecmwf/cfgrib/issues/243>`_.


0.9.9.0 (2021-04-09)
--------------------

- Depend on the ECMWF `eccodes python package <https://pypi.org/project/eccodes>`_ to access
  the low level ecCodes C-library, dropping all other GRIB decoding options.
  See: `#95 <https://github.com/ecmwf/cfgrib/issues/95>`_,
  `#14 <https://github.com/ecmwf/cfgrib/issues/14>`_.
  `#204 <https://github.com/ecmwf/cfgrib/issues/204>`_,
  `#147 <https://github.com/ecmwf/cfgrib/issues/147>`_ and
  `#141 <https://github.com/ecmwf/cfgrib/issues/141>`_.
- Many performance improvements during the generation of the index and during data access.
  See: `#142 <https://github.com/ecmwf/cfgrib/issues/142>`_ and
  `#197 <https://github.com/ecmwf/cfgrib/issues/197>`_.
- ``filter_by_keys`` now can select on all keys known to *ecCodes* without the need to
  add non default ones to ``read_keys`` explicitly.
  See: `#187 <https://github.com/ecmwf/cfgrib/issues/187>`_.
- Include support for `engine="cfgrib"` using *xarray* 0.18+ new backend API.
  See: `#216 <https://github.com/ecmwf/cfgrib/pull/216>`_.
- Fixed issue where could not load a GRIB message that has only one grid point.
  See: `#199 <https://github.com/ecmwf/cfgrib/issues/199>`_.
- Decode ``level`` coordinates as float in all cases, fixed issue with non-int levels.
  See: `#195 <https://github.com/ecmwf/cfgrib/issues/195>`_.


0.9.8.5 (2020-11-11)
--------------------

- Simpler and clearer messages in the event of errors.
- Use `ECCODES_DIR` environment variable if present. Ported from *eccodes-python*
  by xavierabellan. See: `#162 <https://github.com/ecmwf/cfgrib/issues/162>`_.
- Fix using current ecCodes bindings when setting `CFGRIB_USE_EXTERNAL_ECCODES_BINDINGS=1`.


0.9.8.4 (2020-08-03)
--------------------

- Use `ecmwflibs` if present to find the *ecCodes* installation.


0.9.8.3 (2020-06-25)
--------------------

- Added support for ``indexingDate``, ``indexingTime`` time coordinates.
- ``lambert_azimuthal_equal_area`` grids are now returned as 2D arrays.
  See: `#119 <https://github.com/ecmwf/cfgrib/issues/119>`_.


0.9.8.2 (2020-05-22)
--------------------

- Add support for MULTI-FIELD messages used in some GRIB products to store
  ``u`` and ``v`` components of wind (e.g. GFS, NAM, etc). This has been the single
  most reported bug in *cfgrib* with two failed attempts at fixing it already.
  Let's see if the third time's a charm. Please test!
  See: `#45 <https://github.com/ecmwf/cfgrib/issues/45>`_,
  `#76 <https://github.com/ecmwf/cfgrib/issues/76>`_ and
  `#111 <https://github.com/ecmwf/cfgrib/issues/111>`_.


0.9.8.1 (2020-03-13)
--------------------

- Always open GRIB files in binary mode, by @b8raoult


0.9.8.0 (2020-03-12)
--------------------

- Add support of experimental pyeccodes low-level driver by @b8raoult


0.9.7.7 (2020-01-24)
--------------------

- Add support for `forecastMonth` in `cf2cdm.translate_coords`.


0.9.7.6 (2019-12-05)
--------------------

- Fix the README.


0.9.7.5 (2019-12-05)
--------------------

- Deprecate ``ensure_valid_time`` and the config option ``preferred_time_dimension`` that
  are now better handled via ``time_dims``.


0.9.7.4 (2019-11-22)
--------------------

- Add more options to ``time_dims`` forecasts products may be represented as
  ``('time', 'verifying_time')`` or ``('time', 'forecastMonth')``.
  See: `#97 <https://github.com/ecmwf/cfgrib/issues/97>`_.


0.9.7.3 (2019-11-04)
--------------------

- Add support for selecting the time coordinates to use as dimensions via ``time_dims``.
  Forecasts products may be represented as ``('time', 'step')`` (the default),
  ``('time', 'valid_time')`` or ``('valid_time', 'step')``.
  See: `#97 <https://github.com/ecmwf/cfgrib/issues/97>`_.
- Reduce the in-memory footprint of the ``FieldIndex`` and the size of ``.idx`` files.


0.9.7.2 (2019-09-24)
--------------------

- Add support to read additional keys from the GRIB files via ``read_keys``, they
  appear in the variable ``attrs`` and you can ``filter_by_keys`` on them.
  This is a general solution for all issues where users know the name of the additional keys
  they are interested in.
  See: `#89 <https://github.com/ecmwf/cfgrib/issues/89>`_ and
  `#101 <https://github.com/ecmwf/cfgrib/issues/101>`_.


0.9.7.1 (2019-07-08)
--------------------

- Fix a bytes-in-the-place-of-str bug when attempting to write a GRIB on Windows.
  See: `#91 <https://github.com/ecmwf/cfgrib/issues/91>`_.
- Honor setting ``indexpath`` in ``open_datasets``,
  See: `#93 <https://github.com/ecmwf/cfgrib/issues/93>`_.


0.9.7 (2019-05-27)
------------------

- Much improved ``cfgrib.open_datasets`` heuristics now reads many more
  heterogeneous GRIB files. The function is now a supported API.
  See: `#63 <https://github.com/ecmwf/cfgrib/issues/63>`_,
  `#66 <https://github.com/ecmwf/cfgrib/issues/66>`_,
  `#73 <https://github.com/ecmwf/cfgrib/issues/73>`_ and
  `#75 <https://github.com/ecmwf/cfgrib/issues/75>`_.
- Fix conda dependencies on Python 2 only package,
  See: `#78 <https://github.com/ecmwf/cfgrib/issues/78>`_.


0.9.7rc1 (2019-05-14)
---------------------

- Drop support for Python 2, in line with *xarray* 0.12.0.
  The 0.9.6.x series will be supported long term for Python 2 users.
  See: `#69 <https://github.com/ecmwf/cfgrib/issues/69>`_.
- Sync internal ecCodes bindings API to the one in eccodes-python.
  See: `#81 <https://github.com/ecmwf/cfgrib/issues/81>`_.
- Source code has been formatted with ``black -S -l 99``.
- Added initial support for spectral coordinates.


0.9.6.2 (2019-04-15)
--------------------

- Improve merging of variables into a dataset.
  See: `#63 <https://github.com/ecmwf/cfgrib/issues/63>`_.


0.9.6.1.post1 (2019-03-17)
--------------------------

- Fix an issue in the README format.


0.9.6.1 (2019-03-17)
--------------------

- Fixed (for real) MULTI-FIELD messages,
  See: `#45 <https://github.com/ecmwf/cfgrib/issues/45>`_.
- Added a protocol version to the index file. Old ``*.idx`` files must be removed.


0.9.6.post1 (2019-03-07)
------------------------

- Fix an important typo in the README. See: `#64 <https://github.com/ecmwf/cfgrib/issues/64>`_.


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
