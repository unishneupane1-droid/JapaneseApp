import streamlit as st
from supabase import create_client
from datetime import date, timedelta

# Optional calendar libraries
try:
    import nepali_datetime
except ImportError:
    nepali_datetime = None

try:
    import jpholiday
except ImportError:
    jpholiday = None


# --------------------------------------------------
# 1. SUPABASE CONNECTION
# --------------------------------------------------

SUPABASE_URL = "https://ixcmqzwqmdlsemaagjjy.supabase.co"
SUPABASE_KEY = "sb_publishable_-0FW1-_GLoBs7fuLZMJ2xw_GlbcfazP"

st.set_page_config(
    page_title="Japanese - Nepali App",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Japanese - Nepali App")
st.caption("जापानी शब्द, नेपाली अर्थ, नोट र क्यालेन्डर")


@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


try:
    if "sb" not in st.session_state:
        st.session_state.sb = get_supabase()

    sb = st.session_state.sb

except Exception as e:
    st.error("Supabase connection हुन सकेन। URL र API key जाँच गर।")
    st.code(str(e))
    st.stop()


# --------------------------------------------------
# 2. LOGIN / SIGNUP
# --------------------------------------------------

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "user_email" not in st.session_state:
    st.session_state.user_email = ""


if not st.session_state.user_id:
    login_tab, signup_tab = st.tabs(
        ["🔐 Login", "🆕 नयाँ Account"]
    )

    with login_tab:
        st.subheader("आफ्नो Account मा Login गर")

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input(
                "Password",
                type="password"
            )
            login_button = st.form_submit_button(
                "Login",
                use_container_width=True
            )

        if login_button:
            try:
                result = sb.auth.sign_in_with_password({
                    "email": email.strip(),
                    "password": password
                })

                if result.user:
                    st.session_state.user_id = result.user.id
                    st.session_state.user_email = result.user.email or email
                    st.success("Login सफल भयो!")
                    st.rerun()
                else:
                    st.error("Login हुन सकेन। विवरण जाँच गर।")

            except Exception as e:
                st.error("Login हुन सकेन। Email र password जाँच गर।")
                st.caption(str(e))

    with signup_tab:
        st.subheader("नयाँ Account बनाऊ")

        with st.form("signup_form"):
            new_email = st.text_input("आफ्नो Email")
            new_password = st.text_input(
                "Password बनाऊ",
                type="password"
            )
            confirm_password = st.text_input(
                "Password फेरि लेख",
                type="password"
            )

            signup_button = st.form_submit_button(
                "Account बनाउने",
                use_container_width=True
            )

        if signup_button:
            if not new_email.strip():
                st.warning("Email लेख।")
            elif len(new_password) < 6:
                st.warning("Password कम्तीमा 6 अक्षरको राख।")
            elif new_password != confirm_password:
                st.warning("दुवै password मिलेनन्।")
            else:
                try:
                    result = sb.auth.sign_up({
                        "email": new_email.strip(),
                        "password": new_password
                    })

                    if result.session and result.user:
                        st.session_state.user_id = result.user.id
                        st.session_state.user_email = (
                            result.user.email or new_email
                        )
                        st.success("Account बन्यो!")
                        st.rerun()
                    else:
                        st.success(
                            "Account बनाउने अनुरोध सफल भयो। "
                            "Email confirmation मागिएको छ भने email खोलेर "
                            "confirm गर, त्यसपछि Login गर।"
                        )

                except Exception as e:
                    st.error(
                        "Account बनाउन सकिएन। Email, password र "
                        "Supabase Auth settings जाँच गर।"
                    )
                    st.caption(str(e))

    st.info(
        "Login गरेपछि मात्र आफ्नो शब्द, नोट र क्यालेन्डर हेर्न मिल्छ।"
    )
    st.stop()


# --------------------------------------------------
# 3. LOGGED-IN USER
# --------------------------------------------------

user_id = st.session_state.user_id

st.sidebar.success("Login भएको छ")
st.sidebar.write(st.session_state.user_email)

if st.sidebar.button("🚪 Logout", use_container_width=True):
    try:
        sb.auth.sign_out()
    except Exception:
        pass

    st.session_state.user_id = None
    st.session_state.user_email = ""
    st.rerun()


# --------------------------------------------------
# 4. MAIN TABS
# --------------------------------------------------

words_tab, notes_tab, calendar_tab = st.tabs([
    "📖 शब्दकोश",
    "📝 मेरा नोटहरू",
    "📅 क्यालेन्डर"
])


# --------------------------------------------------
# 5. JAPANESE - NEPALI DICTIONARY
# --------------------------------------------------

with words_tab:
    st.header("📖 Japanese - Nepali Dictionary")

    st.write(
        "जापानी शब्द, हिरागाना र नेपाली अर्थ थप, खोज, सच्याऊ वा हटाऊ।"
    )

    add_tab, bulk_tab = st.tabs([
        "➕ एउटा शब्द थप्ने",
        "📥 धेरै शब्द एकैपटक थप्ने"
    ])

    # Add one word
    with add_tab:
        with st.form("add_single_word_form"):
            japanese = st.text_input(
                "Japanese / Kanji",
                placeholder="例：先生"
            )
            hiragana = st.text_input(
                "Hiragana",
                placeholder="せんせい"
            )
            meaning = st.text_input(
                "नेपाली अर्थ",
                placeholder="शिक्षक"
            )

            add_button = st.form_submit_button(
                "💾 शब्द सुरक्षित गर्ने",
                use_container_width=True
            )

        if add_button:
            if not japanese.strip() or not meaning.strip():
                st.warning("Japanese शब्द र नेपाली अर्थ लेख।")
            else:
                try:
                    existing = (
                        sb.table("words")
                        .select("id")
                        .eq("user_id", user_id)
                        .eq("japanese", japanese.strip())
                        .execute()
                    )

                    if existing.data:
                        st.warning(
                            "यो Japanese शब्द पहिले नै छ। "
                            "तलको Search बाट खोजेर Edit गर्न सक्छौ।"
                        )
                    else:
                        sb.table("words").insert({
                            "user_id": user_id,
                            "japanese": japanese.strip(),
                            "hiragana": hiragana.strip(),
                            "meaning": meaning.strip()
                        }).execute()

                        st.success("शब्द सुरक्षित भयो!")
                        st.rerun()

                except Exception as e:
                    st.error("शब्द सुरक्षित भएन। Database जाँच गर।")
                    st.caption(str(e))

    # Bulk add
    with bulk_tab:
        st.write(
            "Word वा Excel बाट 3 वटा column copy गरेर यहाँ paste गर।"
        )
        st.caption(
            "क्रम: Japanese → Hiragana → नेपाली अर्थ। "
            "प्रत्येक शब्द नयाँ line मा राख।"
        )

        bulk_text = st.text_area(
            "धेरै शब्द यहाँ paste गर",
            placeholder=(
                "先生\tせんせい\tशिक्षक\n"
                "学校\tがっこう\tविद्यालय\n"
                "友達\tともだち\tसाथी"
            ),
            height=220,
            key="bulk_words_text"
        )

        if st.button(
            "📥 सबै शब्द सुरक्षित गर्ने",
            key="bulk_save_button",
            use_container_width=True
        ):
            if not bulk_text.strip():
                st.warning("पहिले शब्दहरू paste गर।")
            else:
                added = 0
                skipped = 0
                failed = 0

                lines = bulk_text.strip().splitlines()

                progress = st.progress(0)

                for index, line in enumerate(lines):
                    # Excel / Word tab-separated columns
                    if "\t" in line:
                        parts = line.split("\t")
                    elif "|" in line:
                        parts = line.split("|")
                    else:
                        skipped += 1
                        progress.progress((index + 1) / len(lines))
                        continue

                    parts = [part.strip() for part in parts]

                    if len(parts) < 3:
                        skipped += 1
                        progress.progress((index + 1) / len(lines))
                        continue

                    jp, hira, nepali_meaning = parts[0:3]

                    if not jp or not nepali_meaning:
                        skipped += 1
                        progress.progress((index + 1) / len(lines))
                        continue

                    try:
                        existing = (
                            sb.table("words")
                            .select("id")
                            .eq("user_id", user_id)
                            .eq("japanese", jp)
                            .execute()
                        )

                        if existing.data:
                            skipped += 1
                        else:
                            sb.table("words").insert({
                                "user_id": user_id,
                                "japanese": jp,
                                "hiragana": hira,
                                "meaning": nepali_meaning
                            }).execute()
                            added += 1

                    except Exception:
                        failed += 1

                    progress.progress((index + 1) / len(lines))

                st.success(f"थपिएका शब्द: {added}")
                st.info(f"छोडिएका / दोहोरिएका / नमिलेका line: {skipped}")

                if failed:
                    st.error(
                        f"सुरक्षित हुन नसकेका शब्द: {failed}. "
                        "Database permission वा connection जाँच गर।"
                    )

                if added:
                    st.rerun()

    st.divider()

    # Search dictionary
    st.subheader("🔎 शब्द खोज्ने")

    search_text = st.text_input(
        "Japanese, Hiragana वा नेपाली अर्थ लेख",
        placeholder="उदाहरण: शिक्षक / せんせい / 先生",
        key="dictionary_search"
    )

    try:
        response = (
            sb.table("words")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        all_words = response.data or []

        if search_text.strip():
            search_lower = search_text.strip().casefold()

            filtered_words = [
                word for word in all_words
                if search_lower in str(word.get("japanese", "")).casefold()
                or search_lower in str(word.get("hiragana", "")).casefold()
                or search_lower in str(word.get("meaning", "")).casefold()
            ]
        else:
            filtered_words = all_words

        st.write(
            f"जम्मा शब्द: {len(all_words)} | "
            f"देखाइएका शब्द: {len(filtered_words)}"
        )

        if not filtered_words:
            st.info("शब्द भेटिएन। नयाँ शब्द थप वा Search बदल।")

        for word in filtered_words:
            word_id = word["id"]

            jp = word.get("japanese", "")
            hira = word.get("hiragana", "")
            nepali_meaning = word.get("meaning", "")

            with st.expander(
                f"📘 {jp} — {nepali_meaning}"
            ):
                st.write(f"**Japanese:** {jp}")
                st.write(f"**Hiragana:** {hira}")
                st.write(f"**नेपाली अर्थ:** {nepali_meaning}")

                st.markdown("#### ✏️ शब्द वा अर्थ सच्याउने")

                with st.form(f"edit_word_{word_id}"):
                    edited_jp = st.text_input(
                        "Japanese",
                        value=jp,
                        key=f"edit_jp_{word_id}"
                    )
                    edited_hira = st.text_input(
                        "Hiragana",
                        value=hira,
                        key=f"edit_hira_{word_id}"
                    )
                    edited_meaning = st.text_input(
                        "नेपाली अर्थ",
                        value=nepali_meaning,
                        key=f"edit_meaning_{word_id}"
                    )

                    edit_button = st.form_submit_button(
                        "💾 परिवर्तन सुरक्षित गर्ने"
                    )

                if edit_button:
                    if not edited_jp.strip() or not edited_meaning.strip():
                        st.warning(
                            "Japanese शब्द र नेपाली अर्थ खाली नराख।"
                        )
                    else:
                        try:
                            sb.table("words").update({
                                "japanese": edited_jp.strip(),
                                "hiragana": edited_hira.strip(),
                                "meaning": edited_meaning.strip()
                            }).eq(
                                "id", word_id
                            ).eq(
                                "user_id", user_id
                            ).execute()

                            st.success("परिवर्तन सुरक्षित भयो!")
                            st.rerun()

                        except Exception as e:
                            st.error("शब्द सच्याउन सकिएन।")
                            st.caption(str(e))

                st.markdown("#### 🗑️ शब्द हटाउने")

                confirm_delete = st.checkbox(
                    "यो शब्द हटाउन चाहन्छु",
                    key=f"confirm_delete_{word_id}"
                )

                if st.button(
                    "🗑️ Delete",
                    key=f"delete_word_{word_id}",
                    disabled=not confirm_delete
                ):
                    try:
                        sb.table("words").delete().eq(
                            "id", word_id
                        ).eq(
                            "user_id", user_id
                        ).execute()

                        st.success("शब्द हटाइयो।")
                        st.rerun()

                    except Exception as e:
                        st.error("शब्द हटाउन सकिएन।")
                        st.caption(str(e))

    except Exception as e:
        st.error(
            "Dictionary खोल्न सकिएन। Supabase को words table "
            "र permissions जाँच गर।"
        )
        st.caption(str(e))


# --------------------------------------------------
# 6. PERSONAL NOTES
# --------------------------------------------------

with notes_tab:
    st.header("📝 मेरा नोटहरू")

    st.write(
        "आफ्नो पढाइ, Japanese grammar, class notes वा अरू जानकारी लेखेर सुरक्षित गर।"
    )

    with st.form("add_note_form"):
        note_title = st.text_input(
            "नोटको शीर्षक",
            placeholder="उदाहरण: Japanese Grammar"
        )
        note_content = st.text_area(
            "नोट लेख",
            placeholder="यहाँ आफ्ना नोटहरू लेख...",
            height=180
        )

        save_note_button = st.form_submit_button(
            "💾 नोट सुरक्षित गर्ने",
            use_container_width=True
        )

    if save_note_button:
        if not note_title.strip() or not note_content.strip():
            st.warning("शीर्षक र नोट दुवै लेख।")
        else:
            try:
                sb.table("notes").insert({
                    "user_id": user_id,
                    "title": note_title.strip(),
                    "content": note_content.strip()
                }).execute()

                st.success("नोट सुरक्षित भयो!")
                st.rerun()

            except Exception as e:
                st.error(
                    "नोट सुरक्षित भएन। Supabase मा notes table "
                    "बनाइएको छ कि छैन जाँच गर।"
                )
                st.caption(str(e))

    st.divider()
    st.subheader("📚 सुरक्षित गरिएका नोटहरू")

    try:
        notes_response = (
            sb.table("notes")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        all_notes = notes_response.data or []

        if not all_notes:
            st.info("अहिलेसम्म कुनै नोट छैन।")

        for note in all_notes:
            note_id = note["id"]

            with st.expander(
                f"📝 {note.get('title', 'शीर्षक छैन')}"
            ):
                with st.form(f"edit_note_{note_id}"):
                    edited_title = st.text_input(
                        "शीर्षक",
                        value=note.get("title", ""),
                        key=f"note_title_{note_id}"
                    )
                    edited_content = st.text_area(
                        "नोट",
                        value=note.get("content", ""),
                        height=180,
                        key=f"note_content_{note_id}"
                    )

                    update_note_button = st.form_submit_button(
                        "💾 नोट सच्याउने"
                    )

                if update_note_button:
                    if not edited_title.strip() or not edited_content.strip():
                        st.warning("शीर्षक र नोट खाली नराख।")
                    else:
                        try:
                            sb.table("notes").update({
                                "title": edited_title.strip(),
                                "content": edited_content.strip()
                            }).eq(
                                "id", note_id
                            ).eq(
                                "user_id", user_id
                            ).execute()

                            st.success("नोट परिवर्तन भयो!")
                            st.rerun()

                        except Exception as e:
                            st.error("नोट परिवर्तन हुन सकेन।")
                            st.caption(str(e))

                delete_note_confirm = st.checkbox(
                    "यो नोट हटाउन चाहन्छु",
                    key=f"delete_note_confirm_{note_id}"
                )

                if st.button(
                    "🗑️ नोट Delete",
                    key=f"delete_note_{note_id}",
                    disabled=not delete_note_confirm
                ):
                    try:
                        sb.table("notes").delete().eq(
                            "id", note_id
                        ).eq(
                            "user_id", user_id
                        ).execute()

                        st.success("नोट हटाइयो।")
                        st.rerun()

                    except Exception as e:
                        st.error("नोट हटाउन सकिएन।")
                        st.caption(str(e))

    except Exception as e:
        st.error("नोटहरू खोल्न सकिएन। Database जाँच गर।")
        st.caption(str(e))


# --------------------------------------------------
# 7. CALENDAR
# --------------------------------------------------

with calendar_tab:
    st.header("📅 क्यालेन्डर")

    today = date.today()

    st.write(f"**आजको English Date:** {today.strftime('%Y-%m-%d')}")

    if nepali_datetime is not None:
        try:
            bs_today = nepali_datetime.date.today()

            st.write(
                f"**आजको नेपाली मिति:** "
                f"{bs_today.year}/{bs_today.month}/{bs_today.day}"
            )

        except Exception:
            st.info(
                "नेपाली मिति देखाउन समस्या भयो। "
                "nepali_datetime package जाँच गर।"
            )
    else:
        st.info(
            "नेपाली मिति देखाउन तलको install command चलाउनुपर्छ।"
        )

    if jpholiday is not None:
        try:
            if jpholiday.is_holiday(today):
                holiday_name = jpholiday.is_holiday_name(today)
                st.success(f"🇯🇵 आज जापानमा सार्वजनिक बिदा: {holiday_name}")
            else:
                st.write("🇯🇵 आज जापानको सार्वजनिक बिदा होइन।")
        except Exception:
            st.info("जापानको बिदा जाँच गर्न सकिएन।")
    else:
        st.info(
            "जापानका सार्वजनिक बिदा देखाउन jpholiday package install गर।"
        )

    st.divider()
    st.subheader("📆 मिति छानेर हेर्ने")

    selected_date = st.date_input(
        "English date छान",
        value=today,
        key="calendar_selected_date"
    )

    st.write(
        f"**छानिएको मिति:** {selected_date.strftime('%A, %Y-%m-%d')}"
    )

    if nepali_datetime is not None:
        try:
            bs_selected = nepali_datetime.date.from_datetime_date(
                selected_date
            )

            st.write(
                f"**नेपाली मिति:** "
                f"{bs_selected.year}/{bs_selected.month}/{bs_selected.day}"
            )
        except Exception:
            st.caption("यो मितिको नेपाली मिति देखाउन सकिएन।")

    if jpholiday is not None:
        try:
            if jpholiday.is_holiday(selected_date):
                st.success(
                    "🇯🇵 जापानको सार्वजनिक बिदा: "
                    + str(jpholiday.is_holiday_name(selected_date))
                )
            else:
                st.write("🇯🇵 जापानको सार्वजनिक बिदा होइन।")
        except Exception:
            pass

    st.caption(
        "नोट: यो संस्करणमा English date, नेपाली मिति र जापानका "
        "सार्वजनिक बिदा देखिन्छन्। नेपाली चाडपर्वको छुट्टै सूची "
        "अझै थपिएको छैन।"
    )


# --------------------------------------------------
# 8. FOOTER
# --------------------------------------------------

st.divider()
st.caption(
    "Japanese - Nepali App | आफ्नो Account को data मात्र देखाइन्छ।"
)