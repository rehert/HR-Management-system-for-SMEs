import customtkinter as ctk
import csv
import os
import winsound  # Native Windows audio library for notifications
from tkinter import ttk, messagebox
from datetime import datetime

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class HRView(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Zimbabwe Labour Compliance Portal - HR Management Hub")
        self.geometry("700x550")

        # Keep track of how many items we've already seen to prevent spamming sounds
        self.known_request_count = 0

        # --- UI LAYOUT SETUP ---
        self.title_label = ctk.CTkLabel(self, text="📥 HR Pending Leave Approvals Queue", font=("Arial", 20, "bold"))
        self.title_label.pack(pady=15)

        # 📊 SPREADSHEET TABLE GRID (Treeview)
        # Using classic tkinter styling because it's the standard for displaying data tables
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.pack(pady=10, fill="both", expand=True, padx=20)

        # Define Columns matching our database structure
        columns = ("name", "days", "type", "reason", "deduction")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")

        # Set Table Headers
        self.tree.heading("name", text="Employee Name")
        self.tree.heading("days", text="Days")
        self.tree.heading("type", text="Leave Classification")
        self.tree.heading("reason", text="Reason for Leave")
        self.tree.heading("deduction", text="Est. Salary Deduction")

        # Set Column Widths
        self.tree.column("name", width=100, anchor="center")
        self.tree.column("days", width=50, anchor="center")
        self.tree.column("type", width=150, anchor="w")
        self.tree.column("reason", width=200, anchor="w")
        self.tree.column("deduction", width=120, anchor="center")

        self.tree.pack(side="left", fill="both", expand=True)

        # Add a scrollbar to scroll through long lists of requests
        scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # --- OPTIONAL OVERRIDE DELEGATION TOOLS ---
        self.override_frame = ctk.CTkFrame(self)
        self.override_frame.pack(pady=10, fill="x", padx=20)

        self.lbl_delegate = ctk.CTkLabel(self.override_frame, text="Compliance Action: Leave Type Override/Delegation",
                                         font=("Arial", 12, "italic"))
        self.lbl_delegate.pack(pady=2)

        self.dropdown_override = ctk.CTkOptionMenu(
            self.override_frame,
            values=["Keep Original Choice", "Switch to Sick Leave Half-Pay", "Switch to Vacation Without Pay"],
            width=250
        )
        self.dropdown_override.pack(pady=5)

        # --- MANAGEMENT SUBMIT BUTTONS ---
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=15)

        self.btn_approve = ctk.CTkButton(self.btn_frame, text="✅ Approve & Route to Finance",
                                         command=self.approve_selected, fg_color="green", width=220)
        self.btn_approve.pack(side="left", padx=10)

        self.btn_reject = ctk.CTkButton(self.btn_frame, text="❌ Reject Request", command=self.reject_selected,
                                        fg_color="red", width=220)
        self.btn_reject.pack(side="left", padx=10)

        # Start the background "listener loop" to wait for worker submissions in real time
        self.check_for_new_requests()

    def check_for_new_requests(self):
        """Continuously scans the shared data file. Triggers a sound notification if a row appears."""
        if os.path.exists("pending_requests.csv"):
            current_rows = []
            try:
                with open("pending_requests.csv", mode="r") as file:
                    reader = csv.reader(file)
                    next(reader)  # Skip header
                    for row in reader:
                        # Only show items that are still waiting for review
                        if len(row) >= 6 and row[5] == "Pending HR Review":
                            current_rows.append(row)
            except Exception:
                pass  # Prevent crashes if file is open in worker app simultaneously

            # 🔥 THE WHATSAPP ALERT LOGIC 🔥
            if len(current_rows) > self.known_request_count:
                # Play the official Windows system notification sound block
                winsound.PlaySound("SystemNotification", winsound.SND_ALIAS | winsound.SND_ASYNC)
                self.known_request_count = len(current_rows)

                # Clear out old visual table data and repaint table with fresh entries
                for item in self.tree.get_children():
                    self.tree.delete(item)
                for row in current_rows:
                    self.tree.insert("", "end", values=(row[0], row[1], row[2], row[3], row[4]))

        # Run this function again automatically every 3000 milliseconds (3 seconds)
        self.after(3000, self.check_for_new_requests)

    def get_selected_item_data(self):
        """Helper tool to identify which row HR highlighted with their mouse."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required",
                                   "Please click on an active leave request row from the list first.")
            return None
        return self.tree.item(selected[0])['values']

    def update_request_status(self, name, target_type, new_status):
        """Rewrites the central tracking spreadsheet to clear out the item."""
        rows = []
        if os.path.exists("pending_requests.csv"):
            with open("pending_requests.csv", mode="r") as file:
                reader = csv.reader(file)
                header = next(reader)
                for row in reader:
                    # Look for the exact matching row based on name and leave type
                    if row[0] == name and row[2] == target_type and row[5] == "Pending HR Review":
                        row[5] = new_status  # Update the flag status
                    rows.append(row)

            with open("pending_requests.csv", mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(header)
                writer.writerows(rows)

    def approve_selected(self):
        """Processes approvals and locks the data for Finance to read next."""
        data = self.get_selected_item_data()
        if not data: return

        name, days, leave_type, reason, deduction = data
        override_choice = self.dropdown_override.get()

        # Handle statutory overrides according to Sections 14 & 14A
        if override_choice != "Keep Original Choice":
            leave_type = f"Delegated: {override_choice}"

        # 1. Archive the approval status
        self.update_request_status(name, data[2], "Approved")

        # 2. Append directly to our permanent Finance Pipeline database file
        file_exists = os.path.exists("finance_pipeline.csv")
        with open("finance_pipeline.csv", mode="a", newline="") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Name", "Days", "Type", "Deduction", "Approval_Timestamp"])
            writer.writerow([name, days, leave_type, deduction, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

        messagebox.showinfo("Success",
                            f"Leave application for {name} has been processed and successfully routed to Finance.")
        self.known_request_count = 0  # Forces table refresh loop
        self.dropdown_override.set("Keep Original Choice")

    def reject_selected(self):
        """Processes rejections securely."""
        data = self.get_selected_item_data()
        if not data: return

        name = data[0]
        self.update_request_status(name, data[2], "Rejected by HR")
        messagebox.showinfo("Rejected", f"Leave application for {name} was formally rejected.")
        self.known_request_count = 0  # Forces table refresh loop


if __name__ == "__main__":
    app = HRView()
    app.mainloop()
