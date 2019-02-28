
import os

from maya import cmds, mel
from xgenm.xmaya import xgmSplinePreset


def list_lead_descriptions(nodes):
    """Filter out XGen IGS lead descriptions from nodes

    Args:
        nodes (list): A list of node names

    Return:
        (list): A list of lead description shape nodes

    """
    nodes += cmds.listRelatives(nodes,
                                allDescendents=True,
                                fullPath=True) or []
    description_member = {
        desc: cmds.ls(cmds.listHistory(desc),
                      type="xgmSplineDescription",
                      long=True)
        for desc in cmds.ls(nodes, type="xgmSplineDescription", long=True)
    }

    lead_descriptions = list(description_member.keys())
    # Filtering
    for description, member in description_member.items():
        if len(member) == 1:
            continue

        for sub in member[1:]:
            if sub in lead_descriptions:
                lead_descriptions.remove(sub)

    return lead_descriptions


def list_bound_meshes(description):
    """Return bounded meshes of the XGen IGS description node

    Args:
        description (str): XGen IGS description shape node

    Return:
        (list): A list of bounded mesh name

    """
    return cmds.xgmSplineQuery(description, listBoundMeshes=True)


def find_spline_base(description):
    """Return the xgmSplineBase node of the description

    Args:
        description (str): description shape node name

    Return:
        (str): xgmSplineBase node name

    Raise:
        Exception: If description has no xgmSplineBase child node

    """
    bases = cmds.ls(cmds.listHistory(description),
                    type="xgmSplineBase",
                    long=True)

    if not bases:
        raise Exception("SplineDescription {!r} does not have xgmSplineBase, "
                        "this is not right.".format(description))

    if len(bases) == 1:
        return bases[0]

    descriptions = cmds.ls(cmds.listHistory(description),
                           type="xgmSplineDescription",
                           long=True)

    for sub_desc in descriptions[1:]:
        sub_base = find_spline_base(sub_desc)
        # Remove sub-description's splineBase node
        bases.remove(sub_base)

    return bases[0]


def compose_bbox_data(description):
    """Compute bounded meshes' bounding box data for preset

    Args:
        description (str): description shape node name

    Return:
        (str): Bounded meshes' bounding box data

    """
    spline_base = find_spline_base(description)
    connections = cmds.listConnections(spline_base,
                                       plugs=True,
                                       source=True,
                                       destination=False,
                                       connections=True)

    bounding_box = ""
    for src, dst in zip(connections[::2], connections[1::2]):
        if not src.startswith(spline_base + ".boundMesh["):
            continue

        bound_transform = cmds.listRelatives(cmds.ls(dst, objectsOnly=True),
                                             parent=True)[0]

        head = "." + src.split(".")[-1]
        tail = ",".join([str(i) for i in cmds.xform(bound_transform,
                                                    query=True,
                                                    boundingBox=True)])
        bounding_box += head + ":" + tail + ";"

    return bounding_box


class SplinePresetUtil(xgmSplinePreset.PresetUtil):
    """Enhanced XGen interactive groom preset util class

    This util has implemented preset referencing and multi-mesh bounding,
    and used by a few of XGen IGS input functions:

        `io.import_xgen_IGS_preset`
        `io.reference_xgen_IGS_preset`
        `io.attach_xgen_IGS_preset`

    Mainly used for save and load preset on same meshes, not for transfer
    in between different meshes.

    """

    HEADER = None

    @staticmethod
    def __bindMeshes(meshShapes, rootNodes, descNodes):
        """Bound to multiple or single mesh"""
        for rootNode in rootNodes:
            for i, mesh in enumerate(meshShapes):
                fromAttr = r"%s.worldMesh" % mesh
                toAttr = r"%s.boundMesh[%d]" % (rootNode, i)
                cmds.connectAttr(fromAttr, toAttr)

        for descNode in descNodes:
            # Force grooming DG eval
            # This must be done once before Transfer Mode turned off
            descAttr = r"%s.outSplineData" % descNode
            cmds.dgeval(descAttr)

    @classmethod
    def __convertMAToPreset(cls, inFile, outFile, boundingBoxInfo):
        with open(inFile, r'rb') as f:
            maBuff = f.read()
        melBuff = cls.__convertMAToPresetBuffer(maBuff, boundingBoxInfo)
        with open(outFile, r'wb') as f:
            f.write(melBuff)

    @classmethod
    def __convertMAToPresetBuffer(cls, fileBuff, boundingBoxInfo):
        extraNodeTypes = cls._PresetUtil__getExtendedExtraNodeTypes(fileBuff)
        cont = cls._PresetUtil__getMAToPresetBuffer(fileBuff, extraNodeTypes)
        cont = cls._PresetUtil__filterUnusedTransform(cont)
        cont = cls._PresetUtil__addMetaData(cont, boundingBoxInfo)
        cont = cls.__addHeader(cont)
        content = cont
        return content

    @classmethod
    def __addHeader(cls, content):
        contentList = [
            cls.HEADER,
            r"//",
            r"// Author:       %s" % mel.eval(r'getenv("USER")'),
            r"// Date:         %s" % cmds.date(),
            r"//",
            r"//XGIP:VERSION: %s" % cls.buildVersion,
        ]
        contentList.append(content)
        return '\n'.join(contentList)

    @classmethod
    def convertMAToPreset(cls, inFile, outFile,
                          boundingBoxInfo, removeOriginal=True):
        '''Convert MA to Preset file'''
        cls.HEADER = r"// XGen Interactive Grooming Preset"
        cls.__convertMAToPreset(inFile, outFile, boundingBoxInfo)
        if removeOriginal:
            cls._PresetUtil__removeFile(inFile)

    @classmethod
    def convertMAToMA(cls, inFile, outFile,
                      boundingBoxInfo, removeOriginal=True):
        '''Convert MA to MA file'''
        cls.HEADER = r"//Maya ASCII scene"
        cls.__convertMAToPreset(inFile, outFile, boundingBoxInfo)
        if removeOriginal:
            cls._PresetUtil__removeFile(inFile)

    @classmethod
    def attachPreset(cls, newNodes, meshShapes):
        """Apply preset to meshes

        Args:
            newNodes (list): A list of loaded nodes
            meshShapes (list): A list of bound meshes

        """
        rootNodes = []
        descNodes = []

        for nodeName in newNodes:
            nodeType = cmds.nodeType(nodeName)
            if nodeType == cls.rootNodeType:  # xgmSplineBase
                rootNodes.append(nodeName)
            elif nodeType == cls.descNodeType:  # xgmSplineDescription
                descNodes.append(nodeName)

        # (NOTE) Removed the `transferModeGuard` context. It seems that
        #        entering *transfer mode* will end up not able to apply
        #        back to multiple meshes.
        #        Since we are not meant to do any *transfer*, just want
        #        to bound back to original mesh or meshes, should be safe
        #        to bypass that context.
        cls.__bindMeshes(meshShapes, rootNodes, descNodes)

    @classmethod
    def loadPreset(cls, filePath, namespace, reference):
        """Reference or import preset file, return loaded nodes

        Args:
            filePath (str): Preset file path.
            namespace (str): Namespace to apply to.
            reference (bool): Load preset by reference or import.

        Returns:
            list: A list of loaded nodes

        """
        newNodes = []
        fileVersion = None

        if os.path.isfile(filePath):
            with open(filePath, r"rb") as f:
                for line in f:
                    line = line.rstrip()

                    matchVersionPattern = cls.versionPattern.search(line)
                    if matchVersionPattern:
                        # version appears only once
                        fileVersion = int(matchVersionPattern.group(1))

                    if fileVersion is not None:
                        break

            if fileVersion and fileVersion > cls.buildVersion:
                # TODO: L10N
                raise xgmSplinePreset.ForwardCompatibilityError(
                    "Current Preset build version: {0}. Cannot reference "
                    "Preset of a higher verison: {1}."
                    "".format(cls.buildVersion, fileVersion)
                )

            nodesBeforeImport = set(cmds.ls())

            try:
                if reference:
                    newNodes = cmds.file(
                        filePath,
                        namespace=namespace,
                        reference=True,
                        type=r"mayaAscii",
                        ignoreVersion=True,
                        mergeNamespacesOnClash=True,
                        preserveReferences=True,
                        returnNewNodes=True
                    )
                else:
                    newNodes = cmds.file(
                        filePath,
                        namespace=namespace,
                        i=True,
                        type=r"mayaAscii",
                        ignoreVersion=True,
                        renameAll=True,
                        mergeNamespacesOnClash=True,
                        preserveReferences=True,
                        returnNewNodes=True
                    )
            except Exception:
                import traceback
                traceback.print_exc()
                # If exception occurs during importing, try to recover
                # newNodes by comparing scene nodes snapshots
                nodesAfterImport = set(cmds.ls())
                newNodes = list(nodesAfterImport - nodesBeforeImport)

        return newNodes
