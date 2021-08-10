
import pandas as pd
import numpy as np
import unidecode
from owlready2 import *
import os
import tika
tika.initVM()
from tika import parser
from nltk import wordpunct_tokenize

from py2neo import Graph
from py2neo import Node, Relationship

from flask import Flask, flash, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta



onto=get_ontology("file://base_onto.owl").load()



def extract_text(file_path):
    '''
    Wrapper function to detect the file extension and call text extraction function accordingly
    :param file_path: path of file of which text is to be extracted
    :param extension: extension of file `file_name`
    '''
    # extension=file_path.split(".")[1]
    # text = ''
    # if extension == 'pdf':
    #     text += pdf_to_text(file_path)

    # elif extension == 'docx' or extension == 'doc':
    #     text = docx_to_text(file_path)
    # return text
    #print(file_path)
    parsed = parser.from_file(file_path)
    return parsed["content"]


def transform_string(inputs) :
    #morphologie
    #input=string_morphologie(input)
    #l'appostrof non detecté
    if(len(inputs)>3) :
        if(inputs[0]=="l") :
            inputs=inputs[1:]
    #pluriel
    if(len(inputs)>2) :
        if(inputs[-1]=="s") :
            inputs=inputs[:-1]
    if(len(inputs)>2) :
        if(inputs[-1]=="x") :
            inputs=inputs[:-1]
    #féminin
    if(len(inputs)>3) :
        if(inputs[-1]=="e") :
            inputs=inputs[:-1]
    #remplacement :
        tInput=unidecode.unidecode(inputs.lower())
        #tInput=inputs.replace("é","e").replace("ê","e").replace("è","e")
        #tInput=tInput.replace("à","a").replace("â","a")
        #tInput=tInput.replace("ô","o").replace("ö","o")
        #tInput=tInput.replace("î","i").replace("ï","i")
        #tInput=tInput.replace("î","i").replace("ï","i")
    #elimination des caractères dupliqués
    #    L1=[]
    #    for i in range(0,len(tInput)-1) :
    #        if(tInput[i].lower()!=tInput[i+1].lower()) :
    #            L1.append(tInput[i].lower())
    #    L1.append(tInput[len(tInput)-1].lower())
    #    tk=""
    #    for i in L1 :
    #        tk=tk+i
    #    return tk
    #else :
    return tInput
    
def replace_accro_spec(liste):
    if "elk" in liste:
        for i in ["elasticsearch","logstash","kibana"]:
            liste.insert(liste.index('elk'),i)
    return liste


def replace_spec(desc_text) :
    mappage={".net":"dotnet",
             "vbscript":"vb",
             "ms sql":"sql server",
             "reportone":"report one",
             "businessobjects":"business object",
             "ms bi":"msbi",
             "c++":"cplus",
             "pl/sql":"pl sql",
             "pl\sql":"pl sql",
             "c#":"csharp",
             "t-sql":"t sql",
             "transact-sql":"t sql",
             " de ":" ",
             " des ":" ",
             " au ":" ",
             " à ":" ",
             " l'":" ",
             ".js":"js",
             " r ":" langage_r ",
             " r.":" langage_r ",
             " r,":" langage_r ",
             ",r ":" langage_r ",
             " r,":" langage_r ",
             ";r ":" langage_r ",
             " r;":" langage_r ",
             "scikit-learn":"scikitlearn"}
    descriptif=desc_text.lower()
    
    for ancien, nouveau in mappage.items():
        descriptif = descriptif.replace(ancien, nouveau)

    
    
    
    #l'onto possede des competences avec "caractère espace"
    #donc on ne peut pas juste directement tokeniser
    for i in onto.Competence.instances() :
        if (' ' in i.nomC) and (i.nomC in descriptif) :
            # on cree une balise de marquage pour reintroduire l'espace apres tokenisation
            descriptif=descriptif.replace(i.nomC,i.nomC.replace(' ','__'))
       
    descriptif=wordpunct_tokenize(descriptif)
    

    descriptif=[x.replace("__"," ") for x in descriptif]
    
    descriptif=replace_accro_spec(descriptif)
    return descriptif

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'txt', 'pdf',"doc","docx"}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class cv() :
    def __init__(self,path):
        self.path = path


def deleteOnGraph(graph,objet):
    if objet=='all':
        graph.run("""MATCH (n:CompetenceNonAcquise) DETACH DELETE n""")
        graph.run("""MATCH (n:Competence) DETACH DELETE n""")
        graph.run("""MATCH (n:Domaine) DETACH DELETE n""")
        graph.run("""MATCH (n:Secteur) DETACH DELETE n""")
        graph.run("""MATCH (n:Individu) DETACH DELETE n""")
        print("Base intégralement supprimée")
    elif objet=="indiv":
        graph.run("""MATCH (n:Individu) DETACH DELETE n""")
        print("Individus de la base supprimés")

def recreerBase(graph,onto):
    #deleteOnGraph(graph,"all")
    for i in onto.Domain.instances() :
        graph.run('''MATCH (info:Secteur {nomSect:"informatique"}) 
                    CREATE (ajoutDom:Domaine {nomDom:"%s"})\
                    CREATE (info)-[:POSSEDE]->(ajoutDom)'''%(i.nomD))
        for j in i.has_competence:
            #on verifie si la compétence exite déja, au cas ou ell appartiendrai à plusieurs domaines
            test=graph.run('''MATCH (comp:Competence {nomComp:"%s"}) RETURN comp'''%j.nomC)
            if not(test.data()):# cas ou la competence est pas encore dans la base
                graph.run('''MATCH (dom:Domaine {nomDom:"%s"})\
                CREATE (ajoutComp:Competence {nomComp:"%s"})\
                CREATE (dom)-[:POSSEDE]->(ajoutComp)'''%(i.nomD,j.nomC))
            else: # cas ou le domaine est deja dans la base
                graph.run('''MATCH (dom:Domaine {nomDom:"%s"})\
                MATCH (ajoutComp:Competence {nomComp:"%s"})\
                CREATE (dom)-[:POSSEDE]->(ajoutComp)'''%(i.nomD,j.nomC))
    print("Base recrée")



def lancementGraphDossier():
    for filename in os.listdir('cvs'):
        if filename!=".DS_Store":
            path="cvs/"+filename
            print('cv :','>>>>',path,'<<<<')
            print('***********************************************')
            cv1=cv(path)
            cv_txt=extract_text(cv1.path)
            print(cv1.path)
            nomCV=path.split("/")[-1].split(".")[0]
            lancementGraph(cv_txt,nomCV)
    
    return(nomCV,cv_txt)

def lancementGraphFichier(path):
    #print("#### lancement fichier ####")
    cv1=cv(path)
    cv_txt=extract_text(cv1.path)
    nomCV=path.split("/")[-1].split(".")[0]
    lancementGraph(cv_txt,nomCV)
    return(nomCV,cv_txt)

def evalNiveau(motsDuCV):
    mois={"janvier":"01",
        "fevrier":"02",
        "mars":"03",
        "avril":"04",
        "mai":"05",
        "juin":"06",
        "juillet":"07",
        "aout":"08",
        "septembre":"09",
        "octobre":"10",
        "novembre":"11",
        "decembre":"12"
        }
    niveauComp={}
    allComp=[x.nomC for x in onto.Competence.instances()]
    i=0
    debutEtFin=False
    while i < len(motsDuCV) :
        #si on tombe sur une categorie du CV appellée "compétences" ou "hard skills" on n'affecte plus a la derniere durée d'emploi trouvée car la personne liste ses coméptences générales, pas celles associées a sa dernière expé
        if unidecode.unidecode(motsDuCV[i].lower()) in ["competence","competences","skills"]:
            debutEtFin=False
        if debutEtFin==True:
            if motsDuCV[i] in allComp:
                #print(motsDuCV[i])
                if motsDuCV[i] in niveauComp.keys():
                    niveauComp[motsDuCV[i]]=niveauComp[motsDuCV[i]]+duree.days
                else:
                    niveauComp[motsDuCV[i]]=duree.days
                #print(niveauComp)
        if (motsDuCV[i].isnumeric()) and (len(motsDuCV[i])==4):
            anneesExpe,moisExpe=[],[]
            #print("on tombe sur l annee:",motsDuCV[i])
            anneeDebut=int(motsDuCV[i])
            debutEtFin=True #indique qu'on a trouvé une date et qu'on recherche les competences qu'il a utilisé pendant cette période
            for j in [-3,-2,-1,0,1,2,3]: #des qu'on detecte une annee, on regarde les 3mots avant et les 3 mots apres pour essayer de choper les mois debut et fin, et anne de fin
                
                if unidecode.unidecode(motsDuCV[i+j].lower()) in mois.keys(): # cas ou date ecrite sous forme 'mois (lettres) - annee"
                    moisExpe.append(mois[motsDuCV[i+j].lower()])
                elif  (motsDuCV[i+j].isnumeric()) and (len(motsDuCV[i+j])==2) and (int(motsDuCV[i+j])<=12):# cas ou date ecrite xx/xxx
                    moisExpe.append(int(motsDuCV[i+j]))

                elif (motsDuCV[i+j].isnumeric()) and (len(motsDuCV[i+j])==4) :#on a trouvé une annee dans les momts suivants
                    anneesExpe.append(int(motsDuCV[i+j]))
                
                
            
            if len(moisExpe)==0: # s'il ne met pas de mois c'est quec'est annee complete
                moisExpe.extend([1,12])
            #print("mois detectes :",moisExpe,"annees detectes :",anneesExpe)    
            #print(" ** experience du ",moisExpe[0],anneesExpe[0],"au",moisExpe[-1],anneesExpe[-1],"\n")
            dateDebut = datetime(year=int(anneesExpe[0]), month=int(moisExpe[0]), day=1)
            dateFin = datetime(year=int(anneesExpe[-1]), month=int(moisExpe[-1]), day=28)#on conidere la fin du mois et on au cas ou il ai fini en fevrier ou il peut n'y avoir que 28 jours on defini une fin de mois a 28
            duree=dateFin-dateDebut
            #print(dateDebut,"-",dateFin,":",duree.days,"jours\n")
            i+=j
        i+=1
    return(niveauComp)


def lancementGraph(cv_txt,nomCV="inconnu"):
    mdp = open("mdp.txt", "r").read()
    graph = Graph("localhost:7474", user="neo4j", password=mdp)

    #print("Contenu ",cv_txt)
    text=transform_string(cv_txt)
    #print("texte :",text)
    motsDuCV=replace_spec(text)


    niveauComp=evalNiveau(motsDuCV)


    #print(motsDuCV)
     #Detection des competences 
    codeCompetences=[x for x in onto.Competence.instances() if x.nomC in motsDuCV]
    codeDomaine=pd.Series(list(chain.from_iterable([x.has_domaine for x in codeCompetences]))).drop_duplicates().to_list()
    codeSecteur=[]
    for x in onto.Secteur.instances():
        sectSimilaires=[x.nomS]+x.same_as
        for i in sectSimilaires:
            if i in motsDuCV:
                codeSecteur.append(x)

    competencesPossedees=[x.nomC for x in codeCompetences]
    domainesPossedes=[x.nomD for x in codeDomaine]
    secteurPossedes=[x.nomS for x in codeSecteur]
        
    graph.run("""CREATE (ajoutIndiv:Individu {nomIndiv:"%s"})"""%nomCV)

    for i in codeCompetences :
        if i.nomC in niveauComp:
            expeJour=niveauComp[i.nomC]
        else:
            expeJour="100"#par defaut si il dit pas dans quelles missions il a utilisé cette comp on considere 100 jours d experience
        
        #poids=1#correspondra par la suite au poids de la compétence pour cet individu calculé et pondéré a partir du temps d' experience
        if int(expeJour)<30:# moins d'un mois
            poids=2
        elif  int(expeJour)<360:# moins d'1 an
            poids=10
        elif  int(expeJour)<1090 : #entre 1 et 3 ans
            poids=20
        elif  int(expeJour) < 1800 :# entre 3 et 5 ans
            poids=40
        elif  int(expeJour) <2500 :# entre 5 et 7 ans
            poids=60
        elif  int(expeJour) <3600 :# entre 7 et 10 ans
            poids=80
        else: #plus de 10 a,ns
            poids=100
        
        graph.run("""MATCH (indiv:Individu {nomIndiv:"%s"})
        MATCH (comp:Competence {nomComp:"%s"})
        CREATE (indiv)-[:POSSEDE {poids:%d , expeJour:"%s"}]->(comp)
        """%(nomCV,i.nomC,poids,expeJour))
    
    return(nomCV)


def trouverFormation(graph,metierVoulu):
    
    competencesmetier=graph.run("""MATCH (metier:Metier {nomMetier:"%s"})-[:NECESSITE]->(comp:Competence) RETURN  comp.nomComp
    """%(metierVoulu)).data()
    competencesmetier=[x['comp.nomComp'] for x in competencesmetier]

    listeFormation=[]
    for i in competencesmetier :
        formationsPossibles=graph.run("""MATCH (formation:Formation)-[:ENSEIGNE]->(comp:Competence {nomComp:"%s"}) RETURN  formation.nomFormation
        """%(i)).data()
        formationsPossibles=[x['formation.nomFormation'] for x in formationsPossibles]
        listeFormation.extend(formationsPossibles)
    listeFormation=list(pd.Series(listeFormation).unique())
    return listeFormation


def compMetiers(nomCV,graph):
    metiersproches=graph.run("""MATCH (personne:Individu {nomIndiv:"%s"})-[lien1:POSSEDE]->(comp:Competence)<-[:NECESSITE]-(metier:Metier) RETURN  lien1,comp,metier
"""%(nomCV))

    metiersprochesdata=metiersproches.data()

    #On récupère les compétences qui peuvent lui resservir dans d'autres métiers, les métiers en questions ou il a des compétences, et son niveau sur chaque compétence 
    metiersproches=list(pd.Series([x["metier"]["nomMetier"] for x in metiersprochesdata]).unique())
    niveauIndividuComp=[x['lien1']["poids"] for x in metiersprochesdata]
    compIndividu=[x['comp']["nomComp"] for x in metiersprochesdata]
    
    #On associe son niveau sur les differentes competences dans un dict
    indivComp={}
    for i,j in zip(compIndividu,niveauIndividuComp):
        if i in indivComp.keys():
            continue
        else:
            indivComp[i]=j
    
    #On met dans un dictionnaire les compétences demandées pour chaque métier proche de son domaine
    metierComp={}
    for i in metiersproches:
        compMetier=graph.run("""MATCH (metier:Metier {nomMetier:"%s"})-[:NECESSITE]->(comp:Competence) RETURN comp"""%(i))
        comp=compMetier.data()
        comp=[x["comp"]["nomComp"] for x in comp]
        metierComp[i]=comp

    #on calcule un score pour chaque métier grace aux scores de compétences et aux compétences demandés par métier
    niveauMetier={}
    for i in metierComp.keys():
        #print(i)
        valeur=0
        for j in metierComp[i]:
            if j in indivComp.keys():
                valeur=valeur+int(indivComp[j])
        niveauMetier[i]=valeur/len(metierComp[i]) 
        #print(valeur)

    #print(niveauMetier)
    df=pd.DataFrame(list(niveauMetier.items()), columns=['Metier', 'Score'])
    
    return df

def selectMetier(nomCV,metierChoisi,graph):
    compDuMetier=graph.run("""MATCH (metier:Metier {nomMetier:"%s"})-[:NECESSITE]->(comp:Competence)RETURN  comp
    """%(metierChoisi)).data()
    compDuMetier=[x['comp']["nomComp"] for x in compDuMetier]
    niveauChaqueComp={}
    for i in compDuMetier :
        competenceLevel=graph.run("""MATCH (indiv:Individu {nomIndiv:"%s"})-[lien:POSSEDE]->(comp:Competence {nomComp:"%s"}) RETURN  comp,lien
        """%(nomCV,i)).data()

        niveauIndividuComp=[x['lien']["poids"] for x in competenceLevel]
        if not niveauIndividuComp  :
            niveauIndividuComp=0
        else:
            niveauIndividuComp=niveauIndividuComp[0]
        niveauChaqueComp[i]=int(niveauIndividuComp)

    df=pd.DataFrame(list(niveauChaqueComp.items()), columns=['Competence', 'Score'])

    return df
def scoreDomaines(nomCV,graph):
    compParDomaine={}
    niveau=graph.run("""MATCH (indiv:Individu {nomIndiv:"%s"})-[lien:POSSEDE]->(comp:Competence)<-[:POSSEDE]-(dom:Domaine) RETURN  comp,lien,dom
    """%(nomCV)).data()
    allCompIndiv=[x["comp"]["nomComp"] for x in niveau]
    allNiveauIndiv=[int(x["lien"]["poids"]) for x in niveau]
    allDomaineIndiv=[x["dom"]["nomDom"] for x in niveau]
    for comp,niveau,domaine in zip(allCompIndiv,allNiveauIndiv,allDomaineIndiv):
        if domaine in compParDomaine.keys():
            compParDomaine[domaine][comp]=niveau
        else:
            compParDomaine[domaine]={}
            compParDomaine[domaine][comp]=niveau
    sommaireCompDomaine={}
    for domaine in compParDomaine.keys():
        quantiteComp=graph.run("""MATCH (dom:Domaine {nomDom:"%s"})-[:POSSEDE]->(comp:Competence)RETURN  comp
        """%(domaine)).data()
        sommaireCompDomaine[domaine]=sum(list(compParDomaine[domaine].values()))/len(quantiteComp)
        #print(sum(list(compParDomaine[domaine].values()))/len(quantiteComp))
    df=pd.DataFrame(list(sommaireCompDomaine.items()), columns=['Domaine', 'Score'])
    return df 



def compDomaineNiveau(nomCV,domaine,graph):
    competencesDomaine=graph.run("""MATCH (dom:Domaine {nomDom:"%s"})-[:POSSEDE]->(compAssocie:Competence) RETURN compAssocie
    """%(domaine)).data()
    competencesDomaine=[x["compAssocie"]["nomComp"] for x in competencesDomaine]
    #print("Competences du domaine :",competencesDomaine)
    
    
    niveauIndividuDomaineRequete=graph.run("""MATCH (indiv:Individu {nomIndiv:"%s"})-[lien:POSSEDE]->(compAssocie), (dom:Domaine {nomDom:"%s"}) WHERE (dom)-[:POSSEDE]->(compAssocie:Competence) RETURN compAssocie,lien
        """%(nomCV,domaine)).data()
    niveauIndividuDomaine=[x['lien']["poids"] for x in niveauIndividuDomaineRequete]
    #print(niveauIndividuDomaine)
    
    competencesIndividuDomaine=[x['compAssocie']["nomComp"] for x in niveauIndividuDomaineRequete]
    #print(competencesIndividuDomaine)

    niveau=[]
    for i in competencesDomaine:
        if i in competencesIndividuDomaine:
            if niveauIndividuDomaine[competencesIndividuDomaine.index(i)]=="?":
                niveau.append(100)#valeur par defaut quand on sait pas
            else :
                niveau.append(int(niveauIndividuDomaine[competencesIndividuDomaine.index(i)]))
        else :
            niveau.append(0)
    
    competencesDomaine=pd.Series(competencesDomaine,name="Competences")
    niveau=pd.Series(niveau,name="Score")
    df=pd.concat([competencesDomaine,niveau],axis=1)

    return df

