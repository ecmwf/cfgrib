import os.path
import pathlib
import typing as T

import numpy as np
import pytest

from cfgrib import cfmessage, dataset, messages

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), "sample-data")
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, "era5-levels-members.grib")
TEST_DATA_UKMO = os.path.join(SAMPLE_DATA_FOLDER, "forecast_monthly_ukmo.grib")
TEST_DATA_SCALAR_TIME = os.path.join(SAMPLE_DATA_FOLDER, "era5-single-level-scalar-time.grib")


def test_enforce_unique_attributes() -> None:
    assert dataset.enforce_unique_attributes({"key": [1]}, ["key"])
    assert not dataset.enforce_unique_attributes({"key": ["undef"]}, ["key"])

    with pytest.raises(dataset.DatasetBuildError):
        assert dataset.enforce_unique_attributes({"key": [1, 2]}, ["key"])


def test_Variable() -> None:
    res = dataset.Variable(dimensions=("lat",), data=np.array([0.0]), attributes={})

    assert res == res
    assert res != 1


@pytest.mark.parametrize(
    "item,shape,expected",
    [
        (([1, 5],), (10,), ([1, 5],)),
        ((np.array([1]),), (10,), ([1],)),
        ((slice(0, 3, 2),), (10,), ([0, 2],)),
        ((1,), (10,), ([1],)),
    ],
)
def test_expand_item(item: T.Any, shape: T.Any, expected: T.Any) -> None:
    assert dataset.expand_item(item, shape) == expected


def test_expand_item_error() -> None:
    with pytest.raises(TypeError):
        dataset.expand_item((None,), (1,))


def test_dict_merge() -> None:
    master = {"one": 1}
    dataset.dict_merge(master, {"two": 2})
    assert master == {"one": 1, "two": 2}
    dataset.dict_merge(master, {"two": 2})
    assert master == {"one": 1, "two": 2}

    with pytest.raises(dataset.DatasetBuildError):
        dataset.dict_merge(master, {"two": 3})


def test_encode_cf_first() -> None:
    assert dataset.encode_cf_first({})


def test_build_data_var_components_no_encode() -> None:
    index_keys = sorted(dataset.INDEX_KEYS + ["time", "step"])
    index = messages.FileStream(path=TEST_DATA).index(index_keys).subindex(paramId=130)
    dims, data_var, coord_vars = dataset.build_variable_components(index=index)
    assert dims == {"number": 10, "dataDate": 2, "dataTime": 2, "level": 2, "values": 7320}
    assert data_var.data.shape == (10, 2, 2, 2, 7320)

    # equivalent to not np.isnan without importing numpy
    assert data_var.data[:, :, :, :, :].mean() > 0.0


def test_build_data_var_components_encode_cf_geography() -> None:
    stream = messages.FileStream(path=TEST_DATA, message_class=cfmessage.CfMessage)
    index_keys = sorted(dataset.INDEX_KEYS + ["time", "step"])
    index = stream.index(index_keys).subindex(paramId=130)
    dims, data_var, coord_vars = dataset.build_variable_components(
        index=index, encode_cf="geography"
    )
    assert dims == {
        "number": 10,
        "dataDate": 2,
        "dataTime": 2,
        "level": 2,
        "latitude": 61,
        "longitude": 120,
    }
    assert data_var.data.shape == (10, 2, 2, 2, 61, 120)

    # equivalent to not np.isnan without importing numpy
    assert data_var.data[:, :, :, :, :, :].mean() > 0.0


def test_build_dataset_components_time_dims() -> None:
    index_keys = sorted(dataset.INDEX_KEYS + ["time", "step"])
    index = dataset.open_fileindex(TEST_DATA_UKMO, "warn", "{path}.{short_hash}.idx", index_keys)
    dims = dataset.build_dataset_components(index, read_keys=[])[0]
    assert dims == {
        "latitude": 6,
        "longitude": 11,
        "number": 28,
        "step": 20,
        "time": 8,
    }
    time_dims = ["indexing_time", "verifying_time"]
    index_keys = sorted(dataset.INDEX_KEYS + time_dims)
    index = dataset.open_fileindex(TEST_DATA_UKMO, "warn", "{path}.{short_hash}.idx", index_keys)
    dims, *_ = dataset.build_dataset_components(index, read_keys=[], time_dims=time_dims)
    assert dims == {
        "number": 28,
        "indexing_time": 2,
        "verifying_time": 4,
        "latitude": 6,
        "longitude": 11,
    }

    time_dims = ["indexing_time", "step"]
    index_keys = sorted(dataset.INDEX_KEYS + time_dims)
    index = dataset.open_fileindex(TEST_DATA_UKMO, "warn", "{path}.{short_hash}.idx", index_keys)
    dims, *_ = dataset.build_dataset_components(index, read_keys=[], time_dims=time_dims)
    assert dims == {"number": 28, "indexing_time": 2, "step": 20, "latitude": 6, "longitude": 11}


def test_Dataset() -> None:
    res = dataset.open_file(TEST_DATA)
    assert "Conventions" in res.attributes
    assert "institution" in res.attributes
    assert "history" in res.attributes
    assert res.attributes["GRIB_edition"] == 1
    assert tuple(res.dimensions.keys()) == (
        "number",
        "time",
        "isobaricInhPa",
        "latitude",
        "longitude",
    )
    assert len(res.variables) == 9

    res1 = dataset.open_file(pathlib.Path(TEST_DATA))

    assert res1 == res


def test_Dataset_no_encode() -> None:
    res = dataset.open_file(TEST_DATA, encode_cf=())
    assert "Conventions" in res.attributes
    assert "institution" in res.attributes
    assert "history" in res.attributes
    assert res.attributes["GRIB_edition"] == 1
    assert tuple(res.dimensions.keys()) == ("number", "dataDate", "dataTime", "level", "values")
    assert len(res.variables) == 9


def test_Dataset_encode_cf_time() -> None:
    res = dataset.open_file(TEST_DATA, encode_cf=("time",))
    assert "history" in res.attributes
    assert res.attributes["GRIB_edition"] == 1
    assert tuple(res.dimensions.keys()) == ("number", "time", "level", "values")
    assert len(res.variables) == 9

    # equivalent to not np.isnan without importing numpy
    assert res.variables["t"].data[:, :, :, :].mean() > 0.0


def test_Dataset_encode_cf_geography() -> None:
    res = dataset.open_file(TEST_DATA, encode_cf=("geography",))
    assert "history" in res.attributes
    assert res.attributes["GRIB_edition"] == 1
    assert tuple(res.dimensions.keys()) == (
        "number",
        "dataDate",
        "dataTime",
        "level",
        "latitude",
        "longitude",
    )
    assert len(res.variables) == 9

    # equivalent to not np.isnan without importing numpy
    assert res.variables["t"].data[:, :, :, :, :, :].mean() > 0.0


def test_Dataset_encode_cf_vertical() -> None:
    res = dataset.open_file(TEST_DATA, encode_cf=("vertical",))
    assert "history" in res.attributes
    assert res.attributes["GRIB_edition"] == 1
    expected_dimensions = ("number", "dataDate", "dataTime", "isobaricInhPa", "values")
    assert tuple(res.dimensions.keys()) == expected_dimensions
    assert len(res.variables) == 9

    # equivalent to not np.isnan without importing numpy
    assert res.variables["t"].data[:, :, :, :, :].mean() > 0.0


def test_Dataset_reguler_gg_surface() -> None:
    path = os.path.join(SAMPLE_DATA_FOLDER, "regular_gg_sfc.grib")
    res = dataset.open_file(path)

    assert res.dimensions == {"latitude": 96, "longitude": 192}
    assert np.allclose(res.variables["latitude"].data[:2], [88.57216851, 86.72253095])


def test_Dataset_extra_coords() -> None:
    res = dataset.open_file(TEST_DATA, extra_coords={"experimentVersionNumber": "time"})
    assert "experimentVersionNumber" in res.variables
    assert res.variables["experimentVersionNumber"].dimensions == ("time",)


def test_Dataset_scalar_extra_coords() -> None:
    res = dataset.open_file(
        TEST_DATA_SCALAR_TIME, extra_coords={"experimentVersionNumber": "time"}
    )
    assert "experimentVersionNumber" in res.variables
    assert res.variables["experimentVersionNumber"].dimensions == ()


def test_Dataset_extra_coords_error() -> None:
    with pytest.raises(ValueError):
        dataset.open_file(TEST_DATA, extra_coords={"validityDate": "number"})


def test_OnDiskArray() -> None:
    res = dataset.open_file(TEST_DATA).variables["t"]

    assert isinstance(res.data, dataset.OnDiskArray)
    assert np.allclose(
        res.data[2:4:2, [0, 3], 0, 0, 0], res.data.build_array()[2:4:2, [0, 3], 0, 0, 0]
    )


def test_open_file() -> None:
    res = dataset.open_file(TEST_DATA, filter_by_keys={"shortName": "t"})

    assert "t" in res.variables
    assert "z" not in res.variables
