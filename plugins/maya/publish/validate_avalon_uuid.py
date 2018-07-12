import pyblish.api


class ValidateAvalonUUID(pyblish.api.InstancePlugin):
    """All models ( mesh node's transfrom ) must have an UUID

    validate instance.data:
        avalon_uuid

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Avalon UUID"

    def process(self, instance):
        invalid = instance.data["avalon_uuid"]["None"]
        if invalid:
            self.log.error(
                "'%s' Missing ID attribute on:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <Avalon UUID> Failed." % instance)

        self.log.info("%s <Avalon UUID> Passed." % instance)
