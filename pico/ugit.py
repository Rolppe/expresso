# Import libraries
import os
import urequests
import json
import machine
import time
import network
import ntptime

# Import files
from machine import Pin
from secrets import ssid, password, github_user, github_repo, github_token

# Set default branch to 'developement. Stable at 'master'
default_branch = 'developement'

# Set ignored files
ignore_files = ['ugit.py', 'secrets.py', '.DS_Store', 'ugit_log.txt']
ignore = ignore_files

# Set git url
giturl = f'https://github.com/{github_user}/{github_repo}'

# Set commit url
commit_url = f'https://api.github.com/repos/{github_user}/{github_repo}/commits/{default_branch}'

# Set call trees
call_trees_url = f'https://api.github.com/repos/{github_user}/{github_repo}/git/trees/{default_branch}?recursive=1'

# Set raw url
raw = f'https://raw.githubusercontent.com/{github_user}/{github_repo}/{default_branch}/'


# Function to get latest commit hash and message
def get_latest_commit_hash_and_message():

    # Set headers with User-Agent
    headers = {'User-Agent': 'ota-pico'}

    # If github_token length > 0, add authorization header
    if len(github_token) > 0:

        # Set authorization header with bearer token
        headers['authorization'] = f"bearer {github_token}"

    # Make GET request to commit_url with headers
    r = urequests.get(commit_url, headers=headers)

    # Load JSON data from response 
    data = json.loads(r.content.decode('utf-8'))

    # Return sha and commit message
    return data['sha'], data['commit']['message']

# Function for loading local commit hash
def load_local_commit_hash():

    # Try block for file opening
    try:

        # Open 'ugit_log.txt' for reading
        with open('ugit_log.txt', 'r') as f:

            # Read file content
            content = f.read()

            # Loop through reversed split lines
            for line in reversed(content.splitlines()):

                # If line starts with 'Update ID: '
                if line.startswith('Update ID: '):

                    # Split and strip to get hash
                    return line.split('Update ID: ')[1].strip()

    # Except block if file not found or error
    except:

        # Pass if exception
        pass

    # Return None if no hash found
    return None

# Function to pull file
def pull(f_path, raw_url):

    # Print pulling message
    print(f'Pulling {f_path} from GitHub')

    # Set headers with User-Agent
    headers = {'User-Agent': 'ota-pico'}

    # If github_token length > 0, add authorization
    if len(github_token) > 0:

        # Set authorization header
        headers['authorization'] = f"bearer {github_token}"

    # Make GET request to raw_url
    r = urequests.get(raw_url, headers=headers)

    # Try block for file writing
    try:

        # Open file in binary write mode
        new_file = open(f_path, 'wb')

        # Write response content
        new_file.write(r.content)

        # Close file
        new_file.close()

    # Except block if error
    except:

        # Print error message
        print('Virhe.')

# Define function to check daylight saving time
def is_dst(t):

    # Unpack time tuple
    year, month, day, hour, _, _, _, _ = t

    # Calculate last Sunday in March
    march_last_sunday = 31 - (time.mktime((year, 3, 31, 0, 0, 0, 0, 0)) % 7)

    # Calculate last Sunday in October
    oct_last_sunday = 31 - (time.mktime((year, 10, 31, 0, 0, 0, 0, 0)) % 7)

    # If month < 3 or > 10, no DST
    if month < 3 or month > 10:

        # Return False
        return False

    # If month > 3 and < 10, DST
    if month > 3 and month < 10:

        # Return True
        return True

    # If month == 3
    if month == 3:

        # If day < last Sunday, no DST
        if day < march_last_sunday:

            # Return False
            return False

        # If day > last Sunday, DST
        if day > march_last_sunday:

            # Return True
            return True

        # Return if hour >= 1
        return hour >= 1

    # If month == 10
    if month == 10:

        # If day < last Sunday, DST
        if day < oct_last_sunday:

            # Return True
            return True

        # If day > last Sunday, no DST
        if day > oct_last_sunday:

            # Return False
            return False

        # Return if hour < 1
        return hour < 1

# Define function to get Finland time
def get_finland_time():

    # Get UTC time
    utc = time.localtime()

    # Set offset based on DST
    offset = 3 if is_dst(utc) else 2

    # Calculate Finland time
    fin_time = time.localtime(time.mktime(utc) + offset * 3600)

    # Return Finland time
    return fin_time

# Function for building internal paths
def build_internal_paths():

    # Initialize internal_paths list
    internal_paths = []

    # Define nested function to add paths
    def add_paths(dir_item):

        # If directory
        if is_directory(dir_item):

            # Change directory
            os.chdir(dir_item)

            # For each sub item
            for sub in os.listdir():

                # Recurse add_paths
                add_paths(sub)

            # Change back directory
            os.chdir('..')

        # Else (file)
        else:

            # Construct path
            path = os.getcwd() + '/' + dir_item if os.getcwd() != '/' else dir_item

            # Append stripped path
            internal_paths.append(path.lstrip('/'))

    # Change to root directory
    os.chdir('/')

    # For each item in root
    for i in os.listdir():

        # Call add_paths
        add_paths(i)

    # Return set of internal paths
    return set(internal_paths)

# Define function to check if directory
def is_directory(file):

    # Try block
    try:

        # Get stat
        stat = os.stat(file)

        # Return if directory bit set
        return (stat[0] & 0x4000) != 0

    # Except block
    except:

        # Return False
        return False

# Define function to pull all
def pull_all(tree=call_trees_url, raw=raw, ignore=ignore, isconnected=False):

    # If not connected
    if not isconnected:

        # Connect to WiFi
        wlan = wificonnect()

        # Sleep 2 seconds
        time.sleep(2)

        # Set time from NTP
        ntptime.settime()

    # Get latest hash and message
    latest_hash, commit_message = get_latest_commit_hash_and_message()

    # Load local hash
    local_hash = load_local_commit_hash()

    # If hashes equal
    if latest_hash == local_hash:

        # Print no update message
        print('Sama versio, ei paivitysta.')

        # Return
        return

    # Change to root directory
    os.chdir('/')

    # Get tree data
    tree_data = pull_git_tree()

    # Set github_paths to blob paths
    github_paths = {item['path'] for item in tree_data['tree'] if item['type'] == 'blob'}

    # Get local paths
    local_paths = build_internal_paths()

    # For each path in local_paths copy
    for path in list(local_paths):

        # If not ignored and not in github_paths
        if path not in ignore and path not in github_paths:

            # Try to remove
            try:

                # Remove path
                os.remove(path)

            # Except pass
            except:

                # Pass
                pass

    # For each item in tree_data['tree']
    for i in tree_data['tree']:

        # If type tree
        if i['type'] == 'tree':

            # Try to make directory
            try:

                # Make directory
                os.mkdir(i['path'])

            # Except pass
            except:

                # Pass
                pass

        # Elif path not ignored
        elif i['path'] not in ignore:

            # Try to remove
            try:

                # Remove path
                os.remove(i['path'])

            # Except pass
            except:

                # Pass
                pass

            # Pull file
            pull(i['path'], raw + i['path'])

    # Get Finland time
    t = get_finland_time()

    # Format timestamp
    timestamp = f"{t[0]:04d}/{t[1]:02d}/{t[2]:02d} - {t[3]:02d}:{t[4]:02d}:{t[5]:02d}"

    # Open log file in append mode
    with open('ugit_log.txt', 'a') as logfile:

        # Write timestamp line
        logfile.write(f'Timestamp: {timestamp}\n')

        # Write update ID line
        logfile.write(f'Update ID: {latest_hash}\n')

        # Write update message line
        logfile.write(f'Update message: {commit_message}\n\n')

    # Sleep 5 seconds
    time.sleep(5)
    

# Function for connecting to WiFi
def wificonnect(ssid=ssid, password=password):

    # Create WLAN STA interface
    wlan = network.WLAN(network.STA_IF)

    # Activate interface
    wlan.active(True)

    # Connect to ssid with password
    wlan.connect(ssid, password)

    # Set max wait to 10
    max_wait = 10

    # While max_wait > 0
    while max_wait > 0:

        # If status < 0 or >= 3, break
        if wlan.status() < 0 or wlan.status() >= 3:

            # Break loop
            break

        # Decrement max_wait
        max_wait -= 1

        # Sleep 1 second
        time.sleep(1)

    # If status != 3
    if wlan.status() != 3:

        # Print connection failed
        print('Yhteys epaonnistui')

    # Else
    else:

        # Print connected
        print('Yhdistetty')

    # Return wlan
    return wlan

# Define function to pull git tree
def pull_git_tree(tree_url=call_trees_url, raw=raw):

    # Set headers with User-Agent
    headers = {'User-Agent': 'ota-pico'}

    # If github_token length > 0
    if len(github_token) > 0:

        # Set authorization header
        headers['authorization'] = f"bearer {github_token}"

    # Make GET request
    r = urequests.get(tree_url, headers=headers)

    # Load JSON data
    data = json.loads(r.content.decode('utf-8'))

    # Return data
    return data