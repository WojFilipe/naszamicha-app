import flet as ft
import psycopg2
import os
import datetime

# TU WKLEJ SWÓJ LINK Z NEON.TECH NA CZAS TESTÓW (w cudzysłowach)
# Na serwerze Render ukryjemy go w zmiennych środowiskowych!
DB_URL = os.environ.get("DATABASE_URL", "TUTAJ_WKLEJ_SWOJ_LINK_POSTGRESQL")

def get_db():
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    # Tabela produktów
    cur.execute("CREATE TABLE IF NOT EXISTS produkty (nazwa TEXT PRIMARY KEY, kcal REAL, b REAL, t REAL, w REAL, jednostka TEXT)")
    # Tabela dziennika (Dodano SERIAL id dla chmury)
    cur.execute("CREATE TABLE IF NOT EXISTS dziennik (id SERIAL PRIMARY KEY, user_name TEXT, data TEXT, posilek TEXT, nazwa TEXT, ilosc REAL, jednostka TEXT, kcal REAL, b REAL, t REAL, w REAL)")
    # Tabela profili
    cur.execute("CREATE TABLE IF NOT EXISTS profile (user_name TEXT PRIMARY KEY, cel_kcal REAL)")
    # Tabela wagi
    cur.execute("CREATE TABLE IF NOT EXISTS waga_log (user_name TEXT, data TEXT, waga REAL, PRIMARY KEY(user_name, data))")
    
    cur.execute("INSERT INTO profile (user_name, cel_kcal) VALUES ('Filip', 2500), ('Dziewczyna', 2000) ON CONFLICT DO NOTHING")
    
    gotowe_produkty = [
        ('Pierś z kurczaka', 165, 31, 3.6, 0, '100g'), 
        ('Łosoś świeży', 208, 20, 13, 0, '100g'),
        ('Ryż biały (suchy)', 344, 6.7, 0.7, 78.9, '100g'), 
        ('Ziemniaki surowe', 77, 2, 0.1, 17.5, '100g'),
        ('Jajko kurze (szt.)', 78, 7.3, 5.3, 0.6, 'szt'), 
        ('Banan średni (szt.)', 105, 1.3, 0.4, 27, 'szt'),
        ('Pomidor średni (szt.)', 32, 1.5, 0.3, 6.8, 'szt'), 
        ('Oliwa z oliwek', 884, 0, 100, 0, '100g'),
        ('Bajgiel (szt.)', 250, 9, 1.5, 50, 'szt'),
        ('Makaron do spaghetti (suchy)', 350, 12, 1.5, 72, '100g'),
        ('Mięso mielone wołowo-wieprzowe', 246, 15, 20, 0, '100g'),
        ('Sos pomidorowy (Passata)', 32, 1.6, 0.2, 5.5, '100g'),
        ('Kurczak w panierce / Strips (szt.)', 120, 10, 6, 8, 'szt'),
        ('Pstrąg tęczowy świeży', 119, 20, 3.4, 0, '100g'),
        ('Szejk: Białko + Mleko 2% (porcja)', 240, 32.5, 7, 14, 'szt')
    ]
    cur.executemany("INSERT INTO produkty VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING", gotowe_produkty)
    conn.commit()
    conn.close()

def main(page: ft.Page):
    page.title = "Nasza Micha - Chmura"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    init_db()

    app_date = datetime.date.today()

    user_select = ft.Dropdown(label="Obecnie korzysta:", width=200, options=[ft.dropdown.Option("Filip"), ft.dropdown.Option("Dziewczyna")], value="Filip")

    status_kcal = ft.Text("0 / 0 kcal", size=28, weight="bold")
    prog_bar = ft.ProgressBar(value=0, width=400, height=12, color="green")
    b_txt = ft.Text("B: 0g", color="red", weight="bold"); t_txt = ft.Text("T: 0g", color="orange", weight="bold"); w_txt = ft.Text("W: 0g", color="blue", weight="bold")
    log_list = ft.ListView(expand=1, spacing=0)
    date_display = ft.Text(app_date.strftime("%Y-%m-%d"), size=18, weight="bold")

    input_nowy_cel = ft.TextField(label="Nowy cel Kcal", width=150)
    input_nowa_waga = ft.TextField(label="Dzisiejsza waga (kg)", width=150)
    waga_list = ft.ListView(expand=1, spacing=5)

    def usun_posilek(e):
        row_id = e.control.data
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM dziennik WHERE id=%s", (row_id,))
        conn.commit(); conn.close()
        refresh_all()

    def refresh_all(e=None):
        user = user_select.value
        data_str = app_date.strftime("%Y-%m-%d")
        date_display.value = data_str

        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT cel_kcal FROM profile WHERE user_name=%s", (user,))
        target = cur.fetchone()[0]

        cur.execute("SELECT SUM(kcal), SUM(b), SUM(t), SUM(w) FROM dziennik WHERE user_name=%s AND data=%s", (user, data_str))
        sums = cur.fetchone()
        k = sums[0] or 0; b = sums[1] or 0; t = sums[2] or 0; w = sums[3] or 0

        status_kcal.value = f"{int(k)} / {int(target)} kcal"
        prog_bar.value = min(k / target, 1.0) if target > 0 else 0
        b_txt.value = f"B: {int(b)}g"; t_txt.value = f"T: {int(t)}g"; w_txt.value = f"W: {int(w)}g"

        log_list.controls.clear()
        posilki = ["Śniadanie", "II Śniadanie", "Obiad", "Przekąska", "Kolacja"]
        for p in posilki:
            cur.execute("SELECT id, nazwa, ilosc, jednostka, kcal FROM dziennik WHERE user_name=%s AND data=%s AND posilek=%s", (user, data_str, p))
            items = cur.fetchall()
            if items:
                log_list.controls.append(ft.Text(f"🍽️ {p}", size=16, weight="bold", color="blue200"))
                for item in items:
                    jednostka_str = "g" if item[3] == '100g' else "szt."
                    ilosc_format = int(item[2]) if item[2].is_integer() else item[2]
                    log_list.controls.append(
                        ft.ListTile(title=ft.Text(f"{item[1]} - {ilosc_format} {jednostka_str}"), subtitle=ft.Text(f"{int(item[4])} kcal"), trailing=ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red400", data=item[0], on_click=usun_posilek))
                    )
                log_list.controls.append(ft.Divider(height=2, color="grey800"))

        waga_list.controls.clear()
        cur.execute("SELECT data, waga FROM waga_log WHERE user_name=%s ORDER BY data DESC", (user,))
        for row in cur.fetchall():
            waga_list.controls.append(ft.ListTile(title=ft.Text(f"⚖️ {row[1]} kg"), subtitle=ft.Text(f"Data: {row[0]}")))

        conn.close(); page.update()

    user_select.on_change = refresh_all

    def zmien_cel(e):
        try: nowy_cel = float(input_nowy_cel.value)
        except ValueError: return
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO profile (user_name, cel_kcal) VALUES (%s, %s) ON CONFLICT (user_name) DO UPDATE SET cel_kcal = EXCLUDED.cel_kcal", (user_select.value, nowy_cel))
        conn.commit(); conn.close()
        input_nowy_cel.value = ""; refresh_all()
        page.show_snack_bar(ft.SnackBar(ft.Text("Zaktualizowano limit kalorii!")))

    def dodaj_wage(e):
        try: nowa_waga = float(input_nowa_waga.value.replace(",", "."))
        except ValueError: return
        data_str = app_date.strftime("%Y-%m-%d")
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO waga_log (user_name, data, waga) VALUES (%s, %s, %s) ON CONFLICT (user_name, data) DO UPDATE SET waga = EXCLUDED.waga", (user_select.value, data_str, nowa_waga))
        conn.commit(); conn.close()
        input_nowa_waga.value = ""; refresh_all()

    def prev_day(e): nonlocal app_date; app_date -= datetime.timedelta(days=1); refresh_all()
    def next_day(e): nonlocal app_date; app_date += datetime.timedelta(days=1); refresh_all()
    def today_day(e): nonlocal app_date; app_date = datetime.date.today(); refresh_all()

    kalendarz_row = ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=prev_day), date_display, ft.IconButton(ft.Icons.ARROW_FORWARD, on_click=next_day), ft.TextButton("Dzisiaj", on_click=today_day)], alignment="center")

    meal_select = ft.Dropdown(label="Posiłek", width=140, options=[ft.dropdown.Option(m) for m in ["Śniadanie", "II Śniadanie", "Obiad", "Przekąska", "Kolacja"]], value="Obiad")
    dd_produkt = ft.Dropdown(label="Wybierz produkt", width=250)
    input_ilosc = ft.TextField(label="Ilość", width=90)

    def zmien_etykiete(e):
        if not dd_produkt.value: return
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT jednostka FROM produkty WHERE nazwa=%s", (dd_produkt.value,))
        res = cur.fetchone()
        conn.close()
        if res: input_ilosc.label = "Ile gramów?" if res[0] == '100g' else "Ile sztuk?"
        page.update()

    dd_produkt.on_change = zmien_etykiete

    def load_products():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT nazwa FROM produkty ORDER BY nazwa ASC")
        dd_produkt.options = [ft.dropdown.Option(p[0]) for p in cur.fetchall()]
        conn.close(); page.update()

    def dodaj_posilek(e):
        if not dd_produkt.value or not input_ilosc.value: return
        try: ilosc_wpisana = float(input_ilosc.value.replace(",", "."))
        except ValueError: return
        data_str = app_date.strftime("%Y-%m-%d")
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT kcal, b, t, w, jednostka FROM produkty WHERE nazwa=%s", (dd_produkt.value,))
        p = cur.fetchone()
        mnoznik = ilosc_wpisana / 100 if p[4] == '100g' else ilosc_wpisana
        cur.execute("INSERT INTO dziennik (user_name, data, posilek, nazwa, ilosc, jednostka, kcal, b, t, w) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (user_select.value, data_str, meal_select.value, dd_produkt.value, ilosc_wpisana, p[4], p[0]*mnoznik, p[1]*mnoznik, p[2]*mnoznik, p[3]*mnoznik))
        conn.commit(); conn.close()
        input_ilosc.value = ""; refresh_all()

    n_nazwa = ft.TextField(label="Nazwa produktu")
    n_jednostka = ft.Dropdown(label="Typ", width=150, options=[ft.dropdown.Option("100g"), ft.dropdown.Option("szt")], value="100g")
    n_kcal = ft.TextField(label="Kcal", width=70); n_b = ft.TextField(label="B", width=70); n_t = ft.TextField(label="T", width=70); n_w = ft.TextField(label="W", width=70)

    def zapisz_produkt(e):
        if not n_nazwa.value: return
        try: k = float(n_kcal.value or 0); b = float(n_b.value or 0); t = float(n_t.value or 0); w = float(n_w.value or 0)
        except ValueError: return
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO produkty (nazwa, kcal, b, t, w, jednostka) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (nazwa) DO UPDATE SET kcal=EXCLUDED.kcal, b=EXCLUDED.b, t=EXCLUDED.t, w=EXCLUDED.w, jednostka=EXCLUDED.jednostka", (n_nazwa.value, k, b, t, w, n_jednostka.value))
        conn.commit(); conn.close()
        n_nazwa.value = ""; n_kcal.value = ""; n_b.value = ""; n_t.value = ""; n_w.value = ""
        load_products(); show_dziennik(None); page.update()

    view_dziennik = ft.Column([kalendarz_row, ft.Container(content=ft.Column([status_kcal, prog_bar, ft.Row([b_txt, t_txt, w_txt], alignment="center")], horizontal_alignment="center"), padding=20), ft.Row([meal_select, dd_produkt, input_ilosc], alignment="center", wrap=True), ft.ElevatedButton("ZJEDZONE!", on_click=dodaj_posilek, width=400, bgcolor="blue", color="white"), ft.Divider(), log_list], visible=True, expand=1)
    view_baza = ft.Column([ft.Text("DODAJ SWÓJ PRODUKT", size=18, weight="bold"), ft.Row([n_nazwa, n_jednostka]), ft.Row([n_kcal, n_b, n_t, n_w], wrap=True), ft.ElevatedButton("ZAPISZ PRODUKT", on_click=zapisz_produkt, width=400, bgcolor="green", color="white")], visible=False, expand=1)
    view_profil = ft.Column([ft.Text("USTAWIENIA PROFILU", size=18, weight="bold"), ft.Row([input_nowy_cel, ft.ElevatedButton("Zmień Cel", on_click=zmien_cel, bgcolor="orange", color="white")], alignment="spaceBetween"), ft.Divider(), ft.Text("ŚLEDZENIE WAGI", size=18, weight="bold"), ft.Row([input_nowa_waga, ft.ElevatedButton("Zapisz Wagę", on_click=dodaj_wage, bgcolor="blue", color="white")], alignment="spaceBetween"), waga_list], visible=False, expand=1)

    def show_dziennik(e): view_dziennik.visible = True; view_baza.visible = False; view_profil.visible = False; btn_dziennik.bgcolor = "green"; btn_baza.bgcolor = "grey"; btn_profil.bgcolor = "grey"; page.update()
    def show_baza(e): view_dziennik.visible = False; view_baza.visible = True; view_profil.visible = False; btn_dziennik.bgcolor = "grey"; btn_baza.bgcolor = "green"; btn_profil.bgcolor = "grey"; page.update()
    def show_profil(e): view_dziennik.visible = False; view_baza.visible = False; view_profil.visible = True; btn_dziennik.bgcolor = "grey"; btn_baza.bgcolor = "grey"; btn_profil.bgcolor = "orange"; page.update()

    btn_dziennik = ft.ElevatedButton("🍽️ DZIENNIK", on_click=show_dziennik, bgcolor="green", color="white")
    btn_baza = ft.ElevatedButton("➕ PRODUKT", on_click=show_baza, bgcolor="grey", color="white")
    btn_profil = ft.ElevatedButton("⚙️ PROFIL", on_click=show_profil, bgcolor="grey", color="white")
    
    page.add(ft.Row([user_select], alignment="center"), ft.Row([btn_dziennik, btn_baza, btn_profil], alignment="center"), ft.Divider(), view_dziennik, view_baza, view_profil)
    load_products(); refresh_all()

# KONFIGURACJA POD SERWER W CHMURZE
port = int(os.environ.get("PORT", 8080))
ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, host="0.0.0.0")