#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int main(int argc, char **argv) {
    const char *target;
    char **child_argv;
    int index;
    int argument_offset = 1;
    uid_t original_uid = getuid();
    gid_t original_gid = getgid();
    int prepare_config = 0;
    int prepare_control = 0;

    if (argc < 2) {
        fprintf(stderr, "usage: r1-root-launch PROGRAM [ARG ...]\n");
        return 64;
    }

    if (argc > 2 && strcmp(argv[1], "--prepare-config") == 0) {
        prepare_config = 1;
        argument_offset = 2;
    } else if (argc > 2 && strcmp(argv[1], "--prepare-control") == 0) {
        prepare_control = 1;
        argument_offset = 2;
    } else if (argc > 2 && strcmp(argv[1], "--prepare-data") == 0) {
        prepare_config = 1;
        prepare_control = 1;
        argument_offset = 2;
    }
    if (argument_offset >= argc) {
        fprintf(stderr, "r1-root-launch: missing program\n");
        return 64;
    }

    if (setgid(0) != 0 || setuid(0) != 0) {
        fprintf(stderr, "r1-root-launch: cannot elevate: %s\n", strerror(errno));
        return 77;
    }
    if (prepare_config) {
        if (chown("/config", original_uid, original_gid) != 0 || chmod("/config", 0770) != 0) {
            fprintf(stderr, "r1-root-launch: cannot prepare /config: %s\n", strerror(errno));
            return 73;
        }
    }
    if (prepare_control) {
        if (chown("/control", original_uid, original_gid) != 0 || chmod("/control", 0770) != 0) {
            fprintf(stderr, "r1-root-launch: cannot prepare /control: %s\n", strerror(errno));
            return 73;
        }
    }
    if (prepare_config || prepare_control) {
        if (setgid(original_gid) != 0 || setuid(original_uid) != 0) {
            fprintf(stderr, "r1-root-launch: cannot drop privileges: %s\n", strerror(errno));
            return 77;
        }
    }

    target = argv[argument_offset];
    child_argv = calloc((size_t) (argc - argument_offset + 1), sizeof(char *));
    if (!child_argv) {
        return 70;
    }
    for (index = argument_offset; index < argc; index++) {
        child_argv[index - argument_offset] = argv[index];
    }
    child_argv[argc - argument_offset] = NULL;

    execvp(target, child_argv);
    fprintf(stderr, "r1-root-launch: exec %s failed: %s\n", target, strerror(errno));
    return 127;
}
