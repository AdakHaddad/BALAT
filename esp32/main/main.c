#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "balat_engine.h"
#include "balat_fixture.h"
#include "balat_log.h"
#include "balat_nmea.h"

/*
 * Hardware boundary: GPIO 6/7 drive protected external driver inputs only.
 * GNSS is UART1; USB serial commands are UART0 and cannot enable a cue.
 */
#define TAG "balat"
#define GNSS_UART UART_NUM_1
#define CONSOLE_UART UART_NUM_0
#define LINE_CAP 160u

static balat_engine_t engine;
static balat_map_t map;
static size_t replay_index;
static bool replay_running;

static const balat_engine_config_t ENGINE_CONFIG = {
    .gate = {.stale_ms = 3000u, .max_gap_ms = 5000u,
             .max_speed_cm_s = 1500u, .min_speed_cm_s = 30u,
             .base_uncertainty_cm = 0u, .max_uncertainty_cm = 500u,
             .hdop_scale_cm = 100u, .max_speed_kn100 = 2916u,
             .require_utc = false},
    .traj = {.min_speed_cm_s = 30u, .max_speed_cm_s = 1500u,
             .max_gap_ms = 5000u},
    .risk = {.caution_enter_cm = 500, .caution_exit_cm = 600,
             .danger_enter_cm = 200, .danger_exit_cm = 300,
             .confirm_samples = 2u},
    .cue = {.max_on_ms = 500u, .cooldown_ms = 30000u},
    .use_gga = true,
    .reset_reason = "boot",
};

static uint32_t now_ms(void)
{
    return (uint32_t)(esp_timer_get_time() / 1000LL);
}

static void outputs_apply(void)
{
    const balat_engine_status_t *s = &engine.status;
    bool active = s->cue_active && s->cue_enable && !s->manual_disable &&
                  s->risk_state != BALAT_RISK_INVALID;

#if CONFIG_BALAT_CUE_MODULE_BUZZER
    gpio_set_level(CONFIG_BALAT_CUE_BUZZER_GPIO, active ? 1 : 0);
    gpio_set_level(CONFIG_BALAT_CUE_MOTOR_GPIO, 0);
#else
    gpio_set_level(CONFIG_BALAT_CUE_BUZZER_GPIO, 0);
    gpio_set_level(CONFIG_BALAT_CUE_MOTOR_GPIO, active ? 1 : 0);
#endif
    gpio_set_level(CONFIG_BALAT_LED_INVALID_GPIO,
                   s->risk_state == BALAT_RISK_INVALID ? 1 : 0);
    gpio_set_level(CONFIG_BALAT_LED_CAUTION_GPIO,
                   (s->risk_state == BALAT_RISK_CAUTION ||
                    s->risk_state == BALAT_RISK_DANGER ||
                    s->risk_state == BALAT_RISK_COOLDOWN) ? 1 : 0);
#if CONFIG_BALAT_LED_SAFE_GPIO >= 0
    gpio_set_level(CONFIG_BALAT_LED_SAFE_GPIO,
                   s->risk_state == BALAT_RISK_SAFE ? 1 : 0);
#endif
}

static void log_decision(const char *event)
{
    char line[512];
    (void)balat_log_format_csv(&engine.status, event, line, sizeof(line));
    printf("%s", line);
}

static void process_nmea(const char *text)
{
    balat_nmea_sentence_t sentence;
    balat_nmea_status_t result = balat_nmea_parse(text, &sentence);
    if (result == BALAT_NMEA_OK) {
        balat_engine_on_nmea(&engine, &sentence, now_ms());
    } else if (result != BALAT_NMEA_IGNORED) {
        balat_engine_on_bad_sentence(&engine, result, now_ms());
    }
}

static void reset_engine(void)
{
    balat_engine_init(&engine, &ENGINE_CONFIG, &map);
    replay_index = 0u;
    replay_running = false;
}

static void print_help(void)
{
    puts("HELP STATUS MAP REPLAY START|STOP|RESET FIX <x_cm> <y_cm> NMEA <sentence>");
    puts("FAULT NONE|STALE|MAP|CORRUPT CLEAR RESET");
    puts("USB commands never enable cues; use the physical CUE_ENABLE switch.");
}

static void process_command(char *line)
{
    char *save = NULL;
    char *command = strtok_r(line, " \r\n", &save);
    if (command == NULL) {
        return;
    }
    if (strcmp(command, "HELP") == 0) {
        print_help();
    } else if (strcmp(command, "STATUS") == 0) {
        log_decision("STATUS");
    } else if (strcmp(command, "MAP") == 0) {
        printf("map_valid=%u,version=%lu,checksum=0x%08lX,segments=%u,source=%s\n",
               map.valid ? 1u : 0u, (unsigned long)map.manifest.map_version,
               (unsigned long)map.manifest.checksum,
               (unsigned)map.manifest.segment_count, map.manifest.source);
    } else if (strcmp(command, "REPLAY") == 0) {
        char *arg = strtok_r(NULL, " \r\n", &save);
        if (arg != NULL && strcmp(arg, "START") == 0) replay_running = true;
        else if (arg != NULL && strcmp(arg, "STOP") == 0) replay_running = false;
        else if (arg != NULL && strcmp(arg, "RESET") == 0) replay_index = 0u;
        else puts("ERR REPLAY START|STOP|RESET");
    } else if (strcmp(command, "FIX") == 0) {
        char *x = strtok_r(NULL, " \r\n", &save);
        char *y = strtok_r(NULL, " \r\n", &save);
        char *x_end = NULL;
        char *y_end = NULL;
        long x_value = x == NULL ? 0 : strtol(x, &x_end, 10);
        long y_value = y == NULL ? 0 : strtol(y, &y_end, 10);
        if (x == NULL || y == NULL || x_end == x || y_end == y ||
            *x_end != '\0' || *y_end != '\0' ||
            x_value < -BALAT_MAX_COORD_CM || x_value > BALAT_MAX_COORD_CM ||
            y_value < -BALAT_MAX_COORD_CM || y_value > BALAT_MAX_COORD_CM) {
            puts("ERR FIX expects bounded integer coordinates in cm");
        } else {
            uint32_t time = now_ms();
            balat_engine_on_synthetic_fix(&engine, (int32_t)x_value,
                                          (int32_t)y_value, time, time, 0u);
        }
    } else if (strcmp(command, "NMEA") == 0) {
        char *sentence = strtok_r(NULL, "\r\n", &save);
        if (sentence == NULL) puts("ERR NMEA <sentence>"); else process_nmea(sentence);
    } else if (strcmp(command, "FAULT") == 0) {
        char *arg = strtok_r(NULL, " \r\n", &save);
        if (arg == NULL) puts("ERR FAULT NONE|STALE|MAP|CORRUPT");
        else if (strcmp(arg, "NONE") == 0) balat_engine_clear_injected_faults(&engine);
        else if (strcmp(arg, "STALE") == 0) balat_engine_inject_fault(&engine, BALAT_FAULT_STALE);
        else if (strcmp(arg, "MAP") == 0) balat_engine_inject_fault(&engine, BALAT_FAULT_MAP);
        else if (strcmp(arg, "CORRUPT") == 0) balat_engine_inject_fault(&engine, BALAT_FAULT_CHECKSUM);
        else puts("ERR FAULT NONE|STALE|MAP|CORRUPT");
    } else if (strcmp(command, "CLEAR") == 0) {
        balat_engine_clear_injected_faults(&engine);
    } else if (strcmp(command, "RESET") == 0) {
        reset_engine();
    } else {
        puts("ERR unknown command; try HELP");
    }
}

static void service_uart(uart_port_t port, bool commands)
{
    static char gnss_line[LINE_CAP];
    static char console_line[LINE_CAP];
    static size_t gnss_used;
    static size_t console_used;
    char *line = commands ? console_line : gnss_line;
    size_t *used = commands ? &console_used : &gnss_used;
    uint8_t byte;

    while (uart_read_bytes(port, &byte, 1u, 0) == 1) {
        if (byte == '\n' || byte == '\r') {
            if (*used != 0u) {
                line[*used] = '\0';
                if (commands) process_command(line); else process_nmea(line);
                *used = 0u;
            }
        } else if (*used + 1u < LINE_CAP) {
            line[(*used)++] = (char)byte;
        } else {
            *used = 0u;
            balat_engine_on_bad_sentence(&engine, BALAT_NMEA_MALFORMED, now_ms());
        }
    }
}

void app_main(void)
{
    uint64_t output_mask = (1ULL << CONFIG_BALAT_CUE_BUZZER_GPIO) |
                           (1ULL << CONFIG_BALAT_CUE_MOTOR_GPIO) |
                           (1ULL << CONFIG_BALAT_LED_INVALID_GPIO) |
                           (1ULL << CONFIG_BALAT_LED_CAUTION_GPIO);
    gpio_config_t out;
#if CONFIG_BALAT_LED_SAFE_GPIO >= 0
    output_mask |= 1ULL << CONFIG_BALAT_LED_SAFE_GPIO;
#endif
    out = (gpio_config_t){.pin_bit_mask = output_mask,
                         .mode = GPIO_MODE_OUTPUT, .pull_up_en = GPIO_PULLUP_DISABLE,
                         .pull_down_en = GPIO_PULLDOWN_DISABLE, .intr_type = GPIO_INTR_DISABLE};
    gpio_config_t in = {.pin_bit_mask = (1ULL << CONFIG_BALAT_MANUAL_DISABLE_GPIO) |
                                        (1ULL << CONFIG_BALAT_CUE_ENABLE_GPIO),
                        .mode = GPIO_MODE_INPUT, .pull_up_en = GPIO_PULLUP_ENABLE,
                        .pull_down_en = GPIO_PULLDOWN_DISABLE, .intr_type = GPIO_INTR_DISABLE};
    uart_config_t uart_cfg = {.baud_rate = 9600, .data_bits = UART_DATA_8_BITS,
                              .parity = UART_PARITY_DISABLE, .stop_bits = UART_STOP_BITS_1,
                              .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
                              .source_clk = UART_SCLK_DEFAULT};

    gpio_config(&out);
    gpio_config(&in);
    gpio_set_pull_mode(CONFIG_BALAT_CUE_ENABLE_GPIO, GPIO_PULLDOWN_ONLY);
    gpio_set_level(CONFIG_BALAT_CUE_BUZZER_GPIO, 0);
    gpio_set_level(CONFIG_BALAT_CUE_MOTOR_GPIO, 0);
    gpio_set_level(CONFIG_BALAT_LED_INVALID_GPIO, 1);
    gpio_set_level(CONFIG_BALAT_LED_CAUTION_GPIO, 0);
#if CONFIG_BALAT_LED_SAFE_GPIO >= 0
    gpio_set_level(CONFIG_BALAT_LED_SAFE_GPIO, 0);
#endif
    uart_driver_install(GNSS_UART, 1024, 0, 0, NULL, 0);
    uart_param_config(GNSS_UART, &uart_cfg);
    uart_set_pin(GNSS_UART, CONFIG_BALAT_GNSS_TX_GPIO, CONFIG_BALAT_GNSS_RX_GPIO,
                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    uart_driver_install(CONSOLE_UART, 1024, 0, 0, NULL, 0);

    if (!balat_map_load(&map, &balat_fixture_manifest, balat_fixture_segments)) {
        ESP_LOGE(TAG, "fixture map validation failed; cue remains inhibited");
    }
    reset_engine();
    print_help();
    while (true) {
        uint32_t time = now_ms();
        bool manual_disable = gpio_get_level(CONFIG_BALAT_MANUAL_DISABLE_GPIO) == 0;
        bool cue_enable = gpio_get_level(CONFIG_BALAT_CUE_ENABLE_GPIO) != 0;
        service_uart(GNSS_UART, false);
        service_uart(CONSOLE_UART, true);
        if (replay_running && replay_index < balat_fixture_replay_count) {
            balat_replay_point_t p = balat_fixture_replay[replay_index++];
            balat_engine_on_synthetic_fix(&engine, p.x_cm, p.y_cm,
                                           (uint64_t)time, time, 0u);
        } else if (replay_index >= balat_fixture_replay_count) {
            replay_running = false;
        }
        balat_engine_tick(&engine, time, cue_enable, manual_disable);
        outputs_apply();
        if (engine.decision_pending) {
            log_decision(engine.event_pending ? engine.event : "DECISION");
            balat_engine_clear_decision(&engine);
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
