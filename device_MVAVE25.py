# name=M-VAVE25-custom-configuration
import mixer
import midi

# ================= CONFIG =================

# --- selected-track knobs (CC numbers) ---
CC_VOLUME = 20
CC_PAN    = 21
CC_SEP    = 22
CC_MASTER = 23

# --- CC -> FX send destination ---
SENDS = {
    24: "fx1",
    25: "fx2",
    26: "fx3",
    27: "fx4",
}

# --- CC -> fixed mixer insert volume ---
TRACK_VOL = {
    28: 1,
    29: 2,
    30: 3,
    31: 4,
    35: 5,
    41: 6,
    46: 7,
    47: 8,
}

# --- pads ---
PAD_SOLO = (10, 89)   # F6
PAD_MUTE = (10, 90)   # F#6

# --- CONSTANTS ---
VOL_MAX    = 0.885   # +2.5 dB
SEND_MAX   = 0.8     # +0.0 dB
AUTO_ROUTE = True    # create FX send route if missing
PICKUP     = midi.PIM_None
DEADZONE   = 2       # snap to center
CALIBRATE  = False   # debug

# ================= HELPERS =================

def bipolar(v):
    d = v - 64
    if abs(d) <= DEADZONE:
        return 0.0
    return max(-1.0, min(1.0, d / 63))

def find_track(name):
    name = name.lower()
    for i in range(1, mixer.trackCount()):
        if mixer.getTrackName(i).strip().lower() == name:
            return i
    return None

def set_send(src, dest, v, auto_route):
    if src == 0 or src == dest:
        return
    if not mixer.getRouteSendActive(src, dest):
        if not auto_route or v == 0:
            return
        mixer.setRouteTo(src, dest, 1)
        mixer.afterRoutingChanged()
    lvl = v / 127 * SEND_MAX
    mixer.setRouteToLevel(src, dest, lvl)
    if CALIBRATE: print("send", src, "->", dest, round(lvl, 4))

def pad_match(event, pad):
    return event.midiChan == pad[0] - 1 and event.data1 == pad[1]

# ================= CALLBACKS =================

def OnControlChange(event):
    cc, v = event.data1, event.data2

    if cc in TRACK_VOL:
        mixer.setTrackVolume(TRACK_VOL[cc], v / 127 * VOL_MAX, PICKUP)
        event.handled = True
        return

    if cc in SENDS:
        dest = find_track(SENDS[cc])
        if dest is not None:
            set_send(mixer.trackNumber(), dest, v, AUTO_ROUTE)
        elif CALIBRATE:
            print("send target not found:", SENDS[cc])
        event.handled = True
        return

    if cc not in (CC_VOLUME, CC_PAN, CC_SEP, CC_MASTER):
        return

    track = mixer.trackNumber()

    if cc == CC_VOLUME:
        vol = v / 127 * VOL_MAX
        mixer.setTrackVolume(track, vol, PICKUP)
        if CALIBRATE: print("vol", round(vol, 4))
    elif cc == CC_PAN:
        mixer.setTrackPan(track, bipolar(v), PICKUP)
    elif cc == CC_SEP:
        mixer.setTrackStereoSep(track, bipolar(v), PICKUP)
    elif cc == CC_MASTER:
        set_send(track, 0, v, auto_route=False)

    event.handled = True

def OnNoteOn(event):
    if CALIBRATE: print("note", event.midiChan + 1, event.data1, event.data2)
    is_solo = pad_match(event, PAD_SOLO)
    is_mute = pad_match(event, PAD_MUTE)
    if not (is_solo or is_mute):
        return
    event.handled = True
    if event.data2 == 0:
        return
    track = mixer.trackNumber()
    if is_solo:
        if track != 0:
            mixer.soloTrack(track)
    else:
        mixer.muteTrack(track)

def OnNoteOff(event):
    if pad_match(event, PAD_SOLO) or pad_match(event, PAD_MUTE):
        event.handled = True