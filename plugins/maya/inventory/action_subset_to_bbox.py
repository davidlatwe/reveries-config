
import avalon.api
import avalon.io
import avalon.maya
import time
from maya import cmds


class SubsetToBBox(avalon.api.InventoryAction):

    label = "Subset To BBox"
    icon = "cube"
    color = "#E67E22"

    @staticmethod
    def is_compatible(container):
        if not container:
            return False

        if container["loader"] in [
            "ArnoldAssLoader",
            "ModelLoader",
            "PointCacheReferenceLoader",
            "RigLoader",
        ]:
            return True

    def process(self, containers):

        objects = list()
        for container in containers:
            if not self.is_compatible(container):
                continue

            if not cmds.objExists(container["subsetGroup"]):
                continue

            objects += cmds.ls(container["subsetGroup"])

        if not objects:
            return

        start = time.time()
        cmds.progressWindow(title="Bounding Box From Subset",
                            isInterruptable=True,
                            maxValue=len(objects) + 1)

        bboxes = list()
        bbox_shapes = list()
        for i, obj in enumerate(objects, 1):

            if cmds.progressWindow(query=True, isCancelled=True):
                cmds.delete(bboxes)
                cmds.progressWindow(endProgress=True)
                return

            bbox, bbox_shape = object_to_bbox(obj)
            bboxes.append(bbox)
            bbox_shapes.append(bbox_shape)

            passed = int(time.time() - start)
            cmds.progressWindow(edit=True,
                                progress=i,
                                status=("Creating Bounding Boxes" +
                                        "." * (passed % 3 + 1)))

        cmds.progressWindow(edit=True, progress=i + 1,
                            status="Assigning shaders..")

        shader = bbox_shader(0.8, 0.1, 0.2)
        cmds.sets(bbox_shapes, forceElement=shader)

        group = "|__AUTO_BBOX__"
        if not cmds.objExists(group):
            cmds.group(name=group, empty=True, world=True)
        cmds.parent(bboxes, group)

        cmds.progressWindow(endProgress=True)


def object_to_bbox(object):

    def point_cube():
        cube = cmds.polyCube(createUVs=0, constructionHistory=False)
        cmds.scale(0, 0, 0, cube)
        return cube[0]

    point_a = point_cube()
    point_b = point_cube()

    ax, ay, az, bx, by, bz = cmds.xform(object,
                                        query=True,
                                        boundingBox=True,
                                        worldSpace=True)

    cmds.setAttr(point_a + ".translate", ax, ay, az)
    cmds.setAttr(point_b + ".translate", bx, by, bz)

    group = cmds.group(empty=True, world=True)
    cmds.parent([point_a, point_b], group)

    bbox = cmds.geomToBBox(group, keepOriginal=False, single=True)
    bbox = bbox[0].rsplit(":")[-1]

    # Remove auto generated shader and assign our own later
    bbox_shape = cmds.listRelatives(bbox, shapes=True, path=True)[0]
    cmds.delete(cmds.listConnections(bbox_shape,
                                     type="shadingEngine",
                                     source=False,
                                     destination=True))
    return bbox, bbox_shape


def bbox_shader(color_r=0.5, color_g=0.5, color_b=0.5):
    # (NOTE) Using command `createNode` instead of `shadingNode` to create
    #        lambert node will make it able to be deleted with shadingEngine.
    lambert = cmds.createNode("lambert", name="bboxShader")
    shader = cmds.shadingNode("shadingEngine",
                              name=lambert + "SG",
                              asRendering=True)
    # (NOTE) Connect partition node to avoid "Error while parsing arguments"
    #        error when assigning this shader manually.
    cmds.connectAttr(shader + ".partition",
                     "renderPartition.sets",
                     nextAvailable=True)

    cmds.connectAttr(lambert + ".outColor", shader + ".surfaceShader")
    cmds.setAttr(lambert + ".color", color_r, color_g, color_b)

    return shader
