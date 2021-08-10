import tika
tika.initVM()
from flask import  render_template, send_from_directory
import flask
from fonctionCV import *
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple
import dash_bootstrap_components as dbc

#############################new
from flask import Flask, render_template, redirect, session, url_for, flash, request
from data.db_session import db_auth
from services.accounts_service import create_user, login_user, get_profile
from flask_login import current_user, login_required
import os
#############################new

onto = get_ontology("file://base_onto.owl").load()

mdp = open("mdp.txt", "r").read()
graph = Graph("localhost:7474", user="neo4j", password=mdp)
#graph = db_auth()

domainesTotaux = graph.run("""MATCH (dom:Domaine) RETURN dom
    """).data()
domainesTotaux = [x["dom"]["nomDom"] for x in domainesTotaux]
colors={'background':'rgba(0,0,0,0)',"text":"#000000"}
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'txt', 'pdf', "doc", "docx", "pptx"}

server = Flask(__name__)
dash_app1 = dash.Dash(__name__, server=server, url_base_pathname='/dashboard/')
dash_app2 = dash.Dash(__name__, server=server, url_base_pathname='/dashboard2/')
dash_metiers = dash.Dash(__name__, server = server, url_base_pathname='/dashboardmetiers/' )
dash_formations = dash.Dash(__name__, server = server, url_base_pathname='/dashboardformations/' )



############################################# authentification

server.secret_key = os.urandom(24)

#graph = db_auth()

@server.route('/politique')
def politique():
    return render_template("politique.html")


@server.route('/accounts/register', methods=['GET'])
def register_get():
    data = pd.read_csv("DonneesCV.csv")
    nomCV = data.to_dict()["Informations"][0]
    mail = data.to_dict()["Informations"][1]
    tel = data.to_dict()["Informations"][2]
    donnees = {"nomCV": nomCV,
               "mail": mail,
               "tel": tel}
    return render_template("accounts/register.html", donnees=donnees)


@server.route('/accounts/register', methods=['POST'])
def register_post():
    # Get the form data from register.html
    name = request.form.get('name')
    email = request.form.get('email').lower().strip()
    phone = request.form.get('phone').strip()
    password = request.form.get('password').strip()
    confirm = request.form.get('confirm').strip()

    # Check for blank fields in the registration form
    if not name or not email or not phone or not password or not confirm:
        flash("Please populate all the registration fields", "error")
        return render_template("accounts/register.html", name=name,
                               email=email, phone=phone, password=password, confirm=confirm)

    # Check if password and confirm match
    if password != confirm:
        flash("Passwords do not match")
        return render_template("accounts/register.html", name=name, email=email, phone=phone)

    # Create the user
    user = create_user(name, email, phone, password)
    # Verify another user with the same email does not exist
    if not user:
        flash("A user with that email already exists.")
        #return render_template("accounts/register.html", name=name, email=email, phone=phone)
        return redirect(url_for("register_get"))
    else:
        return redirect(url_for("login_get"))
    #return redirect(url_for("profile_get"))
    #return redirect(url_for("login_get"))


@server.route('/accounts/login', methods=['GET'])
def login_get():
    # Check if the user is already logged in.  if yes, redirect to profile page.
    if "usr" in session:
        return redirect(url_for("index"))
    else:
        return render_template("accounts/login.html")


@server.route('/accounts/login', methods=['POST'])
def login_post():
    # Get the form data from login.html
    email = request.form['email']
    password = request.form['password']
    if not email or not password:
        return render_template("accounts/login.html", email=email, password=password)

    # Validate the user
    user = login_user(email, password)
    if not user:
        flash("No account for that email address or the password is incorrect", "error")
        return render_template("accounts/login.html", email=email, password=password)

    # Log in user and create a user session, redirect to user profile page.
    usr = request.form["email"]
    session["usr"] = usr
    #return redirect(url_for("drag_drop.html"))

    data = pd.read_csv("DonneesCV.csv")
    nomCV = data.to_dict()["Informations"][0]
    #####

    #return render_template("drag_drop.html", nomCV=nomCV)
    #return redirect(url_for("analyzefichier"))
    return redirect(url_for("index"))


@server.route('/accounts/profile', methods=['GET'])
def profile_get():
    # Make sure the user has an active session.  If not, redirect to the login page.
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        user_profile = get_profile(usr)
        return render_template("accounts/index.html", user_profile=user_profile)
    else:
        return redirect(url_for("login_get"))


@server.route('/accounts/profile', methods=['POST'])
def profile_post():
    # Make sure the user has an active session.  If not, redirect to the login page.
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        user_profile = get_profile(usr)
        return render_template("drag_drop.html", user_profile=user_profile)
    else:
        return redirect(url_for("login_get"))


@server.route('/accounts/logout')
def logout():
    session.pop("usr", None)
    return redirect(url_for("index"))

############################################# authentification




########################ghraph 1
dash_app1.head = [html.Link(rel='stylesheet', href="https://cdnjs.cloudflare.com/ajax/libs/bulma/0.7.1/css/bulma.min.css")]
dash_app1.layout = html.Div([
    html.H1("Overview"),
    dcc.Graph(id='graph'),
    html.Label([
        "Domaine",
        dcc.Dropdown(
            id='choixDomaine', clearable=False,
            value='big data', options=[
                {'label': c, 'value': c}
                for c in domainesTotaux
            ]),
        html.Button('Suivant', id='submit-val', n_clicks=0,
                    style={"background-color": " #428bca", "text-align": "center", 'border-radius': '4px',
                           "color": "white"}),
    ]),
])

# Define callback to update graph

@dash_app1.callback(
    Output('graph', 'figure'),
    [Input("choixDomaine", "value")]
)
def update_figure(domaine):
    data = pd.read_csv("DonneesCV.csv")
    nomCV = data.to_dict()["Informations"][0]
    df = compDomaineNiveau(nomCV, domaine, graph)
    render_dashboard2()
    print("###\n###\n###\n###\n")
    fig = px.pie(
        df, names="Competences", values="Score",
        title="Champs des compétences pour le domaine : " + domaine
    )
    fig.update_traces(textposition='inside')
    fig.update_layout(uniformtext_minsize=12, uniformtext_mode='hide')

    return fig
########################ghraph 1


########################ghraph 2
dash_app2.layout = html.Div([
    html.H1("Avancé"),
    html.Div([
        dcc.Graph(id='graph2'),
    ], className='divBorder',
        style={'height': "750px", 'width': '50%', "float": "left", 'display': 'inline-block', 'padding': '0 20'}),
    html.Div([
        html.Label([
            "Domaine",
            dcc.Dropdown(
                id='choixDomaine2', clearable=False,
                value='big data', options=[
                    {'label': c, 'value': c}
                    for c in domainesTotaux
                ], style={"width": "50%"})
        ]),
    ], className='divBorder',
        style={'height': "750px", 'width': '40%', "float": "left", 'display': 'inline-block', 'padding': '0 20'})
])  # Define callback to update graph


@dash_app2.callback(
    Output('graph2', 'figure'),
    [Input("choixDomaine2", "value")]
)
def update_figure2(domaine):
    data = pd.read_csv("DonneesCV.csv")
    nomCV = data.to_dict()["Informations"][0]
    df = compDomaineNiveau(nomCV, domaine, graph)

    return px.bar(
        df, x="Competences", y="Score",
        color_continuous_scale=domaine,
        title="Niveau de compétences pour le domaine : " + domaine
    )  # Run app and display result inline in the notebook

server.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
########################ghraph 2


######################## Métiers
listeAllMetiers=graph.run("""Match (metiers:Metier) RETURN metiers""")
listeAllMetiers=listeAllMetiers.data()
listeAllMetiers=[x["metiers"]["nomMetier"] for x in listeAllMetiers]


dash_metiers.layout=html.Div([
    html.H1("Métiers similaires",style={'textAlign':'center'}),
    html.Div([
    html.Label([
        "Métiers",
        dcc.Dropdown(
            id='choixMetiers', clearable=False,
            value=listeAllMetiers[0], options=[
                {'label': c, 'value': c}
                for c in listeAllMetiers#["Data-scientist","Développeur web","Data analyst","Data Ingineer","Boulanger"]
                # a remplacer par metiers de l'ontologie quan dispo
            ],style={"width":"50%"})
    ]),
    ],className='divBorder',style={'height':"60px",'width': '90%',"float":"center", 'display': 'inline-block', 'padding': '0 20'}),
 
    html.Div([
    dcc.Graph(id='graphMetiers'),
    ],className='divBorder',style={'height':"150px",'width': '50%',"float":"left", 'display': 'inline-block', 'padding': '0 20'}),
    html.Div([
    dcc.Graph(id='graphMetierChoisi'),
    ],className='divBorder',style={'height':"150px",'width': '50%',"float":"left", 'display': 'inline-block'}),   
])
@dash_metiers.callback(
    Output('graphMetiers', 'figure'),
    Output('graphMetierChoisi', 'figure'),
    [Input("choixMetiers", "value")]
)
def update_metier(metier):
    data=pd.read_csv("DonneesCV.csv")
    nomCV=data.to_dict()["Informations"][0]

    df=compMetiers(nomCV,graph)
    graphListeMetiers=px.bar(
        df, x="Metier", y="Score",
        title="Niveau de compétences pour les différents métiers reliés à vos compétences : "
    )
    graphListeMetiers.update_layout(plot_bgcolor=colors['background'],
                                    paper_bgcolor=colors['background'],
                                    font_color=colors['text']
                                    )
    
    df2=selectMetier(nomCV,metier,graph)
    graphMetierChoisi=px.bar(
        df2, x="Competence", y="Score",
        title="Niveau de compétences pour le métier : "+metier
    )
    graphMetierChoisi.update_layout(plot_bgcolor=colors['background'],
                                    paper_bgcolor=colors['background'],
                                    font_color=colors['text']
                                    )
    
    return graphListeMetiers,graphMetierChoisi # Run app and display result inline in the notebook

######################## Métiers

dash_formations.layout=html.Div([
    html.H1("Formations "),
    
])









@server.route('/')
def index():
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        user_profile = get_profile(usr)
        return render_template("drag_drop.html", user_profile=user_profile)
    else:
        return render_template("drag_drop.html")


@server.route('/dashboard')
def render_dashboard():
    return flask.redirect("/dash1")


@server.route('/dashboard2')
def render_dashboard2():
    return flask.redirect("/dash2")


@server.route('/dashboardmetiers')
def render_dashmetiers():
    return flask.redirect("/dashmetiers")

@server.route('/dashboardformations')
def render_dashformations():
    return flask.redirect("/dashformations")


@server.route('/lancement', methods=["POST"])
def analyzedossier():
    global graph, onto
    if request.method == 'POST':
        # pathway = request.form['cv_pathway']

        nomCV, text = lancementGraphDossier()
        nomCV = nomCV.split("/")[-1]
    for i in text.replace("\n", " ").split(" "):
        if "@" in i:
            mail = i

    essai = text.replace('.', ' ').replace('-', ' ')
    x = re.findall("[0-9][0-9] [0-9][0-9] [0-9][0-9] [0-9][0-9] [0-9][0-9]", essai)[0]
    tel = "".join(x.split(" "))

    donnees = {"nom": nomCV,
               "mail": mail,
               "tel": tel}
    # print("###\n###\n",donnees)
    df = pd.DataFrame(list(donnees.values()), columns=['Informations'], index=list(donnees.keys()))
    df.to_csv("DonneesCV.csv")

    return render_template('lancement.html', nomCV=nomCV)


@server.route('/uploads/<name>')
def download_file(name):
    return send_from_directory(server.config["UPLOAD_FOLDER"], name)


@server.route('/suppIndiv')
def suppIndiv():
    mdp = open("mdp.txt", "r").read()
    graph = Graph("localhost:7474", user="neo4j", password=mdp)
    deleteOnGraph(graph, 'indiv')
    return render_template('home.html')


@server.route('/suppAll')
def suppAll():
    global graph
    deleteOnGraph(graph, 'all')
    return render_template('home.html')


@server.route('/createComp')
def createComp():
    global graph, onto
    graph.run("""CREATE (ajoutSect:Secteur {nomSect:"informatique"})""")
    recreerBase(graph, onto)

    return render_template('home.html')


@server.route('/lancement2', methods=["GET", "POST"])
def analyzefichier():
    print("je passe par le fichier")

    if request.method == 'POST':
        # check if the post request has the file part
        print("ok 0")
        print(request.files)
        if 'myfile' not in request.files:
            flash('No file part')
            return render_template("drag_drop.html")
            # return redirect(request.url)
        file = request.files['myfile']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            #return redirect(request.url)
            return render_template("drag_drop.html")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(server.config['UPLOAD_FOLDER'], filename))
            # return redirect(url_for('download_file', name=filename))
        print("my file name : ", filename)
        chemin = server.config['UPLOAD_FOLDER'] + filename
        #print("le chemin :", chemin)

        nomCV, text = lancementGraphFichier(chemin)
        nomCV = nomCV.split("/")[-1]
        for i in text.replace("\n", " ").split(" "):
            if "@" in i:
                mail = i
        if 'mail' not in locals():
            mail="inconnu"
#Prend en compte le cas de figure ou les couples de chiffres sont separes par des espaces, par des points, par des tirets
#et lorsqu'il y a des parenthèse apres le 06 ex +33(06)10101010

        essai = text.replace('.', ' ').replace('-', ' ')
        try:
            x = re.findall("[0-9][0-9]\)?\s?[0-9][0-9]\s?[0-9][0-9]\s?[0-9][0-9]\s?[0-9][0-9]", essai)
            tel=x[0].replace(" ","").replace(")","")
        except:
            tel="inconnu"

        donnees = {"nom": nomCV,
                   "mail": mail,
                   "tel": tel}
        df = pd.DataFrame(list(donnees.values()), columns=['Informations'], index=list(donnees.keys()))
        df.to_csv("DonneesCV.csv")
        # supression du cv chargé dans le dossier upload une fois ajouté a la base NoSQL
        os.remove(chemin)

        if "usr" in session:
            usr = session["usr"]
            session["usr"] = usr
            user_profile = get_profile(usr)
            return render_template("lancement.html", user_profile=user_profile, nomCV=nomCV)
        else:
            return redirect(url_for("register_get"))


########################################################## mon code


appi = dash.Dash(__name__, server=server, url_base_pathname='/sbd/')

SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background": "#FFEFFB",
    "text-align": "center",
    "color":"#D30E6D",

}

# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

sidebar = html.Div(
    [

        html.Br(),
        html.Img(src='https://wevops.fr/wp-content/uploads/2021/04/cropped-Group-311-1.png',width="200px"),
        #html.Div(html.H1("WEVOPS"), style={"background-color": " white", "color": "#D30E6D", "text-align":"center",
        #                                               "padding-top":"4px", "padding-bottom":"3px", "border-radius":"8px"}),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        dbc.Nav(
            [
                dbc.NavLink("Analyse simple ", href="/sbd/", active="exact"),
                html.Br(),
                dbc.NavLink("Analyse Avancée", href="/sbd/1", active="exact"),
                html.Br(),
                dbc.NavLink("Réorientation", href="/sbd/2", active="exact"),
                html.Br(),
                dbc.NavLink("Formations", href="/sbd/3", active="exact"),
                html.Br(),
                dbc.NavLink("Analyser un autre CV", href="http://192.168.1.5:8080/", active="exact"),
                html.Br()

            ],
            vertical=True,
            pills=True,

        ),
    ],
    style=SIDEBAR_STYLE,
)

content = html.Div(id="page-content",
                    style=CONTENT_STYLE)

appi.layout = html.Div([dcc.Location(id="url"), sidebar, content])


#@appi.callback([Input('back','n_clicks')])
#def retour(n_clicks):
    #print(n_clicks)
    #return dcc.Location(pathname="/")

@appi.callback(Output("page-content", "children"), [Input("url", "pathname")])


@server.route('/sbd')
def sidebar_f(pathname):
    if pathname == "/sbd/":
        data=pd.read_csv("DonneesCV.csv")
        nomCV=data.to_dict()["Informations"][0]
        dfgeneral=scoreDomaines(nomCV,graph)
        figResume =px.pie(
                        dfgeneral, names="Domaine", values="Score",
                        title="Niveau de compétences dans les différents domaines",
                        width=1140,height=500)
        figResume.update_layout(plot_bgcolor="white",
                                paper_bgcolor="#F0F0F0",
                                font_color=colors['text']
                                #colors['background']
                                )
        resultat_1 = html.Div([
            html.Div(html.H1("Analyse simple"), style={"background-color": " #D30E6D", "color": "white", "text-align":"center",
                                                       "padding-top":"10px", "padding-bottom":"10px"}),
            html.Br(),
            html.Br(),
            html.Div([
                    dcc.Graph(id='summaryGraph',figure=figResume)
                    ],className='divBorder',style={"float":"center", 'display': 'inline-block', 'padding': '0 20',
                                                   "border":"0px black solid","border-radius": "0px","background-color":"transparent"}),
                    ])# Define callback to update graph
        
        return resultat_1

    elif pathname == "/sbd/1":
        resultat_2 = html.Div([
            html.Div(html.H1("Analyse Avancé"),
                     style={"background-color": " #D30E6D", "color": "white", "text-align": "center",
                            "padding-top": "10px", "padding-bottom": "10px"}),
            html.Br(),

            html.Div([
                html.Label([
                    "Choisissez un domaine :",
                    html.Br(),

                    dcc.Dropdown(
                        id='choixDomaine2', clearable=False,
                        value='big data', options=[
                            {'label': c, 'value': c}
                            for c in domainesTotaux
                        ], style={"width": "100%", "background-color": "white", "border-color": "#F0F0F0",
                                  "border-radius": "0px"})
                ]),
            ], className='divBorder', style={'height': "100%", 'width': '100%', "float": "center"}),
            html.Br(),

            html.Div([
                html.Div([
                    dcc.Graph(id='graph2'),
                ], className='divBorder', style={'display': 'inline-block', 'padding': '0', "border": "0px black solid",
                                                 "border-radius": "0px", "background-color": "#F0F0F0",
                                                 'height': '100%', 'width': '100%'}),
                html.Br(),
                html.Br(),
                html.Div([
                    dcc.Graph(id='graph2Domaine'),
                ], className='divBorder', style={'display': 'inline-block', 'padding': '0', "border": "0px black solid",
                                                 "border-radius": "0px", "background-color": "#F0F0F0",
                                                 'height': '100%', 'width': '100%'}),

                html.Br(),
                html.Br(),
                html.Div([
                    dcc.Graph(id='graphPie'),
                ], className='divBorder', style={'display': 'inline-block', 'padding': '0', "border": "0px black solid",
                                                 "border-radius": "0px", "background-color": "#F0F0F0",
                                                 'height': '100%', 'width': '100%'}),
                html.Br(),
            ], className='divBorder', style={'width': '100%', "float": "center"})
        ])
        return resultat_2



    elif pathname == "/sbd/2":

        #########################################################################################

        resultat_3= html.Div([
            html.Div(html.H1("Réorientation vers des métiers selon vos compétences"),
                     style={"background-color": " #D30E6D", "color": "white", "text-align":"center",
                                                       "padding-top":"10px", "padding-bottom":"10px"}),
            html.Br(),

            html.Div([
                html.Label([
                    "Choisissez un métier :",
                    html.Br(),

                    dcc.Dropdown(
                        id='choixMetiers', clearable=False,
                        value=listeAllMetiers[0], options=[
                            {'label': c, 'value': c}
                            for c in listeAllMetiers
                        ], style={"width": "100%", "background-color": "white", "border-color": "#F0F0F0",
                                  "border-radius": "0px"})
                ]),
            ], className='divBorder', style={'height': "100%", 'width': '100%', "float": "center"}),
            html.Br(),

                html.Div([
                    html.Div([
                        dcc.Graph(id='graphMetiers'),
                    ], className='divBorder', style={'display': 'inline-block', 'padding': '0', "border": "0px black solid",
                                                     "border-radius": "0px", "background-color": "#F0F0F0", 'height':'100%', 'width':'100%'}),
                    html.Br(),
                    html.Br(),
                    html.Div([
                        dcc.Graph(id='graphMetierChoisi'),
                    ], className='divBorder', style={'display': 'inline-block', 'padding': '0', "border": "0px black solid",
                                                     "border-radius": "0px", "background-color": "#F0F0F0", 'height':'100%', 'width':'100%'}),
                    html.Br(),
                ], className='divBorder', style={'width': '100%', "float": "center"}),

                html.Div([
                    html.Button('Rechercher une formation', id='button_pred', n_clicks=0,style={"background-color":" #428bca","text-align": "center",'border-radius': '4px',"color":"white"}),
                ])
        ])
####################################################################
        return resultat_3

    elif pathname == "/sbd/3":
        metierVoulu="Ingenieur-reseau-Exemple"
        resultatFormation=trouverFormation(graph,metierVoulu)
        
        resultat_4 = html.Div([
                        html.Div([
                            html.H1("Formations"),  
                        ],style={"background-color": " #D30E6D", "color": "white", "text-align": "center"}),
                        html.Div([
                            html.Label([
                                "Choisissez un métier :",
                                html.Br(),

                                dcc.Dropdown(
                                    id='choixMetiers2', clearable=False,
                                    value=listeAllMetiers[0], options=[
                                        {'label': c, 'value': c}
                                        for c in listeAllMetiers
                                    ], style={"width": "100%", "background-color": "white", "border-color": "#F0F0F0",
                                            "border-radius": "0px"})
                            ]),
                        ], className='divBorder', style={'height': "100%", 'width': '100%', "float": "center"}),
                        dcc.Markdown(resultatFormation,id="listeResultatsformations"),
                        
                        ])
        
        return resultat_4

    # If the user tries to reach a different page, return a 404 message
    return dbc.Jumbotron(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ]
    )

@appi.callback(
    Output('graphPie', 'figure'),
    Output('graph2', 'figure'),
    Output('graph2Domaine', 'figure'),
    [Input("choixDomaine2", "value")]
)
def update_figure2(domaine):
    data=pd.read_csv("DonneesCV.csv")
    nomCV=data.to_dict()["Informations"][0]
    df=compDomaineNiveau(nomCV,domaine,graph)
    niveauUnDomaine=px.bar(
        df, x="Competences", y="Score",
        color_continuous_scale=domaine,
        title="Niveau de compétences pour le domaine : "+domaine,
        width=1132,height=400
    )
    niveauUnDomaine.update_layout(plot_bgcolor=colors['background'],
                                    paper_bgcolor=colors['background'],
                                    font_color=colors['text']
                                    )
    df2=scoreDomaines(nomCV,graph)
    niveauToutDomaines=px.bar(
        df2, x="Domaine", y="Score",
        title="Niveau de compétences dans les différents domaines ",
        width=1132,height=400
    )
    niveauToutDomaines.update_layout(plot_bgcolor=colors['background'],
                                    paper_bgcolor=colors['background'],
                                    font_color=colors['text']
                                    )

    df3=compDomaineNiveau(nomCV,domaine,graph)
    figResume = px.pie(
        df3, names="Competences", values="Score",
        title="Champs des compétences pour le domaine : "+domaine,
        width=1132,height=400
    )
    figResume.update_traces(textposition='inside')
    figResume.update_layout(uniformtext_minsize=12, uniformtext_mode='hide')
    figResume.update_layout(plot_bgcolor=colors['background'],
                                    paper_bgcolor=colors['background'],
                                    font_color=colors['text']
                                    )
    
    return figResume,niveauUnDomaine,niveauToutDomaines# Run app and display result inline in the notebook

@appi.callback(
    Output('graph', 'figure'),
    [Input("choixDomaine", "value")]
)
def update_figure(domaine):
    data = pd.read_csv("DonneesCV.csv")
    nomCV = data.to_dict()["Informations"][0]
    df = compDomaineNiveau(nomCV, domaine, graph)
    render_dashboard2()
    fig = px.pie(
        df, names="Competences", values="Score",
        title="Champs des compétences pour le domaine : " + domaine
    )
    fig.update_traces(textposition='inside')
    fig.update_layout(uniformtext_minsize=12, uniformtext_mode='hide')
    fig.update_layout(plot_bgcolor=colors['background'],
                                    paper_bgcolor=colors['background'],
                                    font_color=colors['text']
                                    )

    return fig


@appi.callback(
    Output('graphMetiers', 'figure'),
    Output('graphMetierChoisi', 'figure'),
    [Input("choixMetiers", "value")]
)
def update_metier(metier):
    data = pd.read_csv("DonneesCV.csv")
    nomCV = data.to_dict()["Informations"][0]

    df = compMetiers(nomCV, graph)
    graphListeMetiers = px.bar(
        df, x="Metier", y="Score",
        title="Niveau de compétences pour les différents métiers reliés à vos compétences : "
    )
    graphListeMetiers.update_layout(plot_bgcolor=colors['background'],
                                    paper_bgcolor=colors['background'],
                                    font_color=colors['text']
                                    )

    df2 = selectMetier(nomCV, metier, graph)
    graphMetierChoisi = px.bar(
        df2, x="Competence", y="Score",
        title="Niveau de compétences pour le métier : " + metier
    )
    graphMetierChoisi.update_layout(plot_bgcolor=colors['background'],
                                    paper_bgcolor=colors['background'],
                                    font_color=colors['text']
                                    )

    return graphListeMetiers, graphMetierChoisi


@appi.callback(
    Output('listeResultatsformations', 'children'),
    [Input("choixMetiers2", "value")]
)
def update_formation(metierVoulu):
    resultatFormation=trouverFormation(graph,metierVoulu)
    return resultatFormation





########################################################## mon code

app = DispatcherMiddleware(server, {
    '/dash1': dash_app1.server,
    '/dash2': dash_app2.server,
    "/dashmetiers" : dash_metiers.server,
    "/dashformations" : dash_formations.server,



})
run_simple('0.0.0.0', 8080, server, use_reloader=True, use_debugger=True)
