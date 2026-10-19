import streamlit as st
from supabase import create_client
from datetime import date, datetime, timedelta
import calendar
import io
import json
import os
import requests
import feedparser

try:
    import nepali_datetime
except ImportError:
    nepali_datetime = None

try:
    import jpholiday
except ImportError:
    jpholiday = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# --------------------------------------------------
# 1. APP CONFIGURATION / SUPABASE
# --------------------------------------------------
st.set_page_config(
    page_title="Japanese Nepali Learning Hub",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

SUPABASE_URL = st.secrets.get(
    "SUPABASE_URL", "https://ixcmqzwqmdlsemaagjjy.supabase.co"
)
SUPABASE_KEY = st.secrets.get(
    "SUPABASE_KEY", "sb_publishable_-0FW1-_GLoBs7fuLZMJ2xw_GlbcfazP"
)

st.markdown("""
<style>
.block-container {max-width: 1500px; padding-top: 1.2rem; padding-bottom: 2rem;}
.stTextArea textarea {font-size: 16px !important; line-height: 1.6 !important; min-height: 420px;}
/* Large, comfortable writing area for notes */
[data-testid="stTextArea"] textarea {min-height: 420px !important;}
.note-editor textarea {min-height: 68vh !important; font-size: 17px !important; line-height: 1.65 !important;}
.stTextInput input {font-size: 16px !important;}
[data-testid="stTabs"] button {font-size: 15px; white-space: normal;}
.small-muted {font-size: 0.85rem; opacity: .8;}
</style>
""", unsafe_allow_html=True)

st.title("📚 Japanese Nepali Learning Hub")
st.caption("Dictionary • Notes • Calendar • JLPT N3 • Currency • News • Documents • AI Assistant")

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    sb = get_supabase()
except Exception as e:
    st.error("Supabase connection हुन सकेन। URL र API key जाँच गर।")
    st.code(str(e))
    st.stop()


# --------------------------------------------------
# 2. LOGIN / SIGNUP (existing login preserved)
# --------------------------------------------------
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if not st.session_state.user_id:
    login_tab, signup_tab = st.tabs(["🔐 Login", "🆕 नयाँ Account"])

    with login_tab:
        st.subheader("आफ्नो Account मा Login गर")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login", use_container_width=True)
        if login_button:
            try:
                result = sb.auth.sign_in_with_password({
                    "email": email.strip(), "password": password
                })
                if result.user:
                    st.session_state.user_id = result.user.id
                    st.session_state.user_email = result.user.email or email
                    st.rerun()
                else:
                    st.error("Login हुन सकेन। Email र password जाँच गर।")
            except Exception:
                st.error("Login हुन सकेन। Email र password जाँच गर।")

    with signup_tab:
        st.subheader("नयाँ Account बनाऊ")
        with st.form("signup_form"):
            new_email = st.text_input("आफ्नो Email")
            new_password = st.text_input("Password बनाऊ", type="password")
            confirm_password = st.text_input("Password फेरि लेख", type="password")
            signup_button = st.form_submit_button("Account बनाउने", use_container_width=True)
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
                        "email": new_email.strip(), "password": new_password
                    })
                    if result.session and result.user:
                        st.session_state.user_id = result.user.id
                        st.session_state.user_email = result.user.email or new_email
                        st.success("Account बन्यो!")
                        st.rerun()
                    else:
                        st.success("Account अनुरोध सफल भयो। Email confirmation आएमा confirm गरेर Login गर।")
                except Exception:
                    st.error("Account बनाउन सकिएन। Email, password र Supabase Auth settings जाँच गर।")

    st.info("Login गरेपछि मात्र आफ्नो शब्द, नोट र कागजात हेर्न मिल्छ।")
    st.stop()

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
# Helpers
# --------------------------------------------------
def safe_table_select(table, columns="*", order_col="created_at"):
    try:
        q = sb.table(table).select(columns).eq("user_id", user_id)
        if order_col:
            q = q.order(order_col, desc=True)
        return q.execute().data or []
    except Exception:
        return None

def month_names(month_num):
    english = calendar.month_name[month_num]
    japanese = ["", "1月", "2月", "3月", "4月", "5月", "6月",
                "7月", "8月", "9月", "10月", "11月", "12月"][month_num]
    nepali = ["", "जनवरी", "फेब्रुअरी", "मार्च", "अप्रिल", "मे", "जुन",
              "जुलाई", "अगस्ट", "सेप्टेम्बर", "अक्टोबर", "नोभेम्बर", "डिसेम्बर"][month_num]
    return nepali, english, japanese

def get_bs_date(gregorian_date):
    if nepali_datetime is None:
        return None
    try:
        return nepali_datetime.date.from_datetime_date(gregorian_date)
    except Exception:
        return None

# --------------------------------------------------
# 3. MAIN SECTIONS
# --------------------------------------------------
words_tab, notes_tab, calendar_tab, kanji_tab, currency_tab, news_tab, docs_tab, ai_tab, private_tab = st.tabs([
    "📖 Dictionary", "📝 My Notes", "📅 Calendar", "🈶 JLPT N3",
    "💱 Currency Converter", "📰 News", "📎 My Documents", "🤖 AI Assistant", "🔒 Private Folder"
])


# --------------------------------------------------
# 4. DICTIONARY (existing words table/columns preserved)
# --------------------------------------------------
with words_tab:
    st.header("📖 Japanese - Nepali Dictionary")
    st.write("Japanese, Hiragana र नेपाली अर्थ थप, खोज, सच्याऊ वा हटाऊ।")

    add_tab, bulk_tab = st.tabs(["➕ एउटा शब्द थप्ने", "📥 धेरै शब्द एकैपटक थप्ने"])
    with add_tab:
        with st.form("add_single_word_form"):
            japanese = st.text_input("Japanese / Kanji", placeholder="例：先生")
            hiragana = st.text_input("Hiragana", placeholder="せんせい")
            meaning = st.text_input("नेपाली अर्थ", placeholder="शिक्षक")
            example = st.text_input("उदाहरण वाक्य (optional)", placeholder="先生、おはようございます。")
            add_button = st.form_submit_button("💾 शब्द सुरक्षित गर्ने", use_container_width=True)
        if add_button:
            if not japanese.strip() or not meaning.strip():
                st.warning("Japanese शब्द र नेपाली अर्थ लेख।")
            else:
                try:
                    existing = sb.table("words").select("id").eq("user_id", user_id).eq("japanese", japanese.strip()).execute()
                    if existing.data:
                        st.warning("यो शब्द पहिले नै छ। Search गरेर Edit गर्न सक्छौ।")
                    else:
                        row = {
                            "user_id": user_id,
                            "japanese": japanese.strip(),
                            "hiragana": hiragana.strip(),
                            "meaning_ne": meaning.strip()
                        }
                        # Save example only if the existing table has that column.
                        if example.strip():
                            try:
                                sb.table("words").insert({**row, "example": example.strip()}).execute()
                            except Exception:
                                sb.table("words").insert(row).execute()
                        else:
                            sb.table("words").insert(row).execute()
                        st.success("शब्द सुरक्षित भयो!")
                        st.rerun()
                except Exception as e:
                    st.error("शब्द सुरक्षित भएन। Database को words table/permission जाँच गर।")
                    st.caption(str(e))

    with bulk_tab:
        st.caption("प्रत्येक लाइनमा Japanese, Hiragana, नेपाली अर्थ — Tab वा | ले छुट्याऊ।")
        bulk_text = st.text_area("धेरै शब्द यहाँ paste गर", placeholder="先生\tせんせい\tशिक्षक\n学校\tがっこう\tविद्यालय", height=240, key="bulk_words_text")
        if st.button("📥 सबै शब्द सुरक्षित गर्ने", key="bulk_save_button", use_container_width=True):
            if not bulk_text.strip():
                st.warning("पहिले शब्दहरू paste गर।")
            else:
                added = skipped = failed = 0
                lines = bulk_text.strip().splitlines()
                progress = st.progress(0)
                for i, line in enumerate(lines):
                    parts = line.split("\t") if "\t" in line else line.split("|")
                    parts = [p.strip() for p in parts]
                    if len(parts) < 3 or not parts[0] or not parts[2]:
                        skipped += 1
                    else:
                        jp, hira, nepali_meaning = parts[:3]
                        try:
                            existing = sb.table("words").select("id").eq("user_id", user_id).eq("japanese", jp).execute()
                            if existing.data:
                                skipped += 1
                            else:
                                sb.table("words").insert({
                                    "user_id": user_id, "japanese": jp,
                                    "hiragana": hira, "meaning_ne": nepali_meaning
                                }).execute()
                                added += 1
                        except Exception:
                            failed += 1
                    progress.progress((i + 1) / len(lines))
                st.success(f"थपिएका शब्द: {added} | छोडिएका/दोहोरिएका: {skipped} | असफल: {failed}")
                if added:
                    st.rerun()

    st.divider()
    search_text = st.text_input("🔎 Japanese, Hiragana वा नेपाली अर्थ खोज", key="dictionary_search")
    try:
        all_words = sb.table("words").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data or []
        filtered_words = all_words
        if search_text.strip():
            s = search_text.strip().casefold()
            filtered_words = [w for w in all_words if any(
                s in str(w.get(k, "")).casefold()
                for k in ("japanese", "hiragana", "meaning_ne", "meaning", "example")
            )]
        st.write(f"जम्मा शब्द: {len(all_words)} | खोजमा भेटिएका: {len(filtered_words)}")
        if not filtered_words:
            st.info("शब्द भेटिएन।")
        for word in filtered_words:
            wid = word.get("id")
            jp = word.get("japanese", "")
            hira = word.get("hiragana", "")
            meaning_ne = word.get("meaning_ne", word.get("meaning", ""))
            with st.expander(f"📘 {jp} — {meaning_ne}"):
                st.markdown(f"### {jp}")
                st.write(f"**Hiragana:** {hira}")
                st.write(f"**नेपाली अर्थ:** {meaning_ne}")
                if word.get("example"):
                    st.write(f"**उदाहरण:** {word['example']}")
                with st.form(f"edit_word_{wid}"):
                    ejp = st.text_input("Japanese", value=jp, key=f"ejp_{wid}")
                    ehira = st.text_input("Hiragana", value=hira, key=f"ehira_{wid}")
                    emean = st.text_input("नेपाली अर्थ", value=meaning_ne, key=f"emean_{wid}")
                    eexample = st.text_input("उदाहरण वाक्य", value=word.get("example", ""), key=f"eexample_{wid}")
                    save_edit = st.form_submit_button("💾 परिवर्तन सुरक्षित गर्ने")
                if save_edit:
                    try:
                        update = {"japanese": ejp.strip(), "hiragana": ehira.strip(), "meaning_ne": emean.strip()}
                        if "example" in word:
                            update["example"] = eexample.strip()
                        sb.table("words").update(update).eq("id", wid).eq("user_id", user_id).execute()
                        st.success("परिवर्तन सुरक्षित भयो!")
                        st.rerun()
                    except Exception as e:
                        st.error("Edit गर्न सकिएन।")
                        st.caption(str(e))
                confirm = st.checkbox("यो शब्द हटाउन चाहन्छु", key=f"confirm_del_{wid}")
                if st.button("🗑️ शब्द Delete", key=f"del_word_{wid}", disabled=not confirm):
                    try:
                        sb.table("words").delete().eq("id", wid).eq("user_id", user_id).execute()
                        st.rerun()
                    except Exception as e:
                        st.error("हटाउन सकिएन।")
                        st.caption(str(e))
    except Exception as e:
        st.error("Dictionary खोल्न सकिएन। words table र permissions जाँच गर।")
        st.caption(str(e))


# --------------------------------------------------
# 5. NOTES (existing notes table preserved; larger editor)
# --------------------------------------------------
with notes_tab:
    st.header("📝 My Notes")
    st.caption("ठूला अक्षरमा लेख, खोज, सच्याऊ र सुरक्षित गर।")
    note_search = st.text_input("🔎 पुराना नोट खोज", key="note_search")
    with st.form("add_note_form"):
        note_title = st.text_input("नोटको शीर्षक", placeholder="Japanese Grammar / Class Notes")
        note_content = st.text_area("ठूलो नोट लेख्ने ठाउँ", height=600, placeholder="यहाँ आफ्ना नोटहरू लेख...", key="new_note_content", help="लामो नोट लेख्न यो ठूलो ठाउँ प्रयोग गर।")
        save_note = st.form_submit_button("💾 नोट सुरक्षित गर्ने", use_container_width=True)
    if save_note:
        if not note_title.strip() or not note_content.strip():
            st.warning("शीर्षक र नोट दुवै लेख।")
        else:
            try:
                sb.table("notes").insert({"user_id": user_id, "title": note_title.strip(), "content": note_content.strip()}).execute()
                st.success("नोट सुरक्षित भयो!")
                st.rerun()
            except Exception as e:
                st.error("नोट सुरक्षित भएन। Supabase मा notes table जाँच गर।")
                st.caption(str(e))
    st.divider()
    try:
        all_notes = sb.table("notes").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data or []
        all_notes = [n for n in all_notes if not str(n.get("title", "")).startswith("[PRIVATE] ")]
        if note_search.strip():
            s = note_search.strip().casefold()
            all_notes = [n for n in all_notes if s in str(n.get("title", "")).casefold() or s in str(n.get("content", "")).casefold()]
        st.write(f"नोटहरू: {len(all_notes)}")
        for note in all_notes:
            nid = note["id"]
            with st.expander("📝 " + note.get("title", "शीर्षक छैन")):
                with st.form(f"edit_note_{nid}"):
                    nt = st.text_input("शीर्षक", value=note.get("title", ""), key=f"nt_{nid}")
                    nc = st.text_area("ठूलो नोट लेख्ने ठाउँ", value=note.get("content", ""), height=600, key=f"nc_{nid}")
                    update_note = st.form_submit_button("💾 नोट सच्याउने")
                if update_note:
                    try:
                        sb.table("notes").update({"title": nt.strip(), "content": nc.strip()}).eq("id", nid).eq("user_id", user_id).execute()
                        st.success("नोट परिवर्तन भयो!")
                        st.rerun()
                    except Exception as e:
                        st.error("नोट परिवर्तन हुन सकेन।")
                        st.caption(str(e))
                del_confirm = st.checkbox("यो नोट हटाउन चाहन्छु", key=f"del_note_confirm_{nid}")
                if st.button("🗑️ नोट Delete", key=f"del_note_{nid}", disabled=not del_confirm):
                    try:
                        sb.table("notes").delete().eq("id", nid).eq("user_id", user_id).execute()
                        st.rerun()
                    except Exception as e:
                        st.error("नोट हटाउन सकिएन।")
                        st.caption(str(e))
    except Exception as e:
        st.error("नोटहरू खोल्न सकिएन। notes table जाँच गर।")
        st.caption(str(e))


# --------------------------------------------------
# 6. CALENDAR: Nepali / English / Japanese month names
# --------------------------------------------------
with calendar_tab:
    st.header("📅 Monthly Calendar / 月間カレンダー")
    today = date.today()
    this_month = today.replace(day=1)
    if "calendar_month" not in st.session_state:
        st.session_state.calendar_month = this_month
    if "calendar_system_month" not in st.session_state or st.session_state.calendar_system_month != this_month:
        st.session_state.calendar_month = this_month
        st.session_state.calendar_system_month = this_month

    def prev_month():
        c = st.session_state.calendar_month
        st.session_state.calendar_month = date(c.year - 1, 12, 1) if c.month == 1 else date(c.year, c.month - 1, 1)
    def next_month():
        c = st.session_state.calendar_month
        st.session_state.calendar_month = date(c.year + 1, 1, 1) if c.month == 12 else date(c.year, c.month + 1, 1)

    current = st.session_state.calendar_month
    np_month, en_month, jp_month = month_names(current.month)
    left, title, right, today_col = st.columns([1, 4, 1, 1])
    left.button("⬅️ अघिल्लो", on_click=prev_month, use_container_width=True)
    title.markdown(f"### {np_month} / {en_month} / {jp_month} {current.year}")
    right.button("अर्को ➡️", on_click=next_month, use_container_width=True)
    if today_col.button("आज", use_container_width=True):
        st.session_state.calendar_month = this_month
        st.rerun()

    st.write(f"**आज / Today / 今日:** {today.strftime('%A, %Y-%m-%d')} / {today.strftime('%Y年%m月%d日')}")
    bs_today = get_bs_date(today)
    if bs_today:
        st.write(f"**नेपाली मिति:** {bs_today.year}/{bs_today.month:02d}/{bs_today.day:02d}")
    if jpholiday:
        try:
            if jpholiday.is_holiday(today):
                st.success("🇯🇵 आज जापानको सार्वजनिक बिदा: " + str(jpholiday.is_holiday_name(today)))
            else:
                st.caption("🇯🇵 आज जापानको सार्वजनिक बिदा होइन।")
        except Exception:
            pass

    weekdays = ["आइत\nSun\n日", "सोम\nMon\n月", "मंगल\nTue\n火", "बुध\nWed\n水", "बिही\nThu\n木", "शुक्र\nFri\n金", "शनि\nSat\n土"]
    cols = st.columns(7)
    for c, name in zip(cols, weekdays):
        c.markdown(f"**{name}**")
    cal = calendar.Calendar(firstweekday=6)
    for week in cal.monthdatescalendar(current.year, current.month):
        cols = st.columns(7)
        for c, d in zip(cols, week):
            with c:
                if d.month != current.month:
                    st.write(" ")
                    continue
                if d == today:
                    st.markdown(f"**🟢 {d.day} · आज / Today**")
                else:
                    st.markdown(f"**{d.day}**")
                bs = get_bs_date(d)
                if bs:
                    st.caption(f"वि.सं. {bs.year}/{bs.month:02d}/{bs.day:02d}")
                if jpholiday:
                    try:
                        if jpholiday.is_holiday(d):
                            st.caption("🇯🇵 " + str(jpholiday.is_holiday_name(d) or "बिदा"))
                    except Exception:
                        pass

    st.divider()
    st.subheader("♈ आजको नेपाली राशिफल / Today’s Nepali Horoscope")
    st.write(f"📅 आजको मिति: {today.strftime('%Y-%m-%d')}  |  {today.strftime('%A')}")
    st.caption("यो सामान्य मनोरञ्जन र आत्मचिन्तनका लागि हो; भविष्य निश्चित रूपमा बताउने कुरा होइन।")
    zodiac = {
        "मेष / Aries": "आज नयाँ काम सुरु गर्दा योजना बनाएर अघि बढ्नुहोस्।",
        "वृष / Taurus": "धैर्य राख्नुहोस् र पढाइ वा काममा नियमितता कायम गर्नुहोस्।",
        "मिथुन / Gemini": "नयाँ कुरा सिक्ने र स्पष्ट संवाद गर्ने राम्रो अभ्यास गर्नुहोस्।",
        "कर्कट / Cancer": "परिवार र साथीहरूसँग शान्त रूपमा कुरा गर्नुहोस्।",
        "सिंह / Leo": "आत्मविश्वास राख्नुहोस्, तर अरूको विचार पनि सुन्नुहोस्।",
        "कन्या / Virgo": "कामलाई साना चरणमा बाँडेर पूरा गर्नु उपयोगी हुनेछ।",
        "तुला / Libra": "निर्णय गर्दा दुवै पक्ष सोच्नुहोस् र सन्तुलन राख्नुहोस्।",
        "वृश्चिक / Scorpio": "ध्यान केन्द्रित गरेर अधुरो काम पूरा गर्ने प्रयास गर्नुहोस्।",
        "धनु / Sagittarius": "नयाँ ज्ञान र अनुभवका लागि समय निकाल्नुहोस्।",
        "मकर / Capricorn": "लक्ष्यअनुसार सानो तर निरन्तर प्रगति गर्नुहोस्।",
        "कुम्भ / Aquarius": "समस्या समाधानमा नयाँ उपाय सोच्नुहोस्।",
        "मीन / Pisces": "आराम, पढाइ र कामबीच सन्तुलन राख्नुहोस्।",
    }
    selected_zodiac = st.selectbox("आफ्नो राशि छान", list(zodiac.keys()))
    st.info(f"**{selected_zodiac} — आजको राशिफल**\n\n{zodiac[selected_zodiac]}")
    st.caption("राशिफल सामान्य सुझाव हो। यो व्यक्तिगत वा वैज्ञानिक भविष्यवाणी होइन।")


# --------------------------------------------------
# 7. JLPT N3 KANJI / WORKSHEET
# --------------------------------------------------
with kanji_tab:
    st.header("🈶 JLPT N3 Kanji Practice")
    st.caption("आफ्नो N3 शब्द/काञ्जी थपेर worksheet बनाऊ। उदाहरणहरू अभ्यासका लागि हुन्, पूर्ण आधिकारिक प्रश्नपत्र होइनन्.")
    n3_seed = [
        ("経験", "けいけん", "अनुभव"),
        ("必要", "ひつよう", "आवश्यक"),
        ("説明", "せつめい", "व्याख्या"),
        ("連絡", "れんらく", "सम्पर्क"),
        ("確認", "かくにん", "पुष्टि गर्नु"),
        ("準備", "じゅんび", "तयारी"),
        ("利用", "りよう", "प्रयोग"),
        ("結果", "けっか", "नतिजा"),
        ("予定", "よてい", "योजना"),
        ("注意", "ちゅうい", "सावधानी"),
        ("関係", "かんけい", "सम्बन्ध"),
        ("増える", "ふえる", "बढ्नु"),
        ("減る", "へる", "घट्नु"),
        ("決める", "きめる", "निर्णय गर्नु"),
        ("続ける", "つづける", "जारी राख्नु"),
    ]
    try:
        saved_kanji = sb.table("words").select("*").eq("user_id", user_id).execute().data or []
        kanji_items = [w for w in saved_kanji if w.get("japanese")]
    except Exception:
        kanji_items = []
    st.subheader("📝 अभ्यास सामग्री थप्ने")
    with st.form("n3_add_form"):
        kj = st.text_input("Kanji / Japanese", placeholder="経験")
        kh = st.text_input("Hiragana", placeholder="けいけん")
        km = st.text_input("नेपाली अर्थ", placeholder="अनुभव")
        save_kj = st.form_submit_button("शब्दकोशमा सुरक्षित गर्ने")
    if save_kj:
        if kj.strip() and km.strip():
            try:
                sb.table("words").insert({"user_id": user_id, "japanese": kj.strip(), "hiragana": kh.strip(), "meaning_ne": km.strip()}).execute()
                st.success("शब्दकोशमा सुरक्षित भयो।")
                st.rerun()
            except Exception as e:
                st.error("सुरक्षित भएन; सम्भवतः यो शब्द पहिले नै छ।")
                st.caption(str(e))
        else:
            st.warning("Kanji र नेपाली अर्थ लेख।")
    source = [(w.get("japanese", ""), w.get("hiragana", ""), w.get("meaning_ne", w.get("meaning", ""))) for w in kanji_items] or n3_seed
    count = st.slider("Worksheet मा कति प्रश्न?", min_value=5, max_value=min(15, max(5, len(source))), value=min(10, max(5, len(source))))
    if st.button("🧾 Worksheet बनाउने", use_container_width=True):
        chosen = source[:count]
        lines = ["JLPT N3 Japanese–Nepali Practice Worksheet", f"Date: {date.today().isoformat()}", "", "A. Hiragana र नेपाली अर्थ लेख्नुहोस्:"]
        for i, (kanji, hira, meaning) in enumerate(chosen, 1):
            lines.append(f"{i}. {kanji}  → Hiragana: __________  Nepali meaning: __________")
        lines += ["", "B. Answer Key", ""]
        for i, (kanji, hira, meaning) in enumerate(chosen, 1):
            lines.append(f"{i}. {kanji} — {hira} — {meaning}")
        worksheet = "\n".join(lines)
        st.text_area("Worksheet preview", worksheet, height=360)
        st.download_button("⬇️ Worksheet TXT डाउनलोड", worksheet, file_name="JLPT_N3_worksheet.txt", mime="text/plain", use_container_width=True)
    st.subheader("📚 नमुना N3 काञ्जी")
    for kanji, hira, meaning in n3_seed:
        st.write(f"**{kanji}**（{hira}）— {meaning}")


# --------------------------------------------------
# 8. CURRENCY CONVERTER (live rate via public endpoint)
# --------------------------------------------------
with currency_tab:
    st.header("💱 Currency Converter")
    st.caption("दर online स्रोतबाट ल्याइन्छ; दर बदलिन सक्छ। कारोबार अघि बैंकको दर जाँच गर्नुहोस्.")
    currencies = ["JPY", "NPR", "USD", "EUR", "INR", "GBP", "AUD", "CAD", "KRW", "CNY"]
    c1, c2 = st.columns(2)
    from_cur = c1.selectbox("बाट / From", currencies, index=0)
    to_cur = c2.selectbox("मा / To", currencies, index=1)
    amount = st.number_input("रकम / Amount", min_value=0.0, value=1000.0, step=100.0)
    if st.button("दर अपडेट गरेर हिसाब गर", use_container_width=True):
        try:
            response = requests.get(f"https://open.er-api.com/v6/latest/{from_cur}", timeout=12)
            response.raise_for_status()
            data = response.json()
            rate = data.get("rates", {}).get(to_cur)
            if rate is None:
                st.error("यो currency को दर उपलब्ध भएन।")
            else:
                st.metric(f"{amount:,.2f} {from_cur} ≈", f"{amount * rate:,.2f} {to_cur}")
                st.caption(f"दर: 1 {from_cur} = {rate:.6g} {to_cur} | Update: {data.get('time_last_update_utc', 'unknown')}")
        except Exception as e:
            st.error("Live currency दर ल्याउन सकिएन। Internet/API उपलब्धता जाँच गर।")
            st.caption(str(e))


# --------------------------------------------------
# 9. JAPANESE / NEPALI NEWS via RSS (links only; not auto-translated)
# --------------------------------------------------
with news_tab:
    st.header("📰 Japanese / Nepali News")
    st.caption("समाचार स्रोतबाट headline र link देखाइन्छ। यहाँबाट मूल लेख खोल्न सकिन्छ; स्वतः अनुवादका लागि AI tab प्रयोग गर्न सकिन्छ।")
    news_choice = st.radio("समाचार स्रोत", ["NHK Japanese", "Nepal news (Google News RSS)"], horizontal=True)
    rss_url = (
        "https://www3.nhk.or.jp/rss/news/cat0.xml"
        if news_choice == "NHK Japanese"
        else "https://news.google.com/rss/search?q=Nepal&hl=ne&gl=NP&ceid=NP:ne"
    )
    if st.button("🔄 समाचार अपडेट", use_container_width=True):
        try:
            feed = feedparser.parse(rss_url)
            entries = feed.entries[:12]
            if not entries:
                st.warning("समाचार भेटिएन। केही बेरपछि फेरि प्रयास गर।")
            for entry in entries:
                st.markdown(f"**[{entry.get('title', 'शीर्षक छैन')}]({entry.get('link', '#')})**")
                if entry.get("published"):
                    st.caption(entry["published"])
                st.divider()
        except Exception as e:
            st.error("समाचार लोड गर्न सकिएन।")
            st.caption(str(e))
    st.info("समाचार खोल्न headline क्लिक गर। समाचारको पूरा नेपाली अनुवाद स्वतः उपलब्ध हुँदैन; अनुवाद गर्न AI सहायकमा headline वा लेखको अंश paste गर।")


# --------------------------------------------------
# 10. DOCUMENTS: persistent Supabase Storage upload/list/download
# --------------------------------------------------
with docs_tab:
    st.header("📎 My Documents")
    st.write("PDF, DOCX, TXT, Excel, CSV र फोटोहरू आफ्नो account मा cloud मा सुरक्षित राख्न सकिन्छ।")
    st.caption("पहिलो पटक Supabase Storage मा `user-documents` नामको **Private** bucket बनाउनुपर्छ। तलका upload/list सुविधाले त्यही bucket प्रयोग गर्छन्।")
    bucket_name = "user-documents"
    uploaded = st.file_uploader(
        "फाइल छान", type=["pdf", "txt", "docx", "doc", "xlsx", "csv", "png", "jpg", "jpeg"],
        accept_multiple_files=False
    )
    if uploaded:
        st.write(f"छानिएको फाइल: **{uploaded.name}** ({uploaded.size:,} bytes)")
        if st.button("☁️ मेरो account मा सुरक्षित गर्ने", use_container_width=True):
            try:
                safe_name = os.path.basename(uploaded.name).replace("\\", "_").replace("/", "_")
                storage_path = f"{user_id}/{int(datetime.now().timestamp())}_{safe_name}"
                sb.storage.from_(bucket_name).upload(
                    path=storage_path,
                    file=uploaded.getvalue(),
                    file_options={"content-type": uploaded.type or "application/octet-stream", "upsert": "false"}
                )
                st.success("फाइल cloud मा सुरक्षित भयो।")
                st.rerun()
            except Exception as e:
                st.error("फाइल सुरक्षित भएन। Supabase मा `user-documents` Private bucket र Storage policy जाँच गर।")
                st.caption(str(e))

    st.divider()
    st.subheader("☁️ सुरक्षित गरिएका फाइलहरू")
    if st.button("🔄 फाइल सूची अपडेट", use_container_width=True):
        st.session_state["refresh_documents"] = True
    try:
        stored_files = sb.storage.from_(bucket_name).list(path=user_id)
        if not stored_files:
            st.info("अहिलेसम्म cloud मा फाइल छैन, वा bucket/policy setup बाँकी छ।")
        for item in stored_files:
            file_name = item.get("name", "") if isinstance(item, dict) else ""
            if not file_name:
                continue
            storage_path = f"{user_id}/{file_name}"
            c1, c2 = st.columns([4, 1])
            c1.write("📄 " + file_name)
            if c2.button("⬇️ डाउनलोड", key="download_doc_" + file_name, use_container_width=True):
                try:
                    file_bytes = sb.storage.from_(bucket_name).download(storage_path)
                    st.download_button(
                        "फाइल डाउनलोड गर्न यहाँ थिच", data=file_bytes, file_name=file_name,
                        mime="application/octet-stream", key="download_result_" + file_name
                    )
                except Exception as e:
                    st.error("डाउनलोड भएन। Storage policy जाँच गर।")
                    st.caption(str(e))
    except Exception as e:
        st.warning("Cloud document list खोल्न सकिएन। Supabase Dashboard → Storage मा `user-documents` नामको Private bucket बनाउनुहोस् र policy मिलाउनुहोस्।")
        st.caption(str(e))

# --------------------------------------------------
# 11. AI ASSISTANT (requires OpenAI API key in Streamlit secrets)
# --------------------------------------------------
with ai_tab:
    st.header("🤖 AI Assistant")
    st.write("Japanese grammar, N3 Kanji, Nepali meaning, translation, worksheet र सामान्य प्रश्न सोध्न सकिन्छ।")
    st.caption("यो सुविधा चलाउन Streamlit Secrets मा OPENAI_API_KEY राखिएको हुनुपर्छ।")
    prompt = st.text_area("आफ्नो प्रश्न लेख", height=180, placeholder="例：経験（けいけん）の नेपाली अर्थ र एउटा उदाहरण देऊ।")
    if st.button("🤖 AI लाई सोध", use_container_width=True):
        api_key = st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
        if not prompt.strip():
            st.warning("पहिले प्रश्न लेख।")
        elif not api_key:
            st.error("AI चलाउन Streamlit Cloud → App settings → Secrets मा OPENAI_API_KEY थप्नुपर्छ।")
        elif OpenAI is None:
            st.error("OpenAI package install भएको छैन। requirements.txt मा openai थप।")
        else:
            try:
                client = OpenAI(api_key=api_key)
                with st.spinner("उत्तर तयार हुँदैछ..."):
                    result = client.responses.create(
                        model="gpt-4.1-mini",
                        input=[
                            {"role": "system", "content": "You are a helpful Japanese-Nepali learning assistant. Explain in simple Nepali. For Japanese words include Kanji, Hiragana, Nepali meaning, and one short example when useful. For news, summarize only text supplied by the user and distinguish uncertainty."},
                            {"role": "user", "content": prompt.strip()},
                        ],
                    )
                st.markdown(result.output_text)
            except Exception as e:
                st.error("AI उत्तर ल्याउन सकिएन। API key, billing र model access जाँच गर।")
                st.caption(str(e))



# --------------------------------------------------
# 12. PIN-LOCKED PRIVATE FOLDER (personal notes only)
# --------------------------------------------------
with private_tab:
    st.header("🔒 Private Folder")
    st.write("This folder is for your personal notes. Set the PIN in Streamlit Cloud Secrets.")
    st.caption("For safety, adult/pornographic website links are not included. This folder stores private notes in your signed-in account.")

    private_pin = st.secrets.get("PRIVATE_FOLDER_PIN", "")
    if not private_pin:
        st.warning('To enable this folder, add PRIVATE_FOLDER_PIN = "9828" in Streamlit Cloud → App settings → Secrets.')
    else:
        if "private_folder_unlocked" not in st.session_state:
            st.session_state.private_folder_unlocked = False
        if not st.session_state.private_folder_unlocked:
            with st.form("private_folder_unlock_form"):
                entered_pin = st.text_input("Enter folder PIN", type="password")
                unlock = st.form_submit_button("Unlock Private Folder", use_container_width=True)
            if unlock:
                if entered_pin == str(private_pin):
                    st.session_state.private_folder_unlocked = True
                    st.rerun()
                else:
                    st.error("Incorrect PIN. Try again.")
        else:
            if st.button("🔐 Lock folder", use_container_width=False):
                st.session_state.private_folder_unlocked = False
                st.rerun()

            st.subheader("Add a private note")
            with st.form("private_note_add_form"):
                private_title = st.text_input("Title", placeholder="Private study note")
                private_content = st.text_area("Private note", height=360, placeholder="Write your private note here...")
                save_private = st.form_submit_button("Save Private Note", use_container_width=True)
            if save_private:
                if not private_title.strip() or not private_content.strip():
                    st.warning("Enter both a title and note.")
                else:
                    try:
                        sb.table("notes").insert({
                            "user_id": user_id,
                            "title": "[PRIVATE] " + private_title.strip(),
                            "content": private_content.strip()
                        }).execute()
                        st.success("Private note saved.")
                        st.rerun()
                    except Exception as e:
                        st.error("Could not save the private note. Check the Supabase notes table.")
                        st.caption(str(e))

            st.divider()
            st.subheader("Saved private notes")
            try:
                private_notes = sb.table("notes").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data or []
                private_notes = [n for n in private_notes if str(n.get("title", "")).startswith("[PRIVATE] ")]
                if not private_notes:
                    st.info("No private notes saved yet.")
                for note in private_notes:
                    note_id = note.get("id")
                    shown_title = str(note.get("title", "[PRIVATE] Note"))[10:]
                    with st.expander("🔒 " + shown_title):
                        with st.form(f"private_note_edit_{note_id}"):
                            edit_title = st.text_input("Title", value=shown_title, key=f"private_title_{note_id}")
                            edit_content = st.text_area("Private note", value=note.get("content", ""), height=360, key=f"private_content_{note_id}")
                            save_edit = st.form_submit_button("Update Private Note")
                        if save_edit:
                            try:
                                sb.table("notes").update({
                                    "title": "[PRIVATE] " + edit_title.strip(),
                                    "content": edit_content.strip()
                                }).eq("id", note_id).eq("user_id", user_id).execute()
                                st.success("Private note updated.")
                                st.rerun()
                            except Exception as e:
                                st.error("Could not update the private note.")
                                st.caption(str(e))
                        confirm_delete = st.checkbox("Delete this private note", key=f"private_delete_confirm_{note_id}")
                        if st.button("Delete Private Note", key=f"private_delete_{note_id}", disabled=not confirm_delete):
                            try:
                                sb.table("notes").delete().eq("id", note_id).eq("user_id", user_id).execute()
                                st.rerun()
                            except Exception as e:
                                st.error("Could not delete the private note.")
                                st.caption(str(e))
            except Exception as e:
                st.error("Could not load private notes. Check the Supabase notes table and user-level permissions.")
                st.caption(str(e))


# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.divider()
st.caption("Japanese Nepali Learning Hub | Your account shows your own data after login.")
