from . import (
    BUILTIN_MODULE_NAME,
    TList,
    TRecord,
    tString,
    ref_t,
    )


import_rec_t = TRecord(BUILTIN_MODULE_NAME, 'import_rec', {
    'full_name': tString,
    'resource': ref_t,
    })

imports_t = TRecord(BUILTIN_MODULE_NAME, 'imports', {
    'pyobj': TList(import_rec_t),
    'raw': TList(import_rec_t),
    })

python_module_t = TRecord(BUILTIN_MODULE_NAME, 'python_module', {
    'module_name': tString,
    'source': tString,
    'file_path': tString,
    'imports': imports_t,
    })

import_rec_def_t = TRecord(BUILTIN_MODULE_NAME, 'import_rec_def', {
    'full_name': tString,
    'resource': tString,
    })

imports_def_t = TRecord(BUILTIN_MODULE_NAME, 'imports', {
    'pyobj': TList(import_rec_def_t),
    'raw': TList(import_rec_def_t),
    })

python_module_def_t = TRecord(BUILTIN_MODULE_NAME, 'python_module_def', {
    'module_name': tString,
    'file_name': tString,
    'imports': imports_def_t,
    })
