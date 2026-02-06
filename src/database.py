import sqlite3

def init_db():
    conn = sqlite3.connect('trackingsystem.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Faculty (
        FacultyID TEXT PRIMARY KEY,
        FacultyName TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Admin (
        AdminID TEXT PRIMARY KEY,
        AdminPassword TEXT NOT NULL,
        AdminName TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ProgrammeCoordinator (
        CoordinatorID TEXT PRIMARY KEY,
        CoordinatorPassword TEXT NOT NULL,
        CoordinatorName TEXT NOT NULL,
        FacultyID TEXT NOT NULL,
        AdminID TEXT NOT NULL,
        FOREIGN KEY (FacultyID) REFERENCES Faculty(FacultyID),
        FOREIGN KEY (AdminID) REFERENCES Admin(AdminID)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Lecturer (
        LecturerID TEXT PRIMARY KEY,
        LecturerPassword TEXT NOT NULL,
        LecturerName TEXT NOT NULL,
        CoordinatorID TEXT NOT NULL,
        AdminID TEXT NOT NULL,
        FacultyID TEXT NOT NULL,
        FOREIGN KEY (CoordinatorID) REFERENCES ProgrammeCoordinator(CoordinatorID),
        FOREIGN KEY (AdminID) REFERENCES Admin(AdminID),
        FOREIGN KEY (FacultyID) REFERENCES Faculty(FacultyID)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Student (
        StudentID TEXT PRIMARY KEY,
        StudentPassword TEXT NOT NULL,
        StudentName TEXT NOT NULL,
        IsFinalYear INTEGER NOT NULL,
        LecturerID TEXT, 
        AdminID TEXT NOT NULL,
        FacultyID TEXT NOT NULL,
        FOREIGN KEY (LecturerID) REFERENCES Lecturer(LecturerID),
        FOREIGN KEY (AdminID) REFERENCES Admin(AdminID),
        FOREIGN KEY (FacultyID) REFERENCES Faculty(FacultyID)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Paper (
        PaperID TEXT PRIMARY KEY,
        PaperTitle TEXT NOT NULL,
        DOI TEXT NOT NULL,
        DatePublished TEXT NOT NULL,
        LinkToPaper TEXT NOT NULL,
        PaperType TEXT NOT NULL,
        LecturerID TEXT NOT NULL,
        StudentID TEXT,
        FOREIGN KEY (LecturerID) REFERENCES Lecturer(LecturerID),
        FOREIGN KEY (StudentID) REFERENCES Student(StudentID)
    )
    ''')

    conn.commit()
    conn.close()

def populate_db():
    conn = sqlite3.connect('trackingsystem.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    student_names = [
        "Harvind", "Sanjeevan", "Vidhya", "Aizad", "Sybau",
        "Wei Hong", "Siti Aminah", "Rajesh Kumar", "Jason Lee", "Nurul Izzah",
        "Amanda Wong", "Haziq Razak", "Mei Ling", "Kenji Sato", "Sofia Maria",
        "Farid Kamil", "Alice Tan", "Gopal Krishnan", "Ying Ying", "Benjamin Teoh",
        "David Choo", "Priya Kaur", "Lim Wei", "Aisha Bakar", "Robert Fernandez"
    ]

    lecturer_names = [
        "Dr. Azman", "Dr. Sarah", "Dr. Chong",
        "Mr. Mavi", "Ms. Geetha", "Dr. Wong",
        "Dr. Zulaikha", "Mr. Tan", "Ms. Emily",
        "Dr. Ravi", "Dr. Lim", "Ms. Noraini",
        "Mr. James", "Dr. Brenda", "Dr. Hisham"
    ]

    coord_names = ["Prof. Siva", "Dr. Lee", "Ms. Salmah", "Mr. Johnson", "Dr. Faizal"]
    
    admin_names = ["Admin Rose", "Admin Kamal", "Admin Susan", "Admin Raj", "Admin Hafiz"]

    faculties = [
        ("FCI", "Faculty of Computing & Informatics"),
        ("FAIE", "Faculty of Artificial Intelligence and Engineering"),
        ("FCM", "Faculty of Creative Multimedia"),
        ("FAC", "Faculty of Applied Communications"),
        ("FOM", "Faculty of Management")
    ]

    stu_idx = 0
    lec_idx = 0
    coord_idx = 0
    admin_idx = 0

    for code, name in faculties:
        cursor.execute("INSERT OR IGNORE INTO Faculty (FacultyID, FacultyName) VALUES (?, ?)", (code, name))
        
        admin_name = admin_names[admin_idx]
        admin_id = f"ADM-{code}-01"
        cursor.execute("INSERT OR IGNORE INTO Admin (AdminID, AdminPassword, AdminName) VALUES (?, ?, ?)", 
                       (admin_id, "admin123", admin_name))
        admin_idx += 1

        coord_name = coord_names[coord_idx]
        coord_id = f"COO-{code}-01"
        cursor.execute("INSERT OR IGNORE INTO ProgrammeCoordinator (CoordinatorID, CoordinatorPassword, CoordinatorName, FacultyID, AdminID) VALUES (?, ?, ?, ?, ?)", 
                       (coord_id, "coord123", coord_name, code, admin_id))
        coord_idx += 1

        lecturer_ids = []
        for i in range(1, 4):
            lec_name = lecturer_names[lec_idx]
            lec_id = f"LEC-{code}-0{i}"
            lecturer_ids.append(lec_id)
            cursor.execute("INSERT OR IGNORE INTO Lecturer (LecturerID, LecturerPassword, LecturerName, CoordinatorID, AdminID, FacultyID) VALUES (?, ?, ?, ?, ?, ?)", 
                           (lec_id, "lec123", lec_name, coord_id, admin_id, code))
            lec_idx += 1

        for i in range(1, 6):
            student_name = student_names[stu_idx]
            stu_id = f"STU-{code}-0{i}"
            assigned_lecturer = lecturer_ids[(i - 1) % 3]
            is_final = 1 if i == 5 else 0
            
            cursor.execute("INSERT OR IGNORE INTO Student (StudentID, StudentPassword, StudentName, IsFinalYear, LecturerID, AdminID, FacultyID) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                           (stu_id, "stu123", student_name, is_final, assigned_lecturer, admin_id, code))
            stu_idx += 1

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    populate_db()