#
# Copyright 2017-2018 European Centre for Medium-Range Weather Forecasts (ECMWF).
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

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import typing as T  # noqa
import warnings

import xarray as xr


LOGGER = logging.getLogger(__name__)


def open_dataset(path, backend_kwargs={}, filter_by_keys={}, **kwargs):
    # type: (str, T.Mapping[str, T.Any], dict, T.Any) -> xr.Dataset
    """
    Return a ``xr.Dataset`` with the requested ``flavor`` from a GRIB file.
    """
    # validate Dataset keys, DataArray names, and attr keys/values
    from . import cfgrib_
    if filter_by_keys:
        warnings.warn("passing filter_by_keys is depreciated use backend_kwargs", FutureWarning)
    real_backend_kwargs = {
        'flavour_name': 'ecmwf',
        'filter_by_keys': filter_by_keys,
        'errors': 'ignore',
    }
    real_backend_kwargs.update(backend_kwargs)
    store = cfgrib_.CfGribDataStore(path, **real_backend_kwargs)
    return xr.backends.api.open_dataset(store, **kwargs)


def open_datasets(path, backend_kwargs={}, no_warn=False, **kwargs):
    # type: (str, T.Dict[str, T.Any], bool, T.Any) -> T.List[xr.Dataset]
    """
    Open a GRIB file groupping incompatible hypercubes to different datasets via simple heuristics.
    """
    import cfgrib

    if not no_warn:
        warnings.warn("open_datasets is an experimental API, DO NOT RELY ON IT!", FutureWarning)

    fbks = []
    datasets = []
    try:
        datasets.append(open_dataset(path, backend_kwargs=backend_kwargs, **kwargs))
    except cfgrib.DatasetBuildError as ex:
        fbks.extend(ex.args[1])
    # NOTE: the recursive call needs to stay out of the exception handler to avoid showing
    #   to the user a confusing error message due to exception chaining
    # OPTIMIZE: we need a way to cache the index
    for fbk in fbks:
        bks = backend_kwargs.copy()
        bks['filter_by_keys'] = fbk
        datasets.extend(open_datasets(path, backend_kwargs=bks, no_warn=True, **kwargs))
    return datasets
