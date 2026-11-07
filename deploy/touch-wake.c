#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

static long long milliseconds(void) {
    struct timespec value;
    clock_gettime(CLOCK_MONOTONIC, &value);
    return (long long)value.tv_sec * 1000 + value.tv_nsec / 1000000;
}

static int open_touch_device(void) {
    DIR *directory = opendir("/dev/input");
    struct dirent *entry;
    if (!directory) return -1;
    while ((entry = readdir(directory)) != NULL) {
        char path[256], name[256] = {0};
        int fd;
        if (strncmp(entry->d_name, "event", 5) != 0) continue;
        snprintf(path, sizeof(path), "/dev/input/%s", entry->d_name);
        fd = open(path, O_RDONLY);
        if (fd < 0) continue;
        if (ioctl(fd, EVIOCGNAME(sizeof(name)), name) >= 0 && strstr(name, "CST0836")) {
            closedir(directory);
            return fd;
        }
        close(fd);
    }
    closedir(directory);
    return -1;
}

int main(void) {
    int fd = open_touch_device();
    struct input_event event;
    long long first_tap = 0;
    if (fd < 0) {
        fprintf(stderr, "r1-touch-wake: touch device not found: %s\n", strerror(errno));
        return 2;
    }
    while (read(fd, &event, sizeof(event)) == sizeof(event)) {
        if (event.type == EV_KEY && event.code == BTN_TOUCH && event.value == 1) {
            long long now = milliseconds();
            if (first_tap && now - first_tap >= 90 && now - first_tap <= 700) {
                close(fd);
                return 0;
            }
            first_tap = now;
        }
    }
    close(fd);
    return 3;
}
