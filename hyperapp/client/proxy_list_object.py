import bisect
from ..common.htypes import TList
from .list_object import ListDiff, Element, Slice, ListObject
from .proxy_object import ProxyObject
from .proxy_registry import proxy_class_registry


class ProxyListObject(ProxyObject, ListObject):

    def __init__( self, server, path, iface ):
        ProxyObject.__init__(self, server, path, iface)
        ListObject.__init__(self)
        self._default_sort_column_id = None
        self._slices = []  # all slices are stored in ascending order, actual/up-do-date
        self._slices_from_cache = {}  # key_column_id -> Slice list, slices loaded from cache, out-of-date
        self._subscribed = True

    @staticmethod
    def get_objimpl_id():
        return 'list'

    def set_contents( self, contents ):
        ProxyObject.set_contents(self, contents)
        slice = self._slice_from_data(contents.slice)
        self._default_sort_column_id = slice.sort_column_id
        self._merge_in_slice(slice)

    # By default we assume this object was returned from server, and thus is already subscribed,
    # and we do not want redundant call to server with 'subscribe' request.
    # If this method is called it means that assumption is not true, and we are not actually subscribed yet;
    # then 'subscribe' command will be issued on first fetch_elements call.
    def server_subscribe( self ):
        self._subscribed = False

    def get_default_sort_column_id( self ):
        assert self._default_sort_column_id  # there were no set_contents calls
        return self._default_sort_column_id

    def _slice_from_data( self, rec ):
        return Slice.from_data(self.get_key_column_id(), rec)

    def _merge_in_slice( self, new_slice ):
        print '  -- merge_in_slice', id(self), repr(new_slice.from_key), len(new_slice.elements), new_slice.bof
        if new_slice.elements: print '      ', repr(new_slice.elements[0].key), repr(new_slice.elements[-1].key)
        for slice in self._slices:
            if slice.sort_column_id != new_slice.sort_column_id: continue
            assert new_slice.direction == 'asc'  # todo: desc direction
            if new_slice.from_key == slice.elements[-1].key:
                assert not new_slice.bof  # this is continuation for existing slice, bof is not possible
                slice.elements.extend(new_slice.elements)
                slice.eof = new_slice.eof
                print '     > merged', len(slice.elements), repr(slice.elements[0].key), repr(slice.elements[-1].key)
                break
        else:
            self._slices.append(new_slice)
            print '     > added'
        self._store_slices_to_cache(new_slice.sort_column_id)

    def _update_slices( self, diff ):
        for slice in self._slices:
            for idx in reversed(range(len(slice.elements))):
                element = slice.elements[idx]
                if diff.start_key <= element.key and element.key <= diff.end_key:
                    del slice.elements[idx]
                    print '-- slice with sort %r: element is deleted at %d' % (slice.sort_column_id, idx)
            for new_elt in diff.elements:
                new_elt = new_elt.clone_with_sort_column(slice.sort_column_id)
                for idx in range(len(slice.elements)):
                    assert len(diff.elements) <= 1, len(diff.elements)  # inserting more than one elements at once is not yet supported
                    order_key = slice.elements[idx].order_key
                    if idx == 0:
                        if new_elt.order_key <= order_key and slice.bof:
                            slice.elements.insert(0, new_elt)
                            print '-- slice with sort %r: element is inserted to begin of slice' % slice.sort_column_id
                            break
                    else:
                        prev_order_key = slice.elements[idx - 1].order_key
                        if prev_order_key <= new_elt.order_key and new_elt.order_key <= order_key:
                            slice.elements.insert(idx, new_elt)
                            print '-- slice with sort %r: element is inserted at idx %d' % (slice.sort_column_id, idx)
                            break
                if slice.elements:
                    order_key = slice.elements[-1].order_key
                    if new_elt.order_key > order_key and slice.eof:
                        slice.elements.append(new_elt)
                        print '-- slice with sort %r: element is appended to the end of slice' % slice.sort_column_id
                    

    def _pick_slice( self, slices, sort_column_id, from_key, direction ):
        print '  -- pick_slice', id(self), repr(sort_column_id), repr(from_key), direction
        assert direction == 'asc'  # todo: desc direction
        for slice in slices:
            if slice.sort_column_id != sort_column_id: continue
            if from_key == None and slice.bof:
                print '     > bof found', len(slice.elements)
                return slice
            print '       - checking', len(slice.elements), repr(slice.elements[0].order_key), repr(slice.elements[-1].order_key)
            # here we assume sort_column_id == key_column_id:
            if slice.elements[0].order_key <= from_key and from_key <= slice.elements[-1].order_key:
                idx = bisect.bisect_left(slice.elements, from_key)  # must be from_order_key
                print '     - bisecting', idx
                while slice.elements[idx].order_key <= from_key:  # from_order_key
                    idx += 1
                    if slice.elements[idx-1].key == from_key: break  # from_order_key
                print '     - exact key', idx
                if idx < len(slice.elements):
                    print '     > middle found', idx, len(slice.elements), len(slice.elements[idx:])
                    return slice.clone_with_elements(slice.elements[idx:])
        print '     > none found'
        return None  # none found

    def _get_slice_cache_key( self, sort_column_id ):
        return self.make_cache_key('slices-%s' % sort_column_id)

    def _get_slices_cache_type( self ):
        return TList(self.iface.tSlice())

    def _store_slices_to_cache( self, sort_column_id ):
        key = self._get_slice_cache_key(sort_column_id)
        slices = [slice.to_data(self.iface) for slice in self._slices if slice.sort_column_id == sort_column_id]
        self.cache.store_value(key, slices, self._get_slices_cache_type())

    def _load_slices_from_cache( self, sort_column_id ):
        if sort_column_id in self._slices_from_cache: return  # already loaded
        key = self._get_slice_cache_key(sort_column_id)
        slice_recs = self.cache.load_value(key, self._get_slices_cache_type())
        self._slices_from_cache[sort_column_id] = map(self._slice_from_data, slice_recs or [])

    def put_back_slice( self, slice ):
        print '-- proxy put_back_slice', self, len(slice.elements)
        assert isinstance(slice, Slice), repr(slice)
        self._merge_in_slice(slice)

    def process_update( self, diff ):
        print '-- proxy process_update', self, diff, diff.start_key, diff.end_key, diff.elements
        key_column_id = self.get_key_column_id()
        diff = ListDiff.from_data(key_column_id, diff)
        self._update_slices(diff)
        self._notify_diff_applied(diff)

    def get_columns( self ):
        return self.iface.columns

    def get_key_column_id( self ):
        return self.iface.key_column

    def fetch_elements( self, sort_column_id, from_key, direction, count ):
        print '-- proxy fetch_elements', self, self._subscribed, repr(from_key), count
        slice = self._pick_slice(self._slices, sort_column_id, from_key, direction)
        if slice:
            print '   > cached actual', len(slice.elements)
            # return result even if it is stale, for faster gui response, will refresh when server response will be available
            self._notify_fetch_result(slice)
            if self._subscribed:
                return  # otherwise our cache may already be invalid, need to subscribe and refetch anyway
        self._load_slices_from_cache(sort_column_id)
        cached_slices = self._slices_from_cache.get(sort_column_id, [])
        slice = self._pick_slice(cached_slices, sort_column_id, from_key, direction)
        if slice:
            print '   > cached outdated', len(slice.elements)
            self._notify_fetch_result(slice)
            # and subscribe/fetch anyway
        print '   > not cached or not subscribed, requesting'
        if self._subscribed:
            command_id = 'fetch_elements'
        else:
            command_id = 'subscribe_and_fetch_elements'
            # several views can call fetch_elements before response is received, and we do not want several subscribe_and... calls
            # yet a subscribe_... call can fail... todo
            self._subscribed = True
        self.execute_request(command_id, None, sort_column_id, from_key, direction, count)

    def process_response_result( self, command_id, result ):
        if command_id == 'subscribe_and_fetch_elements':
            self.process_subscribe_and_fetch_elements_result(result)
        elif command_id == 'fetch_elements':
            self.process_fetch_elements_result(result)
        else:
            ProxyObject.process_response_result(self, command_id, result)

    def process_subscribe_and_fetch_elements_result( self, result ):
        print '-- proxy process_subscribe_and_fetch_elements_result', self, len(result.slice.elements)
        ProxyObject.set_contents(self, result)
        self._process_fetch_elements_result(result)
        self._notify_object_changed()

    def process_fetch_elements_result( self, result ):
        print '-- proxy process_fetch_elements_result', self, len(result.slice.elements)
        self._process_fetch_elements_result(result)

    def _process_fetch_elements_result( self, result ):
        slice = self._slice_from_data(result.slice)
        self._merge_in_slice(slice)
        self._notify_fetch_result(slice)

    def __del__( self ):
        print '~ProxyListObject', self, self.path


proxy_class_registry.register(ProxyListObject)
