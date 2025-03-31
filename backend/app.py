import os
import json
import uuid
import jwt
import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

# Import your existing classes
from contract_analyzer import ContractAnalyzer, DatabaseManager

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

# Database manager
db_manager = DatabaseManager()

# Create users table if it doesn't exist
def create_users_table():
    with db_manager.conn.cursor() as cursor:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
        ''')
        
        # Add user_id column to documents table if it doesn't exist
        cursor.execute('''
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='documents' AND column_name='user_id'
        ''')
        
        if cursor.fetchone() is None:
            cursor.execute('ALTER TABLE documents ADD COLUMN user_id INTEGER')
            
        db_manager.conn.commit()

create_users_table()

# Helper functions
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # OPTIONS requests don't need authentication
        if request.method == 'OPTIONS':
            return {'message': 'OK'}, 200
            
        token = None
        
        # Get token from header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            # Decode token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            
            # Get user from database
            with db_manager.conn.cursor() as cursor:
                cursor.execute('SELECT * FROM users WHERE id = %s', (data['userId'],))
                user = cursor.fetchone()
                
                if not user:
                    return jsonify({'message': 'User not found'}), 401
                    
                # Add user info to request context
                request.user = {
                    'id': user[0],
                    'name': user[1],
                    'email': user[2]
                }
                
        except Exception as e:
            return jsonify({'message': 'Invalid token', 'error': str(e)}), 401
            
        return f(*args, **kwargs)
    
    return decorated

# Authentication routes
@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return {'message': 'OK'}, 200
        
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Check if user already exists
    with db_manager.conn.cursor() as cursor:
        cursor.execute('SELECT * FROM users WHERE email = %s', (data['email'],))
        if cursor.fetchone():
            return jsonify({'message': 'User already exists'}), 409
    
    # Hash password
    hashed_password = generate_password_hash(data['password'])
    
    # Create new user
    with db_manager.conn.cursor() as cursor:
        cursor.execute(
            'INSERT INTO users (name, email, password, created_at) VALUES (%s, %s, %s, %s) RETURNING id',
            (data['name'], data['email'], hashed_password, datetime.datetime.now())
        )
        user_id = cursor.fetchone()[0]
        db_manager.conn.commit()
    
    return jsonify({'message': 'User created successfully', 'userId': user_id}), 201

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return {'message': 'OK'}, 200
        
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing email or password'}), 400
    
    # Find user
    with db_manager.conn.cursor() as cursor:
        cursor.execute('SELECT * FROM users WHERE email = %s', (data['email'],))
        user = cursor.fetchone()
        
        if not user or not check_password_hash(user[3], data['password']):
            return jsonify({'message': 'Invalid credentials'}), 401
        
        # Generate token
        token = jwt.encode({
            'userId': user[0],
            'email': user[2],
            'name': user[1],
            'exp': datetime.datetime.now() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({'token': token, 'user': {'id': user[0], 'name': user[1], 'email': user[2]}}), 200

# Document routes
@app.route('/api/documents/upload', methods=['POST', 'OPTIONS'])
@token_required
def upload_document():
    if request.method == 'OPTIONS':
        return {'message': 'OK'}, 200
        
    # Check if file part exists
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
        
    file = request.files['file']
    
    # Check if filename is empty
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
        
    # Check file extension
    allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
    if not '.' in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return jsonify({'message': 'File type not allowed'}), 400
    
    # Save file
    filename = secure_filename(file.filename)
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)
    
    # Analyze document
    analyzer = ContractAnalyzer(db_manager)
    analysis = analyzer.analyze_document(file_path)
    
    # Update document with user_id
    with db_manager.conn.cursor() as cursor:
        cursor.execute(
            'UPDATE documents SET user_id = %s WHERE id = %s',
            (request.user['id'], analysis['document_id'])
        )
        db_manager.conn.commit()
    
    return jsonify(analysis), 200

@app.route('/api/documents/<int:document_id>', methods=['GET', 'OPTIONS'])
@token_required
def get_document_analysis(document_id):
    if request.method == 'OPTIONS':
        return {'message': 'OK'}, 200
        
    # Check if document exists and belongs to user
    with db_manager.conn.cursor() as cursor:
        cursor.execute(
            'SELECT * FROM documents WHERE id = %s AND user_id = %s',
            (document_id, request.user['id'])
        )
        document = cursor.fetchone()
        
        if not document:
            return jsonify({'message': 'Document not found or access denied'}), 404
    
    # Get risk analysis for document
    with db_manager.conn.cursor() as cursor:
        cursor.execute(
            '''
            SELECT id, clause_type, clause_text, risk_score, risk_explanation, analysis_date
            FROM risk_analysis
            WHERE document_id = %s
            ''',
            (document_id,)
        )
        risk_analyses = cursor.fetchall()
    
    # Format important clauses
    important_clauses = []
    for analysis in risk_analyses:
        risk_level = "high" if analysis[3] >= 0.7 else "medium" if analysis[3] >= 0.4 else "low" if analysis[3] >= 0.1 else "negligible"
        
        important_clauses.append({
            'type': analysis[1],
            'text': analysis[2],
            'risk_score': analysis[3],
            'risk_level': risk_level,
            'explanation': analysis[4]
        })
    
    # Prepare response
    response = {
        'document_id': document_id,
        'filename': document[1],
        'document_type': document[2],
        'upload_date': document[3].strftime('%Y-%m-%d %H:%M:%S'),
        'metadata': document[5],
        'important_clauses': important_clauses,
        'overall_risk_score': sum(clause['risk_score'] for clause in important_clauses) / len(important_clauses) if important_clauses else 0,
        'analysis_date': risk_analyses[0][5].strftime('%Y-%m-%d %H:%M:%S') if risk_analyses else None,
        'summary': f"Analysis of {document[1]} ({document[2]})"  # Simple summary as a fallback
    }
    
    return jsonify(response), 200

@app.route('/api/documents/user', methods=['GET', 'OPTIONS'])
@token_required
def get_user_documents():
    if request.method == 'OPTIONS':
        return {'message': 'OK'}, 200
        
    # Get all documents for the user
    with db_manager.conn.cursor() as cursor:
        cursor.execute(
            '''
            SELECT d.id, d.filename, d.doc_type, d.upload_date, d.metadata,
                   (SELECT AVG(risk_score) FROM risk_analysis WHERE document_id = d.id) as avg_risk
            FROM documents d
            WHERE d.user_id = %s
            ORDER BY d.upload_date DESC
            ''',
            (request.user['id'],)
        )
        documents = cursor.fetchall()
    
    # Format response
    response = []
    for doc in documents:
        response.append({
            'document_id': doc[0],
            'filename': doc[1],
            'document_type': doc[2],
            'upload_date': doc[3].strftime('%Y-%m-%d %H:%M:%S'),
            'overall_risk_score': float(doc[5]) if doc[5] is not None else 0,
            'analysis_date': doc[3].strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify(response), 200

@app.route('/api/documents/<int:document_id>/query', methods=['POST', 'OPTIONS'])
@token_required
def query_document_api(document_id):
    if request.method == 'OPTIONS':
        return {'message': 'OK'}, 200
        
    data = request.get_json()
    
    if not data or not data.get('query'):
        return jsonify({'message': 'Missing query parameter'}), 400
    
    # Check if document exists and belongs to user
    with db_manager.conn.cursor() as cursor:
        cursor.execute(
            'SELECT * FROM documents WHERE id = %s AND user_id = %s',
            (document_id, request.user['id'])
        )
        document = cursor.fetchone()
        
        if not document:
            return jsonify({'message': 'Document not found or access denied'}), 404
    
    # Query document
    analyzer = ContractAnalyzer(db_manager)
    result = analyzer.query_document(data['query'], document_id)
    
    return jsonify(result), 200

@app.route('/api/documents/<int:document_id>/download', methods=['GET', 'OPTIONS'])
@token_required
def download_document(document_id):
    if request.method == 'OPTIONS':
        return {'message': 'OK'}, 200
        
    # Check if document exists and belongs to user
    with db_manager.conn.cursor() as cursor:
        cursor.execute(
            'SELECT filename FROM documents WHERE id = %s AND user_id = %s',
            (document_id, request.user['id'])
        )
        document = cursor.fetchone()
        
        if not document:
            return jsonify({'message': 'Document not found or access denied'}), 404
    
    # Find the document file
    filename = document[0]
    # This assumes documents are stored with the same name as in database
    # You may need to adapt this to your actual storage strategy
    for file in os.listdir(app.config['UPLOAD_FOLDER']):
        if filename in file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
            return send_file(file_path, as_attachment=True, download_name=filename)
    
    return jsonify({'message': 'File not found'}), 404

@app.route('/api/documents/<int:document_id>/report', methods=['GET', 'OPTIONS'])
@token_required
def download_report(document_id):
    if request.method == 'OPTIONS':
        return {'message': 'OK'}, 200
        
    # Check if document exists and belongs to user
    with db_manager.conn.cursor() as cursor:
        cursor.execute(
            'SELECT * FROM documents WHERE id = %s AND user_id = %s',
            (document_id, request.user['id'])
        )
        document = cursor.fetchone()
        
        if not document:
            return jsonify({'message': 'Document not found or access denied'}), 404
    
    # Get risk analysis for document
    with db_manager.conn.cursor() as cursor:
        cursor.execute(
            '''
            SELECT id, clause_type, clause_text, risk_score, risk_explanation, analysis_date
            FROM risk_analysis
            WHERE document_id = %s
            ''',
            (document_id,)
        )
        risk_analyses = cursor.fetchall()
    
    # Format report data
    report_data = {
        'document_id': document_id,
        'filename': document[1],
        'document_type': document[2],
        'upload_date': document[3].strftime('%Y-%m-%d %H:%M:%S'),
        'clauses': []
    }
    
    for analysis in risk_analyses:
        risk_level = "high" if analysis[3] >= 0.7 else "medium" if analysis[3] >= 0.4 else "low" if analysis[3] >= 0.1 else "negligible"
        
        report_data['clauses'].append({
            'type': analysis[1],
            'text': analysis[2],
            'risk_score': analysis[3],
            'risk_level': risk_level,
            'explanation': analysis[4]
        })
    
    # Create a temporary JSON file
    temp_filename = f"report_{document_id}.json"
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
    
    with open(temp_path, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    return send_file(temp_path, as_attachment=True, download_name=f"analysis_report_{document[1]}.json")

if __name__ == '__main__':
    app.run(debug=False, port=5000)