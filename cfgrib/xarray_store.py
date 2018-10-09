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

from xarray.backends import api


LOGGER = logging.getLogger(__name__)


def open_dataset(path, flavour_name='ecmwf', filter_by_keys={}, errors='ignore', **kwargs):
    # type: (str, str, T.Mapping[str, T.Any], str, T.Any) -> xr.Dataset
    """
    Return a ``xr.Dataset`` with the requested ``flavor`` from a GRIB file.
    """
    # validate Dataset keys, DataArray names, and attr keys/values
    from . import cfgrib_
    overrides = {
        'flavour_name': flavour_name,
        'filter_by_keys': filter_by_keys,
        'errors': errors,
    }
    for k in list(kwargs):  # copy to allow the .pop()
        if k.startswith('encode_'):
            overrides[k] = kwargs.pop(k)
    store = cfgrib_.CfGribDataStore.from_path(path, **overrides)
    return api.open_dataset(store, **kwargs)


def open_datasets(path, flavour_name='ecmwf', filter_by_keys={}, no_warn=False, **kwargs):
    # type: (str, str, T.Dict[str, T.Any], bool, T.Any) -> T.List[xr.Dataset]
    """
    Open a GRIB file groupping incompatible hypercubes to different datasets via simple heuristics.
    """
    import cfgrib

    if not no_warn:
        warnings.warn("open_datasets is an experimental API, DO NOT RELY ON IT!", FutureWarning)

    fbks = []
    datasets = []
    try:
        datasets.append(open_dataset(path, flavour_name, filter_by_keys, **kwargs))
    except cfgrib.DatasetBuildError as ex:
        fbks.extend(ex.args[1])
    # NOTE: the recursive call needs to stay out of the exception handler to avoid showing
    #   to the user a confusing error message due to exception chaining
    # OPTIMIZE: we need a way to cache the index
    for fbk in fbks:
        datasets.extend(open_datasets(path, flavour_name, fbk, no_warn=True, **kwargs))
    return datasets
