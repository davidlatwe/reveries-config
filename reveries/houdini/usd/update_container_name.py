
def run_rename(kwargs):
    import hou

    subnet_node = kwargs['node']
    new_name = subnet_node.name()
    old_name = kwargs['old_name']
    old_path = "/stage/{}".format(old_name)

    nodes = list(hou.node("/obj").allNodes())
    for node in nodes:
        if not node.parm("subnet_usd_path"):
            continue
        if node.evalParm("subnet_usd_path") != old_path:
            continue

        # Update attribute subnet_usd_path
        node.parm("subnet_usd_path").set(subnet_node.path())

        # Update attribute name
        _index = node.parm("usd_index").eval()
        _new_name = "{}_{}".format(new_name, _index)
        node.parm("name").set(_new_name)

        # Update node name
        node.setName("{}_CON".format(_new_name))
