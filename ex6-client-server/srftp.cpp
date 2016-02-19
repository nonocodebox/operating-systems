//********************************* INCLUDES **********************************

#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <string.h>
#include <netdb.h>
#include <unistd.h>
#include <fstream>
#include <vector>
#include <algorithm>

// Uncomment to measure performance
//#define MEASURE_PERFORMANCE

#ifdef MEASURE_PERFORMANCE
#include <sys/time.h>
#endif

using namespace std;


//********************************* VARIABLES *********************************

#define EXIT_CODE_SUCCESS  0
#define EXIT_CODE_ERROR    1
#define HOST_NAME_MAX      64
#define MAX_REQUEST_LINE   SOMAXCONN
#define FAILURE            -1
#define WRITE_ACCESS       "w"
#define FD_ERROR           -1
#define PORT_PARA_INDX     1
#define DATA_BUF_SIZE      4096

typedef enum State{
	FILE_SIZE,
	NAME_SIZE,
	FILE_NAME,
	FILE_DATA
} State;

typedef struct ClientInfo{
	int socket;
	State state;
	int fileSize;
	int nameSize;
	char* fileName;
	FILE *fFileData;
	size_t readOffset;
	char dataBuf[DATA_BUF_SIZE];
}ClientInfo;

vector<ClientInfo*> clients;

//****************************** HELPERS FUNCTIONS ****************************

int findMaxFDAndSET(fd_set *fdset, int sockListen)
{
	int max = sockListen;

	FD_SET(sockListen, fdset);

	for(size_t i = 0; i < clients.size(); i++)
	{
		if(clients[i] == NULL)
		{
			continue;
		}
		if (max < clients[i]->socket)
		{
			max = clients[i]->socket;
		}

		FD_SET(clients[i]->socket, fdset);
	}

	return max + 1;
}

int readFromClient(ClientInfo *client, void *buffer, size_t size)
{
	int result = 0;

	result = recv(client->socket,
			((char*)buffer) + client->readOffset,
			size - client->readOffset,
			0);
	if (result == FAILURE || (result == 0 && client->readOffset < size))
	{
		cerr << "ERROR: read failed" << endl;
		exit(EXIT_CODE_ERROR);
	}

	client->readOffset += result;

	if (client->readOffset >= size)
	{
		client->readOffset = 0;
		return true;
	}

	return false;
}

int readFileDataFromClient(ClientInfo *client)
{
	int result = 0;

	int remainingSize = client->fileSize - client->readOffset;
	int readSize = min(remainingSize, DATA_BUF_SIZE);
	result = recv(client->socket,
			client->dataBuf,
			readSize,
			0);
	if (result == FAILURE ||
			(result == 0 && client->readOffset < (size_t)client->fileSize))
	{
		cerr << "ERROR: read failed" << endl;
		exit(EXIT_CODE_ERROR);
	}

	int numberOfBytes = fwrite(
			client->dataBuf,
			sizeof(char),
			result,
			client->fFileData);

	if (numberOfBytes < result)
	{
		cerr << "ERROR: write failed" << endl;
		exit(EXIT_CODE_ERROR);
	}

	client->readOffset += result;

	if (client->readOffset >= (size_t)client->fileSize)
	{
		return true;
	}

	return false;
}

void releaseClient(int clientIndex)
{
	if (clients[clientIndex]->fFileData != NULL)
	{
		fclose(clients[clientIndex]->fFileData);
	}

	free(clients[clientIndex]->fileName);
	close(clients[clientIndex]->socket);
	free(clients[clientIndex]);
	clients[clientIndex] = NULL;
}

void addClient(ClientInfo *client)
{
	for (size_t i = 0; i < clients.size(); i++)
	{
		if (clients[i] == NULL)
		{
			clients[i] = client;
			return;
		}
	}

	clients.push_back(client);
}

//*********************************** MAIN ************************************


int main(int argc, char* argv[])
{
#ifdef MEASURE_PERFORMANCE
	timeval establishmentTime, releaseTime, difference;
#endif

	int serverPort = atoi(argv[PORT_PARA_INDX]);
	if (serverPort <= 0)
	{
		cerr << "ERROR: usage port failed" << endl;
		exit(EXIT_CODE_ERROR);
	}


	char myname[HOST_NAME_MAX+1];
	int sockListen;
	struct hostent *hp;
	struct sockaddr_in sa;

	memset(&sa, 0, sizeof(struct sockaddr_in));

	int result  = gethostname(myname, HOST_NAME_MAX);
	if(result < 0)
	{
		cerr << "ERROR: gethostname failed" << endl;
		exit(EXIT_CODE_ERROR);
	}
	hp = gethostbyname(myname);
	if (hp == NULL)
	{
		cerr << "ERROR: gethostbyname failed" << endl;
		exit(EXIT_CODE_ERROR);
	}

	sa.sin_family = hp->h_addrtype;
	memcpy(&sa.sin_addr, hp->h_addr, hp->h_length);
	/* this is our host address */
	sa.sin_port= htons(serverPort); /* this is our port number */


	if ((sockListen = socket(AF_INET, SOCK_STREAM, 0)) < 0)
	{/* create socket */
		cerr << "ERROR: socket failed" << endl;
		exit(EXIT_CODE_ERROR);
	}
	if (bind(sockListen , (struct sockaddr *)&sa , sizeof(struct sockaddr_in)) < 0)
	{
		cerr << "ERROR: bind failed" << endl;
		exit(EXIT_CODE_ERROR);
	}

	result = listen(sockListen, MAX_REQUEST_LINE); /* max # of queued connects */
	if(result < 0)
	{
		cerr << "ERROR: listen failed" << endl;
		exit(EXIT_CODE_ERROR);
	}
	while (true)
	{
		fd_set readSet;
		struct timeval timeout;

		timeout.tv_sec = 0;
		timeout.tv_usec = 500000;

		// Wait for new clients and handle existing clients
		FD_ZERO(&readSet);
		int maxFd = findMaxFDAndSET(&readSet, sockListen);

		result = select(maxFd, &readSet, NULL, NULL, &timeout);
		if (result < 0)
		{
			cerr << "ERROR: select failed" << endl;
			exit(EXIT_CODE_ERROR);
		}
		if (result > 0) // There are clients that need to be served.
		{
			if (FD_ISSET(sockListen, &readSet))
			{

				int t; /* socket of connection */

				if ((t = accept(sockListen,NULL,NULL)) < 0)
				{
					cerr << "ERROR: accept failed" << endl;
					exit(EXIT_CODE_ERROR);
				}

#ifdef MEASURE_PERFORMANCE
				result = gettimeofday(&establishmentTime, NULL);
#endif

				ClientInfo* info = (ClientInfo*)malloc(sizeof(ClientInfo));
				if(info == NULL)
				{
					cerr << "ERROR: allocation failed" << endl;
					exit(EXIT_CODE_ERROR);
				}

				info->readOffset = 0;
				info->fFileData = NULL;
				info->fileName=  NULL;
				info->socket = t;
				info->state = FILE_SIZE;

				addClient(info);
			}

			for(size_t i = 0; i < clients.size(); i++)
			{
				if(clients[i] == NULL)
				{
					continue;
				}
				if (FD_ISSET(clients[i]->socket, &readSet))
				{
					switch (clients[i]->state)
					{
					case FILE_SIZE:
						if (readFromClient(clients[i], &clients[i]->fileSize, sizeof(int)))
						{
							if (clients[i]->fileSize < 0)
							{
								cerr << "ERROR: bad file size" << endl;
								exit(EXIT_CODE_ERROR);
							}

							clients[i]->state = NAME_SIZE;
						}
						break;

					case NAME_SIZE:
						if (readFromClient(clients[i], &clients[i]->nameSize, sizeof(int)))
						{
							if (clients[i]->nameSize < 0)
							{
								cerr << "ERROR: bad name size" << endl;
								exit(EXIT_CODE_ERROR);
							}

							clients[i]->state = FILE_NAME;
							clients[i]->fileName = (char*)malloc(clients[i]->nameSize + 1);

							if (clients[i]->fileName == NULL)
							{
								cerr << "ERROR: allocation failed" << endl;
								exit(EXIT_CODE_ERROR);
							}

							memset(clients[i]->fileName, 0, clients[i]->nameSize + 1);
						}
						break;

					case FILE_NAME:
						if (readFromClient(clients[i], clients[i]->fileName, clients[i]->nameSize + 1))
						{
							clients[i]->state = FILE_DATA;

							// Verify the file name ends with a "\0"
							clients[i]->fileName[clients[i]->nameSize] = '\0';

							// Open the file for writing
							clients[i]->fFileData = fopen(clients[i]->fileName, WRITE_ACCESS);

							if (clients[i]->fFileData == NULL)
							{
								cerr << "ERROR: open failed" << endl;
								exit(EXIT_CODE_ERROR);
							}
						}
						break;

					case FILE_DATA:
						if (readFileDataFromClient(clients[i]))
						{
							releaseClient(i);

#ifdef MEASURE_PERFORMANCE
							result = gettimeofday(&releaseTime, NULL);
							difference.tv_sec =
									releaseTime.tv_sec - establishmentTime.tv_sec;
							difference.tv_usec =
								 releaseTime.tv_usec - establishmentTime.tv_usec;

							// Converts the time difference into nanoseconds.
							double timeMicrosecons =
										difference.tv_sec * 1000000 + difference.tv_usec;
							cout.precision(12);
							cout << "Transfer time: " << timeMicrosecons << "us" << endl;
#endif
						}
						break;

					default:
						cerr << "ERROR: state error" << endl;
						exit(EXIT_CODE_ERROR);
						break;
					}
				}
			}
		}
	}
	return EXIT_CODE_SUCCESS;
}
