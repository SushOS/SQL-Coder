# Scalable Mathematical Computation WebApp with LLM Integration

## Overview

This project is a scalable and robust web application that allows users to:
- **Upload a file** (only CSV and XLSX formats).
- **Extract numerical values** from the file.
- **Send the extracted numerical data** to the backend via an API.
- **Perform mathematical operations** (e.g., average, sum, standard deviation, etc.) on the numbers for each column.
- **Leverage a Language Model (LLM)** (via an open-source model from HuggingFace or similar) to dynamically generate code (SQL queries) for the requested mathematical operation.
- **Store the computed results** in a relational database (MySQL) using a session-id/user-id as the primary key.
- **Display the computation results** on the frontend.

To support high concurrency (e.g., >10,000 concurrent users), the system offloads heavy processing tasks to Celery workers using Redis as the message broker and result backend. This decouples the computationally intensive tasks from the main request–response cycle, ensuring the app remains responsive.

## Features

- **File Upload:** Accepts CSV and XLSX files.
- **Numerical Extraction:** Extracts numerical values using Pandas.
- **Mathematical Operations:** Uses an LLM to dynamically generate SQL queries to compute operations such as average, sum, and standard deviation.
- **Asynchronous Processing:** Offloads file processing to Celery workers with Redis as the broker.
- **Database Storage:** Stores computation results in MySQL using a user-id/session-id as the primary key.
- **Frontend Display:** A React-based interface that allows users to upload files, monitor processing, and view results.
- **Task Status Monitoring:** Provides an API endpoint to check the status of background tasks.

## Architecture

The application is divided into the following layers:

- **Frontend:** A React-based UI (served via `index.html` with Tailwind CSS for styling) that:
  - Uploads files.
  - Displays processing status.
  - Allows selection of columns and operations.
  - Shows the computed results and generated SQL query.
  
- **Backend (Flask App):**
  - Provides endpoints for file uploads (`/api/upload`), computation (`/api/compute`), and task status (`/api/task_status/<task_id>`).
  - Uses SQLAlchemy to interact with a MySQL database.
  - Integrates an LLM (via the Groq client or similar) to generate dynamic SQL code.

- **Asynchronous Task Processing:**
  - **Celery** handles heavy file processing in the background.
  - **Redis** acts as the message broker and result backend.

- **Database:**  
  - **MySQL** is used to store extracted numerical data and computed results.

### Architecture Diagram
           +---------------+
           |    Client     |  <-- Web Browser (React UI)
           +---------------+
                  |
                  | HTTP (Upload file, Compute operation, Task Status)
                  v
           +---------------+
           |   Flask API   |  <-- Web Server
           |   (app.py)    |
           +---------------+
                  |         \
         Synchronous         \ Asynchronous Tasks
        Requests, etc         \
                  |            \
                  v             v
           +---------------+      +---------------+
           |   MySQL DB    |<---->|   Celery      |
           | (SQLAlchemy)  |      |   Workers     |
           +---------------+      +---------------+
                                          |
                                          |
                                          v
                                   +---------------+
                                   |    Redis      |  <-- Message Broker & Result Backend
                                   +---------------+

## Prerequisites

- **Python 3.8+**
- **MySQL Server**
- **Redis**
- **pip** for package management

## Installation and Environemnt

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/your-repo.git
   cd your-repo
2. **Setup Virtual Environment**
   ```bash
   conda create --name <env_name> python=<desired_version>

3. **Install Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt

4. **Install and Start Redis**
   ```bash
      brew install redis
      brew services start redis
5. **Configure Environment Variables**
   ```bash
      GROQ_API_KEY
      DATABASE_URL
      CELERY_BROKER_URL
      CELERY_RESULT_BACKEND

## Repository Structure
   ```bash
         MINDFLIX3
         ├── celery_app
         │   ├── backend
         │   │   ├── __pycache__/
         │   │   ├── uploads/ (All the csv/xlsx)
         │   │   ├── .env
         │   │   ├── app.py
         │   │   ├── tasks2.py
         │   ├── frontend
         │   │   ├── index.html
         ├── celery_demo
         │   ├── __pycache__/
         │   ├── async_benchmark.py
         │   ├── sync_benchmark.py
         │   ├── tasks.py
         ├── simple_app
         │   ├── backend
         │   │   ├── __pycache__/
         │   │   ├── uploads/
         │   │   ├── .env
         │   │   ├── app.py
         │   │   ├── requirements.txt
         │   ├── frontend
         │   │   ├── index.html
         ├── commands.txt
         ├── dump.rdb
         ├── readme.md
         ├── requirements.txt
```
## Running Celery Demo
### Demostrating a compariosion between a normal Synchronous task and an Asynchronous task using Celery workers and Redis as message broker.
1. ```bash
   cd celery_demo
2. To check how much time it takes for a synchronous process to execute
   ```bash
   python sync_benchmark.py
3. Start the Celery workers
   ```bash
   celery -A tasks worker --loglevel=info
4. Then run the asynchronous file with the help of the celery workers and redis.
   ```bash
   celery -A tasks worker --loglevel=info
## Comparision Results: 
1. Synchronous Process -> 20 sec 
2. Asynchronous process -> 4 sec

This proves that the code executes 5 times faster in the scenario of a task, which would be more when handling even more heavy tasks.

## Running Simple App
### Running the flask App without the use of Celery workers.
1. ```bash
   cd simple_app
2. ```bash
   cd backend
3. ```bash
   python app.py

## Running Celery App
### Running the flask App with the use of Celery workers and Redis as the message broker.
1. ```bash
   cd celery_app
2. ```bash
   cd backend
3. ```bash
   celery -A app.celery worker --loglevel=info
4. ```bash
   python app.py

## LLM Integration
### Dynamic SQL Generation
The backend leverages an LLM (via the Groq client) to generate SQL queries that compute the requested mathematical operation on the numerical data.
### Flexible Computation
This design supports various operations (e.g., average, sum, standard deviation, count, mean, median, min, max, etc) by dynamically generating the code, ensuring the system is adaptable to future requirements.
### Security Note
API keys and other sensitive information are stored in environment variables (via .env files) and are not hard-coded into the source code.

## Fault Tolerance
1. It may be possible that the LLM is unable to generate the code for the operation demanded by the user, in this case a fall-back mechanism is provided which is predefined, to output the SQL query in the frontend.
2. There are some cases whn the LLM is able to geenrate the SQL query code but that particular code is not compatible with the database which I have used (MySQL). In this case the generated SQL code is printed in the frontend as it is, without computing the result and instad stating that : 'Query is not compatible with the databse.'
3. Even though the code generated by the LLM is a lot of text along with the required SQL query, we perform the necessary post-processing steps to parse and extract only the necessary code and then disply it in the frontend.

## Troubleshooting
1. **Module Not Found:** Ensure the virtual environment is activated and that all dependencies are installed.
2. **Redis Connection Issues:** Verify Redis is running on the correct host and port.
3. **Celery Task Errors:** Ensure that tasks are registered with explicit names and that the Celery worker is started from the correct module.
4. **LLM Issues:** Check API keys and network connectivity if dynamic SQL generation fails.

## Further Enhancements if more time
1. **WSGI Production Server:** It launches 8 worker processes. Each worker process uses 4 threads. The server binds to all available network interfaces (0.0.0.0) on port 5000. The worker processes handle incoming HTTP requests concurrently, distributing the load across multiple CPU cores. The threads within each worker allow for additional concurrency, particularly useful for I/O-bound tasks,
2. **Distributed Session and Caching:** Use Redis for session storage and caching to ensure consistency across multiple application instances.
3. **Horizontal Scaling:** Both the Flask app and Celery workers can be horizontally scaled by deploying multiple instances behind a load balancer (e.g., NGINX).
4. **Containerization and Orchestration:** Package the application into Docker containers and use Kubernetes or Docker Swarm for orchestration and automated scaling.
5. **Monitoring and Logging:** Integrate monitoring (e.g., Prometheus, Grafana) and centralized logging (e.g., ELK Stack) for real-time insights into performance and system health.

## Difficulties I faced in this Assignment
1. I started with a very basic database SQLlite which didn't support a lot of MySQL queries generated by the LLM. SO I had to swith the databse to MySQL.
2. I tried many open-source LLMS for the code generation such star-coder, code-gen, llama3.1, gpt2-medium, distil-gpt2 etc but they didn't produce the SQL code output correctly and even if they did, they did it with lot of hallucinations.
3. I first though that the reason for the hallucinations was a very big input prompt I was giving, but the reason was the inefficient and confusing prompt which didn't follow the desired prompt structure required by the LLM.
4. The code generation process was extremely slow because of lack of compute (didn't have GPU) and also because of the gigantic size of the models. I was downloading 18GB big models from salesforce and other doamins and was executing it on the CPU, expecting fast results...LOL.
5. Then the idea of GROQ striked my mind. I utried different models from GROQ having diffent structures for the input prompts but they often generated a lot of extra text along with the code, which was difficult to parse and print in the frontend.
6. Then I got the idea to use the instruct models, which are specifically good and following instructions in the code genration tasks. I made the desired instruct prompt and did a lot of post-processing of the outputs generated by the LLM. This finally made mt successfull to display the MYSQL code queries in the frontend.
7. Then I had to scale this application of which I didn't have any idea. I explored a lot of techniques to scale the application. I thought of caching of the results computed but then ig it won't be that efficient as when there are a lot of users, they would upload different data individually and commonness between the data is very minimal. So, caching won't be the most beneficial.
8. As a lot of data tables (csv/xlsx) would be uploaded by a huge number of users, optimization should be made in storing the numerical columns of all the different tables. Firstly I though to convert the numerical columns of each table into markdown format and pass that along with the prompt to the LLM, but this would drastically increase the number of tokens in the input and then the LLM would face extreme difficulty in understanding that propmt and return the results. The only way which I could then think of is storing the numerical columns extracted in the MYSQL database and then compute the result using the MySQL query generated by the LLM. But this wouls also create a huge load on the MySQL database due to a large number of files uploaded by large number of users.

## Scaling and Optimization
### How It Works in Practice?
1.	User Uploads a File: The user uploads a file (CSV or XLSX) through the web interface. The Flask API saves the file locally and enqueues the process_file_task with the file path and user ID.
2.	Celery Worker Executes the Task: The Celery worker (running as a separate process) picks up the task from the Redis queue. It processes the file—parsing it, extracting numerical columns, and storing the data into the database. Once the task completes, the result (i.e., the list of numerical columns) is stored and can be queried via the /api/task_status/<task_id> endpoint.
3.	User Continues with Computation: The frontend polls the task status endpoint until it finds that the task is complete. Once complete, the user can select one of the extracted numerical columns and request a mathematical operation. The Flask API then uses an LLM to dynamically generate the corresponding SQL query and execute it to compute the result. The result is saved into the database and displayed on the frontend.

## Summary
### Celery Workers
They are responsible for the asynchronous execution of the process_file_task—which covers the file reading, numeric extraction, and data storage steps.

### Main Flask Process:
Handles incoming HTTP requests, interacts with the LLM for SQL generation, executes computation queries, and serves the frontend pages.

By offloading the heavy file processing to Celery, our architecture ensures that the web server remains responsive and capable of handling high concurrency while the intensive file processing is handled in parallel by dedicated worker processes.

This separation of concerns is key for scaling the application to support more than 10,000 concurrent users and ensuring overall system robustness and fault tolerance.