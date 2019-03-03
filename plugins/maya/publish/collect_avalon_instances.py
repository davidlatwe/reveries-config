import pyblish.api
import avalon


class CollectAvalonInstances(pyblish.api.ContextPlugin):
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

    order = pyblish.api.CollectorOrder - 0.3
    hosts = ["maya"]
    label = "Avalon Instances"

    def process(self, context):
        from maya import cmds

        objset_data = list()

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
            if (members is None and
                    "reveries.imgseq" not in cmds.getAttr(objset + ".family")):
                # family `reveries.imgseq` can be empty
                self.log.warning("Skipped empty Set: \"%s\" " % objset)
                continue

            data = avalon.maya.lib.read(objset)
            data["objectName"] = objset
            data["setMembers"] = members

            objset_data.append(data)

        # Sorting instances via using `data.publishOrder` as prim key
        ordering = (lambda data: (data.get("publishOrder", 0),
                                  data["family"],
                                  data["subset"],
                                  data["objectName"],
                                  ))

        for data in sorted(objset_data, key=ordering):
            objset = data["objectName"]
            members = data.pop("setMembers")

            # For dependency tracking
            data["dependencies"] = dict()
            data["futureDependencies"] = dict()

            # Create the instance
            self.log.info("Creating instance for {}".format(objset))
            instance = context.create_instance(data["subset"])
            instance[:] = cmds.ls(members, long=True)
            instance.data.update(data)

            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info("Found: \"%s\" " % instance.name)

        return context
