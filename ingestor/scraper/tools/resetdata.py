import typer
import os
import shutil

app = typer.Typer(help="Outils internes du projet")
raise_error = "Error while recreating file"

@app.command()
def reset_data():
    def empty_dir(dir):
        if os.path.isdir(dir):
            for f in os.listdir(dir):
                os.remove(os.path.join(dir, f))
            print(f"Le dossier {dir} a été reset")

        else:
            print(f"error : le dossier : {dir} n'existe pas, n'est pas un dossier où est déjà vide")

    empty_dir("../../data/raw")
    empty_dir("../../data/clean")
    empty_dir("../../chk")

if __name__ == "__main__":
    app()