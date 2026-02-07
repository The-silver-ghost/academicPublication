from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import uuid
from werkzeug.utils import secure_filename
from database import init_db, populate_db
from math import ceil
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_this'
DB_NAME = 'trackingsystem.db'
UPLOAD_FOLDER = 'static/uploads/covers'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_name(name):
    name = name.lower()
    for title in ["dr.", "prof.", "mr.", "ms.", "ir.", "ts."]:
        name = name.replace(title, "")
    return name.strip()

def get_public_search_results(user_id, page=1, per_page=10):
    search_query = request.args.get('query', '').strip()
    filter_type = request.args.get('filter_type', '')
    filter_year = request.args.get('filter_year', '')
    
    # Base Query: Only show APPROVED papers for general search
    # Also check if the current user has bookmarked each paper
    sql = '''
        SELECT p.*, 
        CASE WHEN b.PaperID IS NOT NULL THEN 1 ELSE 0 END as IsBookmarked
        FROM Paper p
        LEFT JOIN Bookmarks b ON p.PaperID = b.PaperID AND b.UserID = ?
        WHERE p.Status = 'Approved'
    '''
    params = [user_id]
    
    # 1. Search Logic
    if search_query:
        sql += " AND (p.PaperTitle LIKE ? OR p.Authors LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    # 2. Filter Logic
    if filter_type:
        sql += " AND p.PaperType = ?"
        params.append(filter_type)
        
    if filter_year:
        sql += " AND substr(p.DatePublished, 1, 4) = ?" 
        params.append(filter_year)

    # 3. Pagination
    conn = get_db_connection()
    count_sql = f"SELECT COUNT(*) FROM ({sql})"
    total_count = conn.execute(count_sql, params).fetchone()[0]
    total_pages = ceil(total_count / per_page)
    
    offset = (page - 1) * per_page
    sql += f" LIMIT {per_page} OFFSET {offset}"
    
    papers = conn.execute(sql, params).fetchall()
    conn.close()
    
    return papers, total_count, total_pages, page

def get_filtered_papers(base_query, query_params, page=1, per_page=10):
    search_query = request.args.get('query', '').strip()
    filter_type = request.args.get('filter_type', '')
    filter_status = request.args.get('filter_status', '')
    filter_year = request.args.get('filter_year', '')
    
    sql = base_query
    params = list(query_params)
    
    if search_query:
        sql += " AND (PaperTitle LIKE ? OR Authors LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    if filter_type:
        sql += " AND PaperType = ?"
        params.append(filter_type)
        
    if filter_status:
        sql += " AND Status = ?"
        params.append(filter_status)
        
    if filter_year:
        sql += " AND substr(DatePublished, 1, 4) = ?" 
        params.append(filter_year)

    conn = get_db_connection()
    
    count_sql = f"SELECT COUNT(*) FROM ({sql})"
    total_count = conn.execute(count_sql, params).fetchone()[0]
    total_pages = ceil(total_count / per_page)
    
    offset = (page - 1) * per_page
    sql += f" LIMIT {per_page} OFFSET {offset}"
    
    papers = conn.execute(sql, params).fetchall()
    conn.close()
    
    return papers, total_count, total_pages, page

def validate_authors_and_get_ids(authors_text):
    if not authors_text:
        return False, "Author list cannot be empty.", None, None, None

    conn = get_db_connection()
    cursor = conn.cursor()
    
    author_names = [a.strip() for a in authors_text.split(',') if a.strip()]
    
    found_lec = None
    found_stu = None
    found_coord = None
    
    academic_staff_found = False

    for author in author_names:
        c_name = clean_name(author)
        
        if not found_lec:
            cursor.execute("SELECT LecturerID, LecturerName FROM Lecturer")
            for row in cursor.fetchall():
                if c_name == clean_name(row['LecturerName']):
                    found_lec = row['LecturerID']
                    academic_staff_found = True
                    break
        
        if not found_coord:
            cursor.execute("SELECT CoordinatorID, CoordinatorName FROM ProgrammeCoordinator")
            for row in cursor.fetchall():
                if c_name == clean_name(row['CoordinatorName']):
                    found_coord = row['CoordinatorID']
                    academic_staff_found = True
                    break

        if not found_stu:
            cursor.execute("SELECT StudentID, StudentName, IsFinalYear FROM Student")
            for row in cursor.fetchall():
                if c_name == clean_name(row['StudentName']):
                    if row['IsFinalYear'] != 1:
                         conn.close()
                         return False, f"Error: Student '{row['StudentName']}' is not Final Year.", None, None, None
                    found_stu = row['StudentID']
                    break

    conn.close()

    if not academic_staff_found:
        return False, "Error: Authors must include at least one valid Lecturer or Coordinator.", None, None, None

    return True, None, found_lec, found_stu, found_coord

def process_publication_request(form, file):
    user_role = session.get('role')
    user_id = session.get('user_id')

    title = form.get('title')
    authors = form.get('authors')
    pub_date = form.get('date_published')
    url = form.get('url')
    paper_type = form.get('paper_type')
    doi = form.get('doi')

    if not all([title, authors, pub_date, url, paper_type]):
        flash("Error: Please fill in all required fields.")
        return False

    req_date = datetime.now().strftime('%Y-%m-%d')

    valid, msg, lec_id, stu_id, coord_id = validate_authors_and_get_ids(authors)
    if not valid:
        flash(msg)
        return False

    if user_role != 'admin':
        is_author = False
        if user_role == 'lecturer' and lec_id == user_id: is_author = True
        elif user_role == 'student' and stu_id == user_id: is_author = True
        elif user_role == 'coordinator' and coord_id == user_id: is_author = True
        
        if not is_author:
            flash("Error: You can only request tracking for papers where you are an author.")
            return False

    cover_image = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        cover_image = f"{uuid.uuid4().hex}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], cover_image))
    else:
        flash("Error: Valid Cover Page required.")
        return False

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        paper_id = f"PAP-{uuid.uuid4().hex[:8].upper()}"
        
        admin_id = user_id if user_role == 'admin' else None

        cursor.execute('''
            INSERT INTO Paper (
                PaperID, PaperTitle, DOI, DatePublished, DateRequest, 
                LinkToPaper, PaperType, CoverImage, Authors, Status, 
                LecturerID, StudentID, CoordinatorID, AdminID
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            paper_id, title, doi, pub_date, req_date, 
            url, paper_type, cover_image, authors, 'Under Review', 
            lec_id, stu_id, coord_id, admin_id
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        flash(f"Database Error: {str(e)}")
        return False

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

        # Admin
        cursor.execute("SELECT * FROM Admin WHERE AdminID = ? AND AdminPassword = ?", (user_id, password))
        if cursor.fetchone():
            session['user_id'] = user_id
            session['role'] = 'admin'
            conn.close()
            return redirect(url_for('admin_home'))

        # Coordinator
        cursor.execute("SELECT * FROM ProgrammeCoordinator WHERE CoordinatorID = ? AND CoordinatorPassword = ?", (user_id, password))
        if cursor.fetchone():
            session['user_id'] = user_id
            session['role'] = 'coordinator'
            conn.close()
            return redirect(url_for('coordinator_home'))
        
        # Lecturer
        cursor.execute("SELECT * FROM Lecturer WHERE LecturerID = ? AND LecturerPassword = ?", (user_id, password))
        if cursor.fetchone():
            session['user_id'] = user_id
            session['role'] = 'lecturer'
            conn.close()
            return redirect(url_for('lecturer_student_home'))

        # Student
        cursor.execute("SELECT * FROM Student WHERE StudentID = ? AND StudentPassword = ?", (user_id, password))
        if cursor.fetchone():
            session['user_id'] = user_id
            session['role'] = 'student'
            conn.close()
            return redirect(url_for('lecturer_student_home'))

        conn.close()
        flash('Invalid ID or Password')
        return redirect(url_for('login'))

    return render_template('mainScreens/login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/review/submit', methods=['POST'])
def submit_review():
    paper_id = request.form.get('paper_id')
    action = request.form.get('action')
    feedback = request.form.get('feedback')
    
    new_status = "Approved" if action == "approve" else "Rejected"
    
    conn = get_db_connection()
    conn.execute("UPDATE Paper SET Status = ?, Feedback = ? WHERE PaperID = ?", 
                 (new_status, feedback, paper_id))
    conn.commit()
    conn.close()
    
    flash(f"Paper {new_status} successfully.")
    
    if session.get('role') == 'admin':
        return redirect(url_for('admin_status'))
    else:
        return redirect(url_for('coordinator_status'))

@app.route('/feedback/view')
def view_feedback_detail():
    paper_id = request.args.get('id')
    conn = get_db_connection()
    paper = conn.execute("SELECT * FROM Paper WHERE PaperID = ?", (paper_id,)).fetchone()
    conn.close()
    return render_template('mainScreens/view_feedback.html', paper=paper)

@app.route('/bookmark/toggle', methods=['POST'])
def toggle_bookmark():
    user_id = session.get('user_id')
    paper_id = request.form.get('paper_id')
    
    conn = get_db_connection()
    # Check if exists
    exists = conn.execute("SELECT 1 FROM Bookmarks WHERE UserID = ? AND PaperID = ?", (user_id, paper_id)).fetchone()
    
    if exists:
        conn.execute("DELETE FROM Bookmarks WHERE UserID = ? AND PaperID = ?", (user_id, paper_id))
        msg = "Removed from bookmarks"
    else:
        conn.execute("INSERT INTO Bookmarks (UserID, PaperID) VALUES (?, ?)", (user_id, paper_id))
        msg = "Added to bookmarks"
        
    conn.commit()
    conn.close()
    return redirect(request.referrer)

@app.route('/admin/remove_paper', methods=['POST'])
def admin_remove_paper():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    paper_id = request.form.get('paper_id')
    conn = get_db_connection()
    conn.execute("UPDATE Paper SET Status = 'Removed' WHERE PaperID = ?", (paper_id,))
    conn.commit()
    conn.close()
    flash("Paper removed from search results.")
    return redirect(request.referrer)

def get_bookmarked_papers(user_id, page=1, per_page=10):
    """
    Fetches papers bookmarked by the user.
    """
    search_query = request.args.get('query', '').strip()
    
    sql = '''
        SELECT p.* FROM Paper p
        JOIN Bookmarks b ON p.PaperID = b.PaperID
        WHERE b.UserID = ?
    '''
    params = [user_id]
    
    if search_query:
        sql += " AND (p.PaperTitle LIKE ? OR p.Authors LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    conn = get_db_connection()
    count_sql = f"SELECT COUNT(*) FROM ({sql})"
    total_count = conn.execute(count_sql, params).fetchone()[0]
    total_pages = ceil(total_count / per_page)
    
    offset = (page - 1) * per_page
    sql += f" LIMIT {per_page} OFFSET {offset}"
    
    papers = conn.execute(sql, params).fetchall()
    conn.close()
    
    return papers, total_count, total_pages, page

# ADMIN -----------------------------------------------------------------------------------------------
@app.route('/admin/home')
def admin_home():
    return render_template('admin/admin_home.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin/admin_dashboard.html')

@app.route('/admin/bookmarks')
def admin_bookmarks():
    page = request.args.get('page', 1, type=int)
    papers, total, pages, current = get_bookmarked_papers(session.get('user_id'), page)
    return render_template('admin/admin_bookmarks.html', 
                           papers=papers, total=total, pages=pages, current_page=current)

@app.route('/admin/search_results')
def admin_search_results():
    page = request.args.get('page', 1, type=int)
    papers, total, pages, current = get_public_search_results(session.get('user_id'), page)
    return render_template('admin/admin_publicationresults.html', 
                           papers=papers, total=total, pages=pages, current_page=current)

@app.route('/admin/status')
def admin_status():
    page = request.args.get('page', 1, type=int)
    
    base_query = "SELECT * FROM Paper WHERE 1=1" 
    base_params = []
    
    papers, total, pages, current_page = get_filtered_papers(base_query, base_params, page)
    
    return render_template('admin/admin_publicationStatus.html', 
                           papers=papers, total=total, pages=pages, current_page=current_page)

@app.route('/admin/requests', methods=['GET', 'POST'])
def admin_requests():
    if request.method == 'POST':
        if process_publication_request(request.form, request.files.get('cover_page')):
            flash('Tracking Request Submitted Successfully!')
            return redirect(url_for('admin_dashboard'))
    return render_template('admin/admin_trackingRequests.html')

@app.route('/admin/review_detail')
def admin_review_detail():
    paper_id = request.args.get('id')
    conn = get_db_connection()
    paper = conn.execute("SELECT * FROM Paper WHERE PaperID = ?", (paper_id,)).fetchone()
    conn.close()
    return render_template('admin/admin_review_detail.html', paper=paper)

@app.route('/admin/users')
def admin_users():
    return render_template('admin/userManagement.html')

# COORDINATOR -------------------------------------------------------------------------------------
@app.route('/coordinator/home')
def coordinator_home():
    return render_template('coordinator/coordinator_home.html')

@app.route('/coordinator/dashboard')
def coordinator_dashboard():
    return render_template('coordinator/coordinator_dashboard.html')

@app.route('/coordinator/bookmarks')
def coordinator_bookmarks():
    page = request.args.get('page', 1, type=int)
    papers, total, pages, current = get_bookmarked_papers(session.get('user_id'), page)
    return render_template('coordinator/coordinator_bookmarks.html', 
                           papers=papers, total=total, pages=pages, current_page=current)

@app.route('/coordinator/search_results')
def coordinator_search_results():
    page = request.args.get('page', 1, type=int)
    papers, total, pages, current = get_public_search_results(session.get('user_id'), page)
    return render_template('coordinator/coordinator_publicationresults.html', 
                           papers=papers, total=total, pages=pages, current_page=current)

@app.route('/coordinator/status')
def coordinator_status():
    user_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    
    conn = get_db_connection()
    coord = conn.execute("SELECT FacultyID FROM ProgrammeCoordinator WHERE CoordinatorID = ?", (user_id,)).fetchone()
    faculty_id = coord['FacultyID'] if coord else None
    conn.close()

    base_query = '''
        SELECT DISTINCT p.* FROM Paper p
        LEFT JOIN Lecturer l ON p.LecturerID = l.LecturerID
        LEFT JOIN Student s ON p.StudentID = s.StudentID
        LEFT JOIN ProgrammeCoordinator c ON p.CoordinatorID = c.CoordinatorID
        WHERE (p.CoordinatorID = ? OR l.FacultyID = ? OR s.FacultyID = ? OR c.FacultyID = ?)
    '''
    base_params = [user_id, faculty_id, faculty_id, faculty_id]
    
    papers, total, pages, current_page = get_filtered_papers(base_query, base_params, page)
    
    return render_template('coordinator/coordinator_publicationStatus.html', 
                           papers=papers, total=total, pages=pages, current_page=current_page, current_user_id=user_id)


@app.route('/coordinator/requests', methods=['GET', 'POST'])
def coordinator_requests():
    if request.method == 'POST':
        if process_publication_request(request.form, request.files.get('cover_page')):
            flash('Tracking Request Submitted Successfully!')
            return redirect(url_for('coordinator_dashboard'))
    return render_template('coordinator/coordinator_trackingRequests.html')

@app.route('/coordinator/review')
def coordinator_review():
    paper_id = request.args.get('id')
    conn = get_db_connection()
    paper = conn.execute("SELECT * FROM Paper WHERE PaperID = ?", (paper_id,)).fetchone()
    conn.close()
    return render_template('coordinator/coordinator_review_detail.html', paper=paper)

# LECTURER/STUDENT -----------------------------------------------------------------------
@app.route('/academic/home')
def lecturer_student_home():
    return render_template('lecturerStudent/lecturerStudent_home.html')

@app.route('/academic/dashboard')
def lecturer_student_dashboard():
    return render_template('lecturerStudent/lecturerStudent_dashboard.html')

@app.route('/academic/bookmarks')
def lecturer_student_bookmarks():
    page = request.args.get('page', 1, type=int)
    papers, total, pages, current = get_bookmarked_papers(session.get('user_id'), page)
    return render_template('lecturerStudent/lecturerStudent_bookmarks.html', 
                           papers=papers, total=total, pages=pages, current_page=current)

@app.route('/academic/search_results') 
def lecturer_student_search_results():
    page = request.args.get('page', 1, type=int)
    papers, total, pages, current = get_public_search_results(session.get('user_id'), page)
    return render_template('lecturerStudent/lecturerStudent_publicationresults.html', 
                           papers=papers, total=total, pages=pages, current_page=current)

@app.route('/academic/status')
def lecturer_student_status():
    user_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    
    base_query = "SELECT * FROM Paper WHERE (LecturerID = ? OR StudentID = ?)"
    base_params = [user_id, user_id]
    
    papers, total, pages, current_page = get_filtered_papers(base_query, base_params, page)
    
    return render_template('lecturerStudent/lecturerStudent_publicationStatus.html', 
                           papers=papers, total=total, pages=pages, current_page=current_page)

@app.route('/academic/requests', methods=['GET', 'POST'])
def lecturer_student_requests():
    if request.method == 'POST':
        # logic handles flash messages for errors/success
        if process_publication_request(request.form, request.files.get('cover_page')):
            flash('Tracking Request Submitted Successfully!')
            return redirect(url_for('lecturer_student_dashboard'))
    return render_template('lecturerStudent/lecturerStudent_trackingRequests.html')

if __name__ == '__main__':
    init_db() 
    populate_db()
    app.run(debug=True)