#Makefile for Ex3

LIBSRC=outputdevice.cpp
LIBOBJ=$(LIBSRC:.cpp=.o)

PFTLIB = liboutputdevice.a
TARGETS = $(PFTLIB)

all: $(TARGETS)

$(TARGETS): $(LIBOBJ)
	g++ -Wall -lpthread -g -c outputdevice.cpp
	ar rv liboutputdevice.a outputdevice.o
	ranlib $@

clean:
	rm liboutputdevice.a *.o

tar: outputdevice.cpp README Makefile
	tar vcf ex3.tar README Makefile outputdevice.cpp