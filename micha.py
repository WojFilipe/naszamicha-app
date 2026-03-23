import flet as ft
import psycopg2
import os
import datetime
from contextlib import contextmanager

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_jGvTXNQ0ep2y@ep-small-dream-als2k8po-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
)

@contextmanager
def db():
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


POSILKI = ["Śniadanie", "II Śniadanie", "Obiad", "Przekąska", "Kolacja"]


async def main(page: ft.Page):
    page.title = "Nasza Micha"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 15

    init_db()

    st = {"u": None, "d": datetime.date.today()}

    date_txt  = ft.Text("", size=16, weight="bold")
    kcal_txt  = ft.Text("0 / 0 kcal", size=26, weight="bold")
    pb        = ft.ProgressBar(value=0, height=12, color="green")
    b_txt     = ft.Text("B: 0g", color="red")
    t_txt     = ft.Text("T: 0g", color="orange")
    w_txt     = ft.Text("W: 0g", color="blue")
    macro_row = ft.Row([b_txt, t_txt, w_txt], alignment="center")
    log_list  = ft.ListView(expand=True, spacing=5)

    meal_dd = ft.Dropdown(
        label="Posilek",
        options=[ft.dropdown.Option(m) for m in POSILKI],
        value="Obiad",
        expand=True,
    )
    prod_dd = ft.Dropdown(label="Produkt", expand=True)
    amt_in  = ft.TextField(label="G / Szt", width=90, keyboard_type="number")

    n_nazwa = ft.TextField(label="Nazwa produktu", expand=True)
    n_typ   = ft.Dropdown(
        options=[ft.dropdown.Option("100g"), ft.dropdown.Option("szt")],
        value="100g", width=110,
    )
    n_k = ft.TextField(label="Kcal", expand=1)
    n_b = ft.TextField(label="Bialko", expand=1)
    n_t = ft.TextField(label="Tluszcz", expand=1)
    n_w = ft.TextField(label="Wegle", expand=1)

    p_cel     = ft.TextField(label="Nowy cel kcal", expand=True)
    p_waga    = ft.TextField(label="Waga (kg)", expand=True)
    waga_list = ft.ListView(expand=True, spacing=5)

    async def load_prods():
        with db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT nazwa FROM produkty ORDER BY nazwa ASC")
            prod_dd.options = [ft.dropdown.Option(r[0]) for r in cur.fetchall()]
        await page.update_async()

    async def refresh_data():
        if not st["u"]:
            return
        d_str = st["d"].strftime("%Y-%m-%d")
        date_txt.value = d_str

        with db() as conn:
            cur = conn.cursor()

            cur.execute("SELECT cel_kcal FROM profile WHERE user_name=%s", (st["u"],))
            row = cur.fetchone()
            target = row[0] if row else 2000

            cur.execute(
                "SELECT SUM(kcal), SUM(b), SUM(t), SUM(w) FROM dziennik "
                "WHERE user_name=%s AND data=%s",
                (st["u"], d_str),
            )
            res = cur.fetchone()
            k = res[0] or 0
            b = res[1] or 0
            t = res[2] or 0
            w = res[3] or 0

            kcal_txt.value = f"{int(k)} / {int(target)} kcal"
            pb.value = min(k / target, 1.0) if target > 0 else 0
            pb.color = "red" if k > target else "green"
            b_txt.value = f"B: {int(b)}g"
            t_txt.value = f"T: {int(t)}g"
            w_txt.value = f"W: {int(w)}g"

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
                        subtitle=ft.Text(f"{int(r[2])} j.  -  {int(r[3])} kcal"),
                        trailing=ft.IconButton(
                            ft.Icons.DELETE,
                            data=r[0],
                            on_click=delete_item,
                        ),
                    )
                )

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

        await page.update_async()

    async def snack(msg: str):
        page.snack_bar = ft.SnackBar(ft.Text(msg), open=True)
        await page.update_async()

    async def delete_item(e):
        with db() as conn:
            conn.cursor().execute("DELETE FROM dziennik WHERE id=%s", (e.control.data,))
        await refresh_data()

    async def add_meal(e):
        if not prod_dd.value or not amt_in.value:
            await snack("Wybierz produkt i podaj ilosc!")
            return
        try:
            v = float(amt_in.value.replace(",", "."))
        except ValueError:
            await snack("Nieprawidlowa ilosc!")
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
        await refresh_data()

    async def save_prod(e):
        if not n_nazwa.value.strip():
            await snack("Podaj nazwe produktu!")
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
            await snack("Nieprawidlowe wartosci liczbowe!")
            return
        with db() as conn:
            conn.cursor().execute(
                "INSERT INTO produkty VALUES (%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (nazwa) DO UPDATE SET "
                "kcal=EXCLUDED.kcal, b=EXCLUDED.b, t=EXCLUDED.t, "
                "w=EXCLUDED.w, jednostka=EXCLUDED.jednostka",
                vals,
            )
        for f in [n_nazwa, n_k, n_b, n_t, n_w]:
            f.value = ""
        await load_prods()
        await snack("Produkt zapisany!")

    async def save_cel(e):
        if not p_cel.value:
            return
        try:
            cel = float(p_cel.value.replace(",", "."))
        except ValueError:
            await snack("Nieprawidlowa wartosc!")
            return
        with db() as conn:
            conn.cursor().execute(
                "UPDATE profile SET cel_kcal=%s WHERE user_name=%s",
                (cel, st["u"]),
            )
        p_cel.value = ""
        await snack(f"Cel: {int(cel)} kcal")
        await refresh_data()

    async def save_waga(e):
        if not p_waga.value:
            return
        try:
            waga = float(p_waga.value.replace(",", "."))
        except ValueError:
            await snack("Nieprawidlowa waga!")
            return
        with db() as conn:
            conn.cursor().execute(
                "INSERT INTO waga_log VALUES (%s,%s,%s) "
                "ON CONFLICT (user_name, data) DO UPDATE SET waga=EXCLUDED.waga",
                (st["u"], st["d"].strftime("%Y-%m-%d"), waga),
            )
        p_waga.value = ""
        await refresh_data()

    async def change_d(delta):
        st["d"] += datetime.timedelta(days=delta)
        await refresh_data()

    async def login(user: str):
        st["u"] = user
        v_login.visible = False
        v_main.visible  = True
        page.navigation_bar.visible = True
        await load_prods()
        await refresh_data()

    async def logout(_):
        st["u"] = None
        st["d"] = datetime.date.today()
        v_main.visible  = False
        v_login.visible = True
        page.navigation_bar.visible = False
        tab_dziennik.visible = True
        tab_baza.visible     = False
        tab_profil.visible   = False
        page.navigation_bar.selected_index = 0
        await page.update_async()

    v_login = ft.Column(
        [
            ft.Text("Nasza Micha", size=32, weight="bold"),
            ft.Text("Kto gotuje dzis?", size=18),
            ft.Container(height=20),
            ft.FilledButton(
                "Filip",
                on_click=lambda _: login("Filip"),
                height=70,
                width=260,
                style=ft.ButtonStyle(text_style=ft.TextStyle(size=22)),
            ),
            ft.FilledButton(
                "Nikola",
                on_click=lambda _: login("Nikola"),
                height=70,
                width=260,
                style=ft.ButtonStyle(text_style=ft.TextStyle(size=22)),
            ),
        ],
        horizontal_alignment="center",
        alignment="center",
        spacing=16,
        expand=True,
    )

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
                content=ft.Column([kcal_txt, pb, macro_row], horizontal_alignment="center"),
                padding=10,
            ),
            ft.Row([meal_dd, amt_in]),
            prod_dd,
            ft.FilledButton(
                "ZJEDZONE!",
                on_click=add_meal,
                height=45,
            ),
            ft.Divider(),
            log_list,
        ],
        expand=True,
    )

    tab_baza = ft.Column(
        [
            ft.Text("Nowy produkt", size=20, weight="bold"),
            ft.Row([n_nazwa, n_typ]),
            ft.Row([n_k, n_b, n_t, n_w]),
            ft.FilledButton(
                "DODAJ DO BAZY",
                on_click=save_prod,
            ),
        ],
        visible=False,
    )

    tab_profil = ft.Column(
        [
            ft.Text("Profil", size=20, weight="bold"),
            ft.Row([p_cel, ft.IconButton(ft.Icons.SAVE, on_click=save_cel)]),
            ft.Divider(),
            ft.Text("Waga", size=20, weight="bold"),
            ft.Row([p_waga, ft.IconButton(ft.Icons.ADD, on_click=save_waga)]),
            waga_list,
            ft.Divider(),
            ft.TextButton("Wyloguj", on_click=logout),
        ],
        visible=False,
        expand=True,
    )

    tabs = [tab_dziennik, tab_baza, tab_profil]

    async def nav_change(e):
        idx = e.control.selected_index
        for i, tab in enumerate(tabs):
            tab.visible = (i == idx)
        await page.update_async()

    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.BOOK,      label="Dziennik"),
            ft.NavigationBarDestination(icon=ft.Icons.ADD_CIRCLE, label="Baza"),
            ft.NavigationBarDestination(icon=ft.Icons.PERSON,     label="Profil"),
        ],
        on_change=nav_change,
        visible=False,
    )

    v_main = ft.Container(
        content=ft.Column(tabs, expand=True),
        expand=True,
        visible=False,
    )

    await page.add_async(v_login, v_main)


ft.run(main)
