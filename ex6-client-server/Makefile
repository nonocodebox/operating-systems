# Makefile for Ex5

all: srftp clftp

srftp: srftp.cpp Makefile
	g++ -Wall srftp.cpp -o srftp

clftp: clftp.cpp Makefile
	g++ -Wall clftp.cpp -o clftp

clean:
	rm -f srftp clftp *.o

tar: srftp.cpp clftp.cpp README Makefile performance.jpg
	tar cvf ex6.tar README Makefile clftp.cpp srftp.cpp performance.jpg
