#ifndef BALAT_MAP_H
#define BALAT_MAP_H

#include "balat_types.h"

typedef struct {
    uint16_t seg_id;
    int32_t ax_cm;
    int32_t ay_cm;
    int32_t bx_cm;
    int32_t by_cm;
    int16_t ux_q14;
    int16_t uy_q14;
    uint8_t road_class;
    uint16_t buffer_cm;
} balat_map_segment_t;

typedef struct {
    uint32_t map_version;
    uint32_t checksum;
    uint16_t segment_count;
    int32_t origin_lat_deg7;
    int32_t origin_lon_deg7;
    int16_t cos_lat_q14;
    int32_t min_x_cm;
    int32_t max_x_cm;
    int32_t min_y_cm;
    int32_t max_y_cm;
    const char *source;
    const char *license;
    const char *extraction_utc;
    const char *crs;
    const char *coordinate_unit;
} balat_map_manifest_t;

typedef struct {
    balat_map_manifest_t manifest;
    const balat_map_segment_t *segments;
    size_t count;
    bool valid;
    balat_fault_t fault;
} balat_map_t;

uint32_t balat_map_checksum(const balat_map_segment_t *segments,
                            size_t count,
                            int32_t origin_lat_deg7,
                            int32_t origin_lon_deg7,
                            int16_t cos_lat_q14);

bool balat_map_load(balat_map_t *map,
                    const balat_map_manifest_t *manifest,
                    const balat_map_segment_t *segments);

const balat_map_segment_t *balat_map_find_segment(const balat_map_t *map,
                                                  uint16_t seg_id);

#endif
