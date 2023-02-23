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
#

import datetime
import json
import logging
import os
import typing as T

import attr
import numpy as np

from . import __version__, abc, cfmessage, messages

LOG = logging.getLogger(__name__)

#
# Edition-independent keys in ecCodes namespaces. Documented in:
#   https://software.ecmwf.int/wiki/display/ECC/GRIB%3A+Namespaces
#
GLOBAL_ATTRIBUTES_KEYS = ["edition", "centre", "centreDescription", "subCentre"]

DATA_ATTRIBUTES_KEYS = [
    "paramId",
    "dataType",
    "numberOfPoints",
    "typeOfLevel",
    "stepUnits",
    "stepType",
    "gridType",
]

EXTRA_DATA_ATTRIBUTES_KEYS = [
    "shortName",
    "units",
    "name",
    "cfName",
    "cfVarName",
    "missingValue",
    "totalNumber",
    "numberOfDirections",
    "numberOfFrequencies",
    "NV",
    "gridDefinitionDescription",
]

GRID_TYPE_MAP = {
    "regular_ll": [
        "Nx",
        "iDirectionIncrementInDegrees",
        "iScansNegatively",
        "longitudeOfFirstGridPointInDegrees",
        "longitudeOfLastGridPointInDegrees",
        "Ny",
        "jDirectionIncrementInDegrees",
        "jPointsAreConsecutive",
        "jScansPositively",
        "latitudeOfFirstGridPointInDegrees",
        "latitudeOfLastGridPointInDegrees",
    ],
    "rotated_ll": [
        "Nx",
        "Ny",
        "angleOfRotationInDegrees",
        "iDirectionIncrementInDegrees",
        "iScansNegatively",
        "jDirectionIncrementInDegrees",
        "jPointsAreConsecutive",
        "jScansPositively",
        "latitudeOfFirstGridPointInDegrees",
        "latitudeOfLastGridPointInDegrees",
        "latitudeOfSouthernPoleInDegrees",
        "longitudeOfFirstGridPointInDegrees",
        "longitudeOfLastGridPointInDegrees",
        "longitudeOfSouthernPoleInDegrees",
    ],
    "reduced_ll": [
        "Ny",
        "jDirectionIncrementInDegrees",
        "jPointsAreConsecutive",
        "jScansPositively",
        "latitudeOfFirstGridPointInDegrees",
        "latitudeOfLastGridPointInDegrees",
    ],
    "regular_gg": [
        "N",
        "Ni",
        "Nj",
        "iDirectionIncrementInDegrees",
        "iScansNegatively",
        "jScansPositively",
        "jPointsAreConsecutive",
        "longitudeOfFirstGridPointInDegrees",
        "longitudeOfLastGridPointInDegrees",
        "latitudeOfFirstGridPointInDegrees",
        "latitudeOfLastGridPointInDegrees",
    ],
    "rotated_gg": [
        "Nx",
        "Ny",
        "angleOfRotationInDegrees",
        "iDirectionIncrementInDegrees",
        "iScansNegatively",
        "jPointsAreConsecutive",
        "jScansPositively",
        "latitudeOfFirstGridPointInDegrees",
        "latitudeOfLastGridPointInDegrees",
        "latitudeOfSouthernPoleInDegrees",
        "longitudeOfFirstGridPointInDegrees",
        "longitudeOfLastGridPointInDegrees",
        "longitudeOfSouthernPoleInDegrees",
        "N",
    ],
    "lambert": [
        "LaDInDegrees",
        "LoVInDegrees",
        "iScansNegatively",
        "jPointsAreConsecutive",
        "jScansPositively",
        "latitudeOfFirstGridPointInDegrees",
        "latitudeOfSouthernPoleInDegrees",
        "longitudeOfFirstGridPointInDegrees",
        "longitudeOfSouthernPoleInDegrees",
        "DyInMetres",
        "DxInMetres",
        "Latin2InDegrees",
        "Latin1InDegrees",
        "Ny",
        "Nx",
    ],
    "reduced_gg": ["N", "pl"],
    "sh": ["M", "K", "J"],
}
GRID_TYPE_KEYS = sorted(set(k for _, ks in GRID_TYPE_MAP.items() for k in ks))

ENSEMBLE_KEYS = ["number"]
VERTICAL_KEYS = ["level:float"]
DATA_TIME_KEYS = ["dataDate", "dataTime", "endStep"]
ALL_REF_TIME_KEYS = [
    "time",
    "step",
    "valid_time",
    "verifying_time",
    "forecastMonth",
    "indexing_time",
]
SPECTRA_KEYS = ["directionNumber", "frequencyNumber"]

ALL_HEADER_DIMS = ENSEMBLE_KEYS + VERTICAL_KEYS + SPECTRA_KEYS

INDEX_KEYS = sorted(
    GLOBAL_ATTRIBUTES_KEYS + DATA_ATTRIBUTES_KEYS + DATA_TIME_KEYS + ALL_HEADER_DIMS
)

COORD_ATTRS = {
    # geography
    "latitude": {"units": "degrees_north", "standard_name": "latitude", "long_name": "latitude"},
    "longitude": {"units": "degrees_east", "standard_name": "longitude", "long_name": "longitude"},
    # vertical
    "depthBelowLand": {
        "units": "m",
        "positive": "down",
        "long_name": "soil depth",
        "standard_name": "depth",
    },
    "depthBelowLandLayer": {
        "units": "m",
        "positive": "down",
        "long_name": "soil depth",
        "standard_name": "depth",
    },
    "hybrid": {
        "units": "1",
        "positive": "down",
        "long_name": "hybrid level",
        "standard_name": "atmosphere_hybrid_sigma_pressure_coordinate",
    },
    "heightAboveGround": {
        "units": "m",
        "positive": "up",
        "long_name": "height above the surface",
        "standard_name": "height",
    },
    "isobaricInhPa": {
        "units": "hPa",
        "positive": "down",
        "stored_direction": "decreasing",
        "standard_name": "air_pressure",
        "long_name": "pressure",
    },
    "isobaricInPa": {
        "units": "Pa",
        "positive": "down",
        "stored_direction": "decreasing",
        "standard_name": "air_pressure",
        "long_name": "pressure",
    },
    "isobaricLayer": {
        "units": "Pa",
        "positive": "down",
        "standard_name": "air_pressure",
        "long_name": "pressure",
    },
    # ensemble
    "number": {
        "units": "1",
        "standard_name": "realization",
        "long_name": "ensemble member numerical id",
    },
    # time
    "step": {
        "units": "hours",
        "standard_name": "forecast_period",
        "long_name": "time since forecast_reference_time",
    },
    "time": {
        "units": "seconds since 1970-01-01T00:00:00",
        "calendar": "proleptic_gregorian",
        "standard_name": "forecast_reference_time",
        "long_name": "initial time of forecast",
    },
    "indexing_time": {
        "units": "seconds since 1970-01-01T00:00:00",
        "calendar": "proleptic_gregorian",
        "standard_name": "forecast_reference_time",
        "long_name": "nominal initial time of forecast",
    },
    "valid_time": {
        "units": "seconds since 1970-01-01T00:00:00",
        "calendar": "proleptic_gregorian",
        "standard_name": "time",
        "long_name": "time",
    },
    "verifying_time": {
        "units": "seconds since 1970-01-01T00:00:00",
        "calendar": "proleptic_gregorian",
        "standard_name": "time",
        "long_name": "time",
    },
    "forecastMonth": {"units": "1", "long_name": "months since forecast_reference_time"},
}


class DatasetBuildError(ValueError):
    def __str__(self) -> str:
        return str(self.args[0])


def enforce_unique_attributes(index, attributes_keys, filter_by_keys={}):
    # type: (T.Mapping[str, T.List[T.Any]], T.Sequence[str], T.Dict[str, T.Any]) -> T.Dict[str, T.Any]
    attributes = {}  # type: T.Dict[str, T.Any]
    for key in attributes_keys:
        values = index.get(key, [])
        if len(values) > 1:
            fbks = []
            for value in values:
                fbk = {key: value}
                fbk.update(filter_by_keys)
                fbks.append(fbk)
            raise DatasetBuildError("multiple values for key %r" % key, key, fbks)
        if values and values[0] not in ("undef", "unknown"):
            attributes["GRIB_" + key] = values[0]
    return attributes


@attr.attrs(auto_attribs=True, eq=False)
class Variable:
    dimensions: T.Tuple[str, ...]
    data: np.ndarray
    attributes: T.Dict[str, T.Any] = attr.attrib(default={}, repr=False)

    def __eq__(self, other):
        # type: (T.Any) -> bool
        if other.__class__ is not self.__class__:
            return NotImplemented
        equal = (self.dimensions, self.attributes) == (other.dimensions, other.attributes)
        return equal and np.array_equal(self.data, other.data)


def expand_item(item, shape):
    # type: (T.Tuple[T.Any, ...], T.Sequence[int]) -> T.Tuple[T.List[int], ...]
    expanded_item = []
    for i, size in zip(item, shape):
        if isinstance(i, (list, np.ndarray)):
            expanded_item.append([int(e) for e in i])
        elif isinstance(i, slice):
            expanded_item.append(list(range(i.start or 0, i.stop or size, i.step or 1)))
        elif isinstance(i, int):
            expanded_item.append([i])
        else:
            raise TypeError("Unsupported index type %r" % type(i))
    return tuple(expanded_item)


def get_values_in_order(message, shape):
    # type: (abc.Field, T.Tuple[int]) -> np.ndarray
    # inform the data provider to return missing values as missing_value
    values = message["values"]
    if message.get("alternativeRowScanning", False):
        values = values.copy().reshape(shape)
        values[1::2, :] = values[1::2, ::-1]
        return values.flatten()
    else:
        return values


@attr.attrs(auto_attribs=True)
class OnDiskArray:
    index: abc.Index[T.Any, abc.Field]
    shape: T.Tuple[int, ...]
    field_id_index: T.Dict[
        T.Tuple[T.Any, ...], T.List[T.Union[int, T.Tuple[int, int]]]
    ] = attr.attrib(repr=False)
    missing_value: float
    geo_ndim: int = attr.attrib(default=1, repr=False)
    dtype = np.dtype("float32")

    def build_array(self) -> np.ndarray:
        """Helper method used to test __getitem__"""
        array = np.full(self.shape, fill_value=np.nan, dtype="float32")
        for header_indexes, message_ids in self.field_id_index.items():
            # NOTE: fill a single field as found in the message
            message = self.index.get_field(message_ids[0])  # type: ignore
            values = get_values_in_order(message, array[header_indexes].shape)
            array.__getitem__(header_indexes).flat[:] = values
        array[array == self.missing_value] = np.nan
        return array

    def __getitem__(self, item):
        # type: (T.Tuple[T.Any, ...]) -> np.ndarray
        header_item_list = expand_item(item[: -self.geo_ndim], self.shape)
        header_item = [{ix: i for i, ix in enumerate(it)} for it in header_item_list]
        array_field_shape = tuple(len(i) for i in header_item_list) + self.shape[-self.geo_ndim :]
        array_field = np.full(array_field_shape, fill_value=np.nan, dtype="float32")
        for header_indexes, message_ids in self.field_id_index.items():
            try:
                array_field_indexes = [it[ix] for it, ix in zip(header_item, header_indexes)]
            except KeyError:
                continue
            # NOTE: fill a single field as found in the message
            message = self.index.get_field(message_ids[0])  # type: ignore
            values = get_values_in_order(message, array_field[tuple(array_field_indexes)].shape)
            array_field.__getitem__(tuple(array_field_indexes)).flat[:] = values

        array = np.asarray(array_field[(Ellipsis,) + item[-self.geo_ndim :]])
        array[array == self.missing_value] = np.nan
        for i, it in reversed(list(enumerate(item[: -self.geo_ndim]))):
            if isinstance(it, int):
                array = array[(slice(None, None, None),) * i + (0,)]
        return array


GRID_TYPES_DIMENSION_COORDS = {"regular_ll", "regular_gg"}
GRID_TYPES_2D_NON_DIMENSION_COORDS = {
    "rotated_ll",
    "rotated_gg",
    "lambert",
    "lambert_azimuthal_equal_area",
    "albers",
    "polar_stereographic",
}


def build_geography_coordinates(
    first: abc.Field,
    encode_cf: T.Sequence[str],
    errors: str,
    log: logging.Logger = LOG,
) -> T.Tuple[T.Tuple[str, ...], T.Tuple[int, ...], T.Dict[str, Variable]]:
    geo_coord_vars = {}  # type: T.Dict[str, Variable]
    grid_type = first["gridType"]
    if "geography" in encode_cf and grid_type in GRID_TYPES_DIMENSION_COORDS:
        geo_dims = ("latitude", "longitude")  # type: T.Tuple[str, ...]
        geo_shape = (first["Ny"], first["Nx"])  # type: T.Tuple[int, ...]
        latitudes = np.array(first["distinctLatitudes"], ndmin=1)
        geo_coord_vars["latitude"] = Variable(
            dimensions=("latitude",), data=latitudes, attributes=COORD_ATTRS["latitude"].copy()
        )

        if latitudes[0] > latitudes[-1]:
            geo_coord_vars["latitude"].attributes["stored_direction"] = "decreasing"
        geo_coord_vars["longitude"] = Variable(
            dimensions=("longitude",),
            data=np.array(first["distinctLongitudes"], ndmin=1),
            attributes=COORD_ATTRS["longitude"],
        )
    elif "geography" in encode_cf and grid_type in GRID_TYPES_2D_NON_DIMENSION_COORDS:
        geo_dims = ("y", "x")
        geo_shape = (first["Ny"], first["Nx"])
        try:
            geo_coord_vars["latitude"] = Variable(
                dimensions=("y", "x"),
                data=np.array(first["latitudes"]).reshape(geo_shape),
                attributes=COORD_ATTRS["latitude"],
            )
            geo_coord_vars["longitude"] = Variable(
                dimensions=("y", "x"),
                data=np.array(first["longitudes"]).reshape(geo_shape),
                attributes=COORD_ATTRS["longitude"],
            )
        except KeyError:  # pragma: no cover
            if errors != "ignore":
                log.warning("ecCodes provides no latitudes/longitudes for gridType=%r", grid_type)
    else:
        geo_dims = ("values",)
        geo_shape = (first["numberOfPoints"],)
        # add secondary coordinates if ecCodes provides them
        try:
            latitude = first["latitudes"]
            geo_coord_vars["latitude"] = Variable(
                dimensions=("values",), data=np.array(latitude), attributes=COORD_ATTRS["latitude"]
            )
            longitude = first["longitudes"]
            geo_coord_vars["longitude"] = Variable(
                dimensions=("values",),
                data=np.array(longitude),
                attributes=COORD_ATTRS["longitude"],
            )
        except KeyError:  # pragma: no cover
            if errors != "ignore":
                log.warning("ecCodes provides no latitudes/longitudes for gridType=%r", grid_type)
    return geo_dims, geo_shape, geo_coord_vars


def encode_cf_first(data_var_attrs, encode_cf=("parameter", "time"), time_dims=("time", "step")):
    # type: (T.MutableMapping[str, T.Any], T.Sequence[str], T.Sequence[str]) -> T.List[str]
    coords_map = ENSEMBLE_KEYS[:]
    param_id = data_var_attrs.get("GRIB_paramId", "undef")
    data_var_attrs["long_name"] = "original GRIB paramId: %s" % param_id
    data_var_attrs["units"] = "1"
    if "parameter" in encode_cf:
        if "GRIB_cfName" in data_var_attrs:
            data_var_attrs["standard_name"] = data_var_attrs["GRIB_cfName"]
        if "GRIB_name" in data_var_attrs:
            data_var_attrs["long_name"] = data_var_attrs["GRIB_name"]
        if "GRIB_units" in data_var_attrs:
            data_var_attrs["units"] = data_var_attrs["GRIB_units"]
    if "time" in encode_cf:
        if set(time_dims).issubset(ALL_REF_TIME_KEYS):
            coords_map.extend(time_dims)
        else:
            raise ValueError("time_dims %r not a subset of %r" % (time_dims, ALL_REF_TIME_KEYS))
    else:
        coords_map.extend(DATA_TIME_KEYS)
    coords_map.extend(VERTICAL_KEYS)
    coords_map.extend(SPECTRA_KEYS)
    return coords_map


def read_data_var_attrs(first: abc.Field, extra_keys: T.List[str]) -> T.Dict[str, T.Any]:
    attributes = {}
    for key in extra_keys:
        try:
            value = first[key]
            if value is not None:
                attributes["GRIB_" + key] = value
        except Exception:
            pass
    return attributes


def build_variable_components(
    index: abc.Index[T.Any, abc.Field],
    encode_cf: T.Sequence[str] = (),
    filter_by_keys: T.Dict[str, T.Any] = {},
    log: logging.Logger = LOG,
    errors: str = "warn",
    squeeze: bool = True,
    read_keys: T.Iterable[str] = (),
    time_dims: T.Sequence[str] = ("time", "step"),
    extra_coords: T.Dict[str, str] = {},
) -> T.Tuple[T.Dict[str, int], Variable, T.Dict[str, Variable]]:
    data_var_attrs = enforce_unique_attributes(index, DATA_ATTRIBUTES_KEYS, filter_by_keys)
    grid_type_keys = GRID_TYPE_MAP.get(index.getone("gridType"), [])
    extra_keys = sorted(list(read_keys) + EXTRA_DATA_ATTRIBUTES_KEYS + grid_type_keys)
    first = index.first()
    extra_attrs = read_data_var_attrs(first, extra_keys)
    data_var_attrs.update(**extra_attrs)
    coords_map = encode_cf_first(data_var_attrs, encode_cf, time_dims)

    coord_name_key_map = {}
    coord_vars = {}
    for coord_key in coords_map:
        values = index[coord_key]
        if len(values) == 1 and values[0] == "undef":
            log.debug("missing from GRIB stream: %r" % coord_key)
            continue
        orig_name = coord_key.partition(":")[0]
        coord_name = orig_name
        if (
            "vertical" in encode_cf
            and coord_name == "level"
            and "GRIB_typeOfLevel" in data_var_attrs
        ):
            coord_name = data_var_attrs["GRIB_typeOfLevel"]
        coord_name_key_map[coord_name] = coord_key
        attributes = {
            "long_name": "original GRIB coordinate for key: %s(%s)" % (orig_name, coord_name),
            "units": "1",
        }
        attributes.update(COORD_ATTRS.get(coord_name, {}).copy())
        data = np.array(sorted(values, reverse=attributes.get("stored_direction") == "decreasing"))
        dimensions = (coord_name,)  # type: T.Tuple[str, ...]
        if squeeze and len(values) == 1:
            data = data[0]
            dimensions = ()
        coord_vars[coord_name] = Variable(dimensions=dimensions, data=data, attributes=attributes)

    header_dimensions = tuple(d for d, c in coord_vars.items() if not squeeze or c.data.size > 1)
    header_shape = tuple(coord_vars[d].data.size for d in header_dimensions)

    geo_dims, geo_shape, geo_coord_vars = build_geography_coordinates(first, encode_cf, errors)
    dimensions = header_dimensions + geo_dims
    shape = header_shape + geo_shape
    coord_vars.update(geo_coord_vars)

    offsets = {}  # type: T.Dict[T.Tuple[int, ...], T.List[T.Union[int, T.Tuple[int, int]]]]
    header_value_index = {}
    extra_coords_data: T.Dict[str, T.Dict[str, T.Any]] = {
        coord_name: {} for coord_name in extra_coords
    }
    extra_dims = tuple(extra_coords.values())
    for dim in header_dimensions + extra_dims:
        if np.isscalar(coord_vars[dim].data):
            header_value_index[dim] = {coord_vars[dim].data.item(): 0}
        else:
            header_value_index[dim] = {v: i for i, v in enumerate(coord_vars[dim].data.tolist())}
    for header_values, message_ids in index.iter_index():
        header_indexes = []  # type: T.List[int]
        for dim in header_dimensions + extra_dims:
            header_value = header_values[index.index_keys.index(coord_name_key_map.get(dim, dim))]
            if dim in header_dimensions:
                header_indexes.append(header_value_index[dim][header_value])
            for coord_name in extra_coords:
                coord_value = header_values[
                    index.index_keys.index(coord_name_key_map.get(coord_name, coord_name))
                ]
                if dim == extra_coords[coord_name]:
                    saved_coord_value = extra_coords_data[coord_name].get(
                        header_value, coord_value
                    )
                    if saved_coord_value != coord_value:
                        raise ValueError(
                            f"'{coord_name}' cannot be indexed by dimension '{extra_coords[coord_name]}': \n"
                            f"found two '{coord_name}' distinct values ({saved_coord_value}, {coord_value}) "
                            f"for '{extra_coords[coord_name]}' value {header_value}."
                        )

                    extra_coords_data[coord_name][header_value] = coord_value
        offsets[tuple(header_indexes)] = message_ids
    missing_value = data_var_attrs.get("missingValue", messages.MISSING_VAUE_INDICATOR)
    on_disk_array = OnDiskArray(
        index=index,
        shape=shape,
        field_id_index=offsets,
        missing_value=missing_value,
        geo_ndim=len(geo_dims),
    )

    if "time" in coord_vars and "step" in coord_vars:
        # add the 'valid_time' secondary coordinate
        time_dims, time_data = cfmessage.build_valid_time(
            coord_vars["time"].data,
            coord_vars["step"].data,
        )
        attrs = COORD_ATTRS["valid_time"]
        coord_vars["valid_time"] = Variable(dimensions=time_dims, data=time_data, attributes=attrs)

    for coord_name in extra_coords:
        coord_data = np.array(list(extra_coords_data[coord_name].values()))
        if extra_coords[coord_name] not in header_dimensions:
            coord_dims: T.Tuple[str, ...] = ()
            coord_data = coord_data.reshape(())
        else:
            coord_dims = (extra_coords[coord_name],)
        attrs = COORD_ATTRS.get(coord_name, {}).copy()
        coord_vars[coord_name] = Variable(dimensions=coord_dims, data=coord_data, attributes=attrs)

    data_var_attrs["coordinates"] = " ".join(coord_vars.keys())
    # OnDiskArray is close enough to np.ndarray to work, but not to make mypy happy
    data_var = Variable(dimensions=dimensions, data=on_disk_array, attributes=data_var_attrs)  # type: ignore
    dims = {d: s for d, s in zip(dimensions, data_var.data.shape)}
    return dims, data_var, coord_vars


def dict_merge(master, update):
    # type: (T.Dict[str, T.Any], T.Dict[str, T.Any]) -> None
    for key, value in update.items():
        if key not in master:
            master[key] = value
        elif master[key] == value:
            pass
        else:
            raise DatasetBuildError(
                "key present and new value is different: "
                "key=%r value=%r new_value=%r" % (key, master[key], value)
            )


def build_dataset_attributes(index, filter_by_keys, encoding):
    # type: (abc.Index[T.Any, abc.Field], T.Dict[str, T.Any], T.Dict[str, T.Any]) -> T.Dict[str, T.Any]
    attributes = enforce_unique_attributes(index, GLOBAL_ATTRIBUTES_KEYS, filter_by_keys)
    attributes["Conventions"] = "CF-1.7"
    if "GRIB_centreDescription" in attributes:
        attributes["institution"] = attributes["GRIB_centreDescription"]
    attributes_namespace = {
        "cfgrib_version": __version__,
        "cfgrib_open_kwargs": json.dumps(encoding),
        "eccodes_version": messages.eccodes_version,
        "timestamp": datetime.datetime.now().isoformat().partition(".")[0][:16],
    }
    history_in = (
        "{timestamp} GRIB to CDM+CF via "
        "cfgrib-{cfgrib_version}/ecCodes-{eccodes_version} with {cfgrib_open_kwargs}"
    )
    attributes["history"] = history_in.format(**attributes_namespace)
    return attributes


def build_dataset_components(
    index: abc.Index[T.Any, abc.Field],
    errors: str = "warn",
    encode_cf: T.Sequence[str] = ("parameter", "time", "geography", "vertical"),
    squeeze: bool = True,
    log: logging.Logger = LOG,
    read_keys: T.Iterable[str] = (),
    time_dims: T.Sequence[str] = ("time", "step"),
    extra_coords: T.Dict[str, str] = {},
) -> T.Tuple[T.Dict[str, int], T.Dict[str, Variable], T.Dict[str, T.Any], T.Dict[str, T.Any]]:
    dimensions = {}  # type: T.Dict[str, int]
    variables = {}  # type: T.Dict[str, Variable]
    filter_by_keys = index.filter_by_keys
    for param_id in index.get("paramId", []):
        var_index = index.subindex(paramId=param_id)
        try:
            dims, data_var, coord_vars = build_variable_components(
                var_index,
                encode_cf,
                filter_by_keys,
                errors=errors,
                squeeze=squeeze,
                read_keys=read_keys,
                time_dims=time_dims,
                extra_coords=extra_coords,
            )
        except DatasetBuildError as ex:
            # NOTE: When a variable has more than one value for an attribute we need to raise all
            #   the values in the file, not just the ones associated with that variable. See #54.
            key = ex.args[1]
            error_message = "multiple values for unique key, try re-open the file with one of:"
            fbks = []
            for value in index[key]:
                fbk = {key: value}
                fbk.update(filter_by_keys)
                fbks.append(fbk)
                error_message += "\n    filter_by_keys=%r" % fbk
            raise DatasetBuildError(error_message, key, fbks)
        short_name = data_var.attributes.get("GRIB_shortName", "paramId_%d" % param_id)
        var_name = data_var.attributes.get("GRIB_cfVarName", "unknown")
        if "parameter" in encode_cf and var_name not in ("undef", "unknown"):
            short_name = var_name
        try:
            dict_merge(variables, coord_vars)
            dict_merge(variables, {short_name: data_var})
            dict_merge(dimensions, dims)
        except ValueError:
            if errors == "ignore":
                pass
            elif errors == "raise":
                raise
            else:
                log.exception("skipping variable: paramId==%r shortName=%r", param_id, short_name)
    encoding = {
        "source": index.source(),
        "filter_by_keys": filter_by_keys,
        "encode_cf": encode_cf,
    }
    attributes = build_dataset_attributes(index, filter_by_keys, encoding)
    return dimensions, variables, attributes, encoding


@attr.attrs(auto_attribs=True)
class Dataset:
    """
    Map a GRIB file to the NetCDF Common Data Model with CF Conventions.
    """

    dimensions: T.Dict[str, int]
    variables: T.Dict[str, Variable]
    attributes: T.Dict[str, T.Any]
    encoding: T.Dict[str, T.Any]


def compute_index_keys(
    time_dims: T.Sequence[str] = ("time", "step"),
    extra_coords: T.Dict[str, str] = {},
    filter_by_keys: T.Dict[str, T.Any] = {},
) -> T.List[str]:
    return sorted(set(INDEX_KEYS) | set(filter_by_keys) | set(time_dims) | set(extra_coords))


def open_from_index(
    index: abc.Index[T.Any, abc.Field],
    read_keys: T.Sequence[str] = (),
    time_dims: T.Sequence[str] = ("time", "step"),
    extra_coords: T.Dict[str, str] = {},
    **kwargs: T.Any,
) -> Dataset:
    dimensions, variables, attributes, encoding = build_dataset_components(
        index, read_keys=read_keys, time_dims=time_dims, extra_coords=extra_coords, **kwargs
    )
    return Dataset(dimensions, variables, attributes, encoding)


def open_fieldset(
    fieldset: T.Union[abc.Fieldset[abc.Field], abc.MappingFieldset[T.Any, abc.Field]],
    indexpath: T.Optional[str] = None,
    filter_by_keys: T.Dict[str, T.Any] = {},
    read_keys: T.Sequence[str] = (),
    time_dims: T.Sequence[str] = ("time", "step"),
    extra_coords: T.Dict[str, str] = {},
    computed_keys: messages.ComputedKeysType = cfmessage.COMPUTED_KEYS,
    log: logging.Logger = LOG,
    **kwargs: T.Any,
) -> Dataset:
    """Builds a ``cfgrib.Dataset`` form a mapping of mappings."""
    if indexpath is not None and indexpath is not messages.DEFAULT_INDEXPATH:
        log.warning(f"indexpath value {indexpath} is ignored")

    index_keys = compute_index_keys(time_dims, extra_coords, filter_by_keys)
    index = messages.FieldsetIndex.from_fieldset(fieldset, index_keys, computed_keys)
    filtered_index = index.subindex(filter_by_keys)
    return open_from_index(filtered_index, read_keys, time_dims, extra_coords, **kwargs)


def open_fileindex(
    stream: messages.FileStream,
    indexpath: str = messages.DEFAULT_INDEXPATH,
    index_keys: T.Sequence[str] = INDEX_KEYS + ["time", "step"],
    filter_by_keys: T.Dict[str, T.Any] = {},
    computed_keys: messages.ComputedKeysType = cfmessage.COMPUTED_KEYS,
) -> messages.FileIndex:
    index_keys = sorted(set(index_keys) | set(filter_by_keys))
    index = messages.FileIndex.from_indexpath_or_filestream(
        stream, index_keys, indexpath=indexpath, computed_keys=computed_keys
    )
    return index.subindex(filter_by_keys)


def open_file(
    path: T.Union[str, "os.PathLike[str]"],
    grib_errors: str = "warn",
    indexpath: str = messages.DEFAULT_INDEXPATH,
    filter_by_keys: T.Dict[str, T.Any] = {},
    read_keys: T.Sequence[str] = (),
    time_dims: T.Sequence[str] = ("time", "step"),
    extra_coords: T.Dict[str, str] = {},
    **kwargs: T.Any,
) -> Dataset:
    """Open a GRIB file as a ``cfgrib.Dataset``."""
    path = os.fspath(path)
    stream = messages.FileStream(path, errors=grib_errors)

    index_keys = compute_index_keys(time_dims, extra_coords)
    index = open_fileindex(stream, indexpath, index_keys, filter_by_keys=filter_by_keys)

    return open_from_index(index, read_keys, time_dims, extra_coords, **kwargs)
