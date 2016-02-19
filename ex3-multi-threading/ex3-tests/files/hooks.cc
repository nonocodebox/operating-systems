#include <stdio.h>
#include <stdint.h>
#include <bits/pthreadtypes.h>
#include <unistd.h>
#include <pthread.h>
#include <stdarg.h>


#ifdef __cplusplus
#include <fstream>
#include <ios>
#endif

#include "hooks.h"

// Config data
// /////////////////////////////////////////////////////////////////////////////////
int last_thread_id;
useconds_t delay_time;

void set_fwrite_delay(useconds_t delay) {
  delay_time = delay;
}

// HOOKS for C
// /////////////////////////////////////////////////////////////////////////////////
int hooked_pthread_create(pthread_t * thread, pthread_attr_t * attr,
    void * (*start)(void*), void * arg) {
  int rc;

  rc = pthread_create(thread, attr, start, arg);
  if (rc == 0)
    last_thread_id = (int)(*thread);
  return rc;
}

size_t hooked_fwrite(const void * ptr, size_t size, size_t nmemb, FILE * stream) {
  if (delay_time != 0)
    usleep(delay_time);

  return fwrite(ptr, size, nmemb, stream);
}

ssize_t hooked_write(int fd, const void *buf, size_t count) {
  if (delay_time != 0)
    usleep(delay_time);

  return write(fd, buf, count);
}

int hooked_fputs(const char * s, FILE * stream) {
  if (delay_time != 0)
    usleep(delay_time);

  return fputs(s, stream);
}


int hooked_fprintf(FILE *stream, const char *format, ...) {
  int retval;
  va_list argptr;

  if (delay_time != 0)
    usleep(delay_time);

  va_start(argptr, format);
  retval = vfprintf(stream, format, argptr);
  va_end(argptr);

  return retval;
}

// HOOKS for C++
// /////////////////////////////////////////////////////////////////////////////////
#ifdef __cplusplus
using namespace std;

std::hooked_ofstream::hooked_ofstream() : _ofs()
{
}

  std::hooked_ofstream::hooked_ofstream(const char * filename, const ios::openmode& om)
: _ofs(filename, om)
{
}

void std::hooked_ofstream::open(const char * filename, const ios::openmode& om) {
  _ofs.open(filename, om);
}

std::hooked_ofstream& std::hooked_ofstream::write(const char * s, std::streamsize n) {
  if (delay_time != 0)
    usleep(delay_time);
  _ofs.write(s, n);
  return *this;
}

std::hooked_ofstream& std::hooked_ofstream::flush() {
  _ofs.flush();
  return *this;
}

bool std::hooked_ofstream::fail() const{
  return _ofs.fail();
}

void std::hooked_ofstream::close() {
  _ofs.close();
}

bool std::hooked_ofstream::is_open() const {
  return _ofs.is_open();
}

bool std::hooked_ofstream::bad() const {
  return _ofs.bad();
}

bool std::hooked_ofstream::eof() const {
  return _ofs.eof();
}

bool std::hooked_ofstream::good() const {
  return _ofs.good();
}

ios::iostate std::hooked_ofstream::exceptions() const {
  return _ofs.exceptions();
}

ios::iostate std::hooked_ofstream::rdstate() const {
  return _ofs.rdstate();
}

void std::hooked_ofstream::exceptions(ios::iostate except) {
  _ofs.exceptions(except);
}

void std::hooked_ofstream::clear(ios::iostate state) {
  _ofs.clear(state);
}

std::filebuf * std::hooked_ofstream::rdbuf() const {
  if (delay_time != 0)
    usleep(delay_time);

  return _ofs.rdbuf();
}

bool std::hooked_ofstream::operator!() const {
  return !_ofs;
}

std::hooked_ofstream::operator bool() const {
  return bool(_ofs);
}

#endif // c++

