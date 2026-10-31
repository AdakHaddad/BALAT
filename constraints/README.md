# Constraints

Add the official Basys 3 XDC constraints required by the selected board revision.
Verify every pin against the Digilent master XDC and board schematic. Do not guess pin mappings.
Constrain the 100 MHz board clock and all external I/O timing as appropriate.

- `basys3_demo.xdc` — pins for the synthetic-trace demo, taken from Digilent's
  `Basys-3-Master.xdc` (rev B). JA1 is a logic-level cue observation output.
- `basys3_herdsync.xdc` — the same board pins plus the on-board USB-UART:
  `RsRx=B18` input and `RsTx=A18` output, both taken from Digilent's master XDC.
  The asynchronous RX input is a false path; it is synchronized in `uart_rx.v`.
