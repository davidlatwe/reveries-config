
import pyblish.api
from reveries.plugins import context_process


class CollectReferencedNamespaces(pyblish.api.InstancePlugin):
    """Collect referenced subsets' namespaces and their content

    Get namespaces of subsets which were loaded by referencing for escaping
    no namespace validation.

    Currently this is for preserving model references on rigging tasks, and
    those namespaces will be stripped in an undoable context while extracting
    the rig.

    If the subset gets imported, it will not be collected, and the namespace
    will need to be removed.

    """

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Referenced Namespaces"
    families = [
        "reveries.rig",
    ]

    @context_process
    def process(self, context):
        from maya import cmds

        referenced_namespace = set()
        referenced_content = set()

        all_containers = dict()
        all_containers.update(context.data["RootContainers"])
        all_containers.update(context.data["SubContainers"])

        for container in all_containers.values():
            if container.get("loader") == "LookLoader":
                # lookDev does not have `subsetGroup`
                continue

            group = container["subsetGroup"]
            members = cmds.sets(container["objectName"], query=True)

            references = cmds.ls(members, type="reference")
            if not references:
                # Imported
                continue

            # Incase referenced member get removed from container by any
            # reason.
            referenced_members = []
            for reference in references:
                referenced_members += cmds.referenceQuery(reference,
                                                          nodes=True)

            members = list(set(members + referenced_members))

            referenced_content.add(group)
            referenced_content.update(cmds.ls(members,
                                              long=True,
                                              referencedNodes=True))

            referenced_namespace.add(container["namespace"])

        context.data["referencedNamespace"] = referenced_namespace
        context.data["referencedNamespaceContent"] = referenced_content
