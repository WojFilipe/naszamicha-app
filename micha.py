import flet as ft
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import datetime
from contextlib import contextmanager

# ---------------------------------------------------------------------------
# KONFIGURACJA BAZY
# ---------------------------------------------------------------------------
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_jGvTXNQ0ep2y@ep-small-dream-als2k8po-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
)

@contextmanager
def db():
    """Context manager – połączenie zamykane automatycznie."""
    conn = psycopg2.connect(DB_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS produkty (
                nazwa TEXT PRIMARY KEY,
                kcal REAL, b REAL, t REAL, w REAL,
                jednostka TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dziennik (
                id SERIAL PRIMARY KEY,
                user_name TEXT, data TEXT, posilek TEXT,
                nazwa TEXT, ilosc REAL, jednostka TEXT,
                kcal REAL, b REAL, t REAL, w REAL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                user_name TEXT PRIMARY KEY,
                cel_kcal REAL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS waga_log (
                user_name TEXT, data TEXT, waga REAL,
                PRIMARY KEY (user_name, data)
            )
        """)
        cur.execute("""
            INSERT INTO profile (user_name, cel_kcal)
            VALUES ('Filip', 2500), ('Nikola', 2000)
            ON CONFLICT DO NOTHING
        """)


# ---------------------------------------------------------------------------
# UŻYTKOWNICY I PINY
# ---------------------------------------------------------------------------
USERS = {"Filip": "1111", "Nikola": "2222"}
POSILKI = ["Śniadanie", "II Śniadanie", "Obiad", "Przekąska", "Kolacja"]


# ---------------------------------------------------------------------------
# APLIKACJA
# ---------------------------------------------------------------------------
def main(page: ft.Page):
    page.title = "Nasza Micha v1.0"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 15

    init_db()

    # Stan sesji – ładowany z client_storage dla trwałego logowania
    # Flet 1.0: client_storage → page.session
    saved_user = page.session.get("logged_user")
    st = {
        "u": saved_user,
        "d": datetime.date.today(),
    }

    # -----------------------------------------------------------------------
    # WIDŻETY – DZIENNIK
    # -----------------------------------------------------------------------
    date_txt   = ft.Text("", size=16, weight="bold")
    kcal_txt   = ft.Text("0 / 0 kcal", size=26, weight="bold")
    pb         = ft.ProgressBar(value=0, height=12, color="green")
    b_txt      = ft.Text("B: 0g", color="red")
    t_txt      = ft.Text("T: 0g", color="orange")
    w_txt      = ft.Text("W: 0g", color="blue")
    macro_row  = ft.Row([b_txt, t_txt, w_txt], alignment="center")
    log_list   = ft.ListView(expand=True, spacing=5)

    meal_dd = ft.Dropdown(
        label="Posiłek",
        options=[ft.dropdown.Option(m) for m in POSILKI],
        value="Obiad",
        expand=True,
    )
    prod_dd = ft.Dropdown(label="Produkt", expand=True)
    amt_in  = ft.TextField(label="G/Szt", width=80, keyboard_type="number")

    # -----------------------------------------------------------------------
    # WIDŻETY – BAZA PRODUKTÓW
    # -----------------------------------------------------------------------
    n_nazwa = ft.TextField(label="Nazwa", expand=True)
    n_typ   = ft.Dropdown(
        options=[ft.dropdown.Option("100g"), ft.dropdown.Option("szt")],
        value="100g", width=100,
    )
    n_k = ft.TextField(label="Kcal", expand=1)
    n_b = ft.TextField(label="B",    expand=1)
    n_t = ft.TextField(label="T",    expand=1)
    n_w = ft.TextField(label="W",    expand=1)

    # -----------------------------------------------------------------------
    # WIDŻETY – PROFIL
    # -----------------------------------------------------------------------
    p_cel   = ft.TextField(label="Nowy cel kcal", expand=True)
    p_waga  = ft.TextField(label="Dzisiejsza waga (kg)", expand=True)
    waga_list = ft.ListView(expand=True, spacing=5)

    # -----------------------------------------------------------------------
    # LOGIKA DANYCH
    # -----------------------------------------------------------------------
    def load_prods():
        with db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT nazwa FROM produkty ORDER BY nazwa ASC")
            prod_dd.options = [ft.dropdown.Option(r[0]) for r in cur.fetchall()]
        page.update()

    def refresh_data():
        if not st["u"]:
            return
        d_str = st["d"].strftime("%Y-%m-%d")
        date_txt.value = d_str

        with db() as conn:
            cur = conn.cursor()

            # Cel kalorii
            cur.execute("SELECT cel_kcal FROM profile WHERE user_name=%s", (st["u"],))
            row = cur.fetchone()
            target = row[0] if row else 2000

            # Sumy dnia
            cur.execute(
                "SELECT SUM(kcal), SUM(b), SUM(t), SUM(w) FROM dziennik "
                "WHERE user_name=%s AND data=%s",
                (st["u"], d_str),
            )
            res = cur.fetchone()
            k, b, t, w = (res[0] or 0, res[1] or 0, res[2] or 0, res[3] or 0)

            # Pasek kalorii
            kcal_txt.value = f"{int(k)} / {int(target)} kcal"
            pb.value = min(k / target, 1.0) if target > 0 else 0
            pb.color = "red" if k > target else "green"

            # Makro
            b_txt.value = f"B: {int(b)}g"
            t_txt.value = f"T: {int(t)}g"
            w_txt.value = f"W: {int(w)}g"

            # Lista wpisów
            log_list.controls.clear()
            cur.execute(
                "SELECT id, nazwa, ilosc, kcal, posilek FROM dziennik "
                "WHERE user_name=%s AND data=%s ORDER BY id DESC",
                (st["u"], d_str),
            )
            for r in cur.fetchall():
                log_list.controls.append(
                    ft.ListTile(
                        title=ft.Text(f"{r[1]}  ({r[4]})"),
                        subtitle=ft.Text(f"{int(r[2])} j.  –  {int(r[3])} kcal"),
                        trailing=ft.IconButton(
                            ft.Icons.DELETE,
                            data=r[0],
                            on_click=delete_item,
                        ),
                    )
                )

            # Historia wagi
            waga_list.controls.clear()
            cur.execute(
                "SELECT data, waga FROM waga_log "
                "WHERE user_name=%s ORDER BY data DESC LIMIT 10",
                (st["u"],),
            )
            for rw in cur.fetchall():
                waga_list.controls.append(
                    ft.ListTile(
                        title=ft.Text(f"{rw[1]} kg"),
                        subtitle=ft.Text(rw[0]),
                    )
                )

        page.update()

    # -----------------------------------------------------------------------
    # OBSŁUGA ZDARZEŃ
    # -----------------------------------------------------------------------
    def delete_item(e):
        with db() as conn:
            conn.cursor().execute("DELETE FROM dziennik WHERE id=%s", (e.control.data,))
        refresh_data()

    def add_meal(e):
        if not prod_dd.value or not amt_in.value:
            page.open(ft.SnackBar(ft.Text("Wybierz produkt i podaj ilość!")))
            return
        try:
            v = float(amt_in.value.replace(",", "."))
        except ValueError:
            page.open(ft.SnackBar(ft.Text("Nieprawidłowa ilość!")))
            return

        with db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT kcal, b, t, w, jednostka FROM produkty WHERE nazwa=%s",
                (prod_dd.value,),
            )
            p = cur.fetchone()
            if not p:
                return
            m = v / 100 if p[4] == "100g" else v
            cur.execute(
                "INSERT INTO dziennik "
                "(user_name, data, posilek, nazwa, ilosc, jednostka, kcal, b, t, w) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (st["u"], st["d"].strftime("%Y-%m-%d"), meal_dd.value,
                 prod_dd.value, v, p[4],
                 p[0]*m, p[1]*m, p[2]*m, p[3]*m),
            )
        amt_in.value = ""
        refresh_data()

    def save_prod(e):
        if not n_nazwa.value:
            page.open(ft.SnackBar(ft.Text("Podaj nazwę produktu!")))
            return
        try:
            vals = (
                n_nazwa.value.strip(),
                float(n_k.value or 0),
                float(n_b.value or 0),
                float(n_t.value or 0),
                float(n_w.value or 0),
                n_typ.value,
            )
        except ValueError:
            page.open(ft.SnackBar(ft.Text("Nieprawidłowe wartości!")))
            return

        with db() as conn:
            conn.cursor().execute(
                "INSERT INTO produkty VALUES (%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (nazwa) DO UPDATE SET "
                "kcal=EXCLUDED.kcal, b=EXCLUDED.b, t=EXCLUDED.t, "
                "w=EXCLUDED.w, jednostka=EXCLUDED.jednostka",
                vals,
            )
        for field in [n_nazwa, n_k, n_b, n_t, n_w]:
            field.value = ""
        load_prods()
        page.open(ft.SnackBar(ft.Text("✅ Produkt dodany!")))

    def save_cel(e):
        if not p_cel.value:
            return
        try:
            cel = float(p_cel.value.replace(",", "."))
        except ValueError:
            page.open(ft.SnackBar(ft.Text("Nieprawidłowa wartość!")))
            return
        with db() as conn:
            conn.cursor().execute(
                "UPDATE profile SET cel_kcal=%s WHERE user_name=%s",
                (cel, st["u"]),
            )
        p_cel.value = ""
        page.open(ft.SnackBar(ft.Text(f"✅ Cel ustawiony: {int(cel)} kcal")))
        refresh_data()

    def save_waga(e):
        if not p_waga.value:
            return
        try:
            waga = float(p_waga.value.replace(",", "."))
        except ValueError:
            page.open(ft.SnackBar(ft.Text("Nieprawidłowa waga!")))
            return
        with db() as conn:
            conn.cursor().execute(
                "INSERT INTO waga_log VALUES (%s,%s,%s) "
                "ON CONFLICT (user_name, data) DO UPDATE SET waga=EXCLUDED.waga",
                (st["u"], st["d"].strftime("%Y-%m-%d"), waga),
            )
        p_waga.value = ""
        refresh_data()

    def change_d(delta):
        st["d"] += datetime.timedelta(days=delta)
        refresh_data()

    # -----------------------------------------------------------------------
    # LOGOWANIE I WYLOGOWANIE
    # -----------------------------------------------------------------------
    u_in = ft.Dropdown(
        label="Użytkownik",
        options=[ft.dropdown.Option(u) for u in USERS],
    )
    p_in = ft.TextField(label="PIN", password=True, keyboard_type="number")

    def do_login(user: str):
        st["u"] = user
        page.session.set("logged_user", user)
        v_login.visible = False
        v_main.visible  = True
        page.navigation_bar.visible = True
        load_prods()
        refresh_data()

    def login(e):
        user = u_in.value
        pin  = p_in.value
        if user in USERS and USERS[user] == pin:
            do_login(user)
        else:
            page.open(ft.SnackBar(ft.Text("❌ Błędny PIN!")))
        page.update()

    def logout(_):
        st["u"] = None
        page.session.remove("logged_user")
        v_main.visible  = False
        v_login.visible = True
        page.navigation_bar.visible = False
        u_in.value = None
        p_in.value = ""
        page.update()

    # -----------------------------------------------------------------------
    # WIDOK LOGOWANIA
    # -----------------------------------------------------------------------
    v_login = ft.Column(
        [
            ft.Text("🍽️ NASZA MICHA", size=30, weight="bold", color="blue400"),
            ft.Text("Zaloguj się", size=16),
            u_in,
            p_in,
            ft.ElevatedButton("WEJDŹ", on_click=login, height=50, expand=True),
        ],
        horizontal_alignment="center",
        spacing=15,
    )

    # -----------------------------------------------------------------------
    # ZAKŁADKI GŁÓWNE
    # -----------------------------------------------------------------------
    tab_dziennik = ft.Column(
        [
            ft.Row(
                [
                    ft.IconButton(ft.Icons.ARROW_BACK,    on_click=lambda _: change_d(-1)),
                    date_txt,
                    ft.IconButton(ft.Icons.ARROW_FORWARD, on_click=lambda _: change_d(1)),
                ],
                alignment="center",
            ),
            ft.Container(
                content=ft.Column(
                    [kcal_txt, pb, macro_row],
                    horizontal_alignment="center",
                ),
                padding=10,
            ),
            ft.Row([meal_dd, amt_in]),
            prod_dd,
            ft.ElevatedButton(
                "➕ ZJEDZONE!",
                on_click=add_meal,
                bgcolor="blue",
                color="white",
                height=45,
            ),
            ft.Divider(),
            log_list,
        ],
        expand=True,
    )

    tab_baza = ft.Column(
        [
            ft.Text("➕ NOWY PRODUKT", size=20, weight="bold"),
            ft.Row([n_nazwa, n_typ]),
            ft.Row([n_k, n_b, n_t, n_w]),
            ft.ElevatedButton(
                "DODAJ DO BAZY",
                on_click=save_prod,
                bgcolor="green",
                color="white",
            ),
        ],
    )

    tab_profil = ft.Column(
        [
            ft.Text("⚙️ PROFIL", size=20, weight="bold"),
            ft.Row([p_cel, ft.IconButton(ft.Icons.SAVE, on_click=save_cel)]),
            ft.Divider(),
            ft.Text("⚖️ WAGA", size=20, weight="bold"),
            ft.Row([p_waga, ft.IconButton(ft.Icons.ADD, on_click=save_waga)]),
            waga_list,
            ft.Divider(),
            ft.TextButton("🚪 WYLOGUJ", on_click=logout),
        ],
        expand=True,
    )

    # -----------------------------------------------------------------------
    # NAWIGACJA – poprawna obsługa przełączania zakładek
    # -----------------------------------------------------------------------
    tabs = [tab_dziennik, tab_baza, tab_profil]

    def nav_change(e):
        idx = e.control.selected_index
        for i, tab in enumerate(tabs):
            tab.visible = (i == idx)
        page.update()

    # Wszystkie zakładki w jednym kontenerze
    tabs_container = ft.Column(tabs, expand=True)
    # Ukryj zakładki 1 i 2 na starcie
    tab_baza.visible   = False
    tab_profil.visible = False

    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.BOOK,       label="Dziennik"),
            ft.NavigationBarDestination(icon=ft.Icons.ADD_CIRCLE,  label="Baza"),
            ft.NavigationBarDestination(icon=ft.Icons.PERSON,      label="Profil"),
        ],
        on_change=nav_change,
        visible=False,
    )

    v_main = ft.Container(content=tabs_container, expand=True, visible=False)

    page.add(v_login, v_main)

    # -----------------------------------------------------------------------
    # AUTO-LOGIN – jeśli user jest już w client_storage
    # -----------------------------------------------------------------------
    if st["u"] in USERS:
        do_login(st["u"])
    else:
        load_prods()


ft.app(
    target=main,
    view=ft.AppView.WEB_BROWSER,
    port=int(os.environ.get("PORT", 8080)),
    host="0.0.0.0",
)
