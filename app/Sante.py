from flask import Flask, session, redirect, url_for, request, render_template, flash, g, abort  # escape
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SubmitField, IntegerField, SelectField, \
                    DateTimeField, DecimalField
from wtforms.validators import DataRequired, Email, EqualTo, NumberRange  # Length, NumberRange
from wtforms.fields.html5 import DateField
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from datetime import datetime
import pygal
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models import DatetimeTickFormatter
from bokeh.palettes import Spectral6
from math import pi

app = Flask(__name__)
manager = Manager(app)
bootstrap = Bootstrap(app)

# Read the configurations
app.config.from_pyfile('config/config.py')
# Contenu typique de config.py. Le vrai fichier devrait être changé.
# ADMIN_EMAILID = 'jean.petitclerc@groupepp.com'
# SQLALCHEMY_DATABASE_URI = 'sqlite:///data/sante.db'
# SQLALCHEMY_TRACK_MODIFICATIONS=False
# SECRET_KEY='NotSoSecretKey'
# DEBUG=True

db = SQLAlchemy(app)


# Database Model

class AppUser(db.Model):
    __tablename__ = 'tapp_user'
    user_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(30), nullable=False)
    last_name = db.Column(db.String(30), nullable=False)
    user_email = db.Column(db.String(80), nullable=False, unique=True)
    user_pass = db.Column(db.String(100), nullable=False)
    activated_ts = db.Column(db.DateTime(), nullable=True)
    audit_crt_ts = db.Column(db.DateTime(), nullable=False)
    audit_upd_ts = db.Column(db.DateTime(), nullable=True)

    def __init__(self, first_name, last_name, user_email, user_pass, audit_crt_ts):
        self.first_name = first_name
        self.last_name = last_name
        self.user_email = user_email
        self.user_pass = user_pass
        self.audit_crt_ts = audit_crt_ts

    def __repr__(self):
        return '<user: {}>'.format(self.user_email)


class MesurePA(db.Model):
    __tablename__ = 'tmesure_pa'
    id_mes = db.Column(db.Integer(), primary_key=True, autoincrement=True)
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
        return '<mes_pa: {}>'.format(self.id_mes)


class MesurePoids(db.Model):
    __tablename__ = 'tmesure_poids'
    id_mes = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer(), nullable=False)
    mes_ts = db.Column(db.DateTime(), nullable=False)
    poids = db.Column(db.Float(), nullable=False)

    def __init__(self, user_id, mes_ts, poids):
        self.user_id = user_id
        self.mes_ts = mes_ts
        self.poids = poids

    def __repr__(self):
        return '<mes_poids: {}>'.format(self.id_mes)


# Formulaire pour confirmer la suppression d'une entitée
class DelEntityForm(FlaskForm):
    submit = SubmitField('Supprimer')


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
class MAJMesurePAForm(FlaskForm):
    mes_dt = DateField('DatePicker', format='%Y-%m-%d')
    mes_ts = DateTimeField('Temps de la Mesure')
    pa_systolique = IntegerField('Pression Systolique',
                                 validators=[DataRequired(message='La pression systolique est requise.')])
    pa_diastolique = IntegerField('Pression Diastolique',
                                  validators=[DataRequired(message='La pression diastolique est requise.')])
    freq_cardiaque = IntegerField('Fréquence Cardiaque',
                                  validators=[DataRequired(message='La fréquence cardiaque est requise.')])


# Formulaire pour confirmer la suppression d'une mesure de pression artérielle
class SupMesurePAForm(FlaskForm):
    submit = SubmitField('Supprimer')


# Formulaire pour entrer une mesure de pression artérielle
class MAJMesurePoidsForm(FlaskForm):
    mes_dt = DateField('DatePicker', format='%Y-%m-%d')
    mes_ts = DateTimeField('Temps de la Mesure')
    poids = DecimalField('Poids', validators=[DataRequired(message='Le poids est requis.')])


# Formulaire pour confirmer la suppression d'une mesure de pression artérielle
class SupMesurePoidsForm(FlaskForm):
    submit = SubmitField('Supprimer')


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
    # The method is GET when the form is displayed and POST to process the form
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
                db_change_password(user_email, new_password)
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
        if db_user_exists(user_email):
            flash('Cet usager existe déjà. Veuillez vous connecter.')
            return redirect(url_for('login'))
        else:
            if db_add_user(first_name, last_name, user_email, user_pass):
                flash('Vous pourrez vous connecter quand votre usager sera activé.')
                return redirect(url_for('login'))
            else:
                flash('Une erreur de base de données est survenue.')
                abort(500)
    return render_template('register.html', form=form)


@app.route('/list_users')
def list_users():
    if not logged_in():
        return redirect(url_for('login'))
    try:
        user_id = session.get('user_id')
        admin_user = AppUser.query.filter_by(user_id=user_id, user_email=app.config.get('ADMIN_EMAILID')).first()
        app_users = AppUser.query.order_by(AppUser.first_name).all()
        return render_template('list_users.html', app_users=app_users, admin_user=admin_user)
    except Exception as e:
        app.logger.error('Error: ' + str(e))
        return redirect(url_for('index'))


@app.route('/act_user/<int:user_id>', methods=['GET', 'POST'])
def act_user(user_id):
    if not logged_in():
        return redirect(url_for('login'))
    if db_upd_user_status(user_id, 'A'):
        flash("L'utilisateur est activé.")
    else:
        flash("Quelque chose n'a pas fonctionné.")
    return redirect(url_for('list_users'))


@app.route('/inact_user/<int:user_id>', methods=['GET', 'POST'])
def inact_user(user_id):
    if not logged_in():
        return redirect(url_for('login'))
    if db_upd_user_status(user_id, 'D'):
        flash("L'utilisateur est désactivé.")
    else:
        flash("Quelque chose n'a pas fonctionné.")
    return redirect(url_for('list_users'))


@app.route('/del_user/<int:user_id>', methods=['GET', 'POST'])
def del_user(user_id):
    if not logged_in():
        return redirect(url_for('login'))
    form = DelEntityForm()
    if form.validate_on_submit():
        app.logger.debug('Deleting a user')
        if db_del_user(user_id):
            flash("L'utilisateur a été effacé.")
        else:
            flash("Quelque chose n'a pas fonctionné.")
        return redirect(url_for('list_users'))
    else:
        user = db_user_by_id(user_id)
        if user:
            return render_template('del_user.html', form=form, user=user)
        else:
            flash("L'information n'a pas pu être retrouvée.")
            return redirect(url_for('list_users'))


@app.route('/list_mesures_pa')
def list_mesures_pa():
    if not logged_in():
        return redirect(url_for('login'))
    MAX_SYSTOLIQUE = 130
    MAX_DIASTOLIQUE = 80
    user_id = session.get('user_id')
    mesures_pa = MesurePA.query.filter_by(user_id=user_id).order_by(MesurePA.mes_ts).all()
    xdt = [mes.mes_ts for mes in mesures_pa]

    serie_dia = [(mes.mes_ts, mes.pa_diastolique) for mes in mesures_pa]
    serie_sys = [(mes.mes_ts, mes.pa_systolique) for mes in mesures_pa]
    serie_frq = [(mes.mes_ts, mes.freq_cardiaque) for mes in mesures_pa]
    serie_mdia = [(mes.mes_ts, MAX_DIASTOLIQUE) for mes in mesures_pa]
    serie_msys = [(mes.mes_ts, MAX_SYSTOLIQUE) for mes in mesures_pa]
    chart = pygal.DateTimeLine(title="Pression Artérielle",
                               height=400,
                               disable_xml_declaration=True,
                               # dynamic_print_values=True,
                               truncate_legend=-1,
                               x_label_rotation=35,
                               truncate_label=-1,
                               x_value_formatter=lambda dt: dt.strftime('%Y-%m-%d-%H:%M'))
    chart.add("Diastolique", serie_dia)
    chart.add("Systolique", serie_sys)
    chart.add("Max. Diastolique", serie_mdia, show_dots=False)
    chart.add("Max. Systolique", serie_msys, show_dots=False)
    chart.add("Fréq. Cardiaque", serie_frq)
    msys = [MAX_SYSTOLIQUE for mes in mesures_pa]
    mdia = [MAX_DIASTOLIQUE for mes in mesures_pa]
    ysys = [mes.pa_systolique for mes in mesures_pa]
    ydia = [mes.pa_diastolique for mes in mesures_pa]
    yfrq = [mes.freq_cardiaque for mes in mesures_pa]

    # create a new plot with a title and axis labels
    TOOLS = "crosshair,xpan,wheel_zoom,box_zoom,reset,save,ywheel_pan"
    plot = figure(title="Pression Artérielle", x_axis_type='datetime', x_axis_label='Date', y_axis_label='PA',
                  tools=TOOLS, sizing_mode='scale_width', height=350)
    plot.xaxis[0].formatter = DatetimeTickFormatter(days='%Y-%m-%d')
    plot.xaxis.major_label_orientation = pi / 4

    # add a line renderer with legend and line thickness
    plot.line(xdt, msys, legend_label="Max Systolique", line_width=2, line_color=Spectral6[0])
    plot.line(xdt, mdia, legend_label="Max Diastolique", line_width=2, line_color=Spectral6[1])
    plot.line(xdt, ysys, legend_label="Systolique", line_width=2, line_color=Spectral6[2])
    plot.line(xdt, ydia, legend_label="Diastolique", line_width=2, line_color=Spectral6[3])
    plot.line(xdt, yfrq, legend_label="Fréquence Cardiaque", line_width=2, line_color=Spectral6[4])
    plot.legend.click_policy = "hide"
    script, div = components(plot)

    mesures_pa = MesurePA.query.filter_by(user_id=user_id).order_by(desc(MesurePA.mes_ts)).all()
    return render_template('list_mesures_pa.html', mesures_pa=mesures_pa, chart=chart.render(), script=script, div=div)


@app.route('/ajt_mesure_pa', methods=['GET', 'POST'])
def ajt_mesure_pa():
    if not logged_in():
        return redirect(url_for('login'))
    app.logger.debug('Entering ajt_mesure')
    form = MAJMesurePAForm()
    app.logger.debug('form assigned')
    if form.validate_on_submit():
        app.logger.debug('Validated')
        user_id = session.get('user_id')
        app.logger.debug('Before getting form data')
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


@app.route('/mod_mesure_pa/<int:id_mes>', methods=['GET', 'POST'])
def mod_mesure_pa(id_mes):
    if not logged_in():
        return redirect(url_for('login'))
    session['id_mes'] = id_mes
    form = MAJMesurePAForm()
    if form.validate_on_submit():
        app.logger.debug('Mettre a jour mesure pa')
        mes_ts = form.mes_ts.data
        pa_systolique = form.pa_systolique.data
        pa_diastolique = form.pa_diastolique.data
        freq_cardiaque = form.freq_cardiaque.data
        if db_mod_mesure_pa(id_mes, mes_ts, pa_systolique, pa_diastolique, freq_cardiaque):
            flash("La mesure a été modifiée.")
        else:
            flash("Quelque chose n'a pas fonctionné.")
        return redirect(url_for('list_mesures_pa'))
    else:
        mes = MesurePA.query.get(id_mes)
        if mes:
            form.mes_ts.data = mes.mes_ts
            form.pa_systolique.data = mes.pa_systolique
            form.pa_diastolique.data = mes.pa_diastolique
            form.freq_cardiaque.data = mes.freq_cardiaque
            return render_template("mod_mesure_pa.html", form=form, mes=mes)
        else:
            flash("L'information n'a pas pu être retrouvée.")
            return redirect(url_for('list_mesures_pa'))


@app.route('/sup_mesure_pa/<int:id_mes>', methods=['GET', 'POST'])
def sup_mesure_pa(id_mes):
    if not logged_in():
        return redirect(url_for('login'))
    form = SupMesurePAForm()
    if form.validate_on_submit():
        app.logger.debug('effacer un aliment')
        if db_sup_mesure_pa(id_mes):
            flash("La mesure a été effacée.")
        else:
            flash("Quelque chose n'a pas fonctionné.")
        return redirect(url_for('list_mesures_pa'))
    else:
        mes = MesurePA.query.get(id_mes)
        if mes:
            return render_template('sup_mesure_pa.html', form=form, mes=mes)
        else:
            flash("L'information n'a pas pu être retrouvée.")
            return redirect(url_for('list_mesures_pa'))


@app.route('/list_mesures_poids')
def list_mesures_poids():
    if not logged_in():
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    mesures_poids = MesurePoids.query.filter_by(user_id=user_id).order_by(MesurePoids.mes_ts).all()
    xdt = [mes.mes_ts for mes in mesures_poids]
    ypds = [mes.poids for mes in mesures_poids]

    # Préférable d'utiliser un graphe DateTimeLine que Line.
    serie = [(mes.mes_ts, mes.poids) for mes in mesures_poids]
    chart = pygal.DateTimeLine(title="Poids", height=300, disable_xml_declaration=True, dynamic_print_values=True,
        x_label_rotation=35, truncate_label=-1,
        x_value_formatter=lambda dt: dt.strftime('%Y-%m-%d'))
    chart.add("Poids", serie)

    # create a new plot with a title and axis labels
    TOOLS = "crosshair,xpan,wheel_zoom,box_zoom,reset,save,ywheel_pan"
    plot = figure(title="Poids", x_axis_type='datetime', x_axis_label='Date', y_axis_label='Poids', tools=TOOLS,
                  sizing_mode='scale_width', height=350)
    plot.xaxis[0].formatter = DatetimeTickFormatter(days='%Y-%m-%d', hours='-%H-%M')
    plot.xaxis.major_label_orientation = pi / 5

    # add a line renderer with legend and line thickness
    plot.line(xdt, ypds, legend_label="Poids", line_width=2)
    plot.legend.click_policy = "hide"

    script, div = components(plot)
    mesures_poids = MesurePoids.query.filter_by(user_id=user_id).order_by(desc(MesurePoids.mes_ts)).all()
    return render_template('list_mesures_poids.html', mesures_poids=mesures_poids, chart=chart.render(), script=script,
                           div=div)


@app.route('/ajt_mesure_poids', methods=['GET', 'POST'])
def ajt_mesure_poids():
    if not logged_in():
        return redirect(url_for('login'))
    app.logger.debug('Entering ajt_mesure')
    form = MAJMesurePoidsForm()
    app.logger.debug('form assigned')
    if form.validate_on_submit():
        app.logger.debug('Validated')
        user_id = session.get('user_id')
        app.logger.debug('Before getting form data')
        mes_ts = form.mes_ts.data
        poids = form.poids.data
        app.logger.debug('Calling db_ajt')
        if db_ajt_mesure_poids(user_id, mes_ts, poids):
            app.logger.debug('Ajout ds BD OK')
            flash("La mesure a été ajoutée.")
            return redirect(url_for('list_mesures_poids'))
        else:
            app.logger.debug('Ajout ds la BD - Echec')
            flash('Une erreur de base de données est survenue.')
            abort(500)
    form.mes_ts.data = datetime.now()
    return render_template('ajt_mesure_poids.html', form=form)


@app.route('/mod_mesure_poids/<int:id_mes>', methods=['GET', 'POST'])
def mod_mesure_poids(id_mes):
    if not logged_in():
        return redirect(url_for('login'))
    session['id_mes'] = id_mes
    form = MAJMesurePoidsForm()
    if form.validate_on_submit():
        app.logger.debug('Mettre a jour mesure poids')
        mes_ts = form.mes_ts.data
        poids = form.poids.data
        if db_mod_mesure_poids(id_mes, mes_ts, poids):
            flash("La mesure a été modifiée.")
        else:
            flash("Quelque chose n'a pas fonctionné.")
        return redirect(url_for('list_mesures_poids'))
    else:
        mes = MesurePoids.query.get(id_mes)
        if mes:
            form.mes_ts.data = mes.mes_ts
            form.poids.data = mes.poids
            return render_template("mod_mesure_poids.html", form=form, mes=mes)
        else:
            flash("L'information n'a pas pu être retrouvée.")
            return redirect(url_for('list_mesures_poids'))


@app.route('/sup_mesure_poids/<int:id_mes>', methods=['GET', 'POST'])
def sup_mesure_poids(id_mes):
    if not logged_in():
        return redirect(url_for('login'))
    form = SupMesurePoidsForm()
    if form.validate_on_submit():
        app.logger.debug('effacer une mesure')
        if db_sup_mesure_poids(id_mes):
            flash("La mesure a été effacée.")
        else:
            flash("Quelque chose n'a pas fonctionné.")
        return redirect(url_for('list_mesures_poids'))
    else:
        mes = MesurePoids.query.get(id_mes)
        if mes:
            return render_template('sup_mesure_poids.html', form=form, mes=mes)
        else:
            flash("L'information n'a pas pu être retrouvée.")
            return redirect(url_for('list_mesures_poids'))


# Database functions for AppUser
def db_add_user(first_name, last_name, user_email, user_pass):
    audit_crt_ts = datetime.now()
    try:
        user = AppUser(first_name, last_name, user_email, user_pass, audit_crt_ts)
        if user_email == app.config.get('ADMIN_EMAILID'):
            user.activated_ts = datetime.now()
        db.session.add(user)
        db.session.commit()
        return True
    except Exception as e:
        app.logger.error('Error: ' + str(e))
        return False


def db_upd_user_status(user_id, status):
    try:
        user = AppUser.query.get(user_id)
        if status == 'A':
            user.activated_ts = datetime.now()
        else:
            user.activated_ts = None
        db.session.commit()
        return True
    except Exception as e:
        app.logger.error('Error: ' + str(e))
        return False


def db_user_exists(user_email):
    app.logger.debug('Entering user_exists with: ' + user_email)
    try:
        user = AppUser.query.filter_by(user_email=user_email).first()
        if user is None:
            return False
        else:
            return True
    except Exception as e:
        app.logger.error('Error: ' + str(e))
        return False


def db_user_by_id(user_id):
    try:
        u = AppUser.query.get(user_id)
        return u
    except Exception as e:
        app.logger.error('Error: ' + str(e))
        return None


# Validate if a user is defined in tadmin_user with the proper password.
def db_validate_user(user_email, password):
    try:
        user = AppUser.query.filter_by(user_email=user_email).first()
        if user is None:
            flash("L'usager n'existe pas.")
            return False

        if not user.activated_ts:
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
    except Exception as e:
        app.logger.error('Error: ' + str(e))
        flash("Connection impossible. Une erreur interne s'est produite.")
        return False


def db_del_user(user_id):
    try:
        user = AppUser.query.get(user_id)
        measures = MesurePA.query.filter_by(user_id=user_id).all()
        for m in measures:
            db.session.delete(m)
        measures = MesurePoids.query.filter_by(user_id=user_id).all()
        for m in measures:
            db.session.delete(m)
        db.session.delete(user)
        db.session.commit()
    except Exception as e:
        app.logger.error('Error: ' + str(e))
        return False
    return True


def db_change_password(user_email, new_password):
    try:
        user = AppUser.query.filter_by(user_email=user_email).first()
        if user is None:
            flash("Mot de passe inchangé. L'usager n'a pas été retrouvé.")
            return False
        else:
            user.user_pass = generate_password_hash(new_password)
            user.audit_upd_ts = datetime.now()
            db.session.commit()
            flash("Mot de passe changé.")
            return True
    except Exception as e:
        app.logger.error('Error: ' + str(e))
        flash("Mot de passe inchangé. Une erreur interne s'est produite.")
        return False


def db_ajt_mesure_pa(user_id, mes_ts, pa_systolique, pa_diastolique, freq_cardiaque):
    mes = MesurePA(user_id, mes_ts, pa_systolique, pa_diastolique, freq_cardiaque)
    try:
        db.session.add(mes)
        db.session.commit()
    except Exception as e:
        app.logger.error('DB Error' + str(e))
        return False
    return True


def db_mod_mesure_pa(id_mes, mes_ts, pa_systolique, pa_diastolique, freq_cardiaque):
    mes = MesurePA.query.get(id_mes)
    mes.mes_ts = mes_ts
    mes.pa_systolique = pa_systolique
    mes.pa_diastolique = pa_diastolique
    mes.freq_cardiaque = freq_cardiaque
    try:
        db.session.commit()
    except Exception as e:
        app.logger.error('DB Error' + str(e))
        return False
    return True


def db_sup_mesure_pa(id_mes):
    mes = MesurePA.query.get(id_mes)
    try:
        db.session.delete(mes)
        db.session.commit()
    except Exception as e:
        app.logger.error('DB Error' + str(e))
        return False
    return True


def db_ajt_mesure_poids(user_id, mes_ts, poids):
    mes = MesurePoids(user_id, mes_ts, poids)
    try:
        db.session.add(mes)
        db.session.commit()
    except Exception as e:
        app.logger.error('DB Error' + str(e))
        return False
    return True


def db_mod_mesure_poids(id_mes, mes_ts, poids):
    mes = MesurePoids.query.get(id_mes)
    mes.mes_ts = mes_ts
    mes.poids = poids
    try:
        db.session.commit()
    except Exception as e:
        app.logger.error('DB Error' + str(e))
        return False
    return True


def db_sup_mesure_poids(id_mes):
    mes = MesurePoids.query.get(id_mes)
    try:
        db.session.delete(mes)
        db.session.commit()
    except Exception as e:
        app.logger.error('DB Error' + str(e))
        return False
    return True


# Start the server for the application
if __name__ == '__main__':
    manager.run()
