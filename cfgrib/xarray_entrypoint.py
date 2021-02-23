import os
from distutils.version import LooseVersion

import numpy as np
import xarray as xr

from . import dataset

if LooseVersion(xr.__version__) < "0.18":
    raise ImportError("xarray_entrypoints module needs xarray version >= 0.18")

from xarray.backends.common import (
    BACKEND_ENTRYPOINTS,
    AbstractDataStore,
    BackendArray,
    BackendEntrypoint,
)


# FIXME: Add a dedicated lock, even if ecCodes is supposed to be thread-safe
#   in most circumstances. See:
#       https://confluence.ecmwf.int/display/ECC/Frequently+Asked+Questions
ECCODES_LOCK = xr.backends.locks.SerializableLock()


class CfGribArrayWrapper(BackendArray):
    def __init__(self, datastore, array):
        self.datastore = datastore
        self.shape = array.shape
        self.dtype = array.dtype
        self.array = array

    def __getitem__(self, key):
        return xr.core.indexing.explicit_indexing_adapter(
            key, self.shape, xr.core.indexing.IndexingSupport.BASIC, self._getitem
        )

    def _getitem(self, key):
        with self.datastore.lock:
            return self.array[key]


class CfGribDataStore(AbstractDataStore):
    """
    Implements the ``xr.AbstractDataStore`` read-only API for a GRIB file.
    """

    def __init__(self, filename, lock=None, **backend_kwargs):

        if lock is None:
            lock = ECCODES_LOCK
        self.lock = xr.backends.locks.ensure_lock(lock)
        self.ds = dataset.open_file(filename, **backend_kwargs)

    def open_store_variable(self, name, var):
        if isinstance(var.data, np.ndarray):
            data = var.data
        else:
            wrapped_array = CfGribArrayWrapper(self, var.data)
            data = xr.core.indexing.LazilyOuterIndexedArray(wrapped_array)

        encoding = self.ds.encoding.copy()
        encoding["original_shape"] = var.data.shape

        return xr.core.variable.Variable(var.dimensions, data, var.attributes, encoding)

    def get_variables(self):
        return xr.core.utils.FrozenDict(
            (k, self.open_store_variable(k, v)) for k, v in self.ds.variables.items()
        )

    def get_attrs(self):
        return xr.core.utils.Frozen(self.ds.attributes)

    def get_dimensions(self):
        return xr.core.utils.Frozen(self.ds.dimensions)

    def get_encoding(self):
        dims = self.get_dimensions()
        encoding = {"unlimited_dims": {k for k, v in dims.items() if v is None}}
        return encoding


class CfgribfBackendEntrypoint(BackendEntrypoint):
    def guess_can_open(self, store_spec):
        try:
            _, ext = os.path.splitext(store_spec)
        except TypeError:
            return False
        return ext in {".grib", ".grib2", ".grb", ".grb2"}

    def open_dataset(
        self,
        filename_or_obj,
        *,
        mask_and_scale=True,
        decode_times=True,
        concat_characters=True,
        decode_coords=True,
        drop_variables=None,
        use_cftime=None,
        decode_timedelta=None,
        lock=None,
        indexpath="{path}.{short_hash}.idx",
        filter_by_keys={},
        read_keys=[],
        encode_cf=("parameter", "time", "geography", "vertical"),
        squeeze=True,
        time_dims=("time", "step"),
        errors: str = "warn"
    ):

        store = CfGribDataStore(
            filename_or_obj,
            indexpath=indexpath,
            filter_by_keys=filter_by_keys,
            read_keys=read_keys,
            encode_cf=encode_cf,
            squeeze=squeeze,
            time_dims=time_dims,
            lock=lock,
            errors=errors,
        )
        with xr.core.utils.close_on_error(store):
            vars, attrs = store.load()
            encoding = store.get_encoding()
            vars, attrs, coord_names = xr.conventions.decode_cf_variables(
                vars,
                attrs,
                mask_and_scale=mask_and_scale,
                decode_times=decode_times,
                concat_characters=concat_characters,
                decode_coords=decode_coords,
                drop_variables=drop_variables,
                use_cftime=use_cftime,
                decode_timedelta=decode_timedelta,
            )

            ds = xr.Dataset(vars, attrs=attrs)
            ds = ds.set_coords(coord_names.intersection(vars))
            ds.set_close(store.close)
            ds.encoding = encoding
        return ds