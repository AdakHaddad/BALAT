#include "balat_nmea.h"

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

static int hex_nibble(char c)
{
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'A' && c <= 'F') {
        return c - 'A' + 10;
    }
    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    return -1;
}

static bool is_digit(char c)
{
    return c >= '0' && c <= '9';
}

static size_t split_fields(char *s, char **fields, size_t max_fields)
{
    size_t count = 0;

    if (s == NULL || fields == NULL || max_fields == 0u) {
        return 0u;
    }

    fields[count++] = s;
    for (char *p = s; *p != '\0'; ++p) {
        if (*p == ',') {
            *p = '\0';
            if (count < max_fields) {
                fields[count++] = p + 1;
            }
        }
    }
    return count;
}

static bool parse_fixed_digits(const char *s, size_t digits, uint32_t *out)
{
    uint32_t value = 0;

    if (s == NULL || out == NULL || strlen(s) != digits) {
        return false;
    }
    for (size_t i = 0; i < digits; ++i) {
        if (!is_digit(s[i])) {
            return false;
        }
        value = value * 10u + (uint32_t)(s[i] - '0');
    }
    *out = value;
    return true;
}

static bool is_leap_year(int year)
{
    return (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
}

static int days_in_month(int year, int month)
{
    static const int DAYS[] = {
        31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31
    };

    if (month < 1 || month > 12) {
        return 0;
    }
    if (month == 2 && is_leap_year(year)) {
        return 29;
    }
    return DAYS[month - 1];
}

static int64_t days_from_civil(int year, unsigned month, unsigned day)
{
    int y = year;
    unsigned m = month;
    const int64_t era = (y >= 0 ? y : y - 399) / 400;
    const unsigned yoe = (unsigned)(y - era * 400);
    const unsigned mp = (m > 2u) ? (m - 3u) : (m + 9u);
    const unsigned doy = (153u * mp + 2u) / 5u + day - 1u;
    const unsigned doe = yoe * 365u + yoe / 4u - yoe / 100u + doy;

    return era * 146097 + (int64_t)doe - 719468;
}

static bool parse_time_ms(const char *s, uint64_t *out_ms)
{
    uint32_t hour = 0;
    uint32_t minute = 0;
    uint32_t second = 0;
    uint32_t milli = 0;
    size_t digits = 0;
    size_t i = 0;

    if (s == NULL || out_ms == NULL || s[0] == '\0') {
        return false;
    }

    while (is_digit(s[i])) {
        if (digits >= 6u) {
            return false;
        }
        if (digits < 2u) {
            hour = hour * 10u + (uint32_t)(s[i] - '0');
        } else if (digits < 4u) {
            minute = minute * 10u + (uint32_t)(s[i] - '0');
        } else {
            second = second * 10u + (uint32_t)(s[i] - '0');
        }
        ++digits;
        ++i;
    }
    if (digits != 6u) {
        return false;
    }

    if (s[i] == '.') {
        size_t frac_digits = 0;
        ++i;
        while (is_digit(s[i]) && frac_digits < 3u) {
            milli = milli * 10u + (uint32_t)(s[i] - '0');
            ++frac_digits;
            ++i;
        }
        while (frac_digits < 3u) {
            milli *= 10u;
            ++frac_digits;
        }
        while (is_digit(s[i])) {
            ++i;
        }
    }
    if (s[i] != '\0') {
        return false;
    }
    if (hour >= 24u || minute >= 60u || second > 60u) {
        return false;
    }

    *out_ms = ((uint64_t)hour * 3600u + (uint64_t)minute * 60u + second)
                  * 1000u
              + milli;
    return true;
}

static bool parse_date_days(const char *s, int64_t *out_days)
{
    uint32_t day;
    uint32_t month;
    uint32_t year2;
    int year;

    if (s == NULL || out_days == NULL || s[0] == '\0') {
        return false;
    }
    if (strlen(s) != 6u) {
        return false;
    }
    for (size_t i = 0; i < 6u; ++i) {
        if (!is_digit(s[i])) {
            return false;
        }
    }
    day = (uint32_t)(s[0] - '0') * 10u + (uint32_t)(s[1] - '0');
    month = (uint32_t)(s[2] - '0') * 10u + (uint32_t)(s[3] - '0');
    year2 = (uint32_t)(s[4] - '0') * 10u + (uint32_t)(s[5] - '0');

    year = 2000 + (int)year2;
    if (month < 1u || month > 12u || day < 1u ||
        day > (uint32_t)days_in_month(year, (int)month)) {
        return false;
    }

    *out_days = days_from_civil(year, month, day);
    return true;
}

static balat_nmea_status_t parse_coord_field(const char *field,
                                             int deg_digits,
                                             int32_t max_deg,
                                             int32_t *out_deg7)
{
    const char *dot;
    size_t int_len;
    size_t frac_len = 0;
    uint32_t deg = 0;
    uint32_t min_int = 0;
    uint32_t min_frac = 0;
    uint32_t min_frac_padded;
    uint32_t min_combined;
    uint32_t min_x50;
    uint32_t min_deg7;
    uint32_t deg7;

    if (field == NULL || out_deg7 == NULL || field[0] == '\0') {
        return BALAT_NMEA_MALFORMED;
    }

    dot = strchr(field, '.');
    int_len = (dot == NULL) ? strlen(field) : (size_t)(dot - field);
    if (int_len != (size_t)deg_digits + 2u) {
        return BALAT_NMEA_MALFORMED;
    }

    for (size_t i = 0; i < int_len; ++i) {
        if (!is_digit(field[i])) {
            return BALAT_NMEA_MALFORMED;
        }
    }
    for (size_t i = 0; i < (size_t)deg_digits; ++i) {
        deg = deg * 10u + (uint32_t)(field[i] - '0');
    }
    for (size_t i = (size_t)deg_digits; i < int_len; ++i) {
        min_int = min_int * 10u + (uint32_t)(field[i] - '0');
    }

    if (dot != NULL) {
        for (size_t i = 1; is_digit(dot[i]) && frac_len < 4u; ++i) {
            min_frac = min_frac * 10u + (uint32_t)(dot[i] - '0');
            ++frac_len;
        }
        while (frac_len < 4u) {
            min_frac *= 10u;
            ++frac_len;
        }
    }

    if (deg > (uint32_t)max_deg || min_int >= 60u) {
        return BALAT_NMEA_OUT_OF_RANGE;
    }
    if (deg == (uint32_t)max_deg && (min_int != 0u || min_frac != 0u)) {
        return BALAT_NMEA_OUT_OF_RANGE;
    }

    min_frac_padded = min_frac;
    min_combined = min_int * 10000u + min_frac_padded;
    min_x50 = min_combined * 50u;
    min_deg7 = (min_x50 + 1u) / 3u;
    deg7 = deg * 10000000u + min_deg7;

    if (deg7 > 1800000000u) {
        return BALAT_NMEA_OUT_OF_RANGE;
    }
    *out_deg7 = (int32_t)deg7;
    return BALAT_NMEA_OK;
}

static bool parse_decimal_centi(const char *s, uint16_t *out)
{
    uint32_t whole = 0;
    uint32_t frac = 0;
    size_t frac_digits = 0;
    size_t i = 0;
    bool saw_digit = false;

    if (s == NULL || out == NULL) {
        return false;
    }
    if (s[0] == '\0') {
        *out = 0;
        return true;
    }
    while (is_digit(s[i])) {
        saw_digit = true;
        if (whole > 655u) {
            return false;
        }
        whole = whole * 10u + (uint32_t)(s[i] - '0');
        ++i;
    }
    if (s[i] == '.') {
        ++i;
        while (is_digit(s[i]) && frac_digits < 2u) {
            saw_digit = true;
            frac = frac * 10u + (uint32_t)(s[i] - '0');
            ++frac_digits;
            ++i;
        }
        while (is_digit(s[i])) {
            ++i;
        }
    }
    if (!saw_digit || s[i] != '\0') {
        return false;
    }
    if (frac_digits == 0u) {
        frac = 0u;
    } else if (frac_digits == 1u) {
        frac *= 10u;
    }

    if (whole > 655u) {
        return false;
    }
    *out = (uint16_t)(whole * 100u + frac);
    return true;
}

static bool is_supported_talker(const char *talker, const char *type)
{
    size_t len;

    if (talker == NULL || type == NULL) {
        return false;
    }
    len = strlen(talker);
    if (len != 5u || talker[0] != 'G') {
        return false;
    }
    if (talker[1] != 'P' && talker[1] != 'N') {
        return false;
    }
    return strcmp(talker + 2, type) == 0;
}

static balat_nmea_status_t parse_rmc(char **fields,
                                     size_t count,
                                     balat_nmea_sentence_t *out)
{
    int64_t date_days = 0;
    uint64_t time_ms = 0;
    bool have_date;
    bool have_time;
    balat_nmea_status_t status;

    if (count < 10u) {
        return BALAT_NMEA_MALFORMED;
    }

    out->kind = BALAT_NMEA_RMC;

    if (strcmp(fields[2], "A") == 0) {
        out->fix_valid = true;
    } else if (strcmp(fields[2], "V") == 0) {
        out->fix_valid = false;
    } else {
        return BALAT_NMEA_MALFORMED;
    }

    if (count > 12u && fields[12][0] != '\0' && strcmp(fields[12], "N") == 0) {
        out->fix_valid = false;
    }

    if (out->fix_valid) {
        status = parse_coord_field(fields[3], 2, 90, &out->lat_deg7);
        if (status != BALAT_NMEA_OK) {
            return status;
        }
        if (strcmp(fields[4], "N") == 0) {
            /* positive */
        } else if (strcmp(fields[4], "S") == 0) {
            out->lat_deg7 = -out->lat_deg7;
        } else {
            return BALAT_NMEA_MALFORMED;
        }

        status = parse_coord_field(fields[5], 3, 180, &out->lon_deg7);
        if (status != BALAT_NMEA_OK) {
            return status;
        }
        if (strcmp(fields[6], "E") == 0) {
            /* positive */
        } else if (strcmp(fields[6], "W") == 0) {
            out->lon_deg7 = -out->lon_deg7;
        } else {
            return BALAT_NMEA_MALFORMED;
        }

        if (!parse_decimal_centi(fields[7], &out->speed_kn100)) {
            return BALAT_NMEA_MALFORMED;
        }
    }

    have_time = parse_time_ms(fields[1], &time_ms);
    have_date = parse_date_days(fields[9], &date_days);

    if (have_time && have_date) {
        out->utc_ms = (uint64_t)date_days * 86400000u + time_ms;
        out->utc_valid = true;
    } else if (fields[1][0] == '\0' && fields[9][0] == '\0') {
        out->utc_valid = false;
    } else {
        return BALAT_NMEA_MALFORMED;
    }

    out->quality = out->fix_valid ? 1u : 0u;
    return BALAT_NMEA_OK;
}

static balat_nmea_status_t parse_gga(char **fields,
                                     size_t count,
                                     balat_nmea_sentence_t *out)
{
    uint32_t quality;

    if (count < 9u) {
        return BALAT_NMEA_MALFORMED;
    }

    out->kind = BALAT_NMEA_GGA;
    if (fields[6][0] == '\0' ||
        !parse_fixed_digits(fields[6], strlen(fields[6]), &quality) ||
        quality > 8u) {
        return BALAT_NMEA_MALFORMED;
    }
    out->quality = (uint8_t)quality;
    out->fix_valid = (quality != 0u);
    if (!parse_decimal_centi(fields[8], &out->hdop_centi)) {
        return BALAT_NMEA_MALFORMED;
    }

    if (fields[1][0] != '\0') {
        uint64_t time_ms;
        if (parse_time_ms(fields[1], &time_ms)) {
            /* GGA only carries time of day; it is not used for epoch time. */
            out->utc_valid = false;
        } else {
            return BALAT_NMEA_MALFORMED;
        }
    }

    return BALAT_NMEA_OK;
}

uint8_t balat_nmea_checksum(const char *body, size_t len)
{
    uint8_t checksum = 0u;

    if (body == NULL) {
        return 0u;
    }
    for (size_t i = 0; i < len; ++i) {
        checksum ^= (uint8_t)body[i];
    }
    return checksum;
}

balat_nmea_status_t balat_nmea_parse(const char *sentence,
                                     balat_nmea_sentence_t *out)
{
    const char *star;
    size_t len;
    size_t body_len;
    int high;
    int low;
    uint8_t expected;
    uint8_t actual;
    char body[BALAT_NMEA_MAX_LEN];
    char *fields[24];
    size_t field_count;
    size_t copy_len;

    if (sentence == NULL || out == NULL) {
        return BALAT_NMEA_MALFORMED;
    }

    memset(out, 0, sizeof(*out));

    len = strlen(sentence);
    while (len > 0u &&
           (sentence[len - 1u] == '\r' || sentence[len - 1u] == '\n' ||
            sentence[len - 1u] == ' ' || sentence[len - 1u] == '\t')) {
        --len;
    }
    if (len < 7u || sentence[0] != '$') {
        return BALAT_NMEA_MALFORMED;
    }

    copy_len = len < (sizeof(out->raw) - 1u) ? len : (sizeof(out->raw) - 1u);
    memcpy(out->raw, sentence, copy_len);
    out->raw[copy_len] = '\0';

    star = memchr(sentence, '*', len);
    if (star == NULL || star == sentence) {
        return BALAT_NMEA_MALFORMED;
    }
    body_len = (size_t)(star - sentence) - 1u;
    if (body_len == 0u || body_len >= sizeof(body)) {
        return BALAT_NMEA_MALFORMED;
    }
    if ((size_t)(star - sentence) + 2u >= len) {
        return BALAT_NMEA_MALFORMED;
    }

    high = hex_nibble(star[1]);
    low = hex_nibble(star[2]);
    if (high < 0 || low < 0) {
        return BALAT_NMEA_MALFORMED;
    }
    expected = (uint8_t)((high << 4) | low);
    actual = balat_nmea_checksum(sentence + 1, body_len);
    if (actual != expected) {
        return BALAT_NMEA_BAD_CHECKSUM;
    }

    memcpy(body, sentence + 1, body_len);
    body[body_len] = '\0';
    field_count = split_fields(body, fields, sizeof(fields) / sizeof(fields[0]));
    if (field_count == 0u) {
        return BALAT_NMEA_MALFORMED;
    }

    if (strcmp(fields[0] + (strlen(fields[0]) > 3u ? strlen(fields[0]) - 3u : 0u),
               "RMC") == 0) {
        if (!is_supported_talker(fields[0], "RMC")) {
            return BALAT_NMEA_IGNORED;
        }
        return parse_rmc(fields, field_count, out);
    }
    if (strcmp(fields[0] + (strlen(fields[0]) > 3u ? strlen(fields[0]) - 3u : 0u),
               "GGA") == 0) {
        if (!is_supported_talker(fields[0], "GGA")) {
            return BALAT_NMEA_IGNORED;
        }
        return parse_gga(fields, field_count, out);
    }

    return BALAT_NMEA_IGNORED;
}
