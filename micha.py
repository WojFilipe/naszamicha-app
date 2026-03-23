import flet as ft, psycopg2, os, datetime

DB_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_jGvTXNQ0ep2y@ep-small-dream-als2k8po-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")
def get_db(): return psycopg2.connect(DB_URL)

def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS produkty (nazwa TEXT PRIMARY KEY, kcal REAL, b REAL, t REAL, w REAL, jednostka TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS dziennik (id SERIAL PRIMARY KEY, user_name TEXT, data TEXT, posilek TEXT, nazwa TEXT, ilosc REAL, jednostka TEXT, kcal REAL, b REAL, t REAL, w REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS profile (user_name TEXT PRIMARY KEY, cel_kcal REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS waga_log (user_name TEXT, data TEXT, waga REAL, PRIMARY KEY(user_name, data))")
    cur.execute("INSERT INTO profile (user_name, cel_kcal) VALUES ('Filip', 2500), ('Nikola', 2000) ON CONFLICT DO NOTHING")
    conn.commit(); conn.close()

def main(page: ft.Page):
    page.title = "Nasza Micha"; page.theme_mode = ft.ThemeMode.DARK; page.padding = 15
    init_db()
    app_date = datetime.date.today()

    # --- LOGOWANIE ---
    login_imie = ft.Dropdown(label="Kto się loguje?", options=[ft.dropdown.Option("Filip"), ft.dropdown.Option("Nikola")])
    login_haslo = ft.TextField(label="Hasło (PIN)", password=True, keyboard_type=ft.KeyboardType.NUMBER)
    
    def sprawdz_logowanie(e):
        i = login_imie.value; h = login_haslo.value
        if (i == "Filip" and h == "1111") or (i == "Nikola" and h == "2222"):
            page.client_storage.set("user", i) # Zapisuje w telefonie na stałe!
            view_login.visible = False; view_dziennik.visible = True; page.navigation_bar.visible = True
            naglowek_imie.value = f"Dziennik: {i}"; refresh_all()
            page.open(ft.SnackBar(ft.Text(f"Zalogowano jako {i}!", color="green")))
        else:
            page.open(ft.SnackBar(ft.Text("Błąd PIN!", color="red")))
        page.update()

    view_login = ft.Column([ft.Text("NASZA MICHA", size=30, weight="bold", color="blue400"), login_imie, login_haslo, ft.ElevatedButton("WEJDŹ", on_click=sprawdz_logowanie, expand=True)], visible=True)

    # --- ZMIENNE UI ---
    naglowek_imie = ft.Text("Dziennik", size=22, weight="bold", color="blue400")
    status_kcal = ft.Text("0 / 0 kcal", size=26, weight="bold"); prog_bar = ft.ProgressBar(value=0, height=12, color="green")
    b_txt = ft.Text("B: 0g", color="red"); t_txt = ft.Text("T: 0g", color="orange"); w_txt = ft.Text("W: 0g", color="blue")
    log_list = ft.ListView(expand=True, spacing=5); date_display = ft.Text(app_date.strftime("%Y-%m-%d"), size=16, weight="bold")
    input_nowy_cel = ft.TextField(label="Nowy cel", keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    input_nowa_waga = ft.TextField(label="Waga", keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    waga_list = ft.ListView(expand=True, spacing=5)

    def usun_posilek(e):
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM dziennik WHERE id=%s", (e.control.data,)); conn.commit(); conn.close(); refresh_all()

    def refresh_all(e=None):
        u = page.client_storage.get("user")
        if not u: return
        naglowek_imie.value = f"Dziennik: {u}"; data_str = app_date.strftime("%Y-%m-%d"); date_display.value = data_str
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT cel_kcal FROM profile WHERE user_name=%s", (u,))
        target = (cur.fetchone() or [2000])[0]
        cur.execute("SELECT SUM(kcal), SUM(b), SUM(t), SUM(w) FROM dziennik WHERE user_name=%s AND data=%s", (u, data_str))
        sums = cur.fetchone()
        k, b, t, w = sums[0] or 0, sums[1] or 0, sums[2] or 0, sums[3] or 0
        status_kcal.value = f"{int(k)} / {int(target)} kcal"; prog_bar.value = min(k / target, 1.0) if target > 0 else 0
        b_txt.value = f"B: {int(b)}g"; t_txt.value = f"T: {int(t)}g"; w_txt.value = f"W: {int(w)}g"
        
        log_list.controls.clear()
        for p in ["Śniadanie", "II Śniadanie", "Obiad", "Przekąska", "Kolacja"]:
            cur.execute("SELECT id, nazwa, ilosc, jednostka, kcal FROM dziennik WHERE user_name=%s AND data=%s AND posilek=%s", (u, data_str, p))
            items = cur.fetchall()
            if items:
                log_list.controls.append(ft.Text(f"{p}", size=14, weight="bold", color="blue200"))
                for item in items:
                    log_list.controls.append(ft.ListTile(title=ft.Text(f"{item[1]}"), subtitle=ft.Text(f"{int(item[2])} {item[3]} • {int(item[4])} kcal"), trailing=ft.IconButton(ft.Icons.DELETE, icon_color="red", data=item[0], on_click=usun_posilek)))
        
        waga_list.controls.clear()
        cur.execute("SELECT data, waga FROM waga_log WHERE user_name=%s ORDER BY data DESC", (u,))
        for row in cur.fetchall(): waga_list.controls.append(ft.ListTile(title=ft.Text(f"⚖️ {row[1]} kg"), subtitle=ft.Text(f"{row[0]}")))
        conn.close(); page.update()

    def zmien_cel(e):
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO profile (user_name, cel_kcal) VALUES (%s, %s) ON CONFLICT (user_name) DO UPDATE SET cel_kcal = EXCLUDED.cel_kcal", (page.client_storage.get("user"), float(input_nowy_cel.value)))
        conn.commit(); conn.close(); input_nowy_cel.value = ""; refresh_all(); page.open(ft.SnackBar(ft.Text("Cel zaktualizowany!")))

    def dodaj_wage(e):
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO waga_log (user_name, data, waga) VALUES (%s, %s, %s) ON CONFLICT (user_name, data) DO UPDATE SET waga = EXCLUDED.waga", (page.client_storage.get("user"), app_date.strftime("%Y-%m-%d"), float(input_nowa_waga.value.replace(",", "."))))
        conn.commit(); conn.close(); input_nowa_waga.value = ""; refresh_all(); page.open(ft.SnackBar(ft.Text("Waga zapisana!")))

    def chg_day(d): nonlocal app_date; app_date += datetime.timedelta(days=d); refresh_all()
    kalendarz_row = ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: chg_day(-1)), date_display, ft.IconButton(ft.Icons.ARROW_FORWARD, on_click=lambda e: chg_day(1))], alignment="center")

    meal_select = ft.Dropdown(options=[ft.dropdown.Option(m) for m in ["Śniadanie", "II Śniadanie", "Obiad", "Przekąska", "Kolacja"]], value="Obiad", expand=True)
    dd_produkt = ft.Dropdown(label="Wybierz produkt", expand=True); input_ilosc = ft.TextField(label="Ilość", width=100, keyboard_type=ft.KeyboardType.NUMBER)

    def load_products():
        conn = get_db(); cur = conn.cursor(); cur.execute("SELECT nazwa FROM produkty ORDER BY nazwa ASC")
        dd_produkt.options = [ft.dropdown.Option(p[0]) for p in cur.fetchall()]; conn.close(); page.update()

    def dodaj_posilek(e):
        if not dd_produkt.value or not input_ilosc.value: return
        conn = get_db(); cur = conn.cursor(); cur.execute("SELECT kcal, b, t, w, jednostka FROM produkty WHERE nazwa=%s", (dd_produkt.value,))
        p = cur.fetchone(); ilosc = float(input_ilosc.value.replace(",", ".")); mnoznik = ilosc / 100 if p[4] == '100g' else ilosc
        cur.execute("INSERT INTO dziennik (user_name, data, posilek, nazwa, ilosc, jednostka, kcal, b, t, w) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (page.client_storage.get("user"), app_date.strftime("%Y-%m-%d"), meal_select.value, dd_produkt.value, ilosc, p[4], p[0]*mnoznik, p[1]*mnoznik, p[2]*mnoznik, p[3]*mnoznik))
        conn.commit(); conn.close(); input_ilosc.value = ""; refresh_all(); page.open(ft.SnackBar(ft.Text("Dodano!")))

    n_nazwa = ft.TextField(label="Nazwa", expand=True); n_jednostka = ft.Dropdown(options=[ft.dropdown.Option("100g"), ft.dropdown.Option("szt")], value="100g", width=100)
    n_k = ft.TextField(label="Kcal", expand=1); n_b = ft.TextField(label="B", expand=1); n_t = ft.TextField(label="T", expand=1); n_w = ft.TextField(label="W", expand=1)

    def zapisz_produkt(e):
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO produkty VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO UPDATE SET kcal=EXCLUDED.kcal, b=EXCLUDED.b, t=EXCLUDED.t, w=EXCLUDED.w, jednostka=EXCLUDED.jednostka", (n_nazwa.value, float(n_k.value or 0), float(n_b.value or 0), float(n_t.value or 0), float(n_w.value or 0), n_jednostka.value))
        conn.commit(); conn.close(); n_nazwa.value=""; n_k.value=""; n_b.value=""; n_t.value=""; n_w.value=""; load_products(); page.open(ft.SnackBar(ft.Text("Zapisano w bazie!")))

    def wyloguj(e):
        page.client_storage.remove("user")
        view_dziennik.visible = False; view_baza.visible = False; view_profil.visible = False; page.navigation_bar.visible = False; view_login.visible = True; page.update()

    view_dziennik = ft.Column([naglowek_imie, kalendarz_row, ft.Container(content=ft.Column([status_kcal, prog_bar, ft.Row([b_txt, t_txt, w_txt], alignment="spaceEvenly")], horizontal_alignment="center")), ft.Row([meal_select, input_ilosc]), dd_produkt, ft.ElevatedButton("ZJEDZONE!", on_click=dodaj_posilek, height=50, bgcolor="blue", color="white"), log_list], visible=False, expand=True)
    view_baza = ft.Column([ft.Row([n_nazwa, n_jednostka]), ft.Row([n_k, n_b, n_t, n_w]), ft.ElevatedButton("ZAPISZ PRODUKT", on_click=zapisz_produkt, bgcolor="green", color="white")], visible=False, expand=True)
    view_profil = ft.Column([ft.Row([input_nowy_cel, ft.ElevatedButton("Cel", on_click=zmien_cel)]), ft.Row([input_nowa_waga, ft.ElevatedButton("Waga", on_click=dodaj_wage)]), waga_list, ft.ElevatedButton("WYLOGUJ", on_click=wyloguj, bgcolor="red", color="white")], visible=False, expand=True)

    def chg_tab(e):
        idx = e.control.selected_index
        view_dziennik.visible = (idx == 0); view_baza.visible = (idx == 1); view_profil.visible = (idx == 2); page.update()

    page.navigation_bar = ft.NavigationBar(destinations=[ft.NavigationBarDestination(icon=ft.Icons.BOOK, label="Dziennik"), ft.NavigationBarDestination(icon=ft.Icons.ADD, label="Baza"), ft.NavigationBarDestination(icon=ft.Icons.PERSON, label="Profil")], on_change=chg_tab, visible=False)
    page.add(view_login, view_dziennik, view_baza, view_profil)
    load_products()
    
    # Auto-logowanie jeśli jest zapisana sesja
    if page.client_storage.contains_key("user"):
        view_login.visible = False; view_dziennik.visible = True; page.navigation_bar.visible = True; refresh_all()

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("PORT", 8080)), host="0.0.0.0")
