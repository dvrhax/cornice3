#include <Carbon/Carbon.h>
#include <stdio.h>
#include <Python.h>
#include <string.h>

#define CHECK_RET(val) {                                                \
                OSErr status;                                           \
                if ((status = (val)) != noErr) {                        \
                        PyErr_SetString(PyExc_OSError, my_strerror(status)); \
                        return NULL;                                    \
                }                                                       \
        }


static const char *my_strerror(OSErr status)
{
        switch (status) {
        case nsvErr:
                return "Volume not found";
        case fnfErr: case dirNFErr:
                return "File or directory not found";
        case volGoneErr:
                return "Server volume disconnected";
        case bdNamErr:
                return "Bad filename or volume name";
        case ioErr:
                return "I/O error";
        default:
                return strerror(status);
        }
}


static PyObject *get_ref_info(FSRef *folder)
{
        CFStringRef str;
        char path[PATH_MAX];

        CHECK_RET(LSCopyDisplayNameForRef(folder, &str));
        CHECK_RET(FSRefMakePath(folder, path, PATH_MAX));
        return Py_BuildValue("(ss)", path, CFStringGetCStringPtr(str, 0));
}


static PyObject *get_special_folder(short refnum, OSType type)
{
        FSRef folder;
        CHECK_RET(FSFindFolder(refnum, type, 0, &folder));
        return get_ref_info(&folder);
}


static PyObject *get_user_desktop(PyObject *self, PyObject *args)
{
        return get_special_folder(kUserDomain, kDesktopFolderType);
}


static PyObject *get_user_home(PyObject *self, PyObject *args)
{
        return get_special_folder(kUserDomain, kVolumeRootFolderType);
}


static PyObject *enum_folder(PyObject *self, PyObject *args)
{
        FSRef inFolder;
        OSStatus outStatus;
	
        // Get permissions and node flags and Finder info
        //
        // For maximum performance, specify in the catalog
        // bitmap only the information you need to know
        FSCatalogInfoBitmap kCatalogInfoBitmap = (kFSCatInfoNodeFlags |
                                                  kFSCatInfoFinderInfo);
	
        // number of catalog infos
        //
        // We use the number of FSCatalogInfos that will fit in
        // exactly four VM pages (#113). This is a good balance
        // between the iteration I/O overhead and the risk of
        // incurring additional I/O from additional memory
        // allocation
        const size_t num_requests = ((4096 * 4) /
                                     (sizeof(FSCatalogInfo) + sizeof(FSRef)));
        FSIterator iterator;
        FSCatalogInfo *info_array;
        FSRef *ref_array;

        char *folder_path;
        int hidden;

        PyObject *retval = NULL;

        if (!PyArg_ParseTuple(args, "si", &folder_path, &hidden)) {
                return NULL;
        }

        CHECK_RET(FSPathMakeRef(folder_path, &inFolder, NULL));
	
        // Create an iterator
        CHECK_RET(FSOpenIterator(&inFolder, kFSIterateFlat, &iterator));
	
        // Allocate storage for the returned information
        ref_array = (FSRef *) malloc(sizeof(FSRef) * num_requests);
        info_array = (FSCatalogInfo *) malloc(
                sizeof(FSCatalogInfo) * num_requests);
                
        if (ref_array == NULL || info_array == NULL) {
                goto err_clean;
        }

        retval = PyList_New(0);
        
        // Request information about files in the given
        // directory, until we get a status code back
        // from the File Manager
        do {
                UInt32  i;
                ItemCount actualCount;
                                
                outStatus = FSGetCatalogInfoBulk(
                        iterator, num_requests,
                        &actualCount, NULL, kCatalogInfoBitmap, 
                        info_array, ref_array, NULL, NULL);

                // Process all items received
                if (!(outStatus == noErr || outStatus == errFSNoMoreItems)) {
                        goto err_clean_2;
                }

                for (i = 0; i < actualCount; ++i) {
                        // Do something interesting
                        // with the object found
                        FSCatalogInfo *info = &info_array[i];
                        PyObject *t = NULL;
                        FInfo *finfo;
                        
                        if (!(info->nodeFlags & kFSNodeIsDirectoryMask)) {
                                continue;
                        }

                        finfo = (FInfo *)&info->finderInfo[0];
                        if (!hidden && finfo->fdFlags & kIsInvisible) {
                                continue;
                        }
                        
                        t = get_ref_info(&ref_array[i]);
                        if (!t) {
                                goto err_clean_2;
                        } else {
                                PyList_Append(retval, t);
                        }
                }
        }
        while (outStatus == noErr);

        // errFSNoMoreItems tells us we have successfully
        // processed all items in the directory --
        // not really an error
        if (outStatus == errFSNoMoreItems) {
                outStatus = noErr;
        }


  err_clean:
        // Free the array memory
        if (info_array) free ((void *) info_array);
        if (ref_array) free ((void *) ref_array);

        FSCloseIterator(iterator);

        return retval;

  err_clean_2:
        free ((void *) ref_array);
        free ((void *) info_array);
        Py_DECREF(retval);
        FSCloseIterator(iterator);
        
        return NULL;
}


static PyObject *enum_volumes(PyObject *self, PyObject *args)
{
        FSVolumeRefNum actual_volume;
        FSVolumeInfo volume_info;
        HFSUniStr255 volume_name;
        HFSUniStr255 name;
        FSRef root_dir;
        CFStringRef str;
        OSErr err = 0;
        int i = 1;
        char path[PATH_MAX];
        const char *label;

        PyObject *retval;

        retval = PyList_New(0);
        
        for (i = i; ; ++i) {
                err = FSGetVolumeInfo(kFSInvalidVolumeRefNum, i, &actual_volume,
                                      kFSVolInfoNone, &volume_info,
                                      &volume_name, &root_dir);

                if (err != 0) break;
        
                str = CFStringCreateWithCharacters(kCFAllocatorDefault,
                                                   volume_name.unicode,
                                                   volume_name.length);
        
                CFRelease(str);

                if (FSGetCatalogInfo(&root_dir, kFSCatInfoNone, NULL, &name,
                                     NULL, NULL) == noErr) {
                        str = CFStringCreateWithCharacters(kCFAllocatorDefault,
                                                           name.unicode,
                                                           name.length);
                        label = CFStringGetCStringPtr(str, 0);

                        FSRefMakePath(&root_dir, path, PATH_MAX);

                        PyList_Append(retval,
                                      Py_BuildValue("(ss)", path, label));
                                                            
                        CFRelease(str);
                }
        }

        return retval;
}


static PyMethodDef _dirctrlmac_helper_methods[] = {
        {"enum_volumes", (PyCFunction) enum_volumes, METH_VARARGS,
         "Gets a list of all the mounted volumes"},
        {"enum_folder", (PyCFunction) enum_folder, METH_VARARGS,
         "Gets a list of all the subfolders of the given folder"},
        {"get_user_home", (PyCFunction) get_user_home, METH_VARARGS,
         "Retrieves info (path, display name) for the user home dir"},
        {"get_user_desktop", (PyCFunction) get_user_desktop, METH_VARARGS,
         "Retrieves info (path, display name) for the user desktop dir"},
        {NULL, NULL, 0, NULL}
};


void init_dirctrlmac_helper(void)
{
        Py_InitModule("_dirctrlmac_helper", _dirctrlmac_helper_methods);
}
