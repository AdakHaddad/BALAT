CC ?= gcc
WARN = -std=c11 -Wall -Wextra -Werror -pedantic -O2
INC = -I../components/balat_core/include -I../components/balat_core/generated
CORE = $(wildcard ../components/balat_core/src/*.c) \
       ../components/balat_core/generated/balat_map_fixture.c \
       ../components/balat_core/generated/balat_replay_fixture.c

.PHONY: all clean
all: test_balat_core

test_balat_core: test_balat_core.c $(CORE)
	$(CC) $(WARN) $(INC) -o $@ test_balat_core.c $(CORE)

clean:
	rm -f test_balat_core
