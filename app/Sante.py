from flask import Flask, session, redirect, url_for, request, render_template, flash, g, abort  # escape
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SubmitField, IntegerField, SelectField, \
    DateTimeField
from wtforms.validators import DataRequired, Email, EqualTo, NumberRange  # Length, NumberRange
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
manager = Manager(app)
bootstrap = Bootstrap(app)

# Read the configurations
app.config.from_pyfile('config/config.py')
# Contenu typique de config.py. Le vrai fichier devrait être changé.
# SQLALCHEMY_DATABASE_URI = 'sqlite:///data/sante.db'
# SQLALCHEMY_TRACK_MODIFICATIONS=False
# SECRET_KEY='NotSoSecretKey'
# DEBUG=True

db = SQLAlchemy(app)


# Database Model

class AdminUser(db.Model):
    __tablename__ = 'tadmin_user'
    user_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(30), nullable=False)
    last_name = db.Column(db.String(30), nullable=False)
    user_email = db.Column(db.String(80), nullable=False, unique=True)
    user_pass = db.Column(db.String(100), nullable=False)
    activated = db.Column(db.Boolean(), nullable=False, default=True)

    def __init__(self, first_name, last_name, user_email, user_pass):
        self.first_name = first_name
        self.last_name = last_name
        self.user_email = user_email
        self.user_pass = user_pass

    def __repr__(self):
        return '<user: {}>'.format(self.user_email)


class MesurePA(db.Model):
    __tablename__ = 'tmesure_pa'
    mes_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer(), nullable=False)
    mes_ts = db.Column(db.DateTime(), nullable=False)
    pa_systolique = db.Column(db.Integer(), nullable=False)
    pa_diastolique = db.Column(db.Integer(), nullable=False)
    freq_cardiaque = db.Column(db.Integer(), nullable=False)

    def __init__(self, user_id, mes_ts, pa_sysstolique, pa_diastolique, freq_cardiaque):
        self.user_id = user_id
        self.mes_ts = mes_ts
        self.pa_systolique = pa_sysstolique
        self.pa_diastolique = pa_diastolique
        self.freq_cardiaque = freq_cardiaque

    def __repr__(self):
        return '<mes_pa: {}>'.format(self.mes_id)


# Formulaire web pour l'écran de login
class LoginForm(FlaskForm):
    email = StringField('Courriel', validators=[DataRequired(), Email(message='Le courriel est invalide.')])
    password = PasswordField('Mot de Passe', [DataRequired(message='Le mot de passe est obligatoire.')])
    request_password_change = BooleanField('Changer le mot de passe?')
    password_1 = PasswordField('Nouveau Mot de passe',
                               [EqualTo('password_2', message='Les mots de passe doivent être identiques.')])
    password_2 = PasswordField('Confirmation')
    submit = SubmitField('Se connecter')


# Formulaire web pour l'écran de register
class RegisterForm(FlaskForm):
    first_name = StringField('Prénom', validators=[DataRequired(message='Le prénom est requis.')])
    last_name = StringField('Nom de famille', validators=[DataRequired(message='Le nom de famille est requis.')])
    email = StringField('Courriel', validators=[DataRequired(), Email(message='Le courriel est invalide.')])
    password_1 = PasswordField('Mot de passe',
                               [DataRequired(message='Le mot de passe est obligatoire.'),
                                EqualTo('password_2', message='Les mots de passe doivent être identiques.')])
    password_2 = PasswordField('Confirmation')
    submit = SubmitField('S\'enrégistrer')


# Formulaire pour entrer une mesure de pression artérielle
class AjtMesurePAForm(FlaskForm):
    mes_ts = DateTimeField('Temps de la Mesure')
    pa_systolique = IntegerField('Pression Systolique',
                                 validators=[DataRequired(message='La pression systolique est requise.')])
    pa_diastolique = IntegerField('Pression Diastolique',
                                  validators=[DataRequired(message='La pression diastolique est requise.')])
    freq_cardiaque = IntegerField('Fréquence Cardiaque',
                                  validators=[DataRequired(message='La fréquence cardiaque est requise.')])
    submit = SubmitField('Ajouter')


# Custom error pages
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


# The following functions are views
@app.route('/')
def index():
    if not logged_in():
        return redirect(url_for('login'))
    app.logger.debug('Entering index()')
    first_name = session.get('first_name', None)
    return render_template('sante.html', user=first_name)


@app.route('/login', methods=['GET', 'POST'])
def login():
    app.logger.debug('Entering login()')
    form = LoginForm()
    if form.validate_on_submit():
        user_email = request.form['email']
        password = request.form['password']
        if db_validate_user(user_email, password):
            session['active_time'] = datetime.now()
            request_pwd_change = request.form.get('request_password_change', None)
            if request_pwd_change:
                app.logger.debug("Changer le mot de passe")
                new_password = request.form['password_1']
                change_password(user_email, new_password)
            return redirect(url_for('index'))
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    app.logger.debug('Entering logout()')
    session.pop('user_id', None)
    session.pop('first_name', None)
    session.pop('last_name', None)
    session.pop('user_email', None)
    session.pop('active_time', None)
    flash('Vous êtes maintenant déconnecté.')
    return redirect(url_for('index'))


def logged_in():
    user_email = session.get('user_email', None)
    if user_email:
        active_time = session['active_time']
        delta = datetime.now() - active_time
        if (delta.days > 0) or (delta.seconds > 1800):
            flash('Votre session est expirée.')
            return False
        session['active_time'] = datetime.now()
        return True
    else:
        return False


@app.route('/register', methods=['GET', 'POST'])
def register():
    app.logger.debug('Entering register')
    form = RegisterForm()
    if form.validate_on_submit():
        app.logger.debug('Inserting a new registration')
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        user_email = request.form['email']
        user_pass = generate_password_hash(request.form['password_1'])
        if user_exists(user_email):
            flash('Cet usager existe déjà. Veuillez vous connecter.')
            return redirect(url_for('login'))
        else:
            user = AdminUser(first_name, last_name, user_email, user_pass)
            db.session.add(user)
            db.session.commit()
            flash('Revenez quand votre compte sera activé.')
            return redirect(url_for('index'))
    return render_template('register.html', form=form)


def user_exists(user_email):
    app.logger.debug('Entering user_exists with: ' + user_email)
    user = AdminUser.query.filter_by(user_email=user_email).first()
    if user is None:
        app.logger.debug('user_exists returns False')
        return False
    else:
        app.logger.debug('user_exists returns True' + user[0])
        return True


@app.route('/list_mesures_pa')
def list_mesures_pa():
    if not logged_in():
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    mesures_pa = MesurePA.query.filter_by(user_id=user_id).order_by(MesurePA.mes_ts).all()
    return render_template('list_mesures_pa.html', mesures_pa=mesures_pa)


@app.route('/ajt_mesure_pa', methods=['GET', 'POST'])
def ajt_mesure_pa():
    if not logged_in():
        return redirect(url_for('login'))
    app.logger.debug('Entering ajt_mesure')
    form = AjtMesurePAForm()
    app.logger.debug('form assigned')
    if form.validate_on_submit():
        app.logger.debug('Validated')
        user_id = session.get('user_id')
        app.logger.debug('Before getting form data')
        # mes_ts = request.form['mes_ts']
        # pa_systolique = request.form['pa_systolique']
        # pa_diastolique = request.form['pa_diastolique']
        # freq_cardiaque = request.form['freq_cardiaque']
        mes_ts = form.mes_ts.data
        pa_systolique = form.pa_systolique.data
        pa_diastolique = form.pa_diastolique.data
        freq_cardiaque = form.freq_cardiaque.data
        app.logger.debug('Calling db_ajt')
        if db_ajt_mesure_pa(user_id, mes_ts, pa_systolique, pa_diastolique, freq_cardiaque):
            app.logger.debug('Ajout ds BD OK')
            flash("La mesure a été ajoutée.")
            return redirect(url_for('list_mesures_pa'))
        else:
            app.logger.debug('Ajout ds la BD - Echec')
            flash('Une erreur de base de données est survenue.')
            abort(500)
    form.mes_ts.data = datetime.now()
    return render_template('ajt_mesure_pa.html', form=form)


@app.route('/mod_mesure_pa/<int:mes_id>', methods=['GET', 'POST'])
def mod_mesure_pa(mes_id):
    if not logged_in():
        return redirect(url_for('login'))
    abort(404)


@app.route('/sup_mesure_pa/<int:mes_id>', methods=['GET', 'POST'])
def sup_mesure_pa(mes_id):
    if not logged_in():
        return redirect(url_for('login'))
    abort(404)


# Validate if a user is defined in tadmin_user with the proper password.
def db_validate_user(user_email, password):
    user = AdminUser.query.filter_by(user_email=user_email).first()
    if user is None:
        flash("L'usager n'existe pas.")
        return False

    if not user.activated:
        flash("L'usager n'est pas activé.")
        return False

    if check_password_hash(user.user_pass, password):
        session['user_id'] = user.user_id
        session['user_email'] = user.user_email
        session['first_name'] = user.first_name
        session['last_name'] = user.last_name
        return True
    else:
        flash("Mauvais mot de passe!")
        return False


def change_password(user_email, new_password):
    user = AdminUser.query.filter_by(user_email=user_email).first()
    if user is None:
        flash("Mot de passe inchangé. L'usager n'a pas été retrouvé.")
    else:
        user.user_pass = generate_password_hash(new_password)
        db.session.commit()
        flash("Mot de passe changé.")


def db_ajt_mesure_pa(user_id, mes_ts, pa_systolique, pa_diastolique, freq_cardiaque):
    m = MesurePA(user_id, mes_ts, pa_systolique, pa_diastolique, freq_cardiaque)
    try:
        db.session.add(m)
        db.session.commit()
    except Exception as e:
        app.logger.error('DB Error' + str(e))
        return False
    return True


# Start the server for the application
if __name__ == '__main__':
    manager.run()
