#ifndef BALAT_FIXTURE_H
#define BALAT_FIXTURE_H

#include <stddef.h>
#include <stdint.h>
#include "balat_map.h"

extern const balat_map_manifest_t balat_fixture_manifest;
extern const balat_map_segment_t balat_fixture_segments[];
extern const size_t balat_fixture_segment_count;
typedef struct { int32_t x_cm; int32_t y_cm; } balat_replay_point_t;
extern const balat_replay_point_t balat_fixture_replay[];
extern const size_t balat_fixture_replay_count;
#endif
