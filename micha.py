import flet as ft
import psycopg2
import os
import datetime

# LINK DO NEON - WKLEJ SWÓJ
DB_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_jGvTXNQ0ep2y@ep-small-dream-als2k8po-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

def get_db():
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS produkty (nazwa TEXT PRIMARY KEY, kcal REAL, b REAL, t REAL, w REAL, jednostka TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS dziennik (id SERIAL PRIMARY KEY, user_name TEXT, data TEXT, posilek TEXT, nazwa TEXT, ilosc REAL, jednostka TEXT, kcal REAL, b REAL, t REAL, w REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS profile (user_name TEXT PRIMARY KEY, cel_kcal REAL)")
    cur.execute("INSERT INTO profile (user_name, cel_kcal) VALUES ('Filip', 2500), ('Nikola', 2000) ON CONFLICT DO NOTHING")
    conn.commit(); conn.close()

def main(page: ft.Page):
    page.title = "Nasza Micha"
    page.theme_mode = ft.ThemeMode.DARK
    init_db()
    
    # Dane trzymane tylko w pamięci uruchomionej apki
    state = {"user": None, "date": datetime.date.today()}

    # --- UI ---
    status_label = ft.Text("Zaloguj się", size=25, weight="bold")
    log_view = ft.ListView(expand=True, spacing=5)
    date_label = ft.Text(state["date"].strftime("%Y-%m-%d"), size=18)
    
    prod_dd = ft.Dropdown(label="Produkt", expand=True)
    amt_in = ft.TextField(label="Ilość", width=100, keyboard_type="number")

    def update_screen():
        if not state["user"]: return
        u = state["user"]
        d = state["date"].strftime("%Y-%m-%d")
        date_label.value = d
        
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT cel_kcal FROM profile WHERE user_name=%s", (u,))
        target = (cur.fetchone() or [2000])[0]
        cur.execute("SELECT SUM(kcal) FROM dziennik WHERE user_name=%s AND data=%s", (u, d))
        suma = cur.fetchone()[0] or 0
        
        status_label.value = f"{u}: {int(suma)} / {int(target)} kcal"
        
        log_view.controls.clear()
        cur.execute("SELECT id, nazwa, kcal FROM dziennik WHERE user_name=%s AND data=%s ORDER BY id DESC", (u, d))
        for r in cur.fetchall():
            log_view.controls.append(ft.ListTile(title=ft.Text(r[1]), subtitle=ft.Text(f"{int(r[2])} kcal"), trailing=ft.IconButton(ft.Icons.DELETE, data=r[0], on_click=delete_item)))
        conn.close(); page.update()

    def delete_item(e):
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM dziennik WHERE id=%s", (e.control.data,))
        conn.commit(); conn.close(); update_screen()

    def add_item(e):
        if not prod_dd.value or not amt_in.value: return
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT kcal, jednostka FROM produkty WHERE nazwa=%s", (prod_dd.value,))
        p = cur.fetchone()
        v = float(amt_in.value.replace(",", "."))
        m = v / 100 if p[1] == '100g' else v
        cur.execute("INSERT INTO dziennik (user_name, data, nazwa, ilosc, kcal) VALUES (%s,%s,%s,%s,%s)",
                    (state["user"], state["date"].strftime("%Y-%m-%d"), prod_dd.value, v, p[0]*m))
        conn.commit(); conn.close(); amt_in.value = ""; update_screen()

    def login(e):
        if (u_sel.value == "Filip" and p_in.value == "1111") or (u_sel.value == "Nikola" and p_in.value == "2222"):
            state["user"] = u_sel.value
            v_login.visible = False
            v_main.visible = True
            update_screen()
        else:
            page.open(ft.SnackBar(ft.Text("Błąd!")))
        page.update()

    # --- WIDOKI ---
    u_sel = ft.Dropdown(label="Kto?", options=[ft.dropdown.Option("Filip"), ft.dropdown.Option("Nikola")])
    p_in = ft.TextField(label="PIN", password=True)
    v_login = ft.Column([ft.Text("LOGOWANIE", size=30), u_sel, p_in, ft.ElevatedButton("WEJDŹ", on_click=login)])

    v_main = ft.Column([
        ft.Row([ft.IconButton(ft.Icons.REMOVE, on_click=lambda _: change_d(-1)), date_label, ft.IconButton(ft.Icons.ADD, on_click=lambda _: change_d(1))], alignment="center"),
        status_label,
        ft.Row([amt_in, prod_dd]),
        ft.ElevatedButton("DODAJ", on_click=add_item, bgcolor="blue", color="white"),
        ft.Divider(),
        log_view
    ], visible=False, expand=True)

    def change_d(delta):
        state["date"] += datetime.timedelta(days=delta); update_screen()

    page.add(v_login, v_main)

    # Produkty
    c = get_db(); cur = c.cursor(); cur.execute("SELECT nazwa FROM produkty ORDER BY nazwa ASC")
    prod_dd.options = [ft.dropdown.Option(p[0]) for p in cur.fetchall()]; c.close()

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("PORT", 8080)), host="0.0.0.0")
