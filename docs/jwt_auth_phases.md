# JWT Authentication & RBAC – Implementation Phases

Below is a **step‑by‑step list** of the work required to add a secure JWT authentication system, a custom `User` model with a one‑to‑one `Profile`, and role‑based access control (RBAC) using function‑based views.

---

## Phase 1 – Environment & Dependencies

1. **Create/activate virtual‑env** – `python -m venv venv` (already exists).
2. **Update `requirements.txt** – Append the packages:
   - `djangorestframework`
   - `djangorestframework-simplejwt`
3. **Install packages** – `./venv/Scripts/pip install -r requirements.txt`.
4. **Scaffold the `users` app** – `python manage.py startapp users`.
5. **Register apps in `config/settings.py`** – Add the following to `INSTALLED_APPS`:
   - `"rest_framework"`
   - `"rest_framework_simplejwt"`
   - `"rest_framework_simplejwt.token_blacklist"`
   - `"users"`
6. **Set custom authentication model** – Add `AUTH_USER_MODEL = "users.User"`.
7. **Configure DRF defaults** –
   ```python
   REST_FRAMEWORK = {
       "DEFAULT_AUTHENTICATION_CLASSES": [
           "rest_framework_simplejwt.authentication.JWTAuthentication",
       ],
       "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
   }
   ```
8. **Configure SimpleJWT** –
   ```python
   SIMPLE_JWT = {
       "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
       "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
       "ROTATE_REFRESH_TOKENS": True,
       "BLACKLIST_AFTER_ROTATION": True,
       "AUTH_HEADER_TYPES": ("Bearer",),
   }
   ```
9. **Ensure imports** – `from datetime import timedelta`, `import dj_database_url, os, sys` are present at the top of `settings.py`.

---

## Phase 2 – Data Model Design (User & Profile)

1. **Define `UserRole` enum** – `class UserRole(models.TextChoices): ADMIN = "admin", "Admin"; MANAGER = "manager", "Manager"; USER = "user", "User"`.
2. **Create `UserManager`** – Implements `create_user(email, password, **extra_fields)` and `create_superuser(email, password, **extra_fields)`; superuser gets role `ADMIN`.
3. **Implement `User` model** – Subclass `AbstractBaseUser, PermissionsMixin` with fields:
   - `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
   - `email = models.EmailField(unique=True, db_index=True)`
   - `role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.USER)`
   - `is_active = models.BooleanField(default=True)`
   - `is_staff = models.BooleanField(default=False)`
   - `created_at = models.DateTimeField(auto_now_add=True)`
   - `updated_at = models.DateTimeField(auto_now=True)`
   - `USERNAME_FIELD = "email"`
   - `REQUIRED_FIELDS = []`
4. **Implement `Profile` model** – Fields:
   - `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
   - `first_name = models.CharField(max_length=150, blank=True)`
   - `last_name = models.CharField(max_length=150, blank=True)`
   - `phone = models.CharField(max_length=11, blank=True)`
   - `user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")`
5. **Auto‑create profile** – Use Django's `post_save` signal on `User` to automatically create a linked `Profile` instance when a new user is saved.
6. **Register models in admin (`users/admin.py`)** –
   - Register `User` with `CustomUserAdmin` (using `CustomUserCreationForm` and `CustomUserChangeForm` with `email` as the identifier, `role`, permissions, and timestamps).
   - Attach `ProfileInline` to `CustomUserAdmin` (hidden on the Add page so it does not conflict with the `post_save` signal).
   - Register `Profile` with `ProfileAdmin` displaying `user`, `first_name`, `last_name`, and `phone`.
7. **Create migration** – `python manage.py makemigrations users`.
8. **Apply migration** – `python manage.py migrate` (creates `users_user` and `users_profile` tables).
9. **ERD note** – The diagram shows a one‑to‑one relationship between `User` and `Profile`.

1. **Define `UserRole` enum** – `class UserRole(models.TextChoices): ADMIN = "admin", "Admin" …`.
2. **Create `UserManager`** – Implements `create_user` and `create_superuser`; the superuser is forced to have `role=admin`.
4. **Implement `Profile` model** – Any extra profile fields you need plus a one‑to‑one link:
   ```python
   user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
   ```
5. **Register models in admin** – Custom `UserAdmin` that uses `email` as the identifier; optionally add an inline admin for `Profile`.
6. **Create migration** – `python manage.py makemigrations users`.
7. **Apply migration** – `python manage.py migrate` (creates `users_user` and `users_profile`).
8. **ERD note** – The diagram shows a `User ↔︎ Profile` one‑to‑one relationship.

---

## Phase 3 – Serializers (Function‑Based View Compatible)

- **`EmailTokenObtainPairSerializer`** – Extends SimpleJWT's `TokenObtainPairSerializer`; validates `email` + `password` and adds custom claims (`role`, `email`, `user_id`).
- **`UserRegisterSerializer`** – `ModelSerializer` accepting `first_name`, `last_name`, `email`, and `password`; uses only `email` and `password` for `User` creation (ensuring email uniqueness and hashing the password), and saves `first_name` and `last_name` to the user's `Profile`.
- **`UserSerializer`** – Minimal fields: `id`, `email`, `first_name`, `last_name`, `role`.
- **`ProfileSerializer`** – Serializes the `Profile` model; can be nested inside `UserSerializer` when needed.
- **`LogoutSerializer`** – Accepts a `refresh` token string and blacklists it.
- **`validators.py` (optional)** – Central place for password strength and email‑format validators.

---

## Phase 4 – Function‑Based Views (FBVs)

- **`register_user`** – `POST`, permission `AllowAny`; registers a user with `first_name`, `last_name`, `email`, and `password` using `UserRegisterSerializer` (creating the `User` with `email`/`password` and updating `Profile` with `first_name`/`last_name`).
- **`login_user`** – `POST`, permission `AllowAny`; authenticates the user and returns a JWT pair and user data using `EmailTokenObtainPairSerializer`.
- **`refresh_token`** – `POST`, permission `AllowAny`; accepts a `refresh` token and returns a new `access` token (plus rotated `refresh` token) using SimpleJWT's `TokenRefreshSerializer`.
- **`logout_user`** – `POST`, permission `IsAuthenticated`; blacklists the supplied `refresh` token using `LogoutSerializer`.
- **`profile_view`** – `GET`/`PUT`/`PATCH`, permission `IsAuthenticated`; retrieves the authenticated user with nested profile (`UserWithProfileSerializer`) or updates `Profile` fields (`ProfileSerializer`).
- **`change_password`** – `POST`, permission `IsAuthenticated`; verifies the current password and sets a new password for the authenticated user.

All views are decorated with `@api_view([...])` and `@permission_classes([...])` and return DRF `Response` objects.


---

## Phase 5 – Permissions (RBAC)

- **`HasRole` (base class)** – Checks `request.user.role` against a provided list of allowed roles.
- **`IsAdmin`** – Allows users with `role == "admin"` **or** `request.user.is_superuser`.
- **`IsManager`** – Allows roles `manager` or `admin`, plus superusers.
- **`IsOwnerOrAdmin`** – Object‑level permission: the object belongs to the requesting user OR the user is an admin.
- **`RequireRole(*roles)`** – Factory that creates a temporary permission class for ad‑hoc use, e.g., `@permission_classes([RequireRole("manager")])`.

---

## Phase 6 – URL Configuration

1. **Create `users/urls.py`** – Map each FBV to a path, e.g., `path("auth/register/", register_view)`, `path("auth/login/", login_view)`, etc.
2. **Include in project URLs** – Add `path("api/", include("users.urls"))` to `config/urls.py`.
3. *(Optional)* Set `app_name = "users"` for namespacing.

---

## Phase 7 – Testing & Verification

- **Unit tests** (`users/tests.py`): cover model creation, serializer validation, view status codes, RBAC enforcement, token rotation, and blacklisting.
- **Automated run** – Execute `python manage.py test users`; all tests should pass.
- **Manual API checks** – Use `curl` or Postman to:
  1. Register a user.
  2. Log in and obtain access/refresh tokens.
  3. Access protected endpoints with the access token.
  4. Refresh the token.
  5. Log out (blacklist the refresh token) and verify the token cannot be used again.
- **Database sanity** – Verify each `User` has an associated `Profile` via the Django shell.
- **Static analysis** (optional) – Run `ruff` or `flake8` to enforce coding standards.

---

## Phase 8 – Documentation & Future Enhancements

- Add a README section with quick‑start commands.
- Optionally generate an OpenAPI schema using `drf‑spectacular`.
- Future features may include:
  - Email verification workflow.
  - Password‑reset flow.
  - Additional profile fields (avatar, bio, etc.).
  - Admin UI for managing token blacklist.

---

*When you’re ready, let me know which phase you’d like to start with, or if any item needs clarification.*
