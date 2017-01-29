import os.path
import glob
import logging
from ..common.util import encode_path
from ..common.htypes import (
    tString,
    tBool,
    TOptional,
    TList,
    Field,
    TRecord,
    tResource,
    tResourceList,
    )
from ..common.packet_coders import packet_coders

log = logging.getLogger(__name__)


command_rec_t = TRecord([
    Field('is_default', tBool),
    Field('text', tString),
    Field('description', tString),
    Field('shortcuts', TList(tString)),
    ])

column_rec_t = TRecord([
    Field('text', tString),
    Field('description', TOptional(tString)),
    ])

interface_resources_t = TRecord([
    Field('commands', TOptional(TList(command_rec_t))),
    Field('columns', TOptional(TList(column_rec_t))),
    ])


class ResourcesLoader(object):

    def __init__( self, dir_map ):
        self._dir_map = dir_map  # resource prefix -> dir

    def load_resources( self, resource_id ):
        dir = self._dir_map.get(resource_id[0])
        assert dir, 'Unknown resource type: %r' % resource_id[0]
        log.info('loading resources for %r from %r', encode_path(resource_id), dir)
        for fpath in glob.glob(os.path.join(dir, '%s.resources.*.yaml' % resource_id[1])):
            locale = fpath.split('.')[-2]
            log.info('  found resources for locale %r' % locale)
            with open(fpath, 'rb') as f:
                localeResources =  packet_coders.decode('yaml', f.read(), tLocaleResources)
                yield tResources(resource_id, locale, localeResources)
