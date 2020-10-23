
import pyblish.api


class ValidateBypassed(pyblish.api.InstancePlugin):
    """Ensure ROP node not set to 'bypass'
    """

    order = pyblish.api.ValidatorOrder - 0.1
    families = ["*"]
    hosts = ["houdini"]
    label = "Validate ROP Bypass"

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            rop = invalid[0]
            raise RuntimeError(
                "ROP node %s is set to bypass, publishing cannot continue.." %
                rop.path()
            )

    @classmethod
    def get_invalid(cls, instance):
        if len(instance):
            rop = instance[0]
            if rop and rop.isBypassed():
                return [rop]
