# ParkEZily - Vehicle Parking App (V1)

A Flask-based multi-user web application to manage 4-wheeler parking lots. This project is built for the Modern Application Development I course.

## Core Technologies

* **Backend:** Python, Flask
* **Frontend:** Jinja2, HTML, Bootstrap, CSS, Chart.js
* **Database:** SQLite

## Roles

* **Admin:** Has full control over parking lots, spots, and user data.
* **User:** Can register, log in, view available lots, book a spot, release a spot, and view their parking history, and spends.

---

## Issue Log & Resolutions

This section documents the key technical challenges and architectural decisions made during development.

### 1. **Data Integrity on Lot Deletion**

* **Issue:** The initial database schema used `ON DELETE CASCADE` for parking lots. This meant that when an admin deleted a lot, all associated user reservation history was permanently erased, leading to critical data loss.
* **Resolution:** The architecture was shifted to a "soft delete" model. A `status` column was added to the `parking_lot` table. Now, deleting a lot updates its status to 'deleted' but preserves the row. The `reservation` table's foreign key was changed to `ON DELETE SET NULL`. This combination ensures that historical records are never lost, maintaining a complete audit trail.

### 2. **Handling Active Sessions During Lot Deletion**

* **Issue:** A critical bug was discovered where an admin could delete a lot while a user was actively parked in it. This would leave the user's account in a "stuck" state, as their active reservation could no longer be resolved, preventing them from parking elsewhere.
* **Resolution:** The `remove_lot` function in the admin controller was significantly enhanced. Before marking a lot as 'deleted', the function now queries for any active reservations within that lot. It then programmatically ends each session, calculates the final cost based on the duration, and updates the user's record before proceeding with the deletion. The admin is notified via a flash message that sessions were forcibly ended.

### 3. **Refactoring for Code Reusability**

* **Issue:** Helper functions, particularly `format_duration`, were duplicated in both `controllers/admin.py` and `controllers/user.py`. This led to redundant code and introduced a bug where the admin's duration calculation was incorrect.
* **Resolution:** A central `controllers/utils.py` file was created to house all shared helper functions. Both controllers were refactored to import these functions from this single source. This fixed the bug, eliminated redundancy, and made the codebase much easier to maintain.

### 4. **Strategic Validation Implementation**

* **Issue:** A decision was needed on the optimal strategy for form validation—whether to rely on the frontend (HTML5), the backend (Flask), or both.
* **Resolution:** A blended approach was adopted. For sensitive user registration data (e.g., strong password complexity, valid full name format), validation is enforced strictly on the backend in Python. For less critical, user-experience-focused rules (e.g., pincode must be numeric), frontend HTML5 `pattern` attributes are used to provide immediate feedback to the user, while the backend still handles the core checks.

### 5. **Jinja2 Template Nesting Errors**

* **Issue:** The user and admin history pages would crash with a `TemplateSyntaxError`, indicating a missing `{% endfor %}` tag after the chart visualization code was added.
* **Resolution:** The error was traced to the new Chart.js `<script>` block being incorrectly placed *inside* the `{% for %}` loop of the history table. The fix was to move the entire chart section to be *after* the `{% endfor %}` tag, ensuring the loop was properly closed before the next block began.

### 6. **Timezone Handling and User Experience**

* **Issue:** All timestamps were being stored and displayed in UTC, which is technically correct but not user-friendly for a specific region.
* **Resolution:** The `pytz` library was added to the project. The `utils.py` file was updated with a `format_ist` function that converts all UTC timestamps from the database into a clean, readable IST format (e.g., `Jul 29, 2025, 09:30 AM`) before they are displayed in any template.
