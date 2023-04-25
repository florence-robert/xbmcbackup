import sys
import xbmc
import xbmcgui
import xbmcvfs
import resources.lib.utils as utils
from resources.lib.backup import XbmcBackup
from resources.lib.authorizers import DropboxAuthorizer
from resources.lib.advanced_editor import AdvancedBackupEditor
from urllib.parse import urlparse, parse_qs
from enum import Enum, auto

# Mode constants
class Mode(Enum):
    BACKUP = auto()
    RESTORE = auto()
    SETTINGS = auto()
    ADVANCED_EDITOR = auto()
    LAUNCHER = auto()

# String constants
STR_OK = utils.getString(30010)
STR_ERROR = utils.getString(30159)
STR_BACKUP = utils.getString(30016)
STR_RESTORE = utils.getString(30017)
STR_SETTINGS = utils.getString(30099)
STR_ADVANCED_EDITOR = utils.getString(30125)
STR_AUTHORIZE_DROPBOX = utils.getString(30027)
STR_AUTHORIZE_SUCCESS = utils.getString(30106)
STR_AUTHORIZE_FAILED = utils.getString(30107)
STR_NO_REMOTE = utils.getString(30045)
STR_REMOVE_AUTH_TITLE = utils.getString(30093)
STR_REMOVE_AUTH_LINE1 = utils.getString(30094)
STR_REMOVE_AUTH_LINE2 = utils.getString(30095)

# Utility functions
def authorize_dropbox():
    """Authorize Dropbox."""
    authorizer = DropboxAuthorizer()
    if authorizer.authorize():
        xbmcgui.Dialog().ok(STR_OK, f'{STR_AUTHORIZE_DROPBOX} {STR_AUTHORIZE_SUCCESS}')
    else:
        xbmcgui.Dialog().ok(STR_OK, f'{STR_AUTHORIZE_FAILED} {STR_AUTHORIZE_DROPBOX}')


def authorize_cloud(cloud_provider):
    """Authorize the specified cloud provider."""
    if cloud_provider == 'dropbox':
        authorize_dropbox()


def remove_auth():
    """Remove authorization for cloud providers."""
    should_delete = xbmcgui.Dialog().yesno(
        STR_REMOVE_AUTH_TITLE,
        f'{STR_REMOVE_AUTH_LINE1}\n{STR_REMOVE_AUTH_LINE2}',
        autoclose=7000
    )

    if should_delete:
        # Delete any of the known token file types
        xbmcvfs.delete(xbmcvfs.translatePath(utils.data_dir() + "tokens.txt"))  # Dropbox
        xbmcvfs.delete(xbmcvfs.translatePath(utils.data_dir() + "google_drive.dat"))  # Google Drive

def get_params():
    """Extract parameters from the command line arguments."""
    try:
        query = urlparse(sys.argv[1]).query
        return {k: v[0] for k, v in parse_qs(query).items()}
    except IndexError:
        return {}

def get_mode(params):
    """Get the mode based on the provided parameters or from the user."""
    if "mode" in params:
        if params['mode'] == 'backup':
            return Mode.BACKUP
        elif params['mode'] == 'restore':
            return Mode.RESTORE
        elif params['mode'] == 'launcher':
            return Mode.LAUNCHER

    # If mode wasn't passed in as arg, get from user
    options = [STR_BACKUP, STR_RESTORE, STR_SETTINGS]

    # Check if we're using the advanced editor
    if utils.getSettingInt('backup_selection_type') == 1:
        options.append(STR_ADVANCED_EDITOR)

    # Get the mode from the user
    selected_mode = xbmcgui.Dialog().select(STR_OK, options)
    return Mode(selected_mode) if selected_mode != -1 else None


def handle_no_remote_configured():
    """Handle the case when remote is not configured."""
    xbmcgui.Dialog().ok(STR_OK, STR_NO_REMOTE)
    utils.openSettings()


def handle_backup():
    """Handle the backup operation."""
    backup = XbmcBackup()

    if not backup.remoteConfigured():
        handle_no_remote_configured()
        return

    backup.backup()

def handle_restore(params):
    """Handle the restore operation."""
    backup = XbmcBackup()

    if not backup.remoteConfigured():
        handle_no_remote_configured()
        return

    restore_points = backup.listBackups()
    point_names = []
    folder_names = []

    for a_dir in restore_points:
        point_names.append(a_dir[1])
        folder_names.append(a_dir[0])

    selected_restore = -1

    if "archive" in params:
        if params['archive'] in folder_names:
            selected_restore = folder_names.index(params['archive'])
            utils.log(f'{selected_restore} : {params["archive"]}')
        else:
            utils.showNotification(STR_NO_REMOTE)
            utils.log(f'{params["archive"]} is not a valid restore point')
    else:
        selected_restore = xbmcgui.Dialog().select(STR_OK, point_names)

    if selected_restore != -1:
        backup.selectRestore(restore_points[selected_restore][0])

    if 'sets' in params:
        backup.restore(selectedSets=params['sets'].split('|'))
    else:
        backup.restore()


def handle_settings():
    """Handle the settings operation."""
    utils.openSettings()


def handle_advanced_editor():
    """Handle the advanced editor operation."""
    if utils.getSettingInt('backup_selection_type') == 1:
        editor = AdvancedBackupEditor()
        editor.showMainScreen()


def handle_launcher(params):
    """Handle the launcher operation."""
    launcher_actions = {
        'authorize_cloud': lambda: authorize_cloud(params['provider']),
        'remove_auth': remove_auth,
        'advanced_editor': handle_advanced_editor,
        'advanced_copy_config': AdvancedBackupEditor().copySimpleConfig
    }

    action = params['action']
    if action in launcher_actions:
        launcher_actions[action]()
    else:
        xbmcgui.Dialog().ok(STR_OK, f'{STR_ERROR} {params["action"]}')


def main():
    """Main function to handle the operations."""
    try:
        mode_functions = {
            Mode.BACKUP: handle_backup,
            Mode.RESTORE: handle_restore,
            Mode.SETTINGS: handle_settings,
            Mode.ADVANCED_EDITOR: handle_advanced_editor,
            Mode.LAUNCHER: handle_launcher,
        }

        params = get_params()
        mode = get_mode(params)
        if mode in mode_functions:
            mode_functions[mode](params)
        else:
            xbmcgui.Dialog().ok(STR_OK, f'{STR_ERROR} {mode}')
    except Exception as e:
        utils.log(f'Error: {e}', loglevel=xbmc.LOGERROR)
        xbmcgui.Dialog().ok(STR_OK, f'{STR_ERROR} {e}')


if __name__ == "__main__":
    main()
