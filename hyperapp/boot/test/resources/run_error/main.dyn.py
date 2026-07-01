def main(args):
    fn(args[0])


def fn(value):
    assert False, f'sample-error:{value}'
