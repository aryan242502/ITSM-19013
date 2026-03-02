import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import firebase_admin
from firebase_admin import credentials, firestore

# ---------- FIREBASE CONNECT (STREAMLIT SECRETS) ----------
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------- PAGE ----------
st.set_page_config(page_title="Smart City ITSM", layout="wide")

# ---------- SESSION ----------
if "logged" not in st.session_state:
    st.session_state.logged = False

# ================== AUTH PAGE ==================
if not st.session_state.logged:

    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    # ---------------- LOGIN ----------------
    with tab1:
        st.subheader("Login")

        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")

        if st.button("Login"):
            users = db.collection("users")\
                .where("username","==",user)\
                .where("password","==",pwd).stream()

            u = None
            for i in users:
                u = i.to_dict()

            if u:
                st.session_state.logged = True
                st.session_state.role = u["role"]
                st.session_state.username = user
                st.success("Login Success")
                st.rerun()
            else:
                st.error("Invalid Login")

    # ---------------- REGISTER ----------------
    with tab2:
        st.subheader("Create Account")

        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        role = st.selectbox("Role", ["Citizen", "Admin"])

        if st.button("Register User"):

            # check if exists
            existing = db.collection("users").where("username","==",new_user).stream()
            exist_flag = False
            for e in existing:
                exist_flag = True

            if exist_flag:
                st.warning("⚠ Username already exists")
            else:
                db.collection("users").add({
                    "username": new_user,
                    "password": new_pass,
                    "role": role
                })
                st.success("✅ User Registered Successfully")

    st.stop()

# ================== AFTER LOGIN ==================
role = st.session_state.role
username = st.session_state.username

# ---------- MENU ----------
if role == "Admin":
    menu = st.sidebar.selectbox("Menu",
    ["Dashboard","Admin Panel"])
else:
    menu = st.sidebar.selectbox("Citizen Menu",
    ["Register Complaint","My Complaints"])

st.title("🏙️ Smart City Infrastructure Management")

# ---------- DASHBOARD ----------
if menu == "Dashboard":
    st.header("📊 Analytics")

    comp = db.collection("complaints").stream()
    data = [c.to_dict() for c in comp]

    if data:
        df = pd.DataFrame(data)

        if "category" in df.columns:
            st.bar_chart(df["category"].value_counts())

        if "status" in df.columns:
            st.subheader("Status Distribution")
            fig, ax = plt.subplots()
            df["status"].value_counts().plot.pie(autopct="%1.1f%%", ax=ax)
            st.pyplot(fig)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total", len(df))
        col2.metric("Pending", len(df[df["status"]=="Pending"]) if "status" in df.columns else 0)
        col3.metric("Resolved", len(df[df["status"]=="Resolved"]) if "status" in df.columns else 0)

    else:
        st.info("No complaints yet")

# ---------- REGISTER COMPLAINT ----------
elif menu == "Register Complaint":
    st.header("Register Complaint")

    cat = st.selectbox("Category",
    ["Road Damage","Street Light Fault","Water Issue","Drainage Block"])

    desc = st.text_area("Description")
    loc = st.text_input("Location")

    priority = "High" if "Water" in cat or "Drainage" in cat else "Medium"

    if st.button("Submit Complaint"):
        db.collection("complaints").add({
            "username": username,
            "category":cat,
            "description":desc,
            "location":loc,
            "priority":priority,
            "status":"Pending",
            "date":datetime.now().strftime("%Y-%m-%d %H:%M")
        })

        st.success("✅ Complaint Submitted")

# ---------- MY COMPLAINT ----------
elif menu == "My Complaints":
    st.header("My Complaints")

    docs = db.collection("complaints").where("username","==",username).stream()

    data = []
    for c in docs:
        d = c.to_dict()
        d["id"] = c.id
        data.append(d)

    if data:
        st.dataframe(pd.DataFrame(data))
    else:
        st.info("No complaints found")

# ---------- ADMIN PANEL ----------
elif menu == "Admin Panel":
    st.header("Admin Complaint Control")

    docs = [(c.id, c.to_dict()) for c in db.collection("complaints").stream()]

    data = []
    for doc_id, doc_data in docs:
        doc_data["id"] = doc_id
        data.append(doc_data)

    if data:
        df = pd.DataFrame(data)
        st.dataframe(df)

        cid = st.selectbox("Select Complaint ID", df["id"])
        new_status = st.selectbox("Status",["Pending","In Progress","Resolved"])

        if st.button("Update"):
            doc_ref = db.collection("complaints").document(cid)
            if doc_ref.get().exists:
                doc_ref.update({"status": new_status})
                st.success("✅ Updated")
            else:
                st.error("Complaint not found")

        if st.button("Delete"):
            db.collection("complaints").document(cid).delete()
            st.warning("🗑 Deleted")

    else:
        st.info("No complaints available")
