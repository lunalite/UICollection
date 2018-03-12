import hashlib
import json
import logging
import operator
import os
import random
import re
import signal
import string
import subprocess
import xml.etree.ElementTree as ET

import time

from crawler.Config import Config

logger = logging.getLogger(__name__)


def get_state(device, pn):
    os.makedirs(os.path.dirname(Config.classwidgetdict), exist_ok=True)

    try:
        with open(Config.classwidgetdict, 'r') as f:
            content = json.load(f)
            dict_of_widget = content
    except FileNotFoundError:
        dict_of_widget = {}

    def get_bit_rep(pn):
        xml = device.dump(compressed=False)
        root = ET.fromstring(xml.encode('utf-8'))
        bit_rep = ''
        btn_rep = ''
        for element in root.iter('node'):
            bit_rep += element.get('index')
            btn_rep += str(dict_of_widget[element.attrib['class']])

        return bit_rep, btn_rep

    try:
        final_rep = get_bit_rep(pn)
        key = final_rep[0] + final_rep[1]
        hash_key = hashlib.md5(key.encode('utf-8'))
        return pn + '-' + hash_key.hexdigest()
    except KeyError:
        get_class_dict(device, Config.classwidgetdict)
        return get_state(device, pn)


def create_child_to_parent(dump):
    dump = dump.encode('ascii', 'replace')
    tree = ET.fromstring(dump)
    pmap = dict((c, p) for p in tree.iter() for c in p)
    return pmap


def get_parent_with_key(key, _parent_map):
    for child, parent in _parent_map.items():
        if key == xml_btn_to_key(child) and child.attrib['clickable'] == 'true':
            return parent
    return -1
    # raise Exception('No parent when getting parent with bound')


def get_siblings(p):
    siblings = []
    for sibling in p:
        siblings.append(sibling)
    return siblings


def get_children(p):
    children = []
    for child in p[0]:
        children.append(child)
    return children


def get_bounds_from_key(key):
    m = re.findall('({.*?})', key)
    return m[-1][1:-1]


def btn_to_key(btn):
    """deprecated. Use btn_info_to_key() instead"""
    signal.alarm(5)
    try:
        info = btn.info
        cd = '' if info['contentDescription'] is None else str(info['contentDescription'])
        key = '{' + info['className'].split('.')[-1] + '}-{' + cd + '}-{' + convert_bounds(btn) + '}'
        return key
    finally:
        signal.alarm(0)


def btn_info_to_key(btn_info):
    signal.alarm(5)
    try:
        info = btn_info
        cd = '' if info['contentDescription'] is None else str(info['contentDescription'])
        key = '{' + info['className'].split('.')[-1] + '}-{' + cd + '}-{' + convert_bounds_with_node_info(
            info['bounds']) + '}'
        return key
    finally:
        signal.alarm(0)


def xml_btn_to_key(xml_btn):
    if xml_btn == -1:
        return None
    info = xml_btn.attrib
    # return info
    cd = '' if info['content-desc'] is None else str(info['content-desc'])
    key = '{' + info['class'].split('.')[-1] + '}-{' + cd + '}-{' + info['bounds'] + '}'
    return key


def convert_bounds_with_node_info(node):
    sbound = ''
    bounds = node
    sbound += '[' + str(bounds['left']) + ',' + str(bounds['top']) + '][' + str(bounds['right']) + ',' + str(
        bounds['bottom']) + ']'
    return sbound


def convert_bounds(node):
    sbound = ''
    if hasattr(node, 'info'):
        bounds = node.info['bounds']
        sbound += '[' + str(bounds['left']) + ',' + str(bounds['top']) + '][' + str(bounds['right']) + ',' + str(
            bounds['bottom']) + ']'
    else:
        logger.warning('No "info" in node')
    return sbound


def get_package_name(d):
    info = d.info
    return info['currentPackageName']


def get_text():
    # TODO: Improve the way text is chosen
    return ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=10))


def dump_log(d, packname, state):
    screen_directory = Config.screen_location + packname + '/'
    xml_directory = Config.xml_location + packname + '/'

    if not os.path.exists(screen_directory):
        os.makedirs(screen_directory)
    else:
        if not os.path.isfile(screen_directory + state + '.png'):
            d.screenshot(screen_directory + state + '.png')

    if not os.path.exists(xml_directory):
        os.makedirs(xml_directory)
    else:
        if not os.path.isfile(xml_directory + state + '.png'):
            d.dump(xml_directory + state + '.xml', compressed=False)


def start_emulator(avdnum, emuname, window_sel):
    """
    Starts the emulator using the size 480x800 to save space. At the same time, it will check if the emulator has booted
    up properly before returning.
    :param avdnum: avd number of the emulator
    :param emuname: emulator name.
    :param window_sel: Window selection, if true, then spawns emulator. Otherwise, return a windowless emulator.
    :return: 1 when the process is done.
    """
    while True:
        android_home = Config.android_home
        # Have to ensure adb is added to environment variable.
        adb_location_msg = subprocess.Popen(
            [android_home + 'platform-tools/adb', '-s', emuname, 'shell', 'getprop', 'init.svc.bootanim'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        bootmsg = adb_location_msg.communicate()
        if bootmsg[0] == b'stopped\n':
            time.sleep(3)
            subprocess.Popen(
                [android_home + 'platform-tools/adb', '-s', emuname, 'shell', 'rm', '-r', '/mnt/sdcard/*'])
            return 1
        elif len(re.findall('not found', bootmsg[1].decode('utf-8'))) >= 1:
            if window_sel:
                subprocess.Popen(
                    [android_home + 'emulator/emulator', '-avd', avdnum, '-wipe-data', '-skin', '480x800', '-port',
                     emuname[-4:]],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            elif not window_sel:
                subprocess.Popen(
                    [android_home + 'emulator/emulator', '-avd', avdnum, '-wipe-data', '-skin', '480x800', '-no-audio',
                     '-no-window', '-port',
                     emuname[-4:]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(10)
        else:
            logger.info('Waiting for emulator to start...')
            time.sleep(5)


def stop_emulator(emuname):
    android_home = Config.android_home
    """
    Stop the emulator with the name emuname
    :param emuname: Emulator name which is to be stopped.
    :return: None
    """
    subprocess.Popen([android_home + 'platform-tools/adb', '-s', emuname, 'emu', 'kill'])
    return None
