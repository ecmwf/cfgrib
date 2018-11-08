
Changelog for cfgrib
====================

0.9.4 (2018-11-08)
------------------

- Saves one index file per set of ``index_keys`` in a much more robust way.
- Refactor CF-encoding and add the new ``encode_cf`` option to ``backend_kwargs``.
  See: `#23 <https://github.com/ecmwf/cfgrib/issues/23>`_.
- Refactor error handling and the option to ignore errors (not well documented yet).
  See: `#13 <https://github.com/ecmwf/cfgrib/issues/13>`_.
- Do not crash on ``gridType`` not fully supported by the installed *ecCodes*
  See: `#27 https://github.com/ecmwf/cfgrib/issues/27`_.
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
