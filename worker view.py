import customtkinter as ctk
import csv
import os
import shutil
import smtplib
from datetime import datetime
from tkinter import messagebox, filedialog
from email.mime.text import MIMEText

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class WorkerView(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Zimbabwe Labour Compliance Portal - Worker Instance")
        self.geometry("500x720")

        self.employee_name = "Tatenda"
        self.daily_rate = 50.00
        self.selected_file_path = ""  # Stores path of uploaded doctor's note

        self.initialize_databases()
        self.load_and_update_balances()

        # --- UI LAYOUT ---
        self.title_label = ctk.CTkLabel(self, text=f"Welcome back, {self.employee_name}", font=("Arial", 22, "bold"))
        self.title_label.pack(pady=15)

        self.balance_frame = ctk.CTkFrame(self)
        self.balance_frame.pack(pady=10, fill="x", padx=20)

        self.lbl_vacation = ctk.CTkLabel(self.balance_frame,
                                         text=f"📊 Accrued Vacation Leave: {self.vacation_bal:.1f} Days (Max 90)",
                                         font=("Arial", 13))
        self.lbl_vacation.pack(pady=5, anchor="w", padx=15)

        self.lbl_sick = ctk.CTkLabel(self.balance_frame,
                                     text=f"🤒 Paid Sick Leave Balance: {90.0 - self.sick_used:.1f} Days Available",
                                     font=("Arial", 13))
        self.lbl_sick.pack(pady=5, anchor="w", padx=15)

        self.lbl_special = ctk.CTkLabel(self.balance_frame,
                                        text=f"🕊️ Statutory Special Leave: {12.0 - self.special_used:.1f} Days Remaining",
                                        font=("Arial", 13))
        self.lbl_special.pack(pady=5, anchor="w", padx=15)

        self.form_label = ctk.CTkLabel(self, text="Submit a New Leave Request", font=("Arial", 14, "bold"))
        self.form_label.pack(pady=15)

        self.entry_days = ctk.CTkEntry(self, placeholder_text="Number of Days Requested", width=350)
        self.entry_days.pack(pady=10)

        self.dropdown_type = ctk.CTkOptionMenu(
            self,
            values=["Vacation Leave", "Sick Leave (Requires Doctor Note)", "Special Leave (Section 14B)"],
            width=350,
            command=self.toggle_upload_button
        )
        self.dropdown_type.pack(pady=10)

        # 📄 FILE UPLOAD PANEL (Hidden by default, unlocks for Sick Leave)
        self.btn_upload = ctk.CTkButton(self, text="📷 Upload Doctor's Note (Image)", command=self.upload_document,
                                        fg_color="purple", width=350)
        self.lbl_file_status = ctk.CTkLabel(self, text="No medical certificate selected.", font=("Arial", 11, "italic"),
                                            text_color="gray")

        self.txt_reason = ctk.CTkTextbox(self, width=350, height=80)
        self.txt_reason.insert("0.0", "Type your reason for leave here...")
        self.txt_reason.pack(pady=10)

        self.btn_calculate = ctk.CTkButton(self, text="Calculate Financial Terms", command=self.calculate_legal_terms,
                                           width=350, fg_color="darkblue")
        self.btn_calculate.pack(pady=15)

        self.lbl_status = ctk.CTkLabel(self, text="", font=("Arial", 12), wraplength=420)
        self.lbl_status.pack(pady=5)

        # Check if HR left any processed status updates in the system file
        self.check_for_hr_feedback()

    def toggle_upload_button(self, choice):
        """Displays the upload button dynamically when Sick Leave is chosen."""
        if "Sick Leave" in choice:
            self.btn_upload.pack(pady=5, before=self.txt_reason)
            self.lbl_file_status.pack(pady=2, before=self.txt_reason)
        else:
            self.btn_upload.pack_forget()
            self.lbl_file_status.pack_forget()
            self.selected_file_path = ""

    def upload_document(self):
        """Launches file explorer allowing worker to pick a file image."""
        file_path = filedialog.askopenfilename(
            title="Select Medical Certificate",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")]
        )
        if file_path:
            self.selected_file_path = file_path
            filename = os.path.basename(file_path)
            self.lbl_file_status.configure(text=f"✅ Selected: {filename}", text_color="green")

    def initialize_databases(self):
        if not os.path.exists("uploaded_notes"):
            os.makedirs("uploaded_notes")  # Generates a storage system folder
        if not os.path.exists("employee_balances.csv"):
            with open("employee_balances.csv", mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(
                    ["Name", "Vacation_Balance", "Sick_Days_Used", "Special_Days_Used", "Last_Accrual_Date"])
                writer.writerow(["Tatenda", "14.0", "0.0", "0.0", datetime.now().strftime("%Y-%m-%d")])
        if not os.path.exists("pending_requests.csv"):
            with open("pending_requests.csv", mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(
                    ["Name", "Days", "Type", "Reason", "Deduction", "Status", "Timestamp", "Note_Path", "HR_Feedback"])

    def load_and_update_balances(self):
        target_row = None
        with open("employee_balances.csv", mode="r") as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                if row[0] == self.employee_name: target_row = row
        self.vacation_bal = float(target_row[1])
        self.sick_used = float(target_row[2])
        self.special_used = float(target_row[3])

    def check_for_hr_feedback(self):
        """Scans data file to see if HR altered their application status state."""
        if os.path.exists("pending_requests.csv"):
            with open("pending_requests.csv", mode="r") as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    if row[0] == self.employee_name and row[5] in ["Approved", "Rejected by HR", "Delegated Overview"]:
                        status = row[5]
                        feedback = row[8] if len(row) >= 9 else "None provided."
                        messagebox.showinfo("⚠️ HR Decision Alert",
                                            f"Your leave request has been processed!\n\nStatus: {status}\nHR Remarks: {feedback}")
                        break

    def send_initial_hr_alert(self, days, leave_type):
        """Sends an instant automated email warning to HR when worker clicks submit."""
        # ⚠️ ENTER WORKING GMAIL CREDENTIALS HERE:
        sender_email = "YOUR_REAL_GMAIL@gmail.com"
        app_password = "YOUR_16_CHARACTER_APP_PASSWORD"
        hr_email = "YOUR_REAL_GMAIL@gmail.com"  # Emulating HR inbox locally

        body = f"Hello HR Team,\n\nEmployee '{self.employee_name}' has formally submitted a digital request for {days} days of {leave_type}.\n\nPlease boot up your HR Dashboard View to approve or reject this request."
        msg = MIMEText(body)
        msg['Subject'] = f"📥 New Leave Request Submitted: {self.employee_name}"
        msg['From'] = sender_email
        msg['To'] = hr_email

        try:
            server = smtplib.SMTP('://gmail.com', 587)
            server.starttls()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, [hr_email], msg.as_string())
            server.quit()
            print("[ALERT LOG] HR alerted via email successfully.")
        except Exception as e:
            print(f"[ALERT LOG] Failed to email HR: {e}")

    def calculate_legal_terms(self):
        try:
            requested_days = float(self.entry_days.get())
            if requested_days <= 0: raise ValueError
        except ValueError:
            self.lbl_status.configure(text="❌ Invalid Input: Enter a valid positive number.", text_color="red")
            return

        leave_type = self.dropdown_type.get()
        reason = self.txt_reason.get("0.0", "end").strip()
        deduction = 0.0
        saved_note_dest = "None"

        # Force medical note compliance check based on Section 14
        if "Sick Leave" in leave_type and not self.selected_file_path:
            messagebox.showerror("Compliance Error",
                                 "Under Section 14(2) of the Labour Act, Sick Leave requests must be supported by a doctor's medical certificate image file.")
            return

        if leave_type == "Vacation Leave" and requested_days > self.vacation_bal:
            deduction = (requested_days - self.vacation_bal) * self.daily_rate
        elif "Sick Leave" in leave_type and (self.sick_used + requested_days) > 90.0:
            deduction = ((self.sick_used + requested_days) - 90.0) * (self.daily_rate * 0.5)

        msg_box = f"Financial Summary:\n• Estimated Pay Cut: ${deduction:.2f} USD\n\nForward this to HR?"
        if messagebox.askyesno("Confirm Terms", msg_box):
            # Process and duplicate uploaded image file to system archive storage
            if self.selected_file_path:
                ext = os.path.splitext(self.selected_file_path)[1]
                saved_note_dest = f"uploaded_notes/{self.employee_name}_{datetime.now().strftime('%M%S')}{ext}"
                shutil.copy(self.selected_file_path, saved_note_dest)

            with open("pending_requests.csv", mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(
                    [self.employee_name, requested_days, leave_type, reason, f"${deduction:.2f}", "Pending HR Review",
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S"), saved_note_dest, ""])

            # Fire email warning to HR immediately
            self.send_initial_hr_alert(requested_days, leave_type)

            self.lbl_status.configure(text="✅ Submitted and HR alerted via email!", text_color="green")
            self.entry_days.delete(0, 'end')
            self.lbl_file_status.configure(text="No medical certificate selected.", text_color="gray")
            self.selected_file_path = ""


if __name__ == "__main__":
    app = WorkerView()
    app.mainloop()

