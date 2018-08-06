import pyblish.api
import avalon


class CollectMayaInstances(pyblish.api.ContextPlugin):
    """Gather instances by objectSet and pre-defined attribute

    This collector takes into account assets that are associated with
    an objectSet and marked with a unique identifier;

    Identifier:
        id (str): "pyblish.avalon.instance"

    Limitations:
        - Does not take into account nodes connected to those
            within an objectSet. Extractors are assumed to export
            with history preserved, but this limits what they will
            be able to achieve and the amount of data available
            to validators.

    """

    order = pyblish.api.CollectorOrder - 0.49
    hosts = ["maya"]
    label = "Avalon Instances"

    def process(self, context):
        from maya import cmds

        for objset in cmds.ls("*.id",
                              long=True,            # Produce full names
                              type="objectSet",     # Only consider objectSets
                              recursive=True,       # Include namespace
                              objectsOnly=True):    # Return objectSet, rather
                                                    # than its members
            # verify objectSet has valid id
            if cmds.getAttr(objset + ".id") != "pyblish.avalon.instance":
                self.log.debug("Skipped non-avalon Set: \"%s\" " % objset)
                continue

            try:
                if not cmds.getAttr(objset + ".active"):
                    continue
            except ValueError:
                # objectSet has no active switch
                pass

            # The developer is responsible for specifying
            # the family of each instance.
            has_family = cmds.attributeQuery("family",
                                             node=objset,
                                             exists=True)
            assert has_family, "\"%s\" was missing a family" % objset

            # verify objectSet has members to collect
            members = cmds.sets(objset, query=True)
            if members is None:
                self.log.warning("Skipped empty Set: \"%s\" " % objset)
                continue

            data = avalon.maya.lib.read(objset)

            # Create the instance
            self.log.info("Creating instance for {}".format(objset))
            name = cmds.ls(objset, long=False)[0]   # use short name
            instance = context.create_instance(data.get("name", name))
            instance[:] = members
            instance.data.update(data)

            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info("Found: \"%s\" " % instance.data["name"])

        context[:] = sorted(context)

        return context
