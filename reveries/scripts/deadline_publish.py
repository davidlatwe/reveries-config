
import pyblish.api
import reveries.lib

if __name__ == "__main__":
    # Script job
    pyblish.api.register_host("deadline")
    pyblish.api.register_target("localhost")
    reveries.lib.publish_remote()
