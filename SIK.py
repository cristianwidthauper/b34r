import random
import os
import time

Settings.MoveMouseDelay = 0
Settings.ClickDelay = 0

HUNT_MODE = "explorer"

def get_documents_dir():
    home = os.path.expanduser("~")
    cfg = os.path.join(home, ".config", "user-dirs.dirs")
    if os.path.exists(cfg):
        try:
            f = open(cfg, "r")
            for line in f:
                line = line.strip()
                if line.startswith("XDG_DOCUMENTS_DIR"):
                    val = line.split("=", 1)[1].strip()
                    val = val.strip('"')
                    val = val.replace("$HOME", home)
                    val = val.replace("${HOME}", home)
                    path = os.path.normpath(val)
                    if os.path.isdir(path):
                        f.close()
                        return path
            f.close()
        except:
            pass
    fallback = os.path.join(home, "Documents")
    if os.path.isdir(fallback):
        return fallback
    return home

DOCS_DIR = get_documents_dir()
IMG_DIR = os.path.join(DOCS_DIR, "B34R")
WPT_DIR = os.path.join(IMG_DIR, "WPT")

addImagePath(IMG_DIR)
addImagePath(WPT_DIR)

WAYPOINTS = [
    {"wpt": 1, "mode": "walk"},
    {"wpt": 2, "mode": "walk"},
    {"wpt": 3, "mode": "walk"},
    {"wpt": 4, "mode": "walk"},
    {"wpt": 5, "mode": "walk"},
    {"wpt": 6, "mode": "walk"},
    {"wpt": 7, "mode": "walk"}
]

regMonstros = Region(1564,37,177,357)
regWpt = Region(1740,38,180,198)

regRope   = Region(710,843,16,10)
regShovel = Region(678,841,15,15)
regUse    = Region(852,439,28,26)

similarity = 0.95
MAX_WPT_TRIES = 50
MAIN_DELAY = 0.03
WPT_TRY_DELAY = 0.75
WAIT_AFTER_WALK = 0.25
WAIT_AFTER_SPECIAL = 1.5

COMBAT_GRACE = 0.60
SCAN_SLICE = 0.03

screen = Screen()

def load_monsters():
    monsters = []
    try:
        files = os.listdir(IMG_DIR)
    except:
        files = []
    for fname in files:
        if not fname.endswith(".png"):
            continue
        if fname.startswith("WPT_"):
            continue
        if fname.startswith("atacando_"):
            continue
        base = fname[:-4]
        idle_pat = Pattern(fname).similar(similarity)
        attack_name = "atacando_%s.png" % base
        attack_path = os.path.join(IMG_DIR, attack_name)
        attack_pat = None
        if os.path.exists(attack_path):
            attack_pat = Pattern(attack_name).similar(similarity)
        monsters.append({"name": base, "idle": idle_pat, "attack": attack_pat})
    return monsters

MONSTERS = load_monsters()

last_combat_ts = 0.0
pending_target_name = None
pending_target_match = None

def mark_combat():
    global last_combat_ts
    last_combat_ts = time.time()

def combat_grace_active():
    return (time.time() - last_combat_ts) < COMBAT_GRACE

def move_mouse_to_center_random():
    cx = screen.getW() / 2
    cy = screen.getH() / 2
    dx = random.randint(-15, 15)
    dy = random.randint(-15, 15)
    mouseMove(Location(int(cx + dx), int(cy + dy)))

def is_attacking():
    for m in MONSTERS:
        pat_attack = m["attack"]
        if pat_attack is None:
            continue
        if regMonstros.exists(pat_attack, 0):
            mark_combat()
            return True
    return False

def find_monster():
    for m in MONSTERS:
        pat_idle = m["idle"]
        match = regMonstros.exists(pat_idle, 0)
        if match:
            mark_combat()
            return (m["name"], match)
    return (None, None)

def fast_wait_scan(duration):
    global pending_target_name, pending_target_match
    start = time.time()
    while (time.time() - start) < duration:
        if not running:
            return True
        if is_attacking():
            return True
        name, match = find_monster()
        if match:
            pending_target_name = name
            pending_target_match = match
            return True
        wait(SCAN_SLICE)
    return False

def do_talk_action(mode):
    if not mode.startswith("talk"):
        return
    start = mode.find("(")
    end = mode.rfind(")")
    if start == -1 or end == -1 or end <= start+1:
        return
    inner = mode[start+1:end]
    parts = [p.strip() for p in inner.split(";") if p.strip() != ""]
    if not parts:
        return
    for phrase in parts:
        type(phrase)
        type(Key.ENTER)
        wait(0.75)

def do_wpt_action(mode):
    if isinstance(mode, basestring) and mode.startswith("talk"):
        do_talk_action(mode)
        return
    if mode == "rope":
        click(regRope.getCenter())
    elif mode == "shovel":
        click(regShovel.getCenter())
    elif mode == "use":
        rightClick(regUse.getCenter())

def is_special_mode(mode):
    if isinstance(mode, basestring) and mode.startswith("talk"):
        return True
    return mode in ("rope", "shovel", "use")

def wait_after_arrive(mode):
    if is_special_mode(mode):
        wait(WAIT_AFTER_SPECIAL)
    else:
        wait(WAIT_AFTER_WALK)

def do_cavebot_step(current_index, tries_for_current, at_current_wpt, hunt_mode):
    if len(WAYPOINTS) == 0:
        return (current_index, tries_for_current, at_current_wpt)

    w = WAYPOINTS[current_index]
    wpt_id = w["wpt"]
    mode = w.get("mode", "walk")

    filename = "WPT_%d.png" % wpt_id
    wpt_pat = Pattern(filename).similar(similarity)

    m = regWpt.exists(wpt_pat, 0.1)

    if hunt_mode == "explorer":
        if not m and tries_for_current == 0:
            current_index = (current_index + 1) % len(WAYPOINTS)
            return (current_index, 0, False)

        if not m and tries_for_current > 0:
            wait_after_arrive(mode)
            do_wpt_action(mode)
            current_index = (current_index + 1) % len(WAYPOINTS)
            return (current_index, 0, False)

        if m:
            tries_for_current += 1
            click(m)
            move_mouse_to_center_random()

            if fast_wait_scan(WPT_TRY_DELAY):
                return (current_index, tries_for_current, at_current_wpt)

            if tries_for_current >= MAX_WPT_TRIES:
                current_index = (current_index + 1) % len(WAYPOINTS)
                return (current_index, 0, False)

            return (current_index, tries_for_current, at_current_wpt)

        return (current_index, tries_for_current, at_current_wpt)

    if not at_current_wpt:
        if not m and tries_for_current == 0:
            current_index = (current_index + 1) % len(WAYPOINTS)
            return (current_index, 0, False)

        if not m and tries_for_current > 0:
            wait_after_arrive(mode)
            do_wpt_action(mode)
            return (current_index, 0, True)

        if m:
            tries_for_current += 1
            click(m)
            move_mouse_to_center_random()

            if fast_wait_scan(WPT_TRY_DELAY):
                return (current_index, tries_for_current, at_current_wpt)

            if tries_for_current >= MAX_WPT_TRIES:
                current_index = (current_index + 1) % len(WAYPOINTS)
                return (current_index, 0, False)

            return (current_index, tries_for_current, at_current_wpt)

        return (current_index, tries_for_current, at_current_wpt)

    current_index = (current_index + 1) % len(WAYPOINTS)
    return (current_index, 0, False)

running = True
def stop_script(event):
    global running
    running = False

Env.addHotkey(Key.ESC, KeyModifier.CTRL, stop_script)

print("Cavebot started.")

wasAttacking = False
current_index = 0
tries_for_current = 0
at_current_wpt = False

while running:
    attacking_now = is_attacking()
    if attacking_now:
        mark_combat()

    if wasAttacking and not attacking_now:
        type(Key.END)
        wait(0.05)

    if pending_target_match and not attacking_now:
        click(pending_target_match)
        move_mouse_to_center_random()
        pending_target_name = None
        pending_target_match = None
        wasAttacking = True
        wait(0.05)
        continue

    can_attack = not attacking_now
    if HUNT_MODE == "box" and not at_current_wpt:
        can_attack = False

    if can_attack:
        monster_name, monster_match = find_monster()
        if monster_match:
            click(monster_match)
            move_mouse_to_center_random()
            wasAttacking = True
            wait(0.05)
            continue

    if attacking_now:
        wasAttacking = True
        wait(MAIN_DELAY)
        continue

    if combat_grace_active():
        wasAttacking = attacking_now
        wait(MAIN_DELAY)
        continue

    current_index, tries_for_current, at_current_wpt = do_cavebot_step(
        current_index, tries_for_current, at_current_wpt, HUNT_MODE
    )

    wasAttacking = attacking_now
    wait(MAIN_DELAY)
