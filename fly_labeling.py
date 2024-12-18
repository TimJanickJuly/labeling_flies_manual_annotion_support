import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from PIL import Image, ImageTk, ImageOps
import pandas as pd
import time

# Helper functions
def update_base_folder():
    base_path = Path(base_folder_entry.get())
    if base_path.exists() and base_path.is_dir():
        global base_folder
        base_folder = base_path
        populate_batches()
    else:
        error_label.config(text="Invalid path. Please enter a valid folder path.")

def populate_batches():
    batch_dropdown['menu'].delete(0, 'end')
    global batches
    batches = [folder for folder in base_folder.iterdir() if folder.is_dir()]
    for batch in batches:
        batch_dropdown['menu'].add_command(
            label=batch.name, command=lambda b=batch: on_batch_selected(b))
    if batches:
        on_batch_selected(batches[0])

def on_batch_selected(selected_batch):
    global current_batch
    current_batch = selected_batch
    batch_var.set(selected_batch.name)
    populate_subjects()

def populate_subjects():
    subject_dropdown['menu'].delete(0, 'end')
    global subjects
    subjects = [folder for folder in current_batch.iterdir() if folder.is_dir()]
    for subject in subjects:
        label_color = "green" if is_labeled(subject.name) else "black"
        subject_dropdown['menu'].add_command(
            label=subject.name, command=lambda s=subject: on_subject_selected(s), foreground=label_color)
    if subjects:
        on_subject_selected(subjects[0])

def on_subject_selected(selected_subject):
    global current_subject, current_image_index
    current_subject = selected_subject
    current_image_index = 0  # Reset to the first image
    subject_var.set(selected_subject.name)
    update_csv_for_subject()
    display_image()
    update_status_label()

def update_csv_for_subject():
    global current_batch, current_subject, results_df
    if current_subject is not None:
        batch_name = current_batch.name
        subject_name = current_subject.name
        if not ((results_df['Batch'] == batch_name) & (results_df['Subject'] == subject_name)).any():
            new_row = {
                'Batch': batch_name,
                'Subject': subject_name,
                'time alive': None,
                'time of metamorphosis': None
            }
            results_df = pd.concat([results_df, pd.DataFrame([new_row])], ignore_index=True)
            save_results_csv()

def display_image():
    global current_subject, current_image_index, is_grayscale_stretching
    if current_subject:
        images = list(current_subject.glob("*.jpg"))
        if images:
            image_path = images[current_image_index]
            image = Image.open(image_path)

            if is_grayscale_stretching:
                image = image.convert("L")
                image = ImageOps.equalize(image)

            load_and_display_image(image)
        else:
            error_label.config(text="No images found in the selected subject folder.")

def load_and_display_image(image):
    try:
        image = image.resize((500, 500))
        photo = ImageTk.PhotoImage(image)
        image_label.config(image=photo)
        image_label.image = photo

        # Extract and display image number
        image_number_label.config(text=f"Image Number: {current_image_index + 1}")
        error_label.config(text="")
    except Exception as e:
        error_label.config(text=f"Error loading image: {e}")

def update_status_label():
    global current_batch, current_subject, results_df
    batch_name = current_batch.name
    subject_name = current_subject.name
    mask = (results_df['Batch'] == batch_name) & (results_df['Subject'] == subject_name)
    if mask.any() and pd.notna(results_df.loc[mask, 'time alive'].iloc[0]):
        status_label.config(text="already labeled", fg="green")
    else:
        status_label.config(text="not labeled yet", fg="gray")

def is_labeled(subject_name):
    global current_batch, results_df
    batch_name = current_batch.name
    mask = (results_df['Batch'] == batch_name) & (results_df['Subject'] == subject_name)
    return mask.any() and pd.notna(results_df.loc[mask, 'time alive'].iloc[0])

def save_results_csv():
    results_df.to_csv(results_file, index=False)

def start_auto_scroll():
    global auto_navigation, is_auto_scrolling

    def scroll_forward():
        global current_image_index
        images = list(current_subject.glob("*.jpg"))
        if is_auto_scrolling and images and current_image_index < len(images) - 1:
            current_image_index += 1
            display_image()
            auto_navigation = root.after(200, scroll_forward)  # Adjusted rate to 200ms

    if not is_auto_scrolling:
        is_auto_scrolling = True
        auto_navigation = root.after(200, scroll_forward)  # Adjusted rate to 200ms

def stop_navigation(event=None):
    global auto_navigation, is_auto_scrolling
    if auto_navigation:
        root.after_cancel(auto_navigation)
        auto_navigation = None
    is_auto_scrolling = False

def on_key_press(event):
    global is_auto_scrolling, current_image_index
    stop_navigation()  # Always stop scrolling on key press
    if not is_auto_scrolling:
        if event.keysym == 'Up':
            start_auto_scroll()
        elif event.keysym == 'x':
            save_time_in_csv('time of metamorphosis', "Time of metamorphosis saved")
        elif event.keysym == 'Return':
            save_time_in_csv('time alive', "Time alive saved")
            current_image_index = 0  # Reset to the first image for the next subject
            go_to_next_subject()
        elif event.keysym in ('Right', 'Left'):
            navigate_single_image(event)

def navigate_single_image(event):
    global current_image_index
    images = list(current_subject.glob("*.jpg"))
    if not images:
        return

    if event.keysym == 'Right' and current_image_index < len(images) - 1:
        current_image_index += 1
        display_image()
    elif event.keysym == 'Left' and current_image_index > 0:
        current_image_index -= 1
        display_image()

def save_time_in_csv(column_name, message):
    global current_batch, current_subject, results_df, current_image_index
    batch_name = current_batch.name
    subject_name = current_subject.name
    images = list(current_subject.glob("*.jpg"))
    if not images:
        return

    image_name = images[current_image_index].name
    image_number = int(float(image_name.split('-')[-2]))  # Ensure integer

    mask = (results_df['Batch'] == batch_name) & (results_df['Subject'] == subject_name)
    results_df.loc[mask, column_name] = image_number
    save_results_csv()
    temporary_message(message)
    update_status_label()

def temporary_message(message):
    feedback_label.config(text=message)
    root.after(1000, lambda: feedback_label.config(text=""))

def go_to_next_subject():
    global subjects, current_subject
    current_index = subjects.index(current_subject)
    if current_index < len(subjects) - 1:
        on_subject_selected(subjects[current_index + 1])
    else:
        feedback_label.config(text="BATCH COMPLETE")

def toggle_grayscale_stretching():
    global is_grayscale_stretching
    is_grayscale_stretching = not is_grayscale_stretching
    display_image()  # Refresh the current image

# GUI Setup
root = tk.Tk()
root.title("Image Classification Tool")
root.geometry("800x600")

base_folder = Path("data_raw")
batches = []
subjects = []
current_batch = None
current_subject = None
current_image_index = 0
auto_navigation = None
is_auto_scrolling = False
is_grayscale_stretching = False

results_file = Path("results.csv")
if not results_file.exists():
    results_df = pd.DataFrame(columns=["Batch", "Subject", "time alive", "time of metamorphosis"])
    results_df.to_csv(results_file, index=False)
else:
    results_df = pd.read_csv(results_file)

# Base folder input
base_folder_label = tk.Label(root, text="Base Folder:")
base_folder_label.pack(pady=5)

base_folder_entry = tk.Entry(root, width=50)
base_folder_entry.insert(0, str(base_folder))
base_folder_entry.pack(pady=5)

base_folder_button = tk.Button(root, text="Set Base Folder", command=update_base_folder)
base_folder_button.pack(pady=5)

# Dropdown menus
batch_var = tk.StringVar()
batch_dropdown = ttk.OptionMenu(root, batch_var, "Select Batch")
batch_dropdown.pack(pady=5)

subject_var = tk.StringVar()
subject_dropdown = tk.OptionMenu(root, subject_var, "Select Subject")
subject_dropdown.pack(pady=5)

# Image display
image_label = tk.Label(root)
image_label.pack(pady=10)

# Grayscale stretching toggle button
graystretch_button = tk.Checkbutton(root, text="Grayscale Stretching", command=toggle_grayscale_stretching)
graystretch_button.place(x=20, y=50)  # Adjusted position

# Image number display
image_number_label = tk.Label(root, text="Image Number: N/A", fg="blue")
image_number_label.place(relx=0.85, rely=0.05, anchor="ne")

# Status label
status_label = tk.Label(root, text="not labeled yet", fg="gray")
status_label.place(relx=0.85, rely=0.1, anchor="ne")

# Feedback label
feedback_label = tk.Label(root, text="", fg="green")
feedback_label.place(relx=0.85, rely=0.15, anchor="ne")

# Error label
error_label = tk.Label(root, text="", fg="red")
error_label.pack(pady=5)

# Key bindings
root.bind("<KeyPress>", on_key_press)

# Initialize the UI
populate_batches()
root.mainloop()
