# My Job Applications Tracking Journal
## CS3980 Final Project, Group 6 Scared Dolphins

Currently, jobseekers are submitting hundreds of job applications just to secure a single offer. We wanted a way to simplify keeping track of the application process, and to manage all of our applications in one place. We designed this web app as a Job Application Journal, where users can insert their current applications, manage these progressions, and discover further opportunities in one place.

``` 
python -m venv venv
./venv/Script/activate
pip install fastapi
pip install pydantic
pip install pymongo
pip install uvicorn
pip install beanie
pip install passlib
pip install bcrypt
pip install openai
pip install pdfminer.six
pip install pyjwt
pip install python-multipart
pip install httpx
pip install pytest

#for macos
pip install certifi

uvicorn main:app --reload
```
The main purpose of the assignment was to build a web app using FASTAPI and demonstrate use of get/post/put/delete (CRUD) methods. 
``` 
pip freeze > requirements.txt
```

App includes basic CRUD methods for posting/putting/getting/deleting applications. Routes.py is the main backend program and includes _app_owner_filter(), which filters applications by the current 
email or id. The _get_current_user function returns the (current) user associated with a specific email.
The _get_owned_applications function finds the application corresponding to a specific app_id and current_user. 
![alt text](image.png)

routes.py also includes CRUD methods for applications, and but for editing applications by uploading the resume, the upload_resume and update_application functions are sufficient to ensure that no other data gets deleted when the resume is updated.
![alt text](image-1.png)
![alt text](image-2.png)

routes.py also inclues the profile_job_search() function, which determines what case the user wants to select (location + title, skills/education/experience, or both), determines the max # of jobs to return, calls the fetch_jobs() function, ranks these jobs using  the rank_jobs function, and puts the top ranked jobs in payload (# of jobs in payload equals limit). For instance, if mode == title_location, then the (optional) city and keywords are passed to fetch_jobs(), and the 

Our app also has authentication routes (in auth_routes.py), including routes for finding user by email, registering, logging in, and creating an admin. When registering, our app hashes the pw; when signing in, our app generates a jwt web token. The route for creating an admin is very similar to that for creating a basic user account, with the main difference being that, for an admin account, is_admin = true. When creating an admin, the admin must be created from the admin's account (unless an admin doesn't exist yet). Of course, when creating the admin, the password is hashed.
![alt text](image-3.png)
![alt text](image-4.png)

Our jobs_api.py page resolves adzuna redirect commands and formats redirect urls correctly. Additionally, it contains the main function that fetches jobs from adzuna. The function configures parameters of return jobs, including id, key, etc; the jobs are officially retrieved from adzuna using res = requests.get(url, params=params). From there, the title, company, location, search city, description, and url of each job is appended to the job object. The jobs are returned, and the fetch_jobs function is called from the profile_job_search() function for each of the 3 cases: location + title, skills/education/experience, or both.
![alt text](image-5.png)

