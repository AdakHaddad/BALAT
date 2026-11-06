#ifndef BALAT_COORD_H
#define BALAT_COORD_H

#include "balat_types.h"

typedef struct {
    int32_t origin_lat_deg7;
    int32_t origin_lon_deg7;
    int16_t cos_lat_q14;
} balat_coord_t;

void balat_coord_init(balat_coord_t *coord,
                      int32_t origin_lat_deg7,
                      int32_t origin_lon_deg7,
                      int16_t cos_lat_q14);

bool balat_coord_convert(const balat_coord_t *coord,
                         int32_t lat_deg7,
                         int32_t lon_deg7,
                         int32_t *x_cm,
                         int32_t *y_cm);

#endif
