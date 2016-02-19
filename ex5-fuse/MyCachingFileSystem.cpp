/*
 * myCachingFileSystem.cpp
 *
 *  Created on: 18 May 2014
 */

#define FUSE_USE_VERSION 26

#include <fuse.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <list>
#include <string>
#include <errno.h>
#include <stdio.h>
#include <algorithm>
#include <linux/limits.h>
#include <vector>
#include <memory.h>
#include <dirent.h>
#include <sys/time.h>
#include <time.h>
#include <iterator>
#include <stdlib.h>
#include <sstream>
#include <iostream>


using namespace std;

// Uncomment to enable O_DIRECT and O_SYNC
//#define ENABLE_DIRECT

#define SUCCESS 0
#define FAILURE -1
#define NOT_FOUND -1
#define ERR_READ -1
#define UPDATE_RECENT 1
#define ADD_NEW_BLOCK 2
#define LOG_FILE "/ioctloutput.log"
#define ERR_OPEN_LOG "system error: couldn't open ioctloutput.log file\n"
#define ERR_WRITE_LOG "system error: couldn't write to ioctloutput.log file\n"
#define ERR_SYSTEM_CALL "system error\n"
#define MSG_USAGE "usage: MyCachingFileSystem rootdir mountdir " \
		"numberOfBlocks blockSize\n"

struct fuse_operations caching_oper;

/* Information block saved in cache. */
typedef struct blockInfo  {
	size_t base;
	char * fileName;
	char * data;
	/* Actual size of the block */
	size_t size;
	/* Time block has been mapped to the cache */
	struct timeval time;
} blockInfo;

/* The global variables of the file system. */
typedef struct globalVariables {
	list<int> cacheManager;
	vector<blockInfo *> cacheVector;
	FILE * logFile;
	size_t blockSize;
	size_t numberOfBlocks;
	char rootdir[PATH_MAX];
} globalVariables;

/* Returns the absolute path of part */
static char * fullPath(const char *rootDir, const char *part)
{
	char * completePath = (char *)malloc(PATH_MAX);
	if (completePath == NULL)
	{
		cerr << ERR_SYSTEM_CALL;
		return NULL;
	}

	memset(completePath, '\0', PATH_MAX); // No error value.
	strcpy(completePath, rootDir); // No error value.
	strcat(completePath, part); // No error value.

	return completePath;

}

/* Update the cache manager, if flag =  UPDATE_RECENT it means we have no
 * room in the cache so we remove the least recently  accessed,
 * else we add the new index to the list. */
void updateCache(const int index, int flag, globalVariables * context)
{
	int result = gettimeofday(&(context->cacheVector.at(index)->time), NULL);
	if (result != SUCCESS)
	{
		cerr << ERR_SYSTEM_CALL;
		return;
	}

	if (flag == UPDATE_RECENT)
	{
		context->cacheManager.remove(index);
	}

	context->cacheManager.push_front(index);
}

/* Finds a block in the cache by its path. */
int findBlockInCache(const char * path, off_t offset, globalVariables *context)
{
	for(size_t i = 0; i < context->cacheVector.size(); i++)
	{
		size_t base = context->cacheVector.at(i)->base;
		size_t size = context->cacheVector.at(i)->size;
		if (base <= (size_t)offset &&
				(size_t)offset < base + size &&
				strcmp(context->cacheVector.at(i)->fileName, path) == 0)
		{
			return i;
		}
	}
	return NOT_FOUND;
}

/* When a user calls rename - we should change all entries with the old name.*/
void renameCache(const char * path, const char * newpath,
		globalVariables * context)
{
	for(size_t i = 0; i < context->cacheVector.size(); i++)
	{
		if(strcmp(context->cacheVector.at(i)->fileName, path) == 0)
		{
			strcpy(context->cacheVector.at(i)->fileName, newpath);
		}
	}
}

/** Get file attributes.
 *
 * Similar to stat().  The 'st_dev' and 'st_blksize' fields are
 * ignored.  The 'st_ino' field is ignored except if the 'use_ino'
 * mount option is given.
 */
int caching_getattr(const char *path, struct stat * statbuf)
{
	globalVariables * context =
			(globalVariables *)(fuse_get_context()->private_data);
	int retstat = 0;
	char * sourcePath = fullPath(context->rootdir, path);
	if (sourcePath == NULL)
	{
		return -ENOMEM;
	}

	retstat = lstat(sourcePath, statbuf);

	if (retstat != SUCCESS)
	{
		int errorCode = -errno;
		cerr << ERR_SYSTEM_CALL;
		free(sourcePath);
		return errorCode;
	}

	free(sourcePath);
	return SUCCESS;
}

/**
 * Get attributes from an open file
 *
 * This method is called instead of the getattr() method if the
 * file information is available.within
 *
 * Currently this is only called after the create() method if that
 * is implemented (see above).  Later it may be called for
 * invocations of fstat() too.
 *
 * Introduced in version 2.5
 */
int caching_fgetattr(const char *path, struct stat *statbuf,
		struct fuse_file_info *fi)
{
	int result = fstat(fi->fh, statbuf);
	if (result != SUCCESS)
	{
		int errorCode = -errno;
		cerr << ERR_SYSTEM_CALL;
		return errorCode;
	}

	return SUCCESS;
}

/**
 * Check file access permissions
 *
 * This will be called for the access() system call.  If the
 * 'default_permissions' mount option is given, this method is not
 * called.
 *
 * This method is not called under Linux kernel versions 2.4.x
 *
 * Introduced in version 2.5
 */
int caching_access(const char *path, int mask)
{
	if (mask & W_OK)
	{
		return -EACCES;
	}

	globalVariables * context =
			(globalVariables *)(fuse_get_context()->private_data);
	char * sourcePath = fullPath(context->rootdir, path);

	int result = access(sourcePath, mask);
	if (result != SUCCESS)
	{
		int errorCode = -errno;
		cerr << ERR_SYSTEM_CALL;
		free(sourcePath);
		return errorCode;
	}

	free(sourcePath);

	return SUCCESS;
}

/** File open operation
 *
 * No creation, or truncation flags (O_CREAT, O_EXCL, O_TRUNC)
 * will be passed to open().  Open should check if the operation
 * is permitted for the given flags.  Optionally open may also
 * return an arbitrary filehandle in the fuse_file_info structure,
 * which will be passed to all file operations.
 *
 * Changed in version 2.2
 */
int caching_open(const char *path, struct fuse_file_info *fi)
{
	int fd;
	globalVariables * context =
			(globalVariables *)(fuse_get_context()->private_data);

	if (fi->flags & (O_CREAT | O_TRUNC | O_APPEND))
	{
		return -EACCES;
	}

#ifdef ENABLE_DIRECT
	/* Should always open with O_DIRECT and O_SYNC */
	fi->flags |= O_DIRECT | O_SYNC;
#endif

	char * sourcePath = fullPath(context->rootdir, path);
	if (sourcePath == NULL)
	{
		return -ENOMEM;
	}

	fd = open(sourcePath, fi->flags);
	if (fd < 0)
	{
		int errorCode = -errno;
		cerr << ERR_SYSTEM_CALL;
		free(sourcePath);
		return errorCode;
	}

	fi->fh = fd;
	free(sourcePath);
	return SUCCESS;
}

void readFromBlock(blockInfo * block, char **buf, size_t &size, off_t &offset,
		globalVariables *context)
{
	size_t bytesToRead = min(
			context->blockSize,
			block->base + block->size - offset);
	bytesToRead = min(bytesToRead, size);
	int remaining = block->size - (offset - block->base);
	memcpy(*buf, block->data + block->size - remaining, bytesToRead);
	size -= bytesToRead;
	offset += bytesToRead;
	*buf += bytesToRead;
}

// Helper function to read data of requested size or until EOF
int readHelper(int fd, char *buf, size_t size)
{
	int total = 0, readSize;

	do
	{
		readSize = read(fd, buf + total, size - (size_t)total);

		if (readSize > 0)
		{
			total += readSize;
		}
	}
	while (readSize > 0 && (size_t)total < size);

	if (total > 0)
	{
		return total; // Return the total number of bytes read
	}

	if (readSize < 0) // Read error and no bytes read
	{
		return ERR_READ;
	}

	return 0; // No bytes read (end of file)
}

/** Read data from an open file
 *
 * Read should return exactly the number of bytes requested except
 * on EOF or error, otherwise the rest of the data will be
 * substituted with zeroes.  An exception to this is when the
 * 'direct_io' mount option is specified, in which case the return
 * value of the read system call will reflect the return value of
 * this operation.
 *
 * Changed in version 2.2
 */
int caching_read(const char *path, char *buf, size_t size, off_t offset,
		struct fuse_file_info *fi)
{
	globalVariables * context =
			(globalVariables *)(fuse_get_context()->private_data);
	int result = size;

	while(size > 0)
	{
		int index = findBlockInCache(path, offset, context);
		if (index != NOT_FOUND)
		{
			readFromBlock(
					context->cacheVector[index], &buf, size, offset, context);
			updateCache(index, UPDATE_RECENT, context);

			// This is the last block in file, we can return
			if (context->cacheVector[index]->size < context->blockSize)
			{
				return result - size;
			}
		}
		else
		{
			blockInfo * newBlock = new blockInfo();
			newBlock->fileName = (char *)malloc(PATH_MAX);
			if (newBlock->fileName == NULL)
			{
				delete newBlock;
				cerr << ERR_SYSTEM_CALL;
				return result - size;
			}

			int align_result = posix_memalign(
					(void**)&(newBlock->data),
					context->blockSize,
					context->blockSize);

			if (align_result != 0)
			{
				free(newBlock->fileName);
				delete newBlock;
				cerr << ERR_SYSTEM_CALL;
				return result - size;
			}

			memset(newBlock->fileName, '\0', PATH_MAX);
			strcpy(newBlock->fileName, path);

			newBlock->base = (offset / context->blockSize) *
					context->blockSize;
			int startFrom = newBlock->base;

			int seekResult = lseek(fi->fh, startFrom , SEEK_SET);
			if (seekResult == FAILURE)
			{
				free(newBlock->data);
				free(newBlock->fileName);
				delete newBlock;
				cerr << ERR_SYSTEM_CALL;
				return result - size;
			}

			int readBytes = readHelper(fi->fh, newBlock->data , context->blockSize);
			if (readBytes == ERR_READ)
			{
				free(newBlock->data);
				free(newBlock->fileName);
				delete newBlock;
				cerr << ERR_SYSTEM_CALL;
				return result - size;
			}

			newBlock->size = readBytes;

			readFromBlock(newBlock, &buf, size, offset, context);

			if (context->cacheVector.size() < context->numberOfBlocks)
			{
				context->cacheVector.push_back(newBlock);
				updateCache(
						context->cacheVector.size() - 1,
						ADD_NEW_BLOCK,
						context);
			}
			else
			{
				int lastIndex = context->cacheManager.back();
				free(context->cacheVector[lastIndex]->fileName);
				free(context->cacheVector[lastIndex]->data);
				delete context->cacheVector[lastIndex];

				context->cacheVector[lastIndex] = newBlock;
				updateCache(lastIndex, UPDATE_RECENT, context);
			}

			// This is the last block in file, we can return
			if (readBytes < (long int)context->blockSize) // End of file
			{
				return result - size;
			}
		}
	}

	return result - size;
}

/** Possibly flush cached data
 *
 * BIG NOTE: This is not equivalent to fsync().  It's not a
 * request to sync dirty data.
 *
 * Flush is called on each close() of a file descriptor.  So if a
 * filesystem wants to return write errors in close() and the file
 * has cached dirty data, this is a good place to write back data
 * and return any errors.  Since many applications ignore close()
 * errors this is not always useful.
 *
 * NOTE: The flush() method may be called more than once for each
 * open().  This happens if more than one file descriptor refers
 * to an opened file due to dup(), dup2() or fork() calls.  It is
 * not possible to determine if a flush is final, so each flush
 * should be treated equally.  Multiple write-flush sequences are
 * relatively rare, so this shouldn't be a problem.
 *
 * Filesystems shouldn't assume that flush will always be called
 * after some writes, or that if will be called at all.
 *
 * Changed in version 2.2
 */
int caching_flush(const char *path, struct fuse_file_info *fi)
{
	return SUCCESS;
}

/** Release an open file
 *
 * Release is called when there are no more references to an open
 * file: all file descriptors are closed and all memory mappings
 * are unmapped.
 *
 * For every open() call there will be exactly one release() call
 * with the same flags and file descriptor.  It is possible to
 * have a file opened more than once, in which case only the last
 * release will mean, that no more reads/writes will happen on the
 * file.  The return value of release is ignored.
 *
 * Changed in version 2.2
 */
int caching_release(const char *path, struct fuse_file_info *fi)
{
	int result = close(fi->fh);
	if (result != SUCCESS)
	{
		int errorCode = -errno;
		cerr << ERR_SYSTEM_CALL;
		return errorCode;
	}

	return SUCCESS;
}

/** Open directory
 *
 * This method should check if the open operation is permitted for
 * this  directory
 *
 * Introduced in version 2.3
 */
int caching_opendir(const char *path, struct fuse_file_info *fi)
{
	DIR *dp;
	globalVariables * context =
			(globalVariables *)(fuse_get_context()->private_data);

	char * sourcePath = fullPath(context->rootdir, path);
	if (sourcePath == NULL)
	{
		return -ENOMEM;
	}

	dp = opendir(sourcePath);
	if (dp == NULL)
	{
		int errorCode = -errno;
		free(sourcePath);
		cerr << ERR_SYSTEM_CALL;
		return errorCode;
	}

	fi->fh = (intptr_t) dp;
	free(sourcePath);

	return SUCCESS;
}

/** Read directory
 *
 * This supersedes the old getdir() interface.  New applications
 * should use this.
 *
 * The filesystem may choose between two modes of operation:
 *
 * 1) The readdir implementation ignores the offset parameter, and
 * passes zero to the filler function's offset.  The filler
 * function will not return '1' (unless an error happens), so the
 * whole directory is read in a single readdir operation.  This
 * works just like the old getdir() method.
 *
 * 2) The readdir implementation keeps track of the offsets of the
 * directory entries.  It uses the offset parameter and always
 * passes non-zero offset to the filler function.  When the buffer
 * is full (or an error happens) the filler function will return
 * '1'.
 *
 * Introduced in version 2.3
 */
int caching_readdir(const char *path, void *buf, fuse_fill_dir_t filler,
		off_t offset, struct fuse_file_info *fi)
{
	DIR *dp;
	struct dirent *de;

	dp = (DIR *) (uintptr_t) fi->fh;
	de = readdir(dp);
	if (de == NULL)
	{
		int errorCode = -errno;
		cerr << ERR_SYSTEM_CALL;
		return errorCode;
	}

	do {
		if (filler(buf, de->d_name, NULL, 0) != 0)
		{
			cerr << ERR_SYSTEM_CALL;
			return -ENOMEM;
		}
	} while ((de = readdir(dp)) != NULL);

	return SUCCESS;
}

/** Release directory
 *
 * Introduced in version 2.3
 */
int caching_releasedir(const char *path, struct fuse_file_info *fi)
{
	int result = closedir((DIR *) (uintptr_t) fi->fh);
	if (result != SUCCESS)
	{
		int errorCode = -errno;
		cerr << ERR_SYSTEM_CALL;
		return errorCode;
	}

	return SUCCESS;
}

/** Rename a file */
int caching_rename(const char *path, const char *newpath)
{
	globalVariables * context =
			(globalVariables *)(fuse_get_context()->private_data);
	char * source = fullPath(context->rootdir, path);
	if (source == NULL)
	{
		return -ENOMEM;
	}

	char * newPath = fullPath(context->rootdir, newpath);
	if (newPath == NULL)
	{
		free(source);
		return -ENOMEM;
	}

	int retstat = rename(source, newPath);
	if (retstat != SUCCESS)
	{
		int errorCode = -errno;
		cerr << ERR_SYSTEM_CALL;
		free(source);
		free(newPath);
		return errorCode;
	}

	renameCache(path, newpath, context);

	free(source);
	free(newPath);

	return SUCCESS;
}

/**
 * Initialize filesystem
 *
 * The return value will passed in the private_data field of
 * fuse_context to all file operations and as a parameter to the
 * destroy() method.
 *
 * Introduced in version 2.3
 * Changed in version 2.6
 */
void *caching_init(struct fuse_conn_info *conn)
{
	return fuse_get_context()->private_data;
}

/**
 * Clean up filesystem
 *
 * Called on filesystem exit.
 *
 * Introduced in version 2.3within
 */
void caching_destroy(void *userdata)
{
	globalVariables * context =
			(globalVariables *)(fuse_get_context()->private_data);

	for(size_t i = 0; i < context->cacheVector.size(); i++){
		free(context->cacheVector.at(i)->data);
		free(context->cacheVector.at(i)->fileName);
		delete context->cacheVector.at(i);
	}
	context->cacheManager.clear();

	int result = fclose(context->logFile);
	if (result != SUCCESS)
	{
		cerr << ERR_SYSTEM_CALL;
	}

	delete context;
}

/**
 * Ioctl
 *
 * flags will have FUSE_IOCTL_COMPAT set for 32bit ioctls in
 * 64bit environment.  The size and direction of data is
 * determined by _IOC_*() decoding of cmd.  For _IOC_NONE,
 * data will be NULL, for _IOC_WRITE data is out area, for
 * _IOC_READ in area and if both are set in/out area.  In all
 * non-NULL cases, the area is of _IOC_SIZE(cmd) bytes.
 *
 * Introduced in version 2.8
 */
int caching_ioctl (const char *, int cmd, void *arg,
		struct fuse_file_info *, unsigned int flags, void *data)
{
	globalVariables * context =
			(globalVariables *)(fuse_get_context()->private_data);
	if (context->logFile == NULL)
	{
		cerr << ERR_WRITE_LOG;
		return NOT_FOUND;
	}

	struct timeval currTime;
	int result = gettimeofday(&currTime, NULL);
	if (result != SUCCESS)
	{
		cerr << ERR_SYSTEM_CALL;
		return NOT_FOUND;
	}

	struct tm * UTCTime = gmtime(&currTime.tv_sec); // No error value.

	result = fprintf(
			context->logFile,
			"%02d:%02d:%02d:%02d:%02d:%03lu\n",
			UTCTime->tm_mon,
			UTCTime->tm_mday,
			UTCTime->tm_hour,
			UTCTime->tm_min,
			UTCTime->tm_sec,
			(currTime.tv_usec / 1000));
	if (result < 0)
	{
		cerr << ERR_WRITE_LOG;
		return NOT_FOUND;
	}

	for (list<int>::iterator it = context->cacheManager.begin();


			it != context->cacheManager.end(); it++)
	{
		blockInfo * block = context->cacheVector.at(*it);
		struct timeval time = block->time;
		int blockNumber = (block->base / context->blockSize) + 1;

		UTCTime = gmtime(&time.tv_sec);
		result = fprintf(
				context->logFile,
				"%s\t%d\t%02d:%02d:%02d:%02d:%02d:%03lu\n",
				block->fileName,
				blockNumber,
				UTCTime->tm_mon,
				UTCTime->tm_mday,
				UTCTime->tm_hour,
				UTCTime->tm_min,
				UTCTime->tm_sec,
				(time.tv_usec / 1000));
		if (result < 0)
		{
			cerr << ERR_WRITE_LOG;
			return NOT_FOUND;
		}
	}

	return SUCCESS;
}

int isDirectory(const char *path)
{
	struct stat st;

	if (stat(path, &st) != SUCCESS)
	{
		return FAILURE;
	}

	if (S_ISDIR(st.st_mode))
	{
		return SUCCESS;
	}

	return FAILURE;
}

int main(int argc, char* argv[])
{
	caching_oper.getattr = caching_getattr;
	caching_oper.access = caching_access;
	caching_oper.open = caching_open;
	caching_oper.read = caching_read;
	caching_oper.flush = caching_flush;
	caching_oper.release = caching_release;
	caching_oper.opendir = caching_opendir;
	caching_oper.readdir = caching_readdir;
	caching_oper.releasedir = caching_releasedir;
	caching_oper.rename = caching_rename;
	caching_oper.init = caching_init;
	caching_oper.destroy = caching_destroy;
	caching_oper.ioctl = caching_ioctl;
	caching_oper.fgetattr = caching_fgetattr;


	caching_oper.readlink = NULL;
	caching_oper.getdir = NULL;
	caching_oper.mknod = NULL;
	caching_oper.mkdir = NULL;
	caching_oper.unlink = NULL;
	caching_oper.rmdir = NULL;
	caching_oper.symlink = NULL;
	caching_oper.link = NULL;
	caching_oper.chmod = NULL;
	caching_oper.chown = NULL;
	caching_oper.truncate = NULL;
	caching_oper.utime = NULL;
	caching_oper.write = NULL;
	caching_oper.statfs = NULL;
	caching_oper.fsync = NULL;
	caching_oper.setxattr = NULL;
	caching_oper.getxattr = NULL;
	caching_oper.listxattr = NULL;
	caching_oper.removexattr = NULL;
	caching_oper.fsyncdir = NULL;
	caching_oper.create = NULL;
	caching_oper.ftruncate = NULL;

	globalVariables * context = new globalVariables;
	char * logPath = (char* )malloc(PATH_MAX);

	if(logPath == NULL)
	{ // Continue without writing a log.
		cerr << ERR_SYSTEM_CALL;
	}
	else
	{
		char * res = getcwd(logPath, PATH_MAX);
		if (res == NULL)
		{
			cerr << ERR_SYSTEM_CALL;
		}
		else
		{
			strcat(logPath, LOG_FILE);
			context->logFile = fopen(logPath, "a+");

			if (context->logFile == NULL)
			{
				cerr << ERR_OPEN_LOG;
			}
		}

		free(logPath);
	}

	bool printUsage = false;

	if (argc != 5)
	{
		printUsage = true;
	}
	else
	{
		context->blockSize = atoi(argv[4]);
		context->numberOfBlocks = atoi(argv[3]);

		if (context->blockSize <= 0 || context->numberOfBlocks <= 0)
		{
			printUsage = true;
		}
		else
		{
			if (isDirectory(argv[1]) != SUCCESS ||
				isDirectory(argv[2]) != SUCCESS)
			{
				printUsage = true;
			}
		}
	}

	if (printUsage)
	{
		int result = fprintf(context->logFile, MSG_USAGE);

		if (result < 0)
		{
			cerr << ERR_WRITE_LOG;
		}

		return FAILURE;
	}

	strcpy(context->rootdir, argv[1]);

	/* We need to pass the -s flag [single thread] so we need it in a buffer
	 * (since argv is not const) */
	char flagSingleThread[] = "-s";

	argv[1] = argv[2];
	argv[2] = flagSingleThread;
	argc = 3;


	/*
	//// Enable this for tests! (foreground mode)
	char flagForeground[] = "-f";
	argv[3] = flagForeground;
	argc = 4;
	*/

	int fuse_stat = fuse_main(argc, argv, &caching_oper, context);

	return fuse_stat;
}
