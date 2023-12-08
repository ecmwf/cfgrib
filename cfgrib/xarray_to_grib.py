#
# Copyright 2017-2021 European Centre for Medium-Range Weather Forecasts (ECMWF).
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

import itertools
import logging
import typing as T
import warnings

import numpy as np
import xarray as xr

from . import cfmessage, dataset, messages

LOGGER = logging.getLogger(__name__)


DEFAULT_GRIB_KEYS = {
    "centre": 255,  # missing value, see: http://apps.ecmwf.int/codes/grib/format/grib1/centre/0/
    "typeOfLevel": "surface",
}
TYPE_OF_LEVELS_SFC = ["surface", "meanSea", "cloudBase", "cloudTop"]
TYPE_OF_LEVELS_PL = ["isobaricInhPa", "isobaricInPa"]
TYPE_OF_LEVELS_ML = ["hybrid"]
ALL_TYPE_OF_LEVELS = TYPE_OF_LEVELS_SFC + TYPE_OF_LEVELS_PL + TYPE_OF_LEVELS_ML
GRID_TYPES = [
    "polar_stereographic",
    "reduced_gg",
    "reduced_ll",
    "regular_gg",
    "regular_ll",
    "rotated_gg",
    "rotated_ll",
    "sh",
]


def regular_ll_params(values, min_value=-180.0, max_value=360.0):
    # type: (np.ndarray, float, float) -> T.Tuple[float, float, int]
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
    lon_step = abs(lon_stop - lon_start) / (lon_num - 1.0)
    if lon_start < 0.0:
        lon_start += 360.0
    if lon_stop < 0.0:
        lon_stop += 360.0
    grib_keys["longitudeOfFirstGridPointInDegrees"] = lon_start
    grib_keys["longitudeOfLastGridPointInDegrees"] = lon_stop
    grib_keys["Ni"] = lon_num
    grib_keys["iDirectionIncrementInDegrees"] = lon_step
    grib_keys["iScansNegatively"] = lon_scan_negatively

    lat_start, lat_stop, lat_num = regular_ll_params(lat, min_value=-90.0, max_value=90.0)
    grib_keys["latitudeOfFirstGridPointInDegrees"] = lat_start
    grib_keys["latitudeOfLastGridPointInDegrees"] = lat_stop
    grib_keys["Nj"] = lat_num
    grib_keys["jDirectionIncrementInDegrees"] = abs(lat_stop - lat_start) / (lat_num - 1.0)
    grib_keys["jScansPositively"] = lat_stop > lat_start
    grib_keys["gridType"] = "regular_ll"

    return grib_keys


def detect_grib_keys(data_var, default_grib_keys, grib_keys={}):
    # type: (xr.DataArray, T.Dict[str, T.Any], T.Dict[str, T.Any]) -> T.Tuple[T.Dict[str, T.Any], T.Dict[str, T.Any]]
    detected_grib_keys = {}
    suggested_grib_keys = default_grib_keys.copy()

    for key_raw, value in data_var.attrs.items():
        key = str(key_raw)
        if key[:5] == "GRIB_":
            suggested_grib_keys[key[5:]] = value

    if "latitude" in data_var.dims and "longitude" in data_var.dims:
        try:
            regular_ll_keys = detect_regular_ll_grib_keys(data_var.longitude, data_var.latitude)
            detected_grib_keys.update(regular_ll_keys)
        except:
            pass

    for tol in ALL_TYPE_OF_LEVELS:
        if tol in data_var.dims or tol in data_var.coords:
            detected_grib_keys["typeOfLevel"] = tol

    if "number" in data_var.dims or "number" in data_var.coords and grib_keys.get("edition") != 1:
        # cannot set 'number' key without setting a productDefinitionTemplateNumber in GRIB2
        detected_grib_keys["productDefinitionTemplateNumber"] = 1

    if "values" in data_var.dims:
        detected_grib_keys["numberOfPoints"] = data_var.shape[data_var.dims.index("values")]

    return detected_grib_keys, suggested_grib_keys


def detect_sample_name(grib_keys, sample_name_template="{geography}_{vertical}_grib{edition}"):
    # type: (T.Mapping[str, T.Any], str) -> str
    edition = grib_keys.get("edition", 2)

    if grib_keys["gridType"] in GRID_TYPES:
        geography = grib_keys["gridType"]
    else:
        LOGGER.warning("unknown 'gridType': %r. Using GRIB2 template", grib_keys["gridType"])
        return "GRIB2"

    if grib_keys["typeOfLevel"] in TYPE_OF_LEVELS_PL:
        vertical = "pl"
    elif grib_keys["typeOfLevel"] in TYPE_OF_LEVELS_SFC:
        vertical = "sfc"
    elif grib_keys["typeOfLevel"] in TYPE_OF_LEVELS_ML:
        vertical = "ml"
    else:
        LOGGER.warning("unknown 'typeOfLevel': %r. Using GRIB2 template", grib_keys["typeOfLevel"])
        return "GRIB2"

    sample_name = sample_name_template.format(**locals())
    return sample_name


def merge_grib_keys(grib_keys, detected_grib_keys, default_grib_keys):
    # type: (T.Dict[str, T.Any], T.Dict[str, T.Any], T.Dict[str, T.Any]) -> T.Dict[str, T.Any]
    merged_grib_keys = {k: v for k, v in grib_keys.items()}
    dataset.dict_merge(merged_grib_keys, detected_grib_keys)
    for key, value in default_grib_keys.items():
        if key not in merged_grib_keys:
            merged_grib_keys[key] = value
    return merged_grib_keys


def expand_dims(data_var: xr.DataArray) -> T.Tuple[T.List[str], xr.DataArray]:
    coords_names = []  # type: T.List[str]
    for coord_name in dataset.ALL_HEADER_DIMS + ALL_TYPE_OF_LEVELS + dataset.ALL_REF_TIME_KEYS:
        if (
            coord_name in data_var.coords
            and data_var.coords[coord_name].size == 1
            and coord_name not in data_var.dims
        ):
            data_var = data_var.expand_dims(coord_name)
        if coord_name in data_var.dims:
            coords_names.append(coord_name)
    return coords_names, data_var


def make_template_message(merged_grib_keys, template_path=None, sample_name=None):
    # type: (T.Dict[str, T.Any], T.Optional[str], T.Optional[str]) -> messages.Message
    if template_path and sample_name:
        raise ValueError("template_path and sample_name should not be both set")

    if template_path:
        with open(template_path, "rb") as file:
            template_message = cfmessage.CfMessage.from_file(file)
    else:
        if sample_name is None:
            sample_name = detect_sample_name(merged_grib_keys)
        template_message = cfmessage.CfMessage.from_sample_name(sample_name)

    for key, value in merged_grib_keys.items():
        try:
            template_message[key] = value
        except KeyError:
            LOGGER.exception("skipping key due to errors: %r" % key)

    return template_message


def canonical_dataarray_to_grib(
    data_var, file, grib_keys={}, default_grib_keys=DEFAULT_GRIB_KEYS, **kwargs
):
    # type: (xr.DataArray, T.IO[bytes], T.Dict[str, T.Any], T.Dict[str, T.Any], T.Any) -> None
    """
    Write a ``xr.DataArray`` in *canonical* form to a GRIB file.
    """
    # validate Dataset keys, DataArray names, and attr keys/values
    detected_keys, suggested_keys = detect_grib_keys(data_var, default_grib_keys, grib_keys)
    merged_grib_keys = merge_grib_keys(grib_keys, detected_keys, suggested_keys)
    merged_grib_keys["missingValue"] = messages.MISSING_VAUE_INDICATOR

    if "gridType" not in merged_grib_keys:
        raise ValueError("required grib_key 'gridType' not passed nor auto-detected")

    template_message = make_template_message(merged_grib_keys, **kwargs)

    coords_names, data_var = expand_dims(data_var)

    header_coords_values = [list(data_var.coords[name].values) for name in coords_names]

    for items in itertools.product(*header_coords_values):
        select = {n: v for n, v in zip(coords_names, items)}
        field_values = data_var.sel(**select).values.flat[:]

        # Missing values handling
        invalid_field_values = np.logical_not(np.isfinite(field_values))

        # There's no need to save a message full of missing values
        if invalid_field_values.all():
            continue

        missing_value = merged_grib_keys.get("GRIB_missingValue", messages.MISSING_VAUE_INDICATOR)
        field_values[invalid_field_values] = missing_value

        message = cfmessage.CfMessage.from_message(template_message)
        for coord_name, coord_value in zip(coords_names, items):
            if coord_name in ALL_TYPE_OF_LEVELS:
                coord_name = "level"
            message[coord_name] = coord_value

        if invalid_field_values.any():
            message["bitmapPresent"] = 1
        message["missingValue"] = missing_value

        # OPTIMIZE: convert to list because Message.message_set doesn't support np.ndarray
        message["values"] = field_values.tolist()

        message.write(file)


def canonical_dataset_to_grib(dataset, path, mode="wb", no_warn=False, grib_keys={}, **kwargs):
    # type: (xr.Dataset, str, str, bool, T.Dict[str, T.Any], T.Any) -> None
    """
    Write a ``xr.Dataset`` in *canonical* form to a GRIB file.
    """
    if not no_warn:
        warnings.warn("GRIB write support is experimental, DO NOT RELY ON IT!", FutureWarning)

    # validate Dataset keys, DataArray names, and attr keys/values
    xr.backends.api._validate_dataset_names(dataset)  # type: ignore
    xr.backends.api._validate_attrs(dataset)  # type: ignore

    real_grib_keys = {str(k)[5:]: v for k, v in dataset.attrs.items() if str(k)[:5] == "GRIB_"}
    real_grib_keys.update(grib_keys)

    with open(path, mode=mode) as file:
        for data_var in dataset.data_vars.values():
            canonical_dataarray_to_grib(data_var, file, grib_keys=real_grib_keys, **kwargs)


to_grib = canonical_dataset_to_grib
