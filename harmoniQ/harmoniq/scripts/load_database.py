import argparse
from pathlib import Path
from typing import Tuple
import getpass
import zipfile

from harmoniq import DB_PATH

try:
    from office365.runtime.auth.user_credential import UserCredential
    from office365.sharepoint.client_context import ClientContext
    from office365.sharepoint.folders.folder import Folder
except ImportError as e:
    print(f"Le module office365 n'est pas installé: {e}")
    print("Installez harmoniq avec l'option dev avec `pip install -e ./harmoniQ[dev]`")
    exit(1)

LOCAL_DB_DIR = Path(__file__).resolve().parents[1] / "db"
LOCAL_DB_NAME = "demande.db.zip"
LOCAL_UNZIPPED_DB_NAME = "demande.db"

SHAREPOINT_SITE_URL = "https://polymtlca0.sharepoint.com/sites/2024-MEC8370-08-09"
SHAREPOINT_FOLDER = "Documents"
SHAREPOINT_SUBFOLDER = "Groupe 08 - Produit et base de données"
SHAREPOINT_FILE = "demande.db.zip"


def get_credentials() -> Tuple[str, str]:
    email = input("Courriel (@polymtlus.ca): ")
    password = getpass.getpass("Mot de passe: ")

    if not email.endswith("@polymtlus.ca"):
        r = input(f"Est-ce que {email}@polymtlus.ca est votre courriel? (o/n)")
        if r.lower() != "o":
            print("Erreur: Le courriel doit se terminer par @polymtlus.ca")
            exit(1)

        email = email + "@polymtlus.ca"

    return email, password


def get_sharepoint_user() -> ClientContext:
    print("Connexion à SharePoint...")
    email, password = get_credentials()
    creds = UserCredential(email, password)
    ctx = ClientContext(SHAREPOINT_SITE_URL).with_credentials(creds)
    me = ctx.web.current_user.get().execute_query()
    print(f"Connecté en tant que {me.login_name}")
    return ctx


def get_sharepoint_folder(ctx: ClientContext) -> Folder:
    print("Récupération du dossier...")
    list_obj = ctx.web.lists.get_by_title(SHAREPOINT_FOLDER)
    folder = list_obj.root_folder.folders.get_by_url(SHAREPOINT_SUBFOLDER)
    return folder


def upload_db():
    print("Compression de la base de données...")
    with zipfile.ZipFile(DB_PATH, "w") as zip_ref:
        zip_ref.write(LOCAL_DB_DIR / LOCAL_UNZIPPED_DB_NAME, LOCAL_DB_NAME)
    
    print("Compression terminée, téléversement de la base de données... (cela peut prendre du temps)")
    ctx = get_sharepoint_user()
    folder = get_sharepoint_folder(ctx)
    with open(DB_PATH, "rb") as local_file:
        file = folder.upload_file(LOCAL_DB_NAME, local_file).execute_query()

    print("Téléversement terminé")


def download_db():
    print("Téléchargement de la base de données... (cela peut prendre du temps)")
    ctx = get_sharepoint_user()
    folder = get_sharepoint_folder(ctx)
    items = folder.files.get().execute_query()
    if SHAREPOINT_FILE not in [item.properties["Name"] for item in items]:
        print(
            f"Erreur: Fichier {SHAREPOINT_SUBFOLDER}/{SHAREPOINT_FILE} non trouvé sur sharepoint"
        )
        exit(1)

    print("Téléchargement du fichier...")
    file = folder.files.get_by_url(SHAREPOINT_FILE)
    file_object = file.open_binary_stream().execute_query()
    file_content = file_object.value
    with open(DB_PATH, "wb") as local_file:
        local_file.write(file_content)

    print("Téléchargement terminé, décompression de la base de données...")
    with zipfile.ZipFile(DB_PATH, "r") as zip_ref:
        zip_ref.extractall(LOCAL_DB_DIR)
    print("Décompression terminée, base de données prête à l'emploi")


def main():
    parser = argparse.ArgumentParser(
        description="Télécharge ou téléverse la base de données",
    )
    parser.add_argument(
        "-u", "--upload", action="store_true", help="Téléverse la base de données"
    )
    parser.add_argument(
        "-d", "--download", action="store_true", help="Télécharge la base de données"
    )

    args = parser.parse_args()

    if args.upload and args.download:
        print("Erreur: Les options -u et -d sont mutuellement exclusives")
        exit(1)
    elif args.upload:
        upload_db()
    elif args.download:
        download_db()
    else:
        print("Utilisez l'option -h pour afficher l'aide")
        exit(1)


if __name__ == "__main__":
    main()
