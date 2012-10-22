
#
# Copyright (c) 2012 Jonathan Topf
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


from xml.dom.minidom import parseString
import os
import sys
import time
from datetime import datetime
import shutil
import random

# directory names

OUTPUT_DIR = '_output'
COMPLETED_DIR = '_completed'

# Define helper class for printing colored text.
class printc():
    @staticmethod
    def warning(text):
        if os.system == 'darwin':
            print '\033[93m' + text + '\033[0m'
        else: 
            print text
    
    @staticmethod
    def error(text):
        if os.system == 'darwin':
            print '\033[91m' + text + '\033[0m'
        else: 
            print text
            
    @staticmethod
    def success(text):
        if os.system == 'darwin':
            print '\033[92m' + text + '\033[0m'
        else: 
            print text


def getDepends(xml_file_path):
    depend_list = []

    directory = os.path.split(xml_file_path)[0]

    file = open(xml_file_path, 'r')
    data = file.read()
    file.close()

    dom = parseString(data)

    for entity in dom.getElementsByTagName('parameter'):
        if entity.getAttribute('name') == 'filename':

            file_name_attr = entity.getAttribute('value')

            if (sys.platform == 'win32') or (sys.platform == 'win64'):
                file_name_attr = file_name_attr.replace('/', '\\')
            else:
                file_name_attr = file_name_attr.replace('\\', '/')

            depend_list.append(os.path.join( directory,  file_name_attr))

    return depend_list


def listAppleseedFiles(directory_path):
    directory_entities =  os.listdir(directory_path)
    files = []
    appleseed_files = []

    for entity in directory_entities:
        file_path = os.path.join(directory_path, entity)
        if os.path.isfile(file_path):
            if os.path.splitext(file_path)[1] == '.appleseed':
                appleseed_files.append(file_path)

    return appleseed_files


def isRenderable(file):
    depend_name_text = 'dependencies for "{0}"'.format(os.path.split(file)[1])
    print(depend_name_text)
    print(len(depend_name_text) * '-')

    is_renderable = True

    for depend in getDepends(file):
        if os.path.exists(os.path.join(depend)):
            printc.success('EXISTS   ' + depend)
        else:
            printc.error('MISSING  ' + depend)
            is_renderable = False

    print

    return is_renderable


def main():
    args = sys.argv
    appleseed_dir = None
    watch_dir = None
    short_name = None
    for arg in args:
        if arg == 'h' or arg == 'help':
            print 'h or help  = print help'
            print 'ad=...     = set appleseed bin directory'
            print 'wd=...     = set watch directory'
            print 'sn=...     = set short name, used to identify the file being rendered'
            return 0
        split_arg = arg.split("=")
        if split_arg[0] == 'ad':
            appleseed_dir = split_arg[1]
            cli_path = os.path.join(appleseed_dir, 'appleseed.cli')
        elif split_arg[0] == 'wd':
            watch_dir = split_arg[1]
        elif split_arg[0] == 'sn':
            short_name = split_arg[1]

    if appleseed_dir == None:
        printc.warning('no path to appleseed provided, use ad=... to set path to appleseed bin directory.')
        return 0

    if watch_dir == None:
        print('no watch directory provided, using working directory.')
        watch_dir = os.getcwd()

    # make folder to put rendered appleseed files into
    if not os.path.exists(os.path.join(watch_dir, COMPLETED_DIR)):
        os.mkdir(os.path.join(watch_dir, COMPLETED_DIR))

    # make folder to put rendered images into
    if not os.path.exists(os.path.join(watch_dir, OUTPUT_DIR)):
        os.mkdir(os.path.join(watch_dir, OUTPUT_DIR))

    while True:
        try:
            appleseed_files = listAppleseedFiles(watch_dir)

            renderable_files_found = False

            # if any appleseed files have been found
            if len(appleseed_files) > 0:

                # define random start point for list
                random_start_point = int(random.random() * (len(appleseed_files) - 1))

                # iterate over re ordered list of files
                for appleseed_file in (appleseed_files[random_start_point:] + appleseed_files[:random_start_point]):

                    print

                    if isRenderable(appleseed_file):

                        renderable_files_found = True

                        printc.warning(':::: RENDERING "{0}" ::::\n'.format(appleseed_file))

                        if short_name is None:
                            in_progress_appendage = '.inprogress'
                        else:
                            in_progress_appendage = '.' + short_name

                        temporary_file_name = appleseed_file + in_progress_appendage

                        # temporarily rename file so others dont try to render it
                        os.rename(appleseed_file, temporary_file_name)

                        # create shell command
                        appleseed_file_name = os.path.split(appleseed_file)[1]
                        output_file_name = os.path.splitext(appleseed_file_name)[0] + '.png'
                        output_file_path = os.path.join(watch_dir, OUTPUT_DIR, output_file_name)
                        command = '{0} -o "{1}" "{2}"'.format(cli_path, output_file_path, temporary_file_name)

                        # execute command
                        return_value = os.system(command)

                        print("")

                        # if the return value is not 0 then something may have gone wrong
                        if return_value != 0:
                            printc.warning('file may not have rendered correctly: ' + appleseed_file)

                        # move the file into _completed directory
                        move_dest = os.path.join(watch_dir, COMPLETED_DIR, os.path.split(temporary_file_name)[1])
                        shutil.move(temporary_file_name, move_dest)

                        # rename the file to its original name

                        # reverted_file_name = os.path.join(watch_dir, COMPLETED_DIR, os.path.split(appleseed_file)[1])
                        # os.rename(move_dest, reverted_file_name)

                        break
                    else:
                        print('{0} - missing dependencies to render "{1}"'.format(datetime.now(), os.path.split(appleseed_file)[1]))
            else:
                print("{0} - nothing to render".format(datetime.now()))
                renderable_files_found = False

            if not renderable_files_found:
                time.sleep(1)
        except:
            princ('an unknown error has occured')


if __name__ == '__main__':
    main()
