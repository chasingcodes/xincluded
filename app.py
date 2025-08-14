import os

import sqlite3
from flask import Flask, flash, redirect, render_template, request, session, abort, url_for
from flask_session import Session
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

# Configure application 
app = Flask(__name__)
app.secret_key = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0" # 40+ random characters


# Configure sessions to use filesystem
app.config["SESSION_PERMANENT"] = False # Logs out admin when browser is closed
app.config["SESSION_TYPE"] = "filesystem" # Stores session data
Session(app) # Initilizes extension

# Prevents browser from caching pages. Data always fresh
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expired"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/race/<slug>")
def race_details(slug):
    conn = sqlite3.connect("races.db")
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    # Fetch the race using the slug
    race = db.execute("SELECT * FROM races WHERE slug = ?", (slug,)).fetchone()
    
    if not race:
        conn.close()
        return redirect("/search")

    # Fetch approved feedback for this race
    community_feedback = db.execute(
        """
        SELECT feedback_public as text, name_of_user as name
        FROM feedback 
        WHERE race_id = ? AND approved = 1 AND feedback_public IS NOT NULL AND feedback_public != ''
        ORDER BY id DESC
        """, 
        (race["id"],)
    ).fetchall()

    conn.close()

    return render_template("race.html", race=race, community_feedback=community_feedback)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_id" not in session:
            return redirect("/admin")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/admin", methods=["GET", "POST"])
def admin_login():

    conn = sqlite3.connect("races.db")
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    # Forget any previous sessions
    session.clear()

    # Log admin in
    if request.method == "GET":
        # Show admin login page
        conn.close()
        return render_template("admin.html")
    
    else: # "POST" - form submission

        # Admin submits info
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        
        # Validate form inputs
        if not email:
            conn.close()
            return render_template("admin.html", error="Must provide valid email")
        if not password:
            conn.close()
            return render_template("admin.html", error="Must provide valid password")

        # Query database for email
        rows = db.execute("SELECT * FROM admin WHERE email = ?", (email,)).fetchall()
        
        # Ensure email exist and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            conn.close()
            return render_template("admin.html", error="Invalid login credentials")
        
        # Remember which admin has logged in
        session["admin_id"] = rows[0]["id"]

        # Redirect admin to dashboard
        conn.close()
        return redirect("/admin/dashboard")
  


@app.route("/admin/dashboard", methods=["GET"])
@login_required
def admin_dashboard():
    conn = sqlite3.connect("races.db")
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    # Get all feedback (both reviewed and unreviewed)
    feedback = db.execute("SELECT * FROM feedback ORDER BY id DESC").fetchall()

    # Get unreviewed suggestions
    suggestions = db.execute("SELECT * FROM suggestions WHERE archived=0 ORDER BY id DESC").fetchall()
    suggestion_count = len(suggestions)

    conn.close() 

    return render_template("dashboard.html", 
                         feedback=feedback, 
                         suggestions=suggestions, 
                         suggestion_count=suggestion_count)



    
@app.route("/admin/dashboard/archive_suggestion/<int:suggestion_id>", methods=["POST"])
@login_required
def archive_suggestion(suggestion_id):
    conn = sqlite3.connect("races.db")
    db = conn.cursor()

    db.execute("UPDATE suggestions SET archived=1 WHERE id=?", (suggestion_id,))
    conn.commit()
    conn.close()

    return redirect("/admin/dashboard")


#Submit feedback on that specific race
@app.route("/race/<slug>/submit_feedback", methods=["POST"])
def submit_feedback(slug):
    conn = sqlite3.connect("races.db")
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    # Get race details by slug
    race = db.execute("SELECT id, name FROM races WHERE slug = ?", (slug,)).fetchone()
    if not race:
        conn.close()
        return redirect("/search")  # Race not found

    race_id = race["id"]
    race_name = race["name"]

    # Get form data
    name_of_user = request.form.get("name", "").strip()
    pronouns = request.form.get("pronouns", "").strip()
    email = request.form.get("email", "").strip()
    event = request.form.get("event", "").strip()
    comment = request.form.get("comment", "").strip()  # Required

    if not comment:
        conn.close()
        # Redirect back to the race page or handle error in template
        return redirect(url_for("race_details", slug=slug))

    # Insert feedback into the table
    db.execute(
        """
        INSERT INTO feedback 
        (race_id, name_of_race, name_of_user, feedback_raw)
        VALUES (?, ?, ?, ?)
        """,
        (race_id, race_name, f"{name_of_user} ({pronouns})" if pronouns else name_of_user, comment)
    )

    conn.commit()
    conn.close()

    # Redirect back to race page with success message (optional)
    return redirect(url_for("race_details", slug=slug))



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/admin")




# index/Homepage
@app.route("/", methods=["GET", "POST"])
def index():

    conn = sqlite3.connect("races.db")
    db = conn.cursor()

    if request.method == "GET":
        # Populate list of states
        db.execute("SELECT state FROM locations ORDER BY state")
        locations = [row[0] for row in db.fetchall()]

        # Populat list of event types
        db.execute("SELECT DISTINCT type_name FROM event_types")
        event_types = [row[0] for row in db.fetchall()]

        # Get total count of races
        db.execute("SELECT * FROM races")
        races = db.fetchall()

        conn.close()
        return render_template("index.html", locations=locations, event_types=event_types, races=races)
    
    else: # Method = POST
        location_state = request.form.get("location_state")
        event_type = request.form.get("event_type")

        # Handle "all" selections by not including them in the query
        location_state_param = location_state if location_state != "all" else ""
        event_type_param = event_type if event_type != "all" else ""

        return redirect(f"/search?location_state={location_state_param}&event_type={event_type_param}")


# Search Page    
@app.route("/search", methods=["GET", "POST"])
def search():
    conn = sqlite3.connect("races.db")
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    location = None

    if request.method == "POST":

        # Retrieve filter values from form
        awards = request.form.get("awards")
        x_gender = request.form.get("x_gender")
        policy = request.form.get("policy")
        location_state = request.form.get("location_state")
        event_type = request.form.getlist("event_type")
        
        # Filter out empty strings from event_type
        event_type = [et for et in event_type if et and et.strip()]
        
        # Handle single event_type from homepage
        if not event_type:
            single_event_type = request.form.get("event_type")
            if single_event_type and single_event_type.strip():
                event_type = [single_event_type]

        # Building SQL query dynamically, will group by slug to avoid duplicates
        query = "SELECT * FROM races WHERE 1=1"     # 1=1 placeholder to be able to use AND after
        params = []   # Empty list that will hold the parameter values of the query

        if awards:                      # Boolean Yes/No
            query += " AND (nb_awards LIKE '%yes%' OR nb_awards LIKE '%top%' OR nb_awards LIKE '%overall%')"
        if x_gender:                    # Boolean Yes/No
            query += " AND nb_registration LIKE '%yes%'"
        if policy:                      # Boolean Yes/No
            query += " AND (trans_policy != 'No' AND trans_policy NOT LIKE 'No -%')"
        if location_state and location_state != "all":                    # Dropdown List
            query += " AND location_state = ?"
            params.append(location_state)
        if event_type and "all" not in event_type:                  # Select Multiple
            placeholders = ",".join("?" for _ in event_type) # Can add mulitple options (?) seperated by ,
            query+= f" AND event_type IN ({placeholders})"
            params.extend(event_type)

        rows = db.execute(query + " GROUP BY slug ORDER BY date DESC", params).fetchall()

        # Build query string for redirect URL
        query_params = []
        if awards:
            query_params.append("awards=1")
        if x_gender:
            query_params.append("x_gender=1")
        if policy:
            query_params.append("policy=1")
        if location_state:
            query_params.append(f"location_state={location_state}")
        if event_type:
            for etype in event_type: # Multiple options selected
                if etype and etype.strip():  # Only add non-empty event types
                    query_params.append(f"event_type={etype}")

        # Then join all with &
        query_string = "&".join(query_params)
        conn.close()

        return redirect(f"/search?{query_string}")

    else:
        # Retrieve filter values from query string
        selected_location_state = request.args.get("location_state")
        selected_event_types = request.args.getlist("event_type")
        
        # Filter out empty strings from selected_event_types
        selected_event_types = [et for et in selected_event_types if et and et.strip()]
        
        awards = request.args.get("awards")
        x_gender = request.args.get("x_gender")
        policy = request.args.get("policy")

        # Fetch dropdown from database
        locations = [row[0] for row in db.execute("SELECT state FROM locations").fetchall()]
        event_types = [row[0] for row in db.execute("SELECT type_name FROM event_types").fetchall()]

        # Build SQL query for GET, will group by slug to avoid duplicates
        query = "SELECT * FROM races WHERE 1=1"
        params = []

        if awards:
            query += " AND (nb_awards LIKE '%yes%' OR nb_awards LIKE '%top%' OR nb_awards LIKE '%overall%')"
        if x_gender:
            query += " AND nb_registration LIKE '%yes%'"
        if policy:                      
            query += " AND (trans_policy != 'No' AND trans_policy NOT LIKE 'No -%')"
        if selected_location_state and selected_location_state != "all":
            query += " AND location_state = ?"
            params.append(selected_location_state)
        if selected_event_types and "all" not in selected_event_types:
            placeholders = ",".join("?" for _ in selected_event_types)
            query+= f" AND event_type IN ({placeholders})"
            params.extend(selected_event_types)

        rows = db.execute(query + " GROUP BY slug ORDER BY date DESC", params).fetchall()

        # Create search description
        search_terms = []
        if selected_location_state and selected_location_state != "all":
            search_terms.append(f"Location: {selected_location_state}")
        if selected_event_types and "all" not in selected_event_types:
            if len(selected_event_types) == 1:
                search_terms.append(f"Event Type: {selected_event_types[0]}")
            else:
                search_terms.append(f"Event Types: {', '.join(selected_event_types)}")
        if awards:
            search_terms.append("Non-binary awards")
        if x_gender:
            search_terms.append("X gender registration")
        if policy:
            search_terms.append("Trans/non-binary policy")
        
        if search_terms:
            placeholders = ", ".join(search_terms)
        else:
            placeholders = "All races"

        if not rows:
            if any([awards, x_gender, policy, selected_location_state, selected_event_types]):
                error = "No events match your search parameter, please try again and/or use the filter"
            else:
                error = None
        else:
            error = None

        conn.close()

        return render_template(
            "search.html", 
            races=rows, 
            error=error,
            awards=awards, 
            x_gender=x_gender, 
            policy=policy,
            selected_location_state=selected_location_state,
            selected_event_types=selected_event_types,
            locations=locations,
            event_types=event_types,
            placeholders=placeholders
        )







# When admin clicks specific feedback, it goes to this:
@app.route("/admin/dashboard/feedback/<int:feedback_id>")
@login_required
def review_feedback(feedback_id):
    conn = sqlite3.connect("races.db")
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    # Query database for that specific id
    feedback = db.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,)).fetchone()

    if not feedback:
        conn.close()
        return redirect("/admin/dashboard")

    conn.close()
    
    return render_template("review_feedback.html", feedback=feedback)




@app.route("/about")
def about():
    return render_template("about.html")




@app.route("/suggest", methods=["GET", "POST"])
def suggest():

    conn = sqlite3.connect("races.db")
    db = conn.cursor()

    if request.method == "POST":

        # read, make default "" for no entry, and trim whitespace
        race_name = request.form.get("race_name", "").strip()
        race_link = request.form.get("race_link", "").strip()
        comment = request.form.get("comment", "").strip()

        if not race_name:
            return render_template("suggest.html", error="Please provide a valid race name")

        if not race_link:
            return render_template("suggest.html", error="Please provide a valid link")

        if not comment:
            return render_template("suggest.html", error="Please provide a reason we should include this event to our database")


        # Add name from race submission page into suggestion SQL database
        db.execute("INSERT INTO suggestions (race_name, race_link, comment) VALUES (?, ?, ?)", (race_name, race_link, comment))

        conn.commit() # Save changes to SQL database
        conn.close() # close connection

        return redirect("/thankyou")

    # method -> GET
    return render_template("suggest.html")




@app.route("/thankyou")
def thankyou():
    return render_template("thankyou.html")

# Route to view and archive individual suggestions
@app.route("/admin/dashboard/review_suggest/<int:suggestion_id>", methods=["GET", "POST"])
@login_required
def review_suggest(suggestion_id):
    """Display individual suggestion details and handle archiving"""
    
    conn = sqlite3.connect("races.db")
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    if request.method == "POST":
        # Archive the suggestion
        db.execute("UPDATE suggestions SET archived = 1 WHERE id = ?", (suggestion_id,))
        conn.commit()
        conn.close()
        flash("Suggestion archived successfully.", "success")
        return redirect("/admin/dashboard")
    
    # GET request - show suggestion details
    suggestion = db.execute("SELECT * FROM suggestions WHERE id = ?", (suggestion_id,)).fetchone()
    conn.close()
    if not suggestion:
        flash("Suggestion not found.", "error")
        return redirect("/admin/dashboard")
    
    return render_template("review_suggest.html", suggestion=suggestion)

@app.route("/admin/dashboard/approve_feedback/<int:feedback_id>", methods=["POST"])
@login_required
def approve_feedback(feedback_id):
    conn = sqlite3.connect("races.db")
    db = conn.cursor()

    # Get the edited public feedback from the form
    feedback_public = request.form.get("feedback_public", "").strip()
    
    if not feedback_public:
        flash("Public feedback cannot be empty.", "error")
        return redirect(f"/admin/dashboard/feedback/{feedback_id}")

    # Update both the approved status and the public feedback text
    db.execute(
        "UPDATE feedback SET approved=1, feedback_public=? WHERE id=?", 
        (feedback_public, feedback_id)
    )
    conn.commit()
    conn.close()

    flash("Feedback approved and published successfully.", "success")
    return redirect(f"/admin/dashboard/feedback/{feedback_id}")

@app.route("/admin/dashboard/unapprove_feedback/<int:feedback_id>", methods=["POST"])
@login_required
def unapprove_feedback(feedback_id):
    conn = sqlite3.connect("races.db")
    db = conn.cursor()

    # Set approved to 0 to hide from public view
    db.execute("UPDATE feedback SET approved=0 WHERE id=?", (feedback_id,))
    conn.commit()
    conn.close()

    flash("Feedback unapproved and hidden from public view.", "success")
    return redirect(f"/admin/dashboard/feedback/{feedback_id}")

@app.route("/admin/dashboard/archived_suggestions")
@login_required
def archived_suggestions():
    conn = sqlite3.connect("races.db")
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    # Get all archived suggestions
    archived = db.execute("SELECT * FROM suggestions WHERE archived=1 ORDER BY id DESC").fetchall()
    archived_count = len(archived)

    conn.close()

    return render_template("archived_suggestions.html", 
                         archived=archived, 
                         archived_count=archived_count)

@app.route("/admin/dashboard/unarchive_suggestion/<int:suggestion_id>", methods=["POST"])
@login_required
def unarchive_suggestion(suggestion_id):
    conn = sqlite3.connect("races.db")
    db = conn.cursor()

    db.execute("UPDATE suggestions SET archived=0 WHERE id=?", (suggestion_id,))
    conn.commit()
    conn.close()

    flash("Suggestion unarchived successfully.", "success")
    return redirect("/admin/dashboard/archived_suggestions")

@app.route("/admin/dashboard/edit_feedback/<int:feedback_id>", methods=["POST"])
@login_required
def edit_feedback(feedback_id):
    conn = sqlite3.connect("races.db")
    db = conn.cursor()

    # Get the updated public feedback from the form
    feedback_public = request.form.get("feedback_public", "").strip()
    
    if not feedback_public:
        flash("Public feedback cannot be empty.", "error")
        return redirect(f"/admin/dashboard/feedback/{feedback_id}")

    # Update the public feedback text
    db.execute(
        "UPDATE feedback SET feedback_public=? WHERE id=?", 
        (feedback_public, feedback_id)
    )
    conn.commit()
    conn.close()

    flash("Feedback updated successfully.", "success")
    return redirect(f"/admin/dashboard/feedback/{feedback_id}")

@app.route("/admin/dashboard/delete_feedback/<int:feedback_id>", methods=["POST"])
@login_required
def delete_feedback(feedback_id):
    conn = sqlite3.connect("races.db")
    db = conn.cursor()

    # Delete the feedback
    db.execute("DELETE FROM feedback WHERE id=?", (feedback_id,))
    conn.commit()
    conn.close()

    flash("Feedback deleted successfully.", "success")
    return redirect("/admin/dashboard")

if __name__ == '__main__':
    app.run(debug=True, port=5001)