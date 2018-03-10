import codecs
import logging
import random
import re
import signal
import socket
import string
import subprocess
import time
import os
import sys

import uiautomator

from uiautomator import Device
from datetime import datetime
from crawler.Config import Config
from crawler import Utility
from enum import Enum

log_location = Config.log_location

os.makedirs(os.path.dirname(log_location), exist_ok=True)
logging.basicConfig(filename=log_location + 'main-' + sys.argv[1] + '.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)
logging.getLogger().addHandler(logging.StreamHandler())
logging.info('================Begin logging==================')

now = time.strftime("%c")
logger.info(now)

activities = {}
clickables = {}
click_hash = {}
scores = {}
visited = {}
parent_map = {}
zero_counter = 0
horizontal_counter = 0
no_clickable_btns_counter = 0
android_home = Config.android_home

def signal_handler(signum, frame):
    logger.info("timeout call...")
    raise Exception('timeout.')


signal.signal(signal.SIGALRM, signal_handler)


class APP_STATE(Enum):
    SCROLLING = 11
    KEYBOARDINT = -1
    FAILTOSTART = -2
    KEYERROR = -3
    INDEXERROR = -4
    CRASHED = -5
    DEADLOCK = -6
    TIMEOUT = -70
    SOCKTIMEOUTERROR = -71
    JSONRPCERROR = -8
    FAILTOCLICK = -9
    UNK = -10


def init():
    """
    Initializing all global variables back to its original state after every testing is done on APK
    :return:
    """
    global clickables, scores, visited, parent_map, activities, click_hash, zero_counter
    activities.clear()
    clickables.clear()
    click_hash.clear()
    scores.clear()
    visited.clear()
    parent_map.clear()
    zero_counter = 0


def click_button(new_click_els, pack_name):
    # Have to use packageName since there might be buttons leading to popups,
    # which can continue exploding into more activity if not limited.
    global d, parent_map, visited, scores, mask, zero_counter, no_clickable_btns_counter, horizontal_counter
    old_state = Utility.get_state(d, pack_name)

    click_els = d(clickable='true', packageName=pack_name) if new_click_els is None else new_click_els
    btn_result = make_decision(click_els)

    if btn_result == -1 or zero_counter >= 5 or no_clickable_btns_counter >= 5:

        print('no clickable1 : {}'.format(no_clickable_btns_counter))
        if no_clickable_btns_counter >= 5:
            return None, None, APP_STATE.DEADLOCK
        elif zero_counter >= 30:
            return None, None, APP_STATE.DEADLOCK

        try:
            # Check if more states available when swiping it
            # For the case of apps where there's horizontal motion with 4 panes usually.
            for i in range(5):
                d(scrollable=True).fling.horiz.forward()
        except uiautomator.JsonRPCError:
            logger.info("Can't scroll horizontal.")
            horizontal_counter += 1
            if horizontal_counter >= 5:
                raise Exception('Tried scrolling horizontal 5 times but fail so stop.')
        finally:
            new_state = Utility.get_state(d, pack_name)
            if new_state != old_state:
                return None, new_state, 1
            d.press('back')

            # Issue with clicking back button prematurely
            if Utility.get_package_name(d) == 'com.google.android.apps.nexuslauncher':
                subprocess.Popen(
                    ['adb', '-s', device_name, 'shell', 'monkey', '-p', pack_name, '5'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            return None, Utility.get_state(d, pack_name), 1
    else:
        try:
            if click_els[btn_result].exists:
                click_btn_info = click_els[btn_result].info
                click_btn_class = click_btn_info['className']
                click_btn = click_els[btn_result]

                # Check if the key of button to be clicked is equal to the key of button stored in clickables
                click_btn.click.wait()

                # If the button that is clicked is EditText or TextView, it might cause autocomplete tab to appear
                # We have to add this to close the tab that appears.
                if click_btn_class == 'android.widget.EditText' or click_btn_class == 'android.widget.TextView':
                    click_els = d(clickable='true', packageName=pack_name)

                    for i in click_els:
                        if i.info['text'] == 'ADD TO DICTIONARY':
                            click_els[0].click.wait()
                            break

                new_state = Utility.get_state(d, pack_name)

                if new_state != old_state:
                    return new_click_els, new_state, 1
                else:
                    # No change in state so give it a score of 0 since it doesn't affect anything
                    return click_els, new_state, 1
            else:
                raise Exception('Warning, no such buttons available in click_button()')
        except IndexError:
            logger.info('@@@@@@@@@@@@@@@=============================')
            logger.info("Index error with finding right button to click. Restarting...")
            logger.warning(len(click_els))
            logger.warning(len(visited[old_state]))
            logger.warning(btn_result)
            raise IndexError('')


def make_decision(click_els):
    global zero_counter, no_clickable_btns_counter
    if len(click_els) == 0:
        logger.info('No clickable buttons available. Returning -1.')
        zero_counter = 0
        print('no clickable2 : {}'.format(no_clickable_btns_counter))
        no_clickable_btns_counter += 1
        return -1
    elif len(click_els) == 1:
        logger.info('One clickable button available. Returning 0.')
        zero_counter += 1
        return 0
    else:
        return int(random.uniform(0, len(click_els)))


def main(app_name, pack_name):
    global clickables, scores, visited, parent_map, activities
    d.press('home')

    logger.info('Force stopping ' + pack_name + ' to reset states')
    subprocess.Popen([android_home + 'platform-tools/adb', '-s', device_name, 'shell', 'am', 'force-stop', pack_name])
    logger.info('Starting ' + pack_name + ' using monkey...')
    msg = subprocess.Popen(
        [android_home + 'platform-tools/adb', '-s', device_name, 'shell', 'monkey', '-p', pack_name, '5'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    startmsg = msg.communicate()[0].decode('utf-8')
    if len(re.findall('No activities found to run', startmsg)) > 0:
        return APP_STATE.FAILTOSTART

    # To ensure that loading page and everything is done before starting testing
    logger.info('Wait 10 seconds for loading of APK.')
    time.sleep(5)

    old_state = Utility.get_state(d, pack_name)

    def rec(local_state):
        global parent_map

        if Utility.get_package_name(d) == 'com.google.android.apps.nexuslauncher':
            # If the current activity is in the main nexus page
            return -2, local_state

        elif Utility.get_package_name(d) != pack_name:
            initstate = Utility.get_state(d, pack_name)
            d.press('back')
            nextstate = Utility.get_state(d, pack_name)
            if nextstate != initstate:
                return -1, nextstate

            # Prepare for the situation of when pressing back button doesn't work
            elif nextstate == initstate:
                localc = 0
                while True:
                    tryclick_btns = d(clickable='true')
                    rand_btn = random.choice(tryclick_btns)
                    rand_btn.click.wait()
                    nextstate = Utility.get_state(d, pack_name)

                    # Check if app has crashed. If it is, restart
                    crashapp = d(clickable='true', packageName='android')
                    for i in crashapp:
                        if i.info['resourceName'] == 'android:id/aerr_restart' \
                                or i.info['resourceName'] == 'android:id/aerr_close':
                            return APP_STATE.CRASHED, nextstate

                    if localc > 2:
                        return APP_STATE.UNK, nextstate
                    if nextstate != initstate:
                        return -1, nextstate
                    localc += 1

        Utility.dump_log(d, pack_name, local_state)
        return 1, local_state

    recvalue, new_state = rec(old_state)
    if recvalue == APP_STATE.CRASHED:
        return APP_STATE.CRASHED

    new_click_els = None
    counter = 0

    while True:
        signal.alarm(60)
        try:
            edit_btns = d(clickable='true', packageName=pack_name)
            for i in edit_btns:
                # Setting of the text.
                i.set_text(Utility.get_text())

            if d(scrollable='true').exists:
                r = random.uniform(0, Config.scroll_probability[2])
                if r < Config.scroll_probability[0]:
                    new_click_els, new_state, state_info = click_button(new_click_els, pack_name)
                else:
                    logger.info('Scrolling...')
                    if r < Config.scroll_probability[1]:
                        d(scrollable='true').fling()
                    elif r < Config.scroll_probability[2]:
                        d(scrollable='true').fling.backward()

                    new_state = Utility.get_state(d, pack_name)
                    new_click_els = d(clickable='true', packageName=pack_name)
                    state_info = APP_STATE.SCROLLING
            else:
                new_click_els, new_state, state_info = click_button(new_click_els, pack_name)

            logger.info('Number of iterations: ' + str(counter))
            logger.info('state_info is ' + str(state_info))
            if state_info == APP_STATE.CRASHED:
                return APP_STATE.CRASHED
            elif state_info == APP_STATE.DEADLOCK:
                return APP_STATE.DEADLOCK
            elif state_info == APP_STATE.FAILTOCLICK:
                return APP_STATE.FAILTOCLICK

            if new_state != old_state and (new_state not in scores or new_state not in visited):
                recvalue = -1
                while recvalue == -1:
                    recvalue, new_state = rec(new_state)
                    if new_state in scores:
                        recvalue = 1
                    if recvalue == APP_STATE.UNK:
                        recvalue = 1

            counter += 1
            if counter >= 300:
                return 1

        except KeyboardInterrupt:
            logger.info('@@@@@@@@@@@@@@@=============================')
            logger.info('KeyboardInterrupt...')
            return APP_STATE.KEYBOARDINT
        except KeyError:
            logger.info('@@@@@@@@@@@@@@@=============================')
            logger.info('Crash')
            return APP_STATE.KEYERROR
        except IndexError:
            logger.info('@@@@@@@@@@@@@@@=============================')
            logger.info('IndexError...')
            return APP_STATE.INDEXERROR
        except TimeoutError:
            logger.info('@@@@@@@@@@@@@@@=============================')
            logger.info('Timeout...')
            return APP_STATE.TIMEOUT
        except uiautomator.JsonRPCError:
            logger.info('@@@@@@@@@@@@@@@=============================')
            logger.info('JSONRPCError...')
            return APP_STATE.JSONRPCERROR
        except socket.timeout:
            logger.info('@@@@@@@@@@@@@@@=============================')
            logger.info('Socket timeout error...')
            return APP_STATE.SOCKTIMEOUTERROR
        finally:
            signal.alarm(0)
            Utility.dump_log(d, pack_name, Utility.get_state(d, pack_name))


def official(_apkdir):
    global no_clickable_btns_counter

    dir = _apkdir

    with open(apklist, 'r') as f:
        apks_to_test = [line.rstrip() for line in f]
    timestr = time.strftime("%Y%m%d%H%M%S")

    info_location = Config.info_location
    if not os.path.exists(info_location):
        os.makedirs(info_location)
    file = codecs.open(info_location + '/information-' + timestr + '.txt', 'w', 'utf-8')

    no_apks_tested = 0
    start_time = datetime.now()
    for i in apks_to_test:
        english = True
        attempts = 0
        m = re.findall('^(.*)_.*\.apk', i)
        apk_packname = m[0]

        ''' Get the application name from badge. '''
        try:
            ps = subprocess.Popen([android_home + 'build-tools/26.0.1/aapt', 'dump', 'badging', dir + i],
                                  stdout=subprocess.PIPE)
            output = subprocess.check_output(('grep', 'application-label:'), stdin=ps.stdout)
            label = output.decode('utf-8')
        except subprocess.CalledProcessError:
            logger.info("No android application available.")
            label = 'application-label: unknown APK.'

        m = re.findall('^application-label:(.*)$', label)
        appname = m[0][1:-1]

        Config.app_name = appname

        ''' Check if there is non-ASCII character. '''
        for scii in m[0]:
            if scii not in string.printable:
                logger.info('There is a non-ASCII character in application name. Stop immediately.\n')
                file.write('|' + apk_packname + '|' + 'Non-ASCII character detected in appname.' '\n')
                english = False
                break

        if english:
            ''' Start installation of the APK '''
            x = subprocess.Popen([android_home + 'platform-tools/adb', '-s', device_name, 'install', dir + i],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            installmsg = x.communicate()[1].decode('utf-8')
            if len(re.findall('Success', installmsg)) > 0:
                logger.info("Installed success: " + apk_packname + ' APK.')
                pass
            if len(re.findall('INSTALL_FAILED_ALREADY_EXISTS', installmsg)) > 0:
                logger.info("Already exists: " + apk_packname + ' APK.')
                pass
            elif len(re.findall('INSTALL_FAILED_NO_MATCHING_ABIS', installmsg)) > 0:
                logger.info('No Matching ABIs: ' + apk_packname + ' APK.')
                file.write('|' + apk_packname + '|' + 'Failed to install; no matching ABIs' '\n')
                continue
            else:
                pass

            logger.info('\nDoing a UI testing on application ' + appname + '.')

            init()
            no_clickable_btns_counter = 0
            while attempts <= 3:
                signal.alarm(60)
                try:
                    retvalue = main(appname, apk_packname)
                    if retvalue == APP_STATE.FAILTOSTART:
                        logger.info("Fail to start application using monkey.")
                        file.write('|' + apk_packname + '|' + 'Failed to start application using monkey.' '\n')
                        break
                    elif retvalue == APP_STATE.KEYERROR:
                        logger.info("Keyerror crash.")
                        file.write('|' + apk_packname + '|' + 'Crashed - KeyError' '\n')
                    elif retvalue == APP_STATE.INDEXERROR:
                        logger.info("Indexerror crash.")
                        file.write('|' + apk_packname + '|' + 'Crashed - IndexError' '\n')
                    elif retvalue == APP_STATE.CRASHED:
                        logger.info("App crashed")
                        file.write('|' + apk_packname + '|' + 'Crashed - UnknownError' '\n')
                        break
                    elif retvalue == APP_STATE.DEADLOCK:
                        logger.info("Dead lock. Restarting...")
                    elif retvalue == APP_STATE.FAILTOCLICK:
                        logger.info("Fail to click. Restarting...")
                    elif retvalue == APP_STATE.TIMEOUT:
                        logger.info("Timeout. Restarting...")
                    elif retvalue == APP_STATE.JSONRPCERROR:
                        logger.info("JSONRPCError. Restarting...")
                    elif retvalue == APP_STATE.SOCKTIMEOUTERROR:
                        logger.info("Socket timeout. Restarting...")
                    elif retvalue == APP_STATE.KEYBOARDINT:
                        logger.info("keyboard interrupt. Restarting...")
                except BaseException as e:
                    if re.match('timeout', str(e), re.IGNORECASE):
                        logger.info("Timeout from nothing happening. Restarting... ")
                    else:
                        logger.info("Unknown exception." + str(e))
                        raise Exception(e)
                finally:
                    signal.alarm(0)
                    attempts += 1
                    logger.info('==========================================')
                    new_time = datetime.now()
                    logger.info('Current time is ' + str(new_time))
                    logger.info('Time elapsed: ' + str(new_time - start_time))
                    logger.info('Last APK tested is: {}'.format(apk_packname))
                    logger.info('==========================================')

            logger.info('Force stopping ' + apk_packname + ' to end test for the APK')
            subprocess.Popen(
                [android_home + 'platform-tools/adb', '-s', device_name, 'shell', 'am', 'force-stop', apk_packname])

            subprocess.Popen([android_home + 'platform-tools/adb', '-s', device_name, 'uninstall', apk_packname],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info('Uninstalled ' + apk_packname)
            logger.info('@@@@@@@@@@@ End ' + apk_packname + ' APK @@@@@@@@@@@')

        no_apks_tested += 1
        if no_apks_tested % 50 == 0:
            logger.info('Total apks tested: {}'.format(no_apks_tested))
            logger.info('Restarting emulator...')
            Utility.stop_emulator(device_name)
            time.sleep(10)
            Utility.start_emulator(avdname, device_name)

            logger.info('==========================================')
            new_time = datetime.now()
            logger.info('Current time is ' + str(new_time))
            logger.info('Time elapsed: ' + str(new_time - start_time))
            logger.info('Last APK tested is: {}'.format(apk_packname))
            logger.info('==========================================')


try:
    """
    device_name e.g. emulator-5554
    apklist e.g. directory-to-apk-x
    avdname e.g, avd0
    e.g. python3 Main.py emulator-5554 ../apk/apk-0 avd0
    """
    device_name = sys.argv[1]
    apklist = sys.argv[2]
    apkdir = sys.argv[3]
    avdname = sys.argv[4]
    d = Device(device_name)

    Utility.start_emulator(avdname, device_name, window_sel=True)
    official(_apkdir=apkdir)

except Exception as e:
    logging.exception("message")
