# Makefile for Ex5

TARGETS=$(MCFS)
MCFS=MyCachingFileSystem

all: $(TARGETS)

$(MCFS): MyCachingFileSystem.cpp
	g++ -Wall `pkg-config fuse --cflags --libs` -g MyCachingFileSystem.cpp -o ${MCFS}
# explanation: `instruction here` - run in shell and paste content here
	
clean:
	rm -f $(TARGETS) *.o

tar: MyCachingFileSystem.cpp README Makefile
	tar cvf ex5.tar README Makefile MyCachingFileSystem.cpp