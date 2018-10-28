
Changelog for cfgrib
====================

0.9.3 (2018-10-28)
------------------

- Big performance improvement: add support to save to and read from disk
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
