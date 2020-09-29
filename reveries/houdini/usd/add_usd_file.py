import re


def update_node(node, usd_info):
    import hou

    # Get information
    asset_name = usd_info.get('asset_name')
    asset_name_lower = asset_name.lower()

    _parm_num = 0
    for _parm in node.parms():
        if 'parm_{}_'.format(asset_name_lower) in _parm.name():
            _parm_num = int(_parm.name().split('_')[-1])

    num = 1 + _parm_num

    parm_suffix = '{}_{}'.format(asset_name_lower, num)
    top_parm_name = "parm_{}".format(parm_suffix)

    file_path = usd_info.get('file_path')

    subset_info = 'Subset: {}'.format(usd_info.get('subset_name'))
    family_info = 'Family: {}'.format(usd_info.get('family_name'))

    # all_version_num = usd_info.get('latest_version')
    # ver_token = [str(key) for key in range(all_version_num)]
    # ver_name = ['v{:03d}'.format(key + 1) for key in range(all_version_num)]

    # Generate node parameter
    enable_name = "enable_{}".format(parm_suffix)
    enable_parm = hou.ToggleParmTemplate(enable_name, "Enable", default_value=(1))
    disable_py = "{ " + enable_name + " == 0 }"

    asset_parm = hou.StringParmTemplate(
        "asset_info_{}".format(parm_suffix), asset_name, 2,
        default_value=(subset_info, family_info),
        disable_when='{ asset_info_# != "" }'
    )
    path_parm = hou.StringParmTemplate(
        "file_path_{}".format(parm_suffix),
        "File Path", 1,
        default_value=(file_path,),
        disable_when='{ file_path_# != "" }'
    )

    # Primitive path setting option
    _prim_path = '/ROOT'
    prim_path_parm = hou.StringParmTemplate(
        "prim_path_{}".format(parm_suffix), "Primitive Path", 1, default_value=(_prim_path,),
        disable_when=disable_py)
    prim_path_parm.setConditional(hou.parmCondType.HideWhen, "{ file_type_" + parm_suffix + " == \"sublayer\"}")

    # Prim name setting option
    _prim_name = 'ref_{0}_{1}'.format(asset_name_lower, num)
    update_label_py = "hou.phm().update_label(kwargs, \"{}\");".format(top_parm_name)
    prim_name_parm = hou.StringParmTemplate(
        "prim_name_{}".format(parm_suffix), "Reference Prim Name", 1, default_value=(_prim_name,),
        disable_when=disable_py,
        script_callback=update_label_py,
        script_callback_language=hou.scriptLanguage.Python)
    prim_name_parm.setConditional(hou.parmCondType.HideWhen, "{ file_type_" + parm_suffix + " == \"sublayer\"}")

    # Version option
    cur_ver_name = re.findall("/(v\\d+)/USD", file_path)[0]
    ver_update_path_py = "hou.phm().update_file_path(\"{}\", \"{}\");".format(node, parm_suffix)
    ver_update_version_py = "node = hou.pwd()\n" \
                            "menu=node.hdaModule().get_latest_version(\"{}\", \"{}\")\n" \
                            "return menu".format(asset_name, usd_info.get('subset_name'))
    ver_parm = hou.StringParmTemplate(
        "ver_name_{}".format(parm_suffix), "Version", 1,
        # menu_items=(ver_name),
        # menu_labels=(ver_name),
        item_generator_script=ver_update_version_py,
        item_generator_script_language=hou.scriptLanguage.Python,
        disable_when=disable_py,
        default_value=(cur_ver_name,),
        script_callback=ver_update_path_py,
        script_callback_language=hou.scriptLanguage.Python
    )

    # Type option
    type_parm = hou.StringParmTemplate(
        "file_type_{}".format(parm_suffix), "File Type", 1,
        menu_items=(["reference", "sublayer"]), menu_labels=(["Reference", "Sublayer"]),
        disable_when=disable_py
    )

    # Remove button
    remove_py = "node = hou.pwd();" \
                "ptg = node.parmTemplateGroup();" \
                "ptg.remove(ptg.find('{}'));" \
                "node.setParmTemplateGroup(ptg);".format(top_parm_name)
    remove_btn = hou.ButtonParmTemplate("remove_{}".format(parm_suffix), "Remove", script_callback=remove_py,
                                        script_callback_language=hou.scriptLanguage.Python)
    sepparm_parm = hou.SeparatorParmTemplate("sepparm_{}".format(parm_suffix))

    # Status string
    status_name = "status_{}".format(parm_suffix)
    status_parm = hou.StringParmTemplate(status_name, "Status", 1, default_value=("",))
    status_parm.setConditional(hou.parmCondType.HideWhen, "{ " + status_name + " == ""}")
    status_parm.setConditional(hou.parmCondType.DisableWhen, "{ " + status_name + " != ""}")

    parm_parm = hou.FolderParmTemplate(top_parm_name, '{0}: {1}'.format(asset_name, _prim_name),
                                       folder_type=hou.folderType.Simple)
    parm_parm.addParmTemplate(enable_parm)
    parm_parm.addParmTemplate(asset_parm)
    parm_parm.addParmTemplate(path_parm)
    parm_parm.addParmTemplate(prim_path_parm)
    parm_parm.addParmTemplate(prim_name_parm)
    parm_parm.addParmTemplate(ver_parm)
    parm_parm.addParmTemplate(type_parm)
    parm_parm.addParmTemplate(remove_btn)
    parm_parm.addParmTemplate(sepparm_parm)
    parm_parm.addParmTemplate(status_parm)

    # add_parm = hou.FolderParmTemplate("add_parm", "Add Parameter", folder_type=hou.folderType.MultiparmBlock)
    # add_parm.addParmTemplate(parm_parm)

    node.addSpareParmTuple(parm_parm)

    # Refresh node
    for c in node.children():
        c.cook(force=True, frame_range=(hou.hscriptExpression('$RFSTART'), hou.hscriptExpression('$RFSTART + 1')))
