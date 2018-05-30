/*
 * declarations from grib_api.h
 */

typedef struct grib_handle    grib_handle;
typedef struct grib_context   grib_context;

const char* grib_get_error_message(int code);
int grib_get_gaussian_latitudes(long truncation,double* latitudes);

#define GRIB_SUCCESS		0
#define GRIB_END_OF_FILE		-1
#define GRIB_END_OF_INDEX		-43

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


/*
 * declarations from eccodes.h
 */

typedef struct grib_handle            codes_handle;
typedef struct grib_context           codes_context;
typedef struct grib_keys_iterator     codes_keys_iterator;
typedef struct grib_index             codes_index;

codes_index* codes_index_new_from_file(codes_context* c, char* filename,const char* keys,int *err);
int codes_index_get_size(codes_index* index,const char* key,size_t* size);
int codes_index_get_long(codes_index* index,const char* key,long* values,size_t *size);
int codes_index_get_double(codes_index* index,const char* key, double* values,size_t *size);
int codes_index_get_string(codes_index* index,const char* key,char** values,size_t *size);
int codes_index_select_long(codes_index* index,const char* key,long value);
int codes_index_select_double(codes_index* index,const char* key,double value);
int codes_index_select_string(codes_index* index,const char* key,char* value);
codes_handle* codes_handle_new_from_index(codes_index* index,int *err);
void codes_index_delete(codes_index* index);

int codes_get_message(codes_handle* h ,const void** message, size_t *message_length  );
int codes_write_message(codes_handle* h,const char* file,const char* mode);
codes_handle* codes_grib_handle_new_from_samples (codes_context* c, const char* sample_name);

int codes_handle_delete(codes_handle* h);
int codes_grib_get_data(codes_handle *h, double *lats, double *lons, double *values);
int codes_get_size(codes_handle* h, const char* key,size_t *size);
int codes_get_length(codes_handle* h, const char* key,size_t *length);
int codes_get_string_array(codes_handle* h, const char* name, char** val, size_t *length);
int codes_get_double_array(codes_handle* h, const char* key, double* vals, size_t *length);
int codes_get_long_array(codes_handle* h, const char* key, long* vals, size_t *length);

int codes_set_long(codes_handle* h, const char* key, long val);
int codes_set_double(codes_handle* h, const char* key, double val);
int codes_set_string(codes_handle* h, const char*  key , const char* mesg, size_t *length);
int codes_set_double_array(codes_handle* h, const char* key, const double* vals, size_t length);

int codes_get_native_type(codes_handle* h, const char* name,int* type);

codes_keys_iterator* codes_keys_iterator_new(codes_handle* h,unsigned long filter_flags, const char* name_space);
int codes_keys_iterator_next(codes_keys_iterator *kiter);
const char* codes_keys_iterator_get_name(codes_keys_iterator *kiter);
int codes_keys_iterator_delete( codes_keys_iterator* kiter);
/*
 * definitions from grib_api_prototypes.h
 */

grib_handle* grib_new_from_file(grib_context *c, FILE *f, int headers_only, int *error);

