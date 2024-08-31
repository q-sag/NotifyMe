import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import threading
import time
import os
import json
import keyboard
from pystray import Icon as TrayIcon, Menu as TrayMenu, MenuItem as TrayMenuItem
from PIL import Image, ImageDraw
from win10toast import ToastNotifier
import pygame

# Initialize the pygame mixer
pygame.mixer.init()

# Directory where notification sounds are stored
SOUND_DIR = "notification_sounds"
DEFAULT_SOUND = "default.mp3"
CACHE_FILE = "notifications_cache.json"

# Initialize the toaster
toaster = ToastNotifier()

# Notification list to keep track of scheduled notifications
notifications = []

# Load notifications from cache
def load_notifications_from_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            loaded_notifications = json.load(file)
            for notification in loaded_notifications:
                notification['time'] = datetime.strptime(notification['time'], "%Y-%m-%d %H:%M")
            return loaded_notifications
    return []

# Save notifications to cache
def save_notifications_to_cache():
    with open(CACHE_FILE, "w") as file:
        notifications_to_save = [
            {**notification, 'time': notification['time'].strftime("%Y-%m-%d %H:%M")}
            for notification in notifications
        ]
        json.dump(notifications_to_save, file)

# Function to play a sound
def play_sound(sound_file):
    sound_path = os.path.join(SOUND_DIR, sound_file)
    if os.path.exists(sound_path):
        pygame.mixer.music.load(sound_path)
        pygame.mixer.music.play()
    else:
        messagebox.showerror("Error", f"Sound file {sound_file} not found.")

# Function to check and trigger notifications
def check_notifications():
    while True:
        current_time = datetime.now()
        for notification_data in notifications[:]:
            if notification_data['time'] <= current_time:
                play_sound(notification_data['sound'])
                toaster.show_toast(
                    title=notification_data['label'],
                    msg=notification_data['note'],
                    icon_path=None,  # Add an icon path if desired
                    duration=10,
                    threaded=True,
                    # no_sound=True ensures no default Windows sound
                    # However, win10toast by default has no sound
                )
                if notification_data['recurring']:
                    notification_data['time'] += timedelta(
                        weeks=notification_data['intervals'].get('weeks', 0),
                        days=notification_data['intervals'].get('days', 0),
                        hours=notification_data['intervals'].get('hours', 0),
                        minutes=notification_data['intervals'].get('minutes', 0)
                    )
                    save_notifications_to_cache()
                else:
                    notifications.remove(notification_data)
                    save_notifications_to_cache()
        time.sleep(60)  # Check every minute

# Function to update the active notifications tab
def update_active_notifications_tab(tree):
    for i in tree.get_children():
        tree.delete(i)
    for idx, notification_data in enumerate(notifications):
        tree.insert("", "end", iid=idx, values=(
            notification_data['time'].strftime("%Y-%m-%d %H:%M"),
            notification_data['label'],
            notification_data['note'],
            "Yes" if notification_data['recurring'] else "No"
        ))

# Function to handle scheduling a notification
def schedule_notification():
    try:
        notification_time = datetime.strptime(time_entry.get(), "%Y-%m-%d %H:%M")
        label = label_entry.get()
        note = note_entry.get()
        sound = sound_var.get()
        recurring = recurring_var.get()
        intervals = {}
        if recurring:
            intervals['weeks'] = int(weeks_entry.get() or 0)
            intervals['days'] = int(days_entry.get() or 0)
            intervals['hours'] = int(hours_entry.get() or 0)
            intervals['minutes'] = int(minutes_entry.get() or 0)
            deadline = datetime.strptime(deadline_entry.get(), "%Y-%m-%d %H:%M")
            if notification_time >= deadline:
                messagebox.showerror("Error", "Notification time must be before deadline.")
                return
        notifications.append({
            'time': notification_time,
            'label': label,
            'note': note,
            'sound': sound,
            'recurring': recurring,
            'intervals': intervals if recurring else None
        })
        save_notifications_to_cache()
        update_active_notifications_tab(tree)
        messagebox.showinfo("Success", "Notification scheduled successfully.")
    except ValueError:
        messagebox.showerror("Error", "Invalid input. Please check your entries.")

# Function to create the system tray icon
def setup_tray_icon():
    def on_quit(icon, item):
        save_notifications_to_cache()
        icon.stop()
        root.quit()

    def show_app(icon, item):
        root.deiconify()

    image = Image.new('RGB', (64, 64), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 64, 64], fill="blue")
    draw.text((10, 20), "N", fill="white")

    icon = TrayIcon("Notifier", image, menu=TrayMenu(TrayMenuItem("Show", show_app), TrayMenuItem("Quit", on_quit)))
    icon.run_detached()

# Function to handle editing a notification
def edit_notification(index):
    notification_data = notifications[index]

    def save_edits():
        try:
            notification_time = datetime.strptime(time_entry.get(), "%Y-%m-%d %H:%M")
            label = label_entry.get()
            note = note_entry.get()
            sound = sound_var.get()
            recurring = recurring_var.get()
            intervals = {}
            if recurring:
                intervals['weeks'] = int(weeks_entry.get() or 0)
                intervals['days'] = int(days_entry.get() or 0)
                intervals['hours'] = int(hours_entry.get() or 0)
                intervals['minutes'] = int(minutes_entry.get() or 0)
                deadline = datetime.strptime(deadline_entry.get(), "%Y-%m-%d %H:%M")
                if notification_time >= deadline:
                    messagebox.showerror("Error", "Notification time must be before deadline.")
                    return
            notification_data.update({
                'time': notification_time,
                'label': label,
                'note': note,
                'sound': sound,
                'recurring': recurring,
                'intervals': intervals if recurring else None
            })
            save_notifications_to_cache()
            update_active_notifications_tab(tree)
            messagebox.showinfo("Success", "Notification updated successfully.")
            edit_window.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid input. Please check your entries.")

    edit_window = tk.Toplevel(root)
    edit_window.title("Edit Notification")
    edit_window.configure(bg='#1e1e1e')  # Dark background color

    ttk.Label(edit_window, text="Time:").grid(row=0, column=0, sticky='e', padx=5, pady=5)
    time_entry = ttk.Entry(edit_window)
    time_entry.insert(0, notification_data['time'].strftime("%Y-%m-%d %H:%M"))
    time_entry.grid(row=0, column=1, padx=5, pady=5)

    ttk.Label(edit_window, text="Notification Label:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
    label_entry = ttk.Entry(edit_window)
    label_entry.insert(0, notification_data['label'])
    label_entry.grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(edit_window, text="Notification Note:").grid(row=2, column=0, sticky='e', padx=5, pady=5)
    note_entry = ttk.Entry(edit_window)
    note_entry.insert(0, notification_data['note'])
    note_entry.grid(row=2, column=1, padx=5, pady=5)

    sound_var = tk.StringVar(value=notification_data['sound'])
    ttk.Label(edit_window, text="Notification Sound:").grid(row=3, column=0, sticky='e', padx=5, pady=5)
    sound_menu = ttk.Combobox(edit_window, textvariable=sound_var)
    sound_menu['values'] = [file for file in os.listdir(SOUND_DIR) if file.endswith(".mp3")]
    sound_menu.grid(row=3, column=1, padx=5, pady=5)

    def play_selected_sound():
        play_sound(sound_var.get())

    play_button = ttk.Button(edit_window, text="Play Sound", command=play_selected_sound)
    play_button.grid(row=3, column=2, padx=5, pady=5)

    recurring_var = tk.BooleanVar(value=notification_data['recurring'])
    ttk.Checkbutton(edit_window, text="Recurring", variable=recurring_var).grid(row=4, columnspan=2, sticky='w', padx=5, pady=5)

    def toggle_recurring():
        state = tk.NORMAL if recurring_var.get() else tk.DISABLED
        for widget in recurring_widgets:
            widget.config(state=state)

    recurring_widgets = []

    ttk.Label(edit_window, text="Weeks:").grid(row=5, column=0, sticky='e', padx=5, pady=5)
    weeks_entry = ttk.Entry(edit_window)
    weeks_entry.insert(0, notification_data['intervals'].get('weeks', 0) if notification_data['recurring'] else '')
    weeks_entry.grid(row=5, column=1, padx=5, pady=5)
    recurring_widgets.append(weeks_entry)

    ttk.Label(edit_window, text="Days:").grid(row=6, column=0, sticky='e', padx=5, pady=5)
    days_entry = ttk.Entry(edit_window)
    days_entry.insert(0, notification_data['intervals'].get('days', 0) if notification_data['recurring'] else '')
    days_entry.grid(row=6, column=1, padx=5, pady=5)
    recurring_widgets.append(days_entry)

    ttk.Label(edit_window, text="Hours:").grid(row=7, column=0, sticky='e', padx=5, pady=5)
    hours_entry = ttk.Entry(edit_window)
    hours_entry.insert(0, notification_data['intervals'].get('hours', 0) if notification_data['recurring'] else '')
    hours_entry.grid(row=7, column=1, padx=5, pady=5)
    recurring_widgets.append(hours_entry)

    ttk.Label(edit_window, text="Minutes:").grid(row=8, column=0, sticky='e', padx=5, pady=5)
    minutes_entry = ttk.Entry(edit_window)
    minutes_entry.insert(0, notification_data['intervals'].get('minutes', 0) if notification_data['recurring'] else '')
    minutes_entry.grid(row=8, column=1, padx=5, pady=5)
    recurring_widgets.append(minutes_entry)

    ttk.Label(edit_window, text="Deadline (YYYY-MM-DD HH:MM):").grid(row=9, column=0, sticky='e', padx=5, pady=5)
    deadline_entry = ttk.Entry(edit_window)
    deadline_entry.grid(row=9, column=1, padx=5, pady=5)
    recurring_widgets.append(deadline_entry)

    for widget in recurring_widgets:
        widget.config(state=tk.NORMAL if notification_data['recurring'] else tk.DISABLED)

    recurring_var.trace_add('write', lambda *args: toggle_recurring())

    save_button = ttk.Button(edit_window, text="Save", command=save_edits)
    save_button.grid(row=10, columnspan=2, padx=5, pady=5)

    edit_window.mainloop()

# Function to handle canceling a notification
def cancel_notification(index):
    del notifications[index]
    save_notifications_to_cache()
    update_active_notifications_tab(tree)
    messagebox.showinfo("Success", "Notification canceled successfully.")

# Create the main application window
root = tk.Tk()
root.title("Notification Manager")
root.configure(bg='#1e1e1e')  # Dark background color

# Set window transparency
root.attributes('-alpha', 0.9)  # 90% opacity

# Custom style for dark theme
style = ttk.Style()
style.theme_use('default')
style.configure('TNotebook', background='#1e1e1e', borderwidth=0)
style.configure('TNotebook.Tab', background='#2d2d2d', foreground='white', padding=[10, 5])
style.map('TNotebook.Tab', background=[('selected', '#3c3c3c')])
style.configure('TFrame', background='#1e1e1e')
style.configure('TLabel', background='#1e1e1e', foreground='white', font=('Consolas', 10))
style.configure('TEntry', fieldbackground='#2d2d2d', foreground='white', font=('Consolas', 10))
style.configure('TButton', background='#3c3c3c', foreground='white', font=('Consolas', 10))
style.map('TButton', background=[('active', '#4c4c4c')])
style.configure('Treeview', background='#2d2d2d', foreground='white', fieldbackground='#2d2d2d', font=('Consolas', 10))
style.configure('Treeview.Heading', background='#3c3c3c', foreground='white', font=('Consolas', 10, 'bold'))
style.map('Treeview', background=[('selected', '#4c4c4c')])

# Minimize to system tray instead of closing
def hide_window():
    root.withdraw()

root.protocol("WM_DELETE_WINDOW", hide_window)

# Create a notebook widget to hold tabs
notebook = ttk.Notebook(root)

# Create the scheduling tab
schedule_tab = ttk.Frame(notebook)
notebook.add(schedule_tab, text="Schedule Notification")

# Create the active notifications tab
active_notifications_tab = ttk.Frame(notebook)
notebook.add(active_notifications_tab, text="Active Notifications")

# Pack the notebook into the main window
notebook.pack(expand=True, fill='both', padx=10, pady=10)

# Schedule Notification Interface in the "Schedule Notification" tab
current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
ttk.Label(schedule_tab, text="Time:").grid(row=0, column=0, sticky='e', padx=5, pady=5)
time_entry = ttk.Entry(schedule_tab)
time_entry.insert(0, current_time)
time_entry.grid(row=0, column=1, padx=5, pady=5)

ttk.Label(schedule_tab, text="Notification Label:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
label_entry = ttk.Entry(schedule_tab)
label_entry.grid(row=1, column=1, padx=5, pady=5)

ttk.Label(schedule_tab, text="Notification Note:").grid(row=2, column=0, sticky='e', padx=5, pady=5)
note_entry = ttk.Entry(schedule_tab)
note_entry.grid(row=2, column=1, padx=5, pady=5)

sound_var = tk.StringVar(value=DEFAULT_SOUND)
ttk.Label(schedule_tab, text="Notification Sound:").grid(row=3, column=0, sticky='e', padx=5, pady=5)
sound_menu = ttk.Combobox(schedule_tab, textvariable=sound_var)
sound_menu['values'] = [file for file in os.listdir(SOUND_DIR) if file.endswith(".mp3")]
sound_menu.grid(row=3, column=1, padx=5, pady=5)

def play_selected_sound():
    play_sound(sound_var.get())

play_button = ttk.Button(schedule_tab, text="Play Sound", command=play_selected_sound)
play_button.grid(row=3, column=2, padx=5, pady=5)

recurring_var = tk.BooleanVar(value=False)
ttk.Checkbutton(schedule_tab, text="Recurring", variable=recurring_var).grid(row=4, columnspan=2, sticky='w', padx=5, pady=5)

def toggle_recurring():
    state = tk.NORMAL if recurring_var.get() else tk.DISABLED
    for widget in recurring_widgets:
        widget.config(state=state)

recurring_widgets = []

ttk.Label(schedule_tab, text="Weeks:").grid(row=5, column=0, sticky='e', padx=5, pady=5)
weeks_entry = ttk.Entry(schedule_tab)
weeks_entry.grid(row=5, column=1, padx=5, pady=5)
recurring_widgets.append(weeks_entry)

ttk.Label(schedule_tab, text="Days:").grid(row=6, column=0, sticky='e', padx=5, pady=5)
days_entry = ttk.Entry(schedule_tab)
days_entry.grid(row=6, column=1, padx=5, pady=5)
recurring_widgets.append(days_entry)

ttk.Label(schedule_tab, text="Hours:").grid(row=7, column=0, sticky='e', padx=5, pady=5)
hours_entry = ttk.Entry(schedule_tab)
hours_entry.grid(row=7, column=1, padx=5, pady=5)
recurring_widgets.append(hours_entry)

ttk.Label(schedule_tab, text="Minutes:").grid(row=8, column=0, sticky='e', padx=5, pady=5)
minutes_entry = ttk.Entry(schedule_tab)
minutes_entry.grid(row=8, column=1, padx=5, pady=5)
recurring_widgets.append(minutes_entry)

ttk.Label(schedule_tab, text="Deadline (YYYY-MM-DD HH:MM):").grid(row=9, column=0, sticky='e', padx=5, pady=5)
deadline_entry = ttk.Entry(schedule_tab)
deadline_entry.grid(row=9, column=1, padx=5, pady=5)
recurring_widgets.append(deadline_entry)

for widget in recurring_widgets:
    widget.config(state=tk.DISABLED)

recurring_var.trace_add('write', lambda *args: toggle_recurring())

schedule_button = ttk.Button(schedule_tab, text="Schedule Notification", command=schedule_notification)
schedule_button.grid(row=10, columnspan=2, padx=5, pady=5)

# Create the treeview for active notifications
tree = ttk.Treeview(active_notifications_tab, columns=("Time", "Label", "Note", "Recurring"), show='headings')
tree.heading("Time", text="Time")
tree.heading("Label", text="Label")
tree.heading("Note", text="Note")
tree.heading("Recurring", text="Recurring")
tree.pack(expand=True, fill='both', padx=10, pady=10)

# Add buttons for editing and canceling notifications
def on_tree_select(event):
    selected_item = tree.selection()
    if selected_item:
        index = int(selected_item[0])
        edit_button.config(command=lambda: edit_notification(index))
        cancel_button.config(command=lambda: cancel_notification(index))

edit_button = ttk.Button(active_notifications_tab, text="Edit", command=lambda: None)
edit_button.pack(side='left', padx=5, pady=5)

cancel_button = ttk.Button(active_notifications_tab, text="Cancel", command=lambda: None)
cancel_button.pack(side='left', padx=5, pady=5)

tree.bind("<<TreeviewSelect>>", on_tree_select)

# Load cached notifications and update the treeview
notifications = load_notifications_from_cache()
update_active_notifications_tab(tree)

# Start background threads for checking notifications and setting up the tray icon
notification_thread = threading.Thread(target=check_notifications, daemon=True)
notification_thread.start()

tray_icon_thread = threading.Thread(target=setup_tray_icon, daemon=True)
tray_icon_thread.start()

# Set up the hotkey to open the notification window
keyboard.add_hotkey('ctrl+shift+|', lambda: root.deiconify())

# Run the main application loop
root.mainloop()
