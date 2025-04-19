from unittest.mock import Mock

from . import htypes
from .services import (
    mosaic,
    )
from .code.mark import mark
from .tested.code import ref_list


def test_open():
    piece = ref_list.open_ref_list()
    assert isinstance(piece, htypes.ref_list.model)


@mark.fixture
def file_bundle_factory():
    ref_1_piece = htypes.ref_list_tests.sample_model(id=123)
    storage = htypes.ref_list.storage(
        folders=(
            htypes.ref_list.folder(
                id='folder_1',
                parent_id=None,
                name="Folder 1",
                ),
            htypes.ref_list.folder(
                id='folder_2',
                parent_id=None,
                name="Folder 2",
                ),
            ),
        refs=(
            htypes.ref_list.ref(
                id='ref_1',
                parent_id=None,
                ref=mosaic.put(ref_1_piece),
                ),
            ),
        )
    file_bundle = Mock()
    file_bundle.load_piece.return_value = storage
    return file_bundle


def format_sample_model(piece):
    return f'sample-model({piece.id})'


@mark.config_fixture('formatter_creg')
def formatter_creg_config():
    return {
        htypes.ref_list_tests.sample_model: format_sample_model,
        }


@mark.fixture
def root_model():
    return htypes.ref_list.model(parent_id=None, folder_path=())


@mark.fixture
def folder_2_model():
    return htypes.ref_list.model(parent_id='folder_2', folder_path=('Folder 2',))


def test_root_model(root_model):
    item_list = ref_list.ref_list_model(root_model)
    assert type(item_list) is list
    assert item_list == [
        htypes.ref_list.item('folder_1', 'Folder 1'),
        htypes.ref_list.item('folder_2', 'Folder 2'),
        htypes.ref_list.item('ref_1', 'sample-model(123)'),
        ]


def test_open_folder(root_model, folder_2_model):
    current_key = folder_2_model.parent_id
    piece = ref_list.open(root_model, current_key)
    assert piece == folder_2_model


def test_open_parent(root_model, folder_2_model):
    piece, key = ref_list.open_parent(folder_2_model)
    assert piece == root_model
    assert key == folder_2_model.parent_id


def test_add_root_folder(root_model, file_bundle_factory):
    folder_id = ref_list.add_folder(root_model, 'New folder')
    assert type(folder_id) is str
    file_bundle_factory.save_piece.assert_called_once()


def test_add_ref(folder_2_model, file_bundle_factory):
    ref_2_piece = htypes.ref_list_tests.sample_model(id=456)
    ref_2 = mosaic.put(ref_2_piece)
    ref_id = ref_list.add_ref(folder_2_model, ref_2)
    assert type(ref_id) is str
    file_bundle_factory.save_piece.assert_called_once()


def test_remove_folder(root_model, file_bundle_factory):
    ref_list.remove(root_model, 'folder_1')
    file_bundle_factory.save_piece.assert_called_once()


def test_formatter(folder_2_model):
    text = ref_list.format_model(folder_2_model)
    assert text == "Ref list: /Folder 2/"
