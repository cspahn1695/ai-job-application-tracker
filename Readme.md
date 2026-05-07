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


routes.py also inclues the profile_job_search() function, which determines what case the user wants to select (location + title, skills/education/experience, or both), determines the max # of jobs to return, calls the fetch_jobs() function, ranks these jobs using  the rank_jobs function, and puts the top ranked jobs in payload (# of jobs in payload equals limit). For instance, if mode == title_location, then the (optional) city and keywords are passed to fetch_jobs().
```python
class ProfileJobSearchMode(str, Enum):
    title_location = "title_location"
    profile = "profile"
    both = "both"
```

```python
@router.get("/profile-job-search")
async def profile_job_search(
    mode: ProfileJobSearchMode,
    city: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
):
```

```python
settings = await get_app_settings()
limit = max(1, min(50, int(settings.max_recommend_jobs)))
rpp = max(20, min(50, limit))
```

```python
if mode == ProfileJobSearchMode.title_location:
    t = (title or "").strip()

    jobs = fetch_jobs(city, keywords=t, results_per_page=rpp)

    payload = [_job_payload_entry(j, None) for j in jobs[:limit]]

    return payload
```

```python
if mode == ProfileJobSearchMode.profile:
    bg = await Background.find_one(Background.email == email_n)

    user_text = clean_text(
        " ".join(bg.skills + bg.education + bg.experience)
    )

    jobs = fetch_jobs(city, results_per_page=rpp)

    ranked = rank_jobs(user_text, jobs)
```

```python
if mode == ProfileJobSearchMode.both:
    jobs_keywords = fetch_jobs(city, keywords=t, results_per_page=rpp)

    jobs_broad = fetch_jobs(city, results_per_page=rpp)

    combined = _dedupe_jobs_by_url(jobs_keywords + jobs_broad)

    ranked = rank_jobs(user_text, combined)
```

```python
def _dedupe_jobs_by_url(jobs: List[dict]) -> List[dict]:
    seen = set()
    out: List[dict] = []

    for j in jobs:
        u = (j.get("url") or "").strip()
        key = u if u else f"{j.get('title')}|{j.get('company')}"

        if key in seen:
            continue

        seen.add(key)
        out.append(j)

    return out
```

Our app also has authentication routes (in auth_routes.py), including routes for finding user by email, registering, logging in, and creating an admin. When registering, our app hashes the pw; when signing in, our app generates a jwt web token. The route for creating an admin is very similar to that for creating a basic user account, with the main difference being that, for an admin account, is_admin = true. When creating an admin, the admin must be created from the admin's account (unless an admin doesn't exist yet). Of course, when creating the admin, the password is hashed.
```python
def _norm_email(value: str) -> str:
    return (value or "").strip().lower()
```

```python
async def _find_user_by_email(value: str):
    e = _norm_email(value)
    if not e:
        return None

    user = await User.find_one(User.email == e)
    if user:
        return user

    return await User.find_one(
        {"email": {"$regex": f"^{re.escape(value.strip())}$", "$options": "i"}}
    )
```

```python
@router.post("/register")
async def register(user: UserCreate):
    email = _norm_email(str(user.email))
    existing = await _find_user_by_email(email)

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(
        email=email,
        password=hash_password(user.password),
        is_admin=False,
    )

    await new_user.insert()
    return {"message": "User created"}
```

```python
@router.post("/login", response_model=TokenResponse)
async def login(user: UserLogin):
    email = _norm_email(str(user.email))
    db_user = await _find_user_by_email(email)

    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    is_admin = getattr(db_user, "is_admin", False)
    token, expire = create_access_token(
        {"email": email, "role": "admin" if is_admin else "user"}
    )
```

```python
@router.post("/bootstrap-admin")
async def bootstrap_admin(req: BootstrapAdminRequest):
    if req.bootstrap_secret != _bootstrap_secret():
        raise HTTPException(status_code=403, detail="Invalid bootstrap secret")

    existing_admin = await User.find_one(User.is_admin == True)
    if existing_admin:
        raise HTTPException(
            status_code=400,
            detail="An admin already exists. Use create-admin from an admin account.",
        )

    admin = User(
        email=_norm_email(str(req.email)),
        password=hash_password(req.password),
        is_admin=True,
    )
    await admin.insert()
```

```python
@router.post("/create-admin")
async def create_admin(req: CreateAdminRequest):
    actor = await _find_user_by_email(str(req.admin_email))

    if not actor or not verify_password(req.admin_password, actor.password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")

    if not getattr(actor, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")

    new_admin = User(
        email=_norm_email(str(req.new_email)),
        password=hash_password(req.new_password),
        is_admin=True,
    )

    await new_admin.insert()
```

Our jobs_api.py page resolves adzuna redirect commands and formats redirect urls correctly. Additionally, it contains the main function that fetches jobs from adzuna. The function configures parameters of return jobs, including id, key, etc; the jobs are officially retrieved from adzuna using res = requests.get(url, params=params). From there, the title, company, location, search city, description, and url of each job is appended to the job object. The jobs are returned, and the fetch_jobs function is called from the profile_job_search() function for each of the 3 cases: location + title, skills/education/experience, or both.
```python
params = {
    "app_id": ADZUNA_APP_ID,
    "app_key": ADZUNA_API_KEY,
    "what": keywords,
    "results_per_page": results_per_page,
    "content-type": "application/json",
}
```

```python
where = (city or "").strip()
if where:
    params["where"] = where

res = requests.get(url, params=params)
data = res.json()
```

```python
for item in data.get("results", []) or []:
    loc = _display_location(item)
    if not loc and search_city:
        loc = search_city

    jobs.append(
        {
            "title": item.get("title"),
            "company": _company_display(item),
            "location": loc,
            "search_city": search_city or None,
            "description": item.get("description"),
            "url": _listing_url_from_adzuna_item(item),
        }
    )
```

```python
def _listing_url_from_adzuna_item(item: Dict[str, Any]) -> str:
    direct = (item.get("url") or "").strip()
    if direct:
        return direct
    return (item.get("redirect_url") or "").strip()
```

```python
def _resolve_adzuna_redirect(redirect_url: str, timeout: float = 5.0) -> str:
    u = (redirect_url or "").strip()
    if not u:
        return u

    try:
        with requests.get(
            u,
            allow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": _DEFAULT_UA},
            stream=True,
        ) as resp:
            if resp.status_code >= 400:
                return u
            final = (resp.url or u).strip()

        if final and final != u:
            return final
    except (requests.RequestException, OSError) as exc:
        logger.info("Adzuna redirect resolve failed for %s: %s", u, exc)

    return u
```

Our app also includes jwt.py, which handles JSON Web Token (JWT) creation and validation for user authentication. The API does not store server-side sessions; instead, users authenticate by sending an Authorization: Bearer <token> header with requests to protected routes. The create_access_token() function creates a JWT token containing the user email, role, and expiration timestamp. The expiration timestamp is embedded directly into the token so that tokens automatically expire after a specified time period without requiring a logout endpoint on the backend. The verify_access_token() function decodes and validates the token using the SECRET_KEY and HS256 algorithm. If the token is invalid, expired, or missing required fields such as email or role, an HTTP 401 Unauthorized error is returned. The TokenData model is used to structure validated token information, including the email, role, and expiration datetime of the current user.
```python
token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
```

The app also includes settings_routes.py, which manages global application settings stored in MongoDB using a singleton-style AppSettings document. The main purpose of this route file is to control the maximum number of recommended jobs returned from the Adzuna API. The get_max_recommend_jobs() route allows users to retrieve the current maximum recommendation limit, while the update_max_recommend_jobs() route allows an administrator to modify this limit. To ensure security, the _require_admin() function validates the admin email and password and checks whether the user has administrator privileges before any settings can be updated. Additionally, the route validates that the maximum number of recommended jobs remains within an acceptable range between MIN_JOBS and MAX_JOBS_CAP. The settings are then saved directly into MongoDB so they persist across application restarts.
```python
@router.get("/max-recommend-jobs")
@router.put("/max-recommend-jobs")
if not user.is_admin:
    raise HTTPException(status_code=403, detail="Admin access required")
```

test_adzunaAPI.py tests the real Adzuna job search, settings, and ranking logic without making live API calls. The test_fetch_jobs_maps_payload_and_clamps_results_per_page() function uses a fake response object and patches requests.get so the test can verify that fetch_jobs() correctly builds the Adzuna API request, sends the correct city and keyword parameters, and limits results_per_page to the maximum allowed value of 50. The test also checks that the returned job object correctly includes the job title, company, location, search city, and URL. Another test checks that if the Adzuna result does not include a location, the app falls back to using the search city as the displayed location.
```python
with patch("jobs_api.requests.get", side_effect=fake_get):
    jobs = routes.fetch_jobs("Iowa City", keywords="backend engineer", results_per_page=999)
```

test_adzunaAPI.py also tests the global app settings logic. The test_get_app_settings_returns_existing_document() test confirms that the app returns an existing AppSettings document when one is already stored, while test_get_app_settings_creates_default_when_missing() confirms that a default settings document is created when none exists yet. Finally, this test file checks the rank_jobs() function to make sure jobs with stronger matches to the user’s skills are ranked higher than less relevant jobs. For example, a backend Python engineering job should score higher than a graphic design job when the user profile includes Python, FastAPI, SQL, Docker, REST API, and backend development skills. The final test also verifies that empty user profile text returns a score of 0.0 instead of crashing.
```python
ranked = routes.rank_jobs(user_text, jobs)
assert ranked[0]["job"]["title"] == "Backend Python Engineer"
```

Our app also includes test_application.py, which tests the core application CRUD operations, filtering logic, and profile-based job search features of the backend. This test file uses FastAPI’s TestClient along with mocked database objects to simulate real backend behavior without requiring a live MongoDB connection. A FakeApplication class is used to mimic the behavior of Beanie application documents, while a fake authenticated user is injected into the routes using dependency overrides. The test_application_crud_and_filters() function verifies that users can create, retrieve, update, filter, and delete applications correctly. For example, the test confirms that filtering by application status or company name returns only the matching applications and that deleted applications can no longer be retrieved.
```python
create_1 = client.post("/applications/", json=payload_1)
update_res = client.put(f"/applications/{app_id}", json=update_payload)
```

test_application.py also tests the profile_job_search() route for all supported search modes. The test_profile_job_search_title_location_mode() function verifies that title and location searches correctly call fetch_jobs() and return matching jobs without ranking scores. The test_profile_job_search_profile_mode() function tests profile-based AI ranking by mocking a user background containing skills, education, and experience. The test confirms that backend engineering jobs receive higher ranking scores than unrelated jobs such as graphic design positions. Finally, the test_profile_job_search_both_mode_merges_and_dedupes() function verifies that keyword-based and profile-based job results are merged together and duplicate jobs are removed using the job URL as a unique identifier.
```python
assert data[0]["job"]["title"] == "Backend Engineer"
assert len(data) == 3
```

Our app also includes background_routes.py, which manages each user’s background profile information, including skills, education, experience, and saved jobs. The routes in this file use the logged-in user’s email address to retrieve or modify profile information stored in MongoDB. The get_background() route retrieves a user’s background profile and lazily creates a new empty Background document if one does not already exist. The add_item() and delete_item() routes allow users to dynamically add or remove items from the skills, education, and experience sections. These routes first validate that the requested section is valid and that empty items are not added to the database.
```python
@router.get("/{email}")
@router.post("/{email}/{section}")
@router.delete("/{email}/{section}")
```

background_routes.py also manages saved jobs functionality. The add_saved_job() route allows users to bookmark jobs returned from the Adzuna API, while the delete_saved_job() route removes saved jobs from the user profile. To prevent duplicate job bookmarks, the add_saved_job() function compares URLs before inserting a new saved job. If the same URL already exists in the saved_jobs list, the route simply returns the existing background document without creating duplicates. The routes support multiple endpoint variations so the frontend can either post directly to the saved-jobs collection or append /item to the request URL.
```python
for job in bg.saved_jobs:
    existing_url = (getattr(job, "url", "") or "").strip()
    if existing_url == normalized_url:
        return bg
```

Our app also includes main.py, which serves as the main FastAPI entrypoint and connects together the backend routes, frontend pages, MongoDB initialization, and uploaded resume files. The file first initializes the FastAPI application and configures CORS middleware so the frontend can communicate with the backend from different origins during development. The on_startup() function initializes the MongoDB connection by calling init_mongo() whenever the application starts. The home() route connects the backend to the frontend by returning login.html as the default page when users visit the root URL.
```python
@app.on_event("startup")
async def on_startup():
    await init_mongo()

@app.get("/")
async def home():
    return FileResponse("frontend/login.html")
```

main.py also registers all major backend route groups, including the application routes, authentication routes, background profile routes, and settings routes. These routers are connected using app.include_router(), allowing the frontend to access all backend CRUD, authentication, AI recommendation, and profile management functionality through FastAPI endpoints.
```python
app.include_router(router)
app.include_router(auth_router)
app.include_router(background_router)
app.include_router(settings_router)
```

Finally, main.py mounts both the frontend static files and uploaded resume files using FastAPI’s StaticFiles system. The frontend folder is mounted at /static so HTML, JavaScript, and CSS files can be served directly to users. Additionally, uploaded resumes stored in the uploads directory are exposed through the /uploads route so users can download resumes associated with their applications. The routes are registered before the static mounts to ensure API endpoints are not accidentally overridden by the frontend static file handler.
```python
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
```

important other parts to include in Readme.md file: jwt, settings_routes, test_adzunaAPI.py, test_application.py, background_routes.py, main.js
