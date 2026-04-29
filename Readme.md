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