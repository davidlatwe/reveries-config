
from maya import mel, cmds


def setVrayTextureFilter(*args):

    def job(fileNode, method):
        mel.eval("vray addAttributesFromGroup {} "
                 "vray_texture_filter 1;".format(fileNode))
        cmds.setAttr(fileNode + '.vrayTextureSmoothType', method)

    method = cmds.optionMenu("VMF_menu", query=True, sl=1) - 1

    selected = cmds.ls(sl=True, et="file")
    if selected:
        for fileNode in selected:
            job(fileNode, method)
    else:
        for fileNode in cmds.ls(type="file"):
            job(fileNode, method)


def setVrayTextureGamma(*args):

    def job(fileNode, colorspace):
        mel.eval("vray addAttributesFromGroup {} "
                 "vray_file_gamma 1;".format(fileNode))
        cmds.setAttr(fileNode + '.vrayFileColorSpace', colorspace)

    colorspace = cmds.optionMenu("VMG_menu", query=True, sl=1) - 1

    selected = cmds.ls(sl=True, et="file")
    if selected:
        for fileNode in selected:
            job(fileNode, colorspace)
    else:
        for fileNode in cmds.ls(type="file"):
            job(fileNode, colorspace)


def fileNodeSelect():

    selected = cmds.ls(sl=True, et="file")
    if selected:
        label = "\t{} fileNode selected.".format(len(selected))
    else:
        label = "\tNothing selected.\tDo All."

    cmds.text("selStatus", edit=True, label=label)


windowName = 'setVrayMapAttr'


def show():
    if cmds.window(windowName, query=True, ex=True):
        cmds.deleteUI(windowName)

    cmds.window(windowName, s=False)

    cmds.scriptJob(e=['SelectionChanged', 'fileNodeSelect()'], p=windowName)

    cmds.columnLayout(adj=1, rs=5)

    cmds.text(label='  Selected fileNode : ', al='left')
    cmds.text('selStatus', label='', al='left', w=120)

    cmds.text('  Texture Filter - smooth method', al='left')
    cmds.optionMenu('VMF_menu', w=120, h=25, cc=setVrayTextureFilter)
    cmds.menuItem('Bilinear')
    cmds.menuItem('Bicibuc')
    cmds.menuItem('Biquadratic')

    cmds.text('  Texture input gamma', al='left')
    cmds.optionMenu('VMG_menu', w=120, h=25, cc=setVrayTextureGamma)
    cmds.menuItem('Linear')
    cmds.menuItem('Gamma')
    cmds.menuItem('sRGB')

    cmds.setParent('..')
    cmds.window(windowName, e=1, w=230, h=10)
    cmds.showWindow(windowName)
    fileNodeSelect()
