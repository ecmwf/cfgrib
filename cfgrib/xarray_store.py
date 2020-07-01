#
# Copyright 2017-2020 European Centre for Medium-Range Weather Forecasts (ECMWF).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Authors:
#   Alessandro Amici - B-Open - https://bopen.eu
#

import logging
import typing as T  # noqa
import warnings

import xarray as xr

from . import DatasetBuildError, open_fileindex

LOGGER = logging.getLogger(__name__)


def open_dataset(path, **kwargs):
    # type: (str, T.Any) -> xr.Dataset
    """
    Return a ``xr.Dataset`` with the requested ``backend_kwargs`` from a GRIB file.
    """
    if 'engine' in kwargs and kwargs['engine'] != 'cfgrib':
        raise ValueError("only engine=='cfgrib' is supported")
    kwargs['engine'] = 'cfgrib'
    return xr.backends.api.open_dataset(path, **kwargs)


def merge_datasets(datasets, **kwargs):
    merged = []
    for ds in datasets:
        ds.attrs.pop('history', None)
        for i, o in enumerate(merged):
            if all(o.attrs[k] == ds.attrs[k] for k in o.attrs):
                try:
                    o = xr.merge([o, ds], **kwargs)
                    o.attrs.update(ds.attrs)
                    merged[i] = o
                    break
                except Exception:
                    pass
        else:
            merged.append(ds)
    return merged


def raw_open_datasets(path, backend_kwargs={}, **kwargs):
    # type: (str, T.Dict[str, T.Any], T.Any) -> T.List[xr.Dataset]
    fbks = []
    datasets = []
    try:
        datasets.append(open_dataset(path, backend_kwargs=backend_kwargs, **kwargs))
    except DatasetBuildError as ex:
        fbks.extend(ex.args[2])
    # NOTE: the recursive call needs to stay out of the exception handler to avoid showing
    #   to the user a confusing error message due to exception chaining
    for fbk in fbks:
        bks = backend_kwargs.copy()
        bks['filter_by_keys'] = fbk
        datasets.extend(raw_open_datasets(path, backend_kwargs=bks, **kwargs))
    return datasets


def open_variable_datasets(path, backend_kwargs={}, **kwargs):
    fileindex_kwargs = {
        key: backend_kwargs[key]
        for key in ['filter_by_keys', 'indexpath', 'grib_errors']
        if key in backend_kwargs
    }
    index = open_fileindex(path, **fileindex_kwargs)
    datasets = []
    for param_id in sorted(index['paramId']):
        bk = backend_kwargs.copy()
        bk['filter_by_keys'] = backend_kwargs.get('filter_by_keys', {}).copy()
        bk['filter_by_keys']['paramId'] = param_id
        datasets.extend(raw_open_datasets(path, bk, **kwargs))
    return datasets


def open_datasets(path, no_warn=False, backend_kwargs={}, **kwargs):
    """
    Open a GRIB file groupping incompatible hypercubes to different datasets via simple heuristics.
    """
    if no_warn:
        warnings.warn("open_datasets is now public, no_warn will be removed", FutureWarning)

    squeeze = backend_kwargs.get('squeeze', True)
    backend_kwargs = backend_kwargs.copy()
    backend_kwargs['squeeze'] = False
    datasets = open_variable_datasets(path, backend_kwargs=backend_kwargs, **kwargs)

    type_of_level_datasets = {}
    for ds in datasets:
        for _, da in ds.data_vars.items():
            type_of_level = da.attrs.get('GRIB_typeOfLevel', 'undef')
            type_of_level_datasets.setdefault(type_of_level, []).append(ds)

    merged = []
    for type_of_level in sorted(type_of_level_datasets):
        for ds in merge_datasets(type_of_level_datasets[type_of_level], join='exact'):
            merged.append(ds.squeeze() if squeeze else ds)
    return merged
