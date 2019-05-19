from collections import namedtuple
from contextlib import contextmanager
from enum import Enum
from functools import wraps
import inspect
import logging

import better_contextvars as contextvars

_log = logging.getLogger(__name__)


class RecordKind(Enum):
    LEAF = 1
    ENTER = 2
    EXIT = 3


class LogRecord(namedtuple('LogRecord', 'kind context name params')):

    def with_kind(self, kind):
        return LogRecord(kind, self.context, self.name, self.params)

    def with_context(self, context):
        return LogRecord(self.kind, context[:], self.name, self.params)


def _make_record(name, params, kind=RecordKind.LEAF, context=None):
    return LogRecord(kind, context[:] if context else [], name, params)


def _exit_record(context, params=None):
    return _make_record(None, params or {}, RecordKind.EXIT, context)


def _filter_params(params):
    return {name: value for name, value in params.items()
            if name != 'self' and value is not None}


class _LogFnAdapter:

    def __init__(self):
        pass

    def __getattr__(self, name):
        return _LoggerAdapter(name)

    def __call__(self, *args, **kw):
        assert len(args) == 1 and not kw and callable(args[0])
        fn = args[0]
        sig = inspect.signature(fn)
        default_params = {
            name: parameter.default
            for name, parameter in sig.parameters.items()
            if parameter.default is not inspect.Parameter.empty
            }
        param_names = list(sig.parameters)

        @wraps(fn)
        def wrapper(*args, **kw):
            args_params = {
                param_names[idx]: arg
                for idx, arg in enumerate(args)
                }
            params = {**default_params, **args_params, **kw}
            record = _make_record(fn.__qualname__, _filter_params(params), kind=RecordKind.ENTER)
            logger = _Logger.get_instance()
            if logger:
                logger.enter_context(record)
            try:
                return fn(*args, **kw)
            finally:
                if logger:
                    logger.exit_context()

        return wrapper


log = _LogFnAdapter()


class _LoggerAdapter:

    def __init__(self, record_name):
        self._record_name = record_name

    def __call__(self, **kw):
        record = _make_record(self._record_name, _filter_params(kw))
        logger = _Logger.get_instance()
        if logger:
            logger.add_entry(record)
        return _ContextAdapter()


class _ContextAdapter:

    def __init__(self):
        pass

    def __enter__(self):
        logger = _Logger.get_instance()
        if logger:
            logger.push_context()

    def __exit__(self, exc, value, tb):
        logger = _Logger.get_instance()
        if logger:
            logger.exit_context()


class _Logger:

    instance = None
    _inside_storage = contextvars.ContextVar('logger_context', default=False)
    _context_var = contextvars.ContextVar('logger_context', default=None)
    _pending_record = contextvars.ContextVar('logger_pending_record', default=None)

    @classmethod
    def get_instance(cls):
        if cls._inside_storage.get():
            return None
        else:
            return cls.instance

    def __init__(self, storage):
        self._storage = storage
        self._context_counter = 0

    def add_entry(self, record):
        self._log('add_entry: %r', record)
        self.flush()
        self._pending_record.set(record.with_context(self._context))

    def push_context(self):
        self._log('push_context')
        assert self._pending_record.get()
        record = self._pending_record.get()
        self._pending_record.set(None)
        self._context_counter += 1
        self._context.append(self._context_counter)
        assert self._context
        self._store_record(
            record
            .with_kind(RecordKind.ENTER)
            .with_context(self._context))

    def enter_context(self, record):
        self.add_entry(record)
        self.push_context()

    def exit_context(self):
        self._log('exit_context')
        self.flush()
        assert self._context
        self._store_record(_exit_record(self._context))
        self._context.pop()

    def flush(self):
        if self._pending_record.get():
            self._store_record(self._pending_record.get())
            self._pending_record.set(None)

    @property
    def _context(self):
        context = self._context_var.get()
        if context is None:
            context = []
            self._context_var.set(context)
        return context

    def _store_record(self, record):
        self._log('store record: %r', record)
        self._inside_storage.set(True)
        try:
            self._storage.add_record(record)
        finally:
            self._inside_storage.set(False)

    def _log(self, format, *args):
        _log.debug('  logger (context=%r pending=%r) ' + format, self._context, self._pending_record.get(), *args)


def init_logger(storage):
    _Logger.instance = _Logger(storage)


def close_logger():
    logger = _Logger.instance
    _Logger.instance = None
    logger.flush()
