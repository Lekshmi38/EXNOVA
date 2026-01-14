import math
import random
import copy
from collections import defaultdict, Counter

# ===================== CONFIGURATION =====================
class_group = {
    "S7CSE": "G1", "CSE": "G1",
    "S7IT": "G4", "IT": "G4",
    "S7EC": "G2", "EC": "G2",
    "S7ECE": "G3", "ECE": "G3",
    "S7CE": "G5", "CE": "G5",
    "ME": "G6", "EE": "G7", "CH": "G8", "BT": "G9", "MT": "G10"
}

BLOCK_ORDER = ["Col 1", "Col 2", "Col 3", "Col 4", "Col 5"]

COL_CAPACITY = {
    "Col 1": 7,
    "Col 2": 7,
    "Col 3": 6,
    "Col 4": 7,
    "Col 5": 7
}

ROOM_MAX_CAP = 38
MAX_SUBJ_PER_COL = 2   # 🔥 KEY FIX

# ===================== DATA PROCESSING =====================
def extract_elective_counts(data):
    subj_map = defaultdict(list)
    counts = Counter()

    for roll, branch, subject in data:
        key = f"{branch}:{subject}"
        subj_map[key].append({"roll": roll, "subj": key})
        counts[key] += 1

    for key in subj_map:
        subj_map[key].sort(key=lambda x: x['roll'])

    return subj_map, dict(counts)

def get_room_metrics(room_dict):
    occ = sum(len(col) for col in room_dict.values())
    subjs = {st['subj'] for col in room_dict.values() for st in col}
    grps = {class_group.get(s.split(':')[0], "OTHER") for s in subjs}
    return occ, subjs, grps

def is_safe(room_data, col_name, subject_name):
    subj_grp = class_group.get(subject_name.split(':')[0], "OTHER")
    col_idx = BLOCK_ORDER.index(col_name)

    neighbors = []
    if col_idx > 0:
        neighbors.append(BLOCK_ORDER[col_idx - 1])
    if col_idx < len(BLOCK_ORDER) - 1:
        neighbors.append(BLOCK_ORDER[col_idx + 1])

    for n_blk in neighbors:
        for st in room_data[n_blk]:
            if class_group.get(st['subj'].split(':')[0], "OTHER") == subj_grp:
                return False
    return True

# ===================== ALLOCATION ENGINE =====================
# ===================== ALLOCATION ENGINE =====================
def generate_allocation(subj_map_orig, elective_counts, num_rooms):
    working_subj_map = copy.deepcopy(subj_map_orig)
    subjects = sorted(
        elective_counts.keys(),
        key=lambda x: elective_counts[x],
        reverse=True
    )

    rooms = {
        f"Room{i}": {blk: [] for blk in BLOCK_ORDER}
        for i in range(1, num_rooms + 1)
    }

    remaining_counts = elective_counts.copy()

    # Track which column already has 2-subject pairing per class
    room_class_col_pairing = {
        r_name: defaultdict(lambda: None)  # class -> column that has 2-subject pairing
        for r_name in rooms
    }

    def fill_pass(target_cap, variety_limit):
        for sub in subjects:
            if remaining_counts[sub] <= 0:
                continue

            grp = class_group.get(sub.split(':')[0], "OTHER")
            room_keys = list(rooms.keys())
            random.shuffle(room_keys)

            for r_name in room_keys:
                if remaining_counts[sub] <= 0:
                    break

                occ, subjs, grps = get_room_metrics(rooms[r_name])

                if occ >= target_cap:
                    continue
                if sub not in subjs and len(subjs) >= variety_limit:
                    continue
                if sub not in subjs and grp in grps:
                    continue

                for blk in BLOCK_ORDER:
                    if remaining_counts[sub] <= 0 or occ >= target_cap:
                        break

                    col = rooms[r_name][blk]
                    used = len(col)
                    cap = COL_CAPACITY[blk]
                    col_subjects = {s['subj'] for s in col}

                    # Determine allowed subjects for this column
                    current_pair_col = room_class_col_pairing[r_name][grp]
                    if current_pair_col is None:
                        max_subj_here = 2  # this column can host 2 subjects
                    else:
                        max_subj_here = 1  # other columns limited to 1 subject

                    if used >= cap:
                        continue
                    if sub not in col_subjects and len(col_subjects) >= max_subj_here:
                        continue
                    if not is_safe(rooms[r_name], blk, sub):
                        continue

                    # Assign students
                    free = cap - used
                    take = min(free, remaining_counts[sub])
                    rooms[r_name][blk].extend(working_subj_map[sub][:take])
                    del working_subj_map[sub][:take]
                    remaining_counts[sub] -= take
                    occ += take

                    # Mark this column as the 2-subject pairing if used
                    if max_subj_here == 2 and len(col_subjects) + 1 == 2:
                        room_class_col_pairing[r_name][grp] = blk

    balanced_target = math.ceil(sum(elective_counts.values()) / num_rooms)
    fill_pass(max(20, balanced_target), 2)
    fill_pass(ROOM_MAX_CAP, 3)
    if sum(remaining_counts.values()) > 0:
        fill_pass(ROOM_MAX_CAP, 4)

    return rooms, sum(remaining_counts.values())


# ===================== REPORTING =====================
def save_report(rooms, original_counts):
    total_placed = 0

    with open("Seating_Plan_Adaptive.txt", "w", encoding="utf-8") as f:
        active_rooms = {k: v for k, v in rooms.items() if get_room_metrics(v)[0] > 0}
        room_names = sorted(active_rooms.keys(), key=lambda x: int(x.replace("Room", "")))

        for r_name in room_names:
            r_data = active_rooms[r_name]
            occ, subjs, _ = get_room_metrics(r_data)

            f.write("\n" + "=" * 125 + "\n")
            f.write(f"{r_name.upper()} | CAPACITY: {occ}/{ROOM_MAX_CAP} | SUBJECTS: {len(subjs)}\n")
            f.write("=" * 125 + "\n")
            f.write(f"{'Row':<4} | " + " | ".join([f"{b:<21}" for b in BLOCK_ORDER]) + "\n")
            f.write("-" * 125 + "\n")

            max_rows = max(COL_CAPACITY.values())
            for i in range(max_rows):
                row = f"{i+1:<4} | "
                for blk in BLOCK_ORDER:
                    if i < len(r_data[blk]):
                        st = r_data[blk][i]
                        cell = f"{st['roll']} ({st['subj'].split(':')[0]})"
                        row += f"{cell:<21} | "
                        total_placed += 1
                    elif i < COL_CAPACITY[blk]:
                        row += f"{'--':<21} | "
                    else:
                        row += f"{'X':<21} | "
                f.write(row + "\n")

            f.write("-" * 125 + "\n")

            stats = Counter([st['subj'] for col in r_data.values() for st in col])
            for s, c in stats.items():
                f.write(f"  > {s}: {c} students\n")

        f.write(
            f"\n\nMASTER VERIFICATION\n"
            f"TOTAL PLACED: {total_placed} / {sum(original_counts.values())}\n"
        )

# ===================== MAIN EXECUTION =====================
if __name__ == "__main__":

    raw_data = [
    
    # SUBJECT 1: Large class (47 students)
    ("LBT22CE001", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE002", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE003", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE004", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE005", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE006", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE007", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE008", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE009", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE010", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE011", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE012", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE013", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE014", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE015", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE016", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE017", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE018", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE019", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE020", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE021", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE022", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE023", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE024", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE025", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE026", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE027", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE028", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE029", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE030", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE032", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE033", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LBT22CE034", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LLBT22CE035", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LLBT22CE036", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LLBT22CE037", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LLBT22CE038", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LLBT22CE039", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LLBT22CE040", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LLBT22CE041", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LLBT22CE042", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LLBT22CE043", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LLBT22CE044", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LLBT22CE045", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LLBT22CE046", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    ("LLBT22CE047", "CE", "ADVANCED CONCRETE TECHNOLOGY"),
    
    # SUBJECT 2: Medium class (25 students)
    ("LBT22CS001", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS003", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS014", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS015", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS016", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS021", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS025", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS027", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS029", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS037", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS039", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS046", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS050", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS068", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS070", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS085", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS092", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS099", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS100", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS103", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS107", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS108", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS113", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS114", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    ("LBT22CS127", "CSE", "FOUNDATIONS OF SECURITY IN COMPUTING"),
    
    # SUBJECT 3: Very large class (108 students)
    ("LBT19CS037", "CSE", "PROGRAMMING IN PYTHON"),
    ("LLBT19CS126", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT20CS008", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT20CS045", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT20CS076", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT21CS026", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT21CS067", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT21CS090", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT21CS091", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT21CS109", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS002", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS004", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS005", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS006", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS007", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS008", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS009", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS010", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS011", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS012", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS013", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS017", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS018", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS019", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS020", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS022", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS023", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS024", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS026", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS028", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS030", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS031", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS032", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS033", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS034", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS035", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS036", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS038", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS040", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS041", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS042", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS043", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS044", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS045", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS047", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS048", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS049", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS051", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS052", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS053", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS054", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS055", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS056", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS057", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS058", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS059", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS060", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS061", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS062", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS063", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS064", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS065", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS066", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS067", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS069", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS071", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS072", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS074", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS075", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS076", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS077", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS078", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS079", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS080", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS081", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS082", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS083", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS084", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS086", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS087", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS088", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS089", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS090", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS091", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS093", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS094", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS095", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS096", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS097", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS101", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS102", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS104", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS105", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS106", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS109", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS110", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS111", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS112", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS115", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS116", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS117", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS118", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS119", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS120", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS121", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS122", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS123", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS124", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS125", "CSE", "PROGRAMMING IN PYTHON"),
    ("LBT22CS126", "CSE", "PROGRAMMING IN PYTHON"),
    ("LLBT22CS128", "CSE", "PROGRAMMING IN PYTHON"),
    ("LLBT22CS129", "CSE", "PROGRAMMING IN PYTHON"),
    ("LLBT22CS130", "CSE", "PROGRAMMING IN PYTHON"),
    ("LLBT22CS131", "CSE", "PROGRAMMING IN PYTHON"),
    ("LLBT22CS132", "CSE", "PROGRAMMING IN PYTHON"),
    ("LLBT22CS133", "CSE", "PROGRAMMING IN PYTHON"),
    ("LLBT22CS134", "CSE", "PROGRAMMING IN PYTHON"),
    ("LLBT22CS135", "CSE", "PROGRAMMING IN PYTHON"),
    ("LLBT22CS136", "CSE", "PROGRAMMING IN PYTHON"),

    # SUBJECT 4: Small class (2 students)
    ("LBT20EC027", "EC", "DIGITAL IMAGE PROCESSING"),
    ("LBT20EC054", "EC", "DIGITAL IMAGE PROCESSING"),

    # SUBJECT 5: Medium class (20 students)
    ("LBT22EC002", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC004", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC006", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC010", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC011", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC012", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC017", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC020", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC021", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC022", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC026", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC029", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC030", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC033", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC035", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC037", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC038", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC045", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LBT22EC046", "EC", "DIGITAL SYSTEM DESIGN"),
    ("LLBT22EC048", "EC", "DIGITAL SYSTEM DESIGN"),

    # SUBJECT 6: Large class (36 students)
    ("LBT22EC001", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC003", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC005", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC007", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC008", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC009", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC013", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC014", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC015", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC018", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC019", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC023", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC024", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC025", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC027", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC028", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC031", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC032", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC034", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC036", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC039", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC040", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC041", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC042", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC043", "EC", "EMBEDDED SYSTEMS"),
    ("LBT22EC044", "EC", "EMBEDDED SYSTEMS"),
    ("LLBT22EC047", "EC", "EMBEDDED SYSTEMS"),
    ("LLBT22EC049", "EC", "EMBEDDED SYSTEMS"),
    ("LLBT22EC050", "EC", "EMBEDDED SYSTEMS"),
    ("LLBT22EC051", "EC", "EMBEDDED SYSTEMS"),
    ("LLBT22EC052", "EC", "EMBEDDED SYSTEMS"),
    ("LLBT22EC053", "EC", "EMBEDDED SYSTEMS"),
    ("LLBT22EC054", "EC", "EMBEDDED SYSTEMS"),
    ("LLBT22EC055", "EC", "EMBEDDED SYSTEMS"),
    ("LLBT22EC056", "EC", "EMBEDDED SYSTEMS"),

    # SUBJECT 7: Very small class (2 students)
    ("LBT21EC059", "EC", "INTRODUCTION TO MEMS"),
    ("LLBT21EC062", "EC", "INTRODUCTION TO MEMS"),

    # SUBJECT 8: Medium class (18 students)
    ("LBT22ECE001", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE004", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE005", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE007", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE009", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE016", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE019", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE021", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE024", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE025", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE028", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE029", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE030", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE032", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE037", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE038", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LBT22ECE044", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),
    ("LLBT22ECE049", "ECE", "FOUNDATIONS OF MACHINE LEARNING"),

    # SUBJECT 9: Medium-large class (30 students)
    ("LBT22ECE002", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE003", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE006", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE008", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE010", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE011", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE012", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE013", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE014", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE015", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE017", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE018", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE020", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE022", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE023", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE026", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE027", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE031", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE033", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE034", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE035", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE036", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE039", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE040", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE041", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE042", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE043", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE045", "ECE", "SENSORS AND ACTUATORS"),
    ("LBT22ECE046", "ECE", "SENSORS AND ACTUATORS"),
    ("LLBT22ECE047", "ECE", "SENSORS AND ACTUATORS"),
    ("LLBT22ECE048", "ECE", "SENSORS AND ACTUATORS"),

    # SUBJECT 10: Single student (1 student)
    ("LBT20IT009", "IT", "COMPILER DESIGN"),

    # SUBJECT 11: Single student (1 student)
    ("LBT19IT025", "IT", "DISTRIBUTED SYSTEMS"),

    # SUBJECT 12: Small-medium class (21 students)
    ("LBT22IT003", "IT", "SOFT COMPUTING"),
    ("LBT22IT004", "IT", "SOFT COMPUTING"),
    ("LBT22IT006", "IT", "SOFT COMPUTING"),
    ("LBT22IT007", "IT", "SOFT COMPUTING"),
    ("LBT22IT010", "IT", "SOFT COMPUTING"),
    ("LBT22IT011", "IT", "SOFT COMPUTING"),
    ("LBT22IT014", "IT", "SOFT COMPUTING"),
    ("LBT22IT018", "IT", "SOFT COMPUTING"),
    ("LBT22IT021", "IT", "SOFT COMPUTING"),
    ("LBT22IT023", "IT", "SOFT COMPUTING"),
    ("LBT22IT024", "IT", "SOFT COMPUTING"),
    ("LBT22IT028", "IT", "SOFT COMPUTING"),
    ("LBT22IT029", "IT", "SOFT COMPUTING"),
    ("LBT22IT031", "IT", "SOFT COMPUTING"),
    ("LBT22IT032", "IT", "SOFT COMPUTING"),
    ("LBT22IT033", "IT", "SOFT COMPUTING"),
    ("LBT22IT034", "IT", "SOFT COMPUTING"),
    ("LBT22IT037", "IT", "SOFT COMPUTING"),
    ("LBT22IT040", "IT", "SOFT COMPUTING"),
    ("LBT22IT042", "IT", "SOFT COMPUTING"),
    ("LBT22IT045", "IT", "SOFT COMPUTING"),

    # SUBJECT 13: Medium-large class (30 students)
    ("LBT22IT001", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT002", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT005", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT008", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT009", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT012", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT013", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT015", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT016", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT017", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT019", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT020", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT022", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT025", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT026", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT027", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT030", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT035", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT036", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT038", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT039", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT041", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT043", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LBT22IT044", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LLBT22IT046", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LLBT22IT047", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LLBT22IT048", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LLBT22IT049", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    ("LLBT22IT050", "IT", "USER INTERFACE AND USER EXPERIENCE DESIGN"),
    
    # SUBJECT 14: Very small class (3 students)
    ("LBT22ME001", "ME", "ADVANCED THERMODYNAMICS"),
    ("LBT22ME002", "ME", "ADVANCED THERMODYNAMICS"),
    ("LBT22ME003", "ME", "ADVANCED THERMODYNAMICS"),
    
    # SUBJECT 15: Small class (4 students)
    ("LBT22ME010", "ME", "ROBOTICS ENGINEERING"),
    ("LBT22ME011", "ME", "ROBOTICS ENGINEERING"),
    ("LBT22ME012", "ME", "ROBOTICS ENGINEERING"),
    ("LBT22ME013", "ME", "ROBOTICS ENGINEERING"),
    
    # SUBJECT 16: Small-medium class (8 students)
    ("LBT22EE005", "EE", "POWER SYSTEM ANALYSIS"),
    ("LBT22EE006", "EE", "POWER SYSTEM ANALYSIS"),
    ("LBT22EE007", "EE", "POWER SYSTEM ANALYSIS"),
    ("LBT22EE008", "EE", "POWER SYSTEM ANALYSIS"),
    ("LBT22EE009", "EE", "POWER SYSTEM ANALYSIS"),
    ("LBT22EE010", "EE", "POWER SYSTEM ANALYSIS"),
    ("LBT22EE011", "EE", "POWER SYSTEM ANALYSIS"),
    ("LBT22EE012", "EE", "POWER SYSTEM ANALYSIS"),
    
    # SUBJECT 17: Small class (5 students)
    ("LBT22CH001", "CH", "BIOCHEMICAL ENGINEERING"),
    ("LBT22CH002", "CH", "BIOCHEMICAL ENGINEERING"),
    ("LBT22CH003", "CH", "BIOCHEMICAL ENGINEERING"),
    ("LBT22CH004", "CH", "BIOCHEMICAL ENGINEERING"),
    ("LBT22CH005", "CH", "BIOCHEMICAL ENGINEERING"),
    
    # SUBJECT 18: Single student (1 student)
    ("LBT22BT001", "BT", "BIOPROCESS TECHNOLOGY"),
    
    # SUBJECT 19: Very small class (2 students)
    ("LBT22MT001", "MT", "MATERIALS CHARACTERIZATION"),
    ("LBT22MT002", "MT", "MATERIALS CHARACTERIZATION")
]
    subj_map, elective_counts = extract_elective_counts(raw_data)

    total_students = sum(elective_counts.values())
    rooms_try = math.ceil(total_students / 36)

    best_allocation = None
    min_diff = float("inf")

    while best_allocation is None and rooms_try < 60:
        print(f"Trying {rooms_try} rooms...")

        for _ in range(2000):
            final_rooms, left = generate_allocation(subj_map, elective_counts, rooms_try)
            if left == 0:
                caps = [get_room_metrics(r)[0] for r in final_rooms.values() if get_room_metrics(r)[0] > 0]
                diff = max(caps) - min(caps)

                if diff < min_diff:
                    min_diff = diff
                    best_allocation = final_rooms
                    print(f"✔ Better balance found → diff = {min_diff}")

                if diff <= 1:    
                    break

        if best_allocation is None:
            rooms_try += 1

    if best_allocation:
        save_report(best_allocation, elective_counts)
        print("\n✅ FINAL SEATING PLAN GENERATED")
        print(f"Rooms used: {len([r for r in best_allocation.values() if get_room_metrics(r)[0] > 0])}")
        print(f"Min capacity difference: {min_diff}")
    else:
        print("❌ No valid allocation found")
