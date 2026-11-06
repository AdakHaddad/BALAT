#ifndef BALAT_GEOMETRY_H
#define BALAT_GEOMETRY_H

#include "balat_map.h"

typedef struct {
    bool valid;
    balat_fault_t fault;
    uint16_t segment_id;
    int64_t dist2_cm2;
    int32_t closest_x_cm;
    int32_t closest_y_cm;
    bool inside_span;
} balat_geom_t;

balat_geom_t balat_nearest_segment(const balat_map_t *map,
                                   int32_t x_cm,
                                   int32_t y_cm);

#endif
