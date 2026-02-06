import sqlite3

def create_database():

    conn = sqlite3.connect('tracking_system.db')
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
    print("Database 'tracking_system.db' and tables created successfully.")

if __name__ == "__main__":
    create_database()