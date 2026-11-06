#include "balat_map.h"

#include <string.h>

#define FNV_OFFSET_BASIS 2166136261u
#define FNV_PRIME 16777619u
#define Q14_ONE_SQUARED 268435456LL
#define Q14_TOLERANCE (Q14_ONE_SQUARED / 20LL)
#define MAX_ROAD_BUFFER_CM 5000u

static uint32_t fnv_u8(uint32_t hash, uint8_t value)
{
    return (hash ^ value) * FNV_PRIME;
}

static uint32_t fnv_u16(uint32_t hash, uint16_t value)
{
    hash = fnv_u8(hash, (uint8_t)(value & 0xFFu));
    hash = fnv_u8(hash, (uint8_t)((value >> 8) & 0xFFu));
    return hash;
}

static uint32_t fnv_i16(uint32_t hash, int16_t value)
{
    return fnv_u16(hash, (uint16_t)value);
}

static uint32_t fnv_u32(uint32_t hash, uint32_t value)
{
    for (unsigned i = 0; i < 4u; ++i) {
        hash = fnv_u8(hash, (uint8_t)((value >> (8u * i)) & 0xFFu));
    }
    return hash;
}

static uint32_t fnv_i32(uint32_t hash, int32_t value)
{
    return fnv_u32(hash, (uint32_t)value);
}

uint32_t balat_map_checksum(const balat_map_segment_t *segments,
                            size_t count,
                            int32_t origin_lat_deg7,
                            int32_t origin_lon_deg7,
                            int16_t cos_lat_q14)
{
    uint32_t hash = FNV_OFFSET_BASIS;

    hash = fnv_u32(hash, (uint32_t)count);
    hash = fnv_i32(hash, origin_lat_deg7);
    hash = fnv_i32(hash, origin_lon_deg7);
    hash = fnv_i16(hash, cos_lat_q14);

    if (segments != NULL) {
        for (size_t i = 0; i < count; ++i) {
            hash = fnv_u16(hash, segments[i].seg_id);
            hash = fnv_i32(hash, segments[i].ax_cm);
            hash = fnv_i32(hash, segments[i].ay_cm);
            hash = fnv_i32(hash, segments[i].bx_cm);
            hash = fnv_i32(hash, segments[i].by_cm);
            hash = fnv_i16(hash, segments[i].ux_q14);
            hash = fnv_i16(hash, segments[i].uy_q14);
            hash = fnv_u8(hash, segments[i].road_class);
            hash = fnv_u16(hash, segments[i].buffer_cm);
        }
    }
    return hash;
}

static bool segment_in_range(const balat_map_segment_t *segment)
{
    if (segment->ax_cm < -BALAT_MAX_COORD_CM ||
        segment->ax_cm > BALAT_MAX_COORD_CM ||
        segment->ay_cm < -BALAT_MAX_COORD_CM ||
        segment->ay_cm > BALAT_MAX_COORD_CM ||
        segment->bx_cm < -BALAT_MAX_COORD_CM ||
        segment->bx_cm > BALAT_MAX_COORD_CM ||
        segment->by_cm < -BALAT_MAX_COORD_CM ||
        segment->by_cm > BALAT_MAX_COORD_CM) {
        return false;
    }
    return true;
}

static bool segment_direction_valid(const balat_map_segment_t *segment)
{
    int64_t bax = (int64_t)segment->bx_cm - segment->ax_cm;
    int64_t bay = (int64_t)segment->by_cm - segment->ay_cm;
    int64_t length2 = bax * bax + bay * bay;
    int64_t direction2 = (int64_t)segment->ux_q14 * segment->ux_q14 +
                         (int64_t)segment->uy_q14 * segment->uy_q14;

    if (length2 == 0) {
        return segment->ux_q14 == 0 && segment->uy_q14 == 0;
    }
    if (direction2 < Q14_ONE_SQUARED - Q14_TOLERANCE ||
        direction2 > Q14_ONE_SQUARED + Q14_TOLERANCE) {
        return false;
    }
    if (bax * segment->ux_q14 + bay * segment->uy_q14 <= 0) {
        return false;
    }
    return true;
}

bool balat_map_load(balat_map_t *map,
                    const balat_map_manifest_t *manifest,
                    const balat_map_segment_t *segments)
{
    uint32_t checksum;
    size_t count;

    if (map == NULL) {
        return false;
    }

    memset(map, 0, sizeof(*map));
    map->fault = BALAT_FAULT_MAP;

    if (manifest == NULL || segments == NULL) {
        return false;
    }

    count = manifest->segment_count;
    if (count == 0u || count > BALAT_MAX_SEGMENTS) {
        return false;
    }
    if (manifest->map_version != BALAT_MAP_VERSION) {
        return false;
    }
    if (manifest->origin_lat_deg7 < -900000000 ||
        manifest->origin_lat_deg7 > 900000000 ||
        manifest->origin_lon_deg7 < -1800000000 ||
        manifest->origin_lon_deg7 > 1800000000 ||
        manifest->cos_lat_q14 <= 0) {
        return false;
    }

    checksum = balat_map_checksum(segments, count, manifest->origin_lat_deg7,
                                  manifest->origin_lon_deg7,
                                  manifest->cos_lat_q14);
    if (checksum != manifest->checksum) {
        return false;
    }

    for (size_t i = 0; i < count; ++i) {
        if (!segment_in_range(&segments[i]) ||
            segments[i].buffer_cm > MAX_ROAD_BUFFER_CM ||
            !segment_direction_valid(&segments[i])) {
            return false;
        }
        for (size_t j = 0; j < i; ++j) {
            if (segments[j].seg_id == segments[i].seg_id) {
                return false;
            }
        }
    }

    map->manifest = *manifest;
    map->segments = segments;
    map->count = count;
    map->valid = true;
    map->fault = BALAT_FAULT_NONE;
    return true;
}

const balat_map_segment_t *balat_map_find_segment(const balat_map_t *map,
                                                  uint16_t seg_id)
{
    if (map == NULL || !map->valid || map->segments == NULL) {
        return NULL;
    }
    for (size_t i = 0; i < map->count; ++i) {
        if (map->segments[i].seg_id == seg_id) {
            return &map->segments[i];
        }
    }
    return NULL;
}
