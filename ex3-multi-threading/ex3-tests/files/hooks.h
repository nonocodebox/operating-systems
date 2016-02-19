#ifndef _HOOKS_H
#define _HOOKS_H

#ifdef __cplusplus
#define EXTERN_C extern "C"
#else
#define EXTERN_C
#endif

#include <stdio.h>
#include <stdint.h>
#include <bits/pthreadtypes.h>
#include <unistd.h>
#include <pthread.h>

// Config data
// /////////////////////////////////////////////////////////////////////////////////
EXTERN_C int last_thread_id;
EXTERN_C useconds_t delay_time;

EXTERN_C void set_fwrite_delay(useconds_t delay);

// HOOKS for C
// /////////////////////////////////////////////////////////////////////////////////
EXTERN_C int hooked_pthread_create(pthread_t * thread, pthread_attr_t * attr,
        void * (*start)(void*), void * arg);
EXTERN_C size_t hooked_fwrite(const void * ptr, size_t size, size_t nmemb, FILE * stream);
EXTERN_C int hooked_fprintf(FILE * stream, const char * format, ...);
EXTERN_C int hooked_fputs(const char * s, FILE * stream);
EXTERN_C ssize_t hooked_write(int fd, const void *buf, size_t count);

// HOOKS for C++
// /////////////////////////////////////////////////////////////////////////////////
#ifdef __cplusplus
#include <fstream>
#include <ios>

namespace std {
    class hooked_ofstream {
        public:
            static const ios_base::openmode app = ios_base::app;
            static const ios_base::openmode out = ios_base::out;
            static const ios_base::iostate failbit = ofstream::failbit;
        public:
            hooked_ofstream();

            hooked_ofstream(const char * filename, const ios::openmode& om = ios_base::out);
            void open(const char * filename, const ios::openmode& om = ios_base::out);
            
            template<typename RHS>
              friend ostream& operator<<(hooked_ofstream &ofs, const RHS &rhs) {
                if (delay_time != 0)
                  usleep(delay_time);
                return ofs._ofs << rhs;
              }

            operator bool() const;
            bool operator!() const;

            hooked_ofstream& write(const char * s, std::streamsize n);
            hooked_ofstream& flush();
            bool fail() const;
            void close();
            bool is_open() const;
            bool bad() const;
            bool eof() const;
            bool good() const;
            ios::iostate exceptions() const;
            void exceptions(ios::iostate except);
            void clear(ios::iostate state = ios::goodbit);
            ios::iostate rdstate() const;
            filebuf* rdbuf() const;
        public:
            ofstream _ofs;
    };
}
#endif // c++


#endif // HOOKS
