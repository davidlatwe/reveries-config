import os
import uuid
import sys
import getpass
import subprocess

from avalon import io, style
from avalon.vendor.Qt import QtWidgets

from reveries.common.widgets.messagebox import MessageBoxWindow

from . import utils
from .widget import ValidateWidget, USDSetProgressBarWidget

module = sys.modules[__name__]
module.window = None


def build():
    app = QtWidgets.QApplication(sys.argv)

    # Get set group data from shotgun
    asset_getter = utils.GetSetAssets()
    set_data = asset_getter.get_assets()
    if not set_data:
        msg_window = MessageBoxWindow(
            msg_type=QtWidgets.QMessageBox.Critical,
            text=asset_getter.error_msg)
        msg_window.show()
        app.exec_()
        return

    # === Validation for set asset === #
    progressbar_win = USDSetProgressBarWidget()
    progressbar_win.show()

    app.processEvents()

    validate_obj = utils.ValidateSetAsset(set_data)
    validate_data = validate_obj.validate(progressbar_obj=progressbar_win)
    validate_result = validate_obj.validate_result
    progressbar_win.close()

    # Get setGroup name which need to publish
    pub_set_name = list(validate_data.keys())
    if not validate_result:
        print('Show validate widget...')

        window = ValidateWidget(validate_data=validate_data)
        window.show()
        app.exec_()
        if window.skip_pub:
            return

        # Update publish set name data
        pub_set_name = window.get_pub_set()

    # === Generate usd command line === #
    usd_cmds = {}
    usdenv_bat = os.path.abspath(os.path.join(os.path.dirname(__file__), "usdenv.bat"))
    usd_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "core.py"))

    for set_name, _data in validate_data.items():
        _pub_data = {set_name: _data}
        if set_name in pub_set_name:
            tmp_dir = r'C:/Users/{}/tmp/{}'.format(getpass.getuser(), str(uuid.uuid4())[:4])
            usd_save_path = os.path.join(tmp_dir, 'asset_prim.usda').replace("\\", "/")
            json_save_path = os.path.join(tmp_dir, 'subAsset_data.json').replace("\\", "/")

            cmd = [usdenv_bat, usd_file, str(_pub_data), usd_save_path, json_save_path]
            usd_cmds[set_name] = {
                'cmd': cmd,
                'usd_file': usd_save_path,
                'json_file': json_save_path
            }

    # === Submit usd subprocess === #
    i = 1
    progressbar_win = USDSetProgressBarWidget()
    progressbar_win.setBarRange(i, len(list(usd_cmds.keys()))+1)
    progressbar_win.progressbar.setValue(i)
    progressbar_win.show()

    app.processEvents()

    usd_done = {}
    for set_name, info in usd_cmds.items():
        cmd = info.get('cmd', [])
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        print('out: ', set_name, out)

        if 'Set USD Done' in str(out):
            _tmp = {
                set_name: {
                    'usd_file': info.get('usd_file', ''),
                    'json_file': info.get('json_file', '')
                }
            }
            usd_done.setdefault('done', dict()).update(_tmp)
        else:
            usd_done.setdefault('failed', list()).append(set_name)

        i += 1
        progressbar_win.progressbar.setValue(i)

    progressbar_win.close()

    print('usd_done: {}\n'.format(usd_done))

    # === Publish === #
    pub_msg = ''
    pub_msg_text = 'All publish done'
    pub_msg_type = QtWidgets.QMessageBox.Information
    set_group_publisher = utils.PublishSetGroup()
    for set_name, info in usd_done.get('done', {}).items():
        publish_files = [
            info.get('usd_file', ''),
            info.get('json_file', '')
        ]

        _pub_result = set_group_publisher.publish(set_name, publish_files)
        if _pub_result:
            _msg = '{} publish to v{:03}.<br>'.format(set_name, set_group_publisher.version_name)
            pub_msg += _msg
        else:
            pub_msg_type = QtWidgets.QMessageBox.Warning
            pub_msg_text = 'Some setGroup publish failed.'
            pub_msg += '{} publish failed.<br>'.format(set_name)

    if usd_done.get('failed', []):
        pub_msg_type = QtWidgets.QMessageBox.Warning
        pub_msg_text = 'Some setGroup publish failed.'
        pub_msg += '<br>Below setGroup publish failed: <br> {}'.format('<br>'.join(usd_done.get('failed', [])))

    if not usd_done:
        pub_msg_type = QtWidgets.QMessageBox.Critical
        pub_msg_text = 'SetGroup publish failed.'
        print('usd_cmds:', usd_cmds)

    # Show message widgets
    window = MessageBoxWindow(
        msg_type=pub_msg_type,
        window_title='SetGroup Publish Done',
        text=pub_msg_text,
        info_text=pub_msg)
    window.setStyleSheet(style.load_stylesheet())
    window.show()
    app.exec_()


def cli():
    print('\n\nStart running usd set group')

    io.install()
    build()
    print('\n\nDone')
