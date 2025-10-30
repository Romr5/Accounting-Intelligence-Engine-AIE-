import flet as ft
from aie_app import AIEApp 

def main(page: ft.Page):
    """Entry point for the Flet application."""
    app = AIEApp(page)
    page.add(app)
    app.update_view()

if __name__ == "__main__":
    ft.app(target=main)