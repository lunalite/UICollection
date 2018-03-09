"""======================================================

Config file that holds the variables being used.

======================================================"""
import getpass
import os


class Config:
    """========================================
    Change variables below to suit your settings
    ========================================"""

    # Sets the device name of emulator
    # device_name = 'emulator-5554'
    device_name = ''

    # Selecting the data where data is being stored at.
    data_store_location = '../data/'

    # Set the name for widget to number representation
    classwidgetdict = '../data/serverdata/classWidget.txt'

    # Probability of flinging the screen if scrollable is found
    # not flinging, fling up, fling down
    scroll_probability = [0.8, 0.9, 1.0]

    # base storage location for log files
    log_location = '../log/'

    # base storage location for screenshots
    screen_location = '../data/screen/'

    # base storage location for xml files
    xml_location = '../data/xml/'

    # Information location storing number of activities/clickables stored
    info_location = '../log/info'

    # Directory where APKs are stored in for enumerating through them
    current_user = getpass.getuser()
    android_home = str(os.getenv('ANDROID_HOME')) + '/'
    print(android_home)

    """========================================
            End of variable setting
    ========================================"""

    # app_name = apk_selection[selection_num]
    app_name = ''

    def __init__(self):
        pass
