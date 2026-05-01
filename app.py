import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# Fonction pour se connecter à la base de données
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Création de la table au démarrage
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Lance l'initialisation
init_db()

from flask import Flask, render_template, request, redirect, url_for, session
import random

app = Flask(__name__)

# Une clé secrète est nécessaire pour utiliser les "sessions" (garder l'utilisateur connecté)
app.secret_key = 'inf232_secret_key_joseph'

# Dictionnaire pour stocker temporairement les codes générés { 'email': 'code' }
otp_storage = {}

def collecter_donnees_e_commerce():
    # Plus tard, tu remplaceras ce dictionnaire par ton vrai script de scraping
    # qui va lire les sites e-commerce.
    donnees_extraites = [
        {"produit": "iPhone 15 Pro", "prix": 850000, "quantite": 12},
        {"produit": "Samsung S24 Ultra", "prix": 900000, "quantite": 8},
        {"produit": "MacBook Air M3", "prix": 1200000, "quantite": 5},
        {"produit": "Sony WH-1000XM5", "prix": 250000, "quantite": 25}
    ]
    return donnees_extraites

def calculer_moindres_carres(donnees):
    """
    Calcule la droite de régression linéaire y = ax + b.
    x = Prix, y = Quantité
    """
    if not donnees:
        return 0, 0, "y = 0x + 0"
    
    n = len(donnees)
    
    # 1. Sommes nécessaires
    sum_x = sum(d['prix'] for d in donnees)
    sum_y = sum(d['quantite'] for d in donnees)
    sum_xy = sum(d['prix'] * d['quantite'] for d in donnees)
    sum_x2 = sum(d['prix'] ** 2 for d in donnees)
    
    # 2. Moyennes
    moyenne_x = sum_x / n
    moyenne_y = sum_y / n
    
    # 3. Calcul de la pente 'a' (Covariance / Variance de X)
    # Formule : a = (n * sum(xy) - sum(x)*sum(y)) / (n * sum(x^2) - (sum(x))^2)
    denominateur = (n * sum_x2) - (sum_x ** 2)
    
    if denominateur == 0:  # Éviter la division par zéro
        a = 0
    else:
        a = (n * sum_xy - sum_x * sum_y) / denominateur
        
    # 4. Calcul de l'ordonnée à l'origine 'b'
    # Formule : b = moyenne_y - a * moyenne_x
    b = moyenne_y - (a * moyenne_x)
    
    # Construction de la chaîne d'affichage pour l'équation
    signe = "+" if b >= 0 else "-"
    equation = f"y = {a:.4f}x {signe} {abs(b):.2f}"
    
    return round(moyenne_x, 2), round(a, 4), round(b, 2), equation

@app.route('/')
def index():
    # Si l'utilisateur est déjà passé par l'OTP, on l'envoie direct au Home
    if session.get('authenticated'):
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    # On vide la session pour déconnecter l'utilisateur
    session.clear()
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    
    # On vérifie si l'utilisateur existe ET si le mot de passe haché correspond
    if user and check_password_hash(user['password'], password):
        # Le mot de passe est bon, on lance l'OTP
        otp_code = str(random.randint(100000, 999999))
        otp_storage[email] = otp_code
        session['user_email'] = email
        
        print(f"\n--- CODE OTP : {otp_code} ---\n")
        return redirect(url_for('verify_otp'))
    else:
        return "Email ou mot de passe incorrect. <a href='/'>Réessayer</a>"

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        # On récupère le code saisi dans otp.html
        code_saisi = request.form.get('otp_code')
        email = session.get('user_email')
        
        # Vérification du code
        if email in otp_storage and otp_storage[email] == code_saisi:
            # Succès : on valide la session et on supprime le code utilisé
            session['authenticated'] = True
            del otp_storage[email]
            return redirect(url_for('home'))
        else:
            return "Code incorrect ! <a href='/verify-otp'>Réessayer</a>"

    # Si on arrive sur la page normalement (GET), on affiche le formulaire
    return render_template('otp.html')

@app.route('/home')
def home():
    # Sécurité : si l'utilisateur n'est pas authentifié, retour au login
    if not session.get('authenticated'):
        return redirect(url_for('index'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Sécurité : On hache le mot de passe
        hashed_pw = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                         (username, email, hashed_pw))
            conn.commit()
            conn.close()
            session['user_email'] = email
            session['authenticated'] = True

            return redirect(url_for('home'))
            
        except sqlite3.IntegrityError:
            return "Cet email est déjà utilisé ! <a href='/register'>Réessayer</a>"
            
    return render_template('register.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        # On génère un code OTP spécial pour la récupération
        otp_recovery = str(random.randint(100000, 999999))
        otp_storage[email] = otp_recovery
        session['recovery_email'] = email
        
        print(f"\n--- [RÉCUPÉRATION] CODE POUR {email} : {otp_recovery} ---\n")
        
        # On redirige vers une version modifiée de la page OTP ou une page dédiée
        return redirect(url_for('verify_recovery_otp'))
    return render_template('forgot_password.html')

@app.route('/verify-recovery-otp', methods=['GET', 'POST'])
def verify_recovery_otp():
    if request.method == 'POST':
        # 1. Récupération sécurisée
        code_saisi = request.form.get('otp_code', '').strip()
        email = session.get('user_email')
        
        # 2. Récupération du code attendu (on utilise .get pour éviter les plantages)
        code_attendu = otp_storage.get(email)

        # 3. Affichage pour comprendre ce qui se passe
        print(f"\n--- DEBUG VERIFICATION ---")
        print(f"Email en session : {email}")
        print(f"Code saisi par l'user : '{code_saisi}'")
        print(f"Code stocké en mémoire : '{code_attendu}'")
        print(f"--------------------------\n")

        # 4. Comparaison forcée en texte (String)
        if code_attendu and str(code_saisi) == str(code_attendu):
            print("RÉSULTAT : MATCH RÉUSSI !")
            session['authenticated'] = True
            return redirect(url_for('home'))
        else:
            print("RÉSULTAT : ÉCHEC DE COMPARAISON")
            return "Code incorrect ou expiré. <a href='/verify-recovery-otp'>Réessayer</a>"

    return render_template('otp.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        # Ici on ferait la mise à jour en base de données
        print(f"Mot de passe mis à jour pour {session.get('recovery_email')}")
        return redirect(url_for('index'))
    return render_template('reset_password.html')

import csv
from datetime import datetime

@app.route('/collecte/commerce', methods=['POST'])
def collect_commerce():
    # Simulation d'une collecte de données
    nom_fichier = "collecte_commerce.csv"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # On écrit une ligne de test dans un fichier CSV
    with open(nom_fichier, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, "Secteur Commerce", "Données collectées avec succès"])
    
    print(f"--- COLLECTE LANCÉE : {timestamp} ---")
    
    # On renvoie vers une page de succès ou on reste sur home avec un message
    return f"<h1>Succès !</h1><p>La collecte Commerce a été effectuée à {timestamp}.</p><a href='/home'>Retour</a>"

# Route pour afficher la page des outils
@app.route('/outils')
def outils():
    if not session.get('authenticated'):
        return redirect(url_for('index'))
    return render_template('outils.html')

# Route qui "lance" la collecte
@app.route('/run-collecte', methods=['POST'])
def run_collecte():
    return redirect(url_for('choix_analyse'))

# --- ROUTE POUR L'OPTION 1 (Lancer l'extraction) ---
@app.route('/analyser-donnees', methods=['POST'])
def analyser_donnees():
    source = request.form.get('source')
    donnees = []
    titre = ""

    # 1. Récupération des données
    if source == 'scraping':
        donnees = collecter_donnees_e_commerce()
        titre = "Résultats du Scraping E-commerce"
    elif source == 'manuel':
        noms = request.form.getlist('produit[]')
        prix_list = [float(p) for p in request.form.getlist('prix[]')]
        quantites = [int(q) for q in request.form.getlist('quantite[]')]
        
        for i in range(len(noms)):
            donnees.append({"produit": noms[i], "prix": prix_list[i], "quantite": quantites[i]})
        titre = "Analyse de Saisie Manuelle"

    # 2. Calculs statistiques
    moyenne_prix, a, b, equation = calculer_moindres_carres(donnees)

    # 3. Envoi au template
    return render_template(
        'analyser_donnees.html',
        data=donnees,
        titre=titre,
        moyenne=moyenne_prix,
        equation=equation
    )
# --- ROUTE POUR AFFICHER LE FORMULAIRE (Remplir le tableau) ---
@app.route('/saisie-manuelle')
def saisie_manuelle():
    return render_template('saisie_manuelle.html')

@app.route('/choix-analyse')
def choix_analyse():
    if not session.get('authenticated'):
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    # On récupère toutes les collectes, de la plus récente à la plus ancienne
    donnees = conn.execute('SELECT * FROM collectes ORDER BY id DESC').fetchall()
    conn.close()
    
    return render_template('choix_analyse.html', collectes=donnees)

if __name__ == '__main__':
    # debug=True permet de voir les erreurs en direct et de relancer le serveur à chaque modif
    app.run(debug=True)
