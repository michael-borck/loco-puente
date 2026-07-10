// Interpose dlsym so we can wrap cublasLt* symbols that ts_server resolves at runtime.
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>
#include <stdint.h>

typedef int (*heur_t)(void*, void*, void*, void*, void*, void*, void*, int, void*, int*);
static heur_t real_heur = NULL;

typedef int (*create_t)(void**);
static create_t real_create = NULL;

static int wrap_create(void **handle) {
    int rc = real_create(handle);
    fprintf(stderr, "[HOOK] cublasLtCreate -> rc=%d handle=%p\n", rc, handle ? *handle : NULL);
    fflush(stderr);
    return rc;
}

static int wrap_heur(void *light, void *opDesc, void *A, void *B, void *C, void *D,
                     void *pref, int reqCount, void *results, int *retCount) {
    fprintf(stderr,
        "[HOOK] cublasLtMatmulAlgoGetHeuristic(\n"
        "         lightHandle    = %p\n"
        "         operationDesc  = %p\n"
        "         Adesc          = %p\n"
        "         Bdesc          = %p\n"
        "         Cdesc          = %p\n"
        "         Ddesc          = %p\n"
        "         preference     = %p\n"
        "         requestedAlgoCount = %d\n"
        "         heuristicResultsArray = %p\n"
        "         returnAlgoCount       = %p)\n",
        light, opDesc, A, B, C, D, pref, reqCount, results, (void*)retCount);
    fflush(stderr);

    int rc = real_heur(light, opDesc, A, B, C, D, pref, reqCount, results, retCount);

    fprintf(stderr, "[HOOK]   -> returned rc=%d, returnAlgoCount=%d\n",
            rc, retCount ? *retCount : -999);
    fflush(stderr);
    return rc;
}

void *dlsym(void *handle, const char *symbol) {
    static void *(*real_dlsym)(void*, const char*) = NULL;
    if (!real_dlsym) {
        // __libc_dlsym avoids infinite recursion
        real_dlsym = dlvsym(RTLD_NEXT, "dlsym", "GLIBC_2.2.5");
    }
    void *addr = real_dlsym(handle, symbol);
    if (symbol && addr) {
        if (!strcmp(symbol, "cublasLtMatmulAlgoGetHeuristic")) {
            fprintf(stderr, "[HOOK] intercepted dlsym(%s)\n", symbol); fflush(stderr);
            real_heur = (heur_t)addr;
            return (void*)wrap_heur;
        }
        if (!strcmp(symbol, "cublasLtCreate")) {
            fprintf(stderr, "[HOOK] intercepted dlsym(%s)\n", symbol); fflush(stderr);
            real_create = (create_t)addr;
            return (void*)wrap_create;
        }
        if (!strncmp(symbol, "cublasLt", 8)) {
            fprintf(stderr, "[HOOK] (passthrough) dlsym(%s)\n", symbol); fflush(stderr);
        }
    }
    return addr;
}
