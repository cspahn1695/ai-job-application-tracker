python -m venv venv
./venv/Script/activate
pip install pydantic
![alt text](image-22.png)
![alt text](image-23.png)
The main purpose of the assignment was to build a web app using FASTAPI and demonstrate use of get/post/put/delete (CRUD) methods. The get method on my frontend, getAllApplications(), first obtains the company and status the user wants to restrict the search to. Then it establishes communication with the backend using xhr. Render applications creates the appDiv.innerHTML link, and the values in it are obtained from the backend using a xhr GET request.
![alt text](image.png)
The deleteApplications(id) function also first stablishes communication with backend. Then, it creates a DELETE request for the application of the specific id. 
![alt text](image-1.png)
My editApplications(id) function (for frontend) prompts the user for new values of company, role, status, priority, recruitmentinfo, and jobpostinglink. Once communication is made with backend, the list is refreshed, and a PUT request updates the values of all these parameters. a JSON string of all these values is sent to the backend. Then, getAllApplications() is called once more to refresh them.
![alt text](image-2.png)
The createApplication() function creates a new application by first initializing new values for company, role, status, priority, recruitmentinfo, resumeFile, and jobpostinglink. Then, a post request is sent to the backend with all these new values.
![alt text](image-3.png)
I also have an uploadResume(appId, file) function, which first takes the resume (file) and adds it to a file formData. a POST method is then created for the application of appId, and the resume is sent to the backend using xhr.send.
![alt text](image-4.png)
On the frontend, I also have a getMatchScore(appId) function, which simply obtains the match score, matched skills, and missing skills from the backend and prints them to the frontend. 
![alt text](image-5.png)
Finally, on the frontend, I have a function updateStatistics which computes the interViewRate and offerRate, keeps track of status and priority counts, and calls 2 associated functions which print bar and pi charts to the screen. The bar graph shows the # of jobs in each status category (applied, interview, offer, rejected), and the pi chart shows the % of jobs in each priority (high, medium, low).
![alt text](image-25.png)
![alt text](image-6.png)
![alt text](image-7.png)
On my backend, my main.py file initializes the FastAPI app, initializes CORS settings, connects backend to the frontend, creates database tables, and connects to my router in routes.py (responsible for CRUD methods). It is important that I import UploadFile from fastapi, since my web app involves uploading resumes.
![alt text](image-8.png)
My routes.py file includes all CRUD methods for the backend. For instance, it includes a create_application() post ethod, which creates a new app using the parameters defined in models.py, adds them to the database, commits the database, refreshes the database, and returns the new application to the frontend.
![alt text](image-9.png)
It also includes a post function for a specific appid, which basically allows a user to attach a resume to a pre-existing job application. First, it queries the database to find the appropriate application. Then, a file path is made based off the file sent to the function. the contents from the file sent to the function are written (binary) to the file path. Then, the file path is attached to application.resume_path (a parameter defined in models.py). Finally, the database is committed, and a relevant 'success' message is returned.
![alt text](image-10.png)
Of course, in the backend I also have a get all applications method, and at first it obtains all apps in the database. However, it has special query options for status and company. For instance, if a user specifies that status=applied and company=Boeing, the search will only return applications for which the user applied to Boeing. The results of the query are returned.
![alt text](image-11.png)
The backend also has a get method that returns a single application when the user enters in an acceptable appid (an HTTPException is returned if the user enters an invalid id). The application is returned.
![alt text](image-12.png)
On the backend, thre is also a put (update) method. Basically, a specific app_id is queried, and the values of company, role, status, priority, recruitmentinfo, and jobpostinglink returned from the frontend are updated in the backend (using updated_app.__ values). The database is committed and refreshed.
![alt text](image-26.png)
![alt text](image-13.png)
The backend also includes a delete_application function, which basically operates the same as the delete_todo method used in class. It queries the DB for the application of id app_id, and then, upon finding it, deletes it from the database.
![alt text](image-14.png)
My routes.py backend also includes a get_Match_Score function, whcih returns the match_score, matched_skills, and missing_skills to the frontend. Many of the functions it uses, such as extract_resume/job_text, compute_match_score, and analyze_skill_gap, are defined in ai_matcher.py. The method first checks that the application being queried (of id app_id) exists, that it has a resume, and that it has a job posting. If so, the texts from the resume and job posting are extracted (with non-important info being removed), and the skills/similarities in the 2 texts in skills_DB are compared using compute_match_score. Then, the specific texts included in both texts and those included in just the job posting are determined using the analyze_skill_gap function. Finally, the overall AI score, matched_skills, and missing_skills are returned.
![alt text](image-24.png)
![alt text](image-15.png)
My ai_matcher.py file contains the important methods that my get_Match_Score function in routes.py uses. For instance, it has functions to extract text from the resume and job description. My extract_job_text function extracts text from the specific URL and tries to match the URL to a linkedin job posting; if it fails, it just uses the original URL. Finally, the BeautifulSoup function creates a parse tree of the response.text, and this parse tree is returned. From there, methods can be used to search and extract content from the tree.
![alt text](image-16.png)
The clean_text function makes all text lowercase and reformats it for consistency. The extract_Skills function takes the text in "text" and sees which skills in SKILLS_DB it includes. These skills are then returned. The list of SKILLS_DB can be expanded as the web app is made to accommodate more types of resumes/job postings.
![alt text](image-17.png)
The compute_match_score function(resume_text, job_text) first cleans the text in the resume and job posting using the clean_text function. The job posting size is limited to the most useful material. A vectorizer is created to represent a matrix with the resume and job posting data, and it matches similar phrases (ex. "machine learning" and "computer vision"). Finally, the cosine_similarity function (the cosine_simularity function comes from the sklearn package) compares the resume and job posting texts from the vector and returns an array of matrices detailing how similar they are. The first element rperesents the overall similarity between the job posting and resume. I found these values to be strangely small in my testing, so for the sake of this web app, I multiplied it by 300 to make it more real-world.
![alt text](image-18.png)
My analyze_skill_gap(resume_text, job_text) first extracts skills from the resume and those in the job posting. Then, it compares both sets of skills, and the skills in both texts are referred to as matched_skills. Those only in the job posting are missing_skills. The skills are returned and used in the get_Match_Score function to be sent to the frontend.
![alt text](image-19.png)
My index.html file defines all the main parameter types used in my web app, including company, role, recruitmentinfo, resume file, jobpostinglink, and status. It includes the specific allowed values for 'status' and 'priority'. It includes the buttons for creating an application, searching a company, filtering by status, etc. It loads the bootstrap javascript bundle for interactive components. It also loads the chart.js library used to generate stats charts. It creates a Statistics section that shows total applications, interview rate, offer rate, a status bar chart, and a priority pi chart. It also has a link to main.js (CRUD methods for the frontend). It also has a link to style.css.
![alt text](image-20.png)
I just use an in-memory database (a list) for this project (I have DATABASE_URL = "sqlite:///:memory:"). My SessionLocal includes autocommit=false (if a CRUd method makes changes, it needs to commit them manually) and autoflush=false. Then, database.py includes a method called get_db(), which allows a CRUD method to open a local database session. when the CRUd method is using the database, the get_db() method just yields the database. Once the method is finished using it, the get_db() method closes the database.
![alt text](image-21.png)



python -m venv venv
.\venv\Scripts\Activate
pip install fastapi beanie uvicorn bcrypt pydantic[email] pydantic-sttings pyjwt python-multipart httpx pytest
uvicorn main:app --reload