import flet as ft
import psycopg2
import os
import datetime

# TUTAJ WKLEJ Z POWROTEM SWÓJ LINK Z NEON.TECH
DB_URL = os.environ.get("DATABASE_URL", "TUTAJ_WKLEJ_SWOJ_LINK")

def get_db():
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS produkty (nazwa TEXT PRIMARY KEY, kcal REAL, b REAL, t REAL, w REAL, jednostka TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS dziennik (id SERIAL PRIMARY KEY, user_name TEXT, data TEXT, posilek TEXT, nazwa TEXT, ilosc REAL, jednostka TEXT, kcal REAL, b REAL, t REAL, w REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS profile (user_name TEXT PRIMARY KEY, cel_kcal REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS waga_log (user_name TEXT, data TEXT, waga REAL, PRIMARY KEY(user_name, data))")
    
    cur.execute("INSERT INTO profile (user_name, cel_kcal) VALUES ('Filip', 2500), ('Dziewczyna', 2000) ON CONFLICT DO NOTHING")
    conn.commit()
    conn.close()

def main(page: ft.Page):
    page.title = "Nasza Micha"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 15
    page.vertical_alignment = ft.MainAxisAlignment.START
    init_db()

    app_date = datetime.date.today()

    # WYBÓR UŻYTKOWNIKA (Rozciągnięty na telefon)
    user_select = ft.Dropdown(
        label="Obecnie korzysta:", 
        options=[ft.dropdown.Option("Filip"), ft.dropdown.Option("Dziewczyna")], 
        value="Filip", 
        expand=True
    )

    # WIZUALNE POTWIERDZENIE (Żebyś nie miał wątpliwości na czyim jesteś koncie)
    naglowek_imie = ft.Text("Dziennik: Filip", size=20, weight="bold", color="blue400")
    
    status_kcal = ft.Text("0 / 0 kcal", size=26, weight="bold")
    prog_bar = ft.ProgressBar(value=0, height=12, color="green")
    b_txt = ft.Text("B: 0g", color="red", weight="bold"); t_txt = ft.Text("T: 0g", color="orange", weight="bold"); w_txt = ft.Text("W: 0g", color="blue", weight="bold")
    log_list = ft.ListView(expand=True, spacing=5)
    date_display = ft.Text(app_date.strftime("%Y-%m-%d"), size=16, weight="bold")

    input_nowy_cel = ft.TextField(label="Nowy cel Kcal", expand=True)
    input_nowa_waga = ft.TextField(label="Dzisiejsza waga (kg)", expand=True)
    waga_list = ft.ListView(expand=True, spacing=5)

    def usun_posilek(e):
        row_id = e.control.data
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM dziennik WHERE id=%s", (row_id,))
        conn.commit(); conn.close()
        refresh_all()

    def refresh_all(e=None):
        # Twarde wymuszenie przypisania użytkownika
        if e and hasattr(e.control, "value"):
            user_select.value = e.control.value 
            
        user = user_select.value
        naglowek_imie.value = f"Dziennik: {user}" # Zmienia tekst na ekranie!
        
        data_str = app_date.strftime("%Y-%m-%d")
        date_display.value = data_str

        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT cel_kcal FROM profile WHERE user_name=%s", (user,))
        res_cel = cur.fetchone()
        target = res_cel[0] if res_cel else 2000

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
                log_list.controls.append(ft.Container(content=ft.Text(f"{p}", size=14, weight="bold", color="blue200"), padding=ft.padding.only(top=10, bottom=5)))
                for item in items:
                    jednostka_str = "g" if item[3] == '100g' else "szt."
                    ilosc_format = int(item[2]) if item[2].is_integer() else item[2]
                    log_list.controls.append(
                        ft.ListTile(title=ft.Text(f"{item[1]}", size=14), subtitle=ft.Text(f"{ilosc_format}{jednostka_str} • {int(item[4])} kcal"), trailing=ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red400", data=item[0], on_click=usun_posilek), content_padding=0)
                    )
                log_list.controls.append(ft.Divider(height=1, color="grey800"))

        waga_list.controls.clear()
        cur.execute("SELECT data, waga FROM waga_log WHERE user_name=%s ORDER BY data DESC", (user,))
        for row in cur.fetchall():
            waga_list.controls.append(ft.ListTile(title=ft.Text(f"⚖️ {row[1]} kg"), subtitle=ft.Text(f"{row[0]}"), content_padding=0))

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
        page.show_snack_bar(ft.SnackBar(ft.Text(f"Zaktualizowano limit dla {user_select.value}!")))

    def dodaj_wage(e):
        try: nowa_waga = float(input_nowa_waga.value.replace(",", "."))
        except ValueError: return
        data_str = app_date.strftime("%Y-%m-%d")
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO waga_log (user_name, data, waga) VALUES (%s, %s, %s) ON CONFLICT (user_name, data) DO UPDATE SET waga = EXCLUDED.waga", (user_select.value, data_str, nowa_waga))
        conn.commit(); conn.close()
        input_nowa_waga.value = ""; refresh_all()
        page.show_snack_bar(ft.SnackBar(ft.Text(f"Waga zapisana dla konta: {user_select.value}!")))

    def prev_day(e): nonlocal app_date; app_date -= datetime.timedelta(days=1); refresh_all()
    def next_day(e): nonlocal app_date; app_date += datetime.timedelta(days=1); refresh_all()
    def today_day(e): nonlocal app_date; app_date = datetime.date.today(); refresh_all()

    kalendarz_row = ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=prev_day), date_display, ft.IconButton(ft.Icons.ARROW_FORWARD, on_click=next_day), ft.IconButton(ft.Icons.TODAY, on_click=today_day, icon_color="blue")], alignment="center")

    meal_select = ft.Dropdown(label="Posiłek", options=[ft.dropdown.Option(m) for m in ["Śniadanie", "II Śniadanie", "Obiad", "Przekąska", "Kolacja"]], value="Obiad", expand=True)
    dd_produkt = ft.Dropdown(label="Wybierz produkt", expand=True)
    input_ilosc = ft.TextField(label="Ilość", width=100)

    def zmien_etykiete(e):
        if not dd_produkt.value: return
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT jednostka FROM produkty WHERE nazwa=%s", (dd_produkt.value,))
        res = cur.fetchone()
        conn.close()
        if res: input_ilosc.label = "Gramy" if res[0] == '100g' else "Sztuki"
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
        
        # Pancerne zabezpieczenie - pobieramy usera w chwili kliknięcia!
        aktywny_user = user_select.value 

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT kcal, b, t, w, jednostka FROM produkty WHERE nazwa=%s", (dd_produkt.value,))
        p = cur.fetchone()
        mnoznik = ilosc_wpisana / 100 if p[4] == '100g' else ilosc_wpisana
        
        cur.execute("INSERT INTO dziennik (user_name, data, posilek, nazwa, ilosc, jednostka, kcal, b, t, w) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (aktywny_user, data_str, meal_select.value, dd_produkt.value, ilosc_wpisana, p[4], p[0]*mnoznik, p[1]*mnoznik, p[2]*mnoznik, p[3]*mnoznik))
        conn.commit(); conn.close()
        input_ilosc.value = ""; refresh_all()
        # Wyskakujące info na dole ekranu
        page.show_snack_bar(ft.SnackBar(ft.Text(f"Dodano posiłek do konta: {aktywny_user}")))

    n_nazwa = ft.TextField(label="Nazwa produktu", expand=True)
    n_jednostka = ft.Dropdown(label="Typ", options=[ft.dropdown.Option("100g"), ft.dropdown.Option("szt")], value="100g", width=100)
    n_kcal = ft.TextField(label="Kcal", expand=1); n_b = ft.TextField(label="B", expand=1); n_t = ft.TextField(label="T", expand=1); n_w = ft.TextField(label="W", expand=1)

    def zapisz_produkt(e):
        if not n_nazwa.value: return
        try: k = float(n_kcal.value or 0); b = float(n_b.value or 0); t = float(n_t.value or 0); w = float(n_w.value or 0)
        except ValueError: return
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO produkty (nazwa, kcal, b, t, w, jednostka) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (nazwa) DO UPDATE SET kcal=EXCLUDED.kcal, b=EXCLUDED.b, t=EXCLUDED.t, w=EXCLUDED.w, jednostka=EXCLUDED.jednostka", (n_nazwa.value, k, b, t, w, n_jednostka.value))
        conn.commit(); conn.close()
        n_nazwa.value = ""; n_kcal.value = ""; n_b.value = ""; n_t.value = ""; n_w.value = ""
        load_products()
        page.show_snack_bar(ft.SnackBar(ft.Text("Produkt zapisany w bazie!")))
        page.update()

    # WIDOKI GŁÓWNE (Zoptymalizowane pod telefony)
    view_dziennik = ft.Column([
        naglowek_imie,
        kalendarz_row, 
        ft.Container(content=ft.Column([status_kcal, prog_bar, ft.Row([b_txt, t_txt, w_txt], alignment="spaceEvenly")], horizontal_alignment="center"), padding=10), 
        ft.Row([meal_select, input_ilosc]),
        dd_produkt,
        ft.ElevatedButton("ZJEDZONE!", on_click=dodaj_posilek, height=50, bgcolor="blue", color="white", style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))), 
        ft.Divider(), 
        log_list
    ], visible=True, expand=True)

    view_baza = ft.Column([
        ft.Text("DODAJ NOWY PRODUKT", size=18, weight="bold"), 
        ft.Row([n_nazwa, n_jednostka]), 
        ft.Row([n_kcal, n_b, n_t, n_w]), 
        ft.ElevatedButton("ZAPISZ PRODUKT", on_click=zapisz_produkt, height=50, bgcolor="green", color="white", style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))
    ], visible=False, expand=True)

    view_profil = ft.Column([
        naglowek_imie,
        ft.Text("USTAWIENIA PROFILU", size=18, weight="bold"), 
        ft.Row([input_nowy_cel, ft.ElevatedButton("Zmień Cel", on_click=zmien_cel, bgcolor="orange", color="white")]), 
        ft.Divider(), 
        ft.Text("ŚLEDZENIE WAGI", size=18, weight="bold"), 
        ft.Row([input_nowa_waga, ft.ElevatedButton("Zapisz Wagę", on_click=dodaj_wage, bgcolor="blue", color="white")]), 
        waga_list
    ], visible=False, expand=True)

    def change_tab(e):
        idx = e.control.selected_index
        view_dziennik.visible = (idx == 0)
        view_baza.visible = (idx == 1)
        view_profil.visible = (idx == 2)
        page.update()

    # DOLNE MENU NAWIGACYJNE
    bottom_nav = ft.NavigationBar(
        destinations=[
            ft.NavigationDestination(icon=ft.Icons.DINNER_DINING, label="Dziennik"),
            ft.NavigationDestination(icon=ft.Icons.ADD_BOX, label="Baza"),
            ft.NavigationDestination(icon=ft.Icons.PERSON, label="Profil"),
        ],
        on_change=change_tab
    )
    
    page.navigation_bar = bottom_nav
    page.add(ft.Row([user_select], alignment="center"), ft.Divider(), view_dziennik, view_baza, view_profil)
    
    load_products(); refresh_all()

port = int(os.environ.get("PORT", 8080))
ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, host="0.0.0.0")
