# Constraints

Add the official Basys 3 XDC constraints required by the selected board revision.
Verify every pin against the Digilent master XDC and board schematic. Do not guess pin mappings.
Constrain the 100 MHz board clock and all external I/O timing as appropriate.

- `basys3_demo.xdc` — pins for the synthetic-trace demo, taken from Digilent's
  `Basys-3-Master.xdc` (rev B). JA1 is a logic-level cue observation output.
