import argparse
import sys
import time
import signal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
from termcolor import colored
from utilities import (
    close_all_firefox_instances,
    get_firefox_profile_location,
    get_headless,
    save_to_json,
    scroll_to_bottom,
    wait,
)

# Constantes pour la recherche LinkedIn
REQUETE_PAR_DEFAUT = "développeur"
NOMBRE_RESULTATS_PAR_DEFAUT = 250
EMPLACEMENT_PROFILE_PAR_DEFAUT = "101640738"  # Utilisé comme geoUrn
HEADLESS_PAR_DEFAUT = False
REQUETE_DE_RECHERCHE = REQUETE_PAR_DEFAUT
NOMBRE_RESULTATS = NOMBRE_RESULTATS_PAR_DEFAUT
EMPLACEMENT_PROFILE = EMPLACEMENT_PROFILE_PAR_DEFAUT
OPTION_HEADLESS = HEADLESS_PAR_DEFAUT
PAGE_ACTUELLE = 1

CLASSE_LISTE_RESULTATS = "reusable-search__entity-result-list"
CLASSE_LISTE_PAGINATION = "artdeco-pagination__pages"
CLASSE_NOM_PERSONNE = "entity-result__title-text"
CLASSE_SOUS_TITRE_PERSONNE = "entity-result__primary-subtitle"
CLASSE_SOUS_TITRE_SECONDAIRE_PERSONNE = "entity-result__secondary-subtitle"
CLASSE_RESUME_PERSONNE = "entity-result__summary"
CLASSE_BOUTON_ACTION_PERSONNE = "entity-result__actions"
CONTENEUR_ACTION = "HAkjWyOMTmfTymjcuEAoRxNAMIyhiCZgNcRc"
BARRE_ACTION_MODAL = "artdeco-modal__actionbar"
CONTENU_BOUTON_CONNEXION = "Se connecter"
CONTENU_BOUTON_ADD_MESSAGE = "Ajouter une note"
CONTENU_BOUTON_ENVOYER = "Envoyer"

PERSONNES = []
MAX_PAGES = 10
URL_BASE_LINKEDIN = "https://www.linkedin.com"


def gestion_interruption(sig, frame):
    """
    Gère l'interruption du script avec Ctrl + C.
    """
    print(
        colored("\n[!] Script interrompu par l'utilisateur. Sortie en cours...", "red")
    )
    sys.exit(0)


signal.signal(signal.SIGINT, gestion_interruption)


def analyser_arguments():
    parser = argparse.ArgumentParser(description="Script d'automatisation LinkedIn")
    parser.add_argument(
        "--query", type=str, default=REQUETE_PAR_DEFAUT, help="Requête de recherche"
    )
    parser.add_argument(
        "--n",
        type=int,
        default=NOMBRE_RESULTATS_PAR_DEFAUT,
        help="Nombre de résultats de recherche",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=EMPLACEMENT_PROFILE_PAR_DEFAUT,
        help="Emplacement du profil Firefox",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=HEADLESS_PAR_DEFAUT,
        help="Exécuter en mode headless",
    )
    args = parser.parse_args()
    return args


def initialiser_navigateur(emplacement_profil_firefox, headless):
    """
    Initialise le navigateur Firefox avec le profil et les options spécifiés.
    """
    options = Options()
    if headless:
        options.add_argument("--headless")
    if emplacement_profil_firefox:
        options.set_preference("profile", emplacement_profil_firefox)

    # Empêche le rafraîchissement automatique de la page
    options.set_preference("dom.disable_before_unload", True)
    options.set_preference("browser.sessionstore.resume_from_crash", False)

    try:
        service = Service(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)
        return driver
    except Exception as e:
        print(
            colored(
                f"[!] Erreur lors de l'initialisation du navigateur : {str(e)}", "red"
            )
        )
        sys.exit(1)


def est_connecte(driver):
    """
    Vérifie si l'utilisateur est connecté à LinkedIn.
    """
    try:
        driver.get(URL_BASE_LINKEDIN)
        time.sleep(5)
        bouton_connexion = driver.find_element(By.XPATH, '//a[text()="Se connecter"]')
        return bouton_connexion is None
    except Exception:
        return False


def attendre_connexion(driver):
    """
    Attend que l'utilisateur se connecte à LinkedIn.
    """
    print(colored("[*] Veuillez vous connecter à LinkedIn...", "yellow"))
    WebDriverWait(driver, 300).until(
        EC.presence_of_element_located((By.XPATH, '//a[text()="Se connecter"]'))
    )
    input(
        colored(
            "[*] Vous êtes connecté. Appuyez sur Entrée pour continuer...", "yellow"
        )
    )


def verifier_refresh_page(driver, url_precedente):
    """
    Vérifie si la page a été rafraîchie.
    """
    url_actuelle = driver.current_url
    return url_actuelle != url_precedente


def recuperer_resultats(driver):
    """
    Récupère les résultats de la recherche LinkedIn.
    """
    global PERSONNES
    global PAGE_ACTUELLE
    global NOMBRE_RESULTATS

    print(colored("[*] Accès à la page de recherche...", "yellow"))
    driver.get(
        f"{URL_BASE_LINKEDIN}/search/results/people/?geoUrn={EMPLACEMENT_PROFILE}&keywords={REQUETE_DE_RECHERCHE}&origin=SWITCH_SEARCH_VERTICAL&sid=p%2CR"
    )

    driver.maximize_window()
    wait(4)

    url_precedente = driver.current_url
    scroll_to_bottom(driver)
    wait(2)

    try:
        liste_pagination = driver.find_element(By.CLASS_NAME, CLASSE_LISTE_PAGINATION)
        dernier_numero_page = int(
            liste_pagination.find_elements(By.TAG_NAME, "li")[-1]
            .find_element(By.TAG_NAME, "span")
            .text
        )
    except Exception as e:
        print(
            colored(
                f"[!] Erreur lors de la récupération de la pagination : {str(e)}", "red"
            )
        )
        dernier_numero_page = 1

    global MAX_PAGES
    MAX_PAGES = dernier_numero_page

    for _ in range(MAX_PAGES):
        if len(PERSONNES) >= NOMBRE_RESULTATS:
            break

        print(colored(f"[+] Navigation vers la page {PAGE_ACTUELLE}...", "yellow"))

        driver.get(
            f"{URL_BASE_LINKEDIN}/search/results/people/?geoUrn={EMPLACEMENT_PROFILE}&keywords={REQUETE_DE_RECHERCHE}&origin=SWITCH_SEARCH_VERTICAL&sid=p%2CR&page={PAGE_ACTUELLE}"
        )

        if verifier_refresh_page(driver, url_precedente):
            print(colored("[!] Page rafraîchie, nouvelle tentative...", "yellow"))
            url_precedente = driver.current_url
            wait(4)

        try:
            liste_resultats = driver.find_element(By.CLASS_NAME, CLASSE_LISTE_RESULTATS)
            resultats = liste_resultats.find_elements(By.TAG_NAME, "li")
        except Exception as e:
            print(
                colored(
                    f"[!] Erreur lors de la récupération des résultats : {str(e)}",
                    "red",
                )
            )
            resultats = []

        for resultat in resultats:
            try:
                pfp = resultat.find_element(By.TAG_NAME, "img").get_attribute("src")
            except:
                pfp = ""

            try:
                urls_profil = resultat.find_elements(By.TAG_NAME, "a")
                for url in urls_profil:
                    if "/in/" in url.get_attribute("href"):
                        url_profil = url.get_attribute("href")
                        break
                else:
                    url_profil = ""
            except:
                url_profil = ""

            try:
                nom = (
                    resultat.find_element(By.CLASS_NAME, CLASSE_NOM_PERSONNE)
                    .find_elements(By.TAG_NAME, "span")[1]
                    .text
                )
            except:
                continue

            try:
                sous_titre = resultat.find_element(
                    By.CLASS_NAME, CLASSE_SOUS_TITRE_PERSONNE
                ).text
            except:
                sous_titre = ""

            try:
                sous_titre_secondaire = resultat.find_element(
                    By.CLASS_NAME, CLASSE_SOUS_TITRE_SECONDAIRE_PERSONNE
                ).text
            except:
                sous_titre_secondaire = ""

            try:
                resume = resultat.find_element(
                    By.CLASS_NAME, CLASSE_RESUME_PERSONNE
                ).text
            except:
                resume = ""

            PERSONNES.append(
                {
                    "pfp": pfp,
                    "nom": nom,
                    "url_profil": url_profil,
                    "sous_titre": sous_titre,
                    "sous_titre_secondaire": sous_titre_secondaire,
                    "resume": resume,
                }
            )

        PAGE_ACTUELLE += 1
        wait(2)

    print(colored(f"[+] {len(PERSONNES)} profils récupérés.", "green"))


def sauvegarder_personnes():
    """
    Sauvegarde les personnes récupérées dans un fichier JSON.
    """
    save_to_json(PERSONNES)
    print(colored(f"[+] Profils sauvegardés dans 'personnes.json'.", "green"))


def main():
    args = analyser_arguments()

    global REQUETE_DE_RECHERCHE
    global NOMBRE_RESULTATS
    global EMPLACEMENT_PROFILE
    global OPTION_HEADLESS

    REQUETE_DE_RECHERCHE = args.query
    NOMBRE_RESULTATS = args.n
    EMPLACEMENT_PROFILE = args.profile
    OPTION_HEADLESS = args.headless

    print("[*] Démarrage du script...")

    close_all_firefox_instances()

    driver = None
    try:
        driver = initialiser_navigateur(EMPLACEMENT_PROFILE, OPTION_HEADLESS)
        if not est_connecte(driver):
            attendre_connexion(driver)

        recuperer_resultats(driver)
        sauvegarder_personnes()

    except Exception as e:
        print(colored(f"[!] Une erreur s'est produite : {str(e)}", "red"))

    finally:
        if driver:
            driver.quit()
        print(colored("[*] Arrêt du script.", "yellow"))


if __name__ == "__main__":
    main()
