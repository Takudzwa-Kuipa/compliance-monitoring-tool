# import sqlite3
# import os
# from datetime import datetime
#
#
# # ---------------------------------------------------
# # Database Connection
# # ---------------------------------------------------
#
# conn = sqlite3.connect("compliance.db")
# print("Database connected successfully")
# conn.close()
#
#
# # ---------------------------------------------------
# # Create Tables
# # ---------------------------------------------------
#
# conn = sqlite3.connect("compliance.db")
# cursor = conn.cursor()
#
# # Control Table
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS Control (
#     Control_ID INTEGER PRIMARY KEY AUTOINCREMENT,
#     Framework_ID INTEGER,
#     Risk_ID INTEGER,
#     Frequency TEXT,
#     Requirement_Text TEXT
# )
# """)
#
# # Evidence Table
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS Evidence_Store (
#     Evidence_ID INTEGER PRIMARY KEY AUTOINCREMENT,
#     Task_ID INTEGER,
#     File_Path TEXT,
#     Upload_Date TEXT,
#     Uploaded_By TEXT
# )
# """)
#
# # Audit Log Table
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS Audit_Log (
#     Audit_ID INTEGER PRIMARY KEY AUTOINCREMENT,
#     User_ID TEXT,
#     Action_Type TEXT,
#     Timestamp TEXT,
#     Old_Value TEXT,
#     New_Value TEXT
# )
# """)
#
# # User Table
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS User (
#     User_ID INTEGER PRIMARY KEY AUTOINCREMENT,
#     Username TEXT,
#     Department TEXT
# )
# """)
#
# # Task Table
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS Task (
#     Task_ID INTEGER PRIMARY KEY AUTOINCREMENT,
#     User_ID INTEGER,
#     Control_ID INTEGER,
#     Status TEXT
# )
# """)
#
# print("All tables created successfully")
#
# conn.commit()
# conn.close()
#
#
# # ---------------------------------------------------
# # Audit Logging
# # ---------------------------------------------------
#
# def log_action(user, action, old_value, new_value):
#
#     conn = sqlite3.connect("compliance.db")
#     cursor = conn.cursor()
#
#     cursor.execute("""
#     INSERT INTO Audit_Log (User_ID, Action_Type, Timestamp, Old_Value, New_Value)
#     VALUES (?, ?, ?, ?, ?)
#     """, (
#         user,
#         action,
#         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#         str(old_value),
#         str(new_value)
#     ))
#
#     conn.commit()
#     conn.close()
#
#     print("Audit record created")
#
#
# # ---------------------------------------------------
# # Add Control
# # ---------------------------------------------------
#
# def add_control(framework_id, risk_id, frequency, requirement):
#
#     conn = sqlite3.connect("compliance.db")
#     cursor = conn.cursor()
#
#     cursor.execute("""
#     INSERT INTO Control (Framework_ID, Risk_ID, Frequency, Requirement_Text)
#     VALUES (?, ?, ?, ?)
#     """, (framework_id, risk_id, frequency, requirement))
#
#     conn.commit()
#     conn.close()
#
#     print("Control added successfully")
#
#     log_action("Admin", "INSERT_CONTROL", None, requirement)
#
#
# # ---------------------------------------------------
# # Create Task
# # ---------------------------------------------------
#
# def create_task(user_id, control_id, status):
#
#     conn = sqlite3.connect("compliance.db")
#     cursor = conn.cursor()
#
#     cursor.execute("""
#     INSERT INTO Task (User_ID, Control_ID, Status)
#     VALUES (?, ?, ?)
#     """, (user_id, control_id, status))
#
#     conn.commit()
#     conn.close()
#
#     print("Task created")
#
#     log_action("Admin", "CREATE_TASK", None, f"User {user_id} → Control {control_id}")
#
#
# # ---------------------------------------------------
# # Upload Evidence
# # ---------------------------------------------------
#
# def upload_evidence(task_id, filename, user):
#
#     filepath = os.path.join("evidence_files", filename)
#
#     conn = sqlite3.connect("compliance.db")
#     cursor = conn.cursor()
#
#     cursor.execute("""
#     INSERT INTO Evidence_Store (Task_ID, File_Path, Upload_Date, Uploaded_By)
#     VALUES (?, ?, ?, ?)
#     """, (
#         task_id,
#         filepath,
#         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#         user
#     ))
#
#     conn.commit()
#     conn.close()
#
#     print("Evidence uploaded successfully")
#
#     log_action(user, "UPLOAD_EVIDENCE", None, filename)
#
#
# # ---------------------------------------------------
# # Dashboard
# # ---------------------------------------------------
#
# def dashboard():
#
#     conn = sqlite3.connect("compliance.db")
#     cursor = conn.cursor()
#
#     cursor.execute("SELECT COUNT(*) FROM Control")
#     controls = cursor.fetchone()[0]
#
#     cursor.execute("SELECT COUNT(*) FROM Evidence_Store")
#     evidence = cursor.fetchone()[0]
#
#     cursor.execute("SELECT COUNT(*) FROM Task")
#     tasks = cursor.fetchone()[0]
#
#     cursor.execute("SELECT COUNT(*) FROM Audit_Log")
#     logs = cursor.fetchone()[0]
#
#     print("\n==============================")
#     print("   COMPLIANCE DASHBOARD")
#     print("==============================")
#     print(f"Total Controls       : {controls}")
#     print(f"Total Evidence       : {evidence}")
#     print(f"Total Tasks          : {tasks}")
#     print(f"Audit Log Entries    : {logs}")
#     print("==============================")
#
#     conn.close()
#
#
# # ---------------------------------------------------
# # View Audit Logs
# # ---------------------------------------------------
#
# def view_audit_logs():
#
#     conn = sqlite3.connect("compliance.db")
#     cursor = conn.cursor()
#
#     cursor.execute("SELECT * FROM Audit_Log")
#     rows = cursor.fetchall()
#
#     print("\nAudit Logs:")
#     for row in rows:
#         print(row)
#
#     conn.close()
#
#
# # ---------------------------------------------------
# # Menu System (Main Application)
# # ---------------------------------------------------
#
# def menu():
#
#     while True:
#         print("\n==== COMPLIANCE SYSTEM ====")
#         print("1. Add Control")
#         print("2. Create Task")
#         print("3. Upload Evidence")
#         print("4. View Dashboard")
#         print("5. View Audit Logs")
#         print("6. Exit")
#
#         choice = input("Select option: ")
#
#         if choice == "1":
#             add_control(1, 1, "Monthly", "Encryption policy")
#
#         elif choice == "2":
#             create_task(1, 1, "Pending")
#
#         elif choice == "3":
#             upload_evidence(1, "server_encryption_report.pdf", "Analyst")
#
#         elif choice == "4":
#             dashboard()
#
#         elif choice == "5":
#             view_audit_logs()
#
#         elif choice == "6":
#             print("Exiting system...")
#             break
#
#         else:
#             print("Invalid option")
#
#
# # ---------------------------------------------------
# # RUN SYSTEM
# # ---------------------------------------------------
#
# menu()