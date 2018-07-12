/*
 * Copyright 2005-2018 ECMWF.
 *
 * This software is licensed under the terms of the Apache Licence Version 2.0
 * which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
 *
 * In applying this licence, ECMWF does not waive the privileges and immunities granted to it by
 * virtue of its status as an intergovernmental organisation nor does it submit to any jurisdiction.
 */

/*! \file grib_api.h
  \brief grib_api C header file

*/

typedef enum ProductKind {PRODUCT_ANY, PRODUCT_GRIB, PRODUCT_BUFR, PRODUCT_METAR, PRODUCT_GTS, PRODUCT_TAF} ProductKind;

/* Types */
/*  undefined */
#define GRIB_TYPE_UNDEFINED 0
/*  long integer */
#define GRIB_TYPE_LONG 1
/*  double */
#define GRIB_TYPE_DOUBLE 2
/*  char*    */
#define GRIB_TYPE_STRING 3
/*  bytes */
#define GRIB_TYPE_BYTES 4
/*  section */
#define GRIB_TYPE_SECTION 5
/*  label */
#define GRIB_TYPE_LABEL 6
/*  missing */
#define GRIB_TYPE_MISSING 7

/*! Grib handle,   structure giving access to parsed message values by keys
    \ingroup grib_handle
*/
typedef struct grib_handle    grib_handle;

/*! Grib context,  structure containing the memory methods, the parsers and the formats.
    \ingroup grib_context
*/
typedef struct grib_context   grib_context;

/**
* Convert an error code into a string
* @param code       : the error code
* @return           the error message
*/
const char* grib_get_error_message(int code);

/* The truncation is the Gaussian number (or order) */
int grib_get_gaussian_latitudes(long truncation,double* latitudes);

/*! \defgroup errors Error codes
Error codes returned by the grib_api functions.
*/
/*! @{*/
/** No error */
#define GRIB_SUCCESS		0
/** End of resource reached */
#define GRIB_END_OF_FILE		-1
/** Internal error */
#define GRIB_INTERNAL_ERROR		-2
/** Passed buffer is too small */
#define GRIB_BUFFER_TOO_SMALL		-3
/** Function not yet implemented */
#define GRIB_NOT_IMPLEMENTED		-4
/** Missing 7777 at end of message */
#define GRIB_7777_NOT_FOUND		-5
/** Passed array is too small */
#define GRIB_ARRAY_TOO_SMALL		-6
/** File not found */
#define GRIB_FILE_NOT_FOUND		-7
/** Code not found in code table */
#define GRIB_CODE_NOT_FOUND_IN_TABLE		-8
/** Array size mismatch */
#define GRIB_WRONG_ARRAY_SIZE		-9
/** Key/value not found */
#define GRIB_NOT_FOUND		-10
/** Input output problem */
#define GRIB_IO_PROBLEM		-11
/** Message invalid */
#define GRIB_INVALID_MESSAGE		-12
/** Decoding invalid */
#define GRIB_DECODING_ERROR		-13
/** Encoding invalid */
#define GRIB_ENCODING_ERROR		-14
/** Code cannot unpack because of string too small */
#define GRIB_NO_MORE_IN_SET		-15
/** Problem with calculation of geographic attributes */
#define GRIB_GEOCALCULUS_PROBLEM		-16
/** Memory allocation error */
#define GRIB_OUT_OF_MEMORY		-17
/** Value is read only */
#define GRIB_READ_ONLY		-18
/** Invalid argument */
#define GRIB_INVALID_ARGUMENT		-19
/** Null handle */
#define GRIB_NULL_HANDLE		-20
/** Invalid section number */
#define GRIB_INVALID_SECTION_NUMBER		-21
/** Value cannot be missing */
#define GRIB_VALUE_CANNOT_BE_MISSING		-22
/** Wrong message length */
#define GRIB_WRONG_LENGTH		-23
/** Invalid key type */
#define GRIB_INVALID_TYPE		-24
/** Unable to set step */
#define GRIB_WRONG_STEP		-25
/** Wrong units for step (step must be integer) */
#define GRIB_WRONG_STEP_UNIT		-26
/** Invalid file id */
#define GRIB_INVALID_FILE		-27
/** Invalid grib id */
#define GRIB_INVALID_GRIB		-28
/** Invalid index id */
#define GRIB_INVALID_INDEX		-29
/** Invalid iterator id */
#define GRIB_INVALID_ITERATOR		-30
/** Invalid keys iterator id */
#define GRIB_INVALID_KEYS_ITERATOR		-31
/** Invalid nearest id */
#define GRIB_INVALID_NEAREST		-32
/** Invalid order by */
#define GRIB_INVALID_ORDERBY		-33
/** Missing a key from the fieldset */
#define GRIB_MISSING_KEY		-34
/** The point is out of the grid area */
#define GRIB_OUT_OF_AREA		-35
/** Concept no match */
#define GRIB_CONCEPT_NO_MATCH		-36
/** Hash array no match */
#define GRIB_HASH_ARRAY_NO_MATCH		-37
/** Definitions files not found */
#define GRIB_NO_DEFINITIONS		-38
/** Wrong type while packing */
#define GRIB_WRONG_TYPE		-39
/** End of resource */
#define GRIB_END		-40
/** Unable to code a field without values */
#define GRIB_NO_VALUES		-41
/** Grid description is wrong or inconsistent */
#define GRIB_WRONG_GRID		-42
/** End of index reached */
#define GRIB_END_OF_INDEX		-43
/** Null index */
#define GRIB_NULL_INDEX		-44
/** End of resource reached when reading message */
#define GRIB_PREMATURE_END_OF_FILE		-45
/** An internal array is too small */
#define GRIB_INTERNAL_ARRAY_TOO_SMALL		-46
/** Message is too large for the current architecture */
#define GRIB_MESSAGE_TOO_LARGE		-47
/** Constant field */
#define GRIB_CONSTANT_FIELD		-48
/** Switch unable to find a matching case */
#define GRIB_SWITCH_NO_MATCH		-49
/** Underflow */
#define GRIB_UNDERFLOW		-50
/** Message malformed */
#define GRIB_MESSAGE_MALFORMED		-51
/** Index is corrupted */
#define GRIB_CORRUPTED_INDEX		-52
/** Invalid number of bits per value */
#define GRIB_INVALID_BPV		-53
/** Edition of two messages is different */
#define GRIB_DIFFERENT_EDITION		-54
/** Value is different */
#define GRIB_VALUE_DIFFERENT		-55
/** Invalid key value */
#define GRIB_INVALID_KEY_VALUE		-56
/** String is smaller than requested */
#define GRIB_STRING_TOO_SMALL		-57
/** Wrong type conversion */
#define GRIB_WRONG_CONVERSION		-58
/** Missing BUFR table entry for descriptor */
#define GRIB_MISSING_BUFR_ENTRY		-59
/** Null pointer */
#define GRIB_NULL_POINTER		-60
/** Attribute is already present, cannot add */
#define GRIB_ATTRIBUTE_CLASH		-61
/** Too many attributes. Increase MAX_ACCESSOR_ATTRIBUTES */
#define GRIB_TOO_MANY_ATTRIBUTES		-62
/** Attribute not found. */
#define GRIB_ATTRIBUTE_NOT_FOUND		-63
/** Edition not supported. */
#define GRIB_UNSUPPORTED_EDITION		-64
/** Value out of coding range */
#define GRIB_OUT_OF_RANGE		-65
/** Size of bitmap is incorrect */
#define GRIB_WRONG_BITMAP_SIZE		-66
/*! @}*/
