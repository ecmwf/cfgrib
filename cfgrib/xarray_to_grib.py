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
#   Aureliana Barghini - B-Open - https://bopen.eu
#   Leonardo Barcaroli - B-Open - https://bopen.eu
#

from __future__ import absolute_import, division, print_function, unicode_literals

import itertools
import logging
import typing as T  # noqa
import warnings

import numpy as np
import xarray as xr

import cfgrib
from cfgrib import dataset  # FIXME: write support needs internal functions

LOGGER = logging.getLogger(__name__)


DEFAULT_GRIB_KEYS = {
    'centre': 255,  # missing value, see: http://apps.ecmwf.int/codes/grib/format/grib1/centre/0/
    'typeOfLevel': 'surface',
}


def regular_ll_params(values, min_value=-180., max_value=360.):
    # type: (T.Sequence, float, float) -> T.Tuple[float, float, int]
    start, stop, num = float(values[0]), float(values[-1]), len(values)
    if min(start, stop) < min_value or max(start, stop) > max_value:
        raise ValueError("Unsupported spatial grid: out of bounds (%r, %r)" % (start, stop))
    check_values = np.linspace(start, stop, num)
    if not np.allclose(check_values, values):
        raise ValueError("Unsupported spatial grid: not regular %r" % (check_values,))
    return (start, stop, num)


def detect_regular_ll_grib_keys(lon, lat):
    # type: (np.ndarray, np.ndarray) -> T.Dict[str, T.Any]
    grib_keys = {}  # type: T.Dict[str, T.Any]

    lon_start, lon_stop, lon_num = regular_ll_params(lon)
    lon_scan_negatively = lon_stop < lon_start
    lon_step = abs(lon_stop - lon_start) / (lon_num - 1.)
    if lon_start < 0.:
        lon_start += 360.
    if lon_stop < 0.:
        lon_stop += 360.
    grib_keys['longitudeOfFirstGridPointInDegrees'] = lon_start
    grib_keys['longitudeOfLastGridPointInDegrees'] = lon_stop
    grib_keys['Ni'] = lon_num
    grib_keys['iDirectionIncrementInDegrees'] = lon_step
    grib_keys['iScansNegatively'] = lon_scan_negatively

    lat_start, lat_stop, lat_num = regular_ll_params(lat, min_value=-90., max_value=90.)
    grib_keys['latitudeOfFirstGridPointInDegrees'] = lat_start
    grib_keys['latitudeOfLastGridPointInDegrees'] = lat_stop
    grib_keys['Nj'] = lat_num
    grib_keys['jDirectionIncrementInDegrees'] = abs(lat_stop - lat_start) / (lat_num - 1.)
    grib_keys['jScansPositively'] = lat_stop > lat_start
    grib_keys['gridType'] = 'regular_ll'

    return grib_keys


def detect_grib_keys(data_var, default_grib_keys):
    # type: (xr.DataArray, T.Dict[str, T.Any]) -> T.Tuple[dict, dict]
    detected_grib_keys = {}
    suggested_grib_keys = default_grib_keys.copy()

    for key in ['shortName', 'gridType', 'typeOfLevel', 'totalNumber']:
        if 'GRIB_' + key in data_var.attrs:
            suggested_grib_keys[key] = data_var.attrs['GRIB_' + key]

    if 'latitude' in data_var.dims and 'longitude' in data_var.dims:
        regular_ll_grib_keys = detect_regular_ll_grib_keys(data_var.longitude, data_var.latitude)
        detected_grib_keys.update(regular_ll_grib_keys)

    if 'air_pressure' in data_var.dims or 'air_pressure' in data_var.coords:
        detected_grib_keys['typeOfLevel'] = 'isobaricInhPa'

    if 'number' in data_var.dims or 'number' in data_var.coords:
        # cannot set 'number' key without setting a productDefinitionTemplateNumber in GRIB2
        detected_grib_keys['productDefinitionTemplateNumber'] = 1

    return detected_grib_keys, suggested_grib_keys


def detect_sample_name(grib_keys, sample_name_template='{geography}_{vertical}_grib2'):
    # type: (T.Mapping, str) -> str
    if grib_keys['gridType'] == 'regular_ll':
        geography = 'regular_ll'
    else:
        raise NotImplementedError("Unsupported 'gridType': %r" % grib_keys['gridType'])

    if grib_keys['typeOfLevel'] == 'isobaricInhPa':
        vertical = 'pl'
    elif grib_keys['typeOfLevel'] in ('surface', 'meanSea'):
        vertical = 'sfc'
    else:
        raise NotImplementedError("Unsupported 'typeOfLevel': %r" % grib_keys['typeOfLevel'])

    sample_name = sample_name_template.format(**locals())
    return sample_name


def merge_grib_keys(grib_keys, detected_grib_keys, default_grib_keys):
    merged_grib_keys = {k: v for k, v in grib_keys.items()}
    dataset.dict_merge(merged_grib_keys, detected_grib_keys)
    for key, value in default_grib_keys.items():
        if key not in merged_grib_keys:
            merged_grib_keys[key] = value
    return merged_grib_keys


def expand_dims(data_var):
    header_coords_names = []
    for coord_name in dataset.ALL_HEADER_DIMS:
        if coord_name in set(data_var.coords):
            header_coords_names.append(coord_name)
            if coord_name not in data_var.dims:
                data_var = data_var.expand_dims(coord_name)
    return header_coords_names, data_var


def canonical_dataarray_to_grib(
        file, data_var, grib_keys={}, default_grib_keys=DEFAULT_GRIB_KEYS,
        sample_name_template='{geography}_{vertical}_grib2'
):
    # type: (T.IO[bytes], xr.DataArray, T.Mapping[str, T.Any], T.Dict[str, T.Any], str) -> None
    """
    Write a ``xr.DataArray`` in *canonical* form to a GRIB file.
    """
    # validate Dataset keys, DataArray names, and attr keys/values
    detected_grib_keys, suggested_grib_keys = detect_grib_keys(data_var, default_grib_keys)
    merged_grib_keys = merge_grib_keys(grib_keys, detected_grib_keys, suggested_grib_keys)

    if 'gridType' not in merged_grib_keys:
        raise ValueError("required grib_key 'gridType' not passed nor auto-detected")

    sample_name = detect_sample_name(merged_grib_keys, sample_name_template=sample_name_template)

    header_coords_names, data_var = expand_dims(data_var)

    header_coords_values = [data_var.coords[name].values.tolist() for name in header_coords_names]
    for items in itertools.product(*header_coords_values):
        select = {n: v for n, v in zip(header_coords_names, items)}
        field_values = data_var.sel(**select).values.flat[:]

        # Missing values handling
        invalid_field_values = np.logical_not(np.isfinite(field_values))

        # There's no need to save a message full of missing values
        if invalid_field_values.all():
            continue

        missing_value = merged_grib_keys.get('missingValue', 9999)
        field_values[invalid_field_values] = missing_value

        message = cfgrib.CfMessage.from_sample_name(sample_name)
        for key, value in merged_grib_keys.items():
            try:
                message[key] = value
            except KeyError:
                LOGGER.exception("skipping key due to errors: %r" % key)

        for coord_name, coord_value in zip(header_coords_names, items):
            message[coord_name] = coord_value

        # OPTIMIZE: convert to list because Message.message_set doesn't support np.ndarray
        message['values'] = field_values.tolist()

        message.write(file)


def canonical_dataset_to_grib(dataset, path, mode='wb', no_warn=False, **kwargs):
    # type: (xr.Dataset, str, str, bool, T.Any) -> None
    """
    Write a ``xr.Dataset`` in *canonical* form to a GRIB file.
    """
    if not no_warn:
        warnings.warn("GRIB write support is experimental, DO NOT RELY ON IT!", FutureWarning)

    # validate Dataset keys, DataArray names, and attr keys/values
    xr.backends.api._validate_dataset_names(dataset)
    xr.backends.api._validate_attrs(dataset)

    with open(path, mode=mode) as file:
        for data_var in dataset.data_vars.values():
            canonical_dataarray_to_grib(file, data_var, **kwargs)


def to_grib(*args, **kwargs):
    return canonical_dataset_to_grib(*args, **kwargs)
