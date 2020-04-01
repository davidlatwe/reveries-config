
import avalon.api
import pyblish.api
from reveries import filesys, lib


if __name__ == "__main__":

    avalon.api.install(filesys)
    pyblish.api.register_target("localhost")
    lib.publish_remote()
