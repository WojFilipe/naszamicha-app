import flet as ft
import psycopg2
import os
import datetime

# TWOJA BAZA NEON
DB_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_jGvTXNQ0ep2y@ep-small-dream-als2k8po-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

def get_db():
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS produkty (nazwa TEXT PRIMARY KEY, kcal REAL, b REAL, t REAL, w REAL, jednostka TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS dziennik (id SERIAL PRIMARY KEY, user_name TEXT, data TEXT, posilek TEXT, nazwa TEXT, ilosc REAL, jednostka TEXT, kcal REAL, b REAL, t REAL, w REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS profile (user_name TEXT PRIMARY KEY, cel_kcal REAL)")
    cur.execute("INSERT INTO profile (user_name, cel_kcal) VALUES ('Filip', 2500), ('Nikola', 2000) ON CONFLICT DO NOTHING")
    conn.commit()
    conn.close()

def main(page: ft.Page):
    page.title = "Nasza Micha 1.0"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    init_db()
    
    app_date = datetime.date.today()

    # --- UI COMPONENTS ---
    status_text = ft.Text("0 / 0 kcal", size=28, weight="bold")
    prog_bar = ft.ProgressBar(value=0, height=15, color="green")
    log_list = ft.ListView(expand=True, spacing=10)
    date_text = ft.Text(app_date.strftime("%Y-%m-%d"), size=18, weight="bold")
    
    prod_dd = ft.Dropdown(label="Produkt", expand=True)
    meal_dd = ft.Dropdown(label="Posiłek", options=[ft.dropdown.Option(m) for m in ["Śniadanie", "Obiad", "Kolacja", "Inne"]], value="Obiad", expand=True)
    amt_input = ft.TextField(label="Ilość", width=100, keyboard_type="number")

    # --- LOGIC ---
    def refresh_ui():
        user = page.session.get("current_user")
        if not user: return
        
        d_str = app_date.strftime("%Y-%m-%d")
        date_text.value = d_str
        
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT cel_kcal FROM profile WHERE user_name=%s", (user,))
        target = (cur.fetchone() or [2000])[0]
        
        cur.execute("SELECT SUM(kcal) FROM dziennik WHERE user_name=%s AND data=%s", (user, d_str))
        suma = cur.fetchone()[0] or 0
        
        status_text.value = f"{user}: {int(suma)} / {int(target)} kcal"
        prog_bar.value = min(suma / target, 1.0) if target > 0 else 0
        
        log_list.controls.clear()
        cur.execute("SELECT id, nazwa, ilosc, kcal FROM dziennik WHERE user_name=%s AND data=%s ORDER BY id DESC", (user, d_str))
        for r in cur.fetchall():
            log_list.controls.append(ft.ListTile(title=ft.Text(r[1]), subtitle=ft.Text(f"{int(r[2])} - {int(r[3])} kcal"), trailing=ft.IconButton(ft.Icons.DELETE, data=r[0], on_click=delete_entry)))
        
        conn.close()
        page.update()

    def delete_entry(e):
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM dziennik WHERE id=%s", (e.control.data,))
        conn.commit(); conn.close(); refresh_ui()

    def add_meal(e):
        user = page.session.get("current_user")
        if not prod_dd.value or not amt_input.value: return
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT kcal, jednostka FROM produkty WHERE nazwa=%s", (prod_dd.value,))
        p = cur.fetchone()
        val = float(amt_input.value.replace(",", "."))
        mult = val / 100 if p[1] == '100g' else val
        cur.execute("INSERT INTO dziennik (user_name, data, posilek, nazwa, ilosc, jednostka, kcal) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (user, app_date.strftime("%Y-%m-%d"), meal_dd.value, prod_dd.value, val, p[1], p[0]*mult))
        conn.commit(); conn.close(); amt_input.value = ""; refresh_ui()

    # --- VIEWS ---
    def login_action(e):
        if (login_user.value == "Filip" and pin.value == "1111") or (login_user.value == "Nikola" and pin.value == "2222"):
            page.session.set("current_user", login_user.value)
            login_view.visible = False
            main_view.visible = True
            refresh_ui()
        else:
            page.snack_bar = ft.SnackBar(ft.Text("Błędny PIN")); page.snack_bar.open = True
        page.update()

    login_user = ft.Dropdown(label="Użytkownik", options=[ft.dropdown.Option("Filip"), ft.dropdown.Option("Nikola")])
    pin = ft.TextField(label="PIN", password=True, keyboard_type="number")
    login_view = ft.Column([ft.Text("LOGOWANIE", size=30), login_user, pin, ft.ElevatedButton("ZALOGUJ", on_click=login_action)], horizontal_alignment="center")

    main_view = ft.Column([
        ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: change_day(-1)), date_text, ft.IconButton(ft.Icons.ARROW_FORWARD, on_click=lambda _: change_day(1))], alignment="center"),
        ft.Container(content=ft.Column([status_text, prog_bar], horizontal_alignment="center"), padding=10),
        ft.Row([meal_dd, amt_input]),
        prod_dd,
        ft.ElevatedButton("DODAJ", on_click=add_meal, expand=True, bgcolor="blue", color="white"),
        ft.Divider(),
        log_list,
        ft.TextButton("WYLOGUJ", on_click=lambda _: page.window_reload())
    ], visible=False, expand=True)

    def change_day(d):
        nonlocal app_date; app_date += datetime.timedelta(days=d); refresh_ui()

    page.add(login_view, main_view)

    # Load Products
    c = get_db(); cur = c.cursor(); cur.execute("SELECT nazwa FROM produkty ORDER BY nazwa ASC")
    prod_dd.options = [ft.dropdown.Option(p[0]) for p in cur.fetchall()]; c.close()

def change_day(d): pass # Placeholder

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("PORT", 8080)), host="0.0.0.0")
