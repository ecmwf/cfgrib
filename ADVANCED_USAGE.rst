
ECMWF’s MARS and Metview software introduced the notion of *Fieldset* which is an
ordered collection of GRIB message. The *Fieldset* is an abstract concept and can be
implemented in many ways. In the case of MARS and Metview, a *Fieldset* is an implemented
internally as an array of *Field*s, each *Field* being represented by a file path, an offset and a
length where the actual GRIB message can be found. Thus, a *Fieldset* can represent an
ordered collection of *Field*s which are at various locations of several files.

*cfgrib* now provides the definition of the ``Fieldset`` and ``Field`` interfaces in the
``cfbrib.abc`` module.
Both classes are simple python mappings so the *cfgrib* can build a Dataset form something
as simple as a dictionary of dictionaries.

Classes that implemnent the ``Fieldset`` interface can use the low-level intreface
``cfgrib.open_fielset`` to obtain a ``cfgrib.Dataset`` or be passed directly to
*Xarray*:

.. code-block: python

    >>> import xarray as xr
    >>> fieldset = {
    ...     0: {
    ...         "gridType": "regular_ll",
    ...         "Nx": 2,
    ...         "Ny": 3,
    ...         "distinctLatitudes": [-10.0, 0.0, 10.0],
    ...         "distinctLongitudes": [0.0, 10.0],
    ...         "paramId": 130,
    ...         "shortName": "t",
    ...         "values": [[1, 2], [3, 4], [5, 6]],
    ...     }
    ... }
    >>> ds = xr.open_dataset(fieldset, engine="cfgrib")
    >>> ds
    <xarray.Dataset>
    Dimensions:    (latitude: 3, longitude: 2)
    Coordinates:
      * latitude   (latitude) float64 -10.0 0.0 10.0
      * longitude  (longitude) float64 0.0 10.0
    Data variables:
        t          (latitude, longitude) float32 ...
    Attributes:
        Conventions:  CF-1.7
        history:      ...
    >>> ds.mean()
    <xarray.Dataset>
    Dimensions:  ()
    Data variables:
        t        float32 3.5
