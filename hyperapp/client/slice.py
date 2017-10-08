import bisect
from ..common.htypes import tString, tBool, Field, TRecord, TList, ListInterface
from ..common.list_object import Chunk


class Slice(object):

    @staticmethod
    def data_t(iface):
        return TRecord([
            Field('sort_column_id', tString),
            Field('bof', tBool),
            Field('eof', tBool),
            Field('keys', TList(iface.get_key_type())),
            ])

    def __init__(self, key2element, sort_column_id, bof=False, eof=False, keys=None):
        self.key2element = key2element
        self.sort_column_id = sort_column_id
        self.bof = bof
        self.eof = eof
        self.keys = keys or []

    def __repr__(self):
        return '<%s bof=%s eof=%s %s>' % (self.sort_column_id, self.bof, self.eof, self.keys)

    def __eq__(self, other):
        return (self.sort_column_id == other.sort_column_id and
                self.bof == other.bof and
                self.eof == other.eof and
                self.keys == other.keys)

    def to_data(self, iface):
        assert isinstance(iface, ListInterface), repr(iface)
        return self.data_t(iface)(self.sort_column_id, self.bof, self.eof, self.keys)

    def add_fetched_chunk(self, chunk):
        assert chunk.sort_column_id == self.sort_column_id, repr((chunk.sort_column_id, self.sort_column_id))
        self.key2element.update({element.key: element for element in chunk.elements})
        if chunk.bof:
            assert chunk.from_key is None, repr(chunk.from_key)
            start_idx = 0
            self.bof = True
        else:
            assert chunk.from_key is not None and chunk.from_key in self.keys, repr(chunk.from_key)  # valid from_key is expected for non-bof chunks
            start_idx = self.keys.index(chunk.from_key) + 1
        # elements after this chunk are removed from self.keys
        self.keys = self.keys[:start_idx] + [element.key for element in chunk.elements]
        self.eof = chunk.eof
        return start_idx

    def merge_in_diff(self, diff):
        self.key2element.update({element.key: element for element in diff.elements})
        self.keys = [key for key in self.keys if key not in diff.remove_keys]
        new_key_idx = []
        for element in diff.elements:
            idx = bisect.bisect(self._ordered_elements(self.keys), element.clone_with_sort_column(self.sort_column_id))
            if idx == 0 and not self.bof:
                continue  # before first element - ignore if not bof
            if idx == len(self.keys) and not self.eof:
                continue  # after last element - ignore if not eof
            self.keys.insert(idx, element.key)
            new_key_idx.append(idx)
        return new_key_idx

    def pick_chunk(self, key, desc_count, asc_count):
        if key is None:
            if self.bof:
                idx = 0
            else:
                return None
        else:
            try:
                idx = self.keys.index(key)
            except ValueError:
                return None  # Unknown key
            if idx == len(self.keys) - 1:
                return None  # from key is last element - we need to load next chunk from server
        start = max(0, idx - desc_count)
        end = min(len(self.keys), idx + asc_count)
        if start == 0:
            if self.bof:
                from_key = None
            else:
                from_key = self.keys[start]
                start += 1
        else:
            from_key = self.keys[start - 1]
        keys = self.keys[start:end]
        bof = self.bof and start == 0
        eof = self.eof and end == len(self.keys)
        return Chunk(self.sort_column_id, from_key, self._ordered_elements(keys), bof=bof, eof=eof)

    def _ordered_elements(self, keys ):
        return [self.key2element[key].clone_with_sort_column(self.sort_column_id) for key in keys]


class SliceList(object):

    @staticmethod
    def data_t(iface):
        return TRecord([
            Field('sort_column_id', tString),
            Field('slice_list', TList(Slice.data_t(iface))),
            ])

    def __init__(self, key2element, sort_column_id, slice_list=None):
        self.key2element = key2element
        self.sort_column_id = sort_column_id
        self.slice_list = slice_list or []

    def __repr__(self):
        return '<%r: %r>' % (self.sort_column_id, self.slice_list)

    def __eq__(self, other):
        return (self.sort_column_id == other.sort_column_id and
                self.slice_list == other.slice_list)

    def to_data(self, iface):
        assert isinstance(iface, ListInterface), repr(iface)
        return self.data_t(iface)(self.sort_column_id, [slice.to_data(iface) for slice in self.slice_list])

    # todo: merge intersecting slices to single one
    def add_fetched_chunk(self, chunk):
        if chunk.sort_column_id != self.sort_column_id: return
        has_slice = False
        for slice in self.slice_list:
            if chunk.bof or chunk.from_key in slice.keys:
                slice.add_fetched_chunk(chunk)
                has_slice = True
        if not has_slice:
            slice = Slice(self.key2element, chunk.sort_column_id)
            slice.add_fetched_chunk(chunk)
            self.slice_list.append(slice)

    def merge_in_diff(self, diff):
        for slice in self.slice_list:
            slice.merge_in_diff(diff)

    def pick_chunk(self, sort_column_id, key, desc_count, asc_count):
        if sort_column_id != self.sort_column_id:
            return None
        for slice in self.slice_list:
            chunk = slice.pick_chunk(key, desc_count, asc_count)
            if chunk:
                return chunk
        return None  # none found