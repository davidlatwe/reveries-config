
from maya import cmds


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
