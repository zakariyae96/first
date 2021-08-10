## Avant de commencer, il convient d'avoir installé Neo4j sur votre machine
https://neo4j.com/download-center/#community

Une fois installé, rendez vous dans le dossier d'installation (variable d'environnement NEO4J_HOME)
 et lancez :
 
    bin/neo4j console

Neo4j écoute sur le port 7474, verifiez que tout à bien fonctionné (localhost:7474)

Lors de la premier utilisation utilisez le login "neo4j" et le mot de passe "neo4j", et choisissez un nouveau mot de passe

## Vérifiez également que vous avez les librairies nécéssaires 
flask, owlready2, py2neo, numpy, pandas, unidecode ... (se référer au fichier requirements.txt pour la liste complète des dépendance)

## Fonctionnement du programme

A la racine du dossier Projet_CV créez un fichier "mdp.txt" qui contiendra le mot de passe que vous avez configuré pour Neo4j à l'étape précédente (fichier présent dans le .gitignore et non partagé sur git car dépend de chaque utilisateur)

Assurez vous que neo4j est bien lancé et à l'écoute du port 7474

Lancez le fichier app.py à la racine du dossier Projet_CV, le serveur flask se lance sur le port 5000 (localhost:5000)

* Sur la partie gauche de la page, cliquez sur valider pour envoyer le/les CV présents dans le dossier "cvs" à la racine du projet,

* Sur la partie droite de la page, cliquez sur "parcourir" pour sélectionner manuellement un CV à traiter, vous allez pouvoir choisir un fichier qui est n'importe ou sur votre ordinateur et le charger vers le serveur. Une fois sélectionné ce fichier est chargé dans le dossier "uploads" pour que python puisse aller le récupérer sur le serveur et le parser. A la fin du processus le CV est supprimé du serveur (donc du dossier "uploads")


Lorsque vous arrivez sur la page suivante, il vous affiche que le CV a bien été traité, il a donc été ajouté à la base de donnée NoSQL,
Pour visualiser le graph knowledge il suffit de requêter Neo4j en cypher 

ex : 

pour voir l'arbre complet (compétences acquises et manquantes pour chaque domaine qu'il connait)  :

    MATCH (personne:Individu)-[relatedTo*]->(m) RETURN personne,m

ou 

    MATCH (all) RETURN all

pour voir uniquement les liens compétences et domaines : 

    MATCH (comp:Competence),(dom:Domaine) RETURN comp,dom

Pour voir les compétences que possède l'individu

    MATCH (indiv:Individu)-[:POSSEDE]->(comp:Competence)<-[:POSSEDE]-(dom:Domaine) RETURN indiv,comp,dom



Vous devriez obtenir un knowledge graph similaire à "ExampleArbreCV.png" dans le dossier

## Gestion de la base
Pour tout effacer (si par exemple la structure du graph et des relations devait être revue), utilisez le bouton "supprimer la base" permet de détacher toutes les connections et supprimer les objets (individus, secteurs, domaines, compétences).

Pour réinitialiser les profils sans supprimer la base, utilisez le bouton "supprimer les individus", l'organisation "compétences/domaines/secteurs" persiste mais es individus sont détachés des compétences puis supprimés de la base

Pour effectuer un reset, le bouton "recréer la base" supprime intégralement la base de données et la recrée à partir de l'ontologie  (en cas de mise à jour de l'ontologie par exemple)