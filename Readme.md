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

Our app 