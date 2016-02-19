#include <stdio.h>
#include <cstdlib>
#include <vector>
#include <pthread.h>
#include <string.h>
#include <iostream>
#include <limits.h>

#define SUCCESS 0
#define WAS_FLUSHED 1
#define CLOSE_SUCCESS 1
#define FAILURE -1
#define ACCESS_WRITE "a"
#define FILE_SYSTEM_ERROR -2
#define MUST_CALL_CLOSE -2
#define NO_TASK_ID -2
#define CLOSE_PROGRAM_FLAG 2

// Error messages:
#define SYS_ERR "system error\n"
#define EXIT_SYS_ERR 1
#define ERROR_OCCURED "Output device library error\n"

typedef enum {UNUSED, USED} State;

using namespace std;

typedef struct Task {
	char * buffer;
	int size;
	State state;
} Task;


vector<Task*> tasks;
int howManyWereWritten;
FILE * file = NULL;
bool isChildThreadFinished;
bool isClosingFinished;
bool flagCloseSystem = false;
bool flagShutDown;
bool flagMaxInt;

pthread_mutex_t  mWriteVector;
pthread_mutex_t  mHowManyWritten;
pthread_mutex_t  mFlagMaxInt;
pthread_mutex_t  mShutDown = PTHREAD_MUTEX_INITIALIZER;

//This function locks a given mutex and exits the program in case of an error.
void lock(pthread_mutex_t* mutex)
{
	int result = pthread_mutex_lock(mutex);
	if(result != SUCCESS)
	{
		cerr << SYS_ERR;
		exit(EXIT_SYS_ERR);
	}
}

//This function unlocks a given mutex and exits the program in case of an error.
void unlock(pthread_mutex_t* mutex)
{
	int result = pthread_mutex_unlock(mutex);
	if(result != SUCCESS)
	{
		cerr << SYS_ERR;
		exit(EXIT_SYS_ERR);
	}
}

//Finds the next task to write to disk.
int findAvailableTask()
{
	for(int i = 0; i < (int)tasks.size(); i++)
	{
		if(tasks.at(i) != NULL && tasks.at(i)->buffer != NULL)
		{
			return i;
		}
	}
	return FAILURE;
}

//Releases all the resources in the closing process.
void* releaseResources(void * args)
{
	int result;
	lock(&mShutDown);
	while(!isChildThreadFinished)
	{
		unlock(&mShutDown);
		lock(&mShutDown);
	}
	flagShutDown = true;
	unlock(&mShutDown);

	for(int i = tasks.size() - 1; i >= 0; i--)
	{
		free(tasks.at(i)->buffer);
		tasks.at(i)->buffer = NULL;
		delete tasks.at(i);
		tasks.at(i) = NULL;
		tasks.pop_back();
	}
	tasks.clear();

	result = fclose(file);
	if(result == EOF)
	{
		cerr << SYS_ERR;
		exit(EXIT_SYS_ERR);
	}
	file = NULL;
	pthread_mutex_destroy(&mWriteVector);
	pthread_mutex_destroy(&mHowManyWritten);
	lock(&mShutDown);
	isClosingFinished = true;
	flagCloseSystem = false;
//	flagShutDown = false;
	unlock(&mShutDown);
	return NULL;
}

//This function should run as a thread in the background and flush all tasks to the disk.
void *flushBackground(void *args)
{
	lock(&mShutDown);
	while (!flagCloseSystem)
	{
		unlock(&mShutDown);
		int task_id;

		lock(&mWriteVector);
		while((task_id = findAvailableTask()) != FAILURE)
		{
			tasks.at(task_id)->state = USED;

			unlock(&mWriteVector);

			int numberOfbytes = fwrite(tasks.at(task_id)->buffer, sizeof(char), tasks.at(task_id)->size, file);

			if (numberOfbytes < tasks.at(task_id)->size)
			{
				isChildThreadFinished = true;
				releaseResources(NULL);
				cerr << SYS_ERR;
				exit(EXIT_SYS_ERR);
			}

			lock(&mWriteVector);
			free(tasks.at(task_id)->buffer);
			tasks.at(task_id)->buffer = NULL;
			tasks.at(task_id)->state = UNUSED;

			unlock(&mWriteVector);

			lock(&mHowManyWritten);
			lock(&mFlagMaxInt);
			if(flagMaxInt == true && howManyWereWritten != INT_MAX)
			{
				flagMaxInt = false;
			}
			if(howManyWereWritten == INT_MAX)
			{
				flagMaxInt = true;
				howManyWereWritten = 0;
			}
			unlock(&mFlagMaxInt);
			howManyWereWritten++;
			unlock(&mHowManyWritten);
			lock(&mWriteVector);
		}
		unlock(&mWriteVector);
		lock(&mShutDown);
	}
	unlock(&mShutDown);
	// Closing process
	lock(&mShutDown);
	isChildThreadFinished = true;
	unlock(&mShutDown);
	return NULL;
}

//Finds the lowest task id available.
int nextPlace()
{
	for(int i = 0; i < (int)tasks.size(); i++)
	{
		if(tasks.at(i) != NULL &&
				tasks.at(i)->buffer == NULL
				&& tasks.at(i)->state == UNUSED)
		{
			return i;
		}
	}
	return FAILURE;
}

//Checks if the given id exists.
int findTaskId(int taskId)
{
	if((int)tasks.size() - 1 < taskId)
	{
		cout << '%' << tasks.size() <<'%'<< flagShutDown << endl;
		return NO_TASK_ID;
	}

	if(tasks.at(taskId)->buffer != NULL)
	{
		return SUCCESS;
	}
	return FAILURE;
}

/*
 * DESCRIPTION: The function creates the file filename if it does not exist and open the file for writing.
 *              This function should be called prior to any other functions as a necessary precondition for their success.
 *
 * RETURN VALUE: On success 0, -2 for a filesystem error (inability to create the file, etc.), otherwise -1.
 */
int initdevice(char *filename)
{
	lock(&mShutDown);
	if(filename == NULL || flagCloseSystem)
	{
		unlock(&mShutDown);
		cerr << ERROR_OCCURED;
		return FAILURE;
	}
	unlock(&mShutDown);

	int result;
	pthread_t flushWorkingThread;
	void *args = NULL;

	if (file != NULL)
	{
		// Already initialized.
		return SUCCESS;
	}

	lock(&mShutDown);
	isChildThreadFinished = false;
	isClosingFinished = false;
	flagShutDown = false;
	flagCloseSystem = false;
	unlock(&mShutDown);

	file = fopen(filename ,ACCESS_WRITE);
	if (file == NULL)
	{
		cerr << SYS_ERR;
		return FILE_SYSTEM_ERROR;
	}

	result = pthread_mutex_init(&mFlagMaxInt, NULL);
	if (result != SUCCESS)
	{
		fclose(file);
		// Will never fail because calling create thread was already created.
		cerr << SYS_ERR;
		return FAILURE;
	}

	result = pthread_mutex_init(&mWriteVector, NULL);
	if (result != SUCCESS)
	{
		fclose(file);
		// Will never fail because calling create thread was already created.
		pthread_mutex_destroy(&mFlagMaxInt);
		cerr << SYS_ERR;
		return FAILURE;
	}

	result = pthread_mutex_init(&mHowManyWritten, NULL);
	if (result != SUCCESS)
	{
		fclose(file);
		// Will never fail because calling create thread was already created.
		pthread_mutex_destroy(&mWriteVector);
		pthread_mutex_destroy(&mFlagMaxInt);
		cerr << SYS_ERR;
		return FAILURE;
	}

	lock(&mHowManyWritten);
	howManyWereWritten = 0;
	unlock(&mHowManyWritten);

	lock(&mFlagMaxInt);
	flagMaxInt = false;
	unlock(&mFlagMaxInt);

	result = pthread_create(&flushWorkingThread, NULL, flushBackground, args);
	if (result != SUCCESS)
	{
		fclose(file);
		pthread_mutex_destroy(&mWriteVector);
		pthread_mutex_destroy(&mHowManyWritten);
		pthread_mutex_destroy(&mFlagMaxInt);
		cerr << SYS_ERR;
		return FAILURE;
	}
	return SUCCESS;
}

/*
 * DESCRIPTION: The function writes the input buffer to the file. The buffer may be freed once this call returns.
 *              You should deal with any memory management issues.
 * 		Note this is non-blocking package you are required to implement you should return ASAP,
 * 		even if the buffer has not yet been written to the disk.
 *
 * RETURN VALUE: On success, the function returns a task_id (>= 0), which identifies this write operation.
 * 		 Note, you should reuse task_ids when they become available.  On failure, -1 will be returned.
 */
int write2device(char *buffer, int length)
{
	lock(&mShutDown);
	if (file == NULL || flagCloseSystem)
	{
		// Not yet initialized.
		unlock(&mShutDown);
		return FAILURE;
	}
	unlock(&mShutDown);

	if(buffer == NULL || length <= 0 )
	{
		cerr << ERROR_OCCURED;
		return FAILURE;
	}

	lock(&mWriteVector);

	//find next available place
	int index = nextPlace();
	if(index == FAILURE)
	{ // Allocate new space
		Task *tempTask = new Task;
		if(tempTask == NULL)
		{
			cerr << SYS_ERR;
			return FAILURE;
		}
		tempTask->buffer = (char *)malloc(sizeof(char) * length);
		if(tempTask->buffer == NULL)
		{
			delete tempTask;
			cerr << SYS_ERR;
			return FAILURE;
		}
		memcpy(tempTask->buffer, buffer,length);
		tempTask->size = length;
		tempTask->state = UNUSED;


		tasks.push_back(tempTask);
		index = tasks.size() - 1;
	}
	else
	{
		tasks.at(index)->buffer = (char *)malloc(sizeof(char) * length);
		if(tasks.at(index)->buffer == NULL)
		{
			cerr << SYS_ERR;
			return FAILURE;
		}
		memcpy(tasks.at(index)->buffer, buffer, length);
		tasks.at(index)->size = length;
	}

	unlock(&mWriteVector);

	return index;
}

/*
 * DESCRIPTION: return (withoug blocking) whether the specified task_id has been written to the file
 *      (0 if yes, 1 if not).
 * 		The task_id is a value that was previously returned by write2device function.
 * 		In case of task_id doesn't exist, should return -2; In case of other errors, return -1.
 *
 */
int wasItWritten(int task_id)
{
	int result;
	lock(&mShutDown);
	if (file == NULL || flagShutDown)
	{
		unlock(&mShutDown);
		// Not yet initialized.
		return FAILURE;
	}

	lock(&mWriteVector);
	int index = findTaskId(task_id);
	unlock(&mWriteVector);

	if (index == NO_TASK_ID)
	{
		result = NO_TASK_ID;
	}
	else if (index == FAILURE)
	{
		result = SUCCESS;
	}
	else
	{
		result = WAS_FLUSHED;
	}
	unlock(&mShutDown);
	return result;
}

/*
 * DESCRIPTION: Block until the specified task_id has been written to the file.
 * 		The task_id is a value that was previously returned by write2device function.
 * 		In case of task_id doesn't exist, should return -2; In case of other errors, return -1.
 *
 */
int flush2device(int task_id)
{
	lock(&mShutDown);
	if(file == NULL || flagShutDown)
	{
		unlock(&mShutDown);
		return FAILURE;
	}
	unlock(&mShutDown);
	int result = wasItWritten(task_id);
	if (result == NO_TASK_ID)
	{
		return result;
	}

	if (result == SUCCESS)
	{
		return WAS_FLUSHED;
	}

	while (true)
	{
		if(wasItWritten(task_id) == 0)
		{
			break;
		}
	}

	return WAS_FLUSHED;
}

/*
 * DESCRIPTION: return (withoug blocking) how many tasks have been written to file since last initdevice.
 *      If number exceeds MAX_INT, return MIN_INT.
 * 		In case of error, return -1.
 *
 */
int howManyWritten()
{
	int result;
	lock(&mShutDown);
	if (file == NULL || flagShutDown)
	{
		// Not yet initialized.
		unlock(&mShutDown);
		return FAILURE;
	}


	lock(&mHowManyWritten);
	lock(&mFlagMaxInt);
	if(flagMaxInt == true)
	{
		result = INT_MIN;
	}
	else
	{
		result = howManyWereWritten;
	}
	unlock(&mFlagMaxInt);
	unlock(&mHowManyWritten);
	unlock(&mShutDown);
	return result;
}


/*
 * DESCRIPTION: close the output file and reset the system so that it is possible to call initdevice again.
 *              All pending task_ids should be written to output disk file.
 *              Any attempt to write new buffers (or initialize) while the system is shutting down should
 *              cause an error.
 *              In case of error, the function should cause the process to exit.
 *
 */
void closedevice()
{
	lock(&mShutDown);
	if (file == NULL || flagCloseSystem)
	{
		unlock(&mShutDown);
		// Not yet initialized or closing.
		return;
	}
	unlock(&mShutDown);
	flagCloseSystem = true;
	pthread_t closingThread;
	int result = pthread_create(&closingThread, NULL, releaseResources, NULL);
	if (result != SUCCESS)
	{
		releaseResources(NULL);
		cerr << SYS_ERR;
		exit(EXIT_SYS_ERR);
	}
}

/*
 * DESCRIPTION: Wait for closedevice to finish.
 *              If closing was successful, it returns 1.
 *              If closedevice was not called it should return -2.
 *              In case of other error, it should return -1.
 *
 */
int wait4close()
{
	lock(&mShutDown);
	if (isClosingFinished)
	{
		unlock(&mShutDown);
		return CLOSE_SUCCESS;
	}

	if (!flagCloseSystem)
	{
		return MUST_CALL_CLOSE;
	}
	unlock(&mShutDown);
	lock(&mShutDown);
	while(!isClosingFinished)
	{
		unlock(&mShutDown);
		lock(&mShutDown);
	}
	unlock(&mShutDown);

	return CLOSE_SUCCESS;
}

