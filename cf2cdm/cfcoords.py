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
#

import functools
import logging
import typing as T

import xarray as xr

from . import cfunits

CoordModelType = T.Dict[str, T.Dict[str, str]]
CoordTranslatorType = T.Callable[[str, xr.Dataset, CoordModelType], xr.Dataset]

COORD_MODEL: CoordModelType = {}
COORD_TRANSLATORS: T.Dict[str, CoordTranslatorType] = {}
LOG = logging.getLogger(__name__)


def match_values(match_value_func, mapping):
    # type: (T.Callable[[T.Any], bool], T.Mapping[T.Hashable, T.Any]) -> T.List[str]
    matched_names = []
    for name, value in mapping.items():
        if match_value_func(value):
            matched_names.append(str(name))
    return matched_names


def translate_coord_direction(data, coord_name, stored_direction="increasing"):
    # type: (xr.Dataset, str, str) -> xr.Dataset
    if stored_direction not in ("increasing", "decreasing"):
        raise ValueError("unknown stored_direction %r" % stored_direction)
    if len(data.coords[coord_name].shape) == 0:
        return data
    values = data.coords[coord_name].values
    if values[0] < values[-1] and stored_direction == "decreasing":
        data = data.isel({coord_name: slice(None, None, -1)})
    elif values[0] > values[-1] and stored_direction == "increasing":
        data = data.isel({coord_name: slice(None, None, -1)})
    return data


def coord_translator(
    default_out_name: str,
    default_units: str,
    default_direction: str,
    is_cf_type: T.Callable[[xr.IndexVariable], bool],
    cf_type: str,
    data: xr.Dataset,
    coord_model: CoordModelType = COORD_MODEL,
) -> xr.Dataset:
    out_name = coord_model.get(cf_type, {}).get("out_name", default_out_name)
    units = coord_model.get(cf_type, {}).get("units", default_units)
    stored_direction = coord_model.get(cf_type, {}).get("stored_direction", default_direction)
    matches = match_values(is_cf_type, data.coords)
    if len(matches) > 1:
        raise ValueError("found more than one CF coordinate with type %r." % cf_type)
    if not matches:
        return data
    match = matches[0]
    for name in data.coords:
        if name == out_name and name != match:
            raise ValueError("found non CF compliant coordinate with type %r." % cf_type)
    data = data.rename({match: out_name})
    coord = data.coords[out_name]
    if "units" in coord.attrs:
        data.coords[out_name] = cfunits.convert_units(coord, units, coord.attrs["units"])
        data.coords[out_name].attrs.update(coord.attrs)
        data.coords[out_name].attrs["units"] = units
    if out_name in data.dims:
        data = translate_coord_direction(data, out_name, stored_direction)
    return data


VALID_LAT_UNITS = ["degrees_north", "degree_north", "degree_N", "degrees_N", "degreeN", "degreesN"]


def is_latitude(coord: xr.IndexVariable) -> bool:
    return coord.attrs.get("units") in VALID_LAT_UNITS


COORD_TRANSLATORS["latitude"] = functools.partial(
    coord_translator, "latitude", "degrees_north", "decreasing", is_latitude
)


VALID_LON_UNITS = ["degrees_east", "degree_east", "degree_E", "degrees_E", "degreeE", "degreesE"]


def is_longitude(coord: xr.IndexVariable) -> bool:
    return coord.attrs.get("units") in VALID_LON_UNITS


COORD_TRANSLATORS["longitude"] = functools.partial(
    coord_translator, "longitude", "degrees_east", "increasing", is_longitude
)


def is_time(coord: xr.IndexVariable) -> bool:
    return coord.attrs.get("standard_name") == "forecast_reference_time"


TIME_CF_UNITS = "seconds since 1970-01-01T00:00:00+00:00"


COORD_TRANSLATORS["time"] = functools.partial(
    coord_translator, "time", TIME_CF_UNITS, "increasing", is_time
)


def is_step(coord: xr.IndexVariable) -> bool:
    return coord.attrs.get("standard_name") == "forecast_period"


COORD_TRANSLATORS["step"] = functools.partial(coord_translator, "step", "h", "increasing", is_step)


def is_valid_time(coord: xr.IndexVariable) -> bool:
    if coord.attrs.get("standard_name") == "time":
        return True
    elif str(coord.dtype) == "datetime64[ns]" and "standard_name" not in coord.attrs:
        return True
    return False


COORD_TRANSLATORS["valid_time"] = functools.partial(
    coord_translator, "valid_time", TIME_CF_UNITS, "increasing", is_valid_time
)


def is_depth(coord: xr.IndexVariable) -> bool:
    return coord.attrs.get("standard_name") == "depth"


COORD_TRANSLATORS["depthBelowLand"] = functools.partial(
    coord_translator, "depthBelowLand", "m", "decreasing", is_depth
)


def is_isobaric(coord: xr.IndexVariable) -> bool:
    return cfunits.are_convertible(coord.attrs.get("units", ""), "Pa")


COORD_TRANSLATORS["isobaricInhPa"] = functools.partial(
    coord_translator, "isobaricInhPa", "hPa", "decreasing", is_isobaric
)


def is_number(coord: xr.IndexVariable) -> bool:
    return coord.attrs.get("standard_name") == "realization"


COORD_TRANSLATORS["number"] = functools.partial(
    coord_translator, "number", "1", "increasing", is_number
)


# CF-Conventions have no concept of leadtime expressed in months
def is_forecast_month(coord: xr.IndexVariable) -> bool:
    return coord.attrs.get("long_name") == "months since forecast_reference_time"


COORD_TRANSLATORS["forecastMonth"] = functools.partial(
    coord_translator, "forecastMonth", "1", "increasing", is_forecast_month
)


def translate_coords(
    data, coord_model=COORD_MODEL, errors="warn", coord_translators=COORD_TRANSLATORS
):
    # type: (xr.Dataset, CoordModelType, str, T.Dict[str, CoordTranslatorType]) -> xr.Dataset
    for cf_name, translator in coord_translators.items():
        try:
            data = translator(cf_name, data, coord_model)
        except:
            if errors == "ignore":
                pass
            elif errors == "raise":
                raise RuntimeError("error while translating coordinate: %r" % cf_name)
            else:
                LOG.warning("error while translating coordinate: %r", cf_name)
    return data
