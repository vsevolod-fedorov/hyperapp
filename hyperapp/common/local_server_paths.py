import os.path


LOCAL_HREF_RESOLVER_URL_PATH = '~/.local/share/hyperapp/common/local_href_resolver.url'
LOCAL_SERVER_HREF_LIST_URL_PATH = '~/.local/share/hyperapp/common/local_server_href_list.url'


def save_url_to_file(url_with_routes, path):
    url_path = os.path.expanduser(path)
    dir = os.path.dirname(url_path)
    if not os.path.isdir(dir):
        os.makedirs(dir)
    with open(url_path, 'w') as f:
        f.write(url_with_routes.to_str())
    return url_path
