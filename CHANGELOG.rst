
Changelog for cfgrib
====================

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
