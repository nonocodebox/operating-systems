#!/usr/bin/python

import os
import re
import sys
import glob

BAD_LOGINS = 0
BAD_README = 1


def findInterestingFiles(path):
    files = glob.glob('*.c*')
    #files.extend(glob.glob('*.h'))


# if the login(s) correctly extracted they and the no_appeal error are printed 
def test_README(path):
    
    usernames = None
    readme_filename = os.path.join(os.getcwd(), path, 'README')

    print('Reading ' + readme_filename)
    README_file_obj = open(readme_filename,'r')
    error_codes = set()

    #regex =['^([-A-Za-z\s]+)\s\((\d)+\)(,\s([-A-Za-z\s]+)\s\((\d+)\))?(\r)?\n$']
    #regex.append('^EX:\s'+str(ex_num)+'(\r)?(\n)$')
    #regex.append('^(\r)?(\n)$')
    #regex.append('^FILES:(\r)?(\n)$')

    # err_line = ['names_and_ids','EX','newline','FILES']

    # getting the students names by parsing the first line in the README
    line = README_file_obj.readline()
    # print(line)
    p=re.compile('^((\w+)\s*(,\s?(\w+))?)\s*(\r)?\n$')
    m = p.match(line)
    if not m:
        # print 'error in getting the students names '
        README_file_obj.close()
        error_codes.add('no_logins')
        return (usernames, error_codes)
    else:
        error_codes.add('no_appeal')
        usernames = line.strip()

    
    # parse the second line: names and ids
    r = re.compile('^([ \-A-Za-z]+)([(]?(\d+)[)]?)?\s*(,? ([ \-A-Za-z]+)([(]?(\d+)[)]?)?)?(\r)?\n$')
    line = README_file_obj.readline()
    m = r.match(line)
    if not m:
        error_codes.add('bad_readme')


    # file description is not interesting for me at the moment (ex1)

    # check that the 4 first lines are formatted correctly
    #i=0
    #for reg in regex:
    #    p=re.compile(reg,re.IGNORECASE)#'^(\w+),\s(\w+)(\r)?(\n)$')
    #    line = README_file_obj.readline()
    #    m = p.match(line)
    #    if not m:
    #        print('line number '+str(i)+' in README is not formated correctly')
    #        errors[BAD_README]=1
    #    i=i+1
    #    
    ## get the list of files mentioned in the README
    #files_in_README_set=set([])
    #next=README_file_obj.readline()
    #while(next):
    #    p=re.compile('^([\w.]+)\s*--.*$')
    #    m=p.match(next)
    #    if not m:
    #        break
    #    files_in_README_set.add(m.group(1))
    #    next=README_file_obj.readline()
    #    
    ## check that each submited file is mentioned in the README
    #for sfile in file_list:
    #    # print(sfile)
    #    if sfile not in files_in_README_set:
    #        print('file '+sfile+'is not mentioned or has no description in README')
    #        errors[BAD_README]=1
            
            
    README_file_obj.close()
    return (usernames, error_codes)

