/* The HLE runtime on Windows, linked as bb-probe links it (no game, no Vulkan device):
 * - thread handles (ScePthread) fit 40 bits: the game packs them into 40-bit fields, and a
 *   handle above that never matches its own lock (lamp travel hung at loading);
 * - a debug exception raised by the guest stops the process without exit handlers or static
 *   destructors, which would run under the game's still running threads;
 * - guest threads above the game's priorities (FMOD's mixer and output, 256-265) run at
 *   THREAD_PRIORITY_HIGHEST, the rest at normal priority (BB_THREAD_PRIORITY=0: all normal);
 * - the in-game restart's new launch keeps the standard handles and nothing else of this process.
 * A failed check exits at once (no abort(): its report could wait for a click).
 * After configuring the GPU build: ninja -C out/gpu runtime-windows-test && out/gpu/runtime-windows-test.exe */
#include "runtime.h"
#include "restart_launch.h"
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <windows.h>

/* The settings menu of the GPU library restarts through probe.c, which tests do not link. */
void runtime_restart(void) { abort(); }
uint32_t runtime_thread_tcb_offset(void);

#define CHECK(condition)                                                              \
    do {                                                                              \
        if (!(condition)) {                                                           \
            printf("%s:%d: check failed: %s\n", __FILE__, __LINE__, #condition);      \
            fflush(stdout);                                                           \
            _exit(1);                                                                 \
        }                                                                             \
    } while (0)

typedef void *(ABI *ThreadSelf)(void);
typedef void (ABI *Raise)(uint32_t, uint64_t);
typedef void *(ABI *GuestEntry)(void *);
typedef int32_t (ABI *AttrInit)(void **);
typedef int32_t (ABI *AttrSetParam)(void **, const int *);
typedef int32_t (ABI *ThreadCreate)(void **, void **, GuestEntry, void *, const char *);
typedef int32_t (ABI *ThreadJoin)(void *, void **);
#define GET(type, name) ((type)runtime_resolve(name, 0))

static void *worker(void *unused) {
    (void)unused;
    return GET(ThreadSelf, "aI+OeCz8xrQ#p#J")();
}
static void atexit_ran(void) { puts("atexit handler ran"); }

static void *ABI report_priority(void *unused) {
    (void)unused;
    return (void *)(intptr_t)GetThreadPriority(GetCurrentThread());
}
/* The host priority a guest thread created with this guest priority runs at. */
static int guest_thread_priority(int prio) {
    void *attr = NULL, *thread = NULL, *result = NULL;
    CHECK(GET(AttrInit, "nsYoNRywwNg#p#J")(&attr) == 0);
    CHECK(GET(AttrSetParam, "DzES9hQF4f4#p#J")(&attr, &prio) == 0);
    CHECK(GET(ThreadCreate, "6UgtwV+0zb4#p#J")(&thread, &attr, report_priority, NULL, "prio") == 0);
    CHECK(GET(ThreadJoin, "onNY9Byn-W8#p#J")(thread, &result) == 0);
    return (int)(intptr_t)result;
}

/* The new launch's side: says it runs through the output handle, then stays until it is ended. */
static int restart_child(void) {
    DWORD written=0;
    if (!WriteFile(GetStdHandle(STD_OUTPUT_HANDLE),"child output",12,&written,NULL) || written!=12) return 4;
    Sleep(60000);
    return 5;
}

static void test_restart_keeps_only_the_standard_handles(const char *self) {
    /* The write end stands for the shadNet socket: inheritable like a plain ::socket(). Once this
     * process closes it, the pipe is broken unless the new launch holds a copy, as the session
     * stayed open on the server. */
    SECURITY_ATTRIBUTES inheritable={.nLength=sizeof(inheritable),.bInheritHandle=TRUE};
    HANDLE session_end,session,reader,writer;
    CHECK(CreatePipe(&session_end,&session,&inheritable,0));
    CHECK(CreatePipe(&reader,&writer,&inheritable,0));
    HANDLE saved=GetStdHandle(STD_OUTPUT_HANDLE);
    CHECK(SetStdHandle(STD_OUTPUT_HANDLE,writer));
    char line[MAX_PATH+32];
    snprintf(line,sizeof(line),"\"%s\" --restart-child",self);
    PROCESS_INFORMATION process;
    const BOOL started=restart_launch_start(line,&process);
    SetStdHandle(STD_OUTPUT_HANDLE,saved);
    CHECK(started);
    CloseHandle(writer);
    CloseHandle(session);
    char text[64]={0};
    DWORD got=0;
    CHECK(ReadFile(reader,text,sizeof(text)-1,&got,NULL));
    printf("restart child output: \"%s\"\n",text);
    CHECK(strstr(text,"child output"));
    const BOOL open=PeekNamedPipe(session_end,NULL,0,NULL,NULL,NULL);
    const DWORD error=GetLastError();
    TerminateProcess(process.hProcess,0);
    WaitForSingleObject(process.hProcess,10000);
    CloseHandle(process.hProcess);
    CloseHandle(process.hThread);
    CloseHandle(reader);
    CloseHandle(session_end);
    printf("session after the restart: %s (%lu)\n",open?"still open in the new launch":"closed",error);
    CHECK(!open && error==ERROR_BROKEN_PIPE);
    puts("restart launch keeps only the standard handles: ok");
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc > 1 && !strcmp(argv[1], "--restart-child")) return restart_child();
    runtime_memory_reserve();
    runtime_thread_tcb_offset();
    runtime_start(1);
    if (argc > 1 && !strcmp(argv[1], "--raise-exception")) {
        atexit(atexit_ran);
        GET(Raise, "OMDRKKAZ8I4#p#J")(1, 2);
        return 99;
    }
    test_restart_keeps_only_the_standard_handles(argv[0]);
    void *self = GET(ThreadSelf, "aI+OeCz8xrQ#p#J")();
    CHECK(self);
    printf("main thread handle %p\n", self);
    CHECK(!((uintptr_t)self >> 40));
    for (int i = 0; i < 64; ++i) {
        pthread_t thread;
        void *handle = NULL;
        CHECK(pthread_create(&thread, NULL, worker, NULL) == 0);
        CHECK(pthread_join(thread, &handle) == 0);
        CHECK(handle && handle != self);
        CHECK(!((uintptr_t)handle >> 40));
    }
    /* The records so far left the start of low memory to the game's image (0x800000000, where
     * the guest code hooks expect it). */
    void *image = runtime_low_map(65536, PROT_READ | PROT_WRITE);
    printf("image placed at %p\n", image);
    CHECK((uintptr_t)image == UINT64_C(0x800000000));
    runtime_image_start = (uintptr_t)image;
    /* After it: records from low memory. */
    for (int i = 0; i < 64; ++i) {
        pthread_t thread;
        void *handle = NULL;
        CHECK(pthread_create(&thread, NULL, worker, NULL) == 0);
        CHECK(pthread_join(thread, &handle) == 0);
        CHECK((uintptr_t)handle > (uintptr_t)image && (uintptr_t)handle < UINT64_C(0x1000000000));
    }
    puts("thread handles fit 40 bits: ok");
    /* Audio threads above normal priority (Supermedo 08df6af): on 4-6 core CPUs the draw
     * workers and game threads delayed FMOD's output thread (crackling). */
    CHECK(guest_thread_priority(256) == THREAD_PRIORITY_HIGHEST);
    CHECK(guest_thread_priority(265) == THREAD_PRIORITY_HIGHEST);
    CHECK(guest_thread_priority(700) == THREAD_PRIORITY_NORMAL);
    CHECK(guest_thread_priority(767) == THREAD_PRIORITY_NORMAL);
    CHECK(runtime_thread_host_priority(256, NULL) == THREAD_PRIORITY_HIGHEST);
    CHECK(runtime_thread_host_priority(399, "1") == THREAD_PRIORITY_HIGHEST);
    CHECK(runtime_thread_host_priority(400, NULL) == THREAD_PRIORITY_NORMAL);
    CHECK(runtime_thread_host_priority(256, "0") == THREAD_PRIORITY_NORMAL);
    puts("audio threads above normal priority: ok");
    /* The exit path in a child: rc 23, no exit handlers. */
    char command[1024];
    snprintf(command, sizeof(command), "\"\"%s\" --raise-exception > runtime-windows-raise.log 2>&1\"", argv[0]);
    const int rc = system(command);
    FILE *log = fopen("runtime-windows-raise.log", "rb");
    CHECK(log);
    char text[4096] = {0};
    const size_t n = fread(text, 1, sizeof(text) - 1, log);
    fclose(log);
    remove("runtime-windows-raise.log");
    text[n] = 0;
    printf("raise exception: rc=%d\n", rc);
    CHECK(rc == 23);
    CHECK(strstr(text, "guest raised debug exception"));
    CHECK(!strstr(text, "atexit handler ran"));
    puts("raised exception skips exit handlers: ok");
    puts("PASS: runtime on Windows");
    fflush(stdout);
    /* The runtime's threads and handlers stay as they are: no exit handlers here either. */
    _exit(0);
}
