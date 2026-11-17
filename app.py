import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from iam import initialize, identities, events, joiner, mover, leaver, access_findings, ROLES

st.set_page_config(page_title='IdentityGuard', page_icon='🛡️', layout='wide')
initialize()
st.title('🛡️ IdentityGuard')
st.caption('Local IAM learning dashboard | Synthetic identities | No production authentication')
page = st.sidebar.radio('Navigate', ['Overview', 'Identities', 'JML Workflows', 'Access Review', 'Audit Log'])
people = identities()

if page == 'Overview':
    a,b,c,d = st.columns(4)
    a.metric('Total identities', len(people))
    b.metric('Active', sum(p['status']=='Active' for p in people))
    c.metric('Disabled', sum(p['status']=='Disabled' for p in people))
    d.metric('Active administrators', len(access_findings()))
    if people:
        df = pd.DataFrame(people)
        st.plotly_chart(px.bar(df.groupby('department',as_index=False).size(), x='department',y='size',title='Identities by department'),use_container_width=True)
        st.plotly_chart(px.pie(df,names='role',title='Role distribution'),use_container_width=True)
elif page == 'Identities':
    st.subheader('Identity directory')
    st.dataframe(pd.DataFrame(people),hide_index=True,use_container_width=True)
elif page == 'JML Workflows':
    st.subheader('Joiner - Mover - Leaver')
    join_tab, move_tab, leave_tab = st.tabs(['Onboard', 'Transfer', 'Offboard'])
    with join_tab:
        with st.form('join'):
            name=st.text_input('Full name')
            email=st.text_input('Email')
            department=st.text_input('Department')
            role=st.selectbox('Role',ROLES,index=1)
            submitted=st.form_submit_button('Create identity')
            if submitted:
                try:
                    joiner(name,email,department,role)
                    st.success('Identity created.'); st.rerun()
                except (ValueError,sqlite3.IntegrityError) as exc: st.error(str(exc))
    active=[p for p in people if p['status']=='Active']
    choices={f"{p['id']} - {p['name']} ({p['email']})":p['id'] for p in active}
    with move_tab:
        if choices:
            with st.form('move'):
                selected=st.selectbox('Identity',list(choices),key='move_identity')
                dept=st.text_input('New department')
                role=st.selectbox('New role',ROLES)
                if st.form_submit_button('Update access'):
                    try:
                        mover(choices[selected],dept,role)
                        st.success('Identity updated.'); st.rerun()
                    except ValueError as exc: st.error(str(exc))
        else: st.info('No active identities.')
    with leave_tab:
        if choices:
            with st.form('leave'):
                selected=st.selectbox('Identity to disable',list(choices),key='leave_identity')
                confirm=st.checkbox('Confirm disabling this demo identity')
                if st.form_submit_button('Disable identity'):
                    if not confirm: st.error('Confirmation required.')
                    else:
                        try:
                            leaver(choices[selected]); st.success('Identity disabled.'); st.rerun()
                        except ValueError as exc: st.error(str(exc))
        else: st.info('No active identities.')
elif page == 'Access Review':
    st.subheader('Privileged access review')
    st.info('Review candidates only: active Administrator accounts. This is not a full risk-scoring engine.')
    st.dataframe(pd.DataFrame(access_findings()),hide_index=True,use_container_width=True)
else:
    st.subheader('Audit trail')
    st.dataframe(pd.DataFrame(events()),hide_index=True,use_container_width=True)
