import re


def update(node_name, parm_suffix):
    """
    Update file path for subnet node.
    :param node_name: (str) Node name
    :param parm_suffix: (str) The suffix name of asset's parameter
    :return:
    """
    import hou

    node = hou.node(r'/stage/{}'.format(node_name))

    ver_parm_name = 'ver_name_{}'.format(parm_suffix)
    file_path_parm_name = 'file_path_{}'.format(parm_suffix)

    new_version = node.parm(ver_parm_name).eval()
    current_path = node.parm(file_path_parm_name).eval()

    if new_version and current_path:
        ver_match = re.findall("/(v\\d+)/USD", current_path)

        if ver_match:
            current_version = ver_match[0]
            new_path = current_path.replace(current_version, new_version)
            node.parm(file_path_parm_name).set(new_path)
