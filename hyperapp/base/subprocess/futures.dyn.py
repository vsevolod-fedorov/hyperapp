from concurrent.futures import Future


_process_id_to_future = {}


def get_process_future(process_id):
    future = Future()
    _process_id_to_future[process_id] = future
    return future
