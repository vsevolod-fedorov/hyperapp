from types import SimpleNamespace
from .htypes import (
    tString,
    Field,
    TRecord,
    TList,
    tPath,
    tIfaceId,
    )
from .hierarchy import THierarchy, TExceptionHierarchy
from .switched import tSwitched, TSwitchedRec


def make_request_types():
    types = SimpleNamespace()

    types.tUpdate = TSwitchedRec(['iface'], fields=[
        Field('iface', tIfaceId),
        Field('path', tPath),
        Field('diff', tSwitched),
        ])

    types.tClientPacket = THierarchy('client_packet')
    types.tClientNotificationRec = TSwitchedRec(['iface', 'command_id'], fields=[
        Field('iface', tIfaceId),
        Field('path', tPath),
        Field('command_id', tString),
        Field('params', tSwitched),
        ])
    types.tClientNotification = types.tClientPacket.register('notification', types.tClientNotificationRec)
    types.tRequest = types.tClientPacket.register('request', TSwitchedRec(base=types.tClientNotificationRec, fields=[
        Field('request_id', tString),
        ]))

    types.tError = TExceptionHierarchy('error')
    types.tErrorRoot = types.tError.register('root')
    types.tClientError = types.tError.register('client_error', base=types.tErrorRoot)
    types.tServerError = types.tError.register('server_error', base=types.tErrorRoot)

    types.tServerPacket = THierarchy('server_packet')
    types.tServerNotification = types.tServerPacket.register('notification', fields=[
        Field('updates', TList(types.tUpdate)),
        ])
    types.tResponseRec = TRecord(base=types.tServerNotification, fields=[
                                Field('iface', tIfaceId),
                                Field('command_id', tString),
                                Field('request_id', tString),
                                ])
    types.tResultResponseRec = TSwitchedRec(['iface', 'command_id'],
                                base=types.tResponseRec, fields=[
                                Field('result', tSwitched),
                                ])
    types.tErrorResponseRec = TRecord(base=types.tResponseRec, fields=[
                                Field('error', types.tError),
                                ])
    types.tResponse = types.tServerPacket.register('response')
    types.tResultResponse = types.tServerPacket.register('result_response', types.tResultResponseRec, base=types.tResponse)
    types.tErrorResponse = types.tServerPacket.register('error_response', types.tErrorResponseRec, base=types.tResponse)
    return types
