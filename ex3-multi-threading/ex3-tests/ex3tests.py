#!/usr/bin/env python

import sys
import ctypes
import subprocess
import os
import random

from threading import Thread
from time import sleep, time
from binascii import hexlify
from ctypes import create_string_buffer

DELAY_TIME = 0

liboutputdev = None
_set_fwrite_delay = None

initdevice = None
closedevice = None
write2device = None 
flush2device = None
wasItWritten = None
wait4close = None
 

SUCCESS = 0
ERROR = 1
ERROR_ID = 2
ERROR_BLOCKING = 3
ERROR_DATA = 4
ERROR_FLUSH = 5
ERROR_DOUBLE_INIT = 6

LAST_ERROR = 6

ERROR_NO_RESPONSE_OR_RUNTIME = 7

MAX_TEST_TIME = 20

devname = 'data.out'

TESTS = []

def load_library():
    CHARPTR = ctypes.POINTER(ctypes.c_char)

    global liboutputdev, initdevice, closedevice, write2device
    global flush2device, wasItWritten, wait4close, _set_fwrite_delay

    liboutputdev = ctypes.CDLL('./liboutputdev.so')

    _set_fwrite_delay = liboutputdev.set_fwrite_delay

    initdevice = liboutputdev.initdevice
    closedevice = liboutputdev.closedevice
    write2device = liboutputdev.write2device
    flush2device = liboutputdev.flush2device
    wasItWritten = liboutputdev.wasItWritten
    wait4close = liboutputdev.wait4close

    initdevice.argtypes = [CHARPTR]
    initdevice.restype = ctypes.c_int

    write2device.argtypes = [CHARPTR, ctypes.c_int]
    write2device.restype = ctypes.c_int

    flush2device.argtypes = [ctypes.c_int]
    flush2device.restype = ctypes.c_int

    wasItWritten.argtypes = [ctypes.c_int]
    wasItWritten.restype = ctypes.c_int

    wait4close.restype = ctypes.c_int

def unload_library():
    global liboutputdev, initdevice, closedevice, write2device
    global flush2device, wasItWritten, wait4close, _set_fwrite_delay
    
    liboutputdev = None
    _set_fwrite_delay = None

    initdevice = None
    closedevice = None
    write2device = None 
    flush2device = None
    wasItWritten = None
    wait4close = None

def set_fwrite_delay(delay):
    global DELAY_TIME
    DELAY_TIME = delay
    _set_fwrite_delay(delay * (10**6))

def TestEnv(test_func):
    def wrapped(*args, **kwargs):
        try:
            os.remove(devname)
        except:
            pass
    
        load_library()
        set_fwrite_delay(0)

        rv = test_func(*args, **kwargs)
        unload_library()
        return rv

    wrapped.name = test_func.func_name
    TESTS.append(wrapped)
    return wrapped

def find_test(test_name):
    for test in TESTS:
        if test.name == test_name:
            return test
    return None

def run_sandboxed_test(execname, test_name):
    objs = {}
    def sandbox():
        p = subprocess.Popen([execname, test_name])
        objs['retval'] = p
        objs['pipe'] = p
        p.wait()
        objs['retval']= p.returncode

    t = Thread(target=sandbox)
    t.start()
    t.join(MAX_TEST_TIME)

    if objs['pipe'].poll() is None:
        objs['pipe'].kill()
        return ERROR_NO_RESPONSE_OR_RUNTIME

    return objs['retval']


def test_all(root_dir):
    execname = os.path.join(root_dir, 'ex3tests.py')
    failed_tests = []
    for test in TESTS:
        sleep(0.1)
        print 'Running ' + test.name +'...'
        retval = run_sandboxed_test(execname, test.name)
        print '\t',
        if retval == SUCCESS:
            print '\tOK'
        elif retval in range(LAST_ERROR):
            failed_tests.append(test.name)
            print '\tERROR('+str(retval)+')'
        else:
            failed_tests.append('RUNTIME_'+test.name)
            print '\tRUNTIME_ERROR'
    return failed_tests

@TestEnv
def test_simple_init_and_close():
    status = initdevice(devname)
    if (status != 0):
      return ERROR
    closedevice()
    return SUCCESS

@TestEnv
def test_init_close_twice_fast():
    status = initdevice(devname)
    closedevice()
    status = initdevice(devname)
    if (status != 0):
      return ERROR
    closedevice()
    return SUCCESS

@TestEnv
def test_init_close_twice():
    status = initdevice(devname)
    sleep(0.5)
    closedevice()
    sleep(0.5)
    status = initdevice(devname)
    if (status != 0):
      return ERROR
    closedevice()
    return SUCCESS

@TestEnv
def test_double_init():
    status = initdevice(devname)
    if (status != 0):
      return ERROR
    status = initdevice(devname)
    if (status == 0):
      return ERROR_DOUBLE_INIT
    closedevice()
    return SUCCESS

@TestEnv
def test_write_before_init():
    taskid = write2device('a', 1)
    if taskid != -1:
        return ERROR
    return SUCCESS

@TestEnv
def test_write2device_blocking():
    WAIT_TIME = 5
    initdevice(devname)
    set_fwrite_delay(WAIT_TIME)
    s = hexlify(os.urandom(1000))
    s = create_string_buffer(s)

    def writer():
        tid = write2device(s, len(s.value))
    t = Thread(target=writer)
    t.start()

    t1 = time()
    t.join(2)
    t2 = time()
    closedevice()
    if (t2 - t1) > 1:
        return ERROR_BLOCKING
    return SUCCESS

@TestEnv
def test_write2device_blocking_with_2_tasks():
    WAIT_TIME = 5
    initdevice(devname)
    set_fwrite_delay(WAIT_TIME)
    s = hexlify(os.urandom(1000))
    s = create_string_buffer(s)

    def writer():
        tid = write2device(s, len(s.value))
    t1 = Thread(target=writer)
    t2 = Thread(target=writer)

    t1.start()
    sleep(1)
    t2.start()

    time_start = time()
    t2.join(2)
    time_end = time()
    closedevice()
    if (time_end - time_start) > 1:
        return ERROR_BLOCKING
    return SUCCESS


@TestEnv
def test_simple_write():
    initdevice(devname)

    s = 'test_simple_write ' + hexlify(os.urandom(1000)) + '\n'
    s = create_string_buffer(s)
    obj = {}
    def writer():
        obj['id'] = write2device(s, len(s.value))
    
    t = Thread(target=writer)
    t.start()
    t.join(1)
    
    if t.isAlive():
        return ERROR_BLOCKING

    closedevice()
    sleep(DELAY_TIME)

    if obj['id'] < 0:
        return ERROR_ID
    
    f = open(devname, 'rb')
    if f.read() != s.value:
        return ERROR_DATA
    return SUCCESS

@TestEnv
def test_append_to_file():
    initdevice(devname)

    s = 'test_append_to_file ' + hexlify(os.urandom(1000)) + '\n'
    s = create_string_buffer(s)
    obj = {}
    def writer():
        obj['id'] = write2device(s, len(s.value))
    
    t = Thread(target=writer)
    t.start()
    t.join(0.5)
    sleep(DELAY_TIME)

    closedevice()
    initdevice(devname)
    sleep(0.5)
    closedevice()
    f = open(devname, 'rb')
    if f.read() != s.value:
        return ERROR_DATA
    
    return SUCCESS

@TestEnv
def test_write_and_flush():
    initdevice(devname)
    
    s = 'test_write_and_flush ' + hexlify(os.urandom(1000)) + '\n'
    s = create_string_buffer(s)
    obj = {}
    def writer():
        obj['id'] = write2device(s, len(s.value))
    
    t = Thread(target=writer)
    t.start()
    t.join(1)

    if t.isAlive():
        return ERROR_BLOCKING

    if obj['id'] < 0:
        return ERROR_ID

    sleep(DELAY_TIME + 1)

    def waiter():
        obj['retval'] = flush2device(obj['id'])
    
    t = Thread(target=waiter)
    t.start()
    t.join(1)

    if t.isAlive():
        return ERROR_BLOCKING
    
    if obj['retval'] not in [0,1]:
        print '\tflush2device returned %d' % obj['retval']
        return ERROR_FLUSH
   
    closedevice()

    f = open(devname, 'rb')
    if f.read() != s.value:
        return ERROR_DATA

    return SUCCESS

@TestEnv
def test_close_before_flush():
    initdevice(devname)

    s = 'test_close_before_flush ' + hexlify(os.urandom(1000)) + '\n'
    s = create_string_buffer(s)
    obj = {}
    def writer(i):
        obj[i] = write2device(s, len(s.value))
    
    t1 = Thread(target=writer, args=(1,))
    t1.start()
    t2 = Thread(target=writer, args=(2,))
    t2.start()
    
    t1.join()
    t2.join()

    if obj[1] < 0 or obj[2] < 0:
        return ERROR_ID

    closedevice()
    
    sleep(DELAY_TIME)
    retval = flush2device(obj[2])
    if retval in [0,1]:
        return ERROR_FLUSH

    f = open(devname, 'rb')
    if f.read() != s.value+s.value:
        return ERROR_DATA
    return SUCCESS

@TestEnv
def test_close_before_write():
    initdevice(devname)
    sleep(1)
    closedevice()
    tid = write2device('bla', 3)
    if tid != -1:
        return ERROR

    f = open(devname, 'rb')
    if f.read() != '':
        return ERROR
    return SUCCESS

@TestEnv
def test_flush_illegal_tid():
    initdevice(devname)
    
    s = 'test_flush_illegal_tid ' + hexlify(os.urandom(1000)) + '\n'
    s = create_string_buffer(s)
    obj = {}
    def writer():
        obj['id'] = write2device(s, len(s.value))
    
    t = Thread(target=writer)
    t.start()
    t.join()

    if t.isAlive():
        return ERROR_BLOCKING
    if obj['id'] < 0:
        return ERROR_ID

    retval = flush2device(obj['id']+1)
    if retval != -2:
        return ERROR_FLUSH

    closedevice()
    sleep(1)

    f = open(devname, 'rb')
    if f.read() != s.value:
        return ERROR_DATA
    return SUCCESS

@TestEnv
def test_flush2device_waits_for_correct_task():
    initdevice(devname)
    WAIT_TIME = 4
    set_fwrite_delay(WAIT_TIME)

    s = 'test_flush_waits_for_correct_task ' + hexlify(os.urandom(1000)) + '\n'
    s = create_string_buffer(s)
    obj = {}
    def writer1():
        obj['id1'] = write2device(s, len(s.value))
    def writer2():
        obj['id2'] = write2device(s, len(s.value))

    t1 = Thread(target=writer1)
    t2 = Thread(target=writer2)
    t1.start()
    sleep(2)
    t2.start()
    t2.join(0.1)

    start = time()
    retval = flush2device(1)
    end = time()
    if retval not in [0,1]:
        return ERROR_FLUSH

    if (end - start) < 3:
        return ERROR

    return SUCCESS

def _test_multiple_threads(num_threads, bufsize, rand_delay=False):
    initdevice(devname)

    set_fwrite_delay(0)

    obj = {}
    def writer(i,s):
        obj[i] = write2device(s, len(s.value))

    threads = []
    strings = {}
    for i in xrange(num_threads):
        if rand_delay:
            set_fwrite_delay(1 + random.random())
        s = ''.join([str(i),':',hexlify(os.urandom(bufsize)),'\n'])
        strings[i] = s
        s = create_string_buffer(s)
        t = Thread(target=writer, args=(i,s))
        threads.append(t)
        t.start()

    err = False
    for t in threads:
        t.join(1)
        if t.isAlive():
            err = True
    if err:
        return ERROR_BLOCKING

    closedevice()
    sleep(2)

    # check the strings
    f = open(devname, 'rb')
    lines = f.readlines()
    if len(lines) != len(strings):
        print '\ttest_multiple_threads: %d lines instead of %d!' % (len(lines), len(strings))
        return ERROR_DATA
    for line in lines:
        i = int(line.split(':', 1)[0])
        if i not in strings.keys():
            return ERROR_DATA
        if strings[i].strip() != line.strip():
            print '\ttest_multiple_threads: %d data incorrect!' % (i,)
            return ERROR_DATA

    return SUCCESS

@TestEnv
def test_multiple_threads():
    return _test_multiple_threads(10, 1000)

@TestEnv
def test_multiple_threads_big():
    return _test_multiple_threads(10, 1000000)

@TestEnv
def test_multiple_threads_many():
    return _test_multiple_threads(100, 1000)

@TestEnv
def test_init_creates_worker_thread():
    prev_tid = ctypes.c_int.in_dll(liboutputdev, 'last_thread_id')
    initdevice(devname)
    sleep(1)
    cur_tid = ctypes.c_int.in_dll(liboutputdev, 'last_thread_id')
    if cur_tid == prev_tid:
        closedevice()
        return ERROR
    closedevice()
    return SUCCESS

@TestEnv
def test_flush2device_not_blocking():
    WAIT_TIME = 5
    initdevice(devname)
    set_fwrite_delay(WAIT_TIME)
    s = hexlify(os.urandom(1000))
    s = create_string_buffer(s)
    tid = write2device(s, len(s.value))
    if tid < 0:
        closedevice()
        return ERROR_BLOCKING

    retval = []
    def waiter_func():
        retval.append(flush2device(tid))

    waiter = Thread(target=waiter_func)
    t1 = time()
    waiter.start()
    waiter.join()
    diff = time() - t1
    closedevice()

    if diff < WAIT_TIME-0.5 or diff > WAIT_TIME+0.5:
        print '\tWait time is %d' % diff
        return ERROR
    return SUCCESS

@TestEnv
def test_close_while_flushing():
    WAIT_TIME = 5
    initdevice(devname)
    set_fwrite_delay(WAIT_TIME)
    s = hexlify(os.urandom(1000))
    s = create_string_buffer(s)
    t1 = time()
    tid = write2device(s, len(s.value))
    t2 = time()
    if tid < 0 or (t2 - t1) > 1:
        closedevice()
        return ERROR_ID

    retval = []
    def waiter_func():
        retval.append(flush2device(tid))

    t1 = time()
    waiter = Thread(target=waiter_func)
    waiter.start()
    closedevice()
    waiter.join()
    diff = time() - t1

    if diff < WAIT_TIME-0.5 or diff > WAIT_TIME+0.5:
        return ERROR
    return SUCCESS

@TestEnv
def test_was_it_written():
    WAIT_TIME = 5
    initdevice(devname)
    
    set_fwrite_delay(WAIT_TIME)
    
    s = hexlify(os.urandom(100))
    s = create_string_buffer(s)
    
    tid = write2device(s, len(s.value))
    
    if tid < 0:
        closedevice()
        return ERROR_ID
    
    was_it_before = wasItWritten(tid)
    
    retval = []
    def waiter_func(tid):
        retval.append(flush2device(tid))

    waiter = Thread(target=waiter_func, args=(tid,))
    waiter.start()
    waiter.join()
    
    was_it_after = wasItWritten(tid)
    
    if was_it_before != 1 or was_it_after != 0:
        return ERROR
    return SUCCESS

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(255)
    test_name = sys.argv[1]
    test = find_test(test_name)
    if not test:
        sys.exit(255)
    
    rv = test()
    #sys.exit(rv)
    os._exit(rv)

