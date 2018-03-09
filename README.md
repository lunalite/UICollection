# UICollection
Automated Android UI element collection tool

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

The following are required for the crawler to be deployed:
* Android SDK
* Python 3.6
* OS must be able to run virtual machines.

### Installing

1. Install android SDK
    You can get android SDK by installing [Android Studio](https://developer.android.com/studio/index.html) or by doing it the [manual way](https://github.com/codepath/android_guides/wiki/Installing-Android-SDK-Tools). 
    
    The manual way of installation is as follow:
        
    ```bash
    wget https://dl.google.com/android/repository/sdk-tools-darwin-3859397.zip -P /tmp/;
    unzip /tmp/sdk-tools-darwin-3859397.zip -d ~/android-sdk;
    cd ~/android-sdk/tools/bin;
    yes | ./sdkmanager --licenses;
    ./sdkmanager --update;
    ./sdkmanager "build-tools;26.0.1";
    ```

2. Setup the environment for adb, emulator
    Add the environment variable ANDROID_HOME by finding out where the android sdk home is located.

    ```bash
    export ANDROID_HOME=~/android-sdk
    
    ```

3. run pip install requirements
    ```bash
    pip install -r requirements.txt
    ```

4. Change config.

    

5. Create emulators
    Find the sdkmanager within `$ANDROID_HOME/tools/bin`
    ```bash
    $ANDROID_HOME/tools/bin/sdkmanager "system-images;android-26;google_apis;x86"
    ```
    This is done to install the relevant package image which is used to set up the Android emulator. Do note that you can use your own preferred image in this case. To list the available images, just run
     
    ```bash
    $ANDROID_HOME/tools/bin/sdkmanager --list
    ```
    
    The next step is to create an Android Virtual Device (AVD) for the emulator using the preset image.  
    ```bash
    echo no | $ANDROID_HOME/tools/bin/avdmanager create avd -n avd0 -b x86 -k "system-images;android-26;google_apis;x86" --abi google_apis/x86 
    ```
    In our case, we name it `avd0`. Do take note of the name as we will be using it later on.
    
    Try running the emulator to see if it works.
    ```bash
    $ANDROID_HOME/emulator/emulator -avd avd0
    ```
    
    If the following error occurs: `PANIC: Broken AVD system path. Check your ANDROID_SDK_ROOT value`, check that in your android-sdk folder, there contains the following directories: `emulator`, `platforms`, `platform-tools`, `system-images`. If any of the following doesn't exist, just make an empty directory. More information can be found [here](https://stackoverflow.com/questions/39645178/panic-broken-avd-system-path-check-your-android-sdk-root-value). 

6. Run main and wait.
    Ensure that you are in the folder which you cloned.
    ```bash
    cd crawler && export PYTHONPATH=..; python3 main.py emulator-5554 ../../apk/apk-0 ../../apk2/ avd0 
    ```
    - emulator-5554 represents the name of the emulator, with the numbering '5554' used as the port number to connect from. Typically, it will be in the form emulator-PPPP with PPPP representing port number incremented by two (so emulator-5556, emulator-5558, ...). 
    - ../../apk/apk-0 represents the list of APK which we will be installing into the emulator before crawling happens. 
    - ../../apk2/ will be the directory where all the APKs are located at.
    - avd0 will be the name given to the AVD previously in step 5.
     
