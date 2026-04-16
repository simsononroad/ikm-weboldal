import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, select, text


# Alapbeállítások
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'szuper_titkos_ikm_kulcs_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ikm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Max 16MB kép

db = SQLAlchemy(app)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Ehhez be kell jelentkezned."
login_manager.login_message_category = "warning"

# --- SEGÉDFUNKCIÓK ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- ADATBÁZIS MODELLEK ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=True) # Mindenki admin, aki beléphet

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Sticker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image_filename = db.Column(db.String(255), nullable=False) # Most már csak a fájlnevet tároljuk


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    irl_name = db.Column(db.String(120), nullable=False)
    ig_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    city_name = db.Column(db.String(120), nullable=False)
    prod_title = db.Column(db.String(120), nullable=False)
    prod_desc = db.Column(db.String(120), nullable=False)
    prod_price = db.Column(db.String(120), nullable=False)
    is_ready = db.Column(db.String(2), nullable=False)







@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Kezdeti adatbázis létrehozás
with app.app_context():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    db.create_all()
    # Alap admin létrehozása, ha nincs
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin')
        admin_user.set_password('motorosok2026')
        db.session.add(admin_user)
        db.session.commit()

# --- PUBLIKUS ÚTVONALAK ---

@app.route('/')
def index():
    stickers = Sticker.query.all()
    return render_template('index.html', stickers=stickers)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_stickers'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user)
            flash('Üdv újra, IKM Testvér!', 'success')
            return redirect(url_for('admin_stickers'))
        flash('Hibás adatok.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sikeresen kijelentkeztél.', 'info')
    return redirect(url_for('index'))



@app.route("/gyik")
def gyik():
    return render_template("gyik.html")


@app.route("/order/<title>/<desc>/<price>")
def order(title, desc, price):
    return render_template("order.html", title=title, desc=desc, price=price)

@app.route("/send_order/<title>/<desc>/<price>", methods=["POST", "GET"])
def send_order(title, desc, price):
    irl_name = request.form.get("irl_name")
    ig_name = request.form.get("ig_name")
    email = request.form.get("email")
    city = request.form.get("city")
    print(irl_name, ig_name, email, city, title, desc, price, sep=" | ")
    sticker_name_list = Sticker.query.filter_by(name=title).all()
    if len(sticker_name_list) == 0:
        flash("Nem létezik ilyen matrica!")
        return redirect(f"/order/{title}/{desc}/{price}")
    
    new_order = Order(irl_name=irl_name, ig_name=ig_name, email=email, city_name=city, prod_title=title, prod_desc=desc, prod_price=price, is_ready=0)
    db.session.add(new_order)
    db.session.commit()
    flash("Rendelés sikeresen felvéve!")
    return redirect(f"/")




# --- ADMIN ÚTVONALAK (VÉDETT) ---

# 1. MATRICÁK KEZELÉSE
@app.route('/admin/stickers')
@login_required
def admin_stickers():
    stickers = Sticker.query.all()
    return render_template('admin/admin_stickers.html', stickers=stickers)

# Matrica Hozzáadása FÁYLFELTÖLTÉSSEL
@app.route('/admin/stickers/add', methods=['POST'])
@login_required
def add_sticker():
    name = request.form.get('name')
    description = request.form.get('description')
    price = request.form.get('price')
    file = request.files['image']

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Egyedi fájlnév generálása (megelőzi az felülírást)
        import uuid
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

        new_sticker = Sticker(name=name, description=description, price=price, image_filename=unique_filename)
        db.session.add(new_sticker)
        db.session.commit()
        flash(f'Matrica ({name}) hozzáadva!', 'success')
    else:
        flash('Hiba: Nem megfelelő fájlformátum.', 'danger')
    
    return redirect(url_for('admin/admin_stickers'))

@app.route("/admin/orders")
@login_required
def admin_orders():
    nincs_kesz = db.session.execute(text("SELECT * FROM 'order' WHERE is_ready='0'"))
    kesz = db.session.execute(text("SELECT * FROM 'order' WHERE is_ready='1'"))
    heading = ("ID", "Valódi név", "Instagram név", "email", "Város név", "Áru neve", "Áru leírása", "Áru ára", "Műveletek")
    nincs_kesz_data = list(nincs_kesz)
    kesz_data = list(kesz)
    
    return render_template("admin/orders.html", headings=heading, data_no_r=nincs_kesz_data, kesz_data=kesz_data)

@app.route("/admin/del_order/<order_id>")
@login_required
def del_order(order_id):
    db.session.execute(text(f"DELETE FROM 'order' WHERE id='{order_id}'"))
    db.session.commit()
    return redirect(url_for("admin_orders"))


@app.route("/admin/to_ready/<order_id>")
@login_required
def to_ready(order_id):
    db.session.execute(text(f"UPDATE 'order' SET is_ready='1' WHERE id='{order_id}'"))
    db.session.commit()
    return redirect(url_for("admin_orders"))




# Matrica Szerkesztése (Renderelés)
@app.route('/admin/stickers/edit/<int:id>')
@login_required
def edit_sticker_form(id):
    sticker = Sticker.query.get_or_404(id)
    return render_template('admin/admin_stickers.html', edit_sticker=sticker, stickers=Sticker.query.all())

# Matrica Szerkesztése (Mentés)
@app.route('/admin/stickers/update/<int:id>', methods=['POST'])
@login_required
def update_sticker(id):
    sticker = Sticker.query.get_or_404(id)
    sticker.name = request.form.get('name')
    sticker.description = request.form.get('description')
    sticker.price = request.form.get('price')
    
    file = request.files['image']
    if file and allowed_file(file.filename):
        # Régi kép törlése, ha van
        old_path = os.path.join(app.config['UPLOAD_FOLDER'], sticker.image_filename)
        if os.path.exists(old_path):
            os.remove(old_path)
            
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
        sticker.image_filename = unique_filename

    db.session.commit()
    flash(f'Matrica ({sticker.name}) frissítve.', 'success')
    return redirect(url_for('admin/admin_stickers'))

# Matrica Törlése
@app.route('/admin/stickers/delete/<int:id>')
@login_required
def delete_sticker(id):
    sticker = Sticker.query.get_or_404(id)
    # Képfájl törlése a szerverről
    img_path = os.path.join(app.config['UPLOAD_FOLDER'], sticker.image_filename)
    if os.path.exists(img_path):
        os.remove(img_path)
        
    db.session.delete(sticker)
    db.session.commit()
    flash('Matrica törölve.', 'warning')
    return redirect(url_for('admin/admin_stickers'))


# 2. PROFILOK (FELHASZNÁLÓK) KEZELÉSE
@app.route('/admin/users')
@login_required
def admin_users():
    users = User.query.all()
    return render_template('admin/admin_users.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
@login_required
def add_user():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if User.query.filter_by(username=username).first():
        flash('Ez a felhasználónév már foglalt.', 'danger')
    else:
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash(f'Profil ({username}) létrehozva.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/delete/<int:id>')
@login_required
def delete_user(id):
    if id == current_user.id:
        flash('Magadat nem törölheted!', 'danger')
    else:
        user = User.query.get_or_404(id)
        db.session.delete(user)
        db.session.commit()
        flash('Profil törölve.', 'warning')
    return redirect(url_for('admin/admin_users'))

if __name__ == '__main__':
    app.run(debug=True)