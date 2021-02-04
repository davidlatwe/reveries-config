
def run_delete(kwargs):
    import hou

    subnet_node = kwargs['node']
    subnet_path = subnet_node.path()

    nodes = list(hou.node("/obj").allNodes())
    for node in nodes:
        if not node.parm("subnet_usd_path"):
            continue
        if node.evalParm("subnet_usd_path") != subnet_path:
            continue

        node.destroy()
