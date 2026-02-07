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

        cursor.execute("SELECT * FROM Admin WHERE AdminID = ? AND AdminPassword = ?", (user_id, password))
        if cursor.fetchone():
            session['user_id'] = user_id
            session['role'] = 'admin'
            return redirect(url_for('admin_home'))

        cursor.execute("SELECT * FROM ProgrammeCoordinator WHERE CoordinatorID = ? AND CoordinatorPassword = ?", (user_id, password))
        if cursor.fetchone():
            session['user_id'] = user_id
            session['role'] = 'coordinator'
            return redirect(url_for('public_home'))
        
        cursor.execute("SELECT * FROM Lecturer WHERE LecturerID = ? AND LecturerPassword = ?", (user_id, password))
        if cursor.fetchone():
            session['user_id'] = user_id
            session['role'] = 'lecturer'
            return redirect(url_for('lecturer_home'))

        cursor.execute("SELECT * FROM Student WHERE StudentID = ? AND StudentPassword = ?", (user_id, password))
        if cursor.fetchone():
            session['user_id'] = user_id
            session['role'] = 'student'
            return redirect(url_for('public_home'))

        conn.close()
        flash('Invalid ID or Password')
        return redirect(url_for('login'))

    return render_template('mainScreens/login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/home')
def public_home():
    return render_template('mainScreens/home.html')

@app.route('/analytics')
def analytics():
    return render_template('mainScreens/analytics.html')

@app.route('/bookmarks')
def bookmarks():
    return render_template('mainScreens/bookmarks.html')

@app.route('/status')
def status_check():
    return render_template('mainScreens/status.html')

@app.route('/search_results')
def search_results():
    return render_template('mainScreens/publicationresults.html')

@app.route('/upload')
def upload_request():
    return render_template('lecturerStudent/upload.html')

@app.route('/admin/home')
def admin_home():
    return render_template('admin/home.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/status')
def admin_status():
    return render_template('admin/publicationStatus.html')

@app.route('/admin/requests')
def admin_requests():
    return render_template('admin/trackingRequests.html')

@app.route('/admin/users')
def admin_users():
    return render_template('admin/userManagement.html')

@app.route('/admin/manage_publications')
def admin_manage_pubs():
    return render_template('admin/viewPublications.html')

@app.route('/coordinator/tracking')
def coordinator_dashboard():
    return render_template('coordinator/tracking_status.html')

@app.route('/coordinator/review')
def coordinator_review():
    return render_template('coordinator/review_detail.html')

@app.route('/lecturer/dashboard')
def lecturer_dashboard():
    return render_template('lecturerStudent/lecturerDashboard.html')

@app.route('/lecturer/home')
def lecturer_home():
    return render_template('lecturerStudent/lecturerhome.html')

@app.route('/student/dashboard')
def student_dashboard():
    return render_template('lecturerStudent/studentDashboard.html')

if __name__ == '__main__':
    init_db()
    populate_db()
    app.run(debug=True)