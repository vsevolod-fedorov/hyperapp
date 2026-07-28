def compile_resources():
    print("rc compile resources")


def main(args, compile_resources, subprocess_running, identity_creg):
    print("rc main service:", args)
    print("subprocess_running:", subprocess_running)
    print("identity_creg:", identity_creg)
    compile_resources()
    with subprocess_running('sample', None):
        print("subprocess is running")
    print("subprocess is finished")
