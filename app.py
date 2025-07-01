from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, render_template_string
import pandas as pd, numpy as np
import plotly.graph_objs as go
import plotly.io as pio
import os
from werkzeug.utils import secure_filename
from functools import lru_cache
import csv
from collections import defaultdict
from datetime import timedelta

# Load environment variables from .env if present (requires python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # If python-dotenv is not installed, skip loading .env

app = Flask(__name__)
app.secret_key = 'secret'
app.permanent_session_lifetime = timedelta(minutes=1)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
bp = Blueprint('dashboard', __name__)

SURVEY_CSV = 'survey_answers.csv'
SURVEY_PATH = os.path.join(UPLOAD_FOLDER, SURVEY_CSV)
SURVEY_QUESTIONS = [
    'How long did it take you to master the tool (Jira)?',
    'How often did you use tutorials/onboarding materials?',
    'What is your satisfaction level?',
    'How well does the tool’s (Jira) usability align with Agile principles?'
]
SURVEY_OPTIONS = [
    ['<1 day', '1-3 days', '1 week', '2+ weeks', 'Still learning'],
    ['Never', 'Rarely', 'Sometimes', 'Often', 'Always'],
    ['Very dissatisfied', 'Dissatisfied', 'Neutral', 'Satisfied', 'Very satisfied'],
    ['Not at all', 'Slightly', 'Moderately', 'Well', 'Extremely well']
]

# Require ADMIN_PASSWORD to be set via environment variable, do not use a default
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD environment variable must be set for admin access.")

@lru_cache(maxsize=10)
def parse_and_metrics(filepath):
    print(f"[parse_and_metrics] Parsing CSV: {filepath}")
    df = pd.read_csv(filepath, parse_dates=['created_date','started_date','completed_date'])
    df = df.dropna(subset=['created_date','started_date'])
    metrics = {}
    for _, r in df.iterrows():
        key = r['key']
        days_to_start = (r['started_date'] - r['created_date']).days
        days_to_complete = (r['completed_date'] - r['created_date']).days if pd.notna(r['completed_date']) else np.nan
        plats = [p for p in ['ios','android','tvos','roku','xbox','tizen'] if r.get(p)==1]
        total_changes = sum(r.get(c, 0) for c in ['design_changes','config_changes','store_changes'])
        metrics[key] = {
            'days_to_start': days_to_start,
            'days_to_complete': days_to_complete,
            'active_duration': r['active_duration'],
            'total_duration': r['total_duration'],
            'platforms': plats if plats else ['Other'],
            'total_changes': total_changes
        }
    return pd.DataFrame.from_dict(metrics, orient='index')

def read_survey_answers():
    answers = {}
    if os.path.exists(SURVEY_PATH):
        with open(SURVEY_PATH, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                answers[row['key']] = [row['q1'], row['q2'], row['q3'], row['q4']]
    return answers

def append_survey_answer(key, q1, q2, q3, q4):
    file_exists = os.path.exists(SURVEY_PATH)
    with open(SURVEY_PATH, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['key','q1','q2','q3','q4'])
        if not file_exists:
            writer.writeheader()
        writer.writerow({'key': key, 'q1': q1, 'q2': q2, 'q3': q3, 'q4': q4})

@bp.route('/', methods=['GET','POST'])
def upload():
    # CSV required headers for display
    csv_headers = [
        'key', 'created_date', 'started_date', 'completed_date',
        'active_duration', 'total_duration',
        'ios', 'android', 'tvos', 'roku', 'xbox', 'tizen',
        'design_changes', 'config_changes', 'store_changes'
    ]
    # Check if a file already exists in uploads
    uploaded_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.csv') and f != SURVEY_CSV]
    # Only auto-redirect if NOT coming from the upload button (GET request to '/')
    if uploaded_files and request.method == 'GET' and not request.args.get('force_upload'):
        # Use the most recently modified CSV file (excluding survey_answers.csv)
        latest_file = max(uploaded_files, key=lambda f: os.path.getmtime(os.path.join(app.config['UPLOAD_FOLDER'], f)))
        return redirect(url_for('dashboard.charts', filename=latest_file))
    if request.method == 'POST':
        f = request.files.get('file')
        if not f:
            flash('No file uploaded')
            return redirect(url_for('dashboard.upload'))
        fname = secure_filename(f.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        f.save(path)
        parse_and_metrics.cache_clear()  # Only clear cache here, on new upload
        redirect_url = url_for('dashboard.charts', filename=fname)
        # If AJAX, return JSON for redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'redirect': redirect_url})
        return redirect(redirect_url)
    return render_template('upload.html', csv_headers=csv_headers)

@bp.route('/charts/<filename>', methods=['GET', 'POST'])
def charts(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    df = parse_and_metrics(path)
    if df.empty:
        return render_template('dashboard.html', message="No valid data found.")

    survey_answers = read_survey_answers()
    form_message = None
    show_user_form = False
    new_user_key = None

    # Handle add user form
    if request.method == 'POST' and 'add_user' in request.form:
        new_user_key = request.form.get('new_user_key', '').strip()
        if not new_user_key:
            form_message = "Please enter a user name."
        elif new_user_key in survey_answers:
            form_message = f"User '{new_user_key}' already has a survey."
        else:
            show_user_form = True
    # Handle survey form submission
    elif request.method == 'POST' and 'user_key' in request.form:
        key = request.form.get('user_key')
        q1 = request.form.get('q1')
        q2 = request.form.get('q2')
        q3 = request.form.get('q3')
        q4 = request.form.get('q4')
        if key and q1 and q2 and q3 and q4:
            append_survey_answer(key, q1, q2, q3, q4)
            survey_answers[key] = [q1, q2, q3, q4]
            form_message = f"Survey answers for {key} saved."
        else:
            form_message = "Please answer all questions."

    # Pie charts for survey answers
    pie_charts = []
    if survey_answers:
        q_counts = [defaultdict(int) for _ in range(4)]
        for ans in survey_answers.values():
            for i, val in enumerate(ans):
                q_counts[i][val] += 1
        for i, (q, opts) in enumerate(zip(SURVEY_QUESTIONS, SURVEY_OPTIONS)):
            values = [q_counts[i][opt] for opt in opts]
            pie = go.Figure(go.Pie(labels=opts, values=values, hole=0.4))
            pie.update_layout(
                title=q,
                margin=dict(t=150, b=40, l=40, r=40)  # Add more margin to avoid overlap
            )
            pie_charts.append(pio.to_html(pie, full_html=False))
    else:
        pie_charts = [None]*4

    # Histograms with range sliders
    hist_start = go.Figure(go.Histogram(x=df['days_to_start'], nbinsx=20))
    hist_start.update_layout(
        title='Days to Start Task',
        xaxis=dict(title='Days', rangeslider=dict(visible=True)),
        yaxis_title='Count'
    )

    hist_complete = go.Figure(go.Histogram(x=df['days_to_complete'].dropna(), nbinsx=20))
    hist_complete.update_layout(
        title='Days to Complete Task',
        xaxis=dict(title='Days', rangeslider=dict(visible=True)),
        yaxis_title='Count'
    )

    # Platform boxplot for Days to Start
    bx = go.Figure()
    for plat, sub in df.explode('platforms').groupby('platforms'):
        bx.add_trace(go.Box(y=sub['days_to_start'], name=plat))
    bx.update_layout(title='Days to Start by Platform', yaxis_title='Days')

    # Correlation heatmap
    corr = df[['days_to_start','days_to_complete','active_duration','total_duration','total_changes']].corr()
    hm = go.Figure(go.Heatmap(z=corr.values, x=corr.columns, y=corr.index, colorscale='Viridis'))
    hm.update_layout(title='Correlation Matrix')

    # CSV required headers
    csv_headers = [
        'key', 'created_date', 'started_date', 'completed_date',
        'active_duration', 'total_duration',
        'ios', 'android', 'tvos', 'roku', 'xbox', 'tizen',
        'design_changes', 'config_changes', 'store_changes'
    ]

    # Pass everything to template
    return render_template('dashboard.html',
        hist_start=pio.to_html(hist_start, full_html=False),
        hist_complete=pio.to_html(hist_complete, full_html=False),
        box=pio.to_html(bx, full_html=False),
        heatmap=pio.to_html(hm, full_html=False),
        survey_questions=SURVEY_QUESTIONS,
        survey_options=SURVEY_OPTIONS,
        show_user_form=show_user_form,
        new_user_key=new_user_key,
        pie_charts=pie_charts,
        form_message=form_message,
        filename=filename,
        csv_headers=csv_headers
    )

@bp.route('/survey_answers', methods=['GET', 'POST'])
def survey_answers_view():
    # Admin password protection
    if 'admin_authenticated' not in session:
        if request.method == 'POST' and request.form.get('admin_password'):
            if request.form['admin_password'] == ADMIN_PASSWORD:
                session['admin_authenticated'] = True
                session.permanent = True  # Make session permanent for admin
            else:
                return render_template_string('<div class="container py-4"><h2>Admin Login</h2><form method="post"><input type="password" name="admin_password" class="form-control mb-2" placeholder="Admin Password" required><button class="btn btn-primary" type="submit">Login</button><div class="text-danger mt-2">Incorrect password.</div></form></div>')
        else:
            return render_template_string('<div class="container py-4"><h2>Admin Login</h2><form method="post"><input type="password" name="admin_password" class="form-control mb-2" placeholder="Admin Password" required><button class="btn btn-primary" type="submit">Login</button></form></div>')
    answers = []
    if os.path.exists(SURVEY_PATH):
        with open(SURVEY_PATH, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                answers.append(row)
    message = None
    if request.method == 'POST' and 'action' in request.form:
        action = request.form.get('action')
        key = request.form.get('key')
        if action == 'delete' and key:
            # Remove only the first matching entry and rewrite file
            deleted = False
            new_answers = []
            for row in answers:
                if not deleted and row['key'] == key:
                    deleted = True
                    continue  # skip this row (delete only first occurrence)
                new_answers.append(row)
            answers = new_answers
            with open(SURVEY_PATH, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['key','q1','q2','q3','q4'])
                writer.writeheader()
                writer.writerows(answers)
            message = f"Deleted survey for {key}."
        elif action == 'edit' and key:
            # Update entry
            for row in answers:
                if row['key'] == key:
                    row['q1'] = request.form.get('q1')
                    row['q2'] = request.form.get('q2')
                    row['q3'] = request.form.get('q3')
                    row['q4'] = request.form.get('q4')
            with open(SURVEY_PATH, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['key','q1','q2','q3','q4'])
                writer.writeheader()
                writer.writerows(answers)
            message = f"Edited survey for {key}."
    return render_template('survey_answers.html', answers=answers, survey_questions=SURVEY_QUESTIONS, survey_options=SURVEY_OPTIONS, message=message)

# Optionally, add CORS headers for AJAX POSTs from mobile/public
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

app.register_blueprint(bp)

# Only run the dev server if not running under gunicorn
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)