
import pyblish.api
import reveries.lib


def __main__(*args):
    # Post job script
    pyblish.api.register_host("deadline")
    reveries.lib.publish_remote()


if __name__ == "__main__":
    # Script job per frame
    pyblish.api.register_host("deadline")
    pyblish.api.register_target("distributed")

    # package path
    # fileNodeAttrs
    # Frame range
