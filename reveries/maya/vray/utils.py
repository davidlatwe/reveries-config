
from maya import cmds


def create_vray_settings():

    # Try register vray
    try:
        cmds.renderer('vray')
    except RuntimeError:
        print "Vray already Registered"

    # Collect all vray-Attributes
    globalsTabLabels = cmds.renderer('vray', query=True, globalsTabLabels=True)
    globalsTabCreateProcNames = cmds.renderer('vray',
                                              query=True,
                                              globalsTabCreateProcNames=True)
    globalsTabUpdateProcNames = cmds.renderer('vray',
                                              query=True,
                                              globalsTabUpdateProcNames=True)
    # Construct Vray-Renderer
    for tab_id in range(len(globalsTabLabels)):
        cmds.renderer('vray',
                      edit=True,
                      addGlobalsTab=[
                          str(globalsTabLabels[tab_id]),
                          str(globalsTabCreateProcNames[tab_id]),
                          str(globalsTabUpdateProcNames[tab_id]),
                      ])
    # Create DAG for VRAYSETTINGS
    cmds.shadingNode("VRaySettingsNode", asUtility=True, name="vraySettings")
