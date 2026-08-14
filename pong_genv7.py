import tkinter as tk
from tkinter import messagebox
import json
import os

# =========================
# CSV INPUT
# =========================
csv_data = """
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,#,.,.,#,#,.,.,#,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,.,.,.,.,#,#,.,.,.,.,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,.
.,#,.,A,A,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,#,.,.,#,#,.,.,#,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,A,A,.,#,.
.,#,.,.,A,A,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,.,.,#,#,.,.,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,A,A,.,.,#,.
.,#,A,A,.,.,A,A,.,.,.,.,.,.,.,.,.,.,.,#,#,#,.,.,#,#,.,.,#,#,#,.,.,.,.,.,.,.,.,.,.,.,A,A,.,.,A,A,#,.
.,#,.,A,A,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,A,A,.,#,.
.,.,.,.,A,A,.,C,C,C,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,A,A,.,.,.,.
.,.,.,.,.,.,.,C,C,C,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,.,.,.,.,.,.,C,C,C,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,.,.,.,#,#,.,.,.,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.
.,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,.,.,.,.,#,#,.,.,.,.,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,A,.,.,.,A,.,.,A,.,.,.,A,.,.,A,.,.,.,A,.,.,.,.,#,#,.,.,.,.,A,.,.,.,A,.,.,A,.,.,.,A,.,.,A,.,.,.,A,.
.,.,A,.,A,.,.,.,.,A,.,A,.,.,.,.,A,.,A,.,.,.,.,.,#,#,.,.,.,.,.,A,.,A,.,.,.,.,A,.,A,.,.,.,.,A,.,A,.,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,.,.,.,#,#,.,.,.,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.
.,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,.,.,.,.,#,#,.,.,.,.,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,T,.,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,#,#,#,#,.,#,#,#,#,.,#,#,.,#,.,#,#,#,#,.,.,.,.,#,#,.,.,.,.,#,#,#,#,.,#,.,#,#,.,#,#,#,#,.,#,#,#,#,.
.,#,.,.,#,.,#,.,.,#,.,#,#,#,#,.,#,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,#,.,#,#,#,#,.,#,.,.,#,.,#,.,.,#,.
.,#,#,#,#,.,#,.,.,#,.,#,.,#,#,.,#,.,#,#,.,.,.,.,#,#,.,.,.,.,#,#,.,#,.,#,#,.,#,.,#,.,.,#,.,#,#,#,#,.
.,#,.,.,.,.,#,.,.,#,.,#,.,#,#,.,#,.,.,#,.,.,.,.,#,#,.,.,.,.,#,.,.,#,.,#,#,.,#,.,#,.,.,#,.,.,.,.,#,.
.,#,.,.,.,.,#,#,#,#,.,#,.,.,#,.,#,#,#,#,.,.,.,.,#,#,.,.,.,.,#,#,#,#,.,#,.,.,#,.,#,#,#,#,.,.,.,.,#,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,#,#,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.,.
"""

lines = csv_data.strip().split("\n")
grid = [row.split(",") for row in lines if row.strip()]

rows = len(grid)
cols = len(grid[0])

# =========================
# ROOT
# =========================
root = tk.Tk()
root.title("Grid Editor (Persistent Arrows)")

CELL_SIZE = 25

# =========================
# STATE
# =========================
mode = "single"
first_selection = None
active_path_index = None
insert_index = None

replace_target_index = None # New: Index of the entry to be replaced
last_action_mode = "single" # New: Stores the last non-selection mode
selection_intent = None     # "insert", "replace", "delete", or None
paths = []
rects = {} # Stores canvas rectangle IDs
JSON_FILE = os.path.join(os.path.dirname(__file__), "pong_paths.json")
TERMINAL_COLOR = "#ffff00" # Bright yellow for the end of the path
BLOCKED_COLOR = "#555555" # Dark grey for blocked cells

# =========================
# COLORS
# =========================
COLORS = ["#ff4d4d", "#4d79ff", "#4dff4d", "#d94dff", "#ff944d", "#4dffff"]
DEFAULT_BG = "SystemButtonFace"
SELECTED_ORANGE = "#ffcc00"
REPLACE_HIGHLIGHT_COLOR = "#ff00ff" # Magenta for replace target

def get_path_color(i):
    return COLORS[i % len(COLORS)]

# =========================
# CANVAS
# =========================
main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True)

canvas = tk.Canvas(main_frame, width=cols * CELL_SIZE, height=rows * CELL_SIZE)
canvas.pack(side=tk.LEFT)

# =========================
# HELPERS
# =========================
def center(x, y):
    return (
        x * CELL_SIZE + CELL_SIZE // 2,
        y * CELL_SIZE + CELL_SIZE // 2
    )

def reset_cell(x, y):
    val = grid[y][x]
    r_id = rects[(x, y)]

    if val == "#":
        canvas.itemconfig(r_id, fill="black")
    elif val == "A":
        canvas.itemconfig(r_id, fill="lightblue")
    elif val == "T":
        canvas.itemconfig(r_id, fill="lightgreen")
    else:
        canvas.itemconfig(r_id, fill=DEFAULT_BG)

# =========================
# REDRAW ALL EDGES (IMPORTANT FIX)
# =========================
def redraw():
    canvas.delete("arrow")
    canvas.delete("highlight")

    # 1. Reset all cells
    for y in range(rows):
        for x in range(cols):
            reset_cell(x, y)

    # 2. Draw paths and arrows
    for p_idx, p in enumerate(paths):
        p_color = p["color"]
        num_entries = len(p["entries"])
        for i, entry in enumerate(p["entries"]):
            is_last = (i == num_entries - 1)
            
            if entry[0] == "single":
                ex, ey = entry[1]
                # If it's the last step in the path, use the terminal color
                cell_color = TERMINAL_COLOR if is_last else p_color
                canvas.itemconfig(rects[(ex, ey)], fill=cell_color)
            elif entry[0] == "blocked_single":
                ex, ey = entry[1]
                canvas.itemconfig(rects[(ex, ey)], fill=BLOCKED_COLOR)
            elif entry[0] == "pair":
                a, b = entry[1], entry[2]
                
                # The first point of the pair gets the terminal color if it is the end of the path
                canvas.itemconfig(rects[a], fill=TERMINAL_COLOR if is_last else p_color)
                
                x1, y1 = center(*a)
                x2, y2 = center(*b)
                canvas.create_line(x1, y1, x2, y2, fill="black",
                    width=2,
                    arrow=tk.LAST,
                    tags="arrow"
                )

            # Highlight the insertion/replacement point if it matches the current index in the active path
            if p_idx == active_path_index:
                h_color = None
                if i == insert_index:
                    h_color = "white" # Existing insert highlight
                elif i == replace_target_index: # New: Highlight for replacement
                    h_color = REPLACE_HIGHLIGHT_COLOR
                
                if h_color:
                    h_cells = []
                    if entry[0] in ("single", "blocked_single"): h_cells = [entry[1]]
                    elif entry[0] == "pair": h_cells = [entry[1], entry[2]]
                    # Wait entries don't have a location, so no highlight
                    
                    for hx, hy in h_cells:
                        ax1, ay1 = hx * CELL_SIZE, hy * CELL_SIZE
                        ax2, ay2 = ax1 + CELL_SIZE, ay1 + CELL_SIZE
                        canvas.create_rectangle(ax1+2, ay1+2, ax2-2, ay2-2, outline=h_color, width=3, tags="highlight")
    # Ensure arrows are drawn on top
    canvas.tag_raise("arrow")
    canvas.tag_raise("highlight")

# =========================
# PATH SYSTEM
# =========================
def new_path(): # New: Clears replace_target_index
    global active_path_index, first_selection, insert_index, replace_target_index

    paths.append({
        "entries": [],
        "color": get_path_color(len(paths))
    })

    active_path_index = len(paths) - 1
    first_selection = None
    insert_index = None
    replace_target_index = None # Clear replace target

    refresh_panel()
    redraw()

def clear_paths():
    global paths, active_path_index, first_selection, insert_index, replace_target_index
    if messagebox.askyesno("Clear All", "Are you sure you want to delete all paths?"):
        paths = []
        active_path_index = None
        first_selection = None
        insert_index = None
        replace_target_index = None # Clear replace target
        refresh_panel()
        redraw()

def load_paths():
    global paths, active_path_index
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r") as f:
                data = json.load(f)
                for i, path_entries_from_json in enumerate(data):
                    current_path_entries = []
                    for entry_from_json in path_entries_from_json:
                        entry_type = entry_from_json[0]
                        if entry_type == "single":
                            current_path_entries.append((entry_type, tuple(entry_from_json[1])))
                        elif entry_type == "pair":
                            current_path_entries.append((entry_type, tuple(entry_from_json[1]), tuple(entry_from_json[2])))
                        elif entry_type == "blocked_single":
                            current_path_entries.append((entry_type, tuple(entry_from_json[1])))
                        elif entry_type == "wait":
                            current_path_entries.append((entry_type, None))
                    paths.append({
                        "entries": current_path_entries,
                        "color": get_path_color(i)
                    })
            if paths:
                active_path_index = len(paths) - 1
            print(f"Loaded {len(paths)} paths.")
        except Exception as e:
            print(f"Failed to load paths: {e}")

def refresh_panel():
    panel.delete(0, tk.END)
    for i in range(len(paths)):
        p = paths[i]
        status = ""
        if i == active_path_index:
            status = "👉 "
            if insert_index is not None:
                status += f"[Ins@{insert_index}] "
        label = f"{status}Path {i} (len: {len(p['entries'])})"
        panel.insert(tk.END, label)

def select_path(event):
    global active_path_index, insert_index
    if panel.curselection():
        active_path_index = panel.curselection()[0]
        insert_index = None
        refresh_panel()
        redraw()

# =========================
# MODE TOGGLE
# =========================
def update_labels():
    mode_label.config(text=f"Tool: {mode.upper()}")
    
    if selection_intent == "insert":
        edit_label.config(text="Status: SELECTING INSERT POINT", fg="blue")
    elif selection_intent == "replace":
        edit_label.config(text="Status: SELECTING REPLACE TARGET", fg="magenta")
    elif selection_intent == "delete":
        edit_label.config(text="Status: DELETE MODE (Click to remove)", fg="red")
    elif insert_index is not None:
        edit_label.config(text=f"Status: INSERTING AFTER {insert_index}", fg="blue")
    elif replace_target_index is not None:
        edit_label.config(text=f"Status: REPLACING @ {replace_target_index}", fg="magenta")
    else:
        edit_label.config(text="Status: APPENDING", fg="black")

def toggle_mode():
    global mode, first_selection
    action_modes = ["single", "pair", "blocked_single", "wait"]
    mode_index = (action_modes.index(mode) + 1) % len(action_modes)
    mode = action_modes[mode_index]
    first_selection = None
    update_labels()
    redraw()

def start_select_insert():
    global selection_intent, first_selection, insert_index, replace_target_index
    # Toggle selection intent
    selection_intent = "insert" if selection_intent != "insert" else None
    first_selection = None
    insert_index = None 
    replace_target_index = None
    update_labels()
    redraw() # Clear highlights

def start_select_replace():
    global selection_intent, first_selection, insert_index, replace_target_index
    # Toggle selection intent
    selection_intent = "replace" if selection_intent != "replace" else None
    first_selection = None
    insert_index = None 
    replace_target_index = None
    update_labels()
    redraw() # Clear highlights

def start_select_delete():
    global selection_intent, first_selection, insert_index, replace_target_index
    # Toggle selection intent
    selection_intent = "delete" if selection_intent != "delete" else None
    first_selection = None
    insert_index = None 
    replace_target_index = None
    update_labels()
    redraw() # Clear highlights

def clear_edit_point():
    global insert_index, replace_target_index, selection_intent
    insert_index = None
    replace_target_index = None
    selection_intent = None
    update_labels()
    refresh_panel()
    redraw()

# =========================
# CLICK HANDLER
# =========================
def on_click(x, y): # New: Handles replace_select mode and replacement logic
    global first_selection, mode, insert_index, replace_target_index, selection_intent

    if active_path_index is None:
        print("Create a path first (N)")
        return

    p = paths[active_path_index]

    if selection_intent == "insert":
        found_idx = None
        for i in range(len(p["entries"])):
            entry = p["entries"][i]
            if (entry[0] in ("single", "blocked_single") and entry[1] == (x, y)) or \
               (entry[0] == "pair" and (entry[1] == (x, y) or entry[2] == (x, y))):
                found_idx = i
                break
        insert_index = found_idx
        selection_intent = None
        update_labels()
        redraw()
        refresh_panel()
        return
    
    if selection_intent == "replace":
        found_idx = None
        for i in range(len(p["entries"])):
            entry = p["entries"][i]
            if (entry[0] in ("single", "blocked_single") and entry[1] == (x, y)) or \
               (entry[0] == "pair" and (entry[1] == (x, y) or entry[2] == (x, y))):
                found_idx = i
                break
        
        if found_idx is not None:
            replace_target_index = found_idx
            selection_intent = None
            update_labels()
            redraw() # Highlight the selected entry
            refresh_panel()
        else:
            print(f"No path entry found at ({x}, {y}) in active path.")
        return

    if selection_intent == "delete":
        found_idx = None
        for i in range(len(p["entries"])):
            entry = p["entries"][i]
            if (entry[0] in ("single", "blocked_single") and entry[1] == (x, y)) or \
               (entry[0] == "pair" and (entry[1] == (x, y) or entry[2] == (x, y))):
                found_idx = i
                break
        
        if found_idx is not None:
            p["entries"].pop(found_idx)
            # Adjust edit indices if they were affected by the removal
            if insert_index == found_idx: insert_index = None
            elif insert_index is not None and insert_index > found_idx: insert_index -= 1
            if replace_target_index == found_idx: replace_target_index = None
            elif replace_target_index is not None and replace_target_index > found_idx: replace_target_index -= 1
            update_labels(); redraw(); refresh_panel()
        return

    new_entry = None

    # ---------------- SINGLE ----------------
    if mode == "single":
        new_entry = ("single", (x, y))

    # ---------------- BLOCKED SINGLE ----------------
    elif mode == "blocked_single":
        new_entry = ("blocked_single", (x, y))

    # ---------------- WAIT ----------------
    elif mode == "wait":
        new_entry = ("wait", None)

    # ---------------- PAIR (ARROWS) ----------------
    else:
        if first_selection is None:
            first_selection = (x, y)
            canvas.itemconfig(rects[(x, y)], fill=SELECTED_ORANGE)
        else:
            new_entry = ("pair", first_selection, (x, y))
            first_selection = None

    # New: Apply replacement or insertion/append
    if new_entry:
        if replace_target_index is not None: # New: If replacing, replace the entry
            p["entries"][replace_target_index] = new_entry
            replace_target_index = None # Clear after replacement
            update_labels()
        elif insert_index is not None:
            p["entries"].insert(insert_index + 1, new_entry)
            insert_index += 1
            update_labels()
        else: # Append if no insert/replace target
            p["entries"].append(new_entry)
        redraw()
        refresh_panel()

# =========================
# UNDO
# =========================
def undo(event=None): # New: Handle replace_target_index
    global insert_index, replace_target_index, selection_intent
    if active_path_index is None:
        return "break"

    p = paths[active_path_index]

    if p["entries"]:
        if insert_index is not None:
            p["entries"].pop(insert_index)
            insert_index -= 1
            if insert_index < 0:
                insert_index = None
        elif replace_target_index is not None: # New: If a replacement target is set, undo cancels the selection
            replace_target_index = None
        elif selection_intent is not None:
            selection_intent = None
        else:
            p["entries"].pop()

    update_labels()
    redraw()
    refresh_panel()
    return "break"

root.bind("<Button-3>", undo)

# =========================
# GRID BUILD
# =========================
for y in range(rows):
    for x in range(cols):
        val = grid[y][x]

        x1, y1 = x * CELL_SIZE, y * CELL_SIZE
        x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
        
        rect_id = canvas.create_rectangle(x1, y1, x2, y2, outline="gray")
        rects[(x, y)] = rect_id
        reset_cell(x, y)
        
        # Bind clicks to both rectangle and label
        lbl_id = canvas.create_text(x1 + 12, y1 + 12, text=val, font=("Arial", 8))
        for item in (rect_id, lbl_id):
            canvas.tag_bind(item, "<Button-1>", lambda e, x=x, y=y: on_click(x, y))

# =========================
# UI
# =========================
side_panel = tk.Frame(main_frame)
side_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=10)

top = tk.Frame(side_panel)
top.pack(side=tk.TOP, fill=tk.X)

mode_label = tk.Label(top, text="Tool: SINGLE", font=("Arial", 10, "bold"))
mode_label.pack()

edit_label = tk.Label(top, text="Status: APPENDING", font=("Arial", 9))
edit_label.pack()

tk.Button(top, text="Toggle Mode (M)", command=toggle_mode).pack()
tk.Button(top, text="New Path (N)", command=new_path).pack()
tk.Button(top, text="Set Insert Point (I)", command=start_select_insert).pack()
tk.Button(top, text="Set Replace Target (R)", command=start_select_replace).pack() # New button
tk.Button(top, text="Delete Mode (D)", command=start_select_delete).pack()
tk.Button(top, text="Clear Edit Point", command=clear_edit_point).pack() # Renamed button
tk.Button(top, text="Clear All Paths", command=clear_paths, fg="red").pack()

panel_frame = tk.Frame(side_panel)
panel_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=10)

scrollbar = tk.Scrollbar(panel_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

panel = tk.Listbox(panel_frame, width=30, yscrollcommand=scrollbar.set)
panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scrollbar.config(command=panel.yview)
panel.bind("<<ListboxSelect>>", select_path)

root.bind("m", lambda e: toggle_mode())
root.bind("n", lambda e: new_path())
root.bind("i", lambda e: start_select_insert()) # Existing binding
root.bind("r", lambda e: start_select_replace()) # New binding
root.bind("d", lambda e: start_select_delete())

# =========================
# EXIT
# =========================
def save_paths_to_file():
    """Save paths to a JSON file in pong_path_processing.py format."""
    paths_data = []
    for p in paths:
        # Convert entries to JSON-compatible format (tuples become lists)
        path_entries = []
        for entry in p["entries"]:
            if entry[0] == "single":
                path_entries.append(["single", entry[1]])
            elif entry[0] == "blocked_single":
                path_entries.append(["blocked_single", entry[1]])
            elif entry[0] == "pair":
                path_entries.append(["pair", entry[1], entry[2]])
            elif entry[0] == "wait":
                path_entries.append(["wait", None])
        paths_data.append(path_entries)
    
    filepath = os.path.join(os.path.dirname(__file__), "pong_paths.json")
    with open(filepath, "w") as f:
        json.dump(paths_data, f, indent=2)
    print(f"Paths saved to {filepath}")

def on_close():
    ans = messagebox.askyesnocancel("Exit", "Save changes before exiting?")
    if ans is None: # Cancel
        return
    if ans is True: # Yes
        save_paths_to_file()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

load_paths()
refresh_panel()
redraw()

root.mainloop()