import streamlit as st
import re
from datetime import datetime
import sqlite3
from streamlit_ace import st_ace
from streamlit_monaco import st_monaco
import subprocess
import sys

# Initialize database
def init_db():
    conn = sqlite3.connect('student_projects.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, name TEXT, email TEXT, institution TEXT, 
                  role TEXT, join_date TEXT, profile_pic TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS projects
                 (id INTEGER PRIMARY KEY, title TEXT, description TEXT, 
                  created_by INTEGER, created_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS project_members
                 (project_id INTEGER, user_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY, project_id INTEGER, sender_id INTEGER,
                  message TEXT, sent_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS project_code (project_id INTEGER PRIMARY KEY, code TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS project_chat (project_id INTEGER, sender_id INTEGER, message TEXT, sent_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, project_id INTEGER, filename TEXT, uploader_id INTEGER, upload_date TEXT)''')
    try:
        c.execute('ALTER TABLE users ADD COLUMN profile_pic TEXT')
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def is_edu_email(email):
    # Check if email ends with .edu or similar educational domains
    edu_domains = ['.edu', '.ac.', '.edu.']
    return any(domain in email.lower() for domain in edu_domains)

def user_profile_card(name, role, projects_involved, lines_of_code):
    initials = "".join([n[0] for n in name.split()][:2]).upper()
    card_html = f"""
    <div style='background:white;border-radius:12px;box-shadow:0 2px 8px #eee;padding:20px 24px 16px 24px;width:270px;display:inline-block;margin:10px;'>
        <div style='display:flex;align-items:center;'>
            <div style='background:#1976d2;color:white;border-radius:50%;width:48px;height:48px;display:flex;align-items:center;justify-content:center;font-size:1.5em;font-weight:bold;margin-right:12px;'>
                {initials}
            </div>
            <div>
                <div style='font-weight:600;font-size:1.1em;color:#000;'>{name}</div>
                <div style='color:#000;font-size:0.95em;'>{role}</div>
            </div>
        </div>
        <hr style='margin:16px 0 10px 0;'>
        <div style='color:#000;font-size:1em;margin-bottom:8px;'><b>Your Stats</b></div>
        <div style='display:flex;justify-content:space-between;font-size:1.08em;font-weight:500;margin-bottom:4px;color:#000;'>
            <div style='color:#000;'>Projects Involved</div><div style='color:#000;'>{projects_involved}</div>
        </div>
        <div style='display:flex;justify-content:space-between;font-size:1.08em;font-weight:500;color:#000;'>
            <div style='color:#000;'>Total Lines of Code</div><div style='color:#000;'>{lines_of_code}</div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def main():
    st.title("Student Project Collaboration Platform (Prototype)")
    st.sidebar.image("https://img.icons8.com/color/96/000000/student-center.png", width=100)
    
    # Initialize database
    init_db()
    
    # Session state for login
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None

    # Always fetch user info if logged in
    if st.session_state.user_id is not None:
        conn = sqlite3.connect('student_projects.db')
        c = conn.cursor()
        user = c.execute("SELECT name, role FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
        conn.close()
        if user:
            st.session_state.user_info = {'name': user[0], 'role': user[1]}
        else:
            st.session_state.user_info = None
    else:
        st.session_state.user_info = None

    # Show profile in the top right if logged in
    if st.session_state.user_info:
        col1, col2 = st.columns([6, 1])
        with col2:
            name = st.session_state.user_info['name']
            role = st.session_state.user_info['role']
            badge_color = "#4CAF50" if role.lower() == "student" else "#2196F3"
            st.markdown(
                f"<div style='text-align:right;'>"
                f"<b>{name}</b> <span style='background-color:{badge_color};color:white;padding:2px 8px;border-radius:8px;font-size:0.9em;'>{role}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

    # Sidebar for navigation
    if st.session_state.user_id is None:
        menu = "Login/Register"
    else:
        menu_options = ["Create Project", "Browse Projects", "My Projects", "Messages", "Community", "Logout", "Profile"]
        menu = st.sidebar.selectbox("Menu", menu_options)
    
    if menu == "Login/Register":
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("Login")
            with st.form("login_form"):
                login_email = st.text_input("Email")
                if st.form_submit_button("Login"):
                    conn = sqlite3.connect('student_projects.db')
                    c = conn.cursor()
                    user = c.execute("SELECT id FROM users WHERE email=?", (login_email,)).fetchone()
                    conn.close()
                    if user:
                        st.session_state.user_id = user[0]
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error("User not found")
        
        with col2:
            st.header("Register")
            with st.form("registration_form"):
                name = st.text_input("Full Name")
                email = st.text_input("Educational Email")
                institution = st.text_input("Institution Name")
                role = st.selectbox("Role", ["Student", "Teacher"])
                
                if st.form_submit_button("Register"):
                    if not is_edu_email(email):
                        st.error("Please use an educational email address")
                    else:
                        conn = sqlite3.connect('student_projects.db')
                        c = conn.cursor()
                        c.execute("INSERT INTO users (name, email, institution, role, join_date) VALUES (?, ?, ?, ?, ?)",
                                (name, email, institution, role, datetime.now().strftime("%Y-%m-%d")))
                        conn.commit()
                        conn.close()
                        st.success("Registration successful! Please login.")

    elif menu == "Create Project":
        st.header("Create New Project")
        
        with st.form("project_form"):
            title = st.text_input("Project Title")
            description = st.text_area("Project Description")
            skills_needed = st.multiselect("Skills Needed", 
                ["Programming", "Design", "Writing", "Research", "Data Analysis"])
            max_members = st.number_input("Maximum Team Members", min_value=2, value=5)
            
            if st.form_submit_button("Create Project"):
                conn = sqlite3.connect('student_projects.db')
                c = conn.cursor()
                c.execute("INSERT INTO projects (title, description, created_by, created_date) VALUES (?, ?, ?, ?)",
                         (title, description, st.session_state.user_id, datetime.now().strftime("%Y-%m-%d")))
                project_id = c.lastrowid
                # Add creator as first member
                c.execute("INSERT INTO project_members (project_id, user_id) VALUES (?, ?)",
                         (project_id, st.session_state.user_id))
                conn.commit()
                conn.close()
                st.success("Project created successfully!")

    elif menu == "Browse Projects":
        st.header("Available Projects")
        
        # Search and filter
        search = st.text_input("Search projects")
        
        conn = sqlite3.connect('student_projects.db')
        c = conn.cursor()
        if search:
            projects = c.execute("SELECT * FROM projects WHERE title LIKE ? OR description LIKE ?",
                               (f"%{search}%", f"%{search}%")).fetchall()
        else:
            projects = c.execute("SELECT * FROM projects").fetchall()
        
        for project in projects:
            with st.expander(f"Project: {project[1]}"):
                st.write(f"Description: {project[2]}")
                creator = c.execute("SELECT name FROM users WHERE id=?", (project[3],)).fetchone()
                st.write(f"Created by: {creator[0]}")
                
                # Check if user is already a member
                is_member = c.execute("""
                    SELECT 1 FROM project_members 
                    WHERE project_id=? AND user_id=?
                """, (project[0], st.session_state.user_id)).fetchone()
                
                if not is_member:
                    if st.button(f"Join Project {project[0]}"):
                        c.execute("INSERT INTO project_members (project_id, user_id) VALUES (?, ?)",
                                 (project[0], st.session_state.user_id))
                        conn.commit()
                        st.success("Joined project successfully!")
                else:
                    st.info("You are already a member of this project")
                
                # --- Collaborative Code Editor (Prototype) ---
                st.subheader("Collaborative Code Editor (Prototype)")
                st.caption("Note: Code is saved per project. Not real-time collaborative.")
                # Load last code for this project
                code_row = c.execute("SELECT code FROM project_code WHERE project_id=?", (project[0],)).fetchone()
                code = code_row[0] if code_row else ""
                new_code = st_monaco(
                    value=code,
                    language="python",
                    theme="vs-dark",
                    height=300
                )
                if st.button(f"Save Code {project[0]}"):
                    if code_row:
                        c.execute("UPDATE project_code SET code=? WHERE project_id=?", (new_code, project[0]))
                    else:
                        c.execute("INSERT INTO project_code (project_id, code) VALUES (?, ?)", (project[0], new_code))
                    conn.commit()
                    st.success("Code saved!")
                # Code execution (Python only, demo)
                if st.button(f"Run Code {project[0]}"):
                    try:
                        # Save code to temp file
                        with open("temp_code.py", "w", encoding="utf-8") as f:
                            f.write(new_code)
                        result = subprocess.run([sys.executable, "temp_code.py"], capture_output=True, text=True, timeout=5)
                        st.code(result.stdout + result.stderr, language="text")
                    except Exception as e:
                        st.error(f"Error running code: {e}")
                # --- Project Chat ---
                st.subheader("Project Chat")
                chat_msgs = c.execute("SELECT message, sender_id, sent_date FROM project_chat WHERE project_id=? ORDER BY sent_date DESC LIMIT 10", (project[0],)).fetchall()
                for msg in reversed(chat_msgs):
                    sender = c.execute("SELECT name FROM users WHERE id=?", (msg[1],)).fetchone()
                    st.markdown(f"**{sender[0]}** ({msg[2]}): {msg[0]}")
                chat_input = st.text_input(f"New chat message for project {project[0]}", key=f"chat_input_{project[0]}")
                if st.button(f"Send Chat {project[0]}"):
                    if chat_input.strip():
                        c.execute("INSERT INTO project_chat (project_id, sender_id, message, sent_date) VALUES (?, ?, ?, ?)",
                                  (project[0], st.session_state.user_id, chat_input, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        conn.commit()
                        st.rerun()
                # --- Project File Uploads ---
                st.subheader("Project Files")
                if is_member or ("created_by" in project and project[3] == st.session_state.user_id):
                    uploaded_file = st.file_uploader(f"Upload a file for this project", type=["pdf", "docx", "txt", "png", "jpg", "jpeg", "csv", "xlsx"], key=f"file_upload_{project[0]}")
                    if uploaded_file:
                        import os
                        os.makedirs("project_uploads", exist_ok=True)
                        file_path = f"project_uploads/{project[0]}_{uploaded_file.name}"
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        c.execute("INSERT INTO project_files (project_id, filename, uploader_id, upload_date) VALUES (?, ?, ?, ?)",
                                  (project[0], uploaded_file.name, st.session_state.user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        conn.commit()
                        st.success("File uploaded!")
                # List files
                files = c.execute("SELECT filename, uploader_id, upload_date FROM project_files WHERE project_id=?", (project[0],)).fetchall()
                if files:
                    for file in files:
                        uploader = c.execute("SELECT name FROM users WHERE id=?", (file[1],)).fetchone()
                        st.markdown(f"- [{file[0]}](project_uploads/{project[0]}_{file[0]}) uploaded by {uploader[0]} on {file[2]}")
                else:
                    st.caption("No files uploaded yet.")
                # --- Project Invitations (only for creator) ---
                if "created_by" in project and project[3] == st.session_state.user_id:
                    st.subheader("Invite User by Email")
                    invite_email = st.text_input(f"Invite user to project {project[0]}", key=f"invite_email_{project[0]}")
                    if st.button(f"Send Invite {project[0]}"):
                        invited_user = c.execute("SELECT id FROM users WHERE email=?", (invite_email,)).fetchone()
                        if not invited_user:
                            st.error("No user found with that email.")
                        else:
                            already_member = c.execute("SELECT 1 FROM project_members WHERE project_id=? AND user_id=?", (project[0], invited_user[0])).fetchone()
                            if already_member:
                                st.info("User is already a member of this project.")
                            else:
                                c.execute("INSERT INTO project_members (project_id, user_id) VALUES (?, ?)", (project[0], invited_user[0]))
                                conn.commit()
                                st.success("User invited and added to the project!")
        
        conn.close()

    elif menu == "My Projects":
        st.header("My Projects")
        
        conn = sqlite3.connect('student_projects.db')
        c = conn.cursor()
        my_projects = c.execute("""
            SELECT p.*, COUNT(pm.user_id) as member_count 
            FROM projects p
            JOIN project_members pm ON p.id = pm.project_id
            WHERE p.id IN (
                SELECT project_id FROM project_members WHERE user_id=?
            )
            GROUP BY p.id
        """, (st.session_state.user_id,)).fetchall()
        
        for project in my_projects:
            with st.expander(f"Project: {project[1]}"):
                st.write(f"Description: {project[2]}")
                st.write(f"Start Date: {project[4]}")
                
                # Show team members
                members = c.execute("""
                    SELECT u.name, u.role FROM users u
                    JOIN project_members pm ON u.id = pm.user_id
                    WHERE pm.project_id=?
                """, (project[0],)).fetchall()
                
                st.write("Team:")
                for member in members:
                    st.write(f"- {member[0]} ({member[1]})")
                
                # --- Collaborative Code Editor (Prototype) ---
                st.subheader("Collaborative Code Editor (Prototype)")
                st.caption("Note: Code is saved per project. Not real-time collaborative.")
                c.execute("""CREATE TABLE IF NOT EXISTS project_code (project_id INTEGER PRIMARY KEY, code TEXT)""")
                code_row = c.execute("SELECT code FROM project_code WHERE project_id=?", (project[0],)).fetchone()
                code = code_row[0] if code_row else ""
                new_code = st_monaco(
                    value=code,
                    language="python",
                    theme="vs-dark",
                    height=300
                )
                if st.button(f"Save Code {project[0]}"):
                    if code_row:
                        c.execute("UPDATE project_code SET code=? WHERE project_id=?", (new_code, project[0]))
                    else:
                        c.execute("INSERT INTO project_code (project_id, code) VALUES (?, ?)", (project[0], new_code))
                    conn.commit()
                    st.success("Code saved!")
                # Code execution (Python only, demo)
                if st.button(f"Run Code {project[0]}"):
                    try:
                        with open("temp_code.py", "w", encoding="utf-8") as f:
                            f.write(new_code)
                        result = subprocess.run([sys.executable, "temp_code.py"], capture_output=True, text=True, timeout=5)
                        st.code(result.stdout + result.stderr, language="text")
                    except Exception as e:
                        st.error(f"Error running code: {e}")
                # --- Project Chat ---
                st.subheader("Project Chat")
                chat_msgs = c.execute("SELECT message, sender_id, sent_date FROM project_chat WHERE project_id=? ORDER BY sent_date DESC LIMIT 10", (project[0],)).fetchall()
                for msg in reversed(chat_msgs):
                    sender = c.execute("SELECT name FROM users WHERE id=?", (msg[1],)).fetchone()
                    st.markdown(f"**{sender[0]}** ({msg[2]}): {msg[0]}")
                chat_input = st.text_input(f"New chat message for project {project[0]}", key=f"chat_input_my_{project[0]}")
                if st.button(f"Send Chat {project[0]}"):
                    if chat_input.strip():
                        c.execute("INSERT INTO project_chat (project_id, sender_id, message, sent_date) VALUES (?, ?, ?, ?)",
                                  (project[0], st.session_state.user_id, chat_input, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        conn.commit()
                        st.rerun()
                # --- Project File Uploads ---
                st.subheader("Project Files")
                if ("created_by" in project and project[3] == st.session_state.user_id):
                    uploaded_file = st.file_uploader(f"Upload a file for this project", type=["pdf", "docx", "txt", "png", "jpg", "jpeg", "csv", "xlsx"], key=f"file_upload_my_{project[0]}")
                    if uploaded_file:
                        import os
                        os.makedirs("project_uploads", exist_ok=True)
                        file_path = f"project_uploads/{project[0]}_{uploaded_file.name}"
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        c.execute("INSERT INTO project_files (project_id, filename, uploader_id, upload_date) VALUES (?, ?, ?, ?)",
                                  (project[0], uploaded_file.name, st.session_state.user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        conn.commit()
                        st.success("File uploaded!")
                # List files
                files = c.execute("SELECT filename, uploader_id, upload_date FROM project_files WHERE project_id=?", (project[0],)).fetchall()
                if files:
                    for file in files:
                        uploader = c.execute("SELECT name FROM users WHERE id=?", (file[1],)).fetchone()
                        st.markdown(f"- [{file[0]}](project_uploads/{project[0]}_{file[0]}) uploaded by {uploader[0]} on {file[2]}")
                else:
                    st.caption("No files uploaded yet.")
                # --- Project Invitations (only for creator) ---
                if "created_by" in project and project[3] == st.session_state.user_id:
                    st.subheader("Invite User by Email")
                    invite_email = st.text_input(f"Invite user to project {project[0]}", key=f"invite_email_my_{project[0]}")
                    if st.button(f"Send Invite {project[0]}"):
                        invited_user = c.execute("SELECT id FROM users WHERE email=?", (invite_email,)).fetchone()
                        if not invited_user:
                            st.error("No user found with that email.")
                        else:
                            already_member = c.execute("SELECT 1 FROM project_members WHERE project_id=? AND user_id=?", (project[0], invited_user[0])).fetchone()
                            if already_member:
                                st.info("User is already a member of this project.")
                            else:
                                c.execute("INSERT INTO project_members (project_id, user_id) VALUES (?, ?)", (project[0], invited_user[0]))
                                conn.commit()
                                st.success("User invited and added to the project!")
        
        conn.close()

    elif menu == "Messages":
        st.header("Project Messages")
        
        conn = sqlite3.connect('student_projects.db')
        c = conn.cursor()
        
        # Get user's projects
        projects = c.execute("""
            SELECT p.id, p.title FROM projects p
            JOIN project_members pm ON p.id = pm.project_id
            WHERE pm.user_id=?
        """, (st.session_state.user_id,)).fetchall()
        
        if projects:
            selected_project = st.selectbox("Select Project", 
                [p[1] for p in projects], key='selected_project')
            project_id = projects[[p[1] for p in projects].index(selected_project)][0]
            
            # Show messages
            messages = c.execute("""
                SELECT m.message, u.name, m.sent_date 
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.project_id=?
                ORDER BY m.sent_date DESC
            """, (project_id,)).fetchall()
            
            st.write("Messages:")
            for i, msg in enumerate(messages):
                st.text_area(
                    "",
                    f"{msg[1]} ({msg[2]}): {msg[0]}",
                    height=70,
                    disabled=True,
                    key=f"msg_{i}_{msg[2]}"
                )
            
            # Before the form, check if we need to clear the text area
            if "clear_new_message" in st.session_state and st.session_state["clear_new_message"]:
                st.session_state["new_message"] = ""
                st.session_state["clear_new_message"] = False

            with st.form("message_form"):
                message = st.text_area("New Message", key="new_message")
                if st.form_submit_button("Send"):
                    if message.strip():
                        c.execute(
                            "INSERT INTO messages (project_id, sender_id, message, sent_date) VALUES (?, ?, ?, ?)",
                            (project_id, st.session_state.user_id, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        )
                        conn.commit()
                        st.success("Message sent!")
                        st.session_state["clear_new_message"] = True  # Set flag to clear on next run
                        st.rerun()
                    else:
                        st.warning("Cannot send an empty message.")
        else:
            st.info("Join some projects to start messaging!")
        
        conn.close()

    elif menu == "Community":
        st.header("Community: Students & Teachers")
        conn = sqlite3.connect('student_projects.db')
        c = conn.cursor()
        users = c.execute("SELECT id, name, institution, role, profile_pic FROM users").fetchall()
        for user in users:
            user_id, name, institution, role, profile_pic = user
            # Projects involved: number of projects the user is a member of
            projects_involved = c.execute("SELECT COUNT(*) FROM project_members WHERE user_id=?", (user_id,)).fetchone()[0]
            # Lines of code contributed: sum of lines in all project_code entries for projects the user is a member of
            project_ids = c.execute("SELECT project_id FROM project_members WHERE user_id=?", (user_id,)).fetchall()
            project_ids = [pid[0] for pid in project_ids]
            lines_of_code = 0
            if project_ids:
                q_marks = ','.join(['?']*len(project_ids))
                codes = c.execute(f"SELECT code FROM project_code WHERE project_id IN ({q_marks})", project_ids).fetchall()
                for code_row in codes:
                    code = code_row[0] if code_row and code_row[0] else ""
                    lines_of_code += len(code.splitlines())
            user_profile_card(name, role, projects_involved, lines_of_code)
        conn.close()

    elif menu == "Profile":
        st.header("My Profile")
        conn = sqlite3.connect('student_projects.db')
        c = conn.cursor()
        user = c.execute("SELECT id, name, email, institution, role, join_date, profile_pic FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
        if user:
            user_id, name, email, institution, role, join_date, profile_pic = user
            col1, col2 = st.columns([1, 2])
            with col1:
                if profile_pic:
                    st.image(f"uploads/{profile_pic}", width=120)
                else:
                    st.image("https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y", width=120)
            with col2:
                st.subheader(name)
                st.write(f"**Email:** {email}")
                st.write(f"**Role:** {role}")
                st.write(f"**Institution:** {institution}")
                st.write(f"**Joined:** {join_date}")
            st.markdown("---")
            st.subheader("Edit Profile")
            new_name = st.text_input("Full Name", value=name)
            new_institution = st.text_input("Institution", value=institution)
            new_role = st.selectbox("Role", ["Student", "Teacher"], index=0 if role.lower()=="student" else 1)
            uploaded_pic = st.file_uploader("Upload Profile Picture", type=["png", "jpg", "jpeg"])
            if st.button("Update Profile"):
                pic_filename = profile_pic
                if uploaded_pic:
                    import os
                    os.makedirs("uploads", exist_ok=True)
                    pic_filename = f"user_{user_id}_{uploaded_pic.name}"
                    with open(f"uploads/{pic_filename}", "wb") as f:
                        f.write(uploaded_pic.getbuffer())
                c.execute("UPDATE users SET name=?, institution=?, role=?, profile_pic=? WHERE id=?", (new_name, new_institution, new_role, pic_filename, user_id))
                conn.commit()
                st.success("Profile updated!")
                st.rerun()
        else:
            st.error("User not found.")
        conn.close()

    elif menu == "Logout":
        st.session_state.user_id = None
        st.success("Logged out successfully!")
        st.rerun()

if __name__ == "__main__":
    main()

