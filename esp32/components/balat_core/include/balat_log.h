#ifndef BALAT_LOG_H
#define BALAT_LOG_H

#include "balat_engine.h"

/*
 * Interface: format one self-contained CSV decision record.  The caller owns
 * the output buffer; no storage or transport is performed by the core.
 */
size_t balat_log_format_csv(const balat_engine_status_t *status,
                            const char *event,
                            char *buffer,
                            size_t buffer_len);

#endif
