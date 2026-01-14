import math
import random
from collections import defaultdict, Counter
import re
import pandas as pd

# -------------------------
# 1. CORE CONFIGURATION
# -------------------------
BRANCH_MAP = {
    "COMPUTER SCIENCE & ENGINEERING": "S7CSE",
    "INFORMATION TECHNOLOGY": "S7IT",
    "CIVIL ENGINEERING": "S7CE",
    "ELECTRONICS & COMMUNICATION ENGG": "S7EC",
    "Electronics and Computer Engineering": "S7ER"
}

CLASS_GROUP = {"S7CSE": "G1", "S7IT": "G4", "S7EC": "G2", "S7ER": "G2", "S7CE": "G3"}
MAX_TOTAL_ROOM = 34
MIN_ROOM_SIZE = 28
MAX_SUBJECTS_PER_ROOM = 2
BLOCK_ORDER = ["Left1", "Left3", "Middle2", "Right1", "Right3"]
# Block capacity constraint: 7-7-6-7-7
BLOCK_CAPACITY = {"Left1": 7, "Left3": 7, "Middle2": 6, "Right1": 7, "Right3": 7}

# Target parameters for automated search
TARGET_MAX_DIFFERENCE = 4  # You can change this to 8 if needed
MAX_ATTEMPTS = 5000  # Maximum attempts to find good solution
MAX_PERFECT_ATTEMPTS = 100  # When 0 leftovers found, try this many more times for better difference

def roll_key(r):
    m = re.search(r'(\d{2})[A-Z]{2,3}(\d+)', str(r))
    if not m: return (99, 9999)
    return (int(m.group(1)), int(m.group(2)))

def print_out(s, f):
    f.write(s + "\n")

# -------------------------
# 2. IMPROVED ALLOCATION ENGINE
# -------------------------
def generate_allocation(classes, supply_data, session_subjects):
    """
    Generate room allocation with better balancing
    """
    # Create pool of students
    pool = []
    for cls, count in classes.items():
        s_count = sum(supply_data.get(cls, {}).values())
        pool.extend([cls] * (count + s_count))

    random.shuffle(pool)  # Add randomness for better distribution
    current_pool = pool.copy()

    # Calculate optimal number of rooms
    avg_per_room = 31  # Target average per room
    num_rooms = math.ceil(len(pool) / avg_per_room)
    rooms = {}

    # Calculate target per room with balancing
    target_per_room = []
    total_students = len(pool)
    for i in range(num_rooms):
        if i == num_rooms - 1:
            # Last room gets remaining
            target_per_room.append(total_students - sum(target_per_room))
        else:
            # Distribute with ±3 variation
            base = total_students // num_rooms
            variation = random.randint(-3, 3)
            target_per_room.append(min(base + variation, MAX_TOTAL_ROOM))

    # Allocate to rooms
    for r in range(num_rooms):
        if not current_pool:
            break

        room = f"Room{r+1}"
        room_target = target_per_room[r]

        # Get class counts in remaining pool
        counts = Counter(current_pool)
        if not counts:
            break

        # Select main subject (most abundant)
        main_sub = max(counts.items(), key=lambda x: x[1])[0]
        main_group = CLASS_GROUP.get(main_sub)

        # Find compatible secondary subject (different group, not already in room)
        possible_secondary = []
        for cls, cnt in counts.items():
            if cls == main_sub:
                continue
            if CLASS_GROUP.get(cls) != main_group:
                possible_secondary.append((cls, cnt))

        # Sort secondary options by count
        possible_secondary.sort(key=lambda x: x[1], reverse=True)

        if possible_secondary:
            sec_sub = possible_secondary[0][0]
        else:
            # If no compatible secondary, use same subject but limit to max 2 subjects per room
            sec_sub = main_sub

        # Calculate allocation with better balancing
        main_count = counts[main_sub]
        sec_count = counts.get(sec_sub, 0)

        # Ensure at least 10 students for main subject for better distribution
        target_main = min(main_count, max(10, int(room_target * 0.65)))
        target_sec = min(sec_count, room_target - target_main)

        # Adjust to meet room target
        remaining = room_target - (target_main + target_sec)
        while remaining > 0:
            if target_main < main_count and target_main < 24:  # Increased from 20
                target_main += 1
            elif target_sec < sec_count and target_sec < 16:   # Increased from 14
                target_sec += 1
            else:
                break
            remaining = room_target - (target_main + target_sec)

        # Store room allocation
        rooms[room] = {
            "sub_a": {"cls": main_sub, "qty": target_main},
            "sub_b": {"cls": sec_sub, "qty": target_sec}
        }

        # Remove allocated students from pool
        for _ in range(target_main):
            if main_sub in current_pool:
                current_pool.remove(main_sub)

        if main_sub != sec_sub:
            for _ in range(target_sec):
                if sec_sub in current_pool:
                    current_pool.remove(sec_sub)

    return rooms, current_pool

def create_block_layout(rooms_data, subjects):
    """
    Convert room allocations to block layout with block capacity constraint
    """
    final = {}

    for room_name, data in rooms_data.items():
        blocks = {b: {} for b in BLOCK_ORDER}

        # Main subject allocation (goes to Left1, Middle2, Right3)
        a_cls = data["sub_a"]["cls"]
        a_qty = data["sub_a"]["qty"]

        if a_qty > 0:
            # Distribute main subject across Left1, Middle2, Right3 with capacity constraints
            total_to_distribute = a_qty

            # Calculate capacities
            left1_cap = BLOCK_CAPACITY["Left1"]
            middle2_cap = BLOCK_CAPACITY["Middle2"]
            right3_cap = BLOCK_CAPACITY["Right3"]

            # Fill Middle2 first (capacity 6)
            if total_to_distribute > 0:
                middle_qty = min(total_to_distribute, middle2_cap)
                if middle_qty > 0:
                    blocks["Middle2"] = {"cls": a_cls, "qty": middle_qty, "subject": subjects.get(a_cls)}
                    total_to_distribute -= middle_qty

            # Distribute remaining between Left1 and Right3
            if total_to_distribute > 0:
                # Try to balance between Left1 and Right3
                if total_to_distribute <= (left1_cap + right3_cap):
                    # Distribute as evenly as possible
                    left_qty = min(math.ceil(total_to_distribute / 2), left1_cap)
                    right_qty = total_to_distribute - left_qty

                    # Adjust if exceeds right capacity
                    if right_qty > right3_cap:
                        right_qty = right3_cap
                        left_qty = total_to_distribute - right_qty

                    if left_qty > 0:
                        blocks["Left1"] = {"cls": a_cls, "qty": left_qty, "subject": subjects.get(a_cls)}
                    if right_qty > 0:
                        blocks["Right3"] = {"cls": a_cls, "qty": right_qty, "subject": subjects.get(a_cls)}
                else:
                    # Fill to capacity
                    left_qty = min(total_to_distribute, left1_cap)
                    if left_qty > 0:
                        blocks["Left1"] = {"cls": a_cls, "qty": left_qty, "subject": subjects.get(a_cls)}
                        total_to_distribute -= left_qty

                    if total_to_distribute > 0:
                        right_qty = min(total_to_distribute, right3_cap)
                        if right_qty > 0:
                            blocks["Right3"] = {"cls": a_cls, "qty": right_qty, "subject": subjects.get(a_cls)}

        # Secondary subject allocation (goes to Left3, Right1)
        b_cls = data["sub_b"]["cls"]
        b_qty = data["sub_b"]["qty"]

        if b_qty > 0 and b_cls != a_cls:  # Only if different from main subject
            # Distribute secondary subject across Left3 and Right1
            total_to_distribute = b_qty

            # Calculate capacities
            left3_cap = BLOCK_CAPACITY["Left3"]
            right1_cap = BLOCK_CAPACITY["Right1"]

            if total_to_distribute <= (left3_cap + right1_cap):
                # Distribute as evenly as possible
                left3_qty = min(math.ceil(total_to_distribute / 2), left3_cap)
                right1_qty = total_to_distribute - left3_qty

                # Adjust if exceeds right capacity
                if right1_qty > right1_cap:
                    right1_qty = right1_cap
                    left3_qty = total_to_distribute - right1_qty

                if left3_qty > 0:
                    blocks["Left3"] = {"cls": b_cls, "qty": left3_qty, "subject": subjects.get(b_cls)}
                if right1_qty > 0:
                    blocks["Right1"] = {"cls": b_cls, "qty": right1_qty, "subject": subjects.get(b_cls)}
            else:
                # Fill to capacity
                left3_qty = min(total_to_distribute, left3_cap)
                if left3_qty > 0:
                    blocks["Left3"] = {"cls": b_cls, "qty": left3_qty, "subject": subjects.get(b_cls)}
                    total_to_distribute -= left3_qty

                if total_to_distribute > 0:
                    right1_qty = min(total_to_distribute, right1_cap)
                    if right1_qty > 0:
                        blocks["Right1"] = {"cls": b_cls, "qty": right1_qty, "subject": subjects.get(b_cls)}

        final[room_name] = blocks

    return final

def rebalance_rooms(layout):
    """
    Rebalance student counts across rooms to ensure all rooms have similar capacity
    """
    # Calculate current totals per room
    room_totals = {}
    for room, blocks in layout.items():
        total = sum(b.get("qty", 0) for b in blocks.values())
        room_totals[room] = total

    # Find rooms that are too full or too empty
    avg_students = sum(room_totals.values()) / len(room_totals)

    # Try to balance by moving subjects between rooms
    for _ in range(20):  # Multiple attempts
        unbalanced_rooms = [(r, t) for r, t in room_totals.items()
                           if abs(t - avg_students) > 4]  # Max diff of 4

        if not unbalanced_rooms:
            break

        # Sort by how unbalanced they are
        unbalanced_rooms.sort(key=lambda x: abs(x[1] - avg_students), reverse=True)

        for room_name, total in unbalanced_rooms[:2]:  # Work on most unbalanced
            blocks = layout[room_name]

            # Find a subject to move
            for block_name, block_data in list(blocks.items()):
                if block_data and block_data.get("qty", 0) > 3:
                    # Try to move 1-2 students
                    move_qty = min(2, block_data["qty"] - 3)

                    # Find a room to move to
                    target_room = None
                    for other_room, other_total in room_totals.items():
                        if other_room != room_name and other_total < avg_students:
                            target_room = other_room
                            break

                    if target_room:
                        # Move students
                        block_data["qty"] -= move_qty
                        room_totals[room_name] -= move_qty

                        # Add to target room
                        target_blocks = layout[target_room]
                        for target_block in BLOCK_ORDER:
                            target_data = target_blocks[target_block]
                            if target_data and target_data.get("cls") == block_data["cls"]:
                                target_data["qty"] += move_qty
                                break
                        else:
                            # Find empty block in target room
                            for target_block in BLOCK_ORDER:
                                if not target_blocks[target_block]:
                                    target_blocks[target_block] = {
                                        "cls": block_data["cls"],
                                        "qty": move_qty,
                                        "subject": block_data["subject"]
                                    }
                                    break

                        room_totals[target_room] += move_qty
                        break

    return layout

def cleanup_leftovers(rooms, leftovers, subjects):
    """
    Improved leftover handling with better distribution
    """
    if not leftovers:
        return rooms

    # Count leftovers by class
    counts = Counter(leftovers)

    # Try to distribute leftovers evenly
    for cls, count in counts.items():
        # Sort rooms by current capacity (ascending)
        room_order = sorted(rooms.keys(),
                          key=lambda x: sum(b.get("qty", 0) for b in rooms[x].values()))

        for room_name in room_order:
            if count <= 0:
                break

            blocks = rooms[room_name]
            current_total = sum(b.get("qty", 0) for b in blocks.values())

            # Skip if room is already full
            if current_total >= MAX_TOTAL_ROOM:
                continue

            # Check if this class already exists in the room
            existing_blocks = []
            for block_name, block_data in blocks.items():
                if block_data and block_data.get("cls") == cls:
                    existing_blocks.append((block_name, block_data))

            if existing_blocks:
                # Add to existing block if space allows
                for block_name, block_data in existing_blocks:
                    if count <= 0:
                        break
                    # Check block capacity (max 7 per column)
                    if block_data.get("qty", 0) < BLOCK_CAPACITY[block_name]:
                        add_qty = min(count, BLOCK_CAPACITY[block_name] - block_data["qty"])
                        block_data["qty"] += add_qty
                        count -= add_qty
            else:
                # Find empty block for this class
                for block_name in BLOCK_ORDER:
                    if count <= 0:
                        break
                    if not blocks[block_name]:
                        # Check room capacity and max subjects
                        subjects_in_room = len({b["cls"] for b in blocks.values() if b})
                        if subjects_in_room < MAX_SUBJECTS_PER_ROOM:
                            add_qty = min(count, BLOCK_CAPACITY[block_name], MAX_TOTAL_ROOM - current_total)
                            blocks[block_name] = {
                                "cls": cls,
                                "qty": add_qty,
                                "subject": subjects.get(cls)
                            }
                            count -= add_qty
                            break

    return rooms

def calculate_room_difference(rooms_data):
    """
    Calculate the max difference between room totals
    """
    room_totals = []
    for room, blocks in rooms_data.items():
        total = sum(b.get("qty", 0) for b in blocks.values())
        room_totals.append(total)

    if not room_totals:
        return float('inf')

    return max(room_totals) - min(room_totals)

# -------------------------
# 3. DATA LOADING & EXECUTION
# -------------------------
def main():
    try:
        df = pd.read_excel("/content/Slot_C_Sorted_List.xlsx")
        df.columns = df.columns.str.strip()

        MASTER_ROLLS = defaultdict(list)
        MASTER_SUBJECTS = {}
        classes_count = {}
        supply_data = defaultdict(dict)

        # Process data
        for _, row in df.iterrows():
            reg = str(row["Register No"]).strip()
            branch = str(row["Branch Name"]).strip()
            course = str(row["Course"]).strip().split(" (")[0]
            bcode = BRANCH_MAP.get(branch)

            if bcode and reg and reg != "nan":
                MASTER_ROLLS[bcode].append(reg)
                MASTER_SUBJECTS[bcode] = course

        # Sort rolls and separate regular/supply
        for bcode, rolls in MASTER_ROLLS.items():
            rolls.sort(key=roll_key)
            years = [roll_key(r)[0] for r in rolls]
            max_yr = max(years) if years else 0
            regular = [r for r in rolls if roll_key(r)[0] == max_yr]
            classes_count[bcode] = len(regular)

            # Count supply students by year
            for r in rolls:
                yr = roll_key(r)[0]
                if yr != max_yr:
                    supply_data[bcode][yr] = supply_data[bcode].get(yr, 0) + 1

        # PHASE 1: Find a solution with 0 leftovers
        print("=" * 70)
        print("PHASE 1: Finding solution with 0 leftovers...")
        print("=" * 70)

        best_solution_phase1 = None
        best_leftovers_phase1 = float('inf')
        best_difference_phase1 = float('inf')
        phase1_completed = False

        for attempt in range(MAX_ATTEMPTS):
            # Generate allocation
            rooms_data, leftovers = generate_allocation(classes_count, supply_data, MASTER_SUBJECTS)

            # Convert to block layout
            block_layout = create_block_layout(rooms_data, MASTER_SUBJECTS)

            # Rebalance
            block_layout = rebalance_rooms(block_layout)

            # Handle leftovers
            block_layout = cleanup_leftovers(block_layout, leftovers, MASTER_SUBJECTS)

            # Count remaining leftovers
            total_students = sum(len(rolls) for rolls in MASTER_ROLLS.values())
            allocated_students = sum(
                sum(b.get("qty", 0) for b in room.values())
                for room in block_layout.values()
            )
            current_leftovers = total_students - allocated_students

            # Calculate room difference
            current_difference = calculate_room_difference(block_layout)

            if current_leftovers < best_leftovers_phase1 or (current_leftovers == best_leftovers_phase1 and current_difference < best_difference_phase1):
                best_leftovers_phase1 = current_leftovers
                best_difference_phase1 = current_difference
                best_solution_phase1 = block_layout.copy()

                if attempt % 100 == 0 or current_leftovers == 0:
                    print(f"Attempt {attempt+1}: Best so far - {best_leftovers_phase1} leftovers, diff={best_difference_phase1}")

            # If we found 0 leftovers, move to phase 2
            if current_leftovers == 0:
                print(f"\n✓ Found 0-leftover solution at attempt {attempt+1}")
                print(f"  Current difference: {current_difference}")
                print(f"\nProceeding to Phase 2: Finding better balanced solution...")
                phase1_completed = True
                break

        if not phase1_completed:
            print(f"\n⚠ Could not find 0-leftover solution after {MAX_ATTEMPTS} attempts")
            print(f"  Best found: {best_leftovers_phase1} leftovers, diff={best_difference_phase1}")
            print(f"  Using best available solution...")
            best_solution = best_solution_phase1
            best_leftovers = best_leftovers_phase1
            best_difference = best_difference_phase1
        else:
            # PHASE 2: Keep searching for solutions with 0 leftovers but smaller difference
            print("=" * 70)
            print("PHASE 2: Finding solution with 0 leftovers AND small difference...")
            print("=" * 70)

            best_solution = best_solution_phase1
            best_leftovers = 0
            best_difference = best_difference_phase1

            phase2_start_attempt = 0
            for attempt in range(MAX_PERFECT_ATTEMPTS):
                # Generate allocation
                rooms_data, leftovers = generate_allocation(classes_count, supply_data, MASTER_SUBJECTS)

                # Convert to block layout
                block_layout = create_block_layout(rooms_data, MASTER_SUBJECTS)

                # Rebalance
                block_layout = rebalance_rooms(block_layout)

                # Handle leftovers
                block_layout = cleanup_leftovers(block_layout, leftovers, MASTER_SUBJECTS)

                # Count remaining leftovers
                total_students = sum(len(rolls) for rolls in MASTER_ROLLS.values())
                allocated_students = sum(
                    sum(b.get("qty", 0) for b in room.values())
                    for room in block_layout.values()
                )
                current_leftovers = total_students - allocated_students

                # Calculate room difference
                current_difference = calculate_room_difference(block_layout)

                # Only consider solutions with 0 leftovers
                if current_leftovers == 0:
                    if current_difference < best_difference:
                        best_difference = current_difference
                        best_solution = block_layout.copy()

                        if attempt % 10 == 0 or current_difference <= TARGET_MAX_DIFFERENCE:
                            print(f"Phase 2 Attempt {attempt+1}: Found better solution with diff={current_difference}")

                        # Early exit if we found target difference
                        if current_difference <= TARGET_MAX_DIFFERENCE:
                            print(f"\n🎯 TARGET ACHIEVED! Found solution with 0 leftovers and diff ≤ {TARGET_MAX_DIFFERENCE}")
                            break

            print(f"\nPhase 2 completed. Best difference achieved: {best_difference}")
            if best_difference > TARGET_MAX_DIFFERENCE:
                print(f"⚠ Could not reach target difference of {TARGET_MAX_DIFFERENCE}, but using best available")

        # Use best solution found
        rooms_data = best_solution

        # Prepare working rolls for final assignment
        working_rolls = {k: list(v) for k, v in MASTER_ROLLS.items()}

        # Generate final report
        with open("Seating_Report.txt", "w", encoding="utf-8") as file:
            print_out("="*100, file)
            print_out("AUTOMATED SEATING ARRANGEMENT".center(100), file)
            print_out("="*100, file)

            # Print block capacity legend
            print_out("\n" + "BLOCK CAPACITY CONSTRAINT: 7-7-6-7-7 (Left1-Left3-Middle2-Right1-Right3)".center(100), file)
            print_out("="*100, file)

            # Print search summary
            print_out(f"\nSEARCH SUMMARY:", file)
            print_out(f"  Target max difference: ≤{TARGET_MAX_DIFFERENCE}", file)
            print_out(f"  Best solution found: {best_leftovers} leftovers, max difference = {best_difference}", file)
            if best_leftovers == 0 and best_difference <= TARGET_MAX_DIFFERENCE:
                print_out(f"  ✓ Target achieved successfully!", file)
            elif best_leftovers == 0:
                print_out(f"  ⚠ 0 leftovers achieved but difference could be better", file)
            else:
                print_out(f"  ⚠ Could not achieve 0 leftovers", file)
            print_out("="*100, file)

            for r in sorted(rooms_data.keys(), key=lambda x: int(re.search(r'\d+', x).group())):
                blocks = rooms_data[r]

                # Prepare column data
                col_data = {b: [] for b in BLOCK_ORDER}
                for blk in BLOCK_ORDER:
                    b = blocks.get(blk)
                    if b and b.get("cls"):
                        for _ in range(b["qty"]):
                            if working_rolls[b["cls"]]:
                                col_data[blk].append(working_rolls[b["cls"]].pop(0))

                # Calculate room total
                room_total = sum(len(v) for v in col_data.values())

                # Print room header
                print_out("\n" + "="*95, file)
                print_out(f" {r} | TOTAL: {room_total} | BLOCK CAPACITY: 7-7-6-7-7 ".center(95, "="), file)
                print_out("="*95, file)
                print_out(f"{'Row':<5} | {'Left1 (7)':<15} | {'Left3 (7)':<15} | {'Middle2 (6)':<15} | {'Right1 (7)':<15} | {'Right3 (7)':<15}", file)
                print_out("-" * 95, file)

                # Print rows (max 7 rows per column)
                max_rows = 7
                for i in range(max_rows):
                    row_str = f"{i+1:<5} | "
                    for blk in BLOCK_ORDER:
                        if i < len(col_data[blk]):
                            row_str += f"{col_data[blk][i]:<15} | "
                        else:
                            row_str += f"{'--':<15} | "
                    print_out(row_str, file)

                # Print block usage summary
                print_out("-" * 95, file)
                block_summary = []
                for blk in BLOCK_ORDER:
                    count = len(col_data[blk])
                    capacity = BLOCK_CAPACITY[blk]
                    block_summary.append(f"{blk}: {count}/{capacity}")
                print_out(f"Block Usage: {', '.join(block_summary)}", file)

                # Print subjects
                subjects_set = set()
                for b in blocks.values():
                    if b and b.get('cls'):
                        subjects_set.add(f"{b['cls']}: {b['subject']}")
                subjects_str = ", ".join(sorted(subjects_set))
                print_out(f"Subjects: {subjects_str}", file)

            # Final report
            remaining_students = []
            for cls, rolls in working_rolls.items():
                remaining_students.extend(rolls)

            print_out("\n" + "#"*60, file)
            if not remaining_students:
                print_out("REPORT: SUCCESS (0 Leftover)".center(60), file)
            else:
                print_out(f"REPORT: {len(remaining_students)} STUDENTS NOT ALLOTTED".center(60), file)
                print_out("#"*60, file)
                for i in range(0, len(remaining_students), 10):
                    print_out(", ".join(remaining_students[i:i+10]), file)
            print_out("#"*60, file)

            # Add statistics
            room_totals = []
            for r in sorted(rooms_data.keys(), key=lambda x: int(re.search(r'\d+', x).group())):
                total = sum(b.get("qty", 0) for b in rooms_data[r].values())
                room_totals.append(total)

            if room_totals:
                avg = sum(room_totals) / len(room_totals)
                min_r = min(room_totals)
                max_r = max(room_totals)
                diff = max_r - min_r
                print_out(f"\nRoom Statistics:", file)
                print_out(f"  Average students per room: {avg:.1f}", file)
                print_out(f"  Min students in a room: {min_r}", file)
                print_out(f"  Max students in a room: {max_r}", file)
                print_out(f"  Max difference: {diff}", file)

                # Check if difference is acceptable
                if best_leftovers == 0 and diff <= TARGET_MAX_DIFFERENCE:
                    print_out(f"  ✓ Excellent! 0 leftovers and well-balanced rooms", file)
                elif best_leftovers == 0:
                    print_out(f"  ✓ Good! 0 leftovers achieved", file)
                    print_out(f"  ⚠ Room balance could be better (target ≤{TARGET_MAX_DIFFERENCE})", file)
                else:
                    print_out(f"  ⚠ Could not achieve 0 leftovers", file)

        print(f"\n{'='*70}")
        print(f"FINAL RESULTS:")
        print(f"{'='*70}")
        print(f"  Leftover students: {best_leftovers}")
        print(f"  Max room difference: {best_difference}")
        print(f"  Target difference: ≤{TARGET_MAX_DIFFERENCE}")

        if best_leftovers == 0 and best_difference <= TARGET_MAX_DIFFERENCE:
            print(f"\n  🎯 PERFECT SOLUTION FOUND!")
        elif best_leftovers == 0:
            print(f"\n  ✓ Good solution with 0 leftovers")
            print(f"  ⚠ Room difference could be better")
        else:
            print(f"\n  ⚠ Could not achieve 0 leftovers")

        print(f"\nFile 'Seating_Report.txt' generated successfully.")

    except Exception as e:
        print(f"Error encountered: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
