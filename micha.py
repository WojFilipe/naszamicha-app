import flet as ft
import psycopg2
import os
import datetime

# LINK DO BAZY NEON
DB_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_jGvTXNQ0ep2y@ep-small-dream-als2k8po-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

def get_db():
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS produkty (nazwa TEXT PRIMARY KEY, kcal REAL, b REAL, t REAL, w REAL, jednostka TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS dziennik (id SERIAL PRIMARY KEY, user_name TEXT, data TEXT, posilek TEXT, nazwa TEXT, ilosc REAL, jednostka TEXT, kcal REAL, b REAL, t REAL, w REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS profile (user_name TEXT PRIMARY KEY, cel_kcal REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS waga_log (user_name TEXT, data TEXT, waga REAL, PRIMARY KEY(user_name, data))")
    cur.execute("INSERT INTO profile (user_name, cel_kcal) VALUES ('Filip', 2500), ('Nikola', 2000) ON CONFLICT DO NOTHING")
    conn.commit(); conn.close()

def main(page: ft.Page):
    page.title = "Nasza Micha v1.0"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 15
    init_db()
    
    # State aplikacji
    st = {"u": None, "d": datetime.date.today()}

    # --- ELEMENTY DZIENNIKA ---
    kcal_txt = ft.Text("0 / 0 kcal", size=26, weight="bold")
    pb = ft.ProgressBar(value=0, height=12, color="green")
    macro_row = ft.Row([ft.Text("B: 0", color="red"), ft.Text("T: 0", color="orange"), ft.Text("W: 0", color="blue")], alignment="center")
    log_list = ft.ListView(expand=True, spacing=5)
    date_txt = ft.Text("", size=16, weight="bold")
    
    meal_dd = ft.Dropdown(label="Posiłek", options=[ft.dropdown.Option(m) for m in ["Śniadanie", "II Śniadanie", "Obiad", "Przekąska", "Kolacja"]], value="Obiad", expand=True)
    prod_dd = ft.Dropdown(label="Produkt", expand=True)
    amt_in = ft.TextField(label="G/Szt", width=80, keyboard_type="number")

    # --- ELEMENTY BAZY ---
    n_nazwa = ft.TextField(label="Nazwa", expand=True)
    n_typ = ft.Dropdown(options=[ft.dropdown.Option("100g"), ft.dropdown.Option("szt")], value="100g", width=100)
    n_k = ft.TextField(label="Kcal", expand=1); n_b = ft.TextField(label="B", expand=1); n_t = ft.TextField(label="T", expand=1); n_w = ft.TextField(label="W", expand=1)

    # --- ELEMENTY PROFILU ---
    p_cel = ft.TextField(label="Nowy cel kcal", expand=True)
    p_waga = ft.TextField(label="Dzisiejsza waga", expand=True)
    waga_list = ft.ListView(expand=True, spacing=5)

    def refresh_data():
        if not st["u"]: return
        d_str = st["d"].strftime("%Y-%m-%d")
        date_txt.value = d_str
        conn = get_db(); cur = conn.cursor()
        
        # 1. Kcal i Macro
        cur.execute("SELECT cel_kcal FROM profile WHERE user_name=%s", (st["u"],))
        target = (cur.fetchone() or [2000])[0]
        cur.execute("SELECT SUM(kcal), SUM(b), SUM(t), SUM(w) FROM dziennik WHERE user_name=%s AND data=%s", (st["u"], d_str))
        res = cur.fetchone()
        k, b, t, w = (res[0] or 0, res[1] or 0, res[2] or 0, res[3] or 0)
        
        kcal_txt.value = f"{int(k)} / {int(target)} kcal"
        pb.value = min(k / target, 1.0) if target > 0 else 0
        macro_row.controls[0].value = f"B: {int(b)}g"
        macro_row.controls[1].value = f"T: {int(t)}g"
        macro_row.controls[2].value = f"W: {int(w)}g"
        
        # 2. Lista posiłków
        log_list.controls.clear()
        cur.execute("SELECT id, nazwa, ilosc, kcal, posilek FROM dziennik WHERE user_name=%s AND data=%s ORDER BY id DESC", (st["u"], d_str))
        for r in cur.fetchall():
            log_list.controls.append(ft.ListTile(title=ft.Text(f"{r[1]} ({r[4]})"), subtitle=ft.Text(f"{int(r[2])}j. - {int(r[3])} kcal"), trailing=ft.IconButton(ft.Icons.DELETE, data=r[0], on_click=delete_item)))
        
        # 3. Waga
        waga_list.controls.clear()
        cur.execute("SELECT data, waga FROM waga_log WHERE user_name=%s ORDER BY data DESC", (st["u"],))
        for rw in cur.fetchall(): waga_list.controls.append(ft.ListTile(title=ft.Text(f"{rw[1]} kg"), subtitle=ft.Text(rw[0])))
        
        conn.close(); page.update()

    def delete_item(e):
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM dziennik WHERE id=%s", (e.control.data,))
        conn.commit(); conn.close(); refresh_data()

    def add_meal(e):
        if not prod_dd.value or not amt_in.value: return
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT kcal, b, t, w, jednostka FROM produkty WHERE nazwa=%s", (prod_dd.value,))
        p = cur.fetchone()
        v = float(amt_in.value.replace(",", ".")); m = v / 100 if p[4] == '100g' else v
        cur.execute("INSERT INTO dziennik (user_name, data, posilek, nazwa, ilosc, jednostka, kcal, b, t, w) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (st["u"], st["d"].strftime("%Y-%m-%d"), meal_dd.value, prod_dd.value, v, p[4], p[0]*m, p[1]*m, p[2]*m, p[3]*m))
        conn.commit(); conn.close(); amt_in.value = ""; refresh_data()

    def save_prod(e):
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO produkty VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (nazwa) DO UPDATE SET kcal=EXCLUDED.kcal, b=EXCLUDED.b, t=EXCLUDED.t, w=EXCLUDED.w, jednostka=EXCLUDED.jednostka",
                    (n_nazwa.value, float(n_k.value or 0), float(n_b.value or 0), float(n_t.value or 0), float(n_w.value or 0), n_typ.value))
        conn.commit(); conn.close(); n_nazwa.value=""; n_k.value=""; n_b.value=""; n_t.value=""; n_w.value=""; load_prods(); page.open(ft.SnackBar(ft.Text("Zapisano!")))

    def save_cel(e):
        conn = get_db(); cur = conn.cursor()
        cur.execute("UPDATE profile SET cel_kcal=%s WHERE user_name=%s", (float(p_cel.value), st["u"]))
        conn.commit(); conn.close(); p_cel.value=""; refresh_data()

    def save_waga(e):
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO waga_log VALUES (%s,%s,%s) ON CONFLICT (user_name, data) DO UPDATE SET waga=EXCLUDED.waga", (st["u"], st["d"].strftime("%Y-%m-%d"), float(p_waga.value.replace(",","."))))
        conn.commit(); conn.close(); p_waga.value=""; refresh_data()

    def login(e):
        if (u_in.value == "Filip" and p_in.value == "1111") or (u_in.value == "Nikola" and p_in.value == "2222"):
            st["u"] = u_in.value; v_login.visible = False; v_main.visible = True; page.navigation_bar.visible = True; refresh_data()
        else: page.open(ft.SnackBar(ft.Text("Błąd PIN!")))
        page.update()

    # --- WIDOKI ---
    u_in = ft.Dropdown(label="Użytkownik", options=[ft.dropdown.Option("Filip"), ft.dropdown.Option("Nikola")])
    p_in = ft.TextField(label="PIN", password=True, keyboard_type="number")
    v_login = ft.Column([ft.Text("LOGOWANIE", size=30, color="blue400"), u_in, p_in, ft.ElevatedButton("WEJDŹ", on_click=login, height=50)], horizontal_alignment="center")

    tab_dziennik = ft.Column([
        ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: change_d(-1)), date_txt, ft.IconButton(ft.Icons.ARROW_FORWARD, on_click=lambda _: change_d(1))], alignment="center"),
        ft.Container(content=ft.Column([kcal_txt, pb, macro_row], horizontal_alignment="center")),
        ft.Row([meal_dd, amt_in]), prod_dd, ft.ElevatedButton("ZJEDZONE!", on_click=add_meal, bgcolor="blue", color="white", height=45), ft.Divider(), log_list
    ], expand=True)

    tab_baza = ft.Column([
        ft.Text("NOWY PRODUKT", size=20, weight="bold"), ft.Row([n_nazwa, n_typ]), ft.Row([n_k, n_b, n_t, n_w]), 
        ft.ElevatedButton("DODAJ DO BAZY", on_click=save_prod, bgcolor="green", color="white"),
    ], visible=False)

    tab_profil = ft.Column([
        ft.Text("PROFIL", size=20, weight="bold"), ft.Row([p_cel, ft.IconButton(ft.Icons.SAVE, on_click=save_cel)]),
        ft.Text("WAGA", size=20, weight="bold"), ft.Row([p_waga, ft.IconButton(ft.Icons.ADD, on_click=save_waga)]),
        waga_list, ft.TextButton("WYLOGUJ", on_click=lambda _: page.window_reload(), color="red")
    ], visible=False, expand=True)

    v_main = ft.Container(content=tab_dziennik, expand=True, visible=False)

    def change_d(delta): st["d"] += datetime.timedelta(days=delta); refresh_data()
    
    def nav_change(e):
        tab_dziennik.visible = (e.control.selected_index == 0)
        tab_baza.visible = (e.control.selected_index == 1)
        tab_profil.visible = (e.control.selected_index == 2)
        v_main.content = tab_dziennik if tab_dziennik.visible else (tab_baza if tab_baza.visible else tab_profil)
        page.update()

    page.navigation_bar = ft.NavigationBar(destinations=[
        ft.NavigationBarDestination(icon=ft.Icons.BOOK, label="Dziennik"),
        ft.NavigationBarDestination(icon=ft.Icons.ADD_CIRCLE, label="Baza"),
        ft.NavigationBarDestination(icon=ft.Icons.PERSON, label="Profil")
    ], on_change=nav_change, visible=False)

    def load_prods():
        c = get_db(); cur = c.cursor(); cur.execute("SELECT nazwa FROM produkty ORDER BY nazwa ASC")
        prod_dd.options = [ft.dropdown.Option(p[0]) for p in cur.fetchall()]; c.close(); page.update()

    page.add(v_login, v_main)
    load_prods()

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("PORT", 8080)), host="0.0.0.0")
