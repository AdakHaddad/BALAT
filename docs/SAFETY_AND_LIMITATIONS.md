# Safety, Welfare, and Limitations

## Road and map safety
- OpenStreetMap or any digital map can be incomplete, outdated, or positionally inaccurate.
- A road centerline is not the road edge. Road width and safety buffer require local verification.
- Private roads, farm tracks, new roads, bridges, and access points may be missing.
- GNSS multipath, canopy, buildings, antenna placement, and collar orientation can create large errors.
- A geospatial warning device must not replace fences, supervision, or traffic controls.

## Cue and animal welfare
- No electric shock, painful stimulus, or coercive actuation is part of this project.
- Sound/vibration response is not guaranteed and varies by animal, breed, age, context, and training.
- Habituation, startle, stress, and unintended movement are possible.
- Use positive conditioning and supervised trials in an enclosed safe area.
- Set cue limits, quiet intervals, and manual disable.
- Stop testing if distress or unsafe behavior occurs.
- A cue that causes panic or unpredictable movement is a failed cue.

## Hardware safety
- FPGA I/O cannot directly power motors or speakers.
- Use load-specific driver circuits, current limiting, transient suppression, and suitable power rails.
- Verify all connector pinouts and voltage levels before connecting modules.
- Ensure reset and fault states leave actuators inactive.

## Claims discipline
Clearly distinguish:
- simulated behavior;
- FPGA bench demonstration;
- measured GNSS/map performance;
- controlled animal response observations;
- proven field safety outcomes.

Do not describe the prototype as preventing road accidents until robust field evidence supports that claim.
