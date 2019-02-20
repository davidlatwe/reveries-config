
import os
import json
import tempfile
import logging
import contextlib
from maya import cmds
from xgenm.xmaya import xgmSplinePreset

from . import capsule, lib
from .vendor import capture


log = logging.getLogger(__name__)


def export_fbx(out_path, selected=True):
    from pymel.core import mel as pymel
    try:
        pymel.FBXExport(f=out_path, s=selected)
    finally:
        pymel.FBXResetExport()


@contextlib.contextmanager
def export_fbx_set_pointcache(cache_set_name):
    set_node = cmds.sets(cmds.ls(sl=True), name=cache_set_name)
    fbx_export_settings(reset=True,
                        log=False,
                        ascii=True,
                        cameras=False,
                        lights=False,
                        cache_file=True,
                        cache_set=cache_set_name,
                        anim_only=False,
                        key_reduce=True,
                        shapes=False,
                        skins=False,
                        input_conns=False,
                        )
    try:
        yield
    finally:
        cmds.delete(set_node)


def export_fbx_set_camera():
    fbx_export_settings(reset=True,
                        log=False,
                        ascii=True,
                        cameras=True,
                        lights=False,
                        )


def fbx_export_settings(reset=False, **kwargs):
    """
    """
    from pymel.core import mel as pymel

    if reset:
        pymel.FBXResetExport()

    fbx_export_cmd_map = {
        "log": pymel.FBXExportGenerateLog,
        "ascii": pymel.FBXExportInAscii,
        "version": pymel.FBXExportFileVersion,

        "cameras": pymel.FBXExportCameras,
        "lights": pymel.FBXExportLights,
        "instances": pymel.FBXExportInstances,
        "referenced": pymel.FBXExportReferencedAssetsContent,

        "smoothing_groups": pymel.FBXExportSmoothingGroups,
        "smooth_mesh": pymel.FBXExportSmoothMesh,
        "tangents": pymel.FBXExportTangents,
        "triangulate": pymel.FBXExportTriangulate,
        "hardEdges": pymel.FBXExportHardEdges,

        "constraints": pymel.FBXExportConstraints,
        "input_conns": pymel.FBXExportInputConnections,

        "shapes": pymel.FBXExportShapes,
        "skins": pymel.FBXExportSkins,
        "skeleton": pymel.FBXExportSkeletonDefinitions,

        "anim_only": pymel.FBXExportAnimationOnly,
        "cache_file": pymel.FBXExportCacheFile,
        "cache_set": pymel.FBXExportQuickSelectSetAsCache,

        "bake_anim": pymel.FBXExportBakeComplexAnimation,
        "bake_start": pymel.FBXExportBakeComplexStart,
        "bake_end": pymel.FBXExportBakeComplexEnd,
        "bake_step": pymel.FBXExportBakeComplexStep,
        "bake_resample_all": pymel.FBXExportBakeResampleAll,

        "key_reduce": pymel.FBXExportApplyConstantKeyReducer,
    }

    for key in kwargs:
        fbx_export_cmd_map[key](v=kwargs[key])


# The maya alembic export types
_alembic_options = {
    "startFrame": (int, float),
    "endFrame": (int, float),
    "frameRange": str,  # "start end"; overrides startFrame & endFrame
    "eulerFilter": bool,
    "frameRelativeSample": float,
    "noNormals": bool,
    "renderableOnly": bool,
    "step": float,
    "stripNamespaces": bool,
    "uvWrite": bool,
    "wholeFrameGeo": bool,
    "worldSpace": bool,
    "writeVisibility": bool,
    "writeColorSets": bool,
    "writeFaceSets": bool,
    "writeCreases": bool,  # Maya 2015 Ext1+
    "dataFormat": str,
    "root": (list, tuple),
    "attr": (list, tuple),
    "attrPrefix": (list, tuple),
    "userAttr": (list, tuple),
    "melPerFrameCallback": str,
    "melPostJobCallback": str,
    "pythonPerFrameCallback": str,
    "pythonPostJobCallback": str,
    "selection": bool
}


def export_alembic(file,
                   startFrame=None,
                   endFrame=None,
                   selection=True,
                   uvWrite=True,
                   eulerFilter=True,
                   writeVisibility=True,
                   dataFormat="ogawa",
                   verbose=False,
                   **kwargs):
    """Extract a single Alembic Cache. (modified, from colorbleed config)

    Arguments:

        startFrame (float): Start frame of output. Ignored if `frameRange`
            provided.

        endFrame (float): End frame of output. Ignored if `frameRange`
            provided.

        frameRange (tuple or str): Two-tuple with start and end frame or a
            string formatted as: "startFrame endFrame". This argument
            overrides `startFrame` and `endFrame` arguments.

        dataFormat (str): The data format to use for the cache,
                          defaults to "ogawa"

        verbose (bool): When on, outputs frame number information to the
            Script Editor or output window during extraction.

        noNormals (bool): When on, normal data from the original polygon
            objects is not included in the exported Alembic cache file.

        renderableOnly (bool): When on, any non-renderable nodes or hierarchy,
            such as hidden objects, are not included in the Alembic file.
            Defaults to False.

        stripNamespaces (bool): When on, any namespaces associated with the
            exported objects are removed from the Alembic file. For example, an
            object with the namespace taco:foo:bar appears as bar in the
            Alembic file.

        uvWrite (bool): When on, UV data from polygon meshes and subdivision
            objects are written to the Alembic file. Only the current UV map is
            included.

        worldSpace (bool): When on, the top node in the node hierarchy is
            stored as world space. By default, these nodes are stored as local
            space. Defaults to False.

        eulerFilter (bool): When on, X, Y, and Z rotation data is filtered with
            an Euler filter. Euler filtering helps resolve irregularities in
            rotations especially if X, Y, and Z rotations exceed 360 degrees.
            Defaults to True.

        writeVisibility (bool): If this flag is present, visibility state will
            be stored in the Alembic file.
            Otherwise everything written out is treated as visible.

        wholeFrameGeo (bool): When on, geometry data at whole frames is sampled
            and written to the file. When off (default), geometry data is
            sampled at sub-frames and written to the file.

    Examples: (Copied from MEL cmd `AbcExport -help`)

        AbcExport -j
        "-root |group|foo -root |test|path|bar -file /tmp/test.abc"

            Writes out everything at foo and below and bar and below to
            `/tmp/test.abc`.
            foo and bar are siblings parented to the root of the Alembic scene.

        AbcExport -j
        "-frameRange 1 5 -step 0.5 -root |group|foo -file /tmp/test.abc"

            Writes out everything at foo and below to `/tmp/test.abc` sampling
            at frames: 1 1.5 2 2.5 3 3.5 4 4.5 5

        AbcExport -j
        "-fr 0 10 -frs -0.1 -frs 0.2 -step 5 -file /tmp/test.abc"

        Writes out everything in the scene to `/tmp/test.abc` sampling at
        frames: -0.1 0.2 4.9 5.2 9.9 10.2

        Note: The difference between your highest and lowest
        frameRelativeSample can not be greater than your step size.

        AbcExport -j
        "-step 0.25 -frs 0.3 -frs 0.60 -fr 1 5 -root foo -file test.abc"

        Is illegal because the highest and lowest frameRelativeSamples are 0.3
        frames apart.

        AbcExport -j
        "-sl -root |group|foo -file /tmp/test.abc"

        Writes out all selected nodes and it's ancestor nodes including up to
        foo.
        foo will be parented to the root of the Alembic scene.

    (NOTE) About alembic selection export

    Say we have a hierarchy `A > B > C > D > E`, A is root and E is leaf.

    when the export cmd is "-sl -root |A|B|C" and we select D, then we will
    get `C > D` exported.

    when the export cmd is "-sl" and we select D, then we will get
    `A > B > C > D` exported.

    when the export cmd is "-root |A|B|C", then we will get `C > D > E`
    exported.

    As you can see, flag `-sl` and `-root` are kind of end point and start
    point of the DAG chain.
    If there are multiple `-root`, and `-sl` has given, each root node must
    have it's descendant node been selected, or the root will not be exported.

    """

    # Ensure alembic exporter is loaded
    cmds.loadPlugin('AbcExport', quiet=True)

    # Alembic Exporter requires forward slashes
    file = file.replace('\\', '/')

    # Pass the start and end frame on as `frameRange` so that it
    # never conflicts with that argument
    if "frameRange" not in kwargs:
        # Fallback to maya timeline if no start or end frame provided.
        if startFrame is None:
            startFrame = cmds.playbackOptions(query=True, minTime=True)
        if endFrame is None:
            endFrame = cmds.playbackOptions(query=True, maxTime=True)

        # Ensure valid types are converted to frame range
        assert isinstance(startFrame, _alembic_options["startFrame"])
        assert isinstance(endFrame, _alembic_options["endFrame"])
        kwargs["frameRange"] = "{0} {1}".format(startFrame, endFrame)
    else:
        # Allow conversion from tuple for `frameRange`
        frame_range = kwargs["frameRange"]
        if isinstance(frame_range, (list, tuple)):
            assert len(frame_range) == 2
            kwargs["frameRange"] = "{0} {1}".format(frame_range[0],
                                                    frame_range[1])

    # Assemble options
    options = {
        "selection": selection,
        "uvWrite": uvWrite,
        "eulerFilter": eulerFilter,
        "writeVisibility": writeVisibility,
        "dataFormat": dataFormat
    }
    options.update(kwargs)

    # Validate options
    for key, value in options.copy().items():

        # Discard unknown options
        if key not in _alembic_options:
            options.pop(key)
            continue

        # Validate value type
        valid_types = _alembic_options[key]
        if not isinstance(value, valid_types):
            raise TypeError("Alembic option unsupported type: "
                            "{0} (expected {1})".format(value, valid_types))

    # The `writeCreases` argument was changed to `autoSubd` in Maya 2018+
    maya_version = int(cmds.about(version=True))
    if maya_version >= 2018:
        options['autoSubd'] = options.pop('writeCreases', False)

    # Format the job string from options
    job_args = list()
    for key, value in options.items():
        if isinstance(value, (list, tuple)):
            for entry in value:
                job_args.append("-{} {}".format(key, entry))
        elif isinstance(value, bool):
            # Add only when state is set to True
            if value:
                job_args.append("-{0}".format(key))
        else:
            job_args.append("-{0} {1}".format(key, value))

    job_str = " ".join(job_args)
    job_str += ' -file "%s"' % file

    # Ensure output directory exists
    parent_dir = os.path.dirname(file)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    if verbose:
        log.debug("Preparing Alembic export with options: %s",
                  json.dumps(options, indent=4))
        log.debug("Extracting Alembic with job arguments: %s", job_str)

    # Perform extraction
    print("Alembic Job Arguments : {}".format(job_str))

    # Disable the parallel evaluation temporarily to ensure no buggy
    # exports are made. (PLN-31)
    # TODO: Make sure this actually fixes the issues
    with capsule.evaluation("off"):
        cmds.AbcExport(j=job_str, verbose=verbose)

    if verbose:
        log.debug("Extracted Alembic to: %s", file)

    return file


def export_gpu(out_path, startFrame, endFrame):
    # Ensure alembic exporter is loaded
    cmds.loadPlugin("gpuCache", quiet=True)

    cmds.gpuCache(cmds.ls(sl=True, long=True),
                  startTime=startFrame,
                  endTime=endFrame,
                  optimize=True,
                  optimizationThreshold=40000,
                  writeMaterials=True,
                  writeUVs=True,
                  dataFormat="ogawa",
                  saveMultipleFiles=False,
                  directory=os.path.dirname(out_path),
                  fileName=os.path.splitext(os.path.basename(out_path))[0]
                  )


def wrap_gpu(wrapper_path, gpu_files):
    """Wrapping GPU caches into a MayaAscii file

    (NOTE) The file path of `gpu_files` should be a relative path, relative to
        `wrapper_path`.

        For example:
            ```python

            wrapper_path = ".../publish/pointcache/v001/Alembic/pointcache.ma"
            gpu_files = [("Peter_01/pointcache.abc", "Peter_01"), ...]

            ```

    Args:
        wrapper_path (str): MayaAscii file path
        gpu_files (list): A list of tuple of .abc file path and cached
            asset name.

    """
    MayaAscii_template = """//Maya ASCII scene
requires maya "2016";
requires -nodeType "gpuCache" "gpuCache" "1.0";
"""
    gpu_node_template = """
$cachefile = `file -q -loc "{filePath}"`;  // Resolve relative path
createNode transform -n "{nodeName}";
createNode gpuCache -n "{nodeName}Shape" -p "{nodeName}";
    setAttr ".cfn" -type "string" $cachefile;
"""
    gpu_script = ""
    for gpu_path, node_name in gpu_files:
        gpu_script += gpu_node_template.format(nodeName=node_name,
                                               filePath=gpu_path)

    with open(wrapper_path, "w") as maya_file:
        maya_file.write(MayaAscii_template + gpu_script)


def wrap_abc(wrapper_path, abc_files):
    """Wrapping Alembic caches into a MayaAscii file

    (NOTE) The file path of `gpu_files` should be a relative path, relative to
        `wrapper_path`.

        For example:
            ```python

            wrapper_path = ".../publish/pointcache/v001/Alembic/pointcache.ma"
            gpu_files = [("Peter_01/pointcache.abc", "Peter_01"), ...]

            ```

    Args:
        wrapper_path (str): MayaAscii file path
        abc_files (list): A list of tuple of .abc file path and cached
            asset name.

    """
    MayaAscii_template = """//Maya ASCII scene
requires maya "2016";
requires -nodeType "AlembicNode" "AbcImport" "1.0";
{abcScript}
currentTime `currentTime -q`;  // Trigger refresh
"""
    abc_node_template = """
$cachefile = `file -q -loc "{filePath}"`;  // Resolve relative path
group -n "{groupName}" -empty -world;
AbcImport -reparent "|{groupName}" -mode import $cachefile;
"""
    abc_script = ""
    for abc_path, group_name in abc_files:
        abc_script += abc_node_template.format(groupName=group_name,
                                               filePath=abc_path)

    with open(wrapper_path, "w") as maya_file:
        maya_file.write(MayaAscii_template.format(abcScript=abc_script))


def wrap_fbx(wrapper_path, fbx_files):
    """Wrapping FBX caches into a MayaAscii file

    (NOTE) The file path of `gpu_files` should be a relative path, relative to
        `wrapper_path`.

        For example:
            ```python

            wrapper_path = ".../publish/pointcache/v001/Alembic/pointcache.ma"
            gpu_files = [("Peter_01/pointcache.fbx", "Peter_01"), ...]

            ```

    Args:
        wrapper_path (str): MayaAscii file path
        fbx_files (list): A list of tuple of .fbx file path and cached
            asset name.

    """
    MayaAscii_template = """//Maya ASCII scene
requires maya "2016";
requires "fbxmaya";
FBXResetImport;
"""
    fbx_node_template = """
$cachefile = `file -q -loc "{filePath}"`;  // Resolve relative path
file -import -type "FBX" -groupReference -groupName "{groupName}" $cachefile";
"""
    fbx_script = ""
    for fbx_path, group_name in fbx_files:
        fbx_script += fbx_node_template.format(groupName=group_name,
                                               filePath=fbx_path)

    with open(wrapper_path, "w") as maya_file:
        maya_file.write(MayaAscii_template + fbx_script)


def capture_seq(camera,
                filename,
                start_frame,
                end_frame,
                width=None,
                height=None,
                isolate=None,
                frame_padding=4,
                display_options=None,
                viewport_options=None):

    viewport_options = viewport_options or {
        "headsUpDisplay": False,
    }

    output = capture.capture(
        camera,
        filename=filename,
        start_frame=start_frame,
        end_frame=end_frame,
        width=width,
        height=height,
        format='image',
        compression='png',
        quality=100,
        off_screen=True,
        viewer=False,
        show_ornaments=False,
        sound=None,
        isolate=isolate,
        maintain_aspect_ratio=True,
        overwrite=True,
        frame_padding=frame_padding,
        raw_frame_numbers=False,
        camera_options=None,
        display_options=display_options,
        viewport_options=viewport_options,
        viewport2_options=None
    )
    return output


def export_xgen_IGS_preset(description, out_path):
    """Export XGen IGS description preset

    Args:
        description (str): description shape node name
        out_path (str): preset output path (.xgip)

    """

    spline_base = lib.find_spline_base(description)
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

    # Export tmp mayaAscii file
    ascii_tmp = tempfile.mkdtemp(prefix="__xgenIGS_export") + "/{}.ma"
    ascii_tmp = ascii_tmp.format(description)

    with capsule.maintained_selection():
        cmds.select(description, replace=True)
        cmds.file(ascii_tmp,
                  force=True,
                  typ="mayaAscii",
                  exportSelected=True,
                  preserveReferences=False,
                  constructionHistory=True,
                  channels=True,
                  constraints=True,
                  shader=True,
                  expressions=True)

    xgmSplinePreset.PresetUtil.convertMAToPreset(ascii_tmp,
                                                 out_path,
                                                 bounding_box,
                                                 removeOriginal=True)
