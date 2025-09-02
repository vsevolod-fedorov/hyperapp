import logging
import traceback
from collections import defaultdict
from itertools import groupby

from hyperapp.boot.htypes import Type, HException
from hyperapp.boot.config_key_error import ConfigKeyError
from hyperapp.boot.resource.python_module import PythonModuleResourceImportError

from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    web,
    )
from .code.config_ctl import (
    item_pieces_to_data,
    merge_system_config_pieces,
    service_pieces_to_config,
    )
from .code.import_recorder import IncompleteImportedObjectError, ImportRecorder
from .code.system import UnknownServiceError
from .code.config_layer import MemoryConfigLayer
from .code.config_item_resource import ConfigItemResource
from .code.cfg_item_req import CfgItemReq
from .code.service_req import ServiceReq
from .code.service_ctr import ServiceTemplateCtr
from .code.system_probe import SystemProbe
from .code.requirement_factory import RequirementFactory
from .code.job_result import JobResult

log = logging.getLogger(__name__)


class SystemJobResult(JobResult):

    @staticmethod
    def _resolve_reqirement_refs(rc_requirement_creg, requirement_refs):
        return set(
            rc_requirement_creg.invite(ref)
            for ref in requirement_refs
            )

    def __init__(self, status, used_reqs, error=None, traceback=None):
        super().__init__(status, error, traceback)
        self._used_reqs = used_reqs

    def _resolve_requirements(self, target_factory, requirements):
        req_to_target = {}
        for req in requirements:
            target = req.get_target(target_factory)
            req_to_target[req] = target
        return req_to_target


class Result:

    def __init__(self, module_name, error_msg=None, traceback=None, missing_reqs=None):
        self._module_name = module_name
        self._error_msg = error_msg
        self._traceback = traceback or []
        self._missing_reqs = missing_reqs or set()

    def _imports_to_requirements(self, import_set):
        req_set = set()
        for import_path in import_set:
            req = RequirementFactory(self._module_name).requirement_from_import(import_path)
            if req:
                req_set.add(req)
        return req_set

    def _missing_requirements(self, recorder):
        if recorder:
            import_reqs = self._imports_to_requirements(recorder.missing_imports)
        else:
            import_reqs = set()
        return self._missing_reqs | import_reqs

    def _used_system_reqs(self, key_to_req, system):
        if not system:
            return set()
        result = set()
        for key in system.used_keys:
            req = key_to_req.get(key)
            # assert req, key
            if req:
                result.add(req)
        return result

    def _used_requirements(self, recorder, key_to_req, system):
        if recorder:
            import_reqs = self._imports_to_requirements(recorder.used_imports)
        else:
            import_reqs = set()
        system_reqs = self._used_system_reqs(key_to_req, system)
        return set(req for req in system_reqs | import_reqs if not req.is_builtin)

    def _constructors(self, system):
        ctr_collector = system['ctr_collector']
        return ctr_collector.constructors


class SystemJob:

    @staticmethod
    def req_to_resources_from_pieces(rc_requirement_creg, rc_resource_creg, req_to_resource):
        req_to_resources = defaultdict(set)
        for rec in req_to_resource:
            req = rc_requirement_creg.invite(rec.requirement)
            resource = rc_resource_creg.invite(rec.resource)
            req_to_resources[req].add(resource)
        return dict(req_to_resources)

    def __init__(self, rc_config, python_module_src, req_to_resources):
        self._rc_config = rc_config
        self._src = python_module_src
        self._req_to_resources = req_to_resources
        self._tested_modules = []

    @property
    def req_to_resources(self):
        return self._req_to_resources

    @property
    def _req_to_resource_pieces(self):
        return tuple(
            htypes.system_job.req_to_resource(
                requirement=mosaic.put(req.piece),
                resource=mosaic.put(resource.piece),
                )
            for req, resource_set in self._req_to_resources.items()
            for resource in resource_set
            )

    def _make_key_to_req_map(self, cfg_item_creg):
        result = {}
        for req, resource_set in self._req_to_resources.items():
            for resource in resource_set:
                for service_name, item_list in resource.system_config_items.items():
                    for item_piece in item_list:
                        key, item = cfg_item_creg.animate(item_piece)
                        result[(service_name, key)] = req
                for service_name, item_list in resource.system_config_items_override.items():
                    for item_piece in item_list:
                        key, item = cfg_item_creg.animate(item_piece)
                        result[(service_name, key)] = req
        return result

    def _resource_group(self, resource):
        if resource.is_system_resource:
            return 0
        if resource.is_service_resource:
            return 1
        return 2

    def _compose_resources_config(self, system, resource_list):
        service_to_items = defaultdict(list)
        for resource in resource_list:
            for service_name, item_list in resource.system_config_items.items():
                service_to_items[service_name] += item_list
        # We expect that later resource items will override former ones.
        for resource in resource_list:
            for service_name, item_list in resource.system_config_items_override.items():
                service_to_items[service_name] += item_list
        service_to_config_piece = {
            service_name: item_pieces_to_data(item_list)
            for service_name, item_list in service_to_items.items()
            }
        return service_pieces_to_config(service_to_config_piece)

    def _configure_system(self, system, resource_list):
        sorted_resource_list = sorted(resource_list, key=self._resource_group)
        for resource in sorted_resource_list:
            resource.configure_system(system)

    def _prepare_system(self, resources):
        for res in resources:
            self._tested_modules += res.tested_modules
        system = SystemProbe()
        resources_config = self._compose_resources_config(system, resources)
        config = merge_system_config_pieces(self._rc_config, resources_config)
        system.load_static_config(config)
        system.load_config_layer('memory', MemoryConfigLayer(system))
        system.set_default_layer('memory')
        self._configure_system(system, resources)
        system.migrate_globals()
        _ = system.resolve_service('marker_registry')  # Init markers.
        return system

    def _init_recorder(self, system, recorder_piece):
        ImportRecorder.configure_pyobj_creg(system)
        return pyobj_creg.animate(recorder_piece)

    _system_files = {
        'rc/system_job',
        'rc/test_job',
        'system/system',
        'rc/system_probe',
        'rc/fixture_probe',
        'asyncio/runners',
        'asyncio/base_events',
        }

    def _prepare_traceback(self, x):
        traceback_entries = []
        cause = x
        while cause:
            traceback_entries += traceback.extract_tb(cause.__traceback__)
            last_cause = cause
            cause = cause.__cause__
        for idx, entry in enumerate(traceback_entries):
            if entry.name == 'exec_module':
                del traceback_entries[:idx + 1]
                break
        for idx, entry in enumerate(traceback_entries):
            fpath = entry.filename.split('/')[-2:]
            fname = '/'.join(fpath).replace('.py', '').replace('.dyn', '')
            if fname not in self._system_files:
                del traceback_entries[:idx]
                break
        line_list = traceback.format_list(traceback_entries)
        if isinstance(last_cause, htypes.rpc.server_error):
            for entry in last_cause.traceback:
                line_list += [line + '\n' for line in entry.splitlines()]
        if isinstance(last_cause, SyntaxError):
            line = f'  File "{last_cause.filename}", line {last_cause.lineno}\n{last_cause.text}'
            line_list.append(line)
        return line_list

    def _raise_error(self, x, module_name=None):
        if not module_name:
            module_name = self._src.name
        traceback_lines = self._prepare_traceback(x)
        if isinstance(x, htypes.rpc.server_error):
            message = x.message
        else:
            message = str(x)
        error_msg = f"{type(x).__name__}: {message}"
        if isinstance(x, IncompleteImportedObjectError):
            req = RequirementFactory(module_name).requirement_from_import(x.path)
            self.incomplete_error(module_name, error_msg, traceback_lines[:-1], missing_reqs={req})
        else:
            self.failed_error(module_name, error_msg, traceback_lines)

    def _raise_import_error(self, x):
        self._raise_error(x.original_error)

    def convert_errors(self, fn, *args, **kw):
        module_name = self._src.name
        try:
            return fn(*args, **kw)
        except HException as x:
            error_msg = f"{type(x).__name__}: {x}"
            if isinstance(x, htypes.rc_job.unknown_service_error):
                req = ServiceReq(x.service_name)
                self.incomplete_error(module_name, error_msg, missing_reqs={req})
            if isinstance(x, htypes.rc_job.config_key_error):
                key = web.summon(x.key)
                req = CfgItemReq(x.service_name, key, self._tested_modules)
                if not req.is_type_error:
                    self._raise_error(x)  # Do not treat data registry miss as incomplete jobs.
                self.incomplete_error(module_name, error_msg, missing_reqs={req})
            self._raise_error(x)
        except PythonModuleResourceImportError as x:
            self._raise_import_error(x)
        except UnknownServiceError as x:
            req = ServiceReq(x.service_name)
            error_msg = f"{type(x).__name__}: {x}"
            self.incomplete_error(module_name, error_msg, missing_reqs={req})
        except ConfigKeyError as x:
            if not isinstance(x.key, Type):
                self._raise_error(x)  # Do not treat data registry miss as incomplete jobs.
            req = CfgItemReq.from_actor(x.service_name, x.key, self._tested_modules)
            error_msg = f"{type(x).__name__}: {x}"
            self.incomplete_error(module_name, error_msg, missing_reqs={req})
        except IncompleteImportedObjectError as x:
            if list(x.path[:1]) == ['htypes']:
                path = '.'.join(x.path)
                error_msg = f"Unknown type: {path}" 
                traceback = self._prepare_traceback(x)[:-1]
                self.failed_error(module_name, error_msg, traceback)
            else:
                self._raise_error(x)
        except BaseException as x:
            self._raise_error(x)
