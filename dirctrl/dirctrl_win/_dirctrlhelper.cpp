// -*- mode: C++; indent-tabs-mode: t; c-basic-offset: 8; -*-
// _dirctrlhelper.cpp: Modulo ausiliario per la costruzione di un dir
// control per windows

#include "Python.h"

#include <shlobj.h>
#include <shlwapi.h>
#include <assert.h>
#include <stdio.h>
#include <tchar.h>

//#include <map>

#define CHECK_RET(val, str) if (!SUCCEEDED(val)) { \
				log_msg(str ":"); \
				log_msg(NULL); \
				Py_XDECREF(retval);	    \
                                PyErr_SetFromWindowsErr(0); \
                                return NULL; \
                            }

// se e' 1, abilita logging per debug...
#define ALB_DEBUG 0

#if ALB_DEBUG
#define log_msg(msg) _log_msg(msg)
#else
#define log_msg(msg)
#endif

// prototipi: funzioni ausiliarie per la manipolazione dei PIDLs e altro...
staticforward IShellFolder *get_desktop_folder();
staticforward IMalloc *get_malloc();
staticforward long get_itemid_size(LPCITEMIDLIST pidl);
staticforward LPITEMIDLIST concat_itemids(LPCITEMIDLIST p1, LPCITEMIDLIST p2);

staticforward LPITEMIDLIST get_control_panel_pidl();

staticforward int get_special_sort_index(LPCITEMIDLIST pidl);

staticforward FILE *get_log_target(void);

staticforward void _log_msg(const char *msg);

// ogni directory e` rappresentata da una tupla cosi` composta:
// (pidl, display name, path, icon location, icon index,
//  open icon location, open icon index, has subfolder, special sort index)

// ritorna la radice del file system, ovvero la directory Desktop
// non prende nessun argomento
static PyObject *get_root(PyObject *self, PyObject *args)
{
	LPMALLOC pmalloc;
	LPITEMIDLIST pidl = NULL;
	IShellFolder *desktop = NULL;
	STRRET str;
	TCHAR display_name[MAX_PATH];
	TCHAR path[MAX_PATH];
	SHFILEINFO file_info;
    
	PyObject *retval = NULL;

	if (!PyArg_ParseTuple(args, "")) {
		return NULL;
	}

	pmalloc = get_malloc();
	desktop = get_desktop_folder();
    
	CHECK_RET(SHGetSpecialFolderLocation(NULL, CSIDL_DESKTOP, &pidl),
		  "SHGetSpecialFolderLocation");
	CHECK_RET(SHGetPathFromIDList(pidl, path),
		  "SHGetPathFromIDList");
	CHECK_RET(desktop->GetDisplayNameOf(pidl, SHGDN_INFOLDER, &str),
		  "desktop->GetDisplayNameOf");
	StrRetToBuf(&str, pidl, display_name, MAX_PATH);
    
	CHECK_RET(SHGetFileInfo((char *)pidl, 0, &file_info, sizeof(file_info),
				SHGFI_PIDL|SHGFI_ICONLOCATION|SHGFI_SMALLICON),
		  "SHGetFileInfo");

	// per il desktop ritorniamo un pidl invalido, perche' non ci
	// serve e comunque e' un caso speciale...
	retval = Py_BuildValue("(isssisiii)", 0, path, display_name,
			       file_info.szDisplayName, file_info.iIcon,
			       file_info.szDisplayName, file_info.iIcon, 1, 0);

	pmalloc->Free(pidl);

	return retval;
}


// ritorna una lista di sottodirectory della directory individuata dal pidl
// in ingresso. (Il pidl e` passato come un intero Python)
static PyObject *get_subfolders_of(PyObject *self, PyObject *args)
{
	LPMALLOC pmalloc;
	LPITEMIDLIST item_pidl = NULL;
	IShellFolder *desktop = NULL;
	IShellFolder *folder = NULL;
	STRRET str;
	TCHAR display_name[MAX_PATH];
	TCHAR path[MAX_PATH];
	TCHAR icon_location[MAX_PATH];
	TCHAR open_icon_location[MAX_PATH];
	int icon_index;
	int open_icon_index;
	IExtractIcon *extract_icon;   
	ULONG number;
	ULONG attrs;
	LPITEMIDLIST parent;
	LPENUMIDLIST folder_enum = NULL;
	LPITEMIDLIST absolute_item_pidl;
    
	PyObject *retval = NULL;
	PyObject *list_item;   

	if (!PyArg_ParseTuple(args, "i", (long *)&parent)) {
		return NULL;
	}

	pmalloc = get_malloc();
	desktop = get_desktop_folder();

	if (parent) {
		CHECK_RET(desktop->BindToObject(parent, NULL, IID_IShellFolder,
						(LPVOID *)&folder),
			  "desktop->BindToObject");
	} else {
		// parent == 0, siamo ancora al desktop, non serve (e' anzi
		// errore) chiamare BindToObject perche' abbiamo gia'
		// l'interfaccia restituita da get_desktop_folder
		folder = desktop;
	}
    
	retval = PyList_New(0);

	HRESULT is_cp = desktop->CompareIDs(
		0, parent, get_control_panel_pidl());
	if (HRESULT_CODE(is_cp) == 0) {
		if (folder != desktop) {
			folder->Release();
		}
		return retval;
	}

// 	if (!SUCCEEDED(folder->EnumObjects(NULL, SHCONTF_FOLDERS,
// 					   &folder_enum))) {
// 		log_msg(NULL);
		
// 		return retval;
// 	}

	CHECK_RET(folder->EnumObjects(NULL, SHCONTF_FOLDERS, &folder_enum),
		  "folder->EnumObjects");

	while (1) {
		if (!SUCCEEDED(folder_enum->Next(1, &item_pidl, &number))) {
			log_msg("Fallito folder_enum->Next:");
			log_msg(NULL);
			break;
		}
		if (number != 1) {
			char buffer[255];
			snprintf(buffer, 255, "folder_enum->Next ritorna "
				 "%d risultati", number);
			log_msg(buffer);
			log_msg(NULL);
			break;
		}

		if (parent) {
			absolute_item_pidl = concat_itemids(parent, item_pidl);
		} else {
			absolute_item_pidl = item_pidl;
		}
        
		CHECK_RET(SHGetPathFromIDList(absolute_item_pidl, path),
			  "SHGetPathFromIDList");
        
// 		CHECK_RET(folder->GetUIObjectOf(NULL, 1,
// 						(LPCITEMIDLIST *)&item_pidl,
// 						IID_IExtractIcon,
// 						NULL, (LPVOID *)&extract_icon),
// 			  "folder->GetUIObjectOf");
		if (SUCCEEDED(folder->GetUIObjectOf(
				      NULL, 1,
				      (LPCITEMIDLIST *)&item_pidl,
				      IID_IExtractIcon,
				      NULL, (LPVOID *)&extract_icon))) {
			// recuperiamo le icone (normale, aperto), individuate dal
			// file in cui si trovano e dal loro indice
			CHECK_RET(extract_icon->GetIconLocation(
					  (UINT)0, (char *)icon_location,
					  (UINT)MAX_PATH, &icon_index,
					  (UINT *)&attrs),
				  "extract_icon->GetIconLocation");
			CHECK_RET(extract_icon->GetIconLocation(
					  GIL_OPENICON, open_icon_location,
					  MAX_PATH, &open_icon_index,
					  (UINT *)&attrs),
				  "extract_icon->GetIconLocation");
			extract_icon->Release();
		} else {
			log_msg("Fallito GetUIObjectOf, icon location "
				"e index custom...");
			icon_location = path;
			icon_index = 0;
			open_icon_location = path;
			open_icon_index = 1;
		}

		attrs = SFGAO_HASSUBFOLDER|SFGAO_LINK;
		CHECK_RET(folder->GetAttributesOf(
				  1, (LPCITEMIDLIST *)&item_pidl, &attrs),
			  "folder->GetAttributesOf");

		if (attrs & SFGAO_LINK) {
			// risolviamo il link...
			IShellLink *link;
			CHECK_RET(folder->GetUIObjectOf(
					  NULL, 1,
					  (LPCITEMIDLIST *)&item_pidl,
					  IID_IShellLink,
					  NULL, (LPVOID *)&link),
				  "folder->GetUIObjectOf");
			CHECK_RET(link->Resolve(NULL, SLR_NO_UI|SLR_NOSEARCH|
					  SLR_NOTRACK|SLR_NOUPDATE|
					  SLR_NOLINKINFO),
				  "link->Resolve");
			CHECK_RET(link->GetPath(path, MAX_PATH, NULL,
						SLGP_UNCPRIORITY),
				  "link->GetPath");
			link->Release();
		}

		CHECK_RET(folder->GetDisplayNameOf(item_pidl,
						   SHGDN_INFOLDER, &str),
			  "folder->GetDisplayNameOf");
		StrRetToBuf(&str, item_pidl, display_name, MAX_PATH);	  

		list_item = Py_BuildValue("(isssisiii)",
					  (long)absolute_item_pidl,
					  path,
					  display_name,
					  icon_location, icon_index,
					  open_icon_location, open_icon_index,
					  attrs & SFGAO_HASSUBFOLDER,
					  get_special_sort_index(
						  absolute_item_pidl));

		PyList_Append(retval, list_item);

		if (parent) {
			pmalloc->Free(item_pidl);
		}            
        
	}

	if (folder != desktop) {
		folder->Release();
	}
	folder_enum->Release();

	return retval;
}


// ritorna un handle all'icona per la directory corrispondente al pidl in
// ingresso. Il secondo argomento e' un booleano che indica quale icona si
// vuole: normale (0) o aperta (1). Sia pidl che hicon sono interi in python
static PyObject *get_hicon(PyObject *self, PyObject *args)
{
	int is_open = 0;
	LPITEMIDLIST pidl;
	SHFILEINFO file_info;
	PyObject *retval = NULL;

	if (!PyArg_ParseTuple(args, "ii", (long *)&pidl, &is_open)) {
		return NULL;
	}

	UINT flag = is_open ? SHGFI_OPENICON : 0;

	if (!pidl) {
		CHECK_RET(SHGetSpecialFolderLocation(
				  NULL, CSIDL_DESKTOP, &pidl),
			  "SHGetSpecialFolderLocation");
	}

	CHECK_RET(SHGetFileInfo((char *)pidl, 0, &file_info, sizeof(file_info),
				SHGFI_PIDL|SHGFI_ICON|SHGFI_SMALLICON|flag),
		  "SHGetFileInfo");

	return Py_BuildValue("i", (long)file_info.hIcon);
}


// libera la memoria per il pidl in ingresso
static PyObject *free_pidl(PyObject *self, PyObject *args)
{
	LPITEMIDLIST pidl;

	if (!PyArg_ParseTuple(args, "i", (long *)&pidl)) {
		return NULL;
	}

	if (pidl) {
		get_malloc()->Free(pidl);
	}

	return Py_BuildValue("");
}


static PyMethodDef _dirctrlhelper_methods[] = {
	{"get_root", (PyCFunction)get_root, METH_VARARGS,
	 "Gets the root (`Desktop' folder) of the filesystem"},
	{"get_subfolders_of", (PyCFunction)get_subfolders_of, METH_VARARGS,
	 "Gets the list of subfolders of the given folder"},
	{"get_hicon", (PyCFunction)get_hicon, METH_VARARGS,
	 "Gets an hicon from a filename and an index"},
	{"free_pidl", (PyCFunction)free_pidl, METH_VARARGS,
	 "Frees the memory for the input pidl"},
	{NULL, NULL, 0, NULL}
};


extern "C"
void init_dirctrlhelper(void)
{
	// create the module
	Py_InitModule("_dirctrlhelper", _dirctrlhelper_methods);
}


statichere IShellFolder *get_desktop_folder()
{
	static IShellFolder *desktop_folder = NULL;
	if (!desktop_folder) {
		//assert(SUCCEEDED(SHGetDesktopFolder(&desktop_folder)));
		if (!SUCCEEDED(SHGetDesktopFolder(&desktop_folder))) {
			log_msg("get_desktop_folder:");
			log_msg(NULL);
			abort();
		}
	}
	return desktop_folder;
}

statichere LPITEMIDLIST get_control_panel_pidl()
{
	static LPITEMIDLIST control_panel = NULL;
	if (!SUCCEEDED(SHGetSpecialFolderLocation(NULL, CSIDL_CONTROLS,
						  &control_panel))) {
		log_msg("get_control_panel_pidl:");
		log_msg(NULL);
		abort();
	}
	return control_panel;
}


statichere IMalloc *get_malloc()
{
	static IMalloc *pmalloc = NULL;
	if (!pmalloc) {
		assert(SUCCEEDED(SHGetMalloc(&pmalloc)));
	}
	return pmalloc;
}


// get size of PIDL - returns PIDL size (even if it's composite
// PIDL - i.e. composed from more than one PIDLs)
statichere long get_itemid_size(LPCITEMIDLIST pidl) 
{
	int size = 0;
	if (!pidl) return 0;
	while (pidl->mkid.cb) {
		size += pidl->mkid.cb;
		pidl = (LPCITEMIDLIST)(((LPBYTE)pidl) + pidl->mkid.cb);
	}
	return size;
}


statichere LPITEMIDLIST concat_itemids(LPCITEMIDLIST p1, LPCITEMIDLIST p2)
{
	UINT s1 = get_itemid_size(p1);
	UINT s2 = get_itemid_size(p2);
	UINT s3 = sizeof(p1->mkid.cb);

	LPITEMIDLIST ret = (LPITEMIDLIST)get_malloc()->Alloc(s1 + s2 + s3);
	if(ret == NULL) return NULL; 

	CopyMemory(((LPBYTE)ret), p1, s1); 
	CopyMemory(((LPBYTE)ret) + s1, p2, s2); 
	*((USHORT *)(((LPBYTE) ret) + s1 + s2)) = 0; 
	return ret; 
}

struct Tuple {
	LPCITEMIDLIST pidl;
	int index;
};

statichere int get_special_sort_index(LPCITEMIDLIST pidl)
{
	static Tuple sort_map[10];
	static bool inited = false;
	static int total = 0;

	if (!inited) {
		inited = true;
		Tuple t;
		LPITEMIDLIST p;
		// casi speciali, alcune directory standard che devono avere
		// un ordine particolare...
		// desktop
		if (SUCCEEDED(SHGetSpecialFolderLocation(
				      NULL, CSIDL_DESKTOP, &p))) {
			t.pidl = p;
			t.index = 0;
			sort_map[total++] = t;
		}
		// cestino
		if (SUCCEEDED(SHGetSpecialFolderLocation(
				      NULL, CSIDL_BITBUCKET, &p))) {
			t.pidl = p;
			t.index = 0;
			sort_map[total++] = t;
		}
		// documenti
		if (SUCCEEDED(SHGetSpecialFolderLocation(
				      NULL, 0x000c/*CSIDL_MYDOCUMENTS*/, &p))){
			t.pidl = p;
			t.index = -3;
			sort_map[total++] = t;
		} else {
			// proviamo in quest'altro modo...
			IShellFolder *desktop = get_desktop_folder();
			
			if (SUCCEEDED(
				    desktop->ParseDisplayName(
					    NULL, NULL, 
					    L"::{450d8fba-ad25-11d0-98a8-0800361b1103}", 
					    NULL, &p, NULL))) {
				t.pidl = p;
				t.index = -3;
				sort_map[total++] = t;
			}
		}
		// risorse del computer
		if (SUCCEEDED(SHGetSpecialFolderLocation(
				      NULL, CSIDL_DRIVES, &p))) {
			t.pidl = p;
			t.index = -2;
			sort_map[total++] = t;
		}
		// risorse di rete
		if (SUCCEEDED(SHGetSpecialFolderLocation(
				      NULL, CSIDL_NETWORK, &p))) {
			t.pidl = p;
			t.index = -1;
			sort_map[total++] = t;
		}
		// pannello di controllo
		if (SUCCEEDED(SHGetSpecialFolderLocation(
				      NULL, CSIDL_CONTROLS, &p))) {
			t.pidl = p;
			t.index = 2;
			sort_map[total++] = t;
		}
	}

	IShellFolder *desktop = get_desktop_folder();
	
	for (int i = 0; i < total; ++i) {
		HRESULT res = desktop->CompareIDs(0, pidl, sort_map[i].pidl);
		if ((short)HRESULT_CODE(res) == 0) {
			return sort_map[i].index;
		}
	}
// 	TCHAR path[MAX_PATH];
// 	if (SUCCEEDED(SHGetPathFromIDList(pidl, path))) {
// 		TCHAR drive[_MAX_DRIVE];
// 		TCHAR dir[_MAX_DIR];
// 		_splitpath(path, drive, dir, NULL, NULL);
// 		if (_tcsicmp(dir, "\\") == 0) {
// 			return 0;
// 		}
// 	} else {
// 		log_msg("SHGetPathFromIDList in get_special_sort_index:");
// 		log_msg(NULL);
// 	}
	
	return 1;
}


#include <time.h>

statichere FILE *get_log_target(void)
{
	static FILE *f = NULL;

	if (!f) {
		f = fopen("out.log", "at");
	}

	return f;
}


statichere void _log_msg(const char *msg)
{
	time_t rawtime;
	struct tm *timeinfo;

	time (&rawtime);
	timeinfo = localtime(&rawtime);

	const char *format = "DIRCTRL %s: %s\n";
	
	if (!msg) {
		LPVOID lpMsgBuf;
	
		FormatMessage( 
			FORMAT_MESSAGE_ALLOCATE_BUFFER |
			FORMAT_MESSAGE_FROM_SYSTEM,
			NULL, GetLastError(),
			MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
			(LPTSTR) &lpMsgBuf, 0, NULL 
			);
		
                // Display the string.
		//MessageBox( NULL, lpMsgBuf, "GetLastError", MB_OK|MB_ICONINFORMATION );
		fprintf(stderr, format, asctime(timeinfo), lpMsgBuf);
		fprintf(get_log_target(), format, asctime(timeinfo),
			lpMsgBuf);
                // Free the buffer.
		LocalFree( lpMsgBuf );
	} else {
		fprintf(stderr, format, asctime(timeinfo), msg);
		fprintf(get_log_target(), format, asctime(timeinfo), msg);
	}
}
