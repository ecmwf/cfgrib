import os
import pathlib
import typing as T

import numpy as np
import xarray as xr
from packaging.version import Version

if Version(xr.__version__) <= Version("0.17.0"):
    raise ImportError("xarray_plugin module needs xarray version >= 0.18+")

from xarray.backends.common import AbstractDataStore, BackendArray, BackendEntrypoint

from . import abc, dataset, messages

# FIXME: Add a dedicated lock, even if ecCodes is supposed to be thread-safe
#   in most circumstances. See:
#       https://confluence.ecmwf.int/display/ECC/Frequently+Asked+Questions
ECCODES_LOCK = xr.backends.locks.SerializableLock()  # type: ignore


class CfGribDataStore(AbstractDataStore):
    """
    Implements the ``xr.AbstractDataStore`` read-only API for a GRIB file.
    """

    def __init__(
        self,
        filename: T.Union[str, abc.Fieldset[abc.Field], abc.MappingFieldset[T.Any, abc.Field]],
        lock: T.Union[T.ContextManager[T.Any], None] = None,
        **backend_kwargs: T.Any,
    ):
        if lock is None:
            lock = ECCODES_LOCK
        self.lock = xr.backends.locks.ensure_lock(lock)  # type: ignore
        if isinstance(filename, (str, pathlib.PurePath)):
            opener = dataset.open_file
        else:
            opener = dataset.open_fieldset
        self.ds = opener(filename, **backend_kwargs)

    def open_store_variable(
        self,
        var: dataset.Variable,
    ) -> xr.Variable:
        if isinstance(var.data, np.ndarray):
            data = var.data
        else:
            wrapped_array = CfGribArrayWrapper(self, var.data)
            data = xr.core.indexing.LazilyIndexedArray(wrapped_array)  # type: ignore
        encoding = self.ds.encoding.copy()
        encoding["original_shape"] = var.data.shape

        return xr.Variable(var.dimensions, data, var.attributes, encoding)  # type: ignore

    def get_variables(self) -> xr.core.utils.Frozen[T.Any, T.Any]:
        return xr.core.utils.FrozenDict(
            (k, self.open_store_variable(v)) for k, v in self.ds.variables.items()
        )

    def get_attrs(self) -> xr.core.utils.Frozen[T.Any, T.Any]:
        return xr.core.utils.Frozen(self.ds.attributes)

    def get_dimensions(self) -> xr.core.utils.Frozen[T.Any, T.Any]:
        return xr.core.utils.Frozen(self.ds.dimensions)

    def get_encoding(self) -> T.Dict[str, T.Set[str]]:
        dims = self.get_dimensions()
        encoding = {"unlimited_dims": {k for k, v in dims.items() if v is None}}
        return encoding


class CfGribBackend(BackendEntrypoint):
    description = "Open GRIB files (.grib, .grib2, .grb and .grb2) in Xarray"
    url = "https://github.com/ecmwf/cfgrib"

    def guess_can_open(
        self,
        store_spec: str,
    ) -> bool:
        try:
            _, ext = os.path.splitext(store_spec)
        except TypeError:
            return False
        return ext in {".grib", ".grib2", ".grb", ".grb2"}

    def open_dataset(
        self,
        filename_or_obj: T.Union[str, abc.MappingFieldset[T.Any, abc.Field]],
        *,
        mask_and_scale: bool = True,
        decode_times: bool = True,
        concat_characters: bool = True,
        decode_coords: bool = True,
        drop_variables: T.Union[T.Iterable[str], None] = None,
        use_cftime: T.Union[bool, None] = None,
        decode_timedelta: T.Union[bool, None] = None,
        lock: T.Union[T.ContextManager[T.Any], None] = None,
        indexpath: str = messages.DEFAULT_INDEXPATH,
        filter_by_keys: T.Dict[str, T.Any] = {},
        read_keys: T.Iterable[str] = (),
        encode_cf: T.Sequence[str] = ("parameter", "time", "geography", "vertical"),
        squeeze: bool = True,
        time_dims: T.Iterable[str] = ("time", "step"),
        errors: str = "warn",
        extra_coords: T.Dict[str, str] = {},
    ) -> xr.Dataset:
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
            extra_coords=extra_coords,
        )
        with xr.core.utils.close_on_error(store):
            vars, attrs = store.load()  # type: ignore
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
            )  # type: ignore

            ds = xr.Dataset(vars, attrs=attrs)
            ds = ds.set_coords(coord_names.intersection(vars))
            ds.set_close(store.close)
            ds.encoding = encoding
        return ds


class CfGribArrayWrapper(BackendArray):
    def __init__(
        self, datastore: CfGribDataStore, array: T.Union[dataset.OnDiskArray, np.ndarray]
    ):
        self.datastore = datastore
        self.shape = array.shape
        self.dtype = array.dtype
        self.array = array

    def __getitem__(
        self,
        key: xr.core.indexing.ExplicitIndexer,
    ) -> np.ndarray:
        return xr.core.indexing.explicit_indexing_adapter(
            key, self.shape, xr.core.indexing.IndexingSupport.BASIC, self._getitem
        )

    def _getitem(
        self,
        key: T.Tuple[T.Any, ...],
    ) -> np.ndarray:
        with self.datastore.lock:
            return self.array[key]
