import flet as ft
import psycopg2
import os
import datetime

# TUTAJ WKLEJ SWÓJ LINK Z NEON.TECH
DB_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_jGvTXNQ0ep2y@ep-small-dream-als2k8po-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

def get_db():
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS produkty (nazwa TEXT PRIMARY KEY, kcal REAL, b REAL, t REAL, w REAL, jednostka TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS dziennik (id SERIAL PRIMARY KEY, user_name TEXT, data TEXT, posilek TEXT, nazwa TEXT, ilosc REAL, jednostka TEXT, kcal REAL, b REAL, t REAL, w REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS profile (user_name TEXT PRIMARY KEY, cel_kcal REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS waga_log (user_name TEXT, data TEXT, waga REAL, PRIMARY KEY(user_name, data))")
    cur.execute("INSERT INTO profile (user_name, cel_kcal) VALUES ('Filip', 2500), ('Nikola', 2000) ON CONFLICT DO NOTHING")
    conn.commit()
    conn.close()

def main(page: ft.Page):
    page.title = "Nasza Micha"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    init_db()
    
    app_date = datetime.date.today()

    # --- ELEMENTY INTERFEJSU ---
    naglowek_imie = ft.Text("", size=22, weight="bold", color="blue400")
    status_kcal = ft.Text("0 / 0 kcal", size=26, weight="bold")
    prog_bar = ft.ProgressBar(value=0, height=12, color="green", bgcolor="grey800")
    b_txt = ft.Text("B: 0g", color="red")
    t_txt = ft.Text("T: 0g", color="orange")
    w_txt = ft.Text("W: 0g", color="blue")
    log_list = ft.ListView(expand=True, spacing=5)
    date_display = ft.Text("", size=16, weight="bold")
    
    # Formularze
    meal_select = ft.Dropdown(
        options=[ft.dropdown.Option(m) for m in ["Śniadanie", "II Śniadanie", "Obiad", "Przekąska", "Kolacja"]],
        value="Obiad", expand=True
    )
    dd_produkt = ft.Dropdown(label="Wybierz produkt", expand=True)
    input_ilosc = ft.TextField(label="Ilość", width=100, keyboard_type=ft.KeyboardType.NUMBER)

    # --- FUNKCJE LOGIKI ---
    def refresh_all(e=None):
        u = page.client_storage.get("user")
        if not u: return
        
        data_str = app_date.strftime("%Y-%m-%d")
        date_display.value = data_str
        naglowek_imie.value = f"Dziennik: {u}"
        
        conn = get_db()
        cur = conn.cursor()
        
        # Pobieranie celu
        cur.execute("SELECT cel_kcal FROM profile WHERE user_name=%s", (u,))
        res = cur.fetchone()
        target = res[0] if res else 2000
        
        # Pobieranie sumy
        cur.execute("SELECT SUM(kcal), SUM(b), SUM(t), SUM(w) FROM dziennik WHERE user_name=%s AND data=%s", (u, data_str))
        s = cur.fetchone()
        k, b, t, w = (s[0] or 0, s[1] or 0, s[2] or 0, s[3] or 0)
        
        status_kcal.value = f"{int(k)} / {int(target)} kcal"
        prog_bar.value = min(k / target, 1.0) if target > 0 else 0
        b_txt.value = f"B: {int(b)}g"; t_txt.value = f"T: {int(t)}g"; w_txt.value = f"W: {int(w)}g"
        
        # Lista posiłków
        log_list.controls.clear()
        cur.execute("SELECT id, nazwa, ilosc, jednostka, kcal, posilek FROM dziennik WHERE user_name=%s AND data=%s ORDER BY id", (u, data_str))
        rows = cur.fetchall()
        for row in rows:
            log_list.controls.append(
                ft.ListTile(
                    title=ft.Text(f"{row[1]} ({row[5]})"),
                    subtitle=ft.Text(f"{int(row[2])}{row[3]} - {int(row[4])} kcal"),
                    trailing=ft.IconButton(ft.Icons.DELETE, icon_color="red", data=row[0], on_click=usun_posilek)
                )
            )
        conn.close()
        page.update()

    def usun_posilek(e):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM dziennik WHERE id=%s", (e.control.data,))
        conn.commit()
        conn.close()
        refresh_all()

    def dodaj_posilek_click(e):
        u = page.client_storage.get("user")
        if not dd_produkt.value or not input_ilosc.value: return
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT kcal, b, t, w, jednostka FROM produkty WHERE nazwa=%s", (dd_produkt.value,))
        p = cur.fetchone()
        
        ilosc = float(input_ilosc.value.replace(",", "."))
        mnoznik = ilosc / 100 if p[4] == '100g' else ilosc
        
        cur.execute("INSERT INTO dziennik (user_name, data, posilek, nazwa, ilosc, jednostka, kcal, b, t, w) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (u, app_date.strftime("%Y-%m-%d"), meal_select.value, dd_produkt.value, ilosc, p[4], p[0]*mnoznik, p[1]*mnoznik, p[2]*mnoznik, p[3]*mnoznik))
        conn.commit()
        conn.close()
        input_ilosc.value = ""
        refresh_all()
        page.open(ft.SnackBar(ft.Text("Dodano!")))

    # --- EKRANY ---
    def zaloguj_click(e):
        if login_imie.value and (
            (login_imie.value == "Filip" and login_pin.value == "1111") or 
            (login_imie.value == "Nikola" and login_pin.value == "2222")
        ):
            page.client_storage.set("user", login_imie.value)
            view_login.visible = False
            view_app.visible = True
            page.navigation_bar.visible = True
            refresh_all()
        else:
            page.open(ft.SnackBar(ft.Text("Błędny PIN!", color="red")))
        page.update()

    def wyloguj_click(e):
        page.client_storage.remove("user")
        view_app.visible = False
        page.navigation_bar.visible = False
        view_login.visible = True
        page.update()

    # Ekran Logowania
    login_imie = ft.Dropdown(label="Kto się loguje?", options=[ft.dropdown.Option("Filip"), ft.dropdown.Option("Nikola")], width=300)
    login_pin = ft.TextField(label="PIN", password=True, width=300, keyboard_type=ft.KeyboardType.NUMBER)
    view_login = ft.Column([
        ft.Text("NASZA MICHA", size=32, weight="bold", color="blue400"),
        login_imie, login_pin,
        ft.ElevatedButton("ZALOGUJ", on_click=zaloguj_click, width=300, height=50)
    ], horizontal_alignment="center", visible=True)

    # Ekran Główny
    def chg_day(delta):
        nonlocal app_date
        app_date += datetime.timedelta(days=delta)
        refresh_all()

    view_app = ft.Column([
        naglowek_imie,
        ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: chg_day(-1)),
            date_display,
            ft.IconButton(ft.Icons.ARROW_FORWARD, on_click=lambda _: chg_day(1))
        ], alignment="center"),
        ft.Container(content=ft.Column([status_kcal, prog_bar, ft.Row([b_txt, t_txt, w_txt], alignment="center")], horizontal_alignment="center")),
        ft.Row([meal_select, input_ilosc]),
        dd_produkt,
        ft.ElevatedButton("ZJEDZONE!", on_click=dodaj_posilek_click, expand=True, height=50, bgcolor="blue", color="white"),
        ft.Divider(),
        log_list,
        ft.ElevatedButton("WYLOGUJ", on_click=wyloguj_click, color="red")
    ], visible=False, expand=True)

    # --- START ---
    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.BOOK, label="Dziennik"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Ustawienia")
        ],
        visible=False
    )
    
    page.add(view_login, view_app)
    
    # Załaduj produkty do listy
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT nazwa FROM produkty ORDER BY nazwa ASC")
    dd_produkt.options = [ft.dropdown.Option(p[0]) for p in cur.fetchall()]
    conn.close()

    # Autologowanie
    if page.client_storage.get("user"):
        view_login.visible = False
        view_app.visible = True
        page.navigation_bar.visible = True
        refresh_all()

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("PORT", 8080)), host="0.0.0.0")
