/*
 * Copyright 2005-2018 ECMWF.
 *
 * This software is licensed under the terms of the Apache Licence Version 2.0
 * which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
 *
 * In applying this licence, ECMWF does not waive the privileges and immunities granted to it by
 * virtue of its status as an intergovernmental organisation nor does it submit to any jurisdiction.
 */

/*! \file eccodes.h
  \brief The ecCodes C header file

  This is the only file that must be included to use the ecCodes library
  from C.
*/

/*! Codes handle,   structure giving access to parsed values by keys
    \ingroup codes_handle
    \struct codes_handle
*/
typedef struct grib_handle            codes_handle;

/*! Codes context,  structure containing the memory methods, the parsers and the formats.
    \ingroup codes_context
    \struct codes_context
*/
typedef struct grib_context           codes_context;

/*! Codes keys iterator. Iterator over keys.
    \ingroup keys_iterator
    \struct codes_keys_iterator
*/
typedef struct grib_keys_iterator     codes_keys_iterator;

/*! \defgroup codes_index The indexing feature
The codes_index is the structure giving indexed access to messages in a file.
 */
/*! @{*/

/*! index structure to access messages in a file.
 * \ingroup codes_index
 * \struct codes_index
*/
typedef struct grib_index             codes_index;

/**
 *  Create a new index form a file. The file is indexed with the keys in argument.
 *
 * @param c           : context  (NULL for default context)
 * @param filename    : name of the file of messages to be indexed
 * @param keys        : comma separated list of keys for the index.
 *    The type of the key can be explicitly declared appending :l for long,
 *    (or alternatively :i)
 *    :d for double, :s for string to the key name. If the type is not
 *    declared explicitly, the native type is assumed.
 * @param err         :  0 if OK, integer value on error
 * @return            the newly created index
 */
codes_index* codes_index_new_from_file(codes_context* c, char* filename,const char* keys,int *err);

/**
 *  Get the number of distinct values of the key in argument contained in the index. The key must belong to the index.
 *
 * @param index       : an index created from a file.
 *     The index must have been created with the key in argument.
 * @param key         : key for which the number of values is computed
 * @param size        : number of distinct values of the key in the index
 * @return            0 if OK, integer value on error
 */
int codes_index_get_size(codes_index* index,const char* key,size_t* size);

/**
 *  Get the distinct values of the key in argument contained in the index. The key must belong to the index. This function is used when the type of the key was explicitly defined as long or when the native type of the key is long.
 *
 * @param index       : an index created from a file.
 *     The index must have been created with the key in argument.
 * @param key         : key for which the values are returned
 * @param values      : array of values. The array must be allocated before entering this function and its size must be enough to contain all the values.
 * @param size        : size of the values array
 * @return            0 if OK, integer value on error
 */
int codes_index_get_long(codes_index* index,const char* key,long* values,size_t *size);

/**
 *  Get the distinct values of the key in argument contained in the index. The key must belong to the index. This function is used when the type of the key was explicitly defined as double or when the native type of the key is double.
 *
 * @param index       : an index created from a file.
 *     The index must have been created with the key in argument.
 * @param key         : key for which the values are returned
 * @param values      : array of values. The array must be allocated before entering this function and its size must be enough to contain all the values.
 * @param size        : size of the values array
 * @return            0 if OK, integer value on error
 */
int codes_index_get_double(codes_index* index,const char* key, double* values,size_t *size);

/**
 *  Get the distinct values of the key in argument contained in the index. The key must belong to the index. This function is used when the type of the key was explicitly defined as string or when the native type of the key is string.
 *
 * @param index       : an index created from a file.
 *     The index must have been created with the key in argument.
 * @param key         : key for which the values are returned
 * @param values      : array of values. The array must be allocated before entering this function and its size must be enough to contain all the values.
 * @param size        : size of the values array
 * @return            0 if OK, integer value on error
 */
int codes_index_get_string(codes_index* index,const char* key,char** values,size_t *size);


/**
 *  Select the message subset with key==value. The value is a long. The key must have been created with long type or have long as native type if the type was not explicitly defined in the index creation.
 *
 * @param index       : an index created from a file.
 *     The index must have been created with the key in argument.
 * @param key         : key to be selected
 * @param value       : value of the key to select
 * @return            0 if OK, integer value on error
 */
int codes_index_select_long(codes_index* index,const char* key,long value);

/**
 *  Select the message subset with key==value. The value is a double. The key must have been created with double type or have double as native type if the type was not explicitly defined in the index creation.
 *
 * @param index       : an index created from a file.
 *     The index must have been created with the key in argument.
 * @param key         : key to be selected
 * @param value       : value of the key to select
 * @return            0 if OK, integer value on error
 */
int codes_index_select_double(codes_index* index,const char* key,double value);

/**
 *  Select the message subset with key==value. The value is a string. The key must have been created with string type or have string as native type if the type was not explicitly defined in the index creation.
 *
 * @param index       : an index created from a file.
 *     The index must have been created with the key in argument.
 * @param key         : key to be selected
 * @param value       : value of the key to select
 * @return            0 if OK, integer value on error
 */
int codes_index_select_string(codes_index* index,const char* key,char* value);

/**
 *  Create a new handle from an index after having selected the key values.
 *  All the keys belonging to the index must be selected before calling this function. Successive calls to this function will return all the handles compatible with the constraints defined selecting the values of the index keys.
 * When no more handles are available from the index a NULL pointer is returned and the err variable is set to CODES_END_OF_INDEX.
 *
 * @param index       : an index created from a file.
 * @param err         :  0 if OK, integer value on error. CODES_END_OF_INDEX when no more handles are contained in the index.
 * @return            grib handle.
 */
codes_handle* codes_handle_new_from_index(codes_index* index,int *err);

/**
 *  Delete the index.
 *
 * @param index       : index to be deleted.
 */
void codes_index_delete(codes_index* index);

/**
*  Create a handle from a file resource.
*  The file is read until a message is found. The message is then copied.
*  Remember always to delete the handle when it is not needed anymore to avoid
*  memory leaks.
*
* @param c           : the context from which the handle will be created (NULL for default context)
* @param f           : the file resource
* @param product     : the kind of product e.g. PRODUCT_GRIB, PRODUCT_BUFR
* @param error       : error code set if the returned handle is NULL and the end of file is not reached
* @return            the new handle, NULL if the resource is invalid or a problem is encountered
*/
grib_handle* codes_handle_new_from_file(grib_context* c, FILE* f, ProductKind product, int* error);

/**
*  Write a coded message to a file.
*
* @param h           : codes_handle to be written
* @param file        : name of the output file
* @param mode        : mode
* @return            0 if OK, integer value on error
*/
int codes_write_message(codes_handle* h,const char* file,const char* mode);

/**
 *  Create a handle from a GRIB message contained in the samples directory.
 *  The message is copied at the creation of the handle
 *
 * @param c           : the context from which the handle will be created (NULL for default context)
 * @param sample_name : the name of the sample file (without the .tmpl extension)
 * @return            the new handle, NULL if the resource is invalid or a problem is encountered
 */
codes_handle* codes_grib_handle_new_from_samples (codes_context* c, const char* sample_name);

/**
 *  Create a handle from a BUFR message contained in a samples directory.
 *  The message is copied at the creation of the handle
 *
 * @param c           : the context from which the handle will be created (NULL for default context)
 * @param sample_name : the name of the sample file (without the .tmpl extension)
 * @return            the new handle, NULL if the resource is invalid or a problem is encountered
 */
codes_handle* codes_bufr_handle_new_from_samples (codes_context* c, const char* sample_name);


/**
*  Clone an existing handle using the context of the original handle,
*  The message is copied and reparsed
*
* @param h           : The handle to be cloned
* @return            the new handle, NULL if the message is invalid or a problem is encountered
*/
codes_handle* codes_handle_clone(codes_handle* h)                 ;

/**
*  Frees a handle, also frees the message if it is not a user message
*  @see  codes_handle_new_from_message
* @param h           : The handle to be deleted
* @return            0 if OK, integer value on error
*/
int codes_handle_delete(codes_handle* h);

/*! \defgroup handling_coded_messages Handling coded messages */
/*! @{ */
/**
* getting the message attached to a handle
*
* @param h              : the handle to which the buffer should be gathered
* @param message        : the pointer to be set to the handle's data
* @param message_length : On exit, the message size in number of bytes
* @return            0 if OK, integer value on error
*/
int codes_get_message(codes_handle* h ,const void** message, size_t *message_length  );

/**
* Get latitude/longitude and data values.
* The Latitudes, longitudes and values arrays must be properly allocated by the caller.
* Their required dimension can be obtained by getting the value of the integer key "numberOfPoints".
*
* @param h           : handle from which geography and data values are taken
* @param lats        : returned array of latitudes
* @param lons        : returned array of longitudes
* @param values      : returned array of data values
* @return            0 if OK, integer value on error
*/
int codes_grib_get_data(codes_handle *h, double *lats, double *lons, double *values);

/**
*  Get the number of coded value from a key, if several keys of the same name are present, the total sum is returned
*
* @param h           : the handle to get the offset from
* @param key         : the key to be searched
* @param size        : the address of a size_t where the size will be set
* @return            0 if OK, integer value on error
*/
int codes_get_size(codes_handle* h, const char* key,size_t *size);

/**
*  Get the length of the string representation of the key, if several keys of the same name are present, the maximum length is returned
*
* @param h           : the handle to get the offset from
* @param key         : the key to be searched
* @param length        : the address of a size_t where the length will be set
* @return            0 if OK, integer value on error
*/
int codes_get_length(codes_handle* h, const char* key,size_t *length);

/**
*  Get a long value from a key, if several keys of the same name are present, the last one is returned
*  @see  codes_set_long
*
* @param h           : the handle to get the data from
* @param key         : the key to be searched
* @param value       : the address of a long where the data will be retrieved
* @return            0 if OK, integer value on error
*/
int codes_get_long(codes_handle* h, const char* key, long*   value  );

/**
*  Get a double value from a key, if several keys of the same name are present, the last one is returned
*  @see  codes_set_double
*
* @param h           : the handle to get the data from
* @param key         : the key to be searched
* @param value       : the address of a double where the data will be retrieved
* @return            0 if OK, integer value on error
*/
int codes_get_double(codes_handle* h, const char* key, double* value                             );

/**
*  Get a string value from a key, if several keys of the same name are present, the last one is returned
* @see  codes_set_string
*
* @param h         : the handle to get the data from
* @param key       : the key to be searched
* @param mesg      : the address of a string where the data will be retrieved
* @param length    : the address of a size_t that contains allocated length of the string on input, and that contains the actual length of the string on output
* @return          0 if OK, integer value on error
*/
int codes_get_string(codes_handle* h, const char* key, char* mesg, size_t *length  );

/**
*  Get string array values from a key. If several keys of the same name are present, the last one is returned
* @see  codes_set_string_array
*
* @param h       : the handle to get the data from
* @param key     : the key to be searched
* @param vals    : the address of a string array where the data will be retrieved
* @param length  : the address of a size_t that contains allocated length of the array on input, and that contains the actual length of the array on output
* @return        0 if OK, integer value on error
*/
int codes_get_string_array(codes_handle* h, const char* key, char** vals, size_t *length);

/**
*  Get raw bytes values from a key. If several keys of the same name are present, the last one is returned
* @see  codes_set_bytes
*
* @param h           : the handle to get the data from
* @param key         : the key to be searched
* @param bytes       : the address of a byte array where the data will be retrieved
* @param length      : the address of a size_t that contains allocated length of the byte array on input, and that contains the actual length of the byte array on output
* @return            0 if OK, integer value on error
*/
int codes_get_bytes(codes_handle* h, const char* key, unsigned char* bytes, size_t *length);

/**
*  Get double array values from a key. If several keys of the same name are present, the last one is returned
* @see  codes_set_double_array
*
* @param h        : the handle to get the data from
* @param key      : the key to be searched
* @param vals     : the address of a double array where the data will be retrieved
* @param length   : the address of a size_t that contains allocated length of the double array on input, and that contains the actual length of the double array on output
* @return         0 if OK, integer value on error
*/
int codes_get_double_array(codes_handle* h, const char* key, double* vals, size_t *length);

/**
*  Get long array values from a key. If several keys of the same name are present, the last one is returned
* @see  codes_set_long_array
*
* @param h           : the handle to get the data from
* @param key         : the key to be searched
* @param vals       : the address of a long array where the data will be retrieved
* @param length      : the address of a size_t that contains allocated length of the long array on input, and that contains the actual length of the long array on output
* @return            0 if OK, integer value on error
*/
int codes_get_long_array(codes_handle* h, const char* key, long* vals, size_t *length);

/**
*  Set a long value from a key. If several keys of the same name are present, the last one is set
*  @see  codes_get_long
*
* @param h           : the handle to set the data to
* @param key         : the key to be searched
* @param val         : a long where the data will be read
* @return            0 if OK, integer value on error
*/
int codes_set_long(codes_handle* h, const char* key, long val);

/**
*  Set a double value from a key. If several keys of the same name are present, the last one is set
*  @see  codes_get_double
*
* @param h           : the handle to set the data to
* @param key         : the key to be searched
* @param val       : a double where the data will be read
* @return            0 if OK, integer value on error
*/
int codes_set_double(codes_handle* h, const char* key, double val);

/**
*  Set a string value from a key. If several keys of the same name are present, the last one is set
*  @see  codes_get_string
*
* @param h           : the handle to set the data to
* @param key         : the key to be searched
* @param mesg       : the address of a string where the data will be read
* @param length      : the address of a size_t that contains the length of the string on input, and that contains the actual packed length of the string on output
* @return            0 if OK, integer value on error
*/
int codes_set_string(codes_handle* h, const char*  key , const char* mesg, size_t *length);

/**
*  Set a bytes array from a key. If several keys of the same name are present, the last one is set
*  @see  codes_get_bytes
*
* @param h           : the handle to set the data to
* @param key         : the key to be searched
* @param bytes       : the address of a byte array where the data will be read
* @param length      : the address of a size_t that contains the length of the byte array on input, and that contains the actual packed length of the byte array  on output
* @return            0 if OK, integer value on error
*/
int codes_set_bytes(codes_handle* h, const char*  key, const unsigned char* bytes, size_t *length);

/**
*  Set a double array from a key. If several keys of the same name are present, the last one is set
*   @see  codes_get_double_array
*
* @param h           : the handle to set the data to
* @param key         : the key to be searched
* @param vals        : the address of a double array where the data will be read
* @param length      : a size_t that contains the length of the byte array on input
* @return            0 if OK, integer value on error
*/
int codes_set_double_array(codes_handle* h, const char* key, const double* vals, size_t length);

/**
*  Set a long array from a key. If several keys of the same name are present, the last one is set
*  @see  codes_get_long_array
*
* @param h           : the handle to set the data to
* @param key         : the key to be searched
* @param vals        : the address of a long array where the data will be read
* @param length      : a size_t that contains the length of the long array on input
* @return            0 if OK, integer value on error
*/
int codes_set_long_array(codes_handle* h, const char* key, const long* vals, size_t length);

/**
*  Frees the cached definition files of the context
*
* @param c           : the context to be deleted
*/
void codes_context_delete(codes_context* c);

/**
*  Turn on support for multiple fields in single GRIB messages
*
* @param c            : the context to be modified
*/
void codes_grib_multi_support_on(codes_context* c);

/**
*  Turn off support for multiple fields in single GRIB messages
*
* @param c            : the context to be modified
*/
void codes_grib_multi_support_off(codes_context* c);

/**
*  Get the API version
*
*  @return        API version
*/
long codes_get_api_version(void);

/*! \defgroup keys_iterator Iterating on keys names
The keys iterator is designed to get the key names defined in a message.
Key names on which the iteration is carried out can be filtered through their
attributes or by the namespace they belong to.
*/
/*! @{ */
/*! Create a new iterator from a valid and initialised handle.
*  @param h             : the handle whose keys you want to iterate
*  @param filter_flags  : flags to filter out some of the keys through their attributes
*  @param name_space    : if not null the iteration is carried out only on
*                         keys belonging to the namespace passed. (NULL for all the keys)
*  @return              keys iterator ready to iterate through keys according to filter_flags
*                       and namespace
*/
codes_keys_iterator* codes_keys_iterator_new(codes_handle* h,unsigned long filter_flags, const char* name_space);

/*! Step to the next item from the keys iterator.
*  @param kiter         : valid codes_keys_iterator
*  @return              1 if next iterator exists, 0 if no more elements to iterate on
*/
int codes_keys_iterator_next(codes_keys_iterator *kiter);


/*! get the key name from the keys iterator
*  @param kiter         : valid codes_keys_iterator
*  @return              key name
*/
const char* codes_keys_iterator_get_name(codes_keys_iterator *kiter);

/*! Delete the keys iterator.
*  @param kiter         : valid codes_keys_iterator
*  @return              0 if OK, integer value on error
*/
int codes_keys_iterator_delete( codes_keys_iterator* kiter);
int codes_get_native_type(codes_handle* h, const char* name,int* type);

