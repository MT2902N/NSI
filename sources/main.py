from flask import Flask, render_template, request, session, redirect, url_for
from bs4 import BeautifulSoup
import requests
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from config import SECRET, AWS_ENDPOINT

# TODO: do the documentation in french


app = Flask(__name__)
app.secret_key = SECRET
# Se connecter a la base de donnees
app.config['SQLALCHEMY_DATABASE_URI'] = AWS_ENDPOINT
db = SQLAlchemy(app)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


class User(db.Model):
    """
        Cette classe est un modèle qui correspond au tableau 'users' dans la base de données. Ce tableau a
        3 colonnes, username, id et password. Elle est aussi connecte aux deux autres tableaux de la dataase
        posts et comments pour pouvoir acceder aux posts et commentaires de l'utilisateur.
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    posts = db.relationship('Post', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)


class Post(db.Model):
    """
       Cette classe est un modèle qui correspond au tableau 'posts' dans la base de données. Ce tableau a
       5 colonnes, id, title (titre du post), content (contenu du post), user_id (id de l'utilisateur), created_at
       (date de creation du post). Elle est aussi connecte au tableau de la base de données
       comments pour pouvoir acceder aux commentaires du posts.
    """
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    comments = db.relationship('Comment', backref='post', lazy=True)


class Comment(db.Model):
    """
        Cette classe est un modèle qui correspond au tableau 'comments' dans la base de données. Ce tableau a
        6 colonnes, id,  content (contenu du commentaire), user_id (id de l'utilisateur), created_at
        (date de creation du commentaire), post_id (id du post) et parent_id (id du commentaire parent dans le cas de un
        commentaire d'un commentaire). Elle est aussi connecte au tableau de la base de données comments (donc elle meme
        ) pou pouvoir acceder aux reponses du commentaire.
    """
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'))

    parent = db.relationship('Comment', remote_side=[id], backref=db.backref('replies', lazy=True))


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Cette fonction va montrer la premiere page qui apparait lorsque on lance le site.
    :return: 'index.html'
    """
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Cette fonction permet de gerer le login d'un utilsateur. On va chercher la base de données pour le username et voir
    si le password correspond a cet utilisateur. Si le username existe mais que c'est le mauvais password, on le renvoie
    a index.html avec un message d'erreur, si le username n'existe pas, on le renvoie a index.html avec un message
    d'erreur.
    :return: 'dashboard.html' si l'utilisateur existe sinon 'index_html' si il n'existe pas.
    """
    if request.method == 'POST':
        # On va prendre les informations de index.html
        username = request.form['username']
        password = request.form['password']

        # Si le username n'est pas dans la db => return None, sinon => return une instance of de la Class User
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            # On enregistre le user id dans la session ainsi que le username
            session['user_id'] = user.id
            session['username'] = user.username

            # On redirige l'utilsateur vers le dashboard. redirect(url_for('fonction')) permet de rediriger le code vers
            # la fonction désirée
            return redirect(url_for('dashboard'))

        error = True
        error_msg = 'Invalid Credentials. Please try again.'

        # On renvoie la page 'index.html' avec le messaqge d'erreur ci-dessus
        return render_template('index.html', error=error, error_message=error_msg)


@app.route('/query_db', methods=['GET', 'POST'])
def signup_page():
    """
    :return: 'signup.html'
    """
    return render_template('signup.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    Cette fonction permet de enregistrer un nouvel utilisateur dans la base de données.
    :return: index.html si l'enregistrement de l'utilisateur est réussi, sinon 'signup.html' avec un message d'erreur
    """
    if request.method == 'POST':
        # On va chercher les informations de la page 'signup.html'
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm_password']

        # Verifier si la confirmation de mot de passe et le mot de passe sont les memes
        if password != confirm:
            error = True
            error_msg = 'Les mots de pass ne sont pas identiques.'
            return render_template('signup.html', error=error, error_message=error_msg)

        # Verifiez if username existe deja
        if User.query.filter_by(username=username).first() is not None:
            error = True
            error_msg = "Ce nom d'utilisateur est deja pris, veuillez en choisir un autre. "
            return render_template('signup.html', error=error, error_message=error_msg)

        # Creer une instance de la class User et l'ajouter dans la base de données
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()

        success = True
        success_msg = 'Utilisateur créé avec succès.'
        # On renvoie l'utilisateur a 'index.html' avec un message de succees
        return render_template('index.html', success=success, success_message=success_msg)

    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    """
    Cette fonction permet de montrer le "dashboard" (la page d'accueil) du site, ou l'utilisateur va pouvoir acceder aux
    fonctionalités du site.
    :return: 'dashboard.html' si l'utilsateur est loggé, sinon on le renvoie a 'index.html'
    """
    if 'user_id' in session:
        return render_template('dashboard.html', username=session['username'])

    return redirect(url_for('index'))


@app.route('/dashboard/mes-posts-et-commentaires')
def p_v_viewer():
    """
    Cette fonction va renvoyer la page html qui permet a l'utilsateur de voir ses posts et commentaires.
    :return: 'p_v_viewer.html'
    """
    return render_template('p_v_viewer.html')


@app.route('/dashboard/mes-posts')
def post_viewer():
    """
    Cette fonction va chercher dans la base de données les posts de l'utilisateur et les montrer sur la page.
    :return: 'post_viewer.html'
    """
    if 'user_id' not in session:
        return render_template('index')
    # On définit combien de posts mettre au maximum dans la page (pour ne pas laisser la page devenir trop longue si
    # il y a beaucoup de posts
    per_page = 7

    # On cherche les informations dans la base de données et on le met dans la fonction paginate pour pouvoir fabriquer
    # la pagination de la page
    posts = db.paginate(db.select(Post).filter_by(user_id=session['user_id']).order_by(Post.created_at.desc()), per_page=per_page)

    # On renvoie la page 'post_viewer.html' avec arguments posts=posts (les posts de l'utilsateur) et pagination = posts
    # (pour définir la pagination de la page)
    return render_template('post_viewer.html', posts=posts, pagination=posts)


@app.route('/dashboard/mes-commentaires')
def comment_viewer():
    """
    Cette fonction va chercher dans la base de données les commentaires de l'utilisateur et les montrer sur la page.
    :return: 'comment_viewer.html'
    """
    if 'user_id' not in session:
        return render_template('index')
    per_page = 7
    comments = db.paginate(db.select(Comment).filter_by(user_id=session['user_id']).order_by(Comment.created_at.desc()), per_page=per_page)

    return render_template('comment_viewer.html', comments=comments, pagination=comments)


@app.route('/dashboard/discussion')
def discussion():
    """
    Cette fonction va chercher dans la base de données les commentaires de touts les utilisateurs et les montrer sur la page.
    :return: 'discussion.html'
    """
    if 'user_id' not in session:
        return redirect(url_for('index'))
    per_page = 10

    # On va chercher dans la base de données les posts de touts les utilsateur en les arrangant en ordre du plus récent
    # au plus vieux.
    posts = db.paginate(db.select(Post).order_by(Post.created_at.desc()), per_page=per_page)

    return render_template('discussion.html', posts=posts, pagination=posts)


@app.route('/dashboard/discussion/<int:post_id>')
def post_detail(post_id):
    """
    Quand l'utilisateur va clicker sur un des posts de 'discussion.html', cette fonction va permettre de montrer les
    informations de ce post en question, en montrant le contenu du post ainsi que les commentaires.
    :param post_id: l'id du post
    :return: 'post_detail.html'
    """
    # On va chercher les informations du post en cherchant la base de données pour le post grace au post_id
    post = Post.query.get(post_id)
    per_page = 7

    # Filtrer les commentaires par le id du post et les arrange en ordre du plus recent au moins recent
    comments = db.paginate(db.select(Comment).filter_by(post_id=post_id).order_by(Comment.created_at.desc()), per_page=per_page)

    return render_template('post_detail.html', post=post, comments=comments, pagination=comments, post_id=post_id)


@app.route('/dashboard/discussion/<int:post_id>', methods=['GET', 'POST'])
def comment(post_id):
    """
    Cette fonction permet aux utilisateurs de poster des commentaires a des posts.
    :param post_id: l'id du post
    :return: 'post_detail.html'
    """
    if 'user_id' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # On va chercher ce que l'utilisateur a mis dans la page html comme contenu de commentaire et son id
        # d'utilisateur
        content = request.form['comment']
        user_id = session['user_id']

        # On va voir a quel utilisateur correspond le user_id
        user = User.query.get(user_id)

        # Si le contenu du commentaire est vide, on ne fait rien => on le renvoie a la fonction post_detail()
        if len(content) == 0:
            return redirect(url_for('post_detail', post_id=post_id))

        # Creer un objet Comment et l'ajouter a la base de données avec le contenu du commentaire, l'utilisateur et l'id
        # du post
        comment = Comment(content=content, user=user, post_id=post_id)
        db.session.add(comment)
        db.session.commit()

        return redirect(url_for('post_detail', post_id=post_id))


    return render_template('post_detail.html', post_id=post_id)


@app.route('/dashboard/discussion/<int:post_id>/<int:comment_id>/reply', methods=['POST'])
def reply(post_id, comment_id):
    """
    Cette fonction permet aux utilisateurs de répondres a d'autres commentaires.
    :param post_id: l'id du post
    :param comment_id: l'id du commentaire auquel repond l'utilisateur
    :return: 'post_detail.html'
    """
    if 'user_id' not in session:
        return redirect(url_for('index'))

    # On va chercher ce que l'utilisateur a mis comme reponse de commentaire et son id a partir du html
    content = request.form['reply']
    user_id = session['user_id']
    user = User.query.get(user_id)

    if len(content) == 0:
        return redirect(url_for('post_detail', post_id=post_id))

    comment = Comment(content=content, user=user, post_id=post_id, parent_id=comment_id)

    db.session.add(comment)
    db.session.commit()

    return redirect(url_for('post_detail', post_id=post_id))


@app.route('/dashboard/discussion/recherche', methods=['POST', 'GET'])
def search():
    """
    Cette fonction permet aux utilisateurs de rechercher des posts a partir de mots clés.
    :return: 'discussion.html.
    """
    if 'user_id' not in session:
        return redirect(url_for('index'))

    # On va chercher tout d'abord quels mots clés l'utilisateur veut rechercher a partir du html
    query = request.form['query']

    if len(query) == 0:
        return redirect(url_for('discussion'))

    per_page = 7
    posts = db.paginate(Post.query.filter((Post.title.ilike(f'%{query}%') | Post.content.ilike(f'%{query}%'))), per_page=per_page)

    return render_template('discussion.html', posts=posts, pagination=posts)


@app.route('/dashboard/discussion/pending')
def new_post_page():
    """
    :return: 'new_post.html'
    """
    return render_template('new_post.html')


@app.route('/dashboard/discussion/new_post', methods=['GET', 'POST'])
def new_post():
    """
    Cette fonction permet d'ajouter des nouveux posts au forum.
    :return: 'discussion.html'
    """
    if 'user_id' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # On va chercher le titre, contenu, id de l'utilisateur du post a partir du html
        title = request.form['title']
        content = request.form['content']
        user_id = session['user_id']

        user = User.query.get(user_id)

        # On verifie que ni le titre ni le contenu n'est pas vide
        if len(title) == 0 or len(content) == 0:
            error = True
            error_message = 'Titre ou contenu ne peuvent pas etres vide.'

            # On renvoie 'new_post.html' avec le message d'erreur ci-dessus
            return render_template('new_post.html', error=error, error_message=error_message)

        # On verifie que le titre ne dépasse pas plus de 50 characteres
        if len(title) > 50:
            error = True
            error_message = 'Titre ne peut pas exceder 50 charactere'

            # On renvoie 'new_post.html' avec le message d'erreur ci-dessus
            return render_template('new_post.html', error=error, error_message=error_message)

        # Creer un objet POST et l'ajouter a la base de données
        post = Post(title=title, content=content, user=user)
        db.session.add(post)
        db.session.commit()

        return redirect(url_for('discussion'))


    return render_template('new_post.html')



@app.route('/dashboard/course')
def submit():
    """
    :return: 'request.html'
    """
    return render_template('request.html')


@app.route('/dashboard/course/classement', methods=['POST'])
def resultat():
    """
    Cette fonction renvoie le classement des meilleurs universités dans un certain secteur
    :return: 'classement.html'
    """
    # On va chercher le secteur dans lequel l'utilisateur est interessé a partir du html
    result = request.form.get('Course')

    # On creer un dictionnaire pour convertir les noms anglais a des noms Francais
    angl_fr = {
        'art-and-design': 'Art et Design',
        'business-and-management-studies': 'Études Commerciales',
        'law': 'Loi',
        'psychology': 'Psychologie',
        'general-engineering': 'Ingénierie',
        'medicine': 'Medecine',
        'sports-science': 'Sciences Sportives',
        'computer-science': 'Informatique'
    }

    # On va renvoyer 'classement.html' avec comme informations pour le tableau le resultat de query(result)[:20] (on ne
    # prend que les 20 premiers
    return render_template('classement.html', course=angl_fr[result], data=query(result)[:20])


def query(course):
    """
    Cette fonction va scraper du web des classements pour un secteur d'education
    :param course: le secteur d'education
    :return: un classement d'universites en forme de liste
    """
    try:
        # Tout d'abord, on tente de chercher les informations sur un site
        r = requests.get(f'https://www.thecompleteuniversityguide.co.uk/league-tables/rankings/{course}')

        # En le mettant dans un objet BeautifulSoup, cela rend l'information plus facilement exploitable
        soup = BeautifulSoup(r.content, 'html5lib')

        # On cherche les informations du tableau qui se situe sur le site
        search = soup.find_all("li", {"class": "swiper-slide uni_nam lt_list2"})

        # On filtre l'information pour ne que avoir les noms des universités
        filtered = [i.get_text(strip=True) for i in search][1].split('VIEW COURSES')

        return filtered
    except Exception as e:
        # Si il y a une erreur: example: perte de connection soudaine, on va le renvoyer a la page du début
        # ('index.html')
        return render_template('index.html')



app.run(debug=True)
