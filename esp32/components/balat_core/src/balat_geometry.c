#include "balat_geometry.h"

static int64_t arithmetic_shift_right(int64_t value, unsigned shift)
{
    if (value >= 0) {
        return value >> shift;
    }
    return -(((-value) + ((int64_t)1 << shift) - 1) >> shift);
}

static void evaluate_segment(const balat_map_segment_t *segment,
                             int32_t x_cm,
                             int32_t y_cm,
                             int64_t *dist2_out,
                             int32_t *closest_x_out,
                             int32_t *closest_y_out,
                             bool *inside_out)
{
    int64_t relx = (int64_t)x_cm - segment->ax_cm;
    int64_t rely = (int64_t)y_cm - segment->ay_cm;
    int64_t bax = (int64_t)segment->bx_cm - segment->ax_cm;
    int64_t bay = (int64_t)segment->by_cm - segment->ay_cm;
    int64_t along = relx * segment->ux_q14 + rely * segment->uy_q14;
    int64_t b_along = bax * segment->ux_q14 + bay * segment->uy_q14;
    int64_t perp = relx * segment->uy_q14 - rely * segment->ux_q14;
    int64_t dx;
    int64_t dy;
    bool inside = false;
    int32_t closest_x;
    int32_t closest_y;

    if (along <= 0) {
        dx = relx;
        dy = rely;
        closest_x = segment->ax_cm;
        closest_y = segment->ay_cm;
    } else if (along >= b_along) {
        dx = (int64_t)x_cm - segment->bx_cm;
        dy = (int64_t)y_cm - segment->by_cm;
        closest_x = segment->bx_cm;
        closest_y = segment->by_cm;
    } else {
        int64_t t_q16 = (along << 16) / b_along;
        dx = arithmetic_shift_right(perp, 14);
        dy = 0;
        closest_x = segment->ax_cm +
                    (int32_t)arithmetic_shift_right(bax * t_q16, 16);
        closest_y = segment->ay_cm +
                    (int32_t)arithmetic_shift_right(bay * t_q16, 16);
        inside = true;
    }

    *dist2_out = dx * dx + dy * dy;
    *closest_x_out = closest_x;
    *closest_y_out = closest_y;
    *inside_out = inside;
}

balat_geom_t balat_nearest_segment(const balat_map_t *map,
                                   int32_t x_cm,
                                   int32_t y_cm)
{
    balat_geom_t result;
    int64_t best_dist2 = INT64_MAX;

    result.valid = false;
    result.fault = BALAT_FAULT_MAP;
    result.segment_id = 0u;
    result.dist2_cm2 = 0;
    result.closest_x_cm = 0;
    result.closest_y_cm = 0;
    result.inside_span = false;

    if (map == NULL || !map->valid || map->segments == NULL) {
        return result;
    }

    for (size_t i = 0; i < map->count; ++i) {
        int64_t dist2;
        int32_t closest_x;
        int32_t closest_y;
        bool inside;

        evaluate_segment(&map->segments[i], x_cm, y_cm, &dist2, &closest_x,
                         &closest_y, &inside);
        if (dist2 < best_dist2) {
            best_dist2 = dist2;
            result.segment_id = map->segments[i].seg_id;
            result.dist2_cm2 = dist2;
            result.closest_x_cm = closest_x;
            result.closest_y_cm = closest_y;
            result.inside_span = inside;
        }
    }

    result.valid = true;
    result.fault = BALAT_FAULT_NONE;
    return result;
}
