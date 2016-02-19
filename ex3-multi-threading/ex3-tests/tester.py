#!/usr/bin/python

import os
import re
import subprocess
import test_README
import time
import shutil
import glob

import ex3tests

def get_code_info():
    sources = []
    headers = []
    CC = 'gcc'
    lang = 'c'
    filenames = glob.glob('*')
    for filename in filenames:
        for ext in ['.cpp','.cc','.c++']:
            if filename.endswith(ext):
                sources.append(filename)
                CC = 'g++'
                lang = 'c++'
        if filename.endswith('.c'):
            sources.append(filename)
        if filename.endswith('.h') and 'hooks' not in filename:
            headers.append(filename)
    
    flags = ''
    for filename in filenames:
        if filename.lower() == 'makefile':
            f = open(filename, 'rt')
            for line in f.readlines():
                if 'std=' in line:
                    words = line.split()
                    for word in words:
                        if word.startswith('-std'):
                            flags = word
    
    return (CC, sources, headers, lang, flags)

def extract(filename, ex_obj):
    error_codes = []
    try:
        shutil.rmtree('tmp')
    except:
        pass

    subprocess.call('mkdir tmp', shell=True)

    # extract the archive to a different folder to avoid file overwriting
    e=subprocess.call('tar -xf '+filename+' -C tmp', shell=True)

    # add read permissions
    subprocess.call('chmod +r tmp/*', shell=True)
        
    # check tar executed with no errors
    if(e != 0):
        error_codes.append('bad_tar')
        return error_codes

    return error_codes
    
def stage_tests(hook_code):
    (cc, sources, headers, lang, flags) = get_code_info()

    # hook all files
    if hook_code:
        for filename in sources + headers:
            code = open(filename, 'rt').read()
            code = '#include "hooks.h"\n' + code
            code = re.sub(r'([^_])fwrite', r'\1hooked_fwrite', code)
            code = re.sub(r'(?<![.f])write\((?!void)', r'hooked_write(', code)
            code = re.sub(r'([^_])fputs', r'\1hooked_fputs', code)
            code = re.sub(r'([^_])fprintf(?!\(std)', r'\1hooked_fprintf', code)
            code = re.sub(r'([^_])pthread_create', r'\1hooked_pthread_create', code)
            code = re.sub(r'([^<_"i])iofstream(?![ ]*:)', r'\1hooked_ofstream', code)
            code = re.sub(r'([^<_"i])ofstream(?![ ]*:)', r'\1hooked_ofstream', code)
            code = re.sub(r'([^<_oi"])fstream(?![ ]*:)', r'\1hooked_ofstream', code)
            os.chmod(filename, 0666)
            open(filename, 'wt').write(code)

    # compile
    sources.append('../files/hooks.cc')
    objs = []
    for filename in sources:
        output = os.path.splitext(filename)[0] + '.o'
        objs.append(output)
        cmdline = ' '.join([cc, '-fPIC', '-g', '-x', lang,
            #'-std=c++0x',
            '-std=c++11',
            flags,
            '-include outputdevice.h', '-c', filename, '-o', output])
        err = subprocess.call(cmdline, shell=True)
        if err != 0:
            return err

    cmdline = ' '.join([cc,'-shared','-fPIC','-lpthread',
        ' '.join(objs),
        '-o liboutputdev.so'])
    err = subprocess.call(cmdline, shell=True)
    return err

def writeErrors(exobj, filename, usernames, error_codes):
    if usernames:
        exobj.write(usernames + ':\n')
    else:
        exobj.write(filename + ':\n')

    for error in error_codes:
        exobj.write(' ' + error + '\n')

    exobj.write('\n')


def test(filename, ex_obj, do_extract=True, hook_code=True):
    usernames = None
    error_codes = set()

    if do_extract:
        error_codes = set(extract(filename, ex_obj))
        if 'bad_tar' in error_codes:
            writeErrors(ex_obj, filename, usernames, error_codes)
            return

    # switch to the tmp directory
    root_dir = os.getcwd()
    os.chdir('tmp')

    # test README file
    if not os.path.exists('./README'):
        error_codes.add('missing_README_file')

    (usernames, readme_errors) = test_README.test_README('.')
    error_codes.update(readme_errors)

    # test their compilation
    print('Running make...\n')
    
    shutil.copy('../files/hooks.h', '.')
    shutil.copy('../files/outputdevice.h', '.')

    if (not os.path.exists('Makefile') and not os.path.exists('makefile')):
        error_codes.add('missing_makefile')
    else:
        subprocess.call('make clean', shell=True)
        p=subprocess.Popen('make', shell=True, stderr=subprocess.PIPE)
        res = p.communicate()

        # for some odd reason  'ar: creating libosm.a' is written to stderr
        if (res[1] != '' and res[1] != 'ar: creating liboutputdevice.a\n'):
            if not os.path.exists('liboutputdevice.a'):
                print res[1]
                error_codes.add('compilation')
                writeErrors(ex_obj, filename, usernames, error_codes)
                return error_codes
            else:
                error_codes.add('compilation_warning')

    # clean everything
    subprocess.call('make clean', shell=True)
    remove_files = glob.glob('*.o') + glob.glob('*.so') + glob.glob('*.a')
    if remove_files:
        subprocess.call('rm -f ' + ' '.join(remove_files), shell=True)

    err = stage_tests(hook_code)
    if (err != 0):
        print 'Staging ERROR. Aborting.'
        error_codes.update(['ABORT'])
        return error_codes

    # run the tests and write the errors
    error_codes.update(ex3tests.test_all(root_dir))
    writeErrors(ex_obj, filename, usernames, error_codes)

    # switch back to parent directory and remove tmp
    os.chdir('..')

    return error_codes


def main():
    import time
    import sys
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('filename',
            help='tar filename or submission directory',
            type=str,
            nargs='?')
    parser.add_argument('-t','--test',
            help='Just test the code in the ./tmp directory',
            action='store_true')
    parser.add_argument('-d', '--dry',
            help='Dry run. Do not write to grade file',
            action='store_true')
    parser.add_argument('--nohook',
            help='Do not hook write functions',
            action='store_true')


    args = parser.parse_args()
    
    if not args.filename and not args.test:
        parser.print_help()
        return

    curdir = os.getcwd()

    hook_code = True
    if args.nohook:
        hook_code = False

    # open the grades file
    if args.dry:
        ex_obj = sys.stdout
    else:
        subprocess.call('touch ex3', shell=True)
        ex_obj = open('ex3','a')

    if args.test:
        print('Testing ./tmp...')
        errors = test('<TMP>', ex_obj, False, hook_code)
        os.chdir(curdir)
        return

    if os.path.isdir(args.filename):
        submission_dir = args.filename
        
        for filename in glob.glob(os.path.join(submission_dir, '*')):
            print('Testing ' + filename + '#'*80)
            errors = test(filename, ex_obj, True, hook_code)
            print('Errors: ' + str(errors))
            os.chdir(curdir)
            time.sleep(1)
    else:
        errors = test(args.filename, ex_obj, True, hook_code)
        print('Errors: ' + str(errors))
        os.chdir(curdir)

    ex_obj.close()


if __name__ == '__main__':
    main()
