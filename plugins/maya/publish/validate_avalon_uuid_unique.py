import pyblish.api
from reveries.maya import action


class ValidateNoDuplicateAvalonUUID(pyblish.api.InstancePlugin):
    """Validate the nodes in the instance have a unique Avalon Id

    validate instance.data:
        avalon_uuid

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.01
    actions = [action.SelectInvalidAction,
               action.GenerateUUIDsOnInvalidAction]
    hosts = ['maya']
    label = 'No Duplicated Avalon UUID'

    def process(self, instance):
        """Process all meshes"""

        # Ensure all nodes have a cbId
        invalid = self.get_invalid_dict(instance)
        if invalid:
            self.log.error(
                "'%s' Nodes found with non-unique asset IDs:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception(
                "%s <No Duplicate Avalon UUID> Failed." % instance)

        self.log.info("%s <No Duplicate Avalon UUID> Passed." % instance)

    @classmethod
    def get_invalid_dict(cls, instance):
        """Return a dictionary mapping of id key to list of member nodes"""
        import copy
        # Collect each id with their members
        ids = copy.deepcopy(instance.data["avalon_uuid"])

        # Skip those without IDs (if everything should have an ID that should
        # be another validation)
        ids.pop("None", None)

        # Take only the ids with more than one member
        invalid = dict((_id, members) for _id, members in ids.iteritems() if
                       len(members) > 1)
        return invalid

    @classmethod
    def get_invalid(cls, instance):
        """Return the member nodes that are invalid"""

        invalid_dict = cls.get_invalid_dict(instance)

        # Take only the ids with more than one member
        invalid = list()
        for members in invalid_dict.itervalues():
            invalid.extend(members)

        return invalid
