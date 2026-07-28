from . import (
    BUILTIN_MODULE_NAME,
    TRecord,
    tString,
    tBinary,
    )


file_data_t = TRecord(BUILTIN_MODULE_NAME, 'file_data', {
    'data': tBinary,
    })


file_data_def_t = TRecord(BUILTIN_MODULE_NAME, 'file_data_def', {
    'file_name': tString,
    })
