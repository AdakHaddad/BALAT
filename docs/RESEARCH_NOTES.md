# Research Notes and Questions

## Main research hypothesis
A wearable using locally stored road geometry and GNSS can estimate road-approach risk early enough to request a trained, non-aversive cue. A standalone FPGA implementation can demonstrate the bounded spatial decision pipeline.

This is a hypothesis, not an established result.

## Workstream A — Map and GNSS
Questions:
- How complete are OSM road geometries around the intended farm?
- What is the positional accuracy of the selected GNSS receiver under actual collar placement?
- How should road width, road edge, and uncertainty be represented?
- What is the best local projected coordinate system?
- How frequently should map data be refreshed?
- How are private roads manually added and verified?

## Workstream B — Spatial prediction
Questions:
- Is point-to-segment distance sufficient, or is polygon/buffer geometry needed?
- How many road segments can be evaluated per update within FPGA resource limits?
- What prediction horizon is useful at observed cattle walking speeds?
- How can low-speed heading noise and GNSS jumps be rejected?
- What conservative risk policy minimizes false negatives without excessive cues?

## Workstream C — Cue-response science
Questions:
- Which non-aversive acoustic or tactile cues are detectable but not distressing?
- Can cattle be conditioned to associate a cue with returning to a safe area?
- Does a recall cue generalize across locations and contexts?
- How do individual differences and habituation affect response?
- What is the safest training protocol and stopping criteria?
- How can response be measured objectively without assuming causality?

Do not claim a sound encodes left/right direction unless an experiment demonstrates that animals learn and follow that mapping.

## Workstream D — Digital hardware
Questions:
- What coordinate width and fractional precision are sufficient?
- Can squared-distance comparisons avoid square-root hardware?
- Should the nearest-segment search be serial, pipelined, or parallel?
- What is the LUT/BRAM/DSP trade-off?
- What is the energy cost per position update on the FPGA board?
- Which parts, if any, justify later ASIC integration?

## Suggested literature/search themes
- Virtual fencing cattle welfare and learning reviews.
- Acoustic-only virtual fencing and vibration cue experiments.
- Cattle recall training and positive reinforcement.
- GNSS accuracy in livestock collar mounting.
- Map matching and point-to-polyline distance.
- OSM road completeness in rural areas.
- Fixed-point geometry accelerators and low-power event-driven hardware.

Record exact paper title, authors, year, DOI/URL, sample size, methods, and limitations before using a finding in the proposal.
