import pandas as pd
import numpy as np
import streamlit as st
import altair as alt


def login_screen():
    st.header("This application is private, you must log in to access it.")
    st.button("Log in with Microsoft.", on_click=st.login)

if not st.user.is_logged_in:
    login_screen()
else:
    st.header(f"Welcome, {st.user.name}")

st.button("Log out", on_click=st.logout)

F24 = pd.read_excel('data/source/Fall-2024-PIN-PWL.xlsx', header=0)
S25 = pd.read_excel('data/source/Spring-2025-PIN-PWL.xlsx', header=0)

@st.cache_data
def preprocess(df):
    df['Identifier'] = df['Subject'].astype(str) + '-' + df['COURSE'].astype(str)
    drop_these = ['ACADEMIC_PERIOD', 'SUB_ACADEMIC_PERIOD', 'Subject', 'COURSE', 'DEPARTMENT', 'Sec-CRN', 'DAYS', 'TIME', 'BUILDING', 'ROOM', 'INSTRUCTOR_ID',
                  'LASTNAME', 'FIRSTNAME', 'GROUPNBR', 'Date', 'WAITLIST_COUNT', 'Waitlist remaining space']
    df.drop(drop_these, axis=1, inplace=True)
    df.rename({'ENRL(RE,RW,RT,RC,AU)': 'Enrl'}, axis=1, inplace=True)
    return df

@st.cache_data
def download(df):
    return df.to_csv(index=False).encode("utf-8")

F24_Standard = preprocess(F24)
S25_Standard = preprocess(S25)

F24_Standard_WL = F24_Standard.query('CAMPUS == "PWL"')
F24_Standard_PIN = F24_Standard.query('CAMPUS == "PIN"')
S25_Standard_WL = S25_Standard.query('CAMPUS == "PWL"')
S25_Standard_PIN = S25_Standard.query('CAMPUS == "PIN"')

st.set_page_config(page_title='Faculty Loadings', layout='wide')
st.title("Faculty Loading Insights")

st.sidebar.header("Filter Options")
selected_source = st.sidebar.selectbox("Choose a category", ['West Lafayette', 'Indianapolis'], 
                                       index=None, placeholder="Select a campus location")
st.write("Selected filter", selected_source)
selected_semester = st.sidebar.selectbox("Choose a category", ['Fall 2024', 'Spring 2025', 'All'],
                                       index=None, placeholder='Select a semester')
st.write("Selected filter", selected_semester)


# dataframe selection logic with f24 as default
if selected_source == 'West Lafayette' and selected_semester == 'Fall 2024':
    df = F24_Standard_WL
elif selected_source == 'West Lafayette' and selected_semester == 'Spring 2025':
    df = S25_Standard_WL
elif selected_source == 'West Lafayette' and selected_semester == 'All':
    df = pd.concat([F24_Standard, S25_Standard], ignore_index=True)
    df = df.query('CAMPUS == "PWL"')
elif selected_source == 'Indianapolis' and selected_semester == 'Fall 2024':
    df = F24_Standard_PIN
elif selected_source == 'Indianapolis' and selected_semester == 'Spring 2025':
    df = S25_Standard_PIN
elif selected_source == 'Indianapolis' and selected_semester == 'All':
    df = pd.concat([F24_Standard, S25_Standard], ignore_index=True)
    df = df.query('CAMPUS == "PIN"')
else:
    df = F24_Standard

# ---
# Charts
# ---

if st.user.is_logged_in:

# Departmental Load
    st.subheader("Department Load")
    dept_agg = df.groupby('DEPARTMENT_DESC', as_index=False)['Enrl'].sum()
    dpt_chart = alt.Chart(dept_agg).mark_bar().encode(
        x=alt.X("DEPARTMENT_DESC:N", axis=alt.Axis(labels=False), title='Department'),
        y=alt.Y("Enrl:Q", title='Total Enrollment'),
        color="DEPARTMENT_DESC:N"
    )
    st.altair_chart(dpt_chart, use_container_width=True)

# set columns
    col1, col2 = st.columns(2)

# Instructor Load
    instr_agg = df.groupby(['Instructor', 'Identifier', 'CAMPUS', 'INSTR_TYPE'], as_index=False)[['Enrl', 'LIMIT']].sum()

    if selected_source == 'West Lafayette':
        instr_agg = instr_agg.query('CAMPUS == "PWL"')
    else:
        instr_agg = instr_agg.query('CAMPUS == "PIN"')

    st.sidebar.header("Instructor Search")
    instr = sorted(instr_agg['Instructor'].unique())
    selected_instr = st.sidebar.selectbox("Select an instructor", instr)

    instr_filter = instr_agg[instr_agg['Instructor'] == selected_instr]
    st.subheader(f"Instructor Course Load: {selected_instr}")
#instr_melt = instr_filter.melt(id_vars=['Identifier'], 
#                               value_vars=['Enrl', 'LIMIT'],
#                               var_name='Type', value_name='Count')


# v1 with grouped charts: Nah, this isn't too good for it
#instructor_chart = alt.Chart(instr_melt).mark_bar().encode(
#    x=alt.X('Identifier:N', title='Course'),
#    y=alt.Y('Count:Q', title='Enrollment V. Limit'),
#    color=alt.Color('Type:N', scale=alt.Scale(scheme='tableau10')),
#    column=alt.Column('Type:N', title=None)
#    ).properties(width=300, height=300)

# v2 with bar + line maybe?
    bars = alt.Chart(instr_filter).mark_bar().encode(
        x='Identifier:N',
        y='Enrl:Q',
        color=alt.value('steelblue')
    )

    limits = alt.Chart(instr_filter).mark_rule(color='red').encode(
        x='Identifier:N',
        y='LIMIT:Q'
    )

    instructor_chart = bars + limits

    with col1:
        st.altair_chart(instructor_chart, use_container_width=True)

        st.markdown(":warning: This graph includes all types of course delivery methods. Instructors may include students teaching classes in their capacity as TAs.")

# Instructor Load for both Labs and Lectures
    st.markdown("#### Enrollment and Limits by Instruction Type")

    bars2 = alt.Chart(instr_filter).mark_bar().encode(
        x=alt.X('INSTR_TYPE:N', title='Instruction Type'),
        y=alt.Y('Enrl:Q', title='Enrollment for course'),
        color=alt.value('steelblue'),
        tooltip=['Identifier', 'Enrl', 'LIMIT']
    )

    limit2 = alt.Chart(instr_filter).mark_rule(color='red').encode(
        x='INSTR_TYPE:N',
        y='LIMIT:Q'
    )

    lab_lecs = bars2 + limit2

    with col2:
        st.altair_chart(lab_lecs, use_container_width=True)
        st.markdown(":warning: Total load includes all available instruction types for a course.")

# Metrics
    st.markdown("#### Enrollment by Course")

    for i, r in instr_filter.iterrows():
        enrl = int(r['Enrl'])
        limit = int(r['LIMIT'])
        delta = enrl - limit

        if delta > 0:
            delta_text = f"+{delta} over limit"
            delta_color = 'inverse'
        elif delta < 0:
            delta_text = f"{delta} under limit"
            delta_color = 'normal'
        else:
            delta_text = "At limit"
            delta_color = 'off'

        st.metric(label=f"{r['Identifier']} ({r['INSTR_TYPE']})", 
                value=f"{enrl}", delta=delta_text, delta_color=delta_color)

# Table for instructor data
    st.subheader(f"Tabular data for {selected_instr}")
    st.dataframe(instr_filter, use_container_width=True, hide_index=True)
    data = download(instr_filter)

    st.download_button(
        label="Download Instructor data",
        data=data,
        file_name=f'{selected_instr}-{selected_source}-{selected_semester}.csv',
        mime="text/csv",
        icon=":material/download:"
    )

else:
    st.header("Access Restricted")