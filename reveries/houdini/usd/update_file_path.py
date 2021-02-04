import os
import re


def update(kwargs):
    """
    Update file path for subnet node.
    :param kwargs: (object) kwargs
    :return:
    """
    import hou
    from reveries.common.utils import project_root_path

    node = kwargs['node']  # hou.node(r'/stage/{}'.format(node_name))

    ver_parm_name = kwargs['parm_name']  # 'ver_name_{}'.format(parm_suffix)
    file_path_parm_name = ver_parm_name.replace(
        "ex_ver_name_", "ex_file_path_")  # 'file_path_{}'.format(parm_suffix)

    new_version = node.parm(ver_parm_name).eval()
    current_path = node.parm(file_path_parm_name).eval()

    if new_version and current_path:
        ver_match = re.findall("/(v\\d+)/USD", current_path)

        print("ver_match: ", ver_match)

        if ver_match:
            current_version = ver_match[0]
            new_path = current_path.replace(current_version, new_version)
            if not os.path.exists(new_path):
                new_path = _format_mapping(new_path)

                if not os.path.exists(new_path):
                    hou.ui.displayMessage(
                        "Error: File not exists - {}".format(new_path),
                        severity=hou.severityType.Error
                    )
                    return

            project_root_path = project_root_path(new_path)
            node.parm(file_path_parm_name).set(project_root_path)

            # Update container
            _update_container(kwargs, new_path)


def _update_container(kwargs, new_path):
    import hou
    from reveries.common import path_resolver

    subnet_node = kwargs['node']
    ver_parm_name = kwargs['parm_name']
    index = ver_parm_name.split("_")[-1]
    subnet_node_path = subnet_node.path()

    nodes = list(hou.node("/obj").allNodes())
    for node in nodes:
        if not node.parm("subnet_usd_path"):
            continue
        if node.evalParm("subnet_usd_path") != subnet_node_path:
            continue
        if node.evalParm("usd_index") != index:
            continue
        # Update attribute subnet_usd_path
        resolver_obj = path_resolver.PathResolver(file_path=new_path)
        representation_id = resolver_obj.get_representation_id()
        node.parm("representation").set(str(representation_id))

        break


def _format_mapping(file_path):
    _, ext = os.path.splitext(os.path.basename(file_path))

    if ext == ".usda":
        file_path = file_path.replace(".usda", ".usd")

    if ext == ".usd":
        file_path = file_path.replace(".usd", ".usda")

    return file_path
