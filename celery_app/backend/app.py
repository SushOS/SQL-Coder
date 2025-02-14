import os
import uuid
import pandas as pd
import numpy as np
from flask import Flask, request, session, jsonify, render_template
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, Column, String, Float, Integer, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from dotenv import load_dotenv

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set. Check your .env file.")

print(f"Using DATABASE_URL: {DATABASE_URL}")

# ----------------------------------
# Setup Flask
# ----------------------------------
app = Flask(__name__, template_folder="../frontend")
app.secret_key = os.getenv("SECRET_KEY")

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
ALLOWED_EXTENSIONS = {"csv", "xlsx"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ----------------------------------
# Database Setup (Using MySQL with SQLAlchemy)
# ----------------------------------
# engine = create_engine(DATABASE_URL, echo=False)
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20, echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)
db_session = scoped_session(SessionLocal)

# Table for storing numeric values
# class UploadedValue(Base):
#     __tablename__ = "uploaded_values"
#     id = Column(Integer, primary_key=True)
#     column_name = Column(String(255), index=True)
#     value = Column(Float)

class UploadedValue(Base):
    __tablename__ = "uploaded_values"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), index=True)  # Added to track which user uploaded the data
    column_name = Column(String(255), index=True)
    value = Column(Float)

# Table for storing computed results.
class ComputedResult(Base):
    __tablename__ = "computed_results"
    user_id = Column(String(255), primary_key=True)
    column_name = Column(String(255))
    operation = Column(String(100))
    sql_query = Column(Text)
    result = Column(Text)

Base.metadata.create_all(bind=engine)

# ----------------------------------
# Open-Source LLM Setup (llama-3.1-8b-instant)
# ----------------------------------

from groq import Groq
client = Groq(api_key=groq_api_key)
print("Model loaded successfully.")

# ----------------------------------
# Celery Configuration
# ----------------------------------
from celery import Celery

def make_celery(app):
    # Create a new Celery object and tie it to the Flask app’s context.
    celery = Celery(
        app.import_name,
        backend=app.config["CELERY_RESULT_BACKEND"],
        broker=app.config["CELERY_BROKER_URL"]
    )
    celery.conf.update(app.config)
    
    # Create a subclass of celery.Task that ensures tasks run with the Flask app context.
    class ContextTask(celery.Task):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return super().__call__(*args, **kwargs)
    celery.Task = ContextTask
    return celery

app.config["CELERY_BROKER_URL"] = CELERY_BROKER_URL
app.config["CELERY_RESULT_BACKEND"] = CELERY_RESULT_BACKEND
celery = make_celery(app)

# ----------------------------------
# Utility Functions
# ----------------------------------
def allowed_file(filename):
    """Check if the file has one of the allowed extensions."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_sql_query(column, operation, table_name, user_id):
    # Fallback query if the LLM fails to generate a valid query.
    fallback_query = f"SELECT {operation}(value) FROM uploaded_values WHERE column_name = '{column}' AND user_id = '{user_id}';"
    prompt = (
        "[INST]Your task is to write a MySQL query. "
        "The query must compute the {operation} of the column '{column}' from the table '{table_name}' having user_id : {user_id}. "
        "The table has the following columns: id, column_name, value. "
        "Return ONLY the MySQL query and nothing else, with no additional text or explanation. "
        "The query must start with SELECT.[/INST]"
    ).format(operation=operation, column=column, table_name=table_name, user_id=user_id)
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "SQL code only, no explanation or other text."},
                {"role": "user", "content": prompt}
            ]
        )
        print(f"LLM Output (raw): {response}")
        final_sql_query = response.choices[0].message.content.strip()
        print("The LLM has successfully generated the query.")
        return {"final_sql_query": final_sql_query}
    except Exception as e:
        print("LLM generation failed:", e)
        return {"final_sql_query": fallback_query}

# ----------------------------------
# Celery Task for Processing Files
# ----------------------------------
@celery.task(name='app.process_file_task')
def process_file_task(file_path, user_id):
    """
    Celery task that processes an uploaded file and writes numeric values to the database.
    The task returns the list of numeric columns found.
    """
    import os
    filename = os.path.basename(file_path)
    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as err:
        print(f"Error reading file {file_path}: {err}")
        return {"error": f"Error reading the file: {err}"}
    
    # Extract only numeric columns.
    numeric_df = df.select_dtypes(include=[np.number])
    numeric_columns = [
        col for col in numeric_df.columns
        if col and str(col).strip() != "" and numeric_df[col].notna().any()
    ]
    
    db = SessionLocal()
    # Clear previous data (modify as needed).
    # db.query(UploadedValue).delete()
    # db.commit()

    db.query(UploadedValue).filter(UploadedValue.user_id == user_id).delete()
    db.commit()
    
    for col in numeric_columns:
        for value in numeric_df[col].dropna():
            record = UploadedValue(user_id=user_id, column_name=col, value=float(value))
            db.add(record)
    db.commit()
    db.close()
    print(f"Finished processing file {file_path} for user {user_id}.")
    return {"user_id": user_id, "columns": numeric_columns}

# ----------------------------------
# Endpoint to Check Task Status
# ----------------------------------
@app.route("/api/task_status/<task_id>", methods=["GET"])
def task_status(task_id):
    task = process_file_task.AsyncResult(task_id)
    return jsonify({
        "state": task.state,
        "result": task.result
    })

# ----------------------------------
# Routes
# ----------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request."}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file."}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)
        
        user_id = request.form.get("user_id", "default_user")
        session["user_id"] = user_id

        # Enqueue the file processing task.
        task = process_file_task.delay(file_path, user_id)
        return jsonify({
            "user_id": user_id,
            "message": "File uploaded successfully. Processing is underway in the background.",
            "task_id": task.id
        }), 200
    else:
        return jsonify({"error": "Invalid file type. Please upload a CSV or XLSX file."}), 400

@app.route("/api/compute", methods=["POST"])
def api_compute():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload."}), 400

    column = data.get("column")
    operation = data.get("operation")
    user_id = session.get("user_id", "default_user")
    if not column or not operation or not user_id:
        return jsonify({"error": "Missing required data."}), 400

    table_name = "uploaded_values"
    query_info = generate_sql_query(column, operation, table_name, user_id)
    final_sql_query = query_info["final_sql_query"]

    if not final_sql_query:
        return jsonify({"error": "Error generating SQL query from LLM."}), 500

    computed_value = None
    try:
        conn = engine.connect()
        result_proxy = conn.execute(text(final_sql_query))
        row = result_proxy.fetchone()
        if row and row[0] is not None:
            computed_value = row[0]
    except Exception as e:
        computed_value = "This query is not supported by the database."
    finally:
        conn.close()

    try:
        db = SessionLocal()
        existing = db.query(ComputedResult).filter_by(user_id=user_id).first()
        if existing:
            existing.column_name = column
            existing.operation = operation
            existing.sql_query = final_sql_query
            existing.result = computed_value
        else:
            comp_result = ComputedResult(
                user_id=user_id,
                column_name=column,
                operation=operation,
                sql_query=final_sql_query,
                result=computed_value,
            )
            db.add(comp_result)
        db.commit()
        db_session.remove()
    except Exception as db_e:
        # computed_value = "This query is not supported by the database."
        computed_value = f"{computed_value} (Database error: {db_e})"
        return jsonify({
            "final_sql_query": final_sql_query,
            "result": computed_value
        }), 200
    finally:
        db.close()

    return jsonify({
        "final_sql_query": final_sql_query,
        "result": computed_value
    }), 200

if __name__ == "__main__":
    app.run(debug=True)