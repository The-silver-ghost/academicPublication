from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from database import init_db, populate_db

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_this'
DB_NAME = 'trackingsystem.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def root():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor()

        #Admin
        cursor.execute("SELECT * FROM Admin WHERE AdminID = ? AND AdminPassword = ?", (user_id, password))
        if cursor.fetchone():
            session['user_id'] = user_id
            session['role'] = 'admin'
            return redirect(url_for('admin_home'))

        #Coordinator
        cursor.execute("SELECT * FROM ProgrammeCoordinator WHERE CoordinatorID = ? AND CoordinatorPassword = ?", (user_id, password))
        if cursor.fetchone():
            session['user_id'] = user_id
            session['role'] = 'coordinator'
            return redirect(url_for('coordinator_home'))
        
        #Lecturer
        cursor.execute("SELECT * FROM Lecturer WHERE LecturerID = ? AND LecturerPassword = ?", (user_id, password))
        if cursor.fetchone():
            session['user_id'] = user_id
            session['role'] = 'lecturer'
            return redirect(url_for('lecturer_student_home'))

        #Student
        cursor.execute("SELECT * FROM Student WHERE StudentID = ? AND StudentPassword = ?", (user_id, password))
        if cursor.fetchone():
            session['user_id'] = user_id
            session['role'] = 'student'
            return redirect(url_for('lecturer_student_home'))

        conn.close()
        flash('Invalid ID or Password')
        return redirect(url_for('login'))

    return render_template('mainScreens/login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ADMIN ROUTES ----------------------------------------------------------------------------------------------------------------
@app.route('/admin/home')
def admin_home():
    return render_template('admin/admin_home.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin/admin_dashboard.html')

@app.route('/admin/bookmarks')
def admin_bookmarks():
    return render_template('admin/admin_bookmarks.html')

@app.route('/admin/search_results')
def admin_search_results():
    search_term = request.args.get('query')
    # for DB search logic ltr
    return render_template('admin/admin_publicationresults.html', search_term=search_term)

@app.route('/admin/status')
def admin_status():
    return render_template('admin/admin_publicationStatus.html')

@app.route('/admin/requests')
def admin_requests():
    return render_template('admin/admin_trackingRequests.html')

@app.route('/admin/review_detail')
def admin_review_detail():
    return render_template('admin/admin_review_detail.html')

@app.route('/admin/users')
def admin_users():
    return render_template('admin/userManagement.html')

# COORDINATOR ROUTES ----------------------------------------------------------------------------------------------------------------
@app.route('/coordinator/home')
def coordinator_home():
    return render_template('coordinator/coordinator_home.html')

@app.route('/coordinator/dashboard')
def coordinator_dashboard():
    return render_template('coordinator/coordinator_dashboard.html')

@app.route('/coordinator/bookmarks')
def coordinator_bookmarks():
    return render_template('coordinator/coordinator_bookmarks.html')

@app.route('/coordinator/search_results')
def coordinator_search_results():
    search_term = request.args.get('query')
    return render_template('coordinator/coordinator_publicationresults.html', search_term=search_term)

@app.route('/coordinator/status')
def coordinator_status():
    return render_template('coordinator/coordinator_publicationStatus.html')

@app.route('/coordinator/requests')
def coordinator_requests():
    return render_template('coordinator/coordinator_trackingRequests.html')

@app.route('/coordinator/review')
def coordinator_review():
    return render_template('coordinator/coordinator_review_detail.html')

# LECTURER/STUDENT ROUTES ----------------------------------------------------------------------------------------------------------------
@app.route('/academic/home')
def lecturer_student_home():
    return render_template('lecturerStudent/lecturerStudent_home.html')

@app.route('/academic/dashboard')
def lecturer_student_dashboard():
    return render_template('lecturerStudent/lecturerStudent_dashboard.html')

@app.route('/academic/bookmarks')
def lecturer_student_bookmarks():
    return render_template('lecturerStudent/lecturerStudent_bookmarks.html')

@app.route('/academic/search_results') 
def lecturer_student_search_results():
    search_term = request.args.get('query')
    return render_template('lecturerStudent/lecturerStudent_publicationresults.html', search_term=search_term)

@app.route('/academic/status')
def lecturer_student_status():
    return render_template('lecturerStudent/lecturerStudent_publicationStatus.html')

@app.route('/academic/requests')
def lecturer_student_requests():
    return render_template('lecturerStudent/lecturerStudent_trackingRequests.html')

if __name__ == '__main__':
    init_db()
    populate_db()
    app.run(debug=True)