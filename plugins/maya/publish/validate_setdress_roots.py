
import pyblish.api


class ValidateSetDressRoots(pyblish.api.InstancePlugin):
    """Verify setdress has root transform"""

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Validate SetDress Roots"
    families = ["reveries.setdress"]

    def process(self, instance):

        for intf, root in instance.data["setdressRoots"].items():
            if not root:
                raise Exception("Interface {!r} has no transform nodes, "
                                "this is a bug.".format(str(intf)))
