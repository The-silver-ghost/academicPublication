from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
import uuid
from werkzeug.utils import secure_filename
from database import init_db, populate_db
from math import ceil
from datetime import datetime
import json
from collections import Counter

app = Flask(__name__)
app.secret_key = '2002200520092005'
DB_NAME = 'trackingsystem.db'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'covers')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    print(f"✅ Created directory: {UPLOAD_FOLDER}")

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

@app.route('/admin/api/report-data')
def get_report_data():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    
    # 1. Fetch ALL Papers for general stats
    papers = conn.execute("SELECT * FROM Paper").fetchall()
    
    # --- University Stats ---
    years = {}
    types = {}
    for p in papers:
        y = p['DatePublished'][:4]
        years[y] = years.get(y, 0) + 1
        t = p['PaperType']
        types[t] = types.get(t, 0) + 1

    # --- Faculty Stats ---
    # We link papers to faculty via the uploader (Lecturer OR Student)
    faculty_query = '''
        SELECT f.FacultyName, COUNT(p.PaperID) as Count
        FROM Paper p
        LEFT JOIN Lecturer l ON p.LecturerID = l.LecturerID
        LEFT JOIN Student s ON p.StudentID = s.StudentID
        LEFT JOIN Faculty f ON (l.FacultyID = f.FacultyID OR s.FacultyID = f.FacultyID)
        WHERE f.FacultyName IS NOT NULL
        GROUP BY f.FacultyName
    '''
    faculty_rows = conn.execute(faculty_query).fetchall()
    faculty_stats = {row['FacultyName']: row['Count'] for row in faculty_rows}

    user_stats_list = []

    # A. Student Counts
    stu_rows = conn.execute('''
        SELECT s.StudentName as Name, COUNT(p.PaperID) as Count 
        FROM Paper p 
        JOIN Student s ON p.StudentID = s.StudentID 
        GROUP BY s.StudentName
    ''').fetchall()
    for row in stu_rows:
        user_stats_list.append({'name': row['Name'] + " (Student)", 'count': row['Count']})

    # B. Lecturer Counts
    lec_rows = conn.execute('''
        SELECT l.LecturerName as Name, COUNT(p.PaperID) as Count 
        FROM Paper p 
        JOIN Lecturer l ON p.LecturerID = l.LecturerID 
        GROUP BY l.LecturerName
    ''').fetchall()
    for row in lec_rows:
        # Check if name already exists (e.g. if we want to merge, but usually keeping them separate is safer)
        user_stats_list.append({'name': row['Name'], 'count': row['Count']})

    # C. Coordinator Counts
    coord_rows = conn.execute('''
        SELECT c.CoordinatorName as Name, COUNT(p.PaperID) as Count 
        FROM Paper p 
        JOIN ProgrammeCoordinator c ON p.CoordinatorID = c.CoordinatorID 
        GROUP BY c.CoordinatorName
    ''').fetchall()
    for row in coord_rows:
        user_stats_list.append({'name': row['Name'], 'count': row['Count']})

    # Sort combined list by Count descending
    user_stats_list.sort(key=lambda x: x['count'], reverse=True)

    conn.close()

    return jsonify({
        'university': {
            'annual': {'labels': list(years.keys()), 'data': list(years.values())},
            'types': {'labels': list(types.keys()), 'data': list(types.values())}
        },
        'faculty': {
            'labels': list(faculty_stats.keys()),
            'data': list(faculty_stats.values())
        },
        'users': user_stats_list
    })

@app.route('/coordinator/api/report-data')
def get_coordinator_report_data():
    if session.get('role') != 'coordinator':
        return jsonify({'error': 'Unauthorized'}), 403
    
    mode = request.args.get('mode', 'personal')
    user_id = session.get('user_id')
    conn = get_db_connection()
    
    # Get Coordinator's Faculty
    coord_row = conn.execute("SELECT FacultyID, CoordinatorName FROM ProgrammeCoordinator WHERE CoordinatorID = ?", (user_id,)).fetchone()
    if not coord_row:
        return jsonify({'error': 'Coordinator not found'}), 404
    
    faculty_id = coord_row['FacultyID']
    coord_name = coord_row['CoordinatorName']

    if mode == 'faculty':
        # --- FACULTY STATS MODE ---
        
        # 1. General Stats (Annual & Types) for this Faculty
        # We check if the uploader (Student or Lecturer) belongs to this faculty
        query_general = '''
            SELECT p.DatePublished, p.PaperType
            FROM Paper p
            LEFT JOIN Lecturer l ON p.LecturerID = l.LecturerID
            LEFT JOIN Student s ON p.StudentID = s.StudentID
            WHERE l.FacultyID = ? OR s.FacultyID = ?
        '''
        papers = conn.execute(query_general, (faculty_id, faculty_id)).fetchall()
        
        years = {}
        types = {}
        for p in papers:
            y = p['DatePublished'][:4]
            years[y] = years.get(y, 0) + 1
            t = p['PaperType']
            types[t] = types.get(t, 0) + 1

        # 2. User Performance (FIXED: Include Students & Lecturers)
        authors_list = []

        # Count Student Papers in this Faculty
        stu_query = '''
            SELECT s.StudentName as Name, COUNT(p.PaperID) as Count
            FROM Paper p
            JOIN Student s ON p.StudentID = s.StudentID
            WHERE s.FacultyID = ?
            GROUP BY s.StudentName
        '''
        for row in conn.execute(stu_query, (faculty_id,)).fetchall():
            authors_list.append({'name': row['Name'] + " (Student)", 'count': row['Count']})

        # Count Lecturer Papers in this Faculty
        lec_query = '''
            SELECT l.LecturerName as Name, COUNT(p.PaperID) as Count
            FROM Paper p
            JOIN Lecturer l ON p.LecturerID = l.LecturerID
            WHERE l.FacultyID = ?
            GROUP BY l.LecturerName
        '''
        for row in conn.execute(lec_query, (faculty_id,)).fetchall():
            authors_list.append({'name': row['Name'], 'count': row['Count']})

        # Sort by count descending
        authors_list.sort(key=lambda x: x['count'], reverse=True)

        conn.close()
        return jsonify({
            'mode': 'faculty',
            'faculty_id': faculty_id,
            'annual': {'labels': list(years.keys()), 'data': list(years.values())},
            'types': {'labels': list(types.keys()), 'data': list(types.values())},
            'authors': authors_list[:10] # Top 10
        })

    else:
        # --- PERSONAL MODE ---
        query = "SELECT * FROM Paper WHERE CoordinatorID = ? ORDER BY DatePublished DESC"
        papers = conn.execute(query, (user_id,)).fetchall()
        
        paper_list = []
        for p in papers:
            paper_list.append({
                'title': p['PaperTitle'],
                'authors': p['Authors'], # Includes co-authors string
                'year': p['DatePublished'][:4],
                'type': p['PaperType']
            })
            
        conn.close()
        return jsonify({
            'mode': 'personal',
            'name': coord_name,
            'papers': paper_list
        })

@app.route('/academic/api/report-data')
def get_academic_report_data():
    role = session.get('role')
    if role not in ['lecturer', 'student']:
        return jsonify({'error': 'Unauthorized'}), 403

    user_id = session.get('user_id')
    conn = get_db_connection()

    # 1. Get User Name & Query
    if role == 'lecturer':
        name_row = conn.execute("SELECT LecturerName FROM Lecturer WHERE LecturerID = ?", (user_id,)).fetchone()
        name = name_row['LecturerName'] if name_row else "Unknown"
        query = "SELECT * FROM Paper WHERE LecturerID = ? ORDER BY DatePublished DESC"
    else:
        name_row = conn.execute("SELECT StudentName FROM Student WHERE StudentID = ?", (user_id,)).fetchone()
        name = name_row['StudentName'] if name_row else "Unknown"
        query = "SELECT * FROM Paper WHERE StudentID = ? ORDER BY DatePublished DESC"

    # 2. Fetch Papers
    papers = conn.execute(query, (user_id,)).fetchall()

    paper_list = []
    for p in papers:
        paper_list.append({
            'title': p['PaperTitle'],
            'authors': p['Authors'],
            'year': p['DatePublished'][:4],
            'type': p['PaperType']
        })

    conn.close()
    return jsonify({
        'name': name,
        'papers': paper_list
    })

def get_public_search_results(user_id, page=1, per_page=10):
    search_query = request.args.get('query', '').strip()
    filter_type = request.args.get('filter_type', '')
    filter_year = request.args.get('filter_year', '')

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

def generate_new_user_id(role, faculty_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    prefix_map = {
        'Student': ('STU', 'Student'),
        'Lecturer': ('LEC', 'Lecturer'),
        'ProgrammeCoordinator': ('COO', 'ProgrammeCoordinator'),
        'Admin': ('ADM', 'Admin')
    }
    
    prefix, table = prefix_map.get(role)
    
    query = f"SELECT {table}ID FROM {table} WHERE {table}ID LIKE ?"
    cursor.execute(query, (f"{prefix}-{faculty_id}-%",))
    existing_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    max_num = 0
    for eid in existing_ids:
        try:
            parts = eid.split('-')
            if len(parts) == 3:
                num = int(parts[2])
                if num > max_num: max_num = num
        except:
            continue
            
    new_num = max_num + 1
    return f"{prefix}-{faculty_id}-{str(new_num).zfill(2)}"

def get_analytics_data(user_role, user_id=None, faculty_id=None, year_filter=None):
    conn = get_db_connection()
    papers = []

    if user_role == 'admin':
        if faculty_id:
             papers = conn.execute('''
                SELECT p.* FROM Paper p
                LEFT JOIN Lecturer l ON p.LecturerID = l.LecturerID
                LEFT JOIN Student s ON p.StudentID = s.StudentID
                WHERE p.Status = 'Approved' AND (l.FacultyID = ? OR s.FacultyID = ?)
             ''', (faculty_id, faculty_id)).fetchall()
        else:
             papers = conn.execute("SELECT * FROM Paper WHERE Status = 'Approved'").fetchall()

    elif user_role == 'coordinator':
        if faculty_id == 'personal':
             papers = conn.execute("SELECT * FROM Paper WHERE Status = 'Approved' AND CoordinatorID = ?", (user_id,)).fetchall()
        else:
             coord = conn.execute("SELECT FacultyID FROM ProgrammeCoordinator WHERE CoordinatorID = ?", (user_id,)).fetchone()
             f_id = coord['FacultyID']
             papers = conn.execute('''
                SELECT DISTINCT p.* FROM Paper p
                LEFT JOIN Lecturer l ON p.LecturerID = l.LecturerID
                LEFT JOIN Student s ON p.StudentID = s.StudentID
                LEFT JOIN ProgrammeCoordinator c ON p.CoordinatorID = c.CoordinatorID
                WHERE p.Status = 'Approved' AND (l.FacultyID = ? OR s.FacultyID = ? OR c.FacultyID = ?)
             ''', (f_id, f_id, f_id)).fetchall()

    elif user_role == 'academic':
        papers = conn.execute("SELECT * FROM Paper WHERE Status = 'Approved' AND (LecturerID = ? OR StudentID = ?)", (user_id, user_id)).fetchall()

    conn.close()

    annual_counts = {}
    type_counts = {}
    author_counts = Counter()

    for p in papers:
        year = p['DatePublished'][:4]
        
        if year_filter and year_filter != 'All' and year != str(year_filter):
            continue

        annual_counts[year] = annual_counts.get(year, 0) + 1
        
        p_type = p['PaperType']
        type_counts[p_type] = type_counts.get(p_type, 0) + 1
        
        if p['Authors']:
            authors = [a.strip() for a in p['Authors'].split(',')]
            for a in authors:
                author_counts[a] += 1

    sorted_years = sorted(annual_counts.keys())
    chart_annual = {
        'labels': sorted_years,
        'data': [annual_counts[y] for y in sorted_years]
    }
    
    chart_types = {
        'labels': list(type_counts.keys()),
        'data': list(type_counts.values())
    }
    
    top_5 = author_counts.most_common(5)
    chart_authors = {
        'labels': [x[0] for x in top_5],
        'data': [x[1] for x in top_5]
    }

    return chart_annual, chart_types, chart_authors

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

def get_all_years():
    conn = get_db_connection()
    query = "SELECT DISTINCT substr(DatePublished, 1, 4) as year FROM Paper ORDER BY year DESC"
    years_data = conn.execute(query).fetchall()
    conn.close()
    
    years = [row['year'] for row in years_data if row['year']]
    
    if not years:
        from datetime import datetime
        years = [str(datetime.now().year)]
        
    return years

def clean_name(name):
    return name.lower().replace(" ", "").strip()

def validate_authors_and_get_ids(authors_text, bypass_staff_check=False):
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
                         return False, f"Error: Student '{row['StudentName']}' is not a Final Year student.", None, None, None
                    found_stu = row['StudentID']
                    break

    conn.close()

    if not academic_staff_found and not bypass_staff_check:
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

    is_admin = (user_role == 'admin')
    valid, msg, lec_id, stu_id, coord_id = validate_authors_and_get_ids(authors, bypass_staff_check=is_admin)
    
    if not valid:
        flash(msg)
        return False

    if not is_admin:
        is_author = False
        if user_role == 'lecturer' and lec_id == user_id: is_author = True
        elif user_role == 'student' and stu_id == user_id: is_author = True
        elif user_role == 'coordinator' and coord_id == user_id: is_author = True
        
        if not is_author:
            flash("Error: You can only request tracking for papers where YOU are an author.")
            return False

    cover_image = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        cover_image = f"{uuid.uuid4().hex}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], cover_image))
    else:
        flash("Error: Valid Cover Page (PNG/JPG) required.")
        return False

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        paper_id = f"PAP-{uuid.uuid4().hex[:8].upper()}"
        
        admin_id = user_id if is_admin else None

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
    year_filter = request.args.get('year', 'All') 
    
    annual, types, authors = get_analytics_data('admin', year_filter=year_filter)
    
    all_years = get_all_years()
    
    return render_template('admin/admin_dashboard.html', 
                           annual=annual, types=types, authors=authors, 
                           year_filter=year_filter, years=all_years)

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

@app.route('/admin/users', methods=['GET'])
def admin_users():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    conn = get_db_connection()
    faculties = conn.execute("SELECT * FROM Faculty").fetchall()
    coords = conn.execute("SELECT CoordinatorID, CoordinatorName, FacultyID FROM ProgrammeCoordinator").fetchall()
    lecturers = conn.execute("SELECT LecturerID, LecturerName, FacultyID FROM Lecturer").fetchall()
    conn.close()
    
    return render_template('admin/userManagement.html', 
                           faculties=faculties, coords=coords, lecturers=lecturers)

@app.route('/admin/users/search', methods=['POST'])
def search_user():
    user_id = request.json.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user_data = None
    role = None

    tables = [
        ('Student', 'StudentID'), 
        ('Lecturer', 'LecturerID'), 
        ('ProgrammeCoordinator', 'CoordinatorID'), 
        ('Admin', 'AdminID')
    ]

    for table, pk in tables:
        row = cursor.execute(f"SELECT * FROM {table} WHERE {pk} = ?", (user_id,)).fetchone()
        if row:
            user_data = dict(row)
            role = table
            break
    
    conn.close()
    
    if user_data:
        return json.dumps({'success': True, 'role': role, 'data': user_data})
    else:
        return json.dumps({'success': False})
    
@app.route('/admin/users/save', methods=['POST'])
def save_user():
    action = request.form.get('action')
    role = request.form.get('role')
    faculty_id = request.form.get('faculty')
    name = request.form.get('name')
    password = request.form.get('password')
    
    is_final_year = 1 if request.form.get('is_final_year') else 0
    assigned_lecturer = request.form.get('assigned_lecturer')
    assigned_coord = request.form.get('assigned_coord')
    
    original_id = request.form.get('original_id')
    original_role = request.form.get('original_role')

    admin_id = session.get('user_id')
    conn = get_db_connection()
    
    try:
        if action == 'delete':
            table = original_role
            pk = f"{original_role}ID" if original_role != 'ProgrammeCoordinator' else 'CoordinatorID'
            conn.execute(f"DELETE FROM {table} WHERE {pk} = ?", (original_id,))
            flash("User deleted successfully.")

        elif action == 'create':
            new_id = generate_new_user_id(role, faculty_id)
            
            if role == 'Student':
                conn.execute("INSERT INTO Student (StudentID, StudentPassword, StudentName, IsFinalYear, LecturerID, AdminID, FacultyID) VALUES (?,?,?,?,?,?,?)",
                             (new_id, password, name, is_final_year, assigned_lecturer, admin_id, faculty_id))
            elif role == 'Lecturer':
                conn.execute("INSERT INTO Lecturer (LecturerID, LecturerPassword, LecturerName, CoordinatorID, AdminID, FacultyID) VALUES (?,?,?,?,?,?)",
                             (new_id, password, name, assigned_coord, admin_id, faculty_id))
            elif role == 'ProgrammeCoordinator':
                conn.execute("INSERT INTO ProgrammeCoordinator (CoordinatorID, CoordinatorPassword, CoordinatorName, FacultyID, AdminID) VALUES (?,?,?,?,?)",
                             (new_id, password, name, faculty_id, admin_id))
            elif role == 'Admin':
                conn.execute("INSERT INTO Admin (AdminID, AdminPassword, AdminName) VALUES (?,?,?)",
                             (new_id, password, name))
            
            flash(f"User created: {new_id}")

        elif action == 'update':
            if role == original_role:
                if role == 'Student':
                    conn.execute("UPDATE Student SET StudentName=?, StudentPassword=?, IsFinalYear=?, LecturerID=?, FacultyID=? WHERE StudentID=?",
                                 (name, password, is_final_year, assigned_lecturer, faculty_id, original_id))
                elif role == 'Lecturer':
                    conn.execute("UPDATE Lecturer SET LecturerName=?, LecturerPassword=?, CoordinatorID=?, FacultyID=? WHERE LecturerID=?",
                                 (name, password, assigned_coord, faculty_id, original_id))
                elif role == 'ProgrammeCoordinator':
                    conn.execute("UPDATE ProgrammeCoordinator SET CoordinatorName=?, CoordinatorPassword=?, FacultyID=? WHERE CoordinatorID=?",
                                 (name, password, faculty_id, original_id))
                flash(f"User {original_id} updated.")
            
            else:
                new_id = generate_new_user_id(role, faculty_id)
                
                if role == 'Student':
                    conn.execute("INSERT INTO Student (StudentID, StudentPassword, StudentName, IsFinalYear, LecturerID, AdminID, FacultyID) VALUES (?,?,?,?,?,?,?)",
                                 (new_id, password, name, is_final_year, assigned_lecturer, admin_id, faculty_id))
                elif role == 'Lecturer':
                    conn.execute("INSERT INTO Lecturer (LecturerID, LecturerPassword, LecturerName, CoordinatorID, AdminID, FacultyID) VALUES (?,?,?,?,?,?)",
                                 (new_id, password, name, assigned_coord, admin_id, faculty_id))
                elif role == 'ProgrammeCoordinator':
                    conn.execute("INSERT INTO ProgrammeCoordinator (CoordinatorID, CoordinatorPassword, CoordinatorName, FacultyID, AdminID) VALUES (?,?,?,?,?)",
                                 (new_id, password, name, faculty_id, admin_id))

                conn.execute("UPDATE Bookmarks SET UserID = ? WHERE UserID = ?", (new_id, original_id))
            
                role_col_map = {
                    'Student': 'StudentID',
                    'Lecturer': 'LecturerID',
                    'ProgrammeCoordinator': 'CoordinatorID'
                }
                
                old_col = role_col_map.get(original_role)
                new_col = role_col_map.get(role)

                if old_col and new_col:
                    conn.execute(f"UPDATE Paper SET {new_col} = ?, {old_col} = NULL WHERE {old_col} = ?", (new_id, original_id))

                old_table = original_role
                old_pk = f"{original_role}ID" if original_role != 'ProgrammeCoordinator' else 'CoordinatorID'
                conn.execute(f"DELETE FROM {old_table} WHERE {old_pk} = ?", (original_id,))
                
                flash(f"User migrated from {original_id} to {new_id}")

        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}")
    finally:
        conn.close()

    return redirect(url_for('admin_users'))

# COORDINATOR -------------------------------------------------------------------------------------
@app.route('/coordinator/home')
def coordinator_home():
    return render_template('coordinator/coordinator_home.html')

@app.route('/coordinator/dashboard')
def coordinator_dashboard():
    mode = request.args.get('mode', 'faculty')
    year_filter = request.args.get('year', 'All')
    user_id = session.get('user_id')
    
    faculty_arg = 'personal' if mode == 'personal' else None
    
    annual, types, authors = get_analytics_data('coordinator', user_id, faculty_id=faculty_arg, year_filter=year_filter)
    
    all_years = get_all_years()
    
    return render_template('coordinator/coordinator_dashboard.html', 
                           annual=annual, types=types, authors=authors, mode=mode, 
                           year_filter=year_filter, years=all_years) 

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
    year_filter = request.args.get('year', 'All')
    user_id = session.get('user_id')
    
    annual, types, _ = get_analytics_data('academic', user_id, year_filter=year_filter)
    
    all_years = get_all_years()
    
    return render_template('lecturerStudent/lecturerStudent_dashboard.html', 
                           annual=annual, types=types, 
                           year_filter=year_filter, years=all_years) # Passed 'years'

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