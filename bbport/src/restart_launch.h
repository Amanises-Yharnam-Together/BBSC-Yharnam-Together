/* Starts the launch that replaces this process (the in-game restart). Only the three standard
 * handles go along: a launcher reading the game's log keeps reading the new launch, and the new
 * launch (run.py, alive for the whole next game) does not keep this process's sockets. A copy of
 * the shadNet socket there kept the old session open, and the server refused the new game's login
 * as already logged in. From Supermedo's bloodborne_pc 44ca939 (nick24051998). */
#ifndef BB_RESTART_LAUNCH_H
#define BB_RESTART_LAUNCH_H
#include <windows.h>

static inline BOOL restart_launch_start(char *line, PROCESS_INFORMATION *process) {
    STARTUPINFOEXA startup={.StartupInfo={.cb=sizeof(startup),.dwFlags=STARTF_USESTDHANDLES,
                            .hStdInput=GetStdHandle(STD_INPUT_HANDLE),.hStdOutput=GetStdHandle(STD_OUTPUT_HANDLE),
                            .hStdError=GetStdHandle(STD_ERROR_HANDLE)}};
    HANDLE standard[3]={startup.StartupInfo.hStdInput,startup.StartupInfo.hStdOutput,startup.StartupInfo.hStdError};
    HANDLE inherit[3];
    DWORD count=0;
    for (int i=0;i<3;i++) {
        HANDLE handle=standard[i];
        if (!handle || handle==INVALID_HANDLE_VALUE) continue;
        int seen=0;
        for (DWORD j=0;j<count;j++) seen|=inherit[j]==handle;
        if (!seen && SetHandleInformation(handle,HANDLE_FLAG_INHERIT,HANDLE_FLAG_INHERIT)) inherit[count++]=handle;
    }
    SIZE_T size=0;
    InitializeProcThreadAttributeList(NULL,1,0,&size);
    LPPROC_THREAD_ATTRIBUTE_LIST attributes=count?(LPPROC_THREAD_ATTRIBUTE_LIST)HeapAlloc(GetProcessHeap(),0,size):NULL;
    if (attributes && (!InitializeProcThreadAttributeList(attributes,1,0,&size) ||
                       !UpdateProcThreadAttribute(attributes,0,PROC_THREAD_ATTRIBUTE_HANDLE_LIST,inherit,
                                                  count*sizeof(HANDLE),NULL,NULL))) {
        HeapFree(GetProcessHeap(),0,attributes);
        attributes=NULL;
    }
    startup.lpAttributeList=attributes;
    /* Without the list (no output handles, or the list failed) nothing is inherited at all: the
     * launch still starts, only without the old log pipe. */
    return CreateProcessA(NULL,line,NULL,NULL,attributes!=NULL,attributes?EXTENDED_STARTUPINFO_PRESENT:0,
                          NULL,NULL,&startup.StartupInfo,process);
}
#endif
