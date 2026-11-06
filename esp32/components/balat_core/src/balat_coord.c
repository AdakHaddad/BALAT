#include "balat_coord.h"

static int64_t arithmetic_shift_right(int64_t value, unsigned shift)
{
    if (value >= 0) {
        return value >> shift;
    }
    return -(((-value) + ((int64_t)1 << shift) - 1) >> shift);
}

void balat_coord_init(balat_coord_t *coord,
                      int32_t origin_lat_deg7,
                      int32_t origin_lon_deg7,
                      int16_t cos_lat_q14)
{
    if (coord == NULL) {
        return;
    }
    coord->origin_lat_deg7 = origin_lat_deg7;
    coord->origin_lon_deg7 = origin_lon_deg7;
    coord->cos_lat_q14 = cos_lat_q14;
}

bool balat_coord_convert(const balat_coord_t *coord,
                         int32_t lat_deg7,
                         int32_t lon_deg7,
                         int32_t *x_cm,
                         int32_t *y_cm)
{
    int64_t dlat;
    int64_t dlon;
    int64_t y;
    int64_t x_mid;
    int64_t x;

    if (coord == NULL || x_cm == NULL || y_cm == NULL) {
        return false;
    }
    if (coord->cos_lat_q14 <= 0) {
        return false;
    }

    dlat = (int64_t)lat_deg7 - (int64_t)coord->origin_lat_deg7;
    dlon = (int64_t)lon_deg7 - (int64_t)coord->origin_lon_deg7;

    y = arithmetic_shift_right(dlat * 72872, 16);
    x_mid = arithmetic_shift_right(dlon * 72872, 16);
    x = arithmetic_shift_right(x_mid * (int64_t)coord->cos_lat_q14, 14);

    if (x < -BALAT_MAX_COORD_CM || x > BALAT_MAX_COORD_CM ||
        y < -BALAT_MAX_COORD_CM || y > BALAT_MAX_COORD_CM) {
        return false;
    }

    *x_cm = (int32_t)x;
    *y_cm = (int32_t)y;
    return true;
}
