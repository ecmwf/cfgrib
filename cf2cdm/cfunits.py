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

import typing as T

PRESSURE_CONVERSION_RULES: T.Dict[T.Tuple[str, ...], float] = {
    ("Pa", "pascal", "pascals"): 1.0,
    ("hPa", "hectopascal", "hectopascals", "hpascal", "millibar", "millibars", "mbar"): 100.0,
    ("decibar", "dbar"): 10000.0,
    ("bar", "bars"): 100000.0,
    ("atmosphere", "atmospheres", "atm"): 101325.0,
}

LENGTH_CONVERSION_RULES: T.Dict[T.Tuple[str, ...], float] = {
    ("m", "meter", "meters"): 1.0,
    ("cm", "centimeter", "centimeters"): 0.01,
    ("km", "kilometer", "kilometers"): 1000.0,
}


class ConversionError(Exception):
    pass


def simple_conversion_factor(source_units, target_units, rules):
    # type: (str, str, T.Dict[T.Tuple[str, ...], float]) -> float
    conversion_factor = 1.0
    seen = 0
    for pressure_units, factor in rules.items():
        if source_units in pressure_units:
            conversion_factor /= factor
            seen += 1
        if target_units in pressure_units:
            conversion_factor *= factor
            seen += 1
    if seen != 2:
        raise ConversionError("cannot convert from %r to %r." % (source_units, target_units))
    return conversion_factor


def convert_units(data: T.Any, target_units: str, source_units: str) -> T.Any:
    if target_units == source_units:
        return data
    for rules in [PRESSURE_CONVERSION_RULES, LENGTH_CONVERSION_RULES]:
        try:
            return data * simple_conversion_factor(target_units, source_units, rules)
        except ConversionError:
            pass
    raise ConversionError("cannot convert from %r to %r." % (source_units, target_units))


def are_convertible(source_units: str, target_units: str) -> bool:
    try:
        convert_units(1, source_units, target_units)
    except ConversionError:
        return False
    return True
