from ..htypes import (
    tString,
    Field,
    OpenCommand,
    Interface,
    register_iface,
    stringColumnType,
    intColumnType,
    Column,
    ElementCommand,
    ElementOpenCommand,
    ListInterface,
    )


module_list_iface = ListInterface(
    'module_list',
    columns=[
        Column('name', stringColumnType),
        Column('id', stringColumnType),
        ],
    commands=[
        OpenCommand('add'),
        ElementCommand('delete'),
        ElementOpenCommand('open'),
        ElementOpenCommand('deps'),
    ],
    key_column='id')

module_form_iface = Interface('module_form', commands=[
    OpenCommand('submit', [Field('name', tString)]),
    ])


module_dep_list_iface = ListInterface(
    'module_deps_list',
    columns=[
        Column('dep_id', type=intColumnType),
        Column('visible_as', stringColumnType),
        Column('id', stringColumnType),
        ],
    commands=[
        ElementCommand('remove'),
    ],
    key_column='dep_id')

available_dep_list_iface = ListInterface(
    'available_deps_list',
    columns=[
        Column('name', stringColumnType),
        Column('id', stringColumnType),
        ],
    commands=[
        ElementCommand('add'),
    ],
    key_column='id')



register_iface(module_list_iface)
register_iface(module_form_iface)
register_iface(module_dep_list_iface)
register_iface(available_dep_list_iface)
