# streamlit_app.py
import streamlit as st
from snowflake.snowpark.functions import col

st.set_page_config(page_title="Smoothie Builder", page_icon="🥤")

st.title(":cup_with_straw: Customize Your Smoothie :cup_with_straw:")
st.write("Choose the fruits you want in your custom Smoothie!")

# --- connect (uses .streamlit/secrets.toml) ---
@st.cache_resource(show_spinner=False)
def get_session():
    cnx = st.connection("snowflake")
    return cnx.session()

connect_ok = True
try:
    with st.spinner("Connecting to Snowflake..."):
        session = get_session()
        # quick ping to fail fast on bad creds/role/warehouse
        session.sql("select 1").collect()
except Exception as e:
    connect_ok = False
    st.error(f"Could not connect to Snowflake: {e}")

# --- fetch fruit options as a plain list ---
fruit_options = []
if connect_ok:
    @st.cache_data(ttl=600)
    def load_fruits():
        pdf = (
            session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
            .select(col("FRUIT_NAME"))
            .to_pandas()
        )
        return sorted(
            pdf["FRUIT_NAME"].dropna().astype(str).unique().tolist()
        )
    fruit_options = load_fruits()

# --- inputs ---
name_on_order = st.text_input("Name on Smoothie:")

ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    fruit_options,
    max_selections=5,
)

# --- submit ---
if st.button("Submit Order", type="primary"):
    if not connect_ok:
        st.error("Not connected to Snowflake.")
    elif not name_on_order.strip():
        st.error("Please enter a name for your smoothie.")
    elif not ingredients_list:
        st.error("Please choose at least one ingredient.")
    else:
        # safe strings
        esc = lambda s: s.replace("'", "''")
        ingredients_string = " ".join(ingredients_list).strip()

        insert_sql = f"""
            INSERT INTO SMOOTHIES.PUBLIC.ORDERS (INGREDIENTS, NAME_ON_ORDER)
            VALUES ('{esc(ingredients_string)}', '{esc(name_on_order.strip())}')
        """
        try:
            session.sql(insert_sql).collect()
            st.success(f"Your Smoothie is ordered, {name_on_order.strip()}! ✅")
        except Exception as e:
            st.error(f"Order failed: {e}")
