import sys
import getpass
import subprocess

from avalon import io, api, style
from avalon.tools import lib as tools_lib
# from avalon.vendor.Qt import QtWidgets

from reveries.common.widgets.messagebox import MessageBoxWindow
from reveries.common.publish import publish_subset, \
    publish_version, \
    publish_representation, \
    publish_asset
from .utils import get_set_assets
# from .core import BuildSetGroupUSD


module = sys.modules[__name__]
module.window = None


def _show_msg_widget(msg_type=None):
    try:
        module.window.close()
        del module.window
    except (RuntimeError, AttributeError):
        pass

    with tools_lib.application():
        window = MessageBoxWindow(
            msg_type=msg_type,
            window_title='Update USD Set Group Log',
            text='Update log as below:',
            info_text='All done',
            detail_text='All good.'
        )
        window.setStyleSheet(style.load_stylesheet())
        window.show()

        module.window = window


def build():
    from avalon.vendor.Qt import QtWidgets

    result, set_data = get_set_assets()
    if not result:
        msg_type = QtWidgets.QMessageBox.Critical
        _show_msg_widget(msg_type=msg_type)

    if set_data:
        # Check set already in db:
        for set_name, chilren in set_data.items():
            _filter = {"type": "asset", "name": set_name}
            _set_data = io.find_one(_filter)
            if not _set_data:
                print('set {} not in db'.format(set_name))
                publish_asset.publish(set_name, 'Set')
    print('set_data: ', set_data)
    print('\n\n')

    # Submit usd subprocess
    usdenv_bat = r'F:\usd\test\usd_avalon\reveries-config\reveries\tools\usd_set_group\usdenv.bat'
    usd_file = r'F:\usd\test\usd_avalon\reveries-config\reveries\tools\usd_set_group\core.py'
    set_data = {
        'BillboardGroup': {
            'BillboardA': r'Q:\199909_AvalonPlay\Avalon\PropBox\BoxB\publish\assetPrim\v002\USD\asset_prim.usda',
            'BillboardB': r'Q:\199909_AvalonPlay\Avalon\PropBox\BoxB\publish\assetPrim\v002\USD\asset_prim.usda'
        }
    }
    save_path = r'C:/Users/rebeccalin209/Desktop/aa.usda'
    cmd = [usdenv_bat, usd_file, str(set_data), save_path]

    print('open usdenv cmd: {}\n\n'.format(cmd))

    # p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # out, err = p.communicate()
    # print('out: ', out)

    # # Show message widgets
    # try:
    #     module.window.close()
    #     del module.window
    # except (RuntimeError, AttributeError):
    #     pass
    #
    # with tools_lib.application():
    #     window = MessageBoxWindow(
    #         window_title='Update USD Set Group Log',
    #         text='Update log as below:',
    #         info_text='All done',
    #         detail_text='All good.'
    #     )
    #     window.setStyleSheet(style.load_stylesheet())
    #     window.show()
    #
    #     module.window = window


def _publish():
    #
    asset_name = 'BoxB'
    asset_data = io.find_one({
        "type": "asset",
        "name": asset_name
    })

    # === Publish subset === #
    subset_name = 'setDefault'
    families = ['reveries.model']
    subset_id = publish_subset.publish(asset_data['_id'], subset_name, families)

    # === Publish version === #
    version_id = publish_version.publish(subset_id)

    # === Publish representation === #
    name = 'USD'
    reps_data = {'entryFileName': 'geom.usda'}
    reps_id = publish_representation.publish(version_id, name, data=reps_data)


def cli():
    print('\n\nStart running usd set group')

    io.install()
    build()
    print('\n\nDone')
