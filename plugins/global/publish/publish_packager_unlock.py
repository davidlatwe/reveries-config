
import pyblish.api


class PackagerUnlockVersion(pyblish.api.ContextPlugin):
    """Unlock version directory after subsets have been integrated
    """

    label = "Packager Unlock"
    order = pyblish.api.IntegratorOrder + 0.1

    def process(self, context):

        for instance in context:
            if not instance.data.get("publish", True):
                continue

            packager = instance.data["packager"]
            packager.unlock()
            # (TODO) If publish process stopped by user, version dir will
            #        remain locked since this plugin may not be executed.
            #        To solve this, may require pyblish/pyblish-base#352
            #        be implemented.
