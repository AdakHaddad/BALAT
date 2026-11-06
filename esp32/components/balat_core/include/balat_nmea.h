#ifndef BALAT_NMEA_H
#define BALAT_NMEA_H

#include "balat_types.h"

typedef enum {
    BALAT_NMEA_RMC = 0,
    BALAT_NMEA_GGA = 1
} balat_nmea_kind_t;

typedef enum {
    BALAT_NMEA_OK = 0,
    BALAT_NMEA_IGNORED,
    BALAT_NMEA_BAD_CHECKSUM,
    BALAT_NMEA_MALFORMED,
    BALAT_NMEA_OUT_OF_RANGE
} balat_nmea_status_t;

typedef struct {
    balat_nmea_kind_t kind;
    bool fix_valid;
    uint8_t quality;
    uint16_t hdop_centi;
    int32_t lat_deg7;
    int32_t lon_deg7;
    uint16_t speed_kn100;
    uint64_t utc_ms;
    bool utc_valid;
    char raw[BALAT_NMEA_MAX_LEN];
} balat_nmea_sentence_t;

balat_nmea_status_t balat_nmea_parse(const char *sentence,
                                     balat_nmea_sentence_t *out);

uint8_t balat_nmea_checksum(const char *body, size_t len);

#endif
