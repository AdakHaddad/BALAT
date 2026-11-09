#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#include "balat_engine.h"
#include "balat_fixture.h"
#include "balat_log.h"
#include "balat_nmea.h"

/* PCB v1 net mapping: GPIO3 buzzer, GPIO4 motor, GPIO5 GPS power,
 * GPIO6 report button (repurposed as hold-to-enable), GPIO10 LED, GPIO20 GPS TX.
 * USB Serial/JTAG is the console; UART1 is reserved for the GPS receiver.
 */
#define TAG "balat"
#define GNSS_UART UART_NUM_1
#define LINE_CAP 160u
#define COMMAND_QUEUE_DEPTH 4u

static balat_engine_t engine;
static balat_map_t map;
static size_t replay_index;
static bool replay_running;
static bool mock_mode;
static QueueHandle_t command_queue;
static uint16_t ble_status_handle;
static uint16_t ble_connection = BLE_HS_CONN_HANDLE_NONE;
static uint8_t ble_own_addr_type;
static const ble_uuid128_t balat_service_uuid = BLE_UUID128_INIT(0xa1,0x96,0x8b,0x2f,0x52,0x7c,0x3a,0x8e,0x0d,0x4f,0x15,0x1b,0x01,0x00,0x51,0x7f);
static const ble_uuid128_t balat_control_uuid = BLE_UUID128_INIT(0xa1,0x96,0x8b,0x2f,0x52,0x7c,0x3a,0x8e,0x0d,0x4f,0x15,0x1b,0x02,0x00,0x51,0x7f);
static const ble_uuid128_t balat_status_uuid = BLE_UUID128_INIT(0xa1,0x96,0x8b,0x2f,0x52,0x7c,0x3a,0x8e,0x0d,0x4f,0x15,0x1b,0x03,0x00,0x51,0x7f);

static int ble_access(uint16_t conn, uint16_t attr, struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn; (void)arg;
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
        uint8_t bytes[9]; uint16_t len = 0;
        uint16_t packet_len = OS_MBUF_PKTLEN(ctxt->om);
        if (packet_len > sizeof(bytes) || ble_hs_mbuf_to_flat(ctxt->om, bytes, sizeof(bytes), &len) != 0 || len != packet_len) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
        char command[LINE_CAP] = {0};
        if (len == 9u && bytes[0] == 0x10u) {
            int32_t x = (int32_t)((uint32_t)bytes[1] | ((uint32_t)bytes[2] << 8) | ((uint32_t)bytes[3] << 16) | ((uint32_t)bytes[4] << 24));
            int32_t y = (int32_t)((uint32_t)bytes[5] | ((uint32_t)bytes[6] << 8) | ((uint32_t)bytes[7] << 16) | ((uint32_t)bytes[8] << 24));
            if (x < -BALAT_MAX_COORD_CM || x > BALAT_MAX_COORD_CM || y < -BALAT_MAX_COORD_CM || y > BALAT_MAX_COORD_CM) return BLE_ATT_ERR_UNLIKELY;
            (void)snprintf(command, sizeof(command), "BLEFIX %ld %ld", (long)x, (long)y);
        } else if (len == 2u && bytes[0] == 0x20u) {
            const char *action = bytes[1] == 1u ? "START" : bytes[1] == 2u ? "PAUSE" : bytes[1] == 3u ? "RESET" : bytes[1] == 4u ? "STOP" : NULL;
            if (action == NULL) return BLE_ATT_ERR_UNLIKELY;
            (void)snprintf(command, sizeof(command), "DEMO %s", action);
        } else {
            return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
        }
        return xQueueSend(command_queue, command, 0) == pdTRUE ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
    }
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR && attr == ble_status_handle) {
        const balat_engine_status_t *s = &engine.status; uint8_t body[19] = {1};
        uint32_t x=(uint32_t)s->x_cm, y=(uint32_t)s->y_cm;
        uint32_t distance=(uint32_t)(sqrt((double)s->dist2_cm2)); uint32_t seq=s->fix_seq;
        for (int i=0;i<4;i++) { body[1+i]=(uint8_t)(x>>(8*i)); body[5+i]=(uint8_t)(y>>(8*i)); body[9+i]=(uint8_t)(distance>>(8*i)); body[13+i]=(uint8_t)(seq>>(8*i)); }
        body[17]=(uint8_t)s->risk_state; body[18]=(uint8_t)((s->fix_valid?1u:0u)|(s->map_valid?2u:0u)|(s->cue_active?4u:0u));
        return os_mbuf_append(ctxt->om, body, sizeof(body)) == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
    }
    return BLE_ATT_ERR_UNLIKELY;
}

static const struct ble_gatt_svc_def balat_services[] = {{.type=BLE_GATT_SVC_TYPE_PRIMARY,.uuid=&balat_service_uuid.u,.characteristics=(struct ble_gatt_chr_def[]){{.uuid=&balat_control_uuid.u,.access_cb=ble_access,.flags=BLE_GATT_CHR_F_WRITE},{.uuid=&balat_status_uuid.u,.access_cb=ble_access,.flags=BLE_GATT_CHR_F_READ|BLE_GATT_CHR_F_NOTIFY,.val_handle=&ble_status_handle},{0}}},{0}};

static void ble_advertise(void);
static int ble_gap_event(struct ble_gap_event *event, void *arg)
{
    (void)arg;
    if (event->type == BLE_GAP_EVENT_CONNECT && event->connect.status == 0) ble_connection = event->connect.conn_handle;
    else if (event->type == BLE_GAP_EVENT_DISCONNECT) { ble_connection = BLE_HS_CONN_HANDLE_NONE; ble_advertise(); }
    return 0;
}

static void ble_advertise(void)
{
    struct ble_hs_adv_fields fields = {0}; struct ble_gap_adv_params params = {0};
    int rc;
    const char *name = "BALAT-C3"; fields.name=(uint8_t *)name; fields.name_len=strlen(name); fields.name_is_complete=1; fields.flags=BLE_HS_ADV_F_DISC_GEN|BLE_HS_ADV_F_BREDR_UNSUP;
    rc = ble_gap_adv_set_fields(&fields);
    if (rc != 0) {
        ESP_LOGE(TAG, "BLE advertisement data setup failed: %d", rc);
        return;
    }
    params.conn_mode=BLE_GAP_CONN_MODE_UND; params.disc_mode=BLE_GAP_DISC_MODE_GEN;
    rc = ble_gap_adv_start(ble_own_addr_type,NULL,BLE_HS_FOREVER,&params,ble_gap_event,NULL);
    if (rc != 0) ESP_LOGE(TAG, "BLE advertising start failed: %d", rc);
}

static void ble_sync(void)
{
    int rc = ble_hs_id_infer_auto(0, &ble_own_addr_type);
    if (rc != 0) {
        ESP_LOGE(TAG, "BLE address type inference failed: %d", rc);
        return;
    }
    ble_advertise();
}
static void ble_host(void *arg) { (void)arg; nimble_port_run(); nimble_port_freertos_deinit(); }

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

    gpio_set_level(CONFIG_BALAT_BUZZER_GPIO, active ? 1 : 0);
    gpio_set_level(CONFIG_BALAT_MOTOR_GPIO, active ? 1 : 0);

    /* The PCB has one active-high indicator LED. Invalid blinks at 2 Hz;
     * caution/danger/cooldown is steady on; safe is off. */
    bool led_on = s->risk_state == BALAT_RISK_CAUTION ||
                  s->risk_state == BALAT_RISK_DANGER ||
                  s->risk_state == BALAT_RISK_COOLDOWN;
    if (s->risk_state == BALAT_RISK_INVALID) {
        led_on = ((now_ms() / 250u) & 1u) != 0u;
    }
    gpio_set_level(CONFIG_BALAT_STATUS_LED_GPIO, led_on ? 1 : 0);
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

static void set_gps_power(bool enabled)
{
    /* Q3 is a high-side PNP switch: low turns the GPS module on. */
    gpio_set_level(CONFIG_BALAT_GPS_ENABLE_GPIO, enabled ? 0 : 1);
}

static void print_help(void)
{
    puts("HELP STATUS MAP REPLAY START|STOP|RESET FIX <x_cm> <y_cm>");
    puts("BLE demo replay: DEMO START|PAUSE|RESET|STOP (201 synthetic fixes)");
    puts("NMEA <sentence> is accepted only in mock mode.");
    puts("MOCK START|PAUSE|RESET|STOP; FAULT NONE|STALE|MAP|CORRUPT CLEAR RESET");
    puts("PCB map: BUZ=GPIO3 MOT=GPIO4 GPS_EN=GPIO5 BTN=GPIO6 LED=GPIO10 GPS_RX=GPIO20");
    puts("USB mock data cannot arm cues; hold the PCB button to enable bounded outputs.");
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
    } else if (strcmp(command, "DEMO") == 0) {
        char *arg = strtok_r(NULL, " \r\n", &save);
        if (arg != NULL && strcmp(arg, "START") == 0) {
            if (!mock_mode || replay_index == 0u || replay_index >= balat_fixture_replay_count) reset_engine();
            mock_mode = true;
            set_gps_power(false);
            replay_running = true;
            puts("OK DEMO START; 201 synthetic fixes");
        } else if (arg != NULL && strcmp(arg, "PAUSE") == 0) {
            replay_running = false;
            puts("OK DEMO PAUSE");
        } else if (arg != NULL && strcmp(arg, "RESET") == 0) {
            reset_engine();
            mock_mode = true;
            set_gps_power(false);
            puts("OK DEMO RESET");
        } else if (arg != NULL && strcmp(arg, "STOP") == 0) {
            replay_running = false;
            mock_mode = false;
            reset_engine();
            set_gps_power(true);
            puts("OK DEMO STOP; GPS input selected");
        } else {
            puts("ERR DEMO START|PAUSE|RESET|STOP");
        }
    } else if (strcmp(command, "FIX") == 0 || strcmp(command, "BLEFIX") == 0) {
        if (strcmp(command, "BLEFIX") == 0) { mock_mode = true; set_gps_power(false); }
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
        if (sentence == NULL) puts("ERR NMEA <sentence>");
        else if (!mock_mode) puts("ERR NMEA requires MOCK START");
        else process_nmea(sentence);
    } else if (strcmp(command, "MOCK") == 0) {
        char *arg = strtok_r(NULL, " \r\n", &save);
        if (arg == NULL) puts("ERR MOCK START|PAUSE|RESET|STOP");
        else if (strcmp(arg, "START") == 0) {
            if (!mock_mode) reset_engine();
            mock_mode = true;
            set_gps_power(false);
            puts("OK MOCK START");
        } else if (strcmp(arg, "PAUSE") == 0) {
            if (mock_mode) { reset_engine(); puts("OK MOCK PAUSE; outputs inhibited"); }
            else puts("ERR mock mode is not active");
        } else if (strcmp(arg, "RESET") == 0) {
            if (!mock_mode) puts("ERR mock mode is not active");
            else { reset_engine(); puts("OK MOCK RESET"); }
        } else if (strcmp(arg, "STOP") == 0) {
            mock_mode = false;
            reset_engine();
            set_gps_power(true);
            puts("OK MOCK STOP; GPS input selected");
        } else puts("ERR MOCK START|PAUSE|RESET|STOP");
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

static void service_gnss_uart(void)
{
    static char gnss_line[LINE_CAP];
    static size_t gnss_used;
    uint8_t byte;

    while (uart_read_bytes(GNSS_UART, &byte, 1u, 0) == 1) {
        if (byte == '\n' || byte == '\r') {
            if (gnss_used != 0u) {
                gnss_line[gnss_used] = '\0';
                if (!mock_mode) process_nmea(gnss_line);
                gnss_used = 0u;
            }
        } else if (gnss_used + 1u < LINE_CAP) {
            gnss_line[gnss_used++] = (char)byte;
        } else {
            gnss_used = 0u;
            if (!mock_mode) {
                balat_engine_on_bad_sentence(&engine, BALAT_NMEA_MALFORMED, now_ms());
            }
        }
    }
}

static void usb_console_task(void *arg)
{
    (void)arg;
    char line[LINE_CAP];
    size_t used = 0u;
    while (true) {
        int ch = fgetc(stdin);
        if (ch == EOF) {
            vTaskDelay(pdMS_TO_TICKS(10));
            continue;
        }
        if (ch == '\n' || ch == '\r') {
            if (used != 0u) {
                line[used] = '\0';
                if (xQueueSend(command_queue, line, 0) != pdTRUE) {
                    puts("ERR command queue full");
                }
                used = 0u;
            }
        } else if (used + 1u < sizeof(line)) {
            line[used++] = (char)ch;
        } else {
            used = 0u;
            puts("ERR command too long");
        }
    }
}

void app_main(void)
{
    uint64_t output_mask = (1ULL << CONFIG_BALAT_BUZZER_GPIO) |
                           (1ULL << CONFIG_BALAT_MOTOR_GPIO) |
                           (1ULL << CONFIG_BALAT_GPS_ENABLE_GPIO) |
                           (1ULL << CONFIG_BALAT_STATUS_LED_GPIO);
    gpio_config_t out;
    out = (gpio_config_t){.pin_bit_mask = output_mask,
                         .mode = GPIO_MODE_OUTPUT, .pull_up_en = GPIO_PULLUP_DISABLE,
                         .pull_down_en = GPIO_PULLDOWN_DISABLE, .intr_type = GPIO_INTR_DISABLE};
    gpio_config_t in = {.pin_bit_mask = (1ULL << CONFIG_BALAT_CUE_ENABLE_GPIO),
                        .mode = GPIO_MODE_INPUT, .pull_up_en = GPIO_PULLUP_ENABLE,
                        .pull_down_en = GPIO_PULLDOWN_DISABLE, .intr_type = GPIO_INTR_DISABLE};
    uart_config_t uart_cfg = {.baud_rate = 9600, .data_bits = UART_DATA_8_BITS,
                              .parity = UART_PARITY_DISABLE, .stop_bits = UART_STOP_BITS_1,
                              .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
                              .source_clk = UART_SCLK_DEFAULT};

    gpio_set_level(CONFIG_BALAT_BUZZER_GPIO, 0);
    gpio_set_level(CONFIG_BALAT_MOTOR_GPIO, 0);
    gpio_set_level(CONFIG_BALAT_STATUS_LED_GPIO, 1);
    gpio_set_level(CONFIG_BALAT_GPS_ENABLE_GPIO, 1);
    gpio_config(&out);
    gpio_config(&in);
    set_gps_power(true);
    uart_driver_install(GNSS_UART, 1024, 0, 0, NULL, 0);
    uart_param_config(GNSS_UART, &uart_cfg);
    uart_set_pin(GNSS_UART,
                 CONFIG_BALAT_GNSS_TX_GPIO < 0 ? UART_PIN_NO_CHANGE : CONFIG_BALAT_GNSS_TX_GPIO,
                 CONFIG_BALAT_GNSS_RX_GPIO,
                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    command_queue = xQueueCreate(COMMAND_QUEUE_DEPTH, LINE_CAP);
    if (command_queue == NULL) {
        ESP_LOGE(TAG, "command queue allocation failed; outputs remain disabled");
        return;
    }

    if (!balat_map_load(&map, &balat_fixture_manifest, balat_fixture_segments)) {
        ESP_LOGE(TAG, "fixture map validation failed; cue remains inhibited");
    }
    reset_engine();
    esp_err_t nvs_rc = nvs_flash_init();
    if (nvs_rc == ESP_ERR_NVS_NO_FREE_PAGES || nvs_rc == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        (void)nvs_flash_erase();
        nvs_rc = nvs_flash_init();
    }
    if (nvs_rc == ESP_OK && nimble_port_init() == ESP_OK) {
        ble_svc_gap_init(); ble_svc_gatt_init();
        (void)ble_svc_gap_device_name_set("BALAT-C3");
        if (ble_gatts_count_cfg(balat_services) == 0 && ble_gatts_add_svcs(balat_services) == 0) {
            ble_hs_cfg.sync_cb = ble_sync;
            nimble_port_freertos_init(ble_host);
        } else ESP_LOGE(TAG, "BLE GATT service registration failed");
    } else ESP_LOGE(TAG, "BLE initialization failed; USB bench mode remains available");
    print_help();
    xTaskCreate(usb_console_task, "balat_usb_console", 3072, NULL, 5, NULL);
    while (true) {
        uint32_t time = now_ms();
        bool manual_disable = false;
        bool cue_enable = gpio_get_level(CONFIG_BALAT_CUE_ENABLE_GPIO) == 0;
        service_gnss_uart();
        char command[LINE_CAP];
        while (xQueueReceive(command_queue, command, 0) == pdTRUE) {
            process_command(command);
        }
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
            if (ble_connection != BLE_HS_CONN_HANDLE_NONE && ble_status_handle != 0u) (void)ble_gatts_chr_updated(ble_status_handle);
            balat_engine_clear_decision(&engine);
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
