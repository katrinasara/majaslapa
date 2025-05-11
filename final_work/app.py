from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/images/varieties'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    db = Path(__file__).parent / "berries.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/skirnes")
def berry():
    conn = get_db_connection()
    berries = conn.execute("SELECT * FROM Berries").fetchall()
    conn.close()
    return render_template("berry.html", Varieties=berries)

@app.route("/skirnes/create", methods=["GET", "POST"])
def create_berry():
    if request.method == "POST":
        name = request.form["name"]
        varieties_input = request.form.get("varieties", "")
        regions_input = request.form.get("regions", "")

        image_file = request.files.get("image")
        image_filename = ""
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_filename = filename

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Berries (name, image) VALUES (?, ?)", (name, image_filename))
        berry_id = cursor.lastrowid

        variety_names = list(dict.fromkeys([v.strip() for v in varieties_input.split(",") if v.strip()]))
        for v_name in variety_names:
            variety = cursor.execute("SELECT * FROM Varieties WHERE name = ?", (v_name,)).fetchone()
            if variety:
                cursor.execute("UPDATE Varieties SET berry_id = ? WHERE id = ?", (berry_id, variety["id"]))
            else:
                cursor.execute("INSERT INTO Varieties (name, description, berry_id) VALUES (?, ?, ?)", (v_name, "", berry_id))

        region_names = list(dict.fromkeys([r.strip() for r in regions_input.split(",") if r.strip()]))
        for r_name in region_names:
            region = cursor.execute("SELECT * FROM Regions WHERE name = ?", (r_name,)).fetchone()
            if not region:
                cursor.execute("INSERT INTO Regions (name) VALUES (?)", (r_name,))
                region_id = cursor.lastrowid
            else:
                region_id = region["id"]
            cursor.execute("INSERT INTO berry_region (berry_id, region_id) VALUES (?, ?)", (berry_id, region_id))

        conn.commit()
        conn.close()
        flash("Jauna oga pievienota!")
        return redirect(url_for("berry"))
    return render_template("create_berry.html")

@app.route("/skirnes/<int:berry_id>")
def berries_show(berry_id):
    conn = get_db_connection()
    berry = conn.execute("SELECT * FROM Berries WHERE id = ?", (berry_id,)).fetchone()
    varieties = conn.execute("SELECT * FROM Varieties WHERE berry_id = ?", (berry_id,)).fetchall()
    regions = conn.execute("""
        SELECT r.name FROM Regions r
        JOIN berry_region br ON r.id = br.region_id
        WHERE br.berry_id = ?
        LIMIT 5
    """, (berry_id,)).fetchall()
    conn.close()
    return render_template("berries_show.html", Berries=berry, Varieties=varieties, Regions=regions)

@app.route("/skirnes/<int:berry_id>/edit", methods=["GET", "POST"])
def edit_berry(berry_id):
    conn = get_db_connection()
    if request.method == "POST":
        name = request.form["name"]
        image_file = request.files.get("image")
        cursor = conn.cursor()

        # Get existing image filename from DB
        berry = cursor.execute("SELECT * FROM Berries WHERE id = ?", (berry_id,)).fetchone()
        image_filename = berry["image"] if berry and "image" in berry.keys() else ""

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_filename = filename

        varieties_input = request.form.get("varieties", "")
        regions_input = request.form.get("regions", "")

        cursor.execute("UPDATE Berries SET name = ?, image = ? WHERE id = ?", (name, image_filename, berry_id))

        cursor.execute("UPDATE Varieties SET berry_id = NULL WHERE berry_id = ?", (berry_id,))

        variety_names = list(dict.fromkeys([v.strip() for v in varieties_input.split(",") if v.strip()]))
        for v_name in variety_names[:3]:
            variety = cursor.execute("SELECT * FROM Varieties WHERE name = ?", (v_name,)).fetchone()
            if variety:
                cursor.execute("UPDATE Varieties SET berry_id = ? WHERE id = ?", (berry_id, variety["id"]))
            else:
                cursor.execute("INSERT INTO Varieties (name, description, berry_id) VALUES (?, ?, ?)", (v_name, "", berry_id))

        cursor.execute("DELETE FROM berry_region WHERE berry_id = ?", (berry_id,))

        region_names = list(dict.fromkeys([r.strip() for r in regions_input.split(",") if r.strip()]))
        for r_name in region_names[:5]:
            region = cursor.execute("SELECT * FROM Regions WHERE name = ?", (r_name,)).fetchone()
            if not region:
                cursor.execute("INSERT INTO Regions (name) VALUES (?)", (r_name,))
                region_id = cursor.lastrowid
            else:
                region_id = region["id"]
            cursor.execute("INSERT INTO berry_region (berry_id, region_id) VALUES (?, ?)", (berry_id, region_id))

        conn.commit()
        conn.close()
        flash("Oga tika atjaunināta!")
        return redirect(url_for("berries_show", berry_id=berry_id))

    berry = conn.execute("SELECT * FROM Berries WHERE id = ?", (berry_id,)).fetchone()
    varieties = conn.execute("SELECT * FROM Varieties WHERE berry_id = ?", (berry_id,)).fetchall()
    regions = conn.execute("""
        SELECT r.name FROM Regions r
        JOIN berry_region br ON r.id = br.region_id
        WHERE br.berry_id = ?
        LIMIT 5
    """, (berry_id,)).fetchall()
    conn.close()
    return render_template("edit_berry.html", berry=berry, Varieties=varieties, Regions=regions)

@app.route("/skirnes/<int:berry_id>/delete", methods=["POST"])
def delete_berry(berry_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM Varieties WHERE berry_id = ?", (berry_id,))
    conn.execute("DELETE FROM berry_region WHERE berry_id = ?", (berry_id,))
    conn.execute("DELETE FROM Berries WHERE id = ?", (berry_id,))
    conn.commit()
    conn.close()
    flash("Oga tika izdzēsta!")
    return redirect(url_for("berry"))

@app.route("/varieties/create", methods=["GET", "POST"])
def create_variety():
    conn = get_db_connection()
    berries = conn.execute("SELECT * FROM Berries").fetchall()
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        berry_id = request.form["berry_id"]

        image_file = request.files.get("image")
        image_filename = ""
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_filename = filename

        conn.execute("INSERT INTO Varieties (name, description, image, berry_id) VALUES (?, ?, ?, ?)", (name, description, image_filename, berry_id))
        conn.commit()
        conn.close()
        flash("Jauna šķirne pievienota!")
        return redirect(url_for("berry"))
    conn.close()
    return render_template("create_variety.html", berries=berries)

@app.route("/varieties/<int:variety_id>/edit", methods=["GET", "POST"])
def edit_variety(variety_id):
    conn = get_db_connection()
    variety = conn.execute("SELECT * FROM Varieties WHERE id = ?", (variety_id,)).fetchone()
    berries = conn.execute("SELECT * FROM Berries").fetchall()
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        berry_id = request.form["berry_id"]

        image_file = request.files.get("image")
        image_filename = variety["image"] if variety and "image" in variety.keys() else ""
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_filename = filename

        conn.execute("UPDATE Varieties SET name = ?, description = ?, image = ?, berry_id = ? WHERE id = ?", (name, description, image_filename, berry_id, variety_id))
        conn.commit()
        conn.close()
        flash("Šķirne tika atjaunināta!")
        return redirect(url_for("variety_detail", variety_id=variety_id))
    conn.close()
    return render_template("edit_variety.html", variety=variety, berries=berries)

@app.route("/varieties/<int:variety_id>/delete", methods=["POST"])
def delete_variety(variety_id):
    conn = get_db_connection()
    variety = conn.execute("SELECT * FROM Varieties WHERE id = ?", (variety_id,)).fetchone()
    if variety:
        conn.execute("DELETE FROM Varieties WHERE id = ?", (variety_id,))
        conn.commit()
    conn.close()
    flash("Šķirne tika izdzēsta!")
    return redirect(url_for("berries_show", berry_id=variety["berry_id"]))

@app.route("/varieties/<int:variety_id>")
def variety_detail(variety_id):
    conn = get_db_connection()
    variety = conn.execute("SELECT * FROM Varieties WHERE id = ?", (variety_id,)).fetchone()
    conn.close()
    return render_template("variety.html", Variety=variety)

if __name__ == "__main__":
    app.run(debug=True, port=5001)