import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from contextlib import contextmanager
from os.path import abspath, dirname
from urllib import urlencode, quote
from resolveurl.hmf import HostedMediaFile
import resolveurl
from resolveurl.lib.net import Net, get_ua
import requests
import base64

_plugin_url = sys.argv[0]
_handle = int(sys.argv[1])
_dialog = xbmcgui.Dialog()

profile_dir = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))

def debug(s):
    xbmc.log(str(s), xbmc.LOGDEBUG)

def error(s):
    xbmc.log(str(s), xbmc.LOGERROR)

def webread(url):
    if type(url) is unicode:
        url = url.encode('utf8')
    url = quote(url, ':/')

    net = Net()
    headers = {'User-Agent': get_ua()}
    return net.http_GET(url, headers=headers).content

def action_url(action, **action_args):
    action_args['action'] = action
    for k, v in action_args.items():
        if type(v) is unicode:
            action_args[k] = v.encode('utf8')
    qs = urlencode(action_args)
    return _plugin_url + '?' + qs

def add_item(diritem):
    xbmcplugin.addDirectoryItem(**diritem)

def end_dir():
    xbmcplugin.endOfDirectory(_handle)

def diritem(label_or_stringid, url, image='', isfolder=True, context_menu=[]):
    if type(label_or_stringid) is int:
        label = xbmcaddon.Addon().getLocalizedString(label_or_stringid)
    else:
        label = label_or_stringid
    listitem = xbmcgui.ListItem(label, iconImage=image)
    listitem.addContextMenuItems(context_menu, replaceItems=True)
    # this is unpackable for xbmcplugin.addDirectoryItem
    return dict(
        handle   = _handle,
        url      = url,
        listitem = listitem,
        isFolder = isfolder
    )

def popup(s):
    addon_name = xbmcaddon.Addon().getAddonInfo('name')
    try:
        # Gotham (13.0) and later
        _dialog.notification(addon_name, s)
    except AttributeError:
        _dialog.ok(addon_name, s)

def select(heading, options):
    return _dialog.select(heading, options)

def resolve(url):
    resolved_url = ""
    if 'google' in url and 'googlevideo' not in url:
        resolved_url = url
    else:
        if type(url) is unicode:
            url = url.encode('utf8')
        url = quote(url, ':/')

        # import the resolvers so that resolveurls pick them up
        import lib.resolvers
        hmf = HostedMediaFile(url)
        if hmf:
            resolved_url = hmf.resolve()

    return resolved_url

def sleep(ms):
    xbmc.sleep(ms)

def back_dir():
    # back one directory
    xbmc.executebuiltin('Action(ParentDir)')

def refresh():
    # refresh directory
    xbmc.executebuiltin('Container.Refresh')

def run_plugin(url):
    xbmc.executebuiltin(run_plugin_builtin_url(url))

def run_plugin_builtin_url(url):
    return 'RunPlugin(%s)' % url

def input(heading):
    kb = xbmc.Keyboard(default='', heading=heading)
    kb.doModal()
    if kb.isConfirmed():
        return kb.getText()
    return None

@contextmanager
def busy_indicator():
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    try:
        yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialog)')

def mirrors_request(data_dict, b_url):
    #defining stuff for the request
    request_payload = {'VB_TOKEN': data_dict['token'], 'VB_ID': data_dict['id'], 'VB_NAME': 1, 'VB_U': 1}
    request_headers = {
        'Accept': "*/*",
        'Accept-Encoding': "gzip, deflate",
        'Accept-Language': "en-US,en;q=0.9",
        'Connection': "keep-alive",
        'Content-Length': str(sys.getsizeof(request_payload)),
        'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
        'Host': "vb.icdrama.to",
        'Origin': b_url,
        'User-Agent': get_ua()
        }

    #post request
    post_response = requests.post(data_dict['post_url'], headers=request_headers, data=request_payload)

    #raise exceptions to kodi/higher level? not sure how requests exceptions will be handled
    post_response.raise_for_status()

    # decode links after first 4 entries
    mirror_list = post_response.json()[1][4:]
    for mirror in mirror_list:
        mirror['u'] = base64.b64decode(mirror['u']).encode('utf-8')

    return mirror_list
